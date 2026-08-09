from __future__ import annotations

from fastapi import APIRouter

from .. import db
from ..errors import ApiError, Conflict
from ..models.schemas import (
    CompleteRequest,
    CompleteResponse,
    Medication,
    TriggerRequest,
    TriggerResponse,
    VoiceTurnRequest,
    VoiceTurnResponse,
)
from ..policy.kernel import evaluate_completion
from ..services import ledger, packets, plans
from ..services.seed import get_people

router = APIRouter(tags=["doses"])


@router.post("/doses/trigger", response_model=TriggerResponse)
def trigger(body: TriggerRequest) -> dict:
    plan = plans.get_plan(body.plan_id)
    if plan.status != "active":
        raise ApiError("PLAN_NOT_ACTIVE", "Activate plan before triggering dose")

    medication = (
        plans.get_medication(plan, body.medication_id)
        if body.medication_id
        else plans.pick_medication(plan, body.simulate_time)
    )

    dose = plans.create_dose(plan, medication, body.simulate_time)
    event = ledger.append(
        "dose_triggered",
        plan_id=plan.id,
        dose_id=dose["id"],
        payload={
            "medication_id": medication.id,
            "medication_name": medication.name_raw,
            "simulate_time": body.simulate_time,
            "times": medication.times,
        },
    )
    return {
        "dose_id": dose["id"],
        "status": dose["status"],
        "medication": medication,
        "event_id": event.id,
    }


@router.post("/doses/{dose_id}/voice-turn", response_model=VoiceTurnResponse)
def voice_turn(dose_id: str, body: VoiceTurnRequest) -> dict:
    """Optional server-side dialogue turn. Guesses only — nothing is written
    to the ledger as an outcome here. Only /complete is the source of truth."""
    from ..voice.turn import handle_turn  # Jyotir owns src/voice/**

    dose = plans.get_dose(dose_id)
    if dose["status"] == "completed":
        raise Conflict("DOSE_ALREADY_COMPLETED", f"Dose {dose_id} is already completed")

    if not dose.get("started_at"):
        dose["started_at"] = db.now_iso()
        plans.save_dose(dose)
        ledger.append("dose_started", plan_id=dose["plan_id"], dose_id=dose_id, payload={})

    return handle_turn(dose, body.user_text)


@router.post("/doses/{dose_id}/complete", response_model=CompleteResponse)
def complete(dose_id: str, body: CompleteRequest) -> dict:
    """The only write path for final adherence, exception and caregiver packet."""
    dose = plans.get_dose(dose_id)
    plan = plans.get_plan(dose["plan_id"])
    if plan.status != "active":
        raise ApiError("PLAN_NOT_ACTIVE", "Activate plan before completing dose")

    # Claim last: everything above can reject the call, and a rejected call must
    # not leave the dose marked completed.
    dose = plans.claim_dose_for_completion(dose_id)

    medication = Medication(**dose["medication"])
    decision = evaluate_completion(
        adherence=body.adherence,
        exception_type=body.exception_type,
        criticality=medication.criticality,
        confidence=body.confidence,
    )

    dose["completed_at"] = db.now_iso()
    dose["outcome"] = body.model_dump()
    dose["policy"] = decision.as_policy_result()
    plans.save_dose(dose)

    event_ids: list[str] = []
    event_ids.append(
        ledger.append(
            "dose_completed",
            plan_id=plan.id,
            dose_id=dose_id,
            payload={
                "medication_id": medication.id,
                "adherence": body.adherence,
                "exception_type": body.exception_type,
                "transcript_summary": body.transcript_summary,
                "confidence": body.confidence,
                "policy": decision.as_policy_result(),
            },
        ).id
    )

    if body.exception_type != "none":
        event_ids.append(
            ledger.append(
                "exception_logged",
                plan_id=plan.id,
                dose_id=dose_id,
                payload={
                    "exception_type": body.exception_type,
                    "patient_reported": body.patient_reported,
                    "normalized_symptom": body.normalized_symptom,
                    "confidence": body.confidence,
                },
            ).id
        )

    for refused in decision.refused:
        event_ids.append(
            ledger.append(
                "policy_refused",
                plan_id=plan.id,
                dose_id=dose_id,
                payload={"intent": refused, "reason": decision.reason},
            ).id
        )

    packet_id = None
    if decision.must_escalate:
        people = get_people()
        packet = packets.build_packet(
            patient_name=people["patient"]["display_name"],
            medication=medication,
            adherence=body.adherence,
            exception_type=body.exception_type,
            patient_reported=body.patient_reported,
            normalized_symptom=body.normalized_symptom,
            decision=decision,
            confidence=body.confidence,
            event_time=dose["completed_at"],
        )
        packets.save_packet(packet, plan_id=plan.id, dose_id=dose_id)
        packet_id = packet.id
        event_ids.append(
            ledger.append(
                "packet_sent",
                plan_id=plan.id,
                dose_id=dose_id,
                payload={
                    "packet_id": packet.id,
                    "caregiver_id": plan.caregiver_id,
                    "system_action": packet.system_action,
                    "needs_clinician": packet.needs_clinician,
                },
            ).id
        )

    return {
        "dose_id": dose_id,
        "status": dose["status"],
        "policy": decision.as_policy_result(),
        "packet_id": packet_id,
        "event_ids": event_ids,
    }
