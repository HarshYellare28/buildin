from __future__ import annotations

from fastapi import APIRouter

from ..models.schemas import PeopleResponse
from ..services.seed import ensure_seeded

router = APIRouter(tags=["people"])


@router.get("/people", response_model=PeopleResponse)
def get_people() -> dict:
    people = ensure_seeded()
    return {"patient": people["patient"], "caregiver": people["caregiver"]}
