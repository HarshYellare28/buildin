# DAWA — Features

## Core (MVP)

1. **Rx ingest** — upload a discharge sheet / prescription photo or paste text; add spoken clarification in Hindi/Kannada.
2. **Med graph extraction** — Vision + LLM pull out drug, dose, timing, food rule, duration, warnings, with per-field confidence.
3. **Human confirm step** — editable review screen; low-confidence fields flagged before the plan can be activated.
4. **Role linking** — one patient + one caregiver, each with their own language and channel.
5. **Dose scheduler** — dose windows, quiet hours, retry policy, and a demo clock to jump to the evening dose.
6. **Live dose call** — outbound voice session in the patient's language: STT → policy-bound LLM → TTS, with read-back of critical fields.
7. **Adherence verification** — conversational confirm (taken / missed / partial), not a tap.
8. **Exception classification** — side effect, missed dose, confusion, refusal, brand substitution.
9. **Policy kernel** — deterministic allow/deny between model and action: no invented prescriptions, no silent stopping of high-criticality meds, unsafe asks refused and escalated.
10. **Caregiver packet** — structured cross-language alert card: what happened, which med, confidence, suggested next steps.
11. **Event ledger** — immutable timeline of every dose event, exception, and system action.
12. **Clinician summary** — one-page delta of the episode, generated on demand.

## Stretch

- Real PSTN outbound calling
- Second caregiver with scoped permissions
- Allowlisted refill + Razorpay payment
- Small hardcoded drug-interaction table
- Blister-strip photo verification
- WhatsApp caregiver channel
- Multi-day timeline scrubber

## Out of scope

Diagnosis, autonomous prescription changes, EHR integration, ambient always-on mic, full Indian formulary coverage.
