"""Plan + dose persistence. The med graph is the system of record."""

from __future__ import annotations

from .. import db
from ..errors import ApiError, Conflict, NotFound
from ..models.schemas import FollowUp, Medication, Plan
from .fixtures import formulary_by_id, formulary_by_name
from .seed import ensure_seeded

EVENING_FROM_HOUR = 17
MORNING_UNTIL_HOUR = 12
CRITICALITY_RANK = {"high": 3, "med": 2, "low": 1}


# ----------------------------------------------------------------------- plans


# What the drug *is* comes from fixtures/formulary.json, never from the client.
# criticality is in here because the policy kernel reads it: a client that could
# set it could talk the kernel out of refusing a double dose. Dose and schedule
# stay editable — PATCH is the human-confirm path and titration is a real edit.
LOCKED_FIELDS = ("id", "name_raw", "name_normalized", "route", "criticality")
EDITABLE_FIELDS = (
    "dose",
    "unit",
    "times",
    "schedule_text",
    "food_rule",
    "duration_days",
    "source",
    "confidence",
)


def lock_to_formulary(medications: list[Medication]) -> list[Medication]:
    """Snap edited medications back onto the locked formulary row.

    Extract already snaps onto the formulary; this guards the human-edit path so
    a UI bug cannot push a drug nobody prescribed into an activatable plan, or
    relabel a prescribed one.
    """
    ids = formulary_by_id()
    names = formulary_by_name()

    locked: list[Medication] = []
    for med in medications:
        row = ids.get(med.id) or names.get(med.name_normalized)
        if row is None:
            raise ApiError(
                "MEDICATION_NOT_IN_FORMULARY",
                f"{med.name_raw!r} is not in the locked demo formulary",
            )
        # An id and a name that disagree is a caller bug. Snapping it back to the
        # id's drug would hide a UI that thinks it is editing something else.
        if med.name_normalized and med.name_normalized != row["name_normalized"]:
            raise ApiError(
                "MEDICATION_MISMATCH",
                f"{row['id']} is {row['name_normalized']}, not {med.name_normalized!r}",
            )

        merged = {f: row[f] for f in LOCKED_FIELDS}
        merged.update({f: getattr(med, f) for f in EDITABLE_FIELDS})
        locked.append(Medication(**merged))
    return locked


def create_plan(medications: list[Medication], follow_up: FollowUp | None = None) -> Plan:
    people = ensure_seeded()
    plan = Plan(
        id=db.next_id("plan_demo_", counter="plan"),
        status="draft",
        patient_id=people["patient"]["id"],
        caregiver_id=people["caregiver"]["id"],
        medications=medications,
        follow_up=follow_up,
    )
    db.execute(
        "INSERT INTO plans (id, status, created_at, data) VALUES (?, ?, ?, ?)",
        (plan.id, plan.status, db.now_iso(), db.dumps(plan.model_dump())),
    )
    return plan


def get_plan(plan_id: str) -> Plan:
    row = db.query_one("SELECT data FROM plans WHERE id = ?", (plan_id,))
    if row is None:
        raise NotFound("PLAN_NOT_FOUND", f"No plan {plan_id}")
    return Plan(**db.loads(row["data"]))


def save_plan(plan: Plan) -> Plan:
    db.execute(
        "UPDATE plans SET status = ?, data = ? WHERE id = ?",
        (plan.status, db.dumps(plan.model_dump()), plan.id),
    )
    return plan


def patch_medications(
    plan_id: str,
    medications: list[Medication],
    follow_up: FollowUp | None = None,
    set_follow_up: bool = False,
) -> Plan:
    plan = get_plan(plan_id)
    if plan.status != "draft":
        raise Conflict("PLAN_NOT_DRAFT", "Only draft plans can be edited")
    plan.medications = lock_to_formulary(medications)
    if set_follow_up:  # omitted key keeps the extracted follow-up as-is
        plan.follow_up = follow_up
    return save_plan(plan)


def active_plan_id() -> str | None:
    """The one active plan of the demo world, if there is one."""
    row = db.query_one("SELECT id FROM plans WHERE status = 'active' ORDER BY rowid DESC LIMIT 1")
    return row["id"] if row else None


def activate_plan(plan_id: str) -> Plan:
    plan = get_plan(plan_id)
    if plan.status == "active":
        return plan
    if not plan.medications:
        raise ApiError("PLAN_EMPTY", "Cannot activate a plan with no medications")
    plan.status = "active"
    return save_plan(plan)


def get_medication(plan: Plan, medication_id: str) -> Medication:
    for med in plan.medications:
        if med.id == medication_id:
            return med
    raise NotFound("MEDICATION_NOT_FOUND", f"No medication {medication_id} on plan {plan.id}")


def pick_medication(plan: Plan, simulate_time: str = "evening") -> Medication:
    """Default target for a demo-clock dose: the most critical med due then."""
    if not plan.medications:
        raise ApiError("PLAN_EMPTY", "Plan has no medications")

    window = (simulate_time or "evening").lower()
    candidates = [m for m in plan.medications if _due_in_window(m, window)]
    if not candidates:
        candidates = list(plan.medications)

    return max(
        candidates,
        key=lambda m: (CRITICALITY_RANK.get(m.criticality, 0), m.confidence),
    )


def _due_in_window(med: Medication, window: str) -> bool:
    hours = [_hour(t) for t in med.times]
    hours = [h for h in hours if h is not None]
    if window in ("evening", "night"):
        return any(h >= EVENING_FROM_HOUR for h in hours)
    if window == "morning":
        return any(h < MORNING_UNTIL_HOUR for h in hours)
    return bool(hours)


def _hour(time_text: str) -> int | None:
    try:
        return int(time_text.split(":")[0])
    except (ValueError, IndexError):
        return None


# ----------------------------------------------------------------------- doses


def create_dose(plan: Plan, medication: Medication, simulate_time: str) -> dict:
    dose = {
        "id": db.next_id("dose_", counter="dose"),
        "plan_id": plan.id,
        "medication_id": medication.id,
        "status": "calling",
        "simulate_time": simulate_time,
        "triggered_at": db.now_iso(),
        "medication": medication.model_dump(),
    }
    db.execute(
        "INSERT INTO doses (id, plan_id, medication_id, status, created_at, data) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            dose["id"],
            plan.id,
            medication.id,
            dose["status"],
            dose["triggered_at"],
            db.dumps(dose),
        ),
    )
    return dose


def get_dose(dose_id: str) -> dict:
    row = db.query_one("SELECT data FROM doses WHERE id = ?", (dose_id,))
    if row is None:
        raise NotFound("DOSE_NOT_FOUND", f"No dose {dose_id}")
    return db.loads(row["data"])


def save_dose(dose: dict) -> dict:
    db.execute(
        "UPDATE doses SET status = ?, data = ? WHERE id = ?",
        (dose["status"], db.dumps(dose), dose["id"]),
    )
    return dose


def claim_dose_for_completion(dose_id: str) -> dict:
    """Move a dose to completed, atomically. Exactly one caller can win.

    Reading the status and then writing it are two statements, so a retried
    webhook landing twice at once would otherwise pass both checks and write
    two outcomes and two caregiver packets for one dose. The guard belongs in
    the WHERE clause, not in an if.
    """
    dose = get_dose(dose_id)
    dose["status"] = "completed"
    cur = db.execute(
        "UPDATE doses SET status = 'completed', data = ? WHERE id = ? AND status != 'completed'",
        (db.dumps(dose), dose_id),
    )
    if cur.rowcount == 0:
        raise Conflict("DOSE_ALREADY_COMPLETED", f"Dose {dose_id} is already completed")
    return dose
