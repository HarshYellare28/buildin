"""Discharge text -> follow-up visit ("7 din baad OPD review").

Deterministic, same spirit as the policy kernel: no model call decides when the
patient must see a clinician. We read a duration off the note, anchor it to the
note's own date (falling back to today), and hand back a concrete due date that
a reminder can be built on later.

This is NOT a medication. It never enters the med graph and never triggers a
dose; it rides along on the plan so the caregiver UI can show "OPD review on
16 Aug" and a future scheduler has something to fire on.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from ..config import IST
from ..models.schemas import FollowUp

# Hour of day a clinic-visit reminder should fire (IST).
FOLLOW_UP_HOUR = 10

# Something in the line has to say "come back and be seen".
VISIT_HINTS = (
    "opd",
    "review",
    "follow up",
    "follow-up",
    "followup",
    "checkup",
    "check up",
    "check-up",
    "clinic",
    "aana",
    "dikhana",
    "milna",
    "visit",
    "ओपीडी",
    "दिखाना",
)

# Numerals as written in romanised Hindi / English discharge notes.
WORD_NUMBERS = {
    "ek": 1, "one": 1,
    "do": 2, "two": 2,
    "teen": 3, "three": 3,
    "char": 4, "chaar": 4, "four": 4,
    "panch": 5, "paanch": 5, "five": 5,
    "che": 6, "chhe": 6, "chah": 6, "six": 6,
    "saat": 7, "sat": 7, "seven": 7,
    "aath": 8, "ath": 8, "eight": 8,
    "nau": 9, "nine": 9,
    "das": 10, "ten": 10,
    "pandrah": 15, "fifteen": 15,
}

# unit -> days
UNIT_DAYS = {
    "din": 1, "dino": 1, "dinon": 1, "day": 1, "days": 1, "दिन": 1,
    "hafta": 7, "hafte": 7, "haftey": 7, "hafton": 7,
    "saptah": 7, "week": 7, "weeks": 7, "हफ्ते": 7, "हफ्ता": 7,
    "mahina": 30, "mahine": 30, "month": 30, "months": 30, "महीने": 30,
}

_NUMBER = r"(?P<count>\d{1,3}|" + "|".join(sorted(WORD_NUMBERS, key=len, reverse=True)) + r")"
_UNIT = r"(?P<unit>" + "|".join(sorted(UNIT_DAYS, key=len, reverse=True)) + r")"
DURATION_RE = re.compile(rf"(?<![a-z0-9]){_NUMBER}\s*{_UNIT}(?![a-z])", re.IGNORECASE)

# "Date: 09/08/2026" — Indian notes are DD/MM/YYYY.
NOTE_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})[/-](\d{1,2})[/-](\d{4})(?!\d)")
ISO_DATE_RE = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")

MAX_DAYS = 365


def extract_follow_up(text: str, source: str = "paste") -> FollowUp | None:
    """Best-effort clinic-visit date. Returns None when the note says nothing."""
    if not text:
        return None

    match = _find_visit_duration(text)
    if match is None:
        return None
    line, count, unit, exact_numeral = match

    days = count * UNIT_DAYS[unit]
    if days <= 0 or days > MAX_DAYS:
        return None

    anchor = _anchor_date(text)
    due = anchor + timedelta(days=days)
    due_at = datetime(due.year, due.month, due.day, FOLLOW_UP_HOUR, tzinfo=IST)

    return FollowUp(
        kind="clinic_visit",
        raw_text=line.strip(),
        in_days=days,
        due_date=due.isoformat(),
        due_at=due_at.isoformat(timespec="seconds"),
        anchor_date=anchor.isoformat(),
        source=source,
        confidence=0.9 if exact_numeral else 0.75,
    )


def _find_visit_duration(text: str) -> tuple[str, int, str, bool] | None:
    """A duration on a line that also mentions being seen again.

    Line-scoped on purpose: "7 din baad OPD review" is a follow-up,
    "Metformin 30 din" on a medicine line is a course length, not a visit.
    """
    for line in text.splitlines():
        low = line.lower()
        if not any(hint in low for hint in VISIT_HINTS):
            continue
        found = DURATION_RE.search(low)
        if found is None:
            continue
        count, exact = _to_count(found.group("count"))
        if count is None:
            continue
        return line, count, found.group("unit").lower(), exact
    return None


def _to_count(raw: str) -> tuple[int | None, bool]:
    if raw.isdigit():
        return int(raw), True
    return WORD_NUMBERS.get(raw.lower()), False


def _anchor_date(text: str) -> date:
    """Day 0 for the countdown: the note's own date if it carries one."""
    iso = ISO_DATE_RE.search(text)
    if iso:
        try:
            return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        except ValueError:
            pass

    for day_s, month_s, year_s in NOTE_DATE_RE.findall(text):
        day, month, year = int(day_s), int(month_s), int(year_s)
        if month > 12 and day <= 12:  # written MM/DD by mistake
            day, month = month, day
        try:
            return date(year, month, day)
        except ValueError:
            continue

    return datetime.now(IST).date()
