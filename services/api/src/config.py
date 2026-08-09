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

# Voice models. These names are shared with voice/config.py — the live dose call
# reads the same three vars, so the defaults must agree or the verify scripts
# would exercise a different pair than the demo runs on. saaras:v3 / bulbul:v3 /
# ritu is the combination verified live; ritu is female, which the Hindi
# templates in voice/prompts.py assume (they use "rahi hoon").
SARVAM_STT_MODEL = os.getenv("SARVAM_STT_MODEL", "saaras:v3").strip()
SARVAM_TTS_MODEL = os.getenv("SARVAM_TTS_MODEL", "bulbul:v3").strip()
SARVAM_TTS_SPEAKER = os.getenv("SARVAM_TTS_SPEAKER", "ritu").strip()
SARVAM_VOICE_TIMEOUT_SECONDS = float(os.getenv("SARVAM_VOICE_TIMEOUT_SECONDS", "30"))

# Sarvam Conversations / Instant Outbound. This key can differ from the model
# API key, so never silently send the model key to the Conversations endpoint.
SARVAM_CONVERSATIONS_API_KEY = os.getenv("SARVAM_CONVERSATIONS_API_KEY", "").strip()
SARVAM_OUTBOUND_BASE = os.getenv(
    "SARVAM_OUTBOUND_BASE", "https://apps.sarvam.ai/api/outbounds/v1"
).rstrip("/")
SARVAM_ORG_ID = os.getenv(
    "SARVAM_ORG_ID", "019f996a-c7e4-7e85-b98c-986748c68dc0"
).strip()
SARVAM_WORKSPACE_ID = os.getenv(
    "SARVAM_WORKSPACE_ID", "019f996a-c7e8-7b1b-91a8-486ab550b37b"
).strip()
SARVAM_AGENT_APP_ID = os.getenv(
    "SARVAM_AGENT_APP_ID", "Dawa-dealer-3fa05c2a-8533"
).strip()
SARVAM_AGENT_APP_VERSION = int(os.getenv("SARVAM_AGENT_APP_VERSION", "2"))
SARVAM_CONNECTION_ID = os.getenv(
    "SARVAM_CONNECTION_ID", "9b232ec0-df-2c8c62bf-ba5b"
).strip()
SARVAM_AGENT_PHONE_NUMBER = os.getenv(
    "SARVAM_AGENT_PHONE_NUMBER", "+918065353757"
).strip()
SARVAM_USER_PHONE_NUMBER = os.getenv("SARVAM_USER_PHONE_NUMBER", "").strip()
SARVAM_WEBHOOK_URL = os.getenv("SARVAM_WEBHOOK_URL", "").strip()
SARVAM_WEBHOOK_TOKEN = os.getenv("SARVAM_WEBHOOK_TOKEN", "").strip()
SARVAM_OUTBOUND_TIMEOUT_SECONDS = float(os.getenv("SARVAM_OUTBOUND_TIMEOUT_SECONDS", "30"))

# llm (default): Sarvam first, formulary parse as backstop when it returns
# nothing. deterministic: never call the LLM (tests pin this).
# auto: formulary parse first, LLM only as rescue — fastest, but on the demo
# fixture the parse always hits, so Sarvam is never exercised.
EXTRACT_MODE = os.getenv("EXTRACT_MODE", "llm").strip().lower()

# App loggers are silent under uvicorn's default config (it only attaches
# handlers to its own loggers). Without this, every sarvam log line vanishes.
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip().upper()

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
