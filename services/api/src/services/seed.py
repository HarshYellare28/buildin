"""Seed the demo world: one patient, one caregiver."""

from __future__ import annotations

from .. import db
from ..errors import ApiError
from .fixtures import load_people


def seed_people() -> dict:
    people = load_people()
    for role in ("patient", "caregiver"):
        person = people[role]
        db.execute(
            "INSERT INTO people (id, role, data) VALUES (?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET role = excluded.role, data = excluded.data",
            (person["id"], role, db.dumps(person)),
        )
    return people


def ensure_seeded() -> dict:
    row = db.query_one("SELECT COUNT(*) AS n FROM people")
    if not row or row["n"] < 2:
        return seed_people()
    return get_people()


def get_people() -> dict:
    rows = db.query("SELECT role, data FROM people")
    people = {r["role"]: db.loads(r["data"]) for r in rows}
    if "patient" not in people or "caregiver" not in people:
        return seed_people()
    return people


def get_person(role: str) -> dict:
    people = get_people()
    if role not in people:
        raise ApiError("PERSON_NOT_FOUND", f"No seeded {role}", status_code=404)
    return people[role]
