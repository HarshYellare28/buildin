from __future__ import annotations

from fastapi import APIRouter

from ..models.schemas import (
    ActivateResponse,
    ExtractRequest,
    ExtractResponse,
    Plan,
    PlanPatch,
)
from ..services import ledger, plans
from ..services.extract import extract_medications
from ..services.followup import extract_follow_up

router = APIRouter(tags=["plans"])


@router.post("/plans/extract", response_model=ExtractResponse)
def extract(body: ExtractRequest) -> dict:
    medications = extract_medications(body.text, source=body.source)
    follow_up = extract_follow_up(body.text, source=body.source)
    plan = plans.create_plan(medications, follow_up=follow_up)
    ledger.append(
        "plan_created",
        plan_id=plan.id,
        payload={
            "source": body.source,
            "medication_count": len(medications),
            "medication_ids": [m.id for m in medications],
            "follow_up": follow_up.model_dump() if follow_up else None,
        },
    )
    return {
        "plan_id": plan.id,
        "status": plan.status,
        "medications": medications,
        "follow_up": follow_up,
    }


@router.get("/plans/{plan_id}", response_model=Plan)
def get_plan(plan_id: str) -> Plan:
    return plans.get_plan(plan_id)


@router.patch("/plans/{plan_id}", response_model=Plan)
def patch_plan(plan_id: str, body: PlanPatch) -> Plan:
    return plans.patch_medications(
        plan_id,
        body.medications,
        follow_up=body.follow_up,
        set_follow_up="follow_up" in body.model_fields_set,
    )


@router.post("/plans/{plan_id}/activate", response_model=ActivateResponse)
def activate(plan_id: str) -> dict:
    plan = plans.activate_plan(plan_id)
    event = ledger.append(
        "plan_activated",
        plan_id=plan.id,
        payload={
            "medication_ids": [m.id for m in plan.medications],
            "confirmed_by": "human",
            # Carried so a reminder scheduler can read the due date straight off
            # the ledger without re-reading the plan.
            "follow_up_due_at": plan.follow_up.due_at if plan.follow_up else None,
        },
    )
    return {"plan_id": plan.id, "status": plan.status, "event_id": event.id}
