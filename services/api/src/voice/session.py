"""Session state for one dose call.

In-memory only, by design: Barkha's API owns durable state. This module must never become a
second event store — it holds a conversation until it produces one complete payload, then stops.
"""

import uuid
from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict

from .classify import Classification


class Medication(BaseModel):
    """Subset of docs/API_CONTRACT.md Medication that the dialogue actually needs."""

    model_config = ConfigDict(extra="allow")

    id: str
    name_raw: str
    name_normalized: str | None = None
    dose: float | None = None
    unit: str | None = None
    schedule_text: str | None = None
    times: list[str] = []
    criticality: str = "med"


@dataclass
class Turn:
    role: str  # "agent" | "patient"
    text: str


@dataclass
class DoseVoiceSession:
    dose_id: str
    medication: Medication
    patient_name: str = "ji"
    caregiver_name: str = "aapke parivaar"
    session_id: str = field(default_factory=lambda: f"vs_{uuid.uuid4().hex[:10]}")
    state: str = "GREET_DOSE"
    turns: list[Turn] = field(default_factory=list)
    reask_count: int = 0
    outcome: Classification = field(default_factory=Classification)
    double_dose_refused: bool = False
    needs_human: bool = False
    complete_posted: bool = False
    complete_error: str | None = None

    @property
    def when_hi(self) -> str:
        """Time-of-day word for the greeting, taken from the med graph rather than assumed."""
        schedule = (self.medication.schedule_text or "").lower()
        evening = any(t >= "17:00" for t in self.medication.times)
        if evening or "night" in schedule or "raat" in schedule or "evening" in schedule:
            return "Raat"
        return "Subah"

    def say(self, text: str) -> None:
        self.turns.append(Turn(role="agent", text=text))

    def heard(self, text: str) -> None:
        self.turns.append(Turn(role="patient", text=text))

    def record(self, classification: Classification) -> None:
        """Merge a turn's classification. Adherence is set once — a later 'nahi' answering the
        symptom question must not retroactively flip a confirmed dose to missed."""
        if self.outcome.adherence == "unclear" and classification.adherence != "unclear":
            self.outcome.adherence = classification.adherence
            self.outcome.confidence = classification.confidence

        if classification.has_side_effect:
            self.outcome.exception_type = "side_effect"
            self.outcome.patient_reported = (
                classification.patient_reported or self.outcome.patient_reported
            )
            self.outcome.normalized_symptom = (
                classification.normalized_symptom or self.outcome.normalized_symptom
            )

        if classification.double_dose_request:
            self.double_dose_refused = True

        self.outcome.source = classification.source
        self.outcome.notes.extend(classification.notes)

    @property
    def must_escalate(self) -> bool:
        return (
            self.outcome.exception_type != "none"
            or self.double_dose_refused
            or self.outcome.adherence in ("missed", "partial")
        )

    @property
    def ready_for_complete(self) -> bool:
        return self.outcome.adherence in ("taken", "missed", "partial") and not self.needs_human

    def transcript_summary(self) -> str:
        """Deterministic English summary. Not model-written — it feeds a clinical-adjacent record."""
        med = self.medication.name_raw
        if self.outcome.adherence == "taken":
            base = f"Patient confirmed {med} taken"
        elif self.outcome.adherence == "missed":
            base = f"Patient reported {med} not taken"
        else:
            base = f"Patient reported partial dose of {med}"

        if self.outcome.exception_type == "side_effect":
            symptom = self.outcome.normalized_symptom or "unspecified symptom"
            base += f"; reported {symptom.replace('_', ' ')}"
            if self.outcome.patient_reported:
                base += f' ("{self.outcome.patient_reported}")'
        if self.double_dose_refused:
            base += "; asked about an extra dose and was refused"
        return base + "."

    def complete_payload(self) -> dict:
        """Exactly the body docs/API_CONTRACT.md defines for POST /doses/{dose_id}/complete."""
        exception_type = self.outcome.exception_type
        if exception_type == "none" and self.outcome.adherence == "missed":
            exception_type = "missed_dose"
        return {
            "adherence": self.outcome.adherence,
            "exception_type": exception_type,
            "patient_reported": self.outcome.patient_reported,
            "normalized_symptom": self.outcome.normalized_symptom,
            "transcript_summary": self.transcript_summary(),
            "confidence": round(self.outcome.confidence, 2),
        }


_SESSIONS: dict[str, DoseVoiceSession] = {}


def put(session: DoseVoiceSession) -> DoseVoiceSession:
    _SESSIONS[session.session_id] = session
    return session


def get(session_id: str) -> DoseVoiceSession | None:
    return _SESSIONS.get(session_id)


def clear() -> None:
    _SESSIONS.clear()
