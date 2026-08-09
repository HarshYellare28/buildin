"""Sarvam Instant Outbound client for one DAWA dose call."""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

from ..config import (
    SARVAM_AGENT_APP_ID,
    SARVAM_AGENT_APP_VERSION,
    SARVAM_AGENT_PHONE_NUMBER,
    SARVAM_CONNECTION_ID,
    SARVAM_CONVERSATIONS_API_KEY,
    SARVAM_ORG_ID,
    SARVAM_OUTBOUND_BASE,
    SARVAM_OUTBOUND_TIMEOUT_SECONDS,
    SARVAM_USER_PHONE_NUMBER,
    SARVAM_WEBHOOK_TOKEN,
    SARVAM_WEBHOOK_URL,
    SARVAM_WORKSPACE_ID,
)
from ..errors import ApiError

_E164 = re.compile(r"^\+[1-9]\d{7,14}$")
_UNIT_LABELS = {"mg": "milligram", "mcg": "microgram", "g": "gram", "ml": "millilitre"}


def _required(name: str, value: str) -> str:
    if not value:
        raise ApiError("SARVAM_OUTBOUND_NOT_CONFIGURED", f"{name} is not configured", 503)
    return value


def _phone(value: str, name: str) -> str:
    normalized = value.replace(" ", "").replace("-", "")
    if not _E164.fullmatch(normalized):
        raise ApiError("INVALID_PHONE_NUMBER", f"{name} must use E.164 format", 503)
    return normalized


def _webhook_url() -> str:
    url = _required("SARVAM_WEBHOOK_URL", SARVAM_WEBHOOK_URL)
    token = _required("SARVAM_WEBHOOK_TOKEN", SARVAM_WEBHOOK_TOKEN)
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["token"] = token
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _dose_number(medication: dict) -> str:
    value = medication.get("dose")
    return str(int(value)) if isinstance(value, float) and value.is_integer() else str(value)


def _dose_label(medication: dict) -> str:
    rendered = _dose_number(medication)
    unit = str(medication.get("unit") or "").lower()
    return f"{rendered} {_UNIT_LABELS.get(unit, unit)}".strip()


def build_payload(dose: dict, patient_name: str, caregiver_name: str) -> dict:
    medication = dose["medication"]
    return {
        "app_config": {
            "app_id": SARVAM_AGENT_APP_ID,
            "app_version": SARVAM_AGENT_APP_VERSION,
            "app_type": "agent",
            "connection_config": {
                "connection_id": SARVAM_CONNECTION_ID,
                "agent_phone_number": _phone(
                    SARVAM_AGENT_PHONE_NUMBER, "SARVAM_AGENT_PHONE_NUMBER"
                ),
            },
            "agent_variables": {
                "Patient_name": patient_name,
                "med_name": medication["name_normalized"].title(),
                "med_dose": _dose_label(medication),
                "care_giver": caregiver_name,
                "user_name": patient_name,
                "call_summary": (
                    f"Evening dose check for {medication['name_normalized'].title()} "
                    f"{_dose_number(medication)}{medication.get('unit')}"
                ),
            },
        },
        "user_config": {
            "user_phone_number": _phone(
                _required("SARVAM_USER_PHONE_NUMBER", SARVAM_USER_PHONE_NUMBER),
                "SARVAM_USER_PHONE_NUMBER",
            )
        },
        "webhook_config": {
            "url": _webhook_url(),
            "metadata": {
                "dose_id": dose["id"],
                "plan_id": dose["plan_id"],
                "test": True,
            },
        },
    }


def place_call(dose: dict, patient_name: str, caregiver_name: str) -> dict:
    api_key = _required("SARVAM_CONVERSATIONS_API_KEY", SARVAM_CONVERSATIONS_API_KEY)
    url = (
        f"{SARVAM_OUTBOUND_BASE}/orgs/{SARVAM_ORG_ID}/"
        f"workspaces/{SARVAM_WORKSPACE_ID}/outbounds"
    )
    try:
        response = httpx.post(
            url,
            headers={"Content-Type": "application/json", "X-API-Key": api_key},
            json=build_payload(dose, patient_name, caregiver_name),
            timeout=SARVAM_OUTBOUND_TIMEOUT_SECONDS,
        )
    except httpx.RequestError as exc:
        raise ApiError("SARVAM_OUTBOUND_FAILED", f"Sarvam outbound request failed: {exc}", 502) from exc

    if response.status_code != 200:
        detail = response.text[:500]
        raise ApiError(
            "SARVAM_OUTBOUND_FAILED",
            f"Sarvam outbound returned HTTP {response.status_code}: {detail}",
            502,
        )
    try:
        body = response.json()
    except ValueError as exc:
        raise ApiError("SARVAM_OUTBOUND_FAILED", "Sarvam outbound returned invalid JSON", 502) from exc
    attempt_id = body.get("attempt_id")
    if not attempt_id:
        raise ApiError("SARVAM_OUTBOUND_FAILED", "Sarvam outbound returned no attempt_id", 502)
    return body
