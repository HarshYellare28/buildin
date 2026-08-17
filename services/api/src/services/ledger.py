"""Append-only event ledger. The backend is the only writer."""

from __future__ import annotations

from typing import Any

from .. import db
from ..models.schemas import Event


def append(
    type: str,
    plan_id: str | None = None,
    dose_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> Event:
    event = Event(
        id=db.next_id("evt_", counter="evt"),
        ts=db.now_iso(),
        type=type,  # type: ignore[arg-type]
        plan_id=plan_id,
        dose_id=dose_id,
        payload=payload or {},
    )
    db.execute(
        "INSERT INTO events (id, ts, type, plan_id, dose_id, payload) VALUES (?, ?, ?, ?, ?, ?)",
        (event.id, event.ts, event.type, event.plan_id, event.dose_id, db.dumps(event.payload)),
    )
    return event


def list_events(plan_id: str | None = None) -> list[Event]:
    if plan_id:
        rows = db.query("SELECT * FROM events WHERE plan_id = ? ORDER BY seq ASC", (plan_id,))
    else:
        rows = db.query("SELECT * FROM events ORDER BY seq ASC")
    return [
        Event(
            id=r["id"],
            ts=r["ts"],
            type=r["type"],
            plan_id=r["plan_id"],
            dose_id=r["dose_id"],
            payload=db.loads(r["payload"]),
        )
        for r in rows
    ]
