"""Sarvam STT / LLM / TTS for the dose call — JYOTIR, THIS IS YOURS TO USE.

Thin façade over `services/sarvam.py`, which owns the HTTP, the retries-free
error type and the logging. Edit this file freely; the transport underneath is
shared with `/plans/extract`, so leave that one alone.

    from ..voice.sarvam_client import transcribe, speak, ask, SarvamError

    text  = transcribe(wav_bytes)          # patient audio -> Hindi text
    reply = ask(SYSTEM_PROMPT, turns)      # dialogue turn -> assistant text
    wav   = speak(reply)                   # assistant text -> WAV bytes

Every function raises SarvamError on failure — catch it and fall back to the
deterministic turn in `turn.py` rather than letting a dose call die.

Language defaults come from DEMO_PATIENT_LANG (hi-IN) / DEMO_CAREGIVER_LANG.

Reminder from the contract: nothing here writes state. When the dialogue ends,
POST the outcome to `POST /doses/{dose_id}/complete` — that is the only writer
of adherence, exceptions and caregiver packets.
"""

from __future__ import annotations

from ..config import DEMO_PATIENT_LANG
from ..services.sarvam import (
    SarvamError,
    chat,
    is_configured,
    speech_to_text,
    text_to_speech,
)

__all__ = [
    "SarvamError",
    "ask",
    "is_configured",
    "speak",
    "transcribe",
    "SYSTEM_PROMPT",
]

# The prompt is a rail, not the safety layer. The policy kernel in
# src/policy/kernel.py is what actually refuses a double dose — this text just
# keeps the model from arguing with it out loud.
SYSTEM_PROMPT = (
    "You are DAWA, a medication execution assistant on a phone call with an "
    "elderly patient in India. You are NOT a doctor.\n"
    "Speak natural spoken Hindi in Roman script, one or two short sentences, "
    "warm and unhurried.\n"
    "Your only job this call: confirm whether the patient took the named "
    "medicine, and capture any symptom they mention in their own words.\n"
    "Never name a medicine other than the one given to you. Never suggest a "
    "dose, a new drug, or stopping a drug. If asked whether to take an extra "
    "tablet, refuse warmly and say you will inform the family.\n"
    "If a side effect is reported: acknowledge, say you will tell the family, "
    "and do not give medical advice."
)


def transcribe(
    audio: bytes,
    *,
    language_code: str = DEMO_PATIENT_LANG,
    filename: str = "turn.wav",
    content_type: str = "audio/wav",
) -> str:
    """Patient audio -> text. Raises SarvamError on empty or failed transcription."""
    return speech_to_text(
        audio,
        language_code=language_code,
        filename=filename,
        content_type=content_type,
    )


def speak(text: str, *, language_code: str = DEMO_PATIENT_LANG) -> bytes:
    """Assistant text -> WAV bytes, ready to hand back to the browser."""
    return text_to_speech(text, language_code=language_code)


def ask(
    system_prompt: str,
    turns: list[dict],
    *,
    temperature: float = 0.3,
) -> str:
    """One dialogue turn. `turns` is [{"role": "user"|"assistant", "content": str}]."""
    return chat(
        [{"role": "system", "content": system_prompt}, *turns],
        temperature=temperature,
    )
