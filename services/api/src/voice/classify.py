"""Transcript -> structured outcome.

Two layers, deliberately in this order:
  1. Regex over Latin *and* Devanagari. Deterministic, ~0ms, works if Sarvam's LLM is down.
  2. LLM refinement (strict JSON schema). Fills gaps and normalises the symptom.

Layer 1 is authoritative for anything safety-relevant; layer 2 can only fill unknowns or raise a
refusal flag, never clear one. A demo that survives a flaky LLM is worth more than a nuanced one.
"""

import re
from dataclasses import dataclass, field

from . import prompts
from .config import settings
from .sarvam_client import SarvamError, classify_json

_TAKE_VERB = re.compile(
    r"le\s*li|le\s*liya|leli|li\s*hai|liya|kha\s*li|kha\s*liya|khali|"
    r"ले\s*ली|ले\s*लिया|ली\s*है|खा\s*ली|खा\s*लिया|लिया|ली",
    re.IGNORECASE,
)
_AFFIRM = re.compile(r"\bhaan\b|\bhan\b|\bha\b|\bji\b|\byes\b|हाँ|हां|जी", re.IGNORECASE)
_NEGATION = re.compile(
    r"\bnahi+n?\b|\bnai\b|\bnot\b|\bno\b|bhool|bhul|नहीं|नही|भूल|नहि", re.IGNORECASE
)
_NEG_TAKE = re.compile(
    r"(nahi+n?|nai|bhool\s*gay\w*|bhul\s*gay\w*|नहीं|नही|भूल\s*गय\w*)\s*\S{0,10}\s*"
    r"(li|liya|ली|लिया|khai|खाई)?",
    re.IGNORECASE,
)

_SIDE_EFFECT = re.compile(
    r"jalan|jal\s*rah|jalna|acidity|ulti|ultee|dard|takleef|takliif|pareshani|chakkar|matli|"
    r"pet\s*(kharab|mein|me)|"
    r"जलन|जल\s*रह|उल्टी|दर्द|तकलीफ|परेशानी|चक्कर|मतली|पेट",
    re.IGNORECASE,
)
_DOUBLE_DOSE = re.compile(
    r"do\s*(tablet|goli|gol[ei]|dawai|dose)|double|ek\s*aur|dobara|do\s*baar|two\s*tablet|"
    r"दो\s*(गोली|टैबलेट|दवाई)|एक\s*और|दोबारा",
    re.IGNORECASE,
)

_SYMPTOM_MAP: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"jalan|jal\s*rah|jalna|acidity|जलन|जल\s*रह", re.IGNORECASE), "abdominal_burning"),
    (re.compile(r"ulti|ultee|उल्टी", re.IGNORECASE), "vomiting"),
    (re.compile(r"matli|मतली|nausea", re.IGNORECASE), "nausea"),
    (re.compile(r"chakkar|चक्कर", re.IGNORECASE), "dizziness"),
    (re.compile(r"pet\s*(mein|me|kharab)|पेट|dard|दर्द", re.IGNORECASE), "abdominal_pain"),
]


@dataclass
class Classification:
    adherence: str = "unclear"  # taken | missed | partial | unclear ("unclear" never leaves this module)
    exception_type: str = "none"
    patient_reported: str = ""
    normalized_symptom: str | None = None
    double_dose_request: bool = False
    confidence: float = 0.0
    source: str = "regex"
    notes: list[str] = field(default_factory=list)

    @property
    def has_side_effect(self) -> bool:
        return self.exception_type == "side_effect"


def _normalize_symptom(text: str) -> str | None:
    for pattern, label in _SYMPTOM_MAP:
        if pattern.search(text):
            return label
    return None


def classify_regex(text: str) -> Classification:
    result = Classification()
    if not text.strip():
        return result

    if _DOUBLE_DOSE.search(text):
        result.double_dose_request = True

    has_take_verb = bool(_TAKE_VERB.search(text))
    negated_take = bool(_NEG_TAKE.search(text))
    if negated_take and not has_take_verb:
        result.adherence = "missed"
        result.confidence = 0.8
    elif has_take_verb and not negated_take:
        result.adherence = "taken"
        result.confidence = 0.85
    elif _AFFIRM.search(text) and not _NEGATION.search(text):
        result.adherence = "taken"
        result.confidence = 0.7
    elif _NEGATION.search(text):
        result.adherence = "missed"
        result.confidence = 0.7

    if _SIDE_EFFECT.search(text):
        result.exception_type = "side_effect"
        result.patient_reported = text.strip()
        result.normalized_symptom = _normalize_symptom(text)

    return result


def classify(text: str) -> Classification:
    """Regex first, then optional LLM refinement. Never raises — the call must go on."""
    result = classify_regex(text)
    if not settings.llm_classify_enabled or not text.strip() or not settings.configured:
        return result

    try:
        llm = classify_json(prompts.CLASSIFIER_SYSTEM, text, prompts.CLASSIFIER_SCHEMA)
    except (SarvamError, KeyError, IndexError) as exc:
        result.notes.append(f"llm_classify_failed: {exc}")
        return result

    result.source = "regex+llm"

    if result.adherence == "unclear" and llm.get("adherence") in ("taken", "missed", "partial"):
        result.adherence = llm["adherence"]

    if result.exception_type == "none" and llm.get("exception_type") == "side_effect":
        result.exception_type = "side_effect"
        result.patient_reported = llm.get("patient_reported") or text.strip()

    if result.has_side_effect:
        result.normalized_symptom = result.normalized_symptom or llm.get("normalized_symptom")
        result.patient_reported = result.patient_reported or text.strip()

    # A refusal flag can be raised by either layer, never cleared by the model.
    result.double_dose_request = result.double_dose_request or bool(llm.get("double_dose_request"))

    llm_confidence = llm.get("confidence")
    if isinstance(llm_confidence, (int, float)) and result.adherence != "unclear":
        result.confidence = max(0.5, min(1.0, float(llm_confidence)))

    return result
