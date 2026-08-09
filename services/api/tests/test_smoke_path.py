"""End-to-end contract path, no voice. Mirrors scripts/smoke-api.sh."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from src.config import FIXTURES_DIR
from src.main import app

client = TestClient(app)

DISCHARGE_TEXT = (FIXTURES_DIR / "discharge-messy.txt").read_text(encoding="utf-8")
SAMPLE_PACKET = json.loads((FIXTURES_DIR / "sample-care-packet.json").read_text(encoding="utf-8"))


def reset() -> None:
    assert client.post("/demo/reset").json() == {"ok": True}


def extract_plan() -> dict:
    reset()
    response = client.post("/plans/extract", json={"text": DISCHARGE_TEXT, "source": "paste"})
    assert response.status_code == 200
    return response.json()


def active_plan_id() -> str:
    plan = extract_plan()
    client.post(f"/plans/{plan['plan_id']}/activate").raise_for_status()
    return plan["plan_id"]


def test_health():
    assert client.get("/health").json() == {"ok": True}


def test_people_seeded():
    reset()
    people = client.get("/people").json()
    assert people["patient"]["id"] == "p_lakshmi"
    assert people["patient"]["languages"] == ["hi-IN"]
    assert people["caregiver"]["id"] == "c_ananya"


def test_extract_returns_draft_meds_from_formulary():
    plan = extract_plan()
    assert plan["status"] == "draft"
    ids = [m["id"] for m in plan["medications"]]
    assert ids == ["med_amlodipine", "med_metformin", "med_atorvastatin", "med_paracetamol"]

    amlodipine = plan["medications"][0]
    assert amlodipine["times"] == ["21:00"]
    assert amlodipine["criticality"] == "high"

    metformin = plan["medications"][1]
    assert metformin["times"] == ["08:00", "21:00"]
    assert metformin["food_rule"] == "with_food"


def test_patch_then_activate():
    plan = extract_plan()
    plan_id = plan["plan_id"]

    edited = plan["medications"][:2]
    edited[0]["dose"] = 2.5
    patched = client.patch(f"/plans/{plan_id}", json={"medications": edited}).json()
    assert len(patched["medications"]) == 2
    assert patched["medications"][0]["dose"] == 2.5

    activated = client.post(f"/plans/{plan_id}/activate").json()
    assert activated["status"] == "active"
    assert activated["event_id"].startswith("evt_")

    assert client.get(f"/plans/{plan_id}").json()["status"] == "active"


def test_trigger_requires_active_plan():
    plan = extract_plan()
    response = client.post(
        "/doses/trigger", json={"plan_id": plan["plan_id"], "simulate_time": "evening"}
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "PLAN_NOT_ACTIVE"


def test_trigger_defaults_to_night_high_criticality_med():
    plan_id = active_plan_id()
    dose = client.post(
        "/doses/trigger", json={"plan_id": plan_id, "simulate_time": "evening"}
    ).json()
    assert dose["status"] == "calling"
    assert dose["medication"]["id"] == "med_amlodipine"
    assert dose["event_id"].startswith("evt_")


def test_complete_side_effect_creates_packet_matching_fixture_shape():
    plan_id = active_plan_id()
    dose = client.post(
        "/doses/trigger",
        json={"plan_id": plan_id, "medication_id": "med_amlodipine", "simulate_time": "evening"},
    ).json()

    result = client.post(
        f"/doses/{dose['dose_id']}/complete",
        json={
            "adherence": "taken",
            "exception_type": "side_effect",
            "patient_reported": "pet mein jalan",
            "normalized_symptom": "abdominal_burning",
            "transcript_summary": "Patient confirmed Amlodipine taken; reported burning in stomach.",
            "confidence": 0.86,
        },
    ).json()

    assert result["status"] == "completed"
    assert result["policy"] == {
        "allowed": True,
        "actions": ["log", "escalate_caregiver"],
        "refused": [],
    }
    assert result["packet_id"].startswith("pkt_")
    assert len(result["event_ids"]) == 3  # dose_completed, exception_logged, packet_sent

    packet = client.get("/packets/latest", params={"plan_id": plan_id}).json()
    assert set(packet) == set(SAMPLE_PACKET)
    assert packet["patient_name"] == "Lakshmi"
    assert packet["medication"] == "Amlodipine 5mg"
    assert packet["status"] == "taken"
    assert packet["exception"] == SAMPLE_PACKET["exception"]
    assert packet["system_action"] == "logged_and_escalated"
    assert packet["suggested_caregiver_actions"] == SAMPLE_PACKET["suggested_caregiver_actions"]
    assert packet["confidence"] == 0.86
    assert packet["needs_clinician"] is False
    assert packet["language"] == "en-IN"


def test_ledger_has_full_trail():
    plan_id = active_plan_id()
    dose = client.post(
        "/doses/trigger", json={"plan_id": plan_id, "simulate_time": "evening"}
    ).json()
    client.post(
        f"/doses/{dose['dose_id']}/complete",
        json={
            "adherence": "taken",
            "exception_type": "side_effect",
            "patient_reported": "pet mein jalan",
            "normalized_symptom": "abdominal_burning",
            "confidence": 0.86,
        },
    ).raise_for_status()

    events = client.get("/events", params={"plan_id": plan_id}).json()["events"]
    assert [e["type"] for e in events] == [
        "plan_created",
        "plan_activated",
        "dose_triggered",
        "dose_completed",
        "exception_logged",
        "packet_sent",
    ]
    assert all(e["id"].startswith("evt_") for e in events)
    assert events[0]["ts"].endswith("+05:30")


def test_taken_with_no_exception_logs_only():
    plan_id = active_plan_id()
    dose = client.post(
        "/doses/trigger", json={"plan_id": plan_id, "simulate_time": "evening"}
    ).json()
    result = client.post(
        f"/doses/{dose['dose_id']}/complete",
        json={"adherence": "taken", "exception_type": "none", "confidence": 0.9},
    ).json()

    assert result["policy"]["actions"] == ["log"]
    assert result["packet_id"] is None
    assert client.get("/packets/latest", params={"plan_id": plan_id}).status_code == 404


def test_double_complete_is_refused():
    plan_id = active_plan_id()
    dose = client.post(
        "/doses/trigger", json={"plan_id": plan_id, "simulate_time": "evening"}
    ).json()
    body = {"adherence": "taken", "exception_type": "none", "confidence": 0.9}
    client.post(f"/doses/{dose['dose_id']}/complete", json=body).raise_for_status()

    second = client.post(f"/doses/{dose['dose_id']}/complete", json=body)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "DOSE_ALREADY_COMPLETED"


def test_voice_turn_guesses_without_writing_outcome():
    plan_id = active_plan_id()
    dose = client.post(
        "/doses/trigger", json={"plan_id": plan_id, "simulate_time": "evening"}
    ).json()

    turn = client.post(
        f"/doses/{dose['dose_id']}/voice-turn",
        json={"user_text": "haan le liya, lekin pet mein jalan hai"},
    ).json()
    assert turn["partial"] == {"adherence_guess": "taken", "exception_guess": "side_effect"}
    assert turn["audio_url"] is None
    assert turn["assistant_text"]

    types = [e["type"] for e in client.get("/events", params={"plan_id": plan_id}).json()["events"]]
    assert "dose_started" in types
    assert "dose_completed" not in types


def test_demo_reset_clears_world():
    plan_id = active_plan_id()
    reset()
    assert client.get(f"/plans/{plan_id}").status_code == 404
    assert client.get("/events").json()["events"] == []
    assert client.get("/people").json()["patient"]["id"] == "p_lakshmi"


def test_unknown_plan_is_404_with_error_shape():
    body = client.get("/plans/plan_nope").json()
    assert body["error"]["code"] == "PLAN_NOT_FOUND"
