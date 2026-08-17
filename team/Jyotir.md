# Jyotir — Voice (Sarvam STT → policy LLM → TTS)

**Role:** Person B — live dose session  
**You own the centrepiece of the demo.** If voice is fake, the product looks like a form.

---

## Read first

1. [docs/MVP.md](../docs/MVP.md) — M6, M7, M8
2. [docs/DEMO_SCRIPT.md](../docs/DEMO_SCRIPT.md) — exact Hindi lines
3. [docs/API_CONTRACT.md](../docs/API_CONTRACT.md) — complete payload
4. [docs/WIN_LOSE_TEST.md](../docs/WIN_LOSE_TEST.md)
5. [docs/GIT_AND_AGENTS.md](../docs/GIT_AND_AGENTS.md)

---

## You own (edit freely)

```text
services/api/src/voice/**
```

## You may edit with agreement

```text
cockpit/**           # caregiver call status only; never add a patient mic UI
services/api/src/routes/doses.py   # only if adding voice-turn route with Barkha
```

## You do not own

- Med graph extract/activate (Barkha)
- Full cockpit layout (Harsh)
- Product docs (Arnav)

**Rule:** You may classify adherence/exception from dialogue, but **Barkha’s** `POST /doses/{id}/complete` is the write path. Do not keep a parallel “voice database.”

---

## Branch + where to push

| Item | Value |
| --- | --- |
| Branch | `feat/voice` |
| Primary paths | `services/api/src/voice/**` |
| UI mic bits | same PR or tiny PR into `feat/web` with Harsh ack |

```bash
git checkout main && git pull
git checkout -b feat/voice
# work...
git add services/api/src/voice
git commit -m "feat(voice): hindi dose loop with complete payload"
git push -u origin feat/voice
```

---

## MVP IDs you ship

| ID | Deliverable |
| --- | --- |
| M6 | Live in-app dose call: Saaras STT + Bulbul TTS (real) |
| M7 | Conversational confirm taken (not only tap) |
| M8 | Capture side effect phrase → map to `side_effect` |
| M9 assist | On “double dose?” → refuse language + call policy/check if available |

Stretch only after E2E: fancy barge-in, speaker diarization, PSTN.

---

## Dialogue state machine (keep tiny)

```text
GREET_DOSE
  → ASK_TAKEN
  → (if taken) ASK_FEELING / WAIT_SYMPTOM
  → CONFIRM_READBACK
  → CALL_COMPLETE_API
  → END_ESCALATED
```

Hard rails:

- Read back med name + dose once.
- Never invent a new drug.
- Never tell patient to stop high-critical med on their own.
- Side effect → empathy + “I will tell caregiver” + complete API.

---

## Target modules

```text
services/api/src/voice/
├── README.md
├── sarvam_client.py      # STT + TTS wrappers
├── dialogue.py           # state machine + policy-bound prompts
├── classify.py           # map transcript → adherence + exception
└── session.py            # dose_id, turns, ready_for_complete
```

Web options (pick one with Harsh in hour 0):

**A (recommended):** Browser captures audio → your API endpoint → STT/TTS → return text/audio  
**B:** Browser calls Sarvam directly → then POST complete to Barkha  

Either is fine if keys stay server-side when possible.

---

## Complete payload you must produce

```json
{
  "adherence": "taken",
  "exception_type": "side_effect",
  "patient_reported": "pet mein jalan",
  "normalized_symptom": "abdominal_burning",
  "transcript_summary": "Patient confirmed Amlodipine taken; reported burning in stomach.",
  "confidence": 0.86
}
```

Map Hindi variants: “le li”, “haan le liya”, “jalan”, “pet jal raha”, etc.

---

## Hour-by-hour plan

### Hour 0–1

- [ ] Sarvam key works (curl or tiny script)
- [ ] STT one utterance
- [ ] TTS one sentence playable
- [ ] Agree with Harsh: where the mic button lives

### Hour 1–3

- [ ] Full GREET→ASK_TAKEN loop in isolation (CLI or blank page)
- [ ] Classifier for taken + side_effect
- [ ] No dependency on perfect UI yet

### Hour 3–5

- [ ] Wire to `dose_id` from trigger
- [ ] On end → POST complete
- [ ] Confirm packet appears (Harsh panel or curl)

### Hour 5–7

- [ ] Read-back + refuse double dose line
- [ ] Retry on STT miss
- [ ] Latency trim

### Hour 7–8

- [ ] Rehearse with Arnav as operator
- [ ] Disaster: typed fallback to complete (hidden, not default)

---

## Agent system plan (paste this whole block)

```text
You are Jyotir's coding agent for DAWA voice.

MISSION
Build a reliable live dose-time voice loop in Hindi using Sarvam STT/TTS, then write outcomes through Barkha's complete API.

OWNED PATHS
- services/api/src/voice/**
- Caregiver call status only under `cockpit/`; the patient never gets a web mic/session UI

READ FIRST
- docs/DEMO_SCRIPT.md
- docs/API_CONTRACT.md (complete + optional voice-turn)
- docs/MVP.md M6–M8
- fixtures/formulary.json (amlodipine is the call focus)

HARD RULES
1. STT and TTS must be real Sarvam calls for the demo path.
2. Do not invent prescriptions or tell patient to stop cardiac meds.
3. One happy path: taken + side_effect (pet mein jalan).
4. Final state write = POST /doses/{dose_id}/complete only.
5. Do not create a second event store.
6. Do not build PSTN, WhatsApp, or multi-speaker diarization.
7. Keep dialogue state machine under ~5 states.
8. Never commit API keys.
9. Prefer server-side key usage.
10. If UI is blocked, ship a CLI or minimal HTML mic page under voice/ for integration testing.

PROMPTS / POLICY
- System prompt must say: you are a medication execution assistant, not a doctor.
- On side effect: log + inform caregiver; do not prescribe.
- On double dose: refuse; suggest caregiver/clinic path.

DONE CHECK
- Live mic: user says taken + jalan → complete payload correct → packet exists via API.
- Rehearsed twice.
```

---

## How you test

| Level | Test | Pass |
| --- | --- | --- |
| L0 | STT of “haan le li” | text contains haan/le |
| L0 | TTS plays | audible Hindi |
| L1 | Full dialogue alone | reaches END |
| L2 | With API dose_id | complete 200 |
| L3 | Full demo path | card + ledger update |
| Chaos | mumble | asks to repeat once |
| Chaos | “do tablet le lu?” | refuse, no complete as taken-double |

Do not rely only on recorded audio for the judged demo.
Recording is disaster recovery only.

---

## Merge checklist

- [ ] Voice module isolated
- [ ] Env vars documented in `services/api` README or voice README
- [ ] Complete payload matches contract
- [ ] No secrets in repo
- [ ] Harsh knows which button starts the session

---

## What wins / loses (your lens)

**Win:** Judges hear a real patient conversation and see the English card update.

**Lose:** Pre-recorded theatre only; model gives medical advice; you never call complete; latency &gt; 8s every turn with no feedback.

---

## Coordination

| Person | You need |
| --- | --- |
| Barkha | Working trigger + complete; CORS; dose_id |
| Harsh | Mic button, session state, maybe audio element |
| Arnav | Final Hindi lines; rehearsal schedule; keys |

---

## Explicit do-not list

- Do not expand to full symptom diagnosis.
- Do not add English-only patient path as primary.
- Do not block on perfect accent robustness for all of India — nail the demo lines.
- Do not rewrite Barkha’s policy kernel in the LLM prompt as the only safety (prompt + kernel).
