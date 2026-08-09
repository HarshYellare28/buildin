"""Sarvam Doc AI adapter for the optional prescription photo path.

The document model identifies names; the locked formulary remains authoritative
for the numeric dose (never turn a misread "10mg" into ground truth). Schedule
and food-rule *are* read off the model's output, the same way the paste path
reads them off the source line — dropping them was a bug, not a safety choice.
When the model's dose text disagrees with the formulary default, we flag it
with low confidence instead of silently overwriting or silently ignoring it,
so the human-confirm step actually has something to catch.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any

import httpx

from ..config import SARVAM_API_BASE, SARVAM_API_KEY
from ..errors import ApiError
from ..models.schemas import Medication
from .extract import _schedule_from_line
from .fixtures import load_formulary

EXTRACT_URL = f"{SARVAM_API_BASE}/doc-ai/v1/job/extract"
RESULTS_URL = f"{SARVAM_API_BASE}/doc-ai/v1/job/{{job_id}}/results"
POLL_INTERVAL_SECONDS = 1.5
POLL_TIMEOUT_SECONDS = 45

# Sarvam Doc AI's schema validator (distinct from plain JSON Schema) rejects a
# top-level "required" key and demands a non-empty "description" on every
# property — undocumented, found by trial and error against the live API.
MEDICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "medications": {
            "type": "array",
            "description": "Every medication listed in the prescription or discharge note",
            "items": {
                "type": "object",
                "description": "One medication entry",
                "properties": {
                    "name": {"type": "string", "description": "Drug name as written, with strength if present"},
                    "dose": {"type": "string", "description": "Dose amount and unit as written, e.g. '10 mg'"},
                    "schedule": {"type": "string", "description": "Timing/frequency/food instructions as written"},
                },
            },
        }
    },
}

DOSE_NUMBER_RE = re.compile(r"(\d+(?:\.\d+)?)")


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _match_formulary(raw_name: str) -> dict | None:
    needle = _normalize(raw_name)
    for fixture in load_formulary():
        normalized = _normalize(fixture["name_normalized"])
        if normalized and normalized in needle:
            return fixture
    return None


def _pluck_medications(body: dict[str, Any]) -> list[dict[str, Any]]:
    result: Any = body.get("result") or body.get("results") or {}
    if isinstance(result, list) and result:
        first = result[0]
        result = first.get("result", first) if isinstance(first, dict) else {}
    medications = result.get("medications") if isinstance(result, dict) else None
    return medications if isinstance(medications, list) else []


async def _poll(client: httpx.AsyncClient, headers: dict[str, str], job_id: str) -> dict:
    deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
    url = RESULTS_URL.format(job_id=job_id)
    while time.monotonic() <= deadline:
        response = await client.get(url, headers=headers)
        if response.status_code == 409:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            continue
        if response.status_code >= 400:
            raise ApiError(
                "SARVAM_RESULTS_FAILED",
                f"Sarvam Doc AI results failed ({response.status_code})",
                status_code=502,
            )
        body = response.json()
        status = body.get("status")
        if status in {"failed", "rejected"}:
            raise ApiError("SARVAM_JOB_FAILED", f"Sarvam Doc AI job {status}", status_code=502)
        if status in {"completed", "partially_completed"}:
            return body
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
    raise ApiError("SARVAM_TIMEOUT", "Sarvam Doc AI did not finish in time", status_code=504)


async def extract_document(
    file_bytes: bytes,
    filename: str,
    content_type: str,
) -> list[Medication]:
    if not SARVAM_API_KEY:
        raise ApiError("SARVAM_KEY_MISSING", "SARVAM_API_KEY is not configured", status_code=503)

    headers = {"api-subscription-key": SARVAM_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                EXTRACT_URL,
                headers=headers,
                files={"file": (filename, file_bytes, content_type)},
                data={
                    "schema": json.dumps(MEDICATION_SCHEMA),
                    "language": "en-IN",
                    "output_format": "json",
                },
            )
            if response.status_code >= 400:
                raise ApiError(
                    "SARVAM_SUBMIT_FAILED",
                    f"Sarvam Doc AI rejected the document ({response.status_code})",
                    status_code=502,
                )
            job_id = response.json().get("job_id")
            if not job_id:
                raise ApiError("SARVAM_BAD_RESPONSE", "Sarvam Doc AI returned no job id", status_code=502)
            result = await _poll(client, headers, job_id)
    except httpx.HTTPError as exc:
        raise ApiError("SARVAM_UNREACHABLE", f"Could not reach Sarvam Doc AI: {exc}", status_code=502) from exc

    medications: list[Medication] = []
    for raw in _pluck_medications(result):
        raw_name = str(raw.get("name") or "").strip()
        raw_dose = str(raw.get("dose") or "").strip()
        raw_schedule = str(raw.get("schedule") or "").strip()
        fixture = _match_formulary(raw_name)
        if not fixture:
            continue

        # Timing/food are safe to read off the model's output — worst case a
        # hint word is missed and the formulary default stands, same trust
        # level as the paste path reading a source line.
        data = dict(fixture)
        hint_text = f"{raw_dose} {raw_schedule}".strip()
        if hint_text:
            data = _schedule_from_line(hint_text, data)

        # The numeric dose stays locked to the formulary either way — we never
        # let a model reading turn "10mg" into ground truth. But if the photo
        # disagrees with that default, silently keeping the formulary's number
        # hides the disagreement from the reviewer entirely. Drop confidence
        # instead so the med card's existing low-confidence border catches it.
        mismatch = _dose_mismatches(raw_dose, fixture["dose"])
        confidence = 0.5 if mismatch else min(float(fixture.get("confidence", 0.8)), 0.9)

        data.update(
            name_raw=raw_name or fixture["name_raw"],
            source="ocr",
            confidence=confidence,
        )
        if mismatch:
            note = f"photo reads {raw_dose} — formulary default {fixture['dose']}{fixture['unit']} shown, please verify"
            data["schedule_text"] = f"{data.get('schedule_text', '')} ({note})".strip()
        medications.append(Medication(**data))
    return medications


def _dose_mismatches(raw_dose: str, fixture_dose: float) -> bool:
    """True when the OCR'd dose text names a different number than the formulary default."""
    match = DOSE_NUMBER_RE.search(raw_dose)
    if not match:
        return False
    try:
        photo_dose = float(match.group(1))
    except ValueError:
        return False
    return abs(photo_dose - float(fixture_dose)) > 1e-9
