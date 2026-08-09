from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from src.main import app
from src.models.schemas import Medication
from src.routes import plans as plans_route
from src.services import document_extract

client = TestClient(app)


class _SubmitResponse:
    status_code = 200

    @staticmethod
    def json() -> dict:
        return {"job_id": "job_test"}


class _FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, *args, **kwargs):
        return _SubmitResponse()


def test_document_schedule_is_kept_but_numeric_dose_stays_locked(monkeypatch):
    monkeypatch.setattr(document_extract, "SARVAM_API_KEY", "test-key")
    monkeypatch.setattr(document_extract.httpx, "AsyncClient", _FakeAsyncClient)

    async def fake_poll(*args, **kwargs):
        return {
            "status": "completed",
            "result": {
                "medications": [
                    {
                        "name": "Amlodipine 10mg",
                        "dose": "10 mg",
                        "schedule": "subah khane ke saath",
                    }
                ]
            },
        }

    monkeypatch.setattr(document_extract, "_poll", fake_poll)
    medications = asyncio.run(
        document_extract.extract_document(b"fake-image", "prescription.png", "image/png")
    )

    assert len(medications) == 1
    medication = medications[0]
    assert medication.dose == 5
    assert medication.times == ["08:00"]
    assert medication.food_rule == "with_food"
    assert medication.confidence == 0.5
    assert "please verify" in medication.schedule_text


def test_multipart_ocr_accepts_starlette_upload(monkeypatch):
    async def fake_extract_document(*args, **kwargs):
        return [
            Medication(
                id="med_amlodipine",
                name_raw="Amlodipine 5mg",
                name_normalized="amlodipine",
                dose=5,
                unit="mg",
                times=["21:00"],
                schedule_text="Night",
                criticality="high",
                source="ocr",
                confidence=0.9,
            )
        ]

    monkeypatch.setattr(plans_route, "extract_document", fake_extract_document)
    client.post("/demo/reset").raise_for_status()
    response = client.post(
        "/plans/extract",
        data={"source": "ocr"},
        files={"file": ("prescription.png", b"fake-image", "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["medications"][0]["source"] == "ocr"
