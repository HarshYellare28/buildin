from __future__ import annotations

from fastapi import APIRouter

from .. import db
from ..services.seed import seed_people

router = APIRouter(tags=["demo"])


@router.post("/demo/reset")
def reset() -> dict:
    """Clear plans / doses / events / packets and reload the seeded people."""
    db.reset_world()
    seed_people()
    return {"ok": True}
