"""FastAPI surface for the dose call.

Barkha mounts this with one line in her app:

    from voice.router import router as voice_router
    app.include_router(voice_router)

Everything lives under /voice/* so it cannot collide with the routes in docs/API_CONTRACT.md.
"""

import base64

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from . import dialogue, session as session_store
from .complete_client import check_policy, post_complete
from .config import settings
from .sarvam_client import SarvamError, synthesize, transcribe
from .session import DoseVoiceSession, Medication

router = APIRouter(prefix="/voice", tags=["voice"])


class StartSessionRequest(BaseModel):
    """Fed from Barkha's POST /doses/trigger response — no import-time coupling to her code."""

    dose_id: str
    medication: Medication
    patient_name: str = "Lakshmi"
    caregiver_name: str = "Ananya"
    speak: bool = True


class TurnTextRequest(BaseModel):
    user_text: str
    speak: bool = True


def _speak(text: str, enabled: bool = True) -> tuple[str | None, str | None]:
    if not text or not enabled:
        return None, None
    try:
        return base64.b64encode(synthesize(text)).decode("ascii"), None
    except SarvamError as exc:
        # Surface it instead of 500-ing: the operator can still read the line off the screen.
        return None, str(exc)


def _finalize(sess: DoseVoiceSession) -> None:
    if not sess.ready_for_complete or sess.complete_posted:
        return
    posted, error = post_complete(sess.dose_id, sess.complete_payload())
    sess.complete_posted = posted
    sess.complete_error = error


def _turn(sess: DoseVoiceSession, transcript: str) -> dialogue.Reply:
    """Advance one turn. The dialogue refuses an extra-dose request on its own; this also puts the
    refusal through Barkha's policy kernel so hers is the record, not ours (team/Jyotir.md M9)."""
    refused_before = sess.double_dose_refused
    reply = dialogue.advance(sess, transcript)
    if sess.double_dose_refused and not refused_before:
        sess.policy_check = check_policy("double_dose", sess.medication.id)
    if reply.is_final:
        _finalize(sess)
    return reply


def _view(sess: DoseVoiceSession, **extra) -> dict:
    return {
        "session_id": sess.session_id,
        "dose_id": sess.dose_id,
        "state": sess.state,
        "medication": sess.medication.name_raw,
        "outcome": {
            "adherence": sess.outcome.adherence,
            "exception_type": sess.outcome.exception_type,
            "patient_reported": sess.outcome.patient_reported,
            "normalized_symptom": sess.outcome.normalized_symptom,
            "confidence": round(sess.outcome.confidence, 2),
            "source": sess.outcome.source,
            "notes": sess.outcome.notes,
        },
        "double_dose_refused": sess.double_dose_refused,
        "policy_check": sess.policy_check,
        "must_escalate": sess.must_escalate,
        "needs_human": sess.needs_human,
        "ready_for_complete": sess.ready_for_complete,
        "complete_payload": sess.complete_payload() if sess.ready_for_complete else None,
        "complete_posted": sess.complete_posted,
        "complete_error": sess.complete_error,
        "turns": [{"role": t.role, "text": t.text} for t in sess.turns],
        **extra,
    }


def _require(session_id: str) -> DoseVoiceSession:
    sess = session_store.get(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "SESSION_NOT_FOUND"}})
    return sess


@router.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "sarvam_key_configured": settings.configured,
        "stt_model": settings.stt_model,
        "tts_model": settings.tts_model,
        "llm_classify_enabled": settings.llm_classify_enabled,
        "dawa_api_url": settings.dawa_api_url,
    }


@router.post("/sessions")
def start_session(body: StartSessionRequest) -> dict:
    sess = session_store.put(
        DoseVoiceSession(
            dose_id=body.dose_id,
            medication=body.medication,
            patient_name=body.patient_name,
            caregiver_name=body.caregiver_name,
        )
    )
    reply = dialogue.start(sess)
    audio, tts_error = _speak(reply.text, body.speak)
    return _view(sess, assistant_text=reply.text, audio_b64=audio, tts_error=tts_error, transcript=None)


@router.post("/sessions/{session_id}/turn")
def voice_turn(session_id: str, audio: UploadFile = File(...)) -> dict:
    sess = _require(session_id)
    raw = audio.file.read()
    if not raw:
        raise HTTPException(status_code=400, detail={"error": {"code": "EMPTY_AUDIO"}})

    try:
        heard = transcribe(
            raw,
            filename=audio.filename or "turn.webm",
            content_type=audio.content_type or "audio/webm",
        )
    except SarvamError as exc:
        raise HTTPException(status_code=502, detail={"error": {"code": "STT_FAILED", "message": str(exc)}})

    reply = _turn(sess, heard.text)
    audio_b64, tts_error = _speak(reply.text)
    return _view(
        sess,
        assistant_text=reply.text,
        audio_b64=audio_b64,
        tts_error=tts_error,
        transcript=heard.text,
        stt_language=heard.language_code,
    )


@router.post("/sessions/{session_id}/turn-text")
def text_turn(session_id: str, body: TurnTextRequest) -> dict:
    """Typed input. Used for testing the dialogue without a mic, and as the disaster fallback
    described in team/Jyotir.md — never the default path in a judged demo."""
    sess = _require(session_id)
    reply = _turn(sess, body.user_text)
    audio_b64, tts_error = _speak(reply.text, body.speak)
    return _view(
        sess,
        assistant_text=reply.text,
        audio_b64=audio_b64,
        tts_error=tts_error,
        transcript=body.user_text,
    )


@router.get("/sessions/{session_id}")
def get_session(session_id: str) -> dict:
    return _view(_require(session_id))
