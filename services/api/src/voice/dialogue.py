r"""The dose-call state machine.

GREET_DOSE -> ASK_TAKEN -> WAIT_SYMPTOM -> CONFIRM_READBACK -> END
                  \__ one re-ask on unclear, then hand to a human __/

Every reply is a template from prompts.py. The machine chooses which one; it never writes words.
"""

from dataclasses import dataclass

from . import prompts
from .classify import classify
from .session import DoseVoiceSession


@dataclass
class Reply:
    text: str
    state: str
    is_final: bool = False


def _med_label(session: DoseVoiceSession) -> str:
    return session.medication.name_raw


def start(session: DoseVoiceSession) -> Reply:
    text = prompts.GREET_DOSE.format(
        patient=session.patient_name, when=session.when_hi, med=_med_label(session)
    )
    session.say(text)
    session.state = "ASK_TAKEN"
    return Reply(text=text, state=session.state)


def _readback(session: DoseVoiceSession) -> Reply:
    med = _med_label(session)
    if session.outcome.exception_type == "side_effect":
        text = prompts.READBACK_SIDE_EFFECT.format(
            med=med,
            reported=session.outcome.patient_reported or "takleef",
            caregiver=session.caregiver_name,
        )
    elif session.outcome.adherence == "taken":
        text = prompts.READBACK_TAKEN.format(med=med)
    else:
        text = prompts.READBACK_MISSED.format(med=med, caregiver=session.caregiver_name)

    session.say(text)
    session.state = "CONFIRM_READBACK"
    return Reply(text=text, state=session.state, is_final=True)


def advance(session: DoseVoiceSession, transcript: str) -> Reply:
    session.heard(transcript)
    classification = classify(transcript)

    # Refusal comes before anything else and does not consume the re-ask budget. An extra-dose
    # question is never allowed to be recorded as an extra dose taken — the real allow/deny call
    # belongs to Barkha's policy kernel, which the complete payload triggers.
    if classification.double_dose_request:
        session.record(classification)
        text = prompts.REFUSE_DOUBLE.format(caregiver=session.caregiver_name)
        session.say(text)
        return Reply(text=text, state=session.state)

    if session.state == "ASK_TAKEN":
        if classification.adherence == "unclear":
            if session.reask_count == 0:
                session.reask_count += 1
                text = prompts.REASK_TAKEN.format(med=_med_label(session))
                session.say(text)
                return Reply(text=text, state=session.state)
            session.needs_human = True
            text = prompts.NEEDS_HUMAN.format(caregiver=session.caregiver_name)
            session.say(text)
            session.state = "END"
            return Reply(text=text, state=session.state, is_final=True)

        session.record(classification)
        if session.outcome.adherence == "taken" and not classification.has_side_effect:
            text = prompts.ASK_SYMPTOM
            session.say(text)
            session.state = "WAIT_SYMPTOM"
            return Reply(text=text, state=session.state)
        return _readback(session)

    if session.state == "WAIT_SYMPTOM":
        session.record(classification)
        return _readback(session)

    # Anything after the read-back is out of scope for the demo path.
    return Reply(text="", state=session.state, is_final=True)
