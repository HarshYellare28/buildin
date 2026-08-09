"""Discharge text -> draft medications.

Two paths that both end in the same place:

1. Deterministic parse of the text against fixtures/formulary.json (default).
2. Sarvam LLM, used only when the deterministic parse finds nothing — it reads
   spellings and phrasings the alias table does not know.

A photographed note (`extract_from_document`) is a separate path: Sarvam Doc AI
returns medication rows and those rows are used directly. Whichever path ran,
the drug itself always comes from fixtures/formulary.json.

The LLM only ever answers *which drugs are in this note*. Dose, times, duration
and criticality come from the locked formulary plus the source line, never from
the model — a model that reads "7 din baad OPD review" as a 7-day course would
otherwise corrupt the med graph. See EXTRACT_MODE in config.py.

Neither path can invent a drug outside fixtures/formulary.json, and everything
returned is a draft a human still has to confirm before activate.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from ..config import EXTRACT_MODE
from ..models.schemas import Medication
from . import sarvam
from .fixtures import formulary_by_name, load_formulary

logger = logging.getLogger(__name__)

# Sarvam Doc AI only accepts these. Anything else is rejected before we spend a
# round trip on it.
SUPPORTED_DOCUMENT_TYPES = {"image/jpeg", "image/png", "application/pdf"}

# Transliterations / brand-ish spellings seen in Indian discharge notes.
ALIASES: dict[str, str] = {
    "amlodipine": "amlodipine",
    "amlodipin": "amlodipine",
    "amlong": "amlodipine",
    "amlokind": "amlodipine",
    "एम्लोडिपिन": "amlodipine",
    "metformin": "metformin",
    "metfornin": "metformin",
    "glycomet": "metformin",
    "मेटफॉर्मिन": "metformin",
    "atorvastatin": "atorvastatin",
    "atorvastin": "atorvastatin",
    "atorva": "atorvastatin",
    "storvas": "atorvastatin",
    "एटोरवास्टेटिन": "atorvastatin",
    "paracetamol": "paracetamol",
    "pcm": "paracetamol",
    "dolo": "paracetamol",
    "crocin": "paracetamol",
    "पैरासिटामोल": "paracetamol",
}

MORNING_HINTS = ("subah", "morning", "सुबह", "od morning", "bf", "breakfast")
NIGHT_HINTS = ("raat", "night", "रात", "hs", "bedtime", "evening", "sham", "shaam")
FOOD_HINTS = (
    "khane ke saath", "with food", "after food", "khana", "pc", "भोजन", "खाने",
    # "... ke baad" is how discharge notes actually say after-food.
    "khane ke baad", "khana khane ke baad", "breakfast ke baad", "nashte ke baad",
    "bhojan ke baad", "after meal", "after meals", "after breakfast", "post food",
)
# Checked before FOOD_HINTS and wins: "khana khane se pehle" contains the token
# "khana", so without this it would be filed as with_food — the opposite
# instruction. Metformin before vs with food is a real difference.
BEFORE_FOOD_HINTS = (
    "khane se pehle", "khana khane se pehle", "bhojan se pehle", "nashte se pehle",
    "before food", "before meal", "before meals", "before breakfast",
    "khali pet", "empty stomach", "ac",
)
SOS_HINTS = ("sos", "if needed", "bukhar", "prn", "जरूरत")

# Any signal that a text span actually carries schedule information.
_SCHEDULE_HINTS = MORNING_HINTS + NIGHT_HINTS + FOOD_HINTS + BEFORE_FOOD_HINTS + SOS_HINTS

MORNING_TIME = "08:00"
NIGHT_TIME = "21:00"


def extract_medications(text: str, source: str = "paste") -> list[Medication]:
    """Best available extraction. Never raises on LLM failure."""
    hits: list[dict] = []
    path = ""

    if EXTRACT_MODE != "llm":
        hits = _extract_via_formulary(text)
        path = "formulary"

    if not hits and EXTRACT_MODE != "deterministic":
        if sarvam.is_configured():
            hits = _extract_via_sarvam(text) or []
            path = "sarvam"
        else:
            logger.warning("extract: SARVAM_API_KEY empty, skipping LLM path")

    if not hits and EXTRACT_MODE == "llm":
        hits = _extract_via_formulary(text)
        path = "formulary(backstop)"

    logger.info(
        "extract mode=%s path=%s -> %d med(s): %s",
        EXTRACT_MODE,
        path or "none",
        len(hits),
        ", ".join(h["name_normalized"] for h in hits) or "-",
    )
    return [_to_medication(item, source) for item in hits]


# ---------------------------------------------------------------- deterministic


def _extract_via_formulary(text: str) -> list[dict]:
    """Scan the text for known formulary drugs and read their schedule off the line."""
    positions = _drug_positions(text)
    return [
        {"name_normalized": name, "line": _segment_at(text, idx, positions)}
        for name, idx in sorted(positions.items(), key=lambda kv: kv[1])
    ]


def _drug_positions(text: str) -> dict[str, int]:
    """Earliest index of each formulary drug, under any alias we know."""
    lowered = text.lower()
    positions: dict[str, int] = {}
    for alias, normalized in ALIASES.items():
        idx = lowered.find(alias.lower())
        if idx == -1:
            continue
        if normalized not in positions or idx < positions[normalized]:
            positions[normalized] = idx
    return positions


def _line_at(text: str, index: int) -> str:
    start = text.rfind("\n", 0, index) + 1
    end = text.find("\n", index)
    if end == -1:
        end = len(text)
    return text[start:end]


def _segment_at(text: str, index: int, positions: dict[str, int]) -> str:
    """This drug's own span of its line, not the whole line.

    A note written as prose puts several drugs on one line — "amlodipine 5mg
    morning mein continue karna hai aur metformin 500mg morning evening lena
    hai". Handing that whole line to _schedule_from_line gives *both* drugs both
    schedules, so amlodipine silently picks up a 21:00 dose the note never
    ordered. The span runs from this drug's name to the next drug's name.

    Falls back to the full line when the span carries no schedule word at all,
    which is what happens when the timing leads instead of trails ("Raat ko:
    Amlodipine"). A widened span is only ever as wrong as the old behaviour.
    """
    line_start = text.rfind("\n", 0, index) + 1
    line_end = text.find("\n", index)
    if line_end == -1:
        line_end = len(text)

    following = [p for p in positions.values() if index < p < line_end]
    segment = text[index : min(following) if following else line_end]

    if not _has_hint(segment.lower(), _SCHEDULE_HINTS):
        return text[line_start:line_end]
    return segment


def _has_hint(low: str, hints: tuple[str, ...]) -> bool:
    """Whole-word match so short hints like 'hs' or 'pc' do not fire inside words."""
    return any(
        re.search(rf"(?<![a-z]){re.escape(h)}(?![a-z])", low) is not None for h in hints
    )


def _schedule_from_line(line: str, base: dict) -> dict:
    """Override formulary defaults when the source line is explicit."""
    low = line.lower()
    times: list[str] = []
    if _has_hint(low, MORNING_HINTS):
        times.append(MORNING_TIME)
    if _has_hint(low, NIGHT_HINTS):
        times.append(NIGHT_TIME)

    is_sos = _has_hint(low, SOS_HINTS)
    if is_sos:
        times = []

    out = dict(base)
    if times or is_sos:
        out["times"] = times
        out["schedule_text"] = _schedule_text(times, is_sos)

    # Order matters: "khana khane se pehle" contains the with-food token "khana".
    if _has_hint(low, BEFORE_FOOD_HINTS):
        food_rule, suffix = "before_food", "before food"
    elif _has_hint(low, FOOD_HINTS):
        food_rule, suffix = "with_food", "with food"
    else:
        return out

    out["food_rule"] = food_rule
    if out["schedule_text"] and "food" not in out["schedule_text"].lower():
        out["schedule_text"] = f"{out['schedule_text']} {suffix}"
    return out


def _schedule_text(times: list[str], is_sos: bool) -> str:
    if is_sos:
        return "SOS"
    if times == [MORNING_TIME, NIGHT_TIME]:
        return "Morning and night"
    if times == [MORNING_TIME]:
        return "Morning"
    if times == [NIGHT_TIME]:
        return "Night"
    return ", ".join(times)


# ---------------------------------------------------------------------- Sarvam


def _extract_via_sarvam(text: str) -> list[dict] | None:
    """Ask Sarvam *which* formulary drugs appear. Any failure returns None."""
    allowed = ", ".join(m["name_normalized"] for m in load_formulary())
    prompt = (
        "List the home medications named in this Indian hospital discharge note. "
        "The note mixes English and Hindi (romanised).\n"
        f"Only use these normalized drug names: {allowed}. "
        "Never invent a drug that is not in that list. Do not guess dosing.\n"
        "For each drug also copy back `source_line`: the single line of the note "
        "it appears on, verbatim, character for character. Do not paraphrase it.\n"
        'Reply with JSON only: '
        '{"medications": [{"name_normalized": str, "source_line": str}]}\n\n'
        f"NOTE:\n{text}"
    )
    try:
        content = sarvam.chat(
            [
                {
                    "role": "system",
                    "content": "You extract medication names. You output JSON only.",
                },
                {"role": "user", "content": prompt},
            ]
        )
        parsed = _parse_json_block(content)
        items = parsed.get("medications") if isinstance(parsed, dict) else None
        if not items:
            logger.warning("extract: sarvam returned no medications")
            return None
    except sarvam.SarvamError as exc:
        logger.warning("extract: sarvam unavailable, falling back: %s", exc)
        return None
    except Exception as exc:  # unparseable JSON / shape drift
        logger.warning("extract: sarvam output unusable, falling back: %s", exc)
        return None

    known = formulary_by_name()
    accepted: list[tuple[str, str | None]] = []
    for item in items:
        name = item.get("name_normalized") if isinstance(item, dict) else item
        name = str(name or "").strip().lower()
        name = ALIASES.get(name, name)
        if name not in known or any(n == name for n, _ in accepted):
            continue  # outside the locked formulary -> dropped, not invented
        quoted = item.get("source_line") if isinstance(item, dict) else None
        accepted.append((name, quoted if isinstance(quoted, str) else None))

    # Two passes, because pass 1 is ground truth and pass 2 must not contradict
    # it. Schedule still comes off the source line, exactly like the local path.
    # Our own alias lookup wins wherever it resolves; the model's quoted line is
    # only a rescue for spellings ALIASES has never seen — the one case where
    # _locate_line comes back empty.
    resolved = {name: _locate_line(text, name) for name, _ in accepted}
    claimed = {_collapse(line) for line in resolved.values() if line}

    cleaned: list[dict] = []
    for name, quoted in accepted:
        line = resolved[name] or _match_quoted_line(text, quoted, claimed)
        cleaned.append({"name_normalized": name, "line": line})
    return cleaned or None


def _collapse(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _match_quoted_line(text: str, quoted: str | None, claimed: set[str]) -> str:
    """Resolve the model's quoted line back to a real line of the note.

    Returns "" unless the quote matches a line that is actually present, so a
    hallucinated or paraphrased line can never reach _schedule_from_line and
    move a dose time. `claimed` holds lines already resolved by alias lookup;
    a quote landing on one of those is a misattribution and is dropped.

    Limit worth knowing: when a note writes *every* drug in a spelling ALIASES
    does not know, `claimed` is empty and nothing here can tell which unknown
    name owns which line. A misattributed schedule is still possible then. It
    lands in a draft plan that a human confirms before activate, which is the
    real backstop — this only narrows the window.
    """
    want = _collapse(quoted or "")
    if len(want) < 4:
        return ""

    for line in text.splitlines():
        have = _collapse(line)
        if len(have) < 4 or not (want in have or have in want):
            continue
        # Containment, not equality: `claimed` holds per-drug *segments*, which
        # are substrings of their line once a list marker like "2) Tab. " is
        # stripped. Comparing for equality would silently never match.
        if any(owned in have or have in owned for owned in claimed):
            return ""  # another drug already owns this line by alias — drop it
        return line
    return ""


def _locate_line(text: str, normalized: str) -> str:
    """This drug's own span of the note, under any alias we know. "" if unknown.

    Same segmentation as the deterministic path, so a prose note cannot give one
    drug another's schedule just because Sarvam was the one that named it.
    """
    positions = _drug_positions(text)
    idx = positions.get(normalized)
    return _segment_at(text, idx, positions) if idx is not None else ""


def _parse_json_block(content: str) -> Any:
    content = (content or "").strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", content, re.DOTALL)
    if fenced:
        content = fenced.group(1).strip()
    start, end = content.find("{"), content.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in model output")
    return json.loads(content[start : end + 1])


# ------------------------------------------------------------------ assembling


def _to_medication(item: dict, source: str) -> Medication:
    """Formulary row + whatever the source line overrides. Identical for both paths."""
    base = dict(formulary_by_name()[item["name_normalized"]])
    base["source"] = source

    line = item.get("line") or ""
    if line:
        base = _schedule_from_line(line, base)

    return Medication(**base)


# --------------------------------------------------------------------- Doc AI


def extract_from_document(file_bytes: bytes, filename: str, content_type: str) -> list[Medication]:
    """Photo/PDF of a discharge note -> draft medications, via Sarvam Doc AI.

    The rows Doc AI returns are used as they come back: its `name` picks the
    formulary row, and its `schedule` string is read for times and food rule.
    The note is never reconstructed and re-parsed — what the OCR reports is what
    this path acts on.

    Doc AI still cannot introduce a drug: `name` only ever selects a row from
    fixtures/formulary.json, and dose, unit, route and criticality come from
    that row. A name that matches nothing is dropped and logged.
    """
    result = sarvam.doc_ai_extract(file_bytes, filename, content_type, _DOC_SCHEMA)
    rows = _pluck_medications(result)
    if not rows:
        logger.warning("extract(ocr): Doc AI returned no medication rows")
        return []

    known = formulary_by_name()
    medications: list[Medication] = []
    seen: set[str] = set()
    dropped: list[str] = []

    for row in rows:
        if not isinstance(row, dict):
            continue
        raw_name = str(row.get("name") or "").strip()
        normalized = _normalize_drug_name(raw_name)
        if normalized is None:
            if raw_name:
                dropped.append(raw_name)
            continue
        if normalized in seen:
            continue
        seen.add(normalized)

        base = dict(known[normalized])
        base["source"] = "ocr"
        # Same reader the paste path uses, pointed at Doc AI's own schedule
        # string instead of a line of the note.
        schedule = str(row.get("schedule") or "").strip()
        if schedule:
            base = _schedule_from_line(schedule, base)
        medications.append(Medication(**base))

    logger.info(
        "extract(ocr): %d row(s) -> %d med(s): %s%s",
        len(rows),
        len(medications),
        ", ".join(m.name_normalized for m in medications) or "-",
        f" | not in formulary, dropped: {', '.join(dropped)}" if dropped else "",
    )
    return medications


def _normalize_drug_name(raw_name: str) -> str | None:
    """Doc AI's drug name -> a formulary key, or None if it names nothing we stock.

    Doc AI returns the name as written ("Tab. Amlodipine 5 mg"), so an exact
    lookup misses. Alias substrings are matched longest-first: "amlodipine"
    must win over a shorter alias that happens to be contained in it.
    """
    low = (raw_name or "").lower()
    if not low:
        return None
    known = formulary_by_name()
    for alias in sorted(ALIASES, key=len, reverse=True):
        if alias.lower() in low:
            normalized = ALIASES[alias]
            if normalized in known:
                return normalized
    return None


_DOC_SCHEMA = {
    "type": "object",
    "properties": {
        "medications": {
            "type": "array",
            "description": "Every medication listed in the discharge/prescription document",
            "items": {
                "type": "object",
                "description": "One medication entry",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Drug name exactly as written, with strength if present",
                    },
                    "dose": {
                        "type": "string",
                        "description": "Dose amount and unit, e.g. '5 mg'",
                    },
                    "schedule": {
                        "type": "string",
                        "description": (
                            "When and how to take it, copied as written — e.g. "
                            "'raat ko', 'subah aur raat, khane ke baad', 'SOS'"
                        ),
                    },
                },
            },
        }
    },
}


def _pluck_medications(body: dict) -> list:
    """Dig the medication array out of Doc AI's result envelope.

    The payload has been seen as both `result` and `results`, and as either a
    dict or a single-element list wrapping one.
    """
    result = body.get("result") or body.get("results") or {}
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except ValueError:
            return []
    if isinstance(result, list):
        if not result or not isinstance(result[0], dict):
            return []
        result = result[0].get("result", result[0])
    if isinstance(result, dict):
        meds = result.get("medications")
        if isinstance(meds, list):
            return meds
    return []
