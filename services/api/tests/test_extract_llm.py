"""The Sarvam extract path, exercised without touching the network.

conftest pins EXTRACT_MODE=deterministic for the rest of the suite, so these
tests drive the LLM path directly and stub `sarvam.chat`. The live-key check
lives in scripts/verify-sarvam.py, not here — the suite must stay offline.
"""

from __future__ import annotations

import json

import pytest

from src.services import extract, sarvam

# Amlodipine's formulary default is Night / 21:00. Every note below says subah
# (morning) instead, so a schedule of 08:00 proves the source line was read and
# 21:00 proves it was silently dropped.
NOTE = """Discharge advice:
1) Tab. Amlod 5mg subah
2) Tab. Metformin 500 raat ko khane ke saath
"""


def _stub_chat(monkeypatch, payload: dict) -> None:
    monkeypatch.setattr(sarvam, "chat", lambda *a, **k: json.dumps(payload))


def _stub_chat_raising(monkeypatch, exc: Exception) -> None:
    def boom(*a, **k):
        raise exc

    monkeypatch.setattr(sarvam, "chat", boom)


def test_quoted_line_sets_schedule_for_unknown_spelling(monkeypatch):
    """'Amlod' is not in ALIASES, so only the model's quote can locate the line."""
    _stub_chat(
        monkeypatch,
        {
            "medications": [
                {"name_normalized": "amlodipine", "source_line": "1) Tab. Amlod 5mg subah"}
            ]
        },
    )
    hits = extract._extract_via_sarvam(NOTE)
    assert hits == [{"name_normalized": "amlodipine", "line": "1) Tab. Amlod 5mg subah"}]

    med = extract._to_medication(hits[0], "paste")
    assert med.times == ["08:00"]
    assert med.schedule_text == "Morning"


def test_hallucinated_quote_is_refused(monkeypatch):
    """A line that is not in the note must never reach the scheduler."""
    _stub_chat(
        monkeypatch,
        {
            "medications": [
                {
                    "name_normalized": "amlodipine",
                    "source_line": "Tab. Amlod 5mg subah shaam do baar",
                }
            ]
        },
    )
    hits = extract._extract_via_sarvam(NOTE)
    assert hits == [{"name_normalized": "amlodipine", "line": ""}]
    # No line -> untouched formulary defaults, not an invented twice-daily dose.
    assert extract._to_medication(hits[0], "paste").times == ["21:00"]


def test_quote_stealing_another_drugs_line_is_refused(monkeypatch):
    """Metformin owns line 2 by alias, so amlodipine cannot claim it."""
    _stub_chat(
        monkeypatch,
        {
            "medications": [
                {
                    "name_normalized": "amlodipine",
                    "source_line": "2) Tab. Metformin 500 raat ko khane ke saath",
                },
                {
                    "name_normalized": "metformin",
                    "source_line": "2) Tab. Metformin 500 raat ko khane ke saath",
                },
            ]
        },
    )
    hits = {h["name_normalized"]: h["line"] for h in extract._extract_via_sarvam(NOTE)}
    assert hits["amlodipine"] == ""
    # Metformin resolves by alias lookup, which is ground truth and unaffected.
    # Its span starts at the drug name, so the "2) Tab. " list marker is not in it.
    assert hits["metformin"] == "Metformin 500 raat ko khane ke saath"


def test_alias_lookup_beats_model_quote(monkeypatch):
    """Where our own table resolves the line, the model does not get a vote."""
    _stub_chat(
        monkeypatch,
        {
            "medications": [
                {"name_normalized": "metformin", "source_line": "1) Tab. Amlod 5mg subah"}
            ]
        },
    )
    hits = extract._extract_via_sarvam(NOTE)
    assert hits[0]["line"] == "Metformin 500 raat ko khane ke saath"


def test_drug_outside_formulary_is_dropped(monkeypatch):
    _stub_chat(
        monkeypatch,
        {
            "medications": [
                {"name_normalized": "warfarin", "source_line": "1) Tab. Amlod 5mg subah"},
                {"name_normalized": "amlodipine", "source_line": "1) Tab. Amlod 5mg subah"},
            ]
        },
    )
    hits = extract._extract_via_sarvam(NOTE)
    assert [h["name_normalized"] for h in hits] == ["amlodipine"]


@pytest.mark.parametrize(
    "failure",
    [sarvam.SarvamError("HTTP 401 bad key"), ValueError("no JSON object in model output")],
)
def test_sarvam_failure_returns_none(monkeypatch, failure):
    _stub_chat_raising(monkeypatch, failure)
    assert extract._extract_via_sarvam(NOTE) is None


def test_llm_mode_falls_back_to_formulary_when_sarvam_dies(monkeypatch):
    """A dead key must degrade to the deterministic parse, not to an empty plan."""
    monkeypatch.setattr(extract, "EXTRACT_MODE", "llm")
    monkeypatch.setattr(sarvam, "is_configured", lambda: True)
    _stub_chat_raising(monkeypatch, sarvam.SarvamError("HTTP 401 bad key"))

    meds = extract.extract_medications(NOTE)
    # Metformin is the only one the alias table can see on its own.
    assert [m.name_normalized for m in meds] == ["metformin"]


def test_llm_mode_skips_call_when_key_missing(monkeypatch):
    monkeypatch.setattr(extract, "EXTRACT_MODE", "llm")
    monkeypatch.setattr(sarvam, "is_configured", lambda: False)
    _stub_chat_raising(monkeypatch, AssertionError("chat must not be called"))

    assert [m.name_normalized for m in extract.extract_medications(NOTE)] == ["metformin"]


def test_deterministic_mode_never_calls_sarvam(monkeypatch):
    monkeypatch.setattr(extract, "EXTRACT_MODE", "deterministic")
    _stub_chat_raising(monkeypatch, AssertionError("chat must not be called"))

    assert [m.name_normalized for m in extract.extract_medications(NOTE)] == ["metformin"]
