"""Point the tests at a throwaway SQLite file, never the demo database."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_TMP_DB = Path(tempfile.gettempdir()) / "dawa-test.db"
for suffix in ("", "-wal", "-shm"):
    Path(str(_TMP_DB) + suffix).unlink(missing_ok=True)

# Set before src.config runs load_dotenv (which does not override real env vars).
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB}"
# Keep extract offline and fast. Both are needed: EXTRACT_MODE now defaults to
# "llm", so an empty key alone would only stop the call, not the intent.
os.environ["SARVAM_API_KEY"] = ""
os.environ["EXTRACT_MODE"] = "deterministic"
