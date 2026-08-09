from __future__ import annotations

from fastapi import APIRouter

from ..models.schemas import EventsResponse
from ..services import ledger

router = APIRouter(tags=["events"])


@router.get("/events", response_model=EventsResponse)
def list_events(plan_id: str | None = None) -> dict:
    return {"events": ledger.list_events(plan_id)}
