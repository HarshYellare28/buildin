"""Env + path config. One patient, one caregiver, one SQLite file."""

from __future__ import annotations

import os
from datetime import timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

# services/api/src/config.py -> services/api/src -> services/api -> services -> repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_DIR = REPO_ROOT / "fixtures"

load_dotenv(REPO_ROOT / ".env")

IST = timezone(timedelta(hours=5, minutes=30))

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "").strip()
SARVAM_API_BASE = os.getenv("SARVAM_API_BASE", "https://api.sarvam.ai").rstrip("/")
# sarvam-m is deprecated and 400s. The long extraction prompt can take ~15s.
SARVAM_MODEL = os.getenv("SARVAM_MODEL", "sarvam-105b-conversations").strip()
SARVAM_TIMEOUT_SECONDS = float(os.getenv("SARVAM_TIMEOUT_SECONDS", "25"))

# auto: formulary parse first, LLM only when it finds nothing (fast demo, real
# fallback for off-fixture text). deterministic: never call the LLM.
# llm: LLM first, formulary parse as backstop.
EXTRACT_MODE = os.getenv("EXTRACT_MODE", "auto").strip().lower()

DEMO_PATIENT_LANG = os.getenv("DEMO_PATIENT_LANG", "hi-IN")
DEMO_CAREGIVER_LANG = os.getenv("DEMO_CAREGIVER_LANG", "en-IN")

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if o.strip()
]


def database_path() -> Path:
    """Resolve DATABASE_URL (sqlite only) to a filesystem path under the repo."""
    url = os.getenv("DATABASE_URL", "sqlite:///./data/local/dawa.db")
    raw = url.split("sqlite:///", 1)[-1] if url.startswith("sqlite") else url
    path = Path(raw)
    if not path.is_absolute():
        path = REPO_ROOT / raw.lstrip("./")
    return path
