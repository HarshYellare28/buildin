"""Sarvam Doc AI adapter for the optional prescription photo path.

The document model identifies names; the locked formulary remains authoritative
for dose metadata and safety fields. Unknown drugs are omitted rather than made
activatable from model output.
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
from .fixtures import load_formulary

EXTRACT_URL = f"{SARVAM_API_BASE}/doc-ai/v1/job/extract"
RESULTS_URL = f"{SARVAM_API_BASE}/doc-ai/v1/job/{{job_id}}/results"
POLL_INTERVAL_SECONDS = 1.5
POLL_TIMEOUT_SECONDS = 45

MEDICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "medications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "dose": {"type": "string"},
                    "schedule": {"type": "string"},
                },
                "required": ["name"],
            },
        }
    },
    "required": ["medications"],
}


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
        fixture = _match_formulary(raw_name)
        if not fixture:
            continue
        data = dict(fixture)
        data.update(
            name_raw=raw_name or fixture["name_raw"],
            source="ocr",
            confidence=min(float(fixture.get("confidence", 0.8)), 0.9),
        )
        medications.append(Medication(**data))
    return medications
