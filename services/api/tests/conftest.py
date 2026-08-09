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
os.environ["SARVAM_API_KEY"] = ""  # keep extract on the deterministic path
