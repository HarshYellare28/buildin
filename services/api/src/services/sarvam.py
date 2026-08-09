"""One HTTP client for every Sarvam call the API makes.

Endpoints, all verified against api.sarvam.ai:

    chat()            POST /v1/chat/completions   sarvam-105b-conversations
    doc_ai_extract()  Document Digitization create/upload/start/poll/download
    speech_to_text()  POST /speech-to-text        saaras:v3      (multipart)
    text_to_speech()  POST /text-to-speech        bulbul:v3      (base64 wav)

Every call is logged with model, elapsed ms and outcome. That matters more than
it sounds: the previous extract path swallowed auth and timeout failures into a
bare `return None`, so a dead key and a skipped code path looked identical from
the outside. Failures raise SarvamError here; callers decide whether to fall
back, and the log says which happened.

Callers: services/extract.py (chat, doc_ai_extract). The live dose call runs on
voice/sarvam_client.py, which has its own transport — speech_to_text() and
text_to_speech() here remain for non-voice callers and the L0 verify scripts.
"""

from __future__ import annotations

import base64
import json
import logging
import re
import tempfile
import time
import zipfile
from pathlib import Path

import httpx
from sarvamai import SarvamAI

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


DOC_AI_POLL_INTERVAL_SECONDS = 1.5
DOC_AI_POLL_TIMEOUT_SECONDS = 45
_DOC_AI_TERMINAL = {"completed", "partially_completed", "failed", "rejected"}


def doc_ai_extract(
    file_bytes: bytes,
    filename: str,
    content_type: str,
    schema: dict,
    *,
    language_code: str = "en-IN",
    timeout: float = DOC_AI_POLL_TIMEOUT_SECONDS,
) -> dict:
    """Digitise a page with Sarvam Vision and return its OCR text.

    Sarvam retired the legacy schema-extraction `/doc-ai/v1/job/extract`
    endpoint. The supported API is now a create → upload → start → poll →
    download job. Medication structure is deliberately recovered later by
    DAWA's locked formulary parser, not trusted directly from OCR.
    """
    _require_key("doc-ai")
    if not file_bytes:
        raise SarvamError("doc-ai: empty file")
    del schema, content_type  # structure comes from the locked parser after OCR
    started = time.monotonic()
    safe_name = Path(filename).name or "document.jpg"
    try:
        with tempfile.TemporaryDirectory(prefix="dawa-doc-") as temp_dir:
            input_path = Path(temp_dir) / safe_name
            output_path = Path(temp_dir) / "output.zip"
            input_path.write_bytes(file_bytes)

            client = SarvamAI(api_subscription_key=SARVAM_API_KEY)
            job = client.document_intelligence.create_job(
                language=language_code,
                output_format="md",
            )
            job.upload_file(str(input_path))
            job.start()
            status = job.wait_until_complete(
                poll_interval=DOC_AI_POLL_INTERVAL_SECONDS,
                timeout=timeout,
            )
            if status.job_state not in {"Completed", "PartiallyCompleted"}:
                detail = getattr(status, "error_message", "") or status.job_state
                raise SarvamError(f"doc-ai: job {status.job_state}: {detail}")
            job.download_output(str(output_path))
            text = _digitization_text(output_path)
    except SarvamError:
        raise
    except Exception as exc:
        logger.warning(
            "sarvam doc-digitization FAILED in %.0fms: %s",
            (time.monotonic() - started) * 1000,
            exc,
        )
        raise SarvamError(f"doc-ai: {exc}") from exc

    if not text.strip():
        raise SarvamError("doc-ai: completed job returned no readable text")
    logger.info(
        "sarvam doc-digitization ok in %.0fms (%d chars)",
        (time.monotonic() - started) * 1000,
        len(text),
    )
    return {"status": "completed", "ocr_text": text}


def _digitization_text(output_path: Path) -> str:
    """Read Markdown from Sarvam's output ZIP, with a plain-text fallback."""
    try:
        with zipfile.ZipFile(output_path) as archive:
            markdown = [name for name in archive.namelist() if name.lower().endswith(".md")]
            if markdown:
                text = "\n".join(
                    archive.read(name).decode("utf-8", errors="replace") for name in markdown
                )
                return _strip_embedded_assets(text)
            json_files = [name for name in archive.namelist() if name.lower().endswith(".json")]
            chunks: list[str] = []
            for name in json_files:
                value = json.loads(archive.read(name).decode("utf-8", errors="replace"))
                chunks.extend(_text_values(value))
            return _strip_embedded_assets("\n".join(chunks))
    except zipfile.BadZipFile:
        return _strip_embedded_assets(
            output_path.read_text(encoding="utf-8", errors="replace")
        )


def _strip_embedded_assets(text: str) -> str:
    """Remove base64 image payloads before medication-name scanning.

    Digitization Markdown embeds the uploaded page as a data URI. Random base64
    substrings can equal short formulary aliases such as ``pcm`` and must never
    be interpreted as prescription text.
    """
    text = re.sub(r"!\[[^\]]*\]\(data:[^)]*\)", "", text, flags=re.IGNORECASE)
    return re.sub(
        r"<img\b[^>]*\bsrc=[\"']data:[^\"']*[\"'][^>]*>",
        "",
        text,
        flags=re.IGNORECASE,
    )


def _text_values(value: object) -> list[str]:
    if isinstance(value, dict):
        direct = [
            str(child)
            for key, child in value.items()
            if key.lower() in {"text", "content", "markdown"} and isinstance(child, str)
        ]
        return direct or [text for child in value.values() for text in _text_values(child)]
    if isinstance(value, list):
        return [text for child in value for text in _text_values(child)]
    return []


def _doc_ai_poll(job_id: str, timeout: float) -> dict:
    url = f"{SARVAM_API_BASE}/doc-ai/v1/job/{job_id}/results"
    deadline = time.monotonic() + timeout
    while True:
        try:
            response = httpx.get(url, headers=_headers(json_body=False), timeout=30)
        except Exception as exc:
            raise SarvamError(f"doc-ai/results: {exc}") from exc

        # 409 is RESULTS_NOT_READY, not an error — the job is still running.
        if response.status_code != 409:
            if response.status_code >= 400:
                raise SarvamError(
                    f"doc-ai/results: HTTP {response.status_code} {response.text[:300]}"
                )
            body = response.json()
            status = body.get("status")
            if status in _DOC_AI_TERMINAL:
                if status in ("failed", "rejected"):
                    raise SarvamError(f"doc-ai: job {status}: {str(body)[:300]}")
                logger.info("sarvam doc-ai job %s %s", job_id, status)
                return body

        if time.monotonic() > deadline:
            raise SarvamError(f"doc-ai: job {job_id} unfinished after {timeout:.0f}s")
        time.sleep(DOC_AI_POLL_INTERVAL_SECONDS)


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
