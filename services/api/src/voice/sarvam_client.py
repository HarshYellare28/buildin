"""Thin wrappers over the three Sarvam endpoints the dose call needs.

This client preserves Jyotir's strict voice-session contract: transcription
metadata, template-only TTS, and JSON-schema classification. The extraction
path uses ``services.sarvam`` separately because its chat response is free-form.
"""

import base64
import json
import time
from dataclasses import dataclass

import httpx

from .config import settings


class SarvamError(RuntimeError):
    """Sarvam call failed after its retry. Callers decide whether it is fatal."""


@dataclass
class Transcript:
    text: str
    language_code: str | None
    request_id: str | None


def _speech_headers() -> dict[str, str]:
    return {"api-subscription-key": settings.api_key}


def _llm_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.api_key}",
        "api-subscription-key": settings.api_key,
        "Content-Type": "application/json",
    }


def _require_key() -> None:
    if not settings.configured:
        raise SarvamError("SARVAM_API_KEY is not set — copy .env.example to .env and fill it in.")


# Pool connections because TLS setup is latency the patient hears as silence.
_client = httpx.Client(timeout=settings.speech_timeout)


def _post(url: str, *, timeout: float, retries: int = 1, **kwargs) -> httpx.Response:
    """POST with one retry on timeout / 5xx. 4xx is never retried."""
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = _client.post(url, timeout=timeout, **kwargs)
            if response.status_code < 400:
                return response
            if response.status_code < 500:
                raise SarvamError(f"{url} -> {response.status_code}: {response.text[:300]}")
            last = SarvamError(f"{url} -> {response.status_code}: {response.text[:300]}")
        except httpx.RequestError as exc:
            last = SarvamError(f"{url} -> {type(exc).__name__}: {exc}")
        if attempt < retries:
            time.sleep(0.4)
    raise last if last else SarvamError(f"{url} failed")


def transcribe(
    audio: bytes,
    filename: str = "turn.webm",
    content_type: str = "audio/webm",
) -> Transcript:
    _require_key()
    response = _post(
        f"{settings.api_base}/speech-to-text",
        timeout=settings.speech_timeout,
        headers=_speech_headers(),
        files={"file": (filename, audio, content_type)},
        data={"model": settings.stt_model, "language_code": settings.patient_lang},
    )
    body = response.json()
    return Transcript(
        text=(body.get("transcript") or "").strip(),
        language_code=body.get("language_code"),
        request_id=body.get("request_id"),
    )


def synthesize(text: str, language_code: str | None = None) -> bytes:
    """Return WAV bytes. Callers only pass policy-bound templates."""
    _require_key()
    response = _post(
        f"{settings.api_base}/text-to-speech",
        timeout=settings.speech_timeout,
        headers={**_speech_headers(), "Content-Type": "application/json"},
        json={
            "text": text,
            "target_language_code": language_code or settings.patient_lang,
            "model": settings.tts_model,
            "speaker": settings.tts_speaker,
        },
    )
    audios = response.json().get("audios") or []
    if not audios:
        raise SarvamError("text-to-speech returned no audio")
    return base64.b64decode(audios[0])


def classify_json(system_prompt: str, user_text: str, schema: dict) -> dict:
    """Structured classification. Raises so classify.py can fall back to regex."""
    _require_key()
    response = _post(
        f"{settings.api_base}/v1/chat/completions",
        timeout=settings.llm_timeout,
        retries=0,
        headers=_llm_headers(),
        json={
            "model": settings.llm_model,
            "temperature": 0,
            "max_tokens": 1500,
            "reasoning_effort": "low",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "dose_classification", "strict": True, "schema": schema},
            },
        },
    )
    choice = response.json()["choices"][0]
    content = choice["message"].get("content")
    if not content:
        raise SarvamError(
            f"classifier returned empty content (finish_reason={choice.get('finish_reason')})"
        )
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise SarvamError(f"classifier returned non-JSON: {str(content)[:200]}") from exc
