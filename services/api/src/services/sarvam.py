"""One HTTP client for every Sarvam call the API makes.

Three endpoints, all verified against api.sarvam.ai:

    chat()            POST /v1/chat/completions   sarvam-105b-conversations
    speech_to_text()  POST /speech-to-text        saarika:v2.5   (multipart)
    text_to_speech()  POST /text-to-speech        bulbul:v2      (base64 wav)

Every call is logged with model, elapsed ms and outcome. That matters more than
it sounds: the previous extract path swallowed auth and timeout failures into a
bare `return None`, so a dead key and a skipped code path looked identical from
the outside. Failures raise SarvamError here; callers decide whether to fall
back, and the log says which happened.

Callers: services/extract.py (chat) and voice/sarvam_client.py (all three).
"""

from __future__ import annotations

import base64
import logging
import time

import httpx

from ..config import (
    SARVAM_API_BASE,
    SARVAM_API_KEY,
    SARVAM_MODEL,
    SARVAM_STT_MODEL,
    SARVAM_TIMEOUT_SECONDS,
    SARVAM_TTS_MODEL,
    SARVAM_TTS_SPEAKER,
    SARVAM_VOICE_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)


class SarvamError(RuntimeError):
    """Any Sarvam call that did not return usable content."""


def is_configured() -> bool:
    return bool(SARVAM_API_KEY)


def _headers(json_body: bool = True) -> dict[str, str]:
    # Sarvam accepts the subscription-key header; the bearer is sent too so the
    # same key works if an endpoint is fronted by a standard OpenAI-style proxy.
    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Authorization": f"Bearer {SARVAM_API_KEY}",
    }
    if json_body:
        headers["Content-Type"] = "application/json"
    return headers


def _require_key(op: str) -> None:
    if not SARVAM_API_KEY:
        raise SarvamError(f"{op}: SARVAM_API_KEY is empty — set it in .env")


def _post(op: str, url: str, *, timeout: float, **kwargs) -> dict:
    """POST + log + raise. Returns the decoded JSON body."""
    started = time.monotonic()
    try:
        response = httpx.post(url, timeout=timeout, **kwargs)
        response.raise_for_status()
        body = response.json()
    except httpx.HTTPStatusError as exc:
        elapsed = (time.monotonic() - started) * 1000
        # Body text is the only place Sarvam explains a 400/401/429.
        detail = exc.response.text[:300]
        logger.warning(
            "sarvam %s FAILED http=%s in %.0fms: %s",
            op,
            exc.response.status_code,
            elapsed,
            detail,
        )
        raise SarvamError(f"{op}: HTTP {exc.response.status_code} {detail}") from exc
    except Exception as exc:
        elapsed = (time.monotonic() - started) * 1000
        logger.warning("sarvam %s FAILED in %.0fms: %s", op, elapsed, exc)
        raise SarvamError(f"{op}: {exc}") from exc

    logger.info("sarvam %s ok in %.0fms", op, (time.monotonic() - started) * 1000)
    return body


def chat(
    messages: list[dict],
    *,
    temperature: float = 0,
    model: str = SARVAM_MODEL,
    timeout: float = SARVAM_TIMEOUT_SECONDS,
) -> str:
    """Chat completion. Returns the assistant text, never an empty string."""
    _require_key("chat")
    body = _post(
        f"chat[{model}]",
        f"{SARVAM_API_BASE}/v1/chat/completions",
        headers=_headers(),
        json={"model": model, "temperature": temperature, "messages": messages},
        timeout=timeout,
    )
    try:
        message = body["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise SarvamError(f"chat: unexpected response shape: {str(body)[:200]}") from exc

    # Reasoning models sometimes leave `content` null and put the answer in
    # `reasoning_content`.
    content = message.get("content") or message.get("reasoning_content") or ""
    if not content.strip():
        raise SarvamError("chat: empty content and empty reasoning_content")
    return content


def speech_to_text(
    audio: bytes,
    *,
    language_code: str,
    filename: str = "turn.wav",
    content_type: str = "audio/wav",
    model: str = SARVAM_STT_MODEL,
    timeout: float = SARVAM_VOICE_TIMEOUT_SECONDS,
) -> str:
    """Transcribe one utterance. Returns the transcript text."""
    _require_key("stt")
    if not audio:
        raise SarvamError("stt: empty audio")
    body = _post(
        f"stt[{model}]",
        f"{SARVAM_API_BASE}/speech-to-text",
        headers=_headers(json_body=False),
        files={"file": (filename, audio, content_type)},
        data={"model": model, "language_code": language_code},
        timeout=timeout,
    )
    transcript = (body.get("transcript") or "").strip()
    if not transcript:
        raise SarvamError("stt: empty transcript")
    return transcript


def text_to_speech(
    text: str,
    *,
    language_code: str,
    speaker: str = SARVAM_TTS_SPEAKER,
    model: str = SARVAM_TTS_MODEL,
    timeout: float = SARVAM_VOICE_TIMEOUT_SECONDS,
) -> bytes:
    """Synthesise one line. Returns decoded WAV bytes."""
    _require_key("tts")
    if not (text or "").strip():
        raise SarvamError("tts: empty text")
    body = _post(
        f"tts[{model}]",
        f"{SARVAM_API_BASE}/text-to-speech",
        headers=_headers(),
        json={
            "text": text,
            "target_language_code": language_code,
            "speaker": speaker,
            "model": model,
        },
        timeout=timeout,
    )
    audios = body.get("audios") or []
    if not audios:
        raise SarvamError(f"tts: no audio in response: {str(body)[:200]}")
    try:
        return base64.b64decode(audios[0])
    except Exception as exc:
        raise SarvamError(f"tts: audio was not valid base64: {exc}") from exc
