from __future__ import annotations

from fastapi import APIRouter

from ..errors import ApiError
from ..models.schemas import MealCheck, MealCheckRequest
from ..services import ledger, meal_checks, plans

router = APIRouter(tags=["meal-checks"])


def record_meal_check(
    plan_id: str,
    meal_text: str,
    source: str,
    dose_id: str | None = None,
) -> MealCheck:
    plan = plans.get_plan(plan_id)
    if plan.status != "active":
        raise ApiError("PLAN_NOT_ACTIVE", "Activate and confirm the plan before scoring a meal")
    if dose_id:
        existing = meal_checks.for_dose(dose_id)
        if existing:
            return existing
    check = meal_checks.save(meal_checks.evaluate(plan, meal_text, source, dose_id=dose_id))
    ledger.append(
        "meal_checked",
        plan_id=plan.id,
        dose_id=dose_id,
        payload={
            "meal_check_id": check.id,
            "score": check.score,
            "band": check.band,
            "source": check.source,
            "with_food_matched": any(
                item.timing_status == "matched" for item in check.medication_checks
            ),
        },
    )
    return check


@router.post("/plans/{plan_id}/meal-checks", response_model=MealCheck)
def create_meal_check(plan_id: str, body: MealCheckRequest) -> MealCheck:
    return record_meal_check(plan_id, body.meal_text, body.source)


@router.get("/plans/{plan_id}/meal-checks/latest", response_model=MealCheck | None)
def get_latest_meal_check(plan_id: str) -> MealCheck | None:
    plans.get_plan(plan_id)
    return meal_checks.latest(plan_id)
