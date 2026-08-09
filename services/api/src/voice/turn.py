"""Server-side dialogue turn — JYOTIR OWNS THIS FILE.

Barkha's route `POST /doses/{dose_id}/voice-turn` calls `handle_turn(dose, user_text)`
and returns whatever it gives back, unchanged. Keep the return shape:

    {
      "assistant_text": str,
      "audio_url": str | None,
      "partial": {"adherence_guess": ..., "exception_guess": ...},
    }

`partial` is a GUESS ONLY. Nothing here writes to the ledger. When the dialogue
is finished, POST the final outcome to:

    POST /doses/{dose_id}/complete
    {
      "adherence": "taken" | "missed" | "partial",
      "exception_type": "none" | "side_effect" | "missed_dose" | "confusion" | "refused" | "other",
      "patient_reported": "pet mein jalan",
      "normalized_symptom": "abdominal_burning",
      "transcript_summary": "...",
      "confidence": 0.86
    }

That endpoint is the only writer of adherence, exceptions and caregiver packets.

What is below is a deterministic keyword placeholder so the route works before
the Sarvam STT/LLM loop lands. Replace freely.
"""

from __future__ import annotations

TAKEN_HINTS = ("le liya", "le li", "liya", "khaya", "haan", "ha ", "yes", "taken", "ली")
MISSED_HINTS = ("nahi liya", "nahin liya", "bhool", "miss", "not taken", "no ")
SIDE_EFFECT_HINTS = ("jalan", "pet", "acidity", "burning", "ulti", "vomit", "chakkar", "जलन")
CONFUSION_HINTS = ("samajh nahi", "kaunsi", "which one", "confus", "pata nahi")

# normalized_symptom vocabulary shared with the caregiver packet copy
SYMPTOM_MAP = {
    "jalan": "abdominal_burning",
    "burning": "abdominal_burning",
    "acidity": "abdominal_burning",
    "ulti": "nausea",
    "vomit": "nausea",
    "chakkar": "dizziness",
}


def handle_turn(dose: dict, user_text: str) -> dict:
    text = (user_text or "").lower()
    med_name = dose.get("medication", {}).get("name_raw", "the medicine")

    adherence_guess = None
    if any(h in text for h in MISSED_HINTS):
        adherence_guess = "missed"
    elif any(h in text for h in TAKEN_HINTS):
        adherence_guess = "taken"

    exception_guess = "none"
    if any(h in text for h in SIDE_EFFECT_HINTS):
        exception_guess = "side_effect"
    elif any(h in text for h in CONFUSION_HINTS):
        exception_guess = "confusion"
    elif adherence_guess == "missed":
        exception_guess = "missed_dose"

    if exception_guess == "side_effect":
        assistant_text = "Theek hai, maine likh liya. Jalan tez hai ya halki?"
    elif adherence_guess == "taken":
        assistant_text = "Bahut acha. Aur koi takleef to nahi hui?"
    elif adherence_guess == "missed":
        assistant_text = "Koi baat nahi. Abhi aapke paas tablet hai?"
    else:
        assistant_text = f"Kya aapne {med_name} le li hai?"

    return {
        "assistant_text": assistant_text,
        "audio_url": None,
        "partial": {
            "adherence_guess": adherence_guess,
            "exception_guess": exception_guess,
        },
    }


def normalize_symptom(user_text: str) -> str | None:
    """Helper for the voice module when calling /complete."""
    text = (user_text or "").lower()
    for hint, normalized in SYMPTOM_MAP.items():
        if hint in text:
            return normalized
    return None
