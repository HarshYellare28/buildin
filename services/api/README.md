# DAWA API (Barkha + Jyotir voice module)

FastAPI + SQLite. System of record for plans, doses, policy, events, packets.

## Owner

- **Barkha:** routes, models, policy, ledger, packets, extract
- **Jyotir:** `src/voice/**` — mounted at `/voice/*`

## Contract

Implements [docs/API_CONTRACT.md](../../docs/API_CONTRACT.md) exactly.

## Run

```bash
cd services/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill SARVAM_API_KEY
uvicorn src.main:app --reload --port 8000
```

DB is a SQLite file at `data/local/dawa.db` (repo-root relative, gitignored).
Delete it any time; it is recreated on boot. CORS is open for any
`localhost` / `127.0.0.1` port.

## Smoke + tests

```bash
# from repo root, with API up
./scripts/demo-reset.sh
./scripts/smoke-api.sh

# unit + contract tests (no server needed, never hits the network)
cd services/api && .venv/bin/python -m pytest -q

# 50 Hinglish cases against a running API (real Sarvam calls, ~5 min)
services/api/.venv/bin/python scripts/hinglish-suite.py
services/api/.venv/bin/python scripts/hinglish-suite.py --only 17,40

# is the Sarvam key actually live? chat + STT + TTS + extract
services/api/.venv/bin/python scripts/verify-sarvam.py
```

`hinglish-suite.py` reports `PASS` / `FAIL` / `GAP`, where GAP means the
contract has no such field — currently: no `quantity` on `Medication`,
`duration_days` comes from the formulary rather than the note, and
`/doses/trigger` has no in-flight duplicate guard.

## Endpoints

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/health` | `{"ok": true}` |
| GET | `/people` | seeded patient + caregiver |
| POST | `/plans/extract` | `{text, source}` → draft plan + medications + follow-up |
| GET | `/plans/{plan_id}` | full plan |
| PATCH | `/plans/{plan_id}` | `{medications, follow_up?}`, draft only |
| POST | `/plans/{plan_id}/activate` | human-confirmed → `active` |
| POST | `/doses/trigger` | `{plan_id, medication_id?, simulate_time}` |
| POST | `/doses/{dose_id}/voice-turn` | optional server dialogue turn (guesses only) |
| POST | `/voice/sessions` | start Jyotir's policy-bound dose dialogue |
| POST | `/voice/sessions/{id}/turn` | Sarvam STT audio turn |
| POST | `/voice/sessions/{id}/turn-text` | disaster fallback only |
| POST | `/doses/{dose_id}/complete` | **only** writer of adherence/exception/packet |
| POST | `/policy/check` | `{intent, medication_id}` |
| GET | `/events?plan_id=` | append-only ledger |
| GET | `/packets/latest?plan_id=` | caregiver card |
| POST | `/demo/reset` | clears plans/doses/events/packets, reseeds people |

Interactive docs while running: <http://localhost:8000/docs>

## For Jyotir — the only call that changes truth

```http
POST /doses/{dose_id}/complete
{
  "adherence": "taken",              // taken | missed | partial
  "exception_type": "side_effect",   // none | side_effect | missed_dose | confusion | refused | other
  "patient_reported": "pet mein jalan",
  "normalized_symptom": "abdominal_burning",
  "transcript_summary": "Patient confirmed Amlodipine taken; reported burning in stomach.",
  "confidence": 0.86
}
→ { "dose_id", "status", "policy": {allowed, actions, refused}, "packet_id", "event_ids": [...] }
```

Calling it twice on the same dose returns `409 DOSE_ALREADY_COMPLETED` — the
ledger is append-only and a dose has exactly one outcome.

`src/voice/router.py` is the real Sarvam STT/TTS and deterministic dialogue
path. `src/voice/turn.py` remains a lightweight compatibility endpoint for
older callers; it does not write outcomes.

## Sarvam

Extraction traffic goes through `src/services/sarvam.py`; the mounted voice
router keeps its stricter JSON-schema classifier in `src/voice/sarvam_client.py`.
The configured endpoints are:

| Call | Endpoint | Model env var |
| --- | --- | --- |
| `chat()` | `POST /v1/chat/completions` | `SARVAM_MODEL` = `sarvam-105b-conversations` |
| `speech_to_text()` | `POST /speech-to-text` (multipart) | `SARVAM_STT_MODEL` = `saaras:v3` |
| `text_to_speech()` | `POST /text-to-speech` (base64 wav) | `SARVAM_TTS_MODEL` = `bulbul:v3` |

`sarvam-m` is deprecated and returns 400. Every call logs model, elapsed ms and
outcome at INFO, and failures raise `SarvamError` with the upstream body — a
dead key and a never-entered code path used to look identical from outside.

Check the key end to end before blaming the code:

```bash
services/api/.venv/bin/python scripts/verify-sarvam.py
```

## Extract

The contract paste path remains JSON. Photo/PDF ingest uses multipart form data
with `source=ocr` and `file=<JPEG|PNG|PDF>`, then maps Sarvam Doc AI names onto
the locked formulary. Multipart paste is also accepted for older cockpit builds.

Sarvam first, deterministic formulary parse as backstop when it returns nothing.
Control with `EXTRACT_MODE`:

| Value | Behaviour |
| --- | --- |
| `llm` (default) | Sarvam first (~6s), formulary parse as backstop |
| `auto` | formulary parse first (~0.2s), LLM only as rescue |
| `deterministic` | never calls the LLM (what the tests pin) |

`auto` is faster but the parse matches the demo fixture outright, so a demo run
never reaches Sarvam at all. `llm` is the default so the model is genuinely on
the path; a dead key degrades to the same result the parse would have given.

The LLM only answers **which drugs are in the note**. Dose, times, duration and
criticality always come from the locked formulary plus the source line — never
from the model. (A model asked for schedules read "7 din baad OPD review" as a
7-day course and moved Amlodipine to 22:00; that class of drift can't happen
now.) It is also asked to quote each drug's source line back verbatim; the quote
is only used when our own alias table cannot find the drug, and is discarded
unless it matches a line really present in the note. Both paths snap onto the
formulary — the extractor never invents a drug outside it, and everything it
returns is a **draft** until a human activates.

Schedules are read from each drug's **own span** of its line, not the whole
line, so a prose note naming two drugs at once ("amlodipine 5mg morning ... aur
metformin 500mg morning evening") does not give amlodipine an evening dose.

## Follow-up visit

`POST /plans/extract` also reads the clinic visit off the note — "7 din baad OPD
review", "saat din baad opd aana", "review after 2 weeks" — and returns it on
the plan:

```json
"follow_up": {
  "kind": "clinic_visit",
  "raw_text": "- 7 din baad OPD review",
  "in_days": 7,
  "due_date": "2026-08-16",
  "due_at": "2026-08-16T10:00:00+05:30",
  "anchor_date": "2026-08-09",
  "source": "paste",
  "confidence": 0.9
}
```

`due_at` is the reminder anchor. The countdown starts from the note's own date
(`Date: 09/08/2026`) when it has one, otherwise today. Deterministic, like the
policy kernel — no model decides when a patient must be seen.

It is **not** a medication: it never enters the med graph and never triggers a
dose. A duration on a medicine line ("Metformin 30 din") is not picked up — the
line has to mention being seen again.

`null` when the note says nothing. Caregivers can correct it via `PATCH` (send
`follow_up` to replace, `null` to drop, omit the key to leave it alone). It also
rides the ledger: `plan_created.payload.follow_up` and
`plan_activated.payload.follow_up_due_at`, so a scheduler can read it without
re-fetching the plan.

## Policy kernel

`src/policy/kernel.py`, plain functions, no model calls.

| Situation | Result |
| --- | --- |
| taken, no exception | `log` |
| side effect | `log` + `escalate_caregiver` + caregiver packet |
| double dose (high crit) | refuse, `must_escalate: true` |
| stop med / new Rx / skip | refuse, escalate |
| unrecognised intent | refuse by default |

Refusals are filed against the active plan, so they show up in
`GET /events?plan_id=...` (the cockpit ledger), not just the global feed. Pass
`plan_id` in the body to target a specific plan.

Only formulary drugs can reach the med graph — `PATCH` rejects anything else
with `MEDICATION_NOT_IN_FORMULARY`.

## Errors

```json
{ "error": { "code": "PLAN_NOT_ACTIVE", "message": "Activate plan before triggering dose" } }
```

Codes: `PLAN_NOT_FOUND`, `PLAN_NOT_ACTIVE`, `PLAN_NOT_DRAFT`, `PLAN_EMPTY`,
`MEDICATION_NOT_FOUND`, `MEDICATION_NOT_IN_FORMULARY`, `DOSE_NOT_FOUND`,
`DOSE_ALREADY_COMPLETED`, `PACKET_NOT_FOUND`, `INVALID_REQUEST`.

## Branch

`feat/api` (Barkha), `feat/voice` (Jyotir for voice paths).
