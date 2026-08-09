from __future__ import annotations

from fastapi import APIRouter

from ..errors import NotFound
from ..models.schemas import CarePacket
from ..services import packets

router = APIRouter(tags=["packets"])


@router.get("/packets/latest", response_model=CarePacket)
def latest(plan_id: str | None = None) -> CarePacket:
    packet = packets.latest_packet(plan_id)
    if packet is None:
        raise NotFound("PACKET_NOT_FOUND", "No caregiver packet yet for this plan")
    return packet
