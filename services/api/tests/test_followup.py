"""Follow-up visit extraction: "7 din baad OPD review" -> a date to remind on."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient

from src.config import FIXTURES_DIR, IST
from src.main import app
from src.services.followup import extract_follow_up

client = TestClient(app)

DISCHARGE_TEXT = (FIXTURES_DIR / "discharge-messy.txt").read_text(encoding="utf-8")


# ------------------------------------------------------------------ unit level


def test_fixture_note_yields_seven_day_clinic_visit():
    follow_up = extract_follow_up(DISCHARGE_TEXT)
    assert follow_up is not None
    assert follow_up.kind == "clinic_visit"
    assert follow_up.in_days == 7
    assert follow_up.raw_text == "- 7 din baad OPD review"
    # Anchored to the note's own date (09/08/2026), not to the wall clock.
    assert follow_up.anchor_date == "2026-08-09"
    assert follow_up.due_date == "2026-08-16"
    assert follow_up.due_at == "2026-08-16T10:00:00+05:30"
    assert follow_up.confidence == 0.9


def test_romanised_hindi_numeral():
    follow_up = extract_follow_up("saat din baad opd aana\nDate: 01/03/2026")
    assert follow_up is not None
    assert follow_up.in_days == 7
    assert follow_up.due_date == "2026-03-08"
    assert follow_up.confidence == 0.75  # word numeral, less certain than a digit


def test_weeks_and_months_convert_to_days():
    assert extract_follow_up("review after 2 weeks\nDate: 01/01/2026").in_days == 14
    assert extract_follow_up("1 hafta baad OPD\nDate: 01/01/2026").in_days == 7
    assert extract_follow_up("follow up in 1 month\nDate: 01/01/2026").in_days == 30


def test_medicine_course_length_is_not_a_follow_up():
    """"Metformin 30 din" is a course, not a clinic visit."""
    assert extract_follow_up("Metformin 500mg — 30 din subah raat") is None


def test_note_without_a_visit_returns_none():
    assert extract_follow_up("Amlodipine 5mg raat ko. Rest and fluids.") is None
    assert extract_follow_up("") is None


def test_falls_back_to_today_when_note_has_no_date():
    follow_up = extract_follow_up("OPD review after 3 days")
    assert follow_up is not None
    expected = datetime.now(IST).date() + timedelta(days=3)
    assert follow_up.due_date == expected.isoformat()
    assert follow_up.anchor_date == datetime.now(IST).date().isoformat()


def test_absurd_duration_is_dropped():
    assert extract_follow_up("OPD review after 900 days") is None


# ------------------------------------------------------------------ API level


def test_extract_returns_follow_up_and_plan_persists_it():
    client.post("/demo/reset")
    extracted = client.post(
        "/plans/extract", json={"text": DISCHARGE_TEXT, "source": "paste"}
    ).json()

    assert extracted["follow_up"]["in_days"] == 7
    assert extracted["follow_up"]["due_date"] == "2026-08-16"

    plan = client.get(f"/plans/{extracted['plan_id']}").json()
    assert plan["follow_up"] == extracted["follow_up"]


def test_follow_up_reaches_the_ledger_for_a_future_reminder():
    client.post("/demo/reset")
    plan_id = client.post(
        "/plans/extract", json={"text": DISCHARGE_TEXT, "source": "paste"}
    ).json()["plan_id"]
    client.post(f"/plans/{plan_id}/activate").raise_for_status()

    events = {e["type"]: e for e in client.get("/events", params={"plan_id": plan_id}).json()["events"]}
    assert events["plan_created"]["payload"]["follow_up"]["due_date"] == "2026-08-16"
    assert events["plan_activated"]["payload"]["follow_up_due_at"] == "2026-08-16T10:00:00+05:30"


def test_patch_without_follow_up_key_keeps_it():
    client.post("/demo/reset")
    extracted = client.post(
        "/plans/extract", json={"text": DISCHARGE_TEXT, "source": "paste"}
    ).json()

    patched = client.patch(
        f"/plans/{extracted['plan_id']}", json={"medications": extracted["medications"]}
    ).json()
    assert patched["follow_up"] == extracted["follow_up"]


def test_caregiver_can_correct_the_follow_up_date():
    client.post("/demo/reset")
    extracted = client.post(
        "/plans/extract", json={"text": DISCHARGE_TEXT, "source": "paste"}
    ).json()

    corrected = dict(extracted["follow_up"])
    corrected["due_date"] = "2026-08-20"
    corrected["due_at"] = "2026-08-20T09:30:00+05:30"

    patched = client.patch(
        f"/plans/{extracted['plan_id']}",
        json={"medications": extracted["medications"], "follow_up": corrected},
    ).json()
    assert patched["follow_up"]["due_date"] == "2026-08-20"

    dropped = client.patch(
        f"/plans/{extracted['plan_id']}",
        json={"medications": extracted["medications"], "follow_up": None},
    ).json()
    assert dropped["follow_up"] is None


def test_note_with_no_visit_line_gives_a_plan_without_follow_up():
    client.post("/demo/reset")
    extracted = client.post(
        "/plans/extract", json={"text": "Amlodipine 5mg raat ko", "source": "paste"}
    ).json()
    assert extracted["follow_up"] is None
