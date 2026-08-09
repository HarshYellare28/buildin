import os
from pathlib import Path

from dotenv import load_dotenv

SERVICE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = SERVICE_ROOT.parent.parent
FIXTURES_DIR = REPO_ROOT / "fixtures"

load_dotenv(SERVICE_ROOT / ".env")

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
SARVAM_API_BASE = os.getenv("SARVAM_API_BASE", "https://api.sarvam.ai")
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
