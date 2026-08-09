from __future__ import annotations

from fastapi import APIRouter, Request

from ..errors import ApiError
from ..models.schemas import (
    ActivateResponse,
    ExtractRequest,
    ExtractResponse,
    Plan,
    PlanPatch,
)
from ..models.schemas import Medication
from ..services import ledger, plans
from ..services.extract import (
    SUPPORTED_DOCUMENT_TYPES,
    extract_from_document,
    extract_medications,
)
from ..services.followup import extract_follow_up
from ..services.sarvam import SarvamError

router = APIRouter(tags=["plans"])


@router.post("/plans/extract", response_model=ExtractResponse)
async def extract(request: Request) -> dict:
    """Discharge note -> draft plan.

    Two content types. The cockpit posts multipart/form-data because the photo
    path needs a file part; scripts and tests post JSON.

    A pasted note is text, so it yields both medications and a follow-up visit.
    A photographed note goes to Doc AI, whose output is a medication list and
    nothing else — so there is no note text to read a follow-up off, and
    `follow_up` comes back null for that path.
    """
    source, text, medications = await _read_request(request)

    if medications is None:
        medications = extract_medications(text, source=source)
    follow_up = extract_follow_up(text, source=source) if text else None

    plan = plans.create_plan(medications, follow_up=follow_up)
    ledger.append(
        "plan_created",
        plan_id=plan.id,
        payload={
            "source": source,
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


async def _read_request(request: Request) -> tuple[str, str, list[Medication] | None]:
    """Normalise either body shape down to (source, text, medications).

    `medications` is None for the text paths, meaning "still to be extracted".
    The OCR path returns them already built, because Doc AI's output is the
    medication list itself rather than a note to parse.
    """
    content_type = (request.headers.get("content-type") or "").split(";")[0].strip()

    if content_type == "application/json":
        try:
            body = ExtractRequest(**(await request.json()))
        except ApiError:
            raise
        except Exception as exc:
            raise ApiError("INVALID_REQUEST", f"Malformed JSON body: {exc}") from exc
        if not body.text.strip():
            raise ApiError("MISSING_TEXT", "text is required")
        return body.source, body.text, None

    if content_type not in ("multipart/form-data", "application/x-www-form-urlencoded"):
        raise ApiError(
            "UNSUPPORTED_CONTENT_TYPE",
            "Send application/json or multipart/form-data",
            status_code=415,
        )

    form = await request.form()
    source = str(form.get("source") or "paste").strip().lower()
    if source not in ("paste", "ocr"):
        raise ApiError("BAD_SOURCE", "source must be 'paste' or 'ocr'")

    if source == "paste":
        text = str(form.get("text") or "")
        if not text.strip():
            raise ApiError("MISSING_TEXT", "text is required for source=paste")
        return source, text, None

    upload = form.get("file")
    if upload is None or not hasattr(upload, "read"):
        raise ApiError("MISSING_FILE", "file is required for source=ocr")

    if upload.content_type not in SUPPORTED_DOCUMENT_TYPES:
        raise ApiError(
            "UNSUPPORTED_FILE_TYPE",
            f"'{upload.content_type}' is not supported — send a JPEG, PNG, or PDF.",
        )

    content = await upload.read()
    try:
        medications = extract_from_document(
            content, upload.filename or "upload", upload.content_type or ""
        )
    except SarvamError as exc:
        # 502: the request was fine, the upstream OCR was not.
        raise ApiError("OCR_FAILED", f"Sarvam Doc AI could not read the page: {exc}", 502) from exc

    if not medications:
        raise ApiError(
            "OCR_EMPTY",
            "Sarvam Doc AI found no known medications on that page — try a clearer photo.",
            422,
        )
    return source, "", medications


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
