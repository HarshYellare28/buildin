from __future__ import annotations

from fastapi.testclient import TestClient

from src.main import app
from src.models.schemas import Medication
from src.routes import plans as plans_route
from src.services import extract

client = TestClient(app)


def test_document_schedule_is_kept_but_numeric_dose_stays_locked(monkeypatch):
    monkeypatch.setattr(
        extract.sarvam,
        "doc_ai_extract",
        lambda *args, **kwargs: {
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
        },
    )
    medications = extract.extract_from_document(b"fake-image", "prescription.png", "image/png")

    assert len(medications) == 1
    medication = medications[0]
    assert medication.dose == 5
    assert medication.times == ["08:00"]
    assert medication.food_rule == "with_food"
    assert medication.confidence == 0.5
    assert "please verify" in medication.schedule_text


def test_multipart_ocr_accepts_starlette_upload(monkeypatch):
    def fake_extract_document(*args, **kwargs):
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

    monkeypatch.setattr(plans_route, "extract_from_document", fake_extract_document)
    client.post("/demo/reset").raise_for_status()
    response = client.post(
        "/plans/extract",
        data={"source": "ocr"},
        files={"file": ("prescription.png", b"fake-image", "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["medications"][0]["source"] == "ocr"
