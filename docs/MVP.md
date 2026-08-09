# DAWA — 8-hour MVP freeze

This file is the scope law.
If it is not listed under **SHIP**, do not build it before E2E is green twice.

---

## Win condition

```text
Paste Rx → extract draft meds → human confirm → activate plan
  → jump clock to evening dose
  → live Indic voice dose session
  → patient: taken + side effect ("pet mein jalan")
  → policy: log + escalate (no new Rx, no silent stop)
  → caregiver English card appears from API
  → event ledger shows full trail
```

Without hand-editing the caregiver card.

---

## SHIP (must work live)

| ID | Feature | Owner | Notes |
| --- | --- | --- | --- |
| M1 | Paste Rx / discharge text ingest | Harsh UI + Barkha API | Photo optional later |
| M2 | Extract 3–5 meds into draft med graph | Barkha (+ Sarvam LLM) | Fixed demo formulary |
| M3 | Human confirm + activate | Harsh + Barkha | Block activate until confirm |
| M4 | One patient + one caregiver | Barkha seed + Harsh display | Pre-seeded OK |
| M5 | Demo clock / jump to evening dose | Harsh trigger + Barkha endpoint | Real cron not required |
| M6 | Live dose voice (in-app OK) | Jyotir | STT + TTS must be **real** |
| M7 | Conversational adherence (taken path) | Jyotir + Barkha complete API | Not a tap-only app |
| M8 | One exception: side effect | Jyotir dialogue + Barkha policy | Acidity only |
| M9 | Thin policy kernel | Barkha | Refuse double dose, no invent Rx, escalate SE |
| M10 | Caregiver structured packet (EN) | Barkha generate + Harsh render | From API JSON |
| M11 | Event ledger timeline | Barkha store + Harsh render | Immutable append-only list |

---

## CUT (not day-1)

- Clinician summary page
- Real PSTN / Exotel / Twilio
- Second caregiver
- Refill + Razorpay
- Drug interaction DB (unless 5 hardcoded lines free)
- Blister-strip photo
- WhatsApp channel
- Multi-day scrubber
- Spoken clarification on ingest (unless voice loop already solid)
- Full exception taxonomy (confusion, refusal, brand sub as first-class)
- Med graph version history beyond single active plan

---

## STRETCH (only after two clean E2E runs)

1. Clinician 1-page summary from ledger
2. Photo Rx path with low-confidence highlights
3. Refuse double-dose live in voice
4. Tiny food-rule / interaction note on allowlist
5. WhatsApp or Razorpay theatre

---

## Locked demo formulary

Use only these (names may localize; count stays small):

| Med | Schedule | Criticality | Demo role |
| --- | --- | --- | --- |
| Amlodipine 5mg | Night | high | Dose call focus; do not double |
| Metformin 500mg | Morning + night with food | med | Food rule visible on graph |
| Atorvastatin 10mg | Night | med | Background |
| Paracetamol 500mg | SOS | low | Optional 4th |

Exception story: after evening Amlodipine confirm, patient reports **pet mein jalan** (abdominal burning).

Languages locked:

- Patient: Hindi (or Kannada if team is stronger — pick one and freeze)
- Caregiver: English

---

## Definition of done (team)

- [ ] `./scripts/demo-reset.sh` restores a clean world
- [ ] Paste fixture discharge → draft meds appear
- [ ] Confirm + activate works
- [ ] Jump to evening dose starts voice session
- [ ] Live STT/TTS exchange completes
- [ ] Complete endpoint writes taken + side_effect
- [ ] Caregiver card loads from API (not hardcoded UI string for the outcome)
- [ ] Ledger lists activate → call → taken → escalated → packet
- [ ] Policy refuses “should I double dose?” if exercised
- [ ] Full path rehearsed **twice** without puppeting

---

## What is real vs mocked

| Component | Status |
| --- | --- |
| Sarvam STT | REAL |
| Sarvam TTS | REAL |
| Med graph source of truth | REAL |
| Human confirm | REAL |
| Exception → caregiver packet | REAL |
| Policy kernel | REAL (simple rules) |
| PSTN phone network | MOCK / skip |
| Full pharmacy / EHR | MOCK |
| Exhaustive drug DB | MOCK (formulary only) |

---

## Explicit non-goals

- Diagnosis
- Autonomous prescription changes
- Ambient always-on mic
- Legal medical device claims
- Full Indian formulary
