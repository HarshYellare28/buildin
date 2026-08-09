from __future__ import annotations

from fastapi.testclient import TestClient

from src.main import app
from src.routes import sarvam_outbound as outbound_route
from src.services import plans
from src.services import sarvam_outbound as outbound_service

client = TestClient(app)


def _calling_dose(monkeypatch) -> tuple[str, dict]:
    client.post("/demo/reset").raise_for_status()
    plan = client.post(
        "/plans/extract",
        json={
            "source": "paste",
            "text": "Amlodipine 5 mg roj raat ko 1 tablet",
        },
    ).json()
    client.post(f"/plans/{plan['plan_id']}/activate").raise_for_status()
    dose = client.post(
        "/doses/trigger",
        json={"plan_id": plan["plan_id"], "medication_id": "med_amlodipine"},
    ).json()
    monkeypatch.setattr(
        outbound_route,
        "place_call",
        lambda *_args, **_kwargs: {"attempt_id": "attempt_test_1"},
    )
    response = client.post(f"/sarvam/outbound/{dose['dose_id']}")
    assert response.status_code == 200
    return plan["plan_id"], dose


def test_outbound_payload_uses_locked_agent_variable_names(monkeypatch):
    monkeypatch.setattr(outbound_service, "SARVAM_USER_PHONE_NUMBER", "+918779773480")
    monkeypatch.setattr(
        outbound_service,
        "SARVAM_WEBHOOK_URL",
        "https://dawa.arnavpanicker.com/api/sarvam/webhook",
    )
    monkeypatch.setattr(outbound_service, "SARVAM_WEBHOOK_TOKEN", "test-token")
    dose = {
        "id": "dose_1",
        "plan_id": "plan_demo_1",
        "medication": {
            "name_normalized": "amlodipine",
            "dose": 5.0,
            "unit": "mg",
        },
    }

    payload = outbound_service.build_payload(dose, "Lakshmi", "Ananya")

    assert payload["app_config"]["agent_variables"] == {
        "Patient_name": "Lakshmi",
        "med_name": "Amlodipine",
        "med_dose": "5 milligram",
        "care_giver": "Ananya",
        "user_name": "Lakshmi",
        "call_summary": "Evening dose check for Amlodipine 5mg",
    }
    assert payload["user_config"]["user_phone_number"] == "+918779773480"
    assert payload["webhook_config"]["metadata"] == {
        "dose_id": "dose_1",
        "plan_id": "plan_demo_1",
        "test": True,
    }
    assert payload["webhook_config"]["url"].endswith("?token=test-token")


def test_webhook_completes_primary_path_and_creates_packet(monkeypatch):
    plan_id, dose = _calling_dose(monkeypatch)
    monkeypatch.setattr(outbound_route, "SARVAM_WEBHOOK_TOKEN", "test-token")

    response = client.post(
        "/sarvam/webhook?token=test-token",
        json={
            "attempt_id": "attempt_test_1",
            "status": "connected",
            "metadata": {"dose_id": dose["dose_id"], "plan_id": plan_id, "test": True},
            "transcript": [
                {"role": "agent", "text": "Aapne Amlodipine li?"},
                {"role": "user", "text": "Haan, le li. Lekin pet mein jalan ho rahi hai."},
            ],
            "final_agent_variables": {
                "call_summary": "Dose taken; patient reported stomach burning."
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["processed"] is True
    packet = client.get("/packets/latest", params={"plan_id": plan_id}).json()
    assert packet["status"] == "taken"
    assert packet["exception"] == {
        "type": "side_effect",
        "patient_reported": "pet mein jalan ho rahi hai",
        "normalized": "abdominal_burning",
    }
    event_types = [
        event["type"]
        for event in client.get("/events", params={"plan_id": plan_id}).json()["events"]
    ]
    assert event_types[-3:] == ["dose_completed", "exception_logged", "packet_sent"]


def test_webhook_rejects_wrong_token(monkeypatch):
    monkeypatch.setattr(outbound_route, "SARVAM_WEBHOOK_TOKEN", "test-token")
    response = client.post("/sarvam/webhook?token=wrong", json={})
    assert response.status_code == 401


def test_webhook_marks_failed_call_without_inventing_outcome(monkeypatch):
    plan_id, dose = _calling_dose(monkeypatch)
    monkeypatch.setattr(outbound_route, "SARVAM_WEBHOOK_TOKEN", "test-token")
    response = client.post(
        "/sarvam/webhook?token=test-token",
        json={
            "attempt_id": "attempt_test_1",
            "status": "no_answer",
            "failure_reason": "callee did not answer",
            "metadata": {"dose_id": dose["dose_id"], "plan_id": plan_id},
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert plans.get_dose(dose["dose_id"])["status"] == "failed"
    assert client.get("/packets/latest", params={"plan_id": plan_id}).status_code == 404
