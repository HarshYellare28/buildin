"""Caregiver packet generation.

Shape is locked to fixtures/sample-care-packet.json. Copy is deterministic:
symptom -> caregiver actions, plus whatever the policy kernel refused.
The UI renders this; it never composes the outcome itself.
"""

from __future__ import annotations

from .. import db
from ..config import DEMO_CAREGIVER_LANG
from ..models.schemas import CarePacket, Medication
from ..policy.kernel import PolicyDecision

# normalized_symptom -> caregiver-facing next steps (English, caregiver language)
SYMPTOM_ACTIONS: dict[str, list[str]] = {
    "abdominal_burning": [
        "Ask if burning is severe or with vomiting",
        "If severe, contact clinic on-call",
    ],
    "nausea": [
        "Ask if she has vomited or kept food down",
        "If vomiting repeats, contact clinic on-call",
    ],
    "dizziness": [
        "Ask if she felt faint while standing",
        "Keep her seated and contact clinic on-call if it repeats",
    ],
    "swelling": [
        "Check ankles and face for new swelling",
        "If swelling is increasing, contact clinic on-call",
    ],
}

GENERIC_ACTIONS = [
    "Ask her to describe the problem again in her own words",
    "If it worsens, contact clinic on-call",
]

MISSED_DOSE_ACTIONS = [
    "Confirm whether the dose was actually taken",
    "Check that the strip has tablets left",
]

# Symptoms that must not be handled by a caregiver call alone.
RED_FLAG_SYMPTOMS = {
    "chest_pain",
    "breathlessness",
    "vomiting_blood",
    "black_stool",
    "fainting",
    "severe_bleeding",
}

REFUSAL_LINES = {
    "double_dose": "Do not double next dose",
    "stop_medication": "Do not stop this medicine without the clinician",
    "invent_rx": "Do not start any new medicine at home",
    "skip_dose": "Do not skip the next dose without telling the clinician",
}


def build_packet(
    patient_name: str,
    medication: Medication,
    adherence: str,
    exception_type: str,
    patient_reported: str | None,
    normalized_symptom: str | None,
    decision: PolicyDecision,
    confidence: float,
    event_time: str | None = None,
) -> CarePacket:
    escalated = "escalate_caregiver" in decision.actions
    actions = _suggested_actions(exception_type, normalized_symptom, medication, decision)

    return CarePacket(
        id=db.next_id("pkt_", counter="pkt"),
        patient_name=patient_name,
        event_time=event_time or db.now_iso(),
        medication=medication.name_raw,
        status=adherence,  # type: ignore[arg-type]
        exception={
            "type": exception_type,
            "patient_reported": patient_reported,
            "normalized": normalized_symptom,
        },
        system_action="logged_and_escalated" if escalated else "logged",
        suggested_caregiver_actions=actions,
        confidence=confidence,
        needs_clinician=_needs_clinician(normalized_symptom, decision, confidence),
        language=DEMO_CAREGIVER_LANG,
    )


def _suggested_actions(
    exception_type: str,
    normalized_symptom: str | None,
    medication: Medication,
    decision: PolicyDecision,
) -> list[str]:
    if exception_type == "side_effect":
        actions = list(SYMPTOM_ACTIONS.get(normalized_symptom or "", GENERIC_ACTIONS))
    elif exception_type == "missed_dose":
        actions = list(MISSED_DOSE_ACTIONS)
    else:
        actions = list(GENERIC_ACTIONS)

    # High-criticality meds are never "caught up" by doubling.
    if medication.criticality == "high" and REFUSAL_LINES["double_dose"] not in actions:
        actions.append(REFUSAL_LINES["double_dose"])
    for refusal in decision.refused:
        line = REFUSAL_LINES.get(refusal)
        if line and line not in actions:
            actions.append(line)
    return actions


def _needs_clinician(
    normalized_symptom: str | None, decision: PolicyDecision, confidence: float
) -> bool:
    if normalized_symptom in RED_FLAG_SYMPTOMS:
        return True
    return bool(decision.needs_clinician) or confidence < 0.5


def save_packet(packet: CarePacket, plan_id: str, dose_id: str | None) -> CarePacket:
    db.execute(
        "INSERT INTO packets (id, plan_id, dose_id, created_at, data) VALUES (?, ?, ?, ?, ?)",
        (packet.id, plan_id, dose_id, db.now_iso(), db.dumps(packet.model_dump())),
    )
    return packet


def latest_packet(plan_id: str | None = None) -> CarePacket | None:
    if plan_id:
        row = db.query_one(
            "SELECT data FROM packets WHERE plan_id = ? ORDER BY rowid DESC LIMIT 1", (plan_id,)
        )
    else:
        row = db.query_one("SELECT data FROM packets ORDER BY rowid DESC LIMIT 1")
    return CarePacket(**db.loads(row["data"])) if row else None
