"""Guards added after the contract review: formulary lock + ledger linkage."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.config import FIXTURES_DIR
from src.main import app

client = TestClient(app)

DISCHARGE_TEXT = (FIXTURES_DIR / "discharge-messy.txt").read_text(encoding="utf-8")

FAKE_MED = {
    "id": "med_madeup",
    "name_raw": "Fentanyl 100mcg",
    "name_normalized": "fentanyl",
    "dose": 100,
    "unit": "mcg",
    "times": ["21:00"],
    "criticality": "high",
}


def draft_plan() -> dict:
    client.post("/demo/reset")
    return client.post("/plans/extract", json={"text": DISCHARGE_TEXT, "source": "paste"}).json()


def test_patch_cannot_inject_a_drug_outside_the_formulary():
    plan = draft_plan()
    response = client.patch(f"/plans/{plan['plan_id']}", json={"medications": [FAKE_MED]})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "MEDICATION_NOT_IN_FORMULARY"

    # The plan is untouched — no half-applied edit.
    stored = client.get(f"/plans/{plan['plan_id']}").json()
    assert [m["id"] for m in stored["medications"]] == [m["id"] for m in plan["medications"]]


def test_patch_still_allows_editing_a_real_med():
    plan = draft_plan()
    edited = plan["medications"][:1]
    edited[0]["dose"] = 2.5
    edited[0]["times"] = ["22:00"]

    patched = client.patch(f"/plans/{plan['plan_id']}", json={"medications": edited}).json()
    assert patched["medications"][0]["dose"] == 2.5
    assert patched["medications"][0]["times"] == ["22:00"]


def test_policy_refusal_lands_in_the_plan_filtered_ledger():
    plan = draft_plan()
    plan_id = plan["plan_id"]
    client.post(f"/plans/{plan_id}/activate").raise_for_status()

    refusal = client.post(
        "/policy/check", json={"intent": "double_dose", "medication_id": "med_amlodipine"}
    ).json()
    assert refusal["allowed"] is False

    # The cockpit ledger panel calls this — the refusal must be visible here.
    events = client.get("/events", params={"plan_id": plan_id}).json()["events"]
    refused = [e for e in events if e["type"] == "policy_refused"]
    assert len(refused) == 1
    assert refused[0]["plan_id"] == plan_id
    assert refused[0]["payload"]["intent"] == "double_dose"


def test_policy_check_accepts_an_explicit_plan_id():
    plan = draft_plan()
    plan_id = plan["plan_id"]  # deliberately left in draft — no active plan

    client.post(
        "/policy/check",
        json={"intent": "invent_rx", "plan_id": plan_id},
    ).raise_for_status()

    events = client.get("/events", params={"plan_id": plan_id}).json()["events"]
    assert [e["type"] for e in events if e["type"] == "policy_refused"] == ["policy_refused"]


def test_policy_check_without_any_plan_still_works():
    client.post("/demo/reset")
    body = client.post("/policy/check", json={"intent": "double_dose"}).json()
    assert body["allowed"] is False
    assert body["must_escalate"] is True

    events = client.get("/events").json()["events"]
    assert events[-1]["type"] == "policy_refused"
    assert events[-1]["plan_id"] is None
