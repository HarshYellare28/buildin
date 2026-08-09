import asyncio
import re
import time
from typing import Any, Optional

import httpx

from ..config import SARVAM_API_BASE, SARVAM_API_KEY
from ..store import store

DOC_AI_EXTRACT_URL = f"{SARVAM_API_BASE}/doc-ai/v1/job/extract"
DOC_AI_RESULTS_URL = f"{SARVAM_API_BASE}/doc-ai/v1/job/{{job_id}}/results"

MED_SCHEMA = {
    "type": "object",
    "properties": {
        "medications": {
            "type": "array",
            "description": "Every medication listed in the discharge/prescription document",
            "items": {
                "type": "object",
                "description": "One medication entry",
                "properties": {
                    "name": {"type": "string", "description": "Drug name as written, with strength if present"},
                    "dose": {"type": "string", "description": "Dose amount and unit, e.g. '5 mg'"},
                    "schedule": {"type": "string", "description": "When/how often to take it, e.g. 'night' or 'morning and night with food'"},
                },
            },
        }
    },
}

POLL_INTERVAL_S = 1.5
POLL_TIMEOUT_S = 45
TERMINAL_STATUSES = {"completed", "partially_completed", "failed", "rejected"}


class ExtractError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _match_formulary(name_text: str) -> Optional[dict]:
    needle = _normalize(name_text)
    if not needle:
        return None
    for med in store.formulary:
        if _normalize(med["name_normalized"]) in needle or _normalize(med["name_normalized"]) in _normalize(name_text):
            return med
    return None


def _build_medication(fixture: dict, source: str, raw_name: str, confidence: float) -> dict:
    return {
        **fixture,
        "name_raw": raw_name or fixture["name_raw"],
        "source": source,
        "confidence": round(confidence, 2),
    }


def _fallback_unmatched(raw_name: str, source: str) -> dict:
    """A drug the OCR/paste text mentions that isn't in our demo formulary.
    Still surfaced in the med graph (never silently dropped) but flagged with
    low confidence so the human-confirm step catches it."""
    slug = _normalize(raw_name)[:24] or "unknown"
    return {
        "id": f"med_unmatched_{slug}",
        "name_raw": raw_name,
        "name_normalized": slug,
        "dose": 0,
        "unit": "mg",
        "route": "oral",
        "schedule_text": "Unconfirmed — not in demo formulary",
        "times": [],
        "food_rule": "none",
        "duration_days": None,
        "criticality": "med",
        "source": source,
        "confidence": 0.4,
    }


def extract_from_text(text: str) -> list[dict]:
    """Paste path: match each formulary drug that appears in the pasted text."""
    lowered = text.lower()
    meds = []
    for fixture in store.formulary:
        if _normalize(fixture["name_normalized"]) in _normalize(lowered):
            meds.append(_build_medication(fixture, "paste", fixture["name_raw"], fixture["confidence"]))
    return meds


async def extract_from_photo(file_bytes: bytes, filename: str, content_type: str) -> list[dict]:
    """Photo path: real Sarvam Doc AI extract call, polled to completion, then
    mapped onto the demo formulary for clinical fields (criticality/food rule/route)."""
    if not SARVAM_API_KEY:
        raise ExtractError("SARVAM_KEY_MISSING", "SARVAM_API_KEY is not configured on the server")

    headers = {"api-subscription-key": SARVAM_API_KEY}
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            submit = await client.post(
                DOC_AI_EXTRACT_URL,
                headers=headers,
                files={"file": (filename, file_bytes, content_type or "application/octet-stream")},
                data={
                    "schema": _schema_json(),
                    "language": "en-IN",
                    "output_format": "json",
                },
            )
        except httpx.HTTPError as e:
            raise ExtractError("SARVAM_UNREACHABLE", f"Could not reach Sarvam Doc AI: {e}") from e

        if submit.status_code >= 400:
            raise ExtractError("SARVAM_SUBMIT_FAILED", f"Sarvam Doc AI rejected the job: {submit.status_code} {submit.text}")

        job = submit.json()
        job_id = job.get("job_id")
        if not job_id:
            raise ExtractError("SARVAM_BAD_RESPONSE", f"Sarvam Doc AI response had no job_id: {job}")

        result = await _poll_job(client, headers, job_id)

    raw_meds = _pluck_medications(result)
    meds = []
    for raw in raw_meds:
        name = str(raw.get("name") or "").strip()
        if not name:
            continue
        fixture = _match_formulary(name)
        if fixture:
            meds.append(_build_medication(fixture, "ocr", name, min(fixture["confidence"], 0.9)))
        else:
            meds.append(_fallback_unmatched(name, "ocr"))
    return meds


async def _poll_job(client: httpx.AsyncClient, headers: dict, job_id: str) -> dict[str, Any]:
    deadline = time.monotonic() + POLL_TIMEOUT_S
    url = DOC_AI_RESULTS_URL.format(job_id=job_id)
    while True:
        resp = await client.get(url, headers=headers)
        if resp.status_code == 409:
            # RESULTS_NOT_READY — job hasn't reached a terminal status yet.
            if time.monotonic() > deadline:
                raise ExtractError("SARVAM_TIMEOUT", f"Sarvam Doc AI job {job_id} did not finish within {POLL_TIMEOUT_S}s")
            await asyncio.sleep(POLL_INTERVAL_S)
            continue
        if resp.status_code >= 400:
            raise ExtractError("SARVAM_RESULTS_FAILED", f"Sarvam Doc AI results error: {resp.status_code} {resp.text}")
        body = resp.json()
        status = body.get("status")
        if status in TERMINAL_STATUSES:
            if status in ("failed", "rejected"):
                raise ExtractError("SARVAM_JOB_FAILED", f"Sarvam Doc AI job {status}: {body}")
            return body
        if time.monotonic() > deadline:
            raise ExtractError("SARVAM_TIMEOUT", f"Sarvam Doc AI job {job_id} did not finish within {POLL_TIMEOUT_S}s")
        await asyncio.sleep(POLL_INTERVAL_S)


def _pluck_medications(result_body: dict) -> list[dict]:
    result = result_body.get("result") or result_body.get("results") or {}
    if isinstance(result, list) and result:
        result = result[0].get("result", result[0]) if isinstance(result[0], dict) else {}
    if isinstance(result, dict):
        meds = result.get("medications")
        if isinstance(meds, list):
            return meds
    return []


def _schema_json() -> str:
    import json

    return json.dumps(MED_SCHEMA)
