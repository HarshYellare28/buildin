from __future__ import annotations

from fastapi import APIRouter, Request, UploadFile
from pydantic import ValidationError

from ..errors import ApiError
from ..models.schemas import (
    ActivateResponse,
    ExtractRequest,
    ExtractResponse,
    Plan,
    PlanPatch,
)
from ..services import ledger, plans
from ..services.document_extract import extract_document
from ..services.extract import extract_medications
from ..services.followup import extract_follow_up

router = APIRouter(tags=["plans"])


@router.post("/plans/extract", response_model=ExtractResponse)
async def extract(request: Request) -> dict:
    """Accept contract JSON for paste and multipart for the optional photo path."""
    content_type = request.headers.get("content-type", "")
    text = ""
    source = "paste"
    if content_type.startswith(("multipart/form-data", "application/x-www-form-urlencoded")):
        form = await request.form()
        source = str(form.get("source") or "")
        if source == "ocr":
            upload = form.get("file")
            if not isinstance(upload, UploadFile):
                raise ApiError("MISSING_FILE", "file is required for source=ocr")
            if upload.content_type not in {"image/jpeg", "image/png", "application/pdf"}:
                raise ApiError("UNSUPPORTED_FILE_TYPE", "Send a JPEG, PNG, or PDF")
            medications = await extract_document(
                await upload.read(),
                upload.filename or "prescription",
                upload.content_type,
            )
        elif source == "paste":
            text = str(form.get("text") or "")
            medications = extract_medications(text, source=source)
        else:
            raise ApiError("BAD_SOURCE", "source must be 'paste' or 'ocr'")
    else:
        try:
            body = ExtractRequest.model_validate(await request.json())
        except (ValidationError, ValueError) as exc:
            raise ApiError("INVALID_REQUEST", "text and source are required", status_code=422) from exc
        source = body.source
        text = body.text
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
