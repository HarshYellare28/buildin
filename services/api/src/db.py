"""SQLite store. Rows are JSON blobs — the pydantic models are the schema.

Single file under data/local/ (gitignored). One connection guarded by a lock
because FastAPI runs sync endpoints in a threadpool.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from typing import Any, Iterable

from .config import IST, database_path

_lock = threading.RLock()
_conn: sqlite3.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
  id TEXT PRIMARY KEY,
  role TEXT NOT NULL,
  data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS plans (
  id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS doses (
  id TEXT PRIMARY KEY,
  plan_id TEXT NOT NULL,
  medication_id TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  id TEXT NOT NULL UNIQUE,
  ts TEXT NOT NULL,
  type TEXT NOT NULL,
  plan_id TEXT,
  dose_id TEXT,
  payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS packets (
  id TEXT PRIMARY KEY,
  plan_id TEXT NOT NULL,
  dose_id TEXT,
  created_at TEXT NOT NULL,
  data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS meal_checks (
  id TEXT PRIMARY KEY,
  plan_id TEXT NOT NULL,
  dose_id TEXT,
  created_at TEXT NOT NULL,
  data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS counters (
  name TEXT PRIMARY KEY,
  value INTEGER NOT NULL
);
"""


def get_conn() -> sqlite3.Connection:
    global _conn
    with _lock:
        if _conn is None:
            path = database_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            _conn = sqlite3.connect(str(path), check_same_thread=False)
            _conn.row_factory = sqlite3.Row
            _conn.execute("PRAGMA journal_mode=WAL")
            _conn.executescript(SCHEMA)
            _conn.commit()
        return _conn


def init_db() -> None:
    get_conn()


def execute(sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
    conn = get_conn()
    with _lock:
        cur = conn.execute(sql, tuple(params))
        conn.commit()
        return cur


def query(sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
    conn = get_conn()
    with _lock:
        return conn.execute(sql, tuple(params)).fetchall()


def query_one(sql: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
    rows = query(sql, params)
    return rows[0] if rows else None


def next_id(prefix: str, counter: str | None = None) -> str:
    """Sequential, demo-friendly ids: plan_demo_1, dose_1, pkt_1, evt_1."""
    name = counter or prefix
    conn = get_conn()
    with _lock:
        cur = conn.execute("SELECT value FROM counters WHERE name = ?", (name,))
        row = cur.fetchone()
        value = (row["value"] if row else 0) + 1
        conn.execute(
            "INSERT INTO counters (name, value) VALUES (?, ?) "
            "ON CONFLICT(name) DO UPDATE SET value = excluded.value",
            (name, value),
        )
        conn.commit()
    return f"{prefix}{value}"


def now_iso() -> str:
    return datetime.now(IST).isoformat(timespec="seconds")


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def loads(value: str) -> Any:
    return json.loads(value)


def reset_world() -> None:
    """Clear every demo table. Seeding happens in services/seed.py."""
    conn = get_conn()
    with _lock:
        for table in (
            "people",
            "plans",
            "doses",
            "events",
            "packets",
            "meal_checks",
            "counters",
        ):
            conn.execute(f"DELETE FROM {table}")
        try:
            conn.execute("DELETE FROM sqlite_sequence WHERE name = 'events'")
        except sqlite3.OperationalError:  # no AUTOINCREMENT rows written yet
            pass
        conn.commit()
