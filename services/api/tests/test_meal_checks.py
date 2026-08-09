from __future__ import annotations

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def _active_plan() -> str:
    client.post("/demo/reset").raise_for_status()
    plan = client.post(
        "/plans/extract",
        json={
            "source": "paste",
            "text": (
                "Amlodipine 5 mg roj raat ko. "
                "Metformin 500 mg subah aur raat khane ke saath. "
                "Atorvastatin 10 mg raat ko."
            ),
        },
    ).json()
    client.post(f"/plans/{plan['plan_id']}/activate").raise_for_status()
    return plan["plan_id"]


def test_balanced_meal_scores_strong_and_matches_with_food_rule():
    plan_id = _active_plan()
    response = client.post(
        f"/plans/{plan_id}/meal-checks",
        json={"meal_text": "Dal, chawal, sabzi and curd"},
    )

    assert response.status_code == 200
    meal = response.json()
    assert meal["score"] >= 75
    assert meal["band"] == "strong"
    assert meal["source"] == "caregiver"
    metformin = next(
        item for item in meal["medication_checks"] if item["medication_id"] == "med_metformin"
    )
    assert metformin["timing_status"] == "matched"
    assert "changing" in meal["disclaimer"]
    assert client.get(f"/plans/{plan_id}/meal-checks/latest").json()["id"] == meal["id"]


def test_no_meal_needs_attention_and_never_tells_patient_to_change_dose():
    plan_id = _active_plan()
    meal = client.post(
        f"/plans/{plan_id}/meal-checks",
        json={"meal_text": "Nothing"},
    ).json()

    assert meal["band"] == "needs_attention"
    assert meal["score"] < 50
    combined = " ".join(meal["suggestions"]).lower()
    assert "do not change or skip" in combined
    assert "double" not in combined


def test_grapefruit_with_atorvastatin_is_a_caution_not_a_dose_instruction():
    plan_id = _active_plan()
    meal = client.post(
        f"/plans/{plan_id}/meal-checks",
        json={"meal_text": "I ate roti, sabzi and grapefruit"},
    ).json()

    assert "grapefruit" in meal["suggestions"][0].lower()
    assert "pharmacist" in meal["suggestions"][0].lower()
    assert all("stop atorvastatin" not in suggestion.lower() for suggestion in meal["suggestions"])


def test_draft_plan_cannot_produce_medication_aware_score():
    client.post("/demo/reset").raise_for_status()
    plan = client.post(
        "/plans/extract",
        json={"source": "paste", "text": "Metformin 500 mg khane ke saath"},
    ).json()

    response = client.post(
        f"/plans/{plan['plan_id']}/meal-checks",
        json={"meal_text": "Dal and rice"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "PLAN_NOT_ACTIVE"
