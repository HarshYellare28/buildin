from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..models import Plan
from ..services.extract import ExtractError, extract_from_photo, extract_from_text
from ..store import store

router = APIRouter()

# Sarvam Doc AI only accepts PDF/JPEG/PNG.
SUPPORTED_CONTENT_TYPES = {"image/jpeg", "image/png", "application/pdf"}


def _error(code: str, message: str, status: int) -> HTTPException:
    return HTTPException(status_code=status, detail={"error": {"code": code, "message": message}})


@router.post("/plans/extract")
async def extract_plan(
    source: str = Form(...),
    text: str | None = Form(None),
    file: UploadFile | None = File(None),
):
    if source not in ("paste", "ocr"):
        raise _error("BAD_SOURCE", "source must be 'paste' or 'ocr'", 400)

    if source == "paste":
        if not text or not text.strip():
            raise _error("MISSING_TEXT", "text is required for source=paste", 400)
        medications = extract_from_text(text)
    else:
        if not file:
            raise _error("MISSING_FILE", "file is required for source=ocr", 400)
        if file.content_type not in SUPPORTED_CONTENT_TYPES:
            raise _error(
                "UNSUPPORTED_FILE_TYPE",
                f"'{file.content_type}' is not supported — send a JPEG, PNG, or PDF.",
                400,
            )
        content = await file.read()
        try:
            medications = await extract_from_photo(content, file.filename or "upload", file.content_type or "")
        except ExtractError as e:
            raise _error(e.code, e.message, 502) from e

    plan_id = store.next_plan_id()
    plan = Plan(
        id=plan_id,
        status="draft",
        patient_id=store.people["patient"]["id"],
        caregiver_id=store.people["caregiver"]["id"],
        medications=medications,
    )
    store.plans[plan_id] = plan
    store.events.append(
        {
            "id": store.next_event_id(),
            "type": "plan_created",
            "plan_id": plan_id,
            "payload": {"source": source, "count": len(medications)},
        }
    )
    return {"plan_id": plan_id, "status": plan.status, "medications": medications}


@router.get("/plans/{plan_id}")
def get_plan(plan_id: str):
    plan = store.plans.get(plan_id)
    if not plan:
        raise _error("PLAN_NOT_FOUND", f"No plan {plan_id}", 404)
    return plan


@router.patch("/plans/{plan_id}")
def patch_plan(plan_id: str, body: dict):
    plan = store.plans.get(plan_id)
    if not plan:
        raise _error("PLAN_NOT_FOUND", f"No plan {plan_id}", 404)
    medications = body.get("medications")
    if medications is not None:
        plan.medications = medications
    return plan


@router.post("/plans/{plan_id}/activate")
def activate_plan(plan_id: str):
    plan = store.plans.get(plan_id)
    if not plan:
        raise _error("PLAN_NOT_FOUND", f"No plan {plan_id}", 404)
    plan.status = "active"
    event_id = store.next_event_id()
    store.events.append({"id": event_id, "type": "plan_activated", "plan_id": plan_id, "payload": {}})
    return {"plan_id": plan_id, "status": plan.status, "event_id": event_id}
