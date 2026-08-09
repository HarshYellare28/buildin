"""Every sentence the agent speaks. Nothing here is model-generated.

Lines follow docs/DEMO_SCRIPT.md (Arnav owns the wording — this is the only file to edit).
One deliberate deviation: the script's "Raat ki BP dawai" is generalised to "{when} ki dawai"
so the greeting stays correct if the dose is triggered on a non-BP medication.
"""

GREET_DOSE = (
    "Namaste {patient} ji. {when} ki dawai {med} lene ka samay ho gaya hai. "
    "Kya aapne dawai le li?"
)

REASK_TAKEN = "Maaf kijiye, main theek se sun nahi payi. Kya aapne {med} le li? Haan ya nahi."

ASK_SYMPTOM = "Theek hai. Kya aapko koi takleef ya pareshani ho rahi hai?"

READBACK_SIDE_EFFECT = (
    "Samajh gayi. Aapne {med} le li, aur {reported} batayi. "
    "Main yeh baat {caregiver} ko bhej rahi hoon. Kripya dohra mat lena. "
    "Agar takleef badhe ya ulti ho to clinic se baat karein."
)

READBACK_TAKEN = "Samajh gayi. Aapne {med} le li. Bahut achha, apna khyal rakhiye."

READBACK_MISSED = (
    "Samajh gayi, abhi tak {med} nahi li. Main {caregiver} ko bata rahi hoon. "
    "Kripya apne aap do dawai ek saath mat lena."
)

REFUSE_DOUBLE = (
    "Nahi, kripya do tablet ek saath mat lijiye. Main {caregiver} ko abhi bata rahi hoon. "
    "Agar zaroorat ho to clinic se salah lijiye."
)

NEEDS_HUMAN = (
    "Maaf kijiye, main samajh nahi pa rahi. Main {caregiver} ko bata rahi hoon, "
    "woh aapse baat karengi."
)


CLASSIFIER_SYSTEM = """You are a classifier inside a medication execution system. You are NOT a doctor.
You never give medical advice, never suggest medicines, and never decide clinical actions.

You receive one utterance from an elderly Hindi-speaking patient during a dose-time call about a
single medication. Return JSON only, matching the schema.

Rules:
- adherence: "taken" if they say they took it, "missed" if not taken, "partial" if part of the
  dose, "unclear" if you cannot tell. Do not guess when genuinely ambiguous.
- exception_type: "side_effect" only when the patient reports a physical complaint.
- patient_reported: copy the patient's own words for the complaint, verbatim. Do not translate,
  do not paraphrase. Empty string if no complaint.
- normalized_symptom: snake_case English, e.g. abdominal_burning, nausea, vomiting, dizziness.
  Null if no complaint. Burning/heat in the stomach ("pet mein jalan") is abdominal_burning.
- double_dose_request: true if the patient asks about taking an extra or double dose.
- confidence: 0.0-1.0, your confidence in the adherence value.
"""

CLASSIFIER_SCHEMA = {
    "type": "object",
    "properties": {
        "adherence": {"type": "string", "enum": ["taken", "missed", "partial", "unclear"]},
        "exception_type": {
            "type": "string",
            "enum": ["none", "side_effect", "missed_dose", "confusion", "refused", "other"],
        },
        "patient_reported": {"type": "string"},
        "normalized_symptom": {"type": ["string", "null"]},
        "double_dose_request": {"type": "boolean"},
        "confidence": {"type": "number"},
    },
    "required": [
        "adherence",
        "exception_type",
        "patient_reported",
        "normalized_symptom",
        "double_dose_request",
        "confidence",
    ],
    "additionalProperties": False,
}
