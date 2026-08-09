"""Discharge text -> draft medications.

Two paths that both end in the same place:

1. Deterministic parse of the text against fixtures/formulary.json (default).
2. Sarvam LLM, used only when the deterministic parse finds nothing — it reads
   spellings and phrasings the alias table does not know.

The LLM only ever answers *which drugs are in this note*. Dose, times, duration
and criticality come from the locked formulary plus the source line, never from
the model — a model that reads "7 din baad OPD review" as a 7-day course would
otherwise corrupt the med graph. See EXTRACT_MODE in config.py.

Neither path can invent a drug outside fixtures/formulary.json, and everything
returned is a draft a human still has to confirm before activate.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ..config import (
    EXTRACT_MODE,
    SARVAM_API_BASE,
    SARVAM_API_KEY,
    SARVAM_MODEL,
    SARVAM_TIMEOUT_SECONDS,
)
from ..models.schemas import Medication
from .fixtures import formulary_by_name, load_formulary

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
NIGHT_HINTS = ("raat", "night", "रात", "hs", "bedtime", "evening", "sham")
FOOD_HINTS = ("khane ke saath", "with food", "after food", "khana", "pc", "भोजन", "खाने")
SOS_HINTS = ("sos", "if needed", "bukhar", "prn", "जरूरत")

MORNING_TIME = "08:00"
NIGHT_TIME = "21:00"


def extract_medications(text: str, source: str = "paste") -> list[Medication]:
    """Best available extraction. Never raises on LLM failure."""
    hits: list[dict] = []

    if EXTRACT_MODE != "llm":
        hits = _extract_via_formulary(text)

    if not hits and EXTRACT_MODE != "deterministic" and SARVAM_API_KEY:
        hits = _extract_via_sarvam(text) or []

    if not hits and EXTRACT_MODE == "llm":
        hits = _extract_via_formulary(text)

    return [_to_medication(item, source) for item in hits]


# ---------------------------------------------------------------- deterministic


def _extract_via_formulary(text: str) -> list[dict]:
    """Scan the text for known formulary drugs and read their schedule off the line."""
    lowered = text.lower()
    hits: list[tuple[int, dict]] = []
    seen: set[str] = set()

    for alias, normalized in ALIASES.items():
        idx = lowered.find(alias.lower())
        if idx == -1 or normalized in seen:
            continue
        seen.add(normalized)
        line = _line_at(text, idx)
        hits.append((idx, {"name_normalized": normalized, "line": line}))

    hits.sort(key=lambda pair: pair[0])
    return [item for _, item in hits]


def _line_at(text: str, index: int) -> str:
    start = text.rfind("\n", 0, index) + 1
    end = text.find("\n", index)
    if end == -1:
        end = len(text)
    return text[start:end]


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
    if _has_hint(low, FOOD_HINTS):
        out["food_rule"] = "with_food"
        if out["schedule_text"] and "food" not in out["schedule_text"].lower():
            out["schedule_text"] = f"{out['schedule_text']} with food"
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
        'Reply with JSON only: {"medications": [{"name_normalized": str}]}\n\n'
        f"NOTE:\n{text}"
    )
    try:
        import httpx

        response = httpx.post(
            f"{SARVAM_API_BASE}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {SARVAM_API_KEY}",
                "api-subscription-key": SARVAM_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "model": SARVAM_MODEL,
                "temperature": 0,
                "messages": [
                    {
                        "role": "system",
                        "content": "You extract medication names. You output JSON only.",
                    },
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=SARVAM_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        message = response.json()["choices"][0]["message"]
        # Reasoning models sometimes leave `content` null and put the answer in
        # `reasoning_content`.
        content = message.get("content") or message.get("reasoning_content") or ""
        parsed = _parse_json_block(content)
        items = parsed.get("medications") if isinstance(parsed, dict) else None
        if not items:
            return None
    except Exception:  # network, auth, shape drift — fall back silently
        return None

    known = formulary_by_name()
    cleaned: list[dict] = []
    for item in items:
        name = item.get("name_normalized") if isinstance(item, dict) else item
        name = str(name or "").strip().lower()
        name = ALIASES.get(name, name)
        if name not in known or any(c["name_normalized"] == name for c in cleaned):
            continue  # outside the locked formulary -> dropped, not invented
        # Schedule still comes off the source line, exactly like the local path.
        cleaned.append({"name_normalized": name, "line": _locate_line(text, name)})
    return cleaned or None


def _locate_line(text: str, normalized: str) -> str:
    """Earliest line in the note mentioning this drug under any known alias."""
    lowered = text.lower()
    best = -1
    for alias, canonical in ALIASES.items():
        if canonical != normalized:
            continue
        idx = lowered.find(alias.lower())
        if idx != -1 and (best == -1 or idx < best):
            best = idx
    return _line_at(text, best) if best != -1 else ""


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
