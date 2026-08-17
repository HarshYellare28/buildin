"""Deterministic policy kernel.

Plain functions, no model calls. Every decision here must be reproducible from
its arguments alone.

| Intent / event        | Autonomous action     | Escalate |
| Confirmed taken       | Log                   | No       |
| Side effect reported  | Log + caregiver packet| Yes      |
| Double dose request   | Refuse                | Yes      |
| Stop high-critical med| Refuse silent stop    | Yes      |
| Invent new Rx         | Refuse                | Yes      |
"""

from __future__ import annotations

from dataclasses import dataclass, field

ACTION_LOG = "log"
ACTION_ESCALATE = "escalate_caregiver"

# Intent vocabulary -> canonical intent. Unknown intents are refused by default.
INTENT_ALIASES = {
    "double_dose": "double_dose",
    "double": "double_dose",
    "take_extra_dose": "double_dose",
    "extra_dose": "double_dose",
    "invent_rx": "invent_rx",
    "new_prescription": "invent_rx",
    "add_medication": "invent_rx",
    "prescribe": "invent_rx",
    "stop_medication": "stop_medication",
    "silent_stop": "stop_medication",
    "stop_med": "stop_medication",
    "skip_dose": "skip_dose",
    "log_symptom": "log_symptom",
    "report_side_effect": "log_symptom",
    "confirm_taken": "confirm_taken",
    "escalate_caregiver": "escalate_caregiver",
}


@dataclass
class PolicyDecision:
    allowed: bool
    actions: list[str] = field(default_factory=list)
    refused: list[str] = field(default_factory=list)
    reason: str = ""
    must_escalate: bool = False
    needs_clinician: bool = False

    def as_policy_result(self) -> dict:
        return {"allowed": self.allowed, "actions": self.actions, "refused": self.refused}


def normalize_intent(intent: str | None) -> str:
    if not intent:
        return "unknown"
    return INTENT_ALIASES.get(intent.strip().lower(), "unknown")


def check_intent(intent: str | None, criticality: str | None = None) -> PolicyDecision:
    """Answers 'may the system do X?'. Default deny for anything unrecognised."""
    canonical = normalize_intent(intent)
    crit = (criticality or "med").lower()

    if canonical == "double_dose":
        if crit == "high":
            reason = "Cannot double high-criticality medication"
        else:
            reason = "Cannot double a prescribed dose without clinician approval"
        return PolicyDecision(
            allowed=False,
            actions=[ACTION_LOG, ACTION_ESCALATE],
            refused=["double_dose"],
            reason=reason,
            must_escalate=True,
        )

    if canonical == "invent_rx":
        return PolicyDecision(
            allowed=False,
            actions=[ACTION_LOG, ACTION_ESCALATE],
            refused=["invent_rx"],
            reason="Cannot start a new medication; only a clinician can prescribe",
            must_escalate=True,
        )

    if canonical == "stop_medication":
        if crit == "high":
            reason = "Cannot stop a high-criticality medication without clinician approval"
        else:
            reason = "Cannot stop a prescribed medication without clinician approval"
        return PolicyDecision(
            allowed=False,
            actions=[ACTION_LOG, ACTION_ESCALATE],
            refused=["stop_medication"],
            reason=reason,
            must_escalate=True,
        )

    if canonical == "skip_dose":
        return PolicyDecision(
            allowed=False,
            actions=[ACTION_LOG, ACTION_ESCALATE],
            refused=["skip_dose"],
            reason="Cannot approve skipping a prescribed dose; caregiver will be informed",
            must_escalate=True,
        )

    if canonical in ("log_symptom", "escalate_caregiver"):
        return PolicyDecision(
            allowed=True,
            actions=[ACTION_LOG, ACTION_ESCALATE],
            reason="Symptom logged and caregiver informed",
            must_escalate=True,
        )

    if canonical == "confirm_taken":
        return PolicyDecision(
            allowed=True,
            actions=[ACTION_LOG],
            reason="Adherence logged",
            must_escalate=False,
        )

    return PolicyDecision(
        allowed=False,
        actions=[ACTION_LOG, ACTION_ESCALATE],
        refused=[canonical if canonical != "unknown" else str(intent)],
        reason="Unrecognised intent; refusing by default and escalating to caregiver",
        must_escalate=True,
    )


def evaluate_completion(
    adherence: str,
    exception_type: str = "none",
    criticality: str = "med",
    confidence: float = 1.0,
) -> PolicyDecision:
    """Decides what the system does when a dose session ends."""
    exception_type = (exception_type or "none").lower()
    crit = (criticality or "med").lower()

    escalating_exceptions = {"side_effect", "missed_dose", "refused", "confusion", "other"}
    escalate = exception_type in escalating_exceptions or adherence in ("missed", "partial")

    # Contract example for the side-effect path is exactly ["log", "escalate_caregiver"].
    # The caregiver packet is the concrete form escalation takes; it is not a third action.
    actions = [ACTION_LOG]
    if escalate:
        actions.append(ACTION_ESCALATE)

    # High-criticality meds are never "made up for" by doubling later.
    refused: list[str] = []
    if exception_type == "missed_dose" and crit == "high":
        refused.append("double_dose")

    needs_clinician = confidence < 0.5 or (adherence == "missed" and crit == "high")

    return PolicyDecision(
        allowed=True,
        actions=actions,
        refused=refused,
        reason="Side effect reported; logged and escalated"
        if exception_type == "side_effect"
        else "Dose outcome logged",
        must_escalate=escalate,
        needs_clinician=needs_clinician,
    )
