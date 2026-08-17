"""Schedule reading off the note. Deterministic, no network.

Both cases here were live bugs found by scripts/hinglish-suite.py.
"""

from __future__ import annotations

from src.services.extract import extract_medications


def _by_name(text: str) -> dict:
    return {m.name_normalized: m for m in extract_medications(text)}


# --------------------------------------------------- one line, several drugs


def test_prose_line_does_not_share_schedules_between_drugs():
    """The bug: both drugs inherited every time word on the line."""
    meds = _by_name(
        "Discharge ke baad amlodipine 5mg morning mein continue karna hai "
        "aur metformin 500mg morning evening lena hai."
    )
    assert meds["amlodipine"].times == ["08:00"]  # not ["08:00", "21:00"]
    assert meds["metformin"].times == ["08:00", "21:00"]


def test_numbered_list_still_reads_each_line():
    meds = _by_name(
        "1) Amlodipine 5 mg — roj raat ko\n"
        "2) Metformin 500 mg — subah + raat, khane ke saath\n"
    )
    assert meds["amlodipine"].times == ["21:00"]
    assert meds["metformin"].times == ["08:00", "21:00"]
    assert meds["metformin"].food_rule == "with_food"


def test_schedule_leading_the_drug_name_still_read():
    """Span runs name -> next drug, so a leading time needs the line fallback."""
    meds = _by_name("Raat ko: Amlodipine 5 mg")
    assert meds["amlodipine"].times == ["21:00"]


# ------------------------------------------------------------- food rules


def test_after_food_in_hinglish():
    """'breakfast ke baad' is after-food; it used to fall through as none."""
    meds = _by_name("Amlodipine 5 mg — breakfast ke baad leni hai")
    assert meds["amlodipine"].food_rule == "with_food"


def test_before_food_is_not_filed_as_with_food():
    """'khana khane se pehle' contains the with-food token 'khana'."""
    meds = _by_name("Amlodipine 5 mg — khana khane se pehle leni hai")
    assert meds["amlodipine"].food_rule == "before_food"
    assert "before food" in meds["amlodipine"].schedule_text.lower()


def test_no_food_wording_leaves_the_formulary_default():
    meds = _by_name("Amlodipine 5 mg roz raat ko")
    assert meds["amlodipine"].food_rule == "none"


# --------------------------------------------------------------- time words


def test_shaam_is_evening():
    """NIGHT_HINTS had 'sham'; real notes write 'shaam'."""
    meds = _by_name("Amlodipine 5 mg — shaam ko leni hai")
    assert meds["amlodipine"].times == ["21:00"]


def test_sos_clears_times():
    meds = _by_name("Paracetamol 500 mg — bukhar ho to SOS")
    assert meds["paracetamol"].times == []
    assert meds["paracetamol"].schedule_text == "SOS"
