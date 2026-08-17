"""Place Sarvam calls and ingest their completion webhook."""

from __future__ import annotations

import re
import secrets
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from ..config import SARVAM_WEBHOOK_TOKEN
from ..errors import ApiError, Conflict
from ..models.schemas import CompleteRequest
from ..policy.kernel import check_intent
from ..services import ledger, plans
from ..services.meal_checks import extract_meal_from_patient_text
from ..services.sarvam_outbound import place_call
from ..services.seed import get_people
from ..voice.classify import Classification, classify_regex

router = APIRouter(prefix="/sarvam", tags=["sarvam-outbound"])

_FAILED_STATUSES = {"failed", "busy", "no_answer", "not_connected", "cancelled", "canceled"}
_PATIENT_ROLES = {"user", "patient", "customer", "human", "callee"}


def _walk(value: Any):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _first_key(payload: dict, names: set[str]) -> Any:
    names = {name.lower() for name in names}
    for value in _walk(payload):
        if isinstance(value, dict):
            for key, child in value.items():
                if key.lower() in names and child not in (None, "", [], {}):
                    return child
    return None


def _metadata(payload: dict) -> dict:
    value = _first_key(payload, {"metadata"})
    return value if isinstance(value, dict) else {}


def _final_variables(payload: dict) -> dict:
    for name in ("final_agent_variables", "output_variables", "agent_variables"):
        value = _first_key(payload, {name})
        if isinstance(value, dict):
            return value
    return {}


def _line_text(item: dict) -> str:
    for key in ("text", "en_text", "content", "transcript", "utterance", "message"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _normalized_role(value: Any) -> str:
    role = str(value or "").strip().lower()
    if role in _PATIENT_ROLES:
        return "patient"
    if role in {"agent", "assistant", "bot", "ai"}:
        return "agent"
    return "unknown"


def _normalized_transcript(payload: dict) -> list[dict[str, str]]:
    transcript = _first_key(
        payload,
        {"interaction_transcript", "transcript", "conversation", "messages", "turns"},
    )
    lines: list[dict[str, str]] = []
    if isinstance(transcript, list):
        for item in transcript:
            if not isinstance(item, dict):
                continue
            text = _line_text(item)
            if text:
                lines.append(
                    {
                        "role": _normalized_role(
                            item.get("role") or item.get("speaker") or item.get("participant")
                        ),
                        "text": text,
                    }
                )
    elif isinstance(transcript, str):
        for line in transcript.splitlines():
            match = re.match(
                r"\s*(agent|assistant|bot|ai|patient|user|customer|human|callee)\s*:\s*(.+)",
                line,
                re.I,
            )
            if match:
                lines.append(
                    {"role": _normalized_role(match.group(1)), "text": match.group(2).strip()}
                )
        if not lines and transcript.strip():
            lines.append({"role": "unknown", "text": transcript.strip()})
    return lines


def _patient_text(payload: dict, variables: dict) -> str:
    transcript = _normalized_transcript(payload)
    parts = [line["text"] for line in transcript if line["role"] == "patient"]
    if not parts and transcript and all(line["role"] == "unknown" for line in transcript):
        parts = [line["text"] for line in transcript]

    if not parts:
        summary = next(
            (
                str(value)
                for key, value in variables.items()
                if key.lower() == "call_summary" and value
            ),
            "",
        )
        if summary:
            parts.append(summary)
    return "\n".join(parts).strip()


def _variable_value(variables: dict, names: set[str]) -> Any:
    names = {name.lower() for name in names}
    return next((value for key, value in variables.items() if key.lower() in names), None)


def _outcome(payload: dict) -> tuple[Classification, str]:
    variables = _final_variables(payload)
    patient_text = _patient_text(payload, variables)
    result = classify_regex(patient_text)

    raw_adherence = _variable_value(variables, {"dose_taken", "adherence", "dose_status"})
    normalized_adherence = str(raw_adherence).strip().lower() if raw_adherence is not None else ""
    if result.adherence == "unclear":
        if normalized_adherence in {"yes", "true", "taken", "took", "completed"}:
            result.adherence = "taken"
            result.confidence = max(result.confidence, 0.8)
        elif normalized_adherence in {"no", "false", "missed", "not_taken"}:
            result.adherence = "missed"
            result.confidence = max(result.confidence, 0.8)
        elif re.search(r"\b(taken|took|confirmed.{0,20}taken)\b", patient_text, re.I):
            result.adherence = "taken"
            result.confidence = max(result.confidence, 0.75)

    raw_exception = str(
        _variable_value(variables, {"exception", "exception_type", "side_effect"}) or ""
    ).lower()
    if result.exception_type == "none" and re.search(
        r"side.?effect|jalan|burning|acidity", raw_exception + " " + patient_text, re.I
    ):
        result.exception_type = "side_effect"
        result.normalized_symptom = "abdominal_burning"
    reported = _variable_value(variables, {"patient_reported", "symptom", "complaint"})
    if reported and not result.patient_reported:
        result.patient_reported = str(reported)
    return result, patient_text


@router.post("/outbound/{dose_id}")
def start_outbound(dose_id: str) -> dict:
    dose = plans.get_dose(dose_id)
    if dose["status"] != "calling":
        raise Conflict("DOSE_NOT_CALLING", f"Dose {dose_id} is not waiting for a call")
    if dose.get("sarvam_attempt_id"):
        raise Conflict("OUTBOUND_ALREADY_STARTED", f"Dose {dose_id} already has an outbound attempt")

    people = get_people()
    result = place_call(
        dose,
        patient_name=people["patient"]["display_name"],
        caregiver_name=people["caregiver"]["display_name"],
    )
    dose["sarvam_attempt_id"] = result["attempt_id"]
    plans.save_dose(dose)
    return {"dose_id": dose_id, "status": "calling", "attempt_id": result["attempt_id"]}


@router.get("/outbound/{dose_id}")
def outbound_status(dose_id: str) -> dict:
    dose = plans.get_dose(dose_id)
    return {
        "dose_id": dose_id,
        "status": dose["status"],
        "attempt_id": dose.get("sarvam_attempt_id"),
        "call_status": dose.get("sarvam_call_status"),
        "failure_reason": dose.get("sarvam_failure"),
        "interaction_id": dose.get("sarvam_interaction_id"),
        "duration_seconds": dose.get("sarvam_duration_seconds"),
        "transcript": dose.get("sarvam_transcript", []),
    }


@router.post("/webhook")
async def receive_webhook(request: Request, token: str = Query(default="")) -> dict:
    if not SARVAM_WEBHOOK_TOKEN or not secrets.compare_digest(token, SARVAM_WEBHOOK_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid webhook token")
    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Webhook body must be JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Webhook body must be an object")

    metadata = _metadata(payload)
    dose_id = str(metadata.get("dose_id") or "")
    plan_id = str(metadata.get("plan_id") or "")
    if not dose_id or not plan_id:
        raise HTTPException(status_code=400, detail="Webhook metadata needs dose_id and plan_id")
    dose = plans.get_dose(dose_id)
    if dose["plan_id"] != plan_id:
        raise HTTPException(status_code=400, detail="Webhook dose and plan do not match")

    attempt_id = str(_first_key(payload, {"attempt_id"}) or "")
    expected_attempt = str(dose.get("sarvam_attempt_id") or "")
    if expected_attempt and attempt_id and not secrets.compare_digest(attempt_id, expected_attempt):
        raise HTTPException(status_code=400, detail="Webhook attempt does not match dose")
    if dose["status"] == "completed":
        return {"ok": True, "duplicate": True, "dose_id": dose_id}

    status = str(_first_key(payload, {"status", "call_status"}) or "").lower()
    transcript = _normalized_transcript(payload)
    dose["sarvam_call_status"] = status or "received"
    dose["sarvam_interaction_id"] = _first_key(payload, {"interaction_id"})
    dose["sarvam_duration_seconds"] = _first_key(payload, {"duration", "duration_in_seconds"})
    dose["sarvam_transcript"] = transcript
    plans.save_dose(dose)
    if status in _FAILED_STATUSES:
        dose["status"] = "failed"
        dose["sarvam_failure"] = str(_first_key(payload, {"failure_reason", "reason"}) or status)
        plans.save_dose(dose)
        return {"ok": True, "processed": False, "status": "failed", "dose_id": dose_id}

    result, patient_text = _outcome(payload)
    meal_text = extract_meal_from_patient_text(patient_text)
    if meal_text:
        from .meal_checks import record_meal_check

        record_meal_check(
            plan_id,
            meal_text,
            source="voice_transcript",
            dose_id=dose_id,
        )
    if result.double_dose_request and not dose.get("double_dose_refusal_logged"):
        medication = dose["medication"]
        decision = check_intent("double_dose", medication.get("criticality"))
        ledger.append(
            "policy_refused",
            plan_id=plan_id,
            dose_id=dose_id,
            payload={"intent": "double_dose", "reason": decision.reason},
        )
        dose["double_dose_refusal_logged"] = True
        plans.save_dose(dose)

    if result.adherence not in {"taken", "missed", "partial"}:
        dose["sarvam_outcome_error"] = "No usable adherence outcome in webhook"
        plans.save_dose(dose)
        return {
            "ok": True,
            "processed": False,
            "status": "outcome_unusable",
            "dose_id": dose_id,
        }

    exception_type = result.exception_type
    if exception_type == "none" and result.adherence == "missed":
        exception_type = "missed_dose"
    summary = (
        f"Patient confirmed {dose['medication']['name_raw']} taken"
        if result.adherence == "taken"
        else f"Patient reported {dose['medication']['name_raw']} {result.adherence}"
    )
    if exception_type == "side_effect":
        summary += f"; reported {(result.normalized_symptom or 'side effect').replace('_', ' ')}"
    summary += "."

    from .doses import complete as complete_dose

    try:
        completion = complete_dose(
            dose_id,
            CompleteRequest(
                adherence=result.adherence,
                exception_type=exception_type,
                patient_reported=result.patient_reported or patient_text or None,
                normalized_symptom=result.normalized_symptom,
                transcript_summary=summary,
                confidence=max(0.5, result.confidence),
            ),
        )
    except Conflict:
        return {"ok": True, "duplicate": True, "dose_id": dose_id}
    return {
        "ok": True,
        "processed": True,
        "dose_id": dose_id,
        "attempt_id": attempt_id or expected_attempt or None,
        "packet_id": completion.get("packet_id"),
    }
