"""Medication-aware meal support without pretending to prescribe.

The score is deliberately narrow: confirmed food-timing rules from the plan,
plus broad meal-composition signals. It never changes a dose and never infers
that a medication is clinically safe from a free-text meal description.
"""

from __future__ import annotations

import re

from .. import db
from ..models.schemas import MealCheck, MealMedicationCheck, Plan

PROTEIN = {
    "dal",
    "daal",
    "lentil",
    "lentils",
    "rajma",
    "chana",
    "beans",
    "paneer",
    "curd",
    "dahi",
    "yogurt",
    "egg",
    "eggs",
    "chicken",
    "fish",
    "tofu",
}
PRODUCE = {
    "sabzi",
    "salad",
    "vegetable",
    "vegetables",
    "fruit",
    "apple",
    "banana",
    "orange",
    "palak",
    "spinach",
    "bhindi",
    "gobi",
    "carrot",
}
STAPLE = {
    "roti",
    "chapati",
    "rice",
    "chawal",
    "oats",
    "dalia",
    "poha",
    "upma",
    "idli",
    "dosa",
    "bread",
    "khichdi",
}
SUGARY = {
    "mithai",
    "sweet",
    "sweets",
    "chocolate",
    "cake",
    "cola",
    "soda",
    "gulab",
    "jalebi",
    "biscuit",
    "biscuits",
}
FRIED_OR_SALTY = {
    "samosa",
    "pakora",
    "pakoda",
    "chips",
    "fries",
    "fried",
    "achar",
    "pickle",
}
NO_MEAL = re.compile(
    r"^\s*(?:nothing|none|did not eat|didn't eat|not eaten|kuch nahi|nahi khaya|"
    r"नहीं खाया|कुछ नहीं)\s*[.!]?\s*$",
    re.I,
)
MEAL_CONTEXT = re.compile(
    r"\b(?:ate|had|meal|food|khaya|khayi|khana|khane|khaana|khaane|"
    r"खाया|खायी|खाई|खाना|खाने)\b",
    re.I,
)


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z]+", text.lower()))


def _has(tokens: set[str], vocabulary: set[str]) -> bool:
    return bool(tokens & vocabulary)


def extract_meal_from_patient_text(patient_text: str) -> str | None:
    """Return the patient sentence that actually contains a meal answer."""
    for sentence in re.split(r"[\n.!?]+", patient_text):
        candidate = sentence.strip()
        tokens = _tokens(candidate)
        has_food = any(
            _has(tokens, vocabulary)
            for vocabulary in (PROTEIN, PRODUCE, STAPLE, SUGARY, FRIED_OR_SALTY)
        )
        if candidate and (NO_MEAL.fullmatch(candidate) or (has_food and MEAL_CONTEXT.search(candidate))):
            return candidate[:500]
    return None


def evaluate(plan: Plan, meal_text: str, source: str, dose_id: str | None = None) -> MealCheck:
    text = " ".join(meal_text.split())
    tokens = _tokens(text)
    ate = bool(text) and not bool(NO_MEAL.fullmatch(text))
    has_protein = _has(tokens, PROTEIN)
    has_produce = _has(tokens, PRODUCE)
    has_staple = _has(tokens, STAPLE)
    has_sugary = _has(tokens, SUGARY)
    has_fried_or_salty = _has(tokens, FRIED_OR_SALTY)
    has_grapefruit = "grapefruit" in tokens

    score = 40 if ate else 10
    positive: list[str] = []
    suggestions: list[str] = []

    if has_protein:
        score += 15
        positive.append("Protein source mentioned")
    else:
        suggestions.append("Add a usual protein such as dal, beans, curd, egg, paneer, or fish.")
    if has_produce:
        score += 15
        positive.append("Vegetable or fruit mentioned")
    else:
        suggestions.append("Add a vegetable or unsweetened fruit when practical.")
    if has_staple:
        score += 10
        positive.append("Meal staple mentioned")
    if ate and sum((has_protein, has_produce, has_staple)) >= 2:
        score += 10
        positive.append("More than one food group mentioned")
    if has_sugary:
        score -= 10
        suggestions.append("Keep sweets and sugary drinks smaller and pair them with a balanced meal.")
    if has_fried_or_salty:
        score -= 10
        suggestions.append("Prefer a less fried and less salty option at the next meal when possible.")

    medication_checks: list[MealMedicationCheck] = []
    with_food = [med for med in plan.medications if med.food_rule == "with_food"]
    for medication in plan.medications:
        if medication.food_rule == "with_food":
            if ate:
                status = "matched"
                note = "A meal was reported for this medicine's confirmed with-food instruction."
            else:
                status = "needs_confirmation"
                note = "The confirmed plan says with food, but no meal was reported."
        elif medication.food_rule == "none":
            status = "not_required"
            note = "No meal-timing requirement is recorded in the confirmed plan."
        else:
            status = "needs_confirmation"
            note = f"Confirm the plan instruction: {medication.food_rule}."
        medication_checks.append(
            MealMedicationCheck(
                medication_id=medication.id,
                medication=medication.name_raw,
                food_rule=medication.food_rule,
                timing_status=status,  # type: ignore[arg-type]
                note=note,
            )
        )

    if with_food:
        names = ", ".join(med.name_raw for med in with_food)
        if ate:
            score += 10
            positive.append(f"Reported meal supports the confirmed with-food timing for {names}")
        else:
            score -= 25
            suggestions.insert(
                0,
                f"{names} is marked with food. Confirm the patient has eaten; do not change or skip the dose without a clinician or pharmacist.",
            )

    if has_grapefruit and any(med.name_normalized == "atorvastatin" for med in plan.medications):
        score -= 15
        suggestions.insert(
            0,
            "Grapefruit was mentioned with atorvastatin. Check the medicine leaflet or pharmacist before having more grapefruit juice.",
        )

    score = max(0, min(100, score))
    if score >= 75:
        band = "strong"
        headline = "Meal looks supportive of the confirmed plan"
    elif score >= 50:
        band = "fair"
        headline = "Meal is workable, with room to strengthen it"
    else:
        band = "needs_attention"
        headline = "Meal timing or balance needs caregiver attention"

    return MealCheck(
        id=db.next_id("meal_", counter="meal"),
        plan_id=plan.id,
        dose_id=dose_id,
        recorded_at=db.now_iso(),
        meal_text=text,
        source=source,  # type: ignore[arg-type]
        score=score,
        band=band,
        headline=headline,
        positive_signals=positive,
        suggestions=suggestions[:4],
        medication_checks=medication_checks,
        disclaimer=(
            "Meal support score only. Follow the confirmed prescription and medicine leaflet; "
            "ask a clinician or pharmacist before changing any dose."
        ),
    )


def save(check: MealCheck) -> MealCheck:
    db.execute(
        "INSERT INTO meal_checks (id, plan_id, dose_id, created_at, data) VALUES (?, ?, ?, ?, ?)",
        (check.id, check.plan_id, check.dose_id, check.recorded_at, db.dumps(check.model_dump())),
    )
    return check


def latest(plan_id: str) -> MealCheck | None:
    row = db.query_one(
        "SELECT data FROM meal_checks WHERE plan_id = ? ORDER BY rowid DESC LIMIT 1",
        (plan_id,),
    )
    return MealCheck(**db.loads(row["data"])) if row else None


def for_dose(dose_id: str) -> MealCheck | None:
    row = db.query_one(
        "SELECT data FROM meal_checks WHERE dose_id = ? ORDER BY rowid DESC LIMIT 1",
        (dose_id,),
    )
    return MealCheck(**db.loads(row["data"])) if row else None
