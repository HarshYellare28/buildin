"""Pydantic shapes. Field names are law — see docs/API_CONTRACT.md."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

PlanStatus = Literal["draft", "active"]
DoseStatus = Literal["scheduled", "calling", "completed", "failed"]
Adherence = Literal["taken", "missed", "partial"]
ExceptionType = Literal["none", "side_effect", "missed_dose", "confusion", "refused", "other"]
Criticality = Literal["low", "med", "high"]
EventType = Literal[
    "plan_created",
    "plan_activated",
    "dose_triggered",
    "dose_started",
    "dose_completed",
    "exception_logged",
    "packet_sent",
    "policy_refused",
]


class Medication(BaseModel):
    id: str
    name_raw: str
    name_normalized: str
    dose: float
    unit: str
    route: str = "oral"
    schedule_text: str = ""
    times: list[str] = Field(default_factory=list)
    food_rule: str = "none"
    duration_days: int = 0
    criticality: Criticality = "med"
    source: str = "paste"
    confidence: float = 0.8


class FollowUp(BaseModel):
    """A clinic visit read off the discharge note ("7 din baad OPD review").

    Not a medication and not a dose — it never triggers a call. `due_at` is the
    anchor a reminder can be scheduled on later.
    """

    kind: str = "clinic_visit"
    raw_text: str
    in_days: int
    due_date: str  # YYYY-MM-DD
    due_at: str  # ISO8601 +05:30
    anchor_date: str  # the note's date the countdown started from
    source: str = "paste"
    confidence: float = 0.8


class Plan(BaseModel):
    id: str
    status: PlanStatus
    patient_id: str
    caregiver_id: str
    medications: list[Medication] = Field(default_factory=list)
    follow_up: FollowUp | None = None


class Person(BaseModel):
    id: str
    display_name: str
    role: str
    languages: list[str]
    phone: str


class PeopleResponse(BaseModel):
    patient: Person
    caregiver: Person


class Event(BaseModel):
    id: str
    ts: str
    type: EventType
    plan_id: str | None = None
    dose_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class EventsResponse(BaseModel):
    events: list[Event]


class PacketException(BaseModel):
    type: ExceptionType
    patient_reported: str | None = None
    normalized: str | None = None


class CarePacket(BaseModel):
    id: str
    patient_name: str
    event_time: str
    medication: str
    status: Adherence
    exception: PacketException
    system_action: str
    suggested_caregiver_actions: list[str]
    confidence: float
    needs_clinician: bool
    language: str


# ---------- requests ----------


class ExtractRequest(BaseModel):
    text: str
    source: str = "paste"


class ExtractResponse(BaseModel):
    plan_id: str
    status: PlanStatus
    medications: list[Medication]
    follow_up: FollowUp | None = None


class PlanPatch(BaseModel):
    medications: list[Medication]
    # Optional: omit to leave the extracted follow-up alone, send null to drop it.
    follow_up: FollowUp | None = None


class ActivateResponse(BaseModel):
    plan_id: str
    status: PlanStatus
    event_id: str


class TriggerRequest(BaseModel):
    plan_id: str
    medication_id: str | None = None
    simulate_time: str = "evening"


class TriggerResponse(BaseModel):
    dose_id: str
    status: DoseStatus
    medication: Medication
    event_id: str


class VoiceTurnRequest(BaseModel):
    user_text: str


class VoiceTurnPartial(BaseModel):
    adherence_guess: Adherence | None = None
    exception_guess: ExceptionType | None = None


class VoiceTurnResponse(BaseModel):
    assistant_text: str
    audio_url: str | None = None
    partial: VoiceTurnPartial


class CompleteRequest(BaseModel):
    adherence: Adherence
    exception_type: ExceptionType = "none"
    patient_reported: str | None = None
    normalized_symptom: str | None = None
    transcript_summary: str | None = None
    confidence: float = 0.8


class PolicyResult(BaseModel):
    allowed: bool
    actions: list[str] = Field(default_factory=list)
    refused: list[str] = Field(default_factory=list)


class CompleteResponse(BaseModel):
    dose_id: str
    status: DoseStatus
    policy: PolicyResult
    packet_id: str | None = None
    event_ids: list[str]


class PolicyCheckRequest(BaseModel):
    intent: str
    medication_id: str | None = None
    # Optional. When omitted the refusal is filed against the active plan so it
    # shows up in GET /events?plan_id=...
    plan_id: str | None = None


class PolicyCheckResponse(BaseModel):
    allowed: bool
    reason: str
    must_escalate: bool
