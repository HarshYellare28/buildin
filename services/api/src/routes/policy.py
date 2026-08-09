from __future__ import annotations

from fastapi import APIRouter

from ..models.schemas import PolicyCheckRequest, PolicyCheckResponse
from ..policy.kernel import check_intent
from ..services import ledger, plans
from ..services.fixtures import formulary_by_id

router = APIRouter(tags=["policy"])


@router.post("/policy/check", response_model=PolicyCheckResponse)
def check(body: PolicyCheckRequest) -> dict:
    criticality = "med"
    if body.medication_id:
        med = formulary_by_id().get(body.medication_id)
        if med:
            criticality = med["criticality"]

    decision = check_intent(body.intent, criticality)
    if not decision.allowed:
        # File the refusal against the active plan so it lands in the ledger the
        # cockpit renders (GET /events?plan_id=...), not just the global feed.
        ledger.append(
            "policy_refused",
            plan_id=body.plan_id or plans.active_plan_id(),
            payload={
                "intent": body.intent,
                "medication_id": body.medication_id,
                "reason": decision.reason,
            },
        )
    return {
        "allowed": decision.allowed,
        "reason": decision.reason,
        "must_escalate": decision.must_escalate,
    }
