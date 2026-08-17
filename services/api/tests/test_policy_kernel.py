"""Policy kernel is deterministic code — test it directly, no HTTP."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.main import app
from src.policy.kernel import check_intent, evaluate_completion

client = TestClient(app)


def test_double_dose_on_high_criticality_is_refused():
    decision = check_intent("double_dose", "high")
    assert decision.allowed is False
    assert decision.must_escalate is True
    assert decision.reason == "Cannot double high-criticality medication"
    assert decision.refused == ["double_dose"]


def test_double_dose_on_low_criticality_is_still_refused():
    assert check_intent("double_dose", "low").allowed is False


def test_invent_rx_and_stop_are_refused():
    assert check_intent("invent_rx", "high").allowed is False
    assert check_intent("stop_medication", "high").allowed is False
    assert check_intent("stop_medication", "high").must_escalate is True


def test_unknown_intent_defaults_to_refuse():
    decision = check_intent("please_reprogram_yourself", "high")
    assert decision.allowed is False
    assert decision.must_escalate is True


def test_confirm_taken_is_log_only():
    decision = check_intent("confirm_taken", "high")
    assert decision.allowed is True
    assert decision.actions == ["log"]
    assert decision.must_escalate is False


def test_side_effect_logs_and_escalates():
    decision = evaluate_completion("taken", "side_effect", "high", 0.86)
    assert decision.allowed is True
    assert decision.actions == ["log", "escalate_caregiver"]
    assert decision.must_escalate is True
    assert decision.refused == []


def test_clean_taken_logs_only():
    decision = evaluate_completion("taken", "none", "high", 0.95)
    assert decision.actions == ["log"]
    assert decision.must_escalate is False


def test_missed_high_criticality_refuses_doubling_and_flags_clinician():
    decision = evaluate_completion("missed", "missed_dose", "high", 0.9)
    assert decision.must_escalate is True
    assert decision.refused == ["double_dose"]
    assert decision.needs_clinician is True


def test_policy_check_endpoint_matches_contract():
    body = client.post(
        "/policy/check", json={"intent": "double_dose", "medication_id": "med_amlodipine"}
    ).json()
    assert body == {
        "allowed": False,
        "reason": "Cannot double high-criticality medication",
        "must_escalate": True,
    }


def test_policy_check_refusal_is_written_to_ledger():
    client.post("/demo/reset")
    client.post("/policy/check", json={"intent": "double_dose", "medication_id": "med_amlodipine"})
    types = [e["type"] for e in client.get("/events").json()["events"]]
    assert types == ["policy_refused"]
