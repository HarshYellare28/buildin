"""Write path into Barkha's API — the only place a dose outcome becomes durable state.

STATUS: written, not yet exercised. POST /doses/{dose_id}/complete does not exist yet
(services/api has no routes). Failures are surfaced on the session rather than raised, so a
missing backend degrades the call to "voice worked, write pending" instead of killing it.
"""

import httpx

from .config import settings

# A refused connection to an absent backend costs ~4.6s on Windows (localhost is retried across
# IPv6 then IPv4). That lands inside a live dose call as silence, so the connect phase is capped
# separately from the read phase.
_TIMEOUT = httpx.Timeout(10.0, connect=1.5)


def post_complete(dose_id: str, payload: dict) -> tuple[bool, str | None]:
    """Return (posted, error). Never raises — a dead backend must not abort a live dose call."""
    url = f"{settings.dawa_api_url}/doses/{dose_id}/complete"
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            response = client.post(url, json=payload)
    except httpx.RequestError as exc:
        return False, f"{type(exc).__name__}: {exc}"

    if response.status_code >= 400:
        return False, f"{response.status_code}: {response.text[:300]}"
    return True, None


def check_policy(intent: str, medication_id: str) -> dict | None:
    """Barkha's POST /policy/check. Returns None if unreachable — the dialogue already refused."""
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            response = client.post(
                f"{settings.dawa_api_url}/policy/check",
                json={"intent": intent, "medication_id": medication_id},
            )
        if response.status_code >= 400:
            return None
        return response.json()
    except (httpx.RequestError, ValueError):
        return None
