# Barkha — Backend, med graph, policy, APIs

**Role:** Person C — system of record  
**Stack target:** FastAPI + SQLite (or Postgres if you already know it)  
**You own truth:** plans, doses, events, packets, policy decisions.

---

## Read first

1. [docs/MVP.md](../docs/MVP.md)
2. [docs/API_CONTRACT.md](../docs/API_CONTRACT.md) — **implement this exactly**
3. [docs/GIT_AND_AGENTS.md](../docs/GIT_AND_AGENTS.md)
4. [docs/WIN_LOSE_TEST.md](../docs/WIN_LOSE_TEST.md)
5. Fixtures: `fixtures/formulary.json`, `people.json`, `sample-care-packet.json`

---

## You own (edit freely)

```text
services/api/**
```

Except: coordinate with Jyotir on `services/api/src/voice/**`.
Prefer: you own routes/models/policy/services; Jyotir owns voice dialogue module that **calls your complete endpoint**.

## You do not own

```text
apps/web/**
docs/**            # propose changes; Arnav merges contract edits
fixtures/**        # consume; ask Arnav to change shapes
```

---

## Branch + where to push

| Item | Value |
| --- | --- |
| Branch | `feat/api` |
| Paths in PR | `services/api/**` only (ideally) |
| Merge when | smoke path green OR stubs documented |

```bash
git checkout main && git pull
git checkout -b feat/api
cd services/api
# implement...
git add services/api
git commit -m "feat(api): extract activate trigger complete packet"
git push -u origin feat/api
```

---

## MVP IDs you ship

| ID | Endpoint / module |
| --- | --- |
| M1/M2 | `POST /plans/extract` (paste text → meds; LLM or formulary-matched parse) |
| M3 | `PATCH /plans/{id}`, `POST /plans/{id}/activate` |
| M4 | `GET /people` + seed on reset |
| M5 | `POST /doses/trigger` |
| M7/M8/M9 | `POST /doses/{id}/complete` + `src/policy/` |
| M10 | packet creation on complete |
| M11 | `GET /events` append-only |
| — | `POST /demo/reset`, `GET /health`, `POST /policy/check` |

---

## Target layout

```text
services/api/
├── README.md
├── requirements.txt          # or pyproject.toml
├── .env                      # local only
├── src/
│   ├── main.py               # app factory + routers
│   ├── db.py
│   ├── models/               # pydantic + persistence
│   ├── routes/
│   │   ├── health.py
│   │   ├── plans.py
│   │   ├── doses.py
│   │   ├── events.py
│   │   ├── packets.py
│   │   ├── people.py
│   │   └── demo.py
│   ├── policy/
│   │   └── kernel.py         # pure functions, deterministic
│   ├── services/
│   │   ├── extract.py
│   │   ├── packets.py
│   │   └── ledger.py
│   └── voice/                # Jyotir — leave hooks
└── tests/
    └── test_smoke_path.py
```

---

## Implementation order (do this order)

1. **Health + in-memory or SQLite store + reset**  
   Seed people from `fixtures/people.json`.
2. **Plans extract**  
   Hour-1 acceptable hack: regex/LLM extract **or** map discharge text onto `fixtures/formulary.json` if LLM is slow. Must return contract shape.
3. **Activate + events**
4. **Trigger dose**
5. **Complete + policy + packet**
6. **Wire real Sarvam LLM extract** if time (still human-confirm later in UI)
7. **Policy check endpoint** for double dose

Do not build microservices.
Do not build auth.
Do not build multi-tenant.

---

## Policy kernel (must be boring)

```text
side_effect → allow log + escalate caregiver packet
double_dose on criticality=high → refuse + escalate
invent_rx → refuse
silent_stop high criticality → refuse
taken with no exception → log only
```

File: `services/api/src/policy/kernel.py`  
No “ask the LLM whether stopping is OK.”

---

## Hour-by-hour plan

### Hour 0–1

- [ ] Scaffold FastAPI app
- [ ] `/health`, `/demo/reset`, `/people`
- [ ] PR merge so Harsh can point `NEXT_PUBLIC_API_URL`

### Hour 1–3

- [ ] extract / get / patch / activate
- [ ] trigger / complete / events / packets/latest
- [ ] `../../scripts/smoke-api.sh` passes

### Hour 3–5

- [ ] Improve extract quality on fixture text
- [ ] Packet copy matches `sample-care-packet.json`
- [ ] Help Jyotir call complete with correct body

### Hour 5–7

- [ ] Policy refuse double dose
- [ ] Harden errors (`PLAN_NOT_ACTIVE`, etc.)
- [ ] Fix only integration bugs

### Hour 7–8

- [ ] No new endpoints
- [ ] Crash fixes only

---

## Agent system plan (paste this whole block)

```text
You are Barkha's coding agent for DAWA.

MISSION
Implement the FastAPI backend that is the system of record for med plans, doses, policy, events, and caregiver packets.

OWNED PATHS
- services/api/** 
- Coordinate: services/api/src/voice/** is Jyotir-primary; provide stable complete/trigger APIs they can call.

READ FIRST
- docs/API_CONTRACT.md (law)
- docs/MVP.md
- fixtures/formulary.json
- fixtures/people.json
- fixtures/sample-care-packet.json
- scripts/smoke-api.sh

HARD RULES
1. Match API_CONTRACT field names exactly.
2. Backend writes ledger and packets. No "UI will invent events."
3. Policy kernel is deterministic code, not free-form model actions.
4. MVP only: one patient, one caregiver, paste extract, one side_effect path.
5. Do not add auth, redis, kafka, microservices, or extra apps.
6. Do not commit .env.
7. Prefer SQLite file under data/local/ (gitignored) for speed.
8. On complete(side_effect): create CarePacket shaped like fixtures/sample-care-packet.json.
9. POST /demo/reset must reload seed people and clear plans/events/doses/packets.
10. If extract LLM is hard, fallback: parse fixture-oriented text onto formulary.json — still return draft medications.

IMPLEMENTATION ORDER
health → reset/people → extract → activate → trigger → complete+policy+packet → events/packets GET → policy/check → tests.

DONE CHECK
- ../../scripts/smoke-api.sh passes
- curl complete with side_effect returns packet_id
- double dose policy returns allowed:false
```

---

## How you test

```bash
# from repo root, API running on :8000
./scripts/demo-reset.sh
./scripts/smoke-api.sh

# manual policy
curl -s -X POST localhost:8000/policy/check \
  -H 'Content-Type: application/json' \
  -d '{"intent":"double_dose","medication_id":"med_amlodipine"}'
```

| Case | Expected |
| --- | --- |
| activate then trigger | dose status calling |
| complete taken+side_effect | packet exists, events grow |
| complete before activate | 4xx PLAN_NOT_ACTIVE or similar |
| double_dose high med | allowed false |

Unit-test policy functions if you have 15 minutes — high ROI.

---

## Merge checklist (before asking Arnav to merge)

- [ ] Only `services/api/**` (plus maybe requirements)
- [ ] smoke-api passes on your machine
- [ ] README in `services/api` with run command
- [ ] No secrets
- [ ] Contract names unchanged (or contract PR already merged)

---

## What wins / loses (your lens)

**Win:** Harsh and Jyotir only need your URLs; ledger is trustworthy; policy answer is crisp for judges.

**Lose:** UI stores state that backend does not; packet shape drifts; extract invents random drugs outside formulary without confirm.

---

## Coordination

| Need from | What |
| --- | --- |
| Arnav | Fixture freezes, keys, merge |
| Harsh | Will call your REST only — keep CORS open for localhost |
| Jyotir | Exact complete payload; optional voice-turn route if you agree |

CORS: allow `http://localhost:3000` (or Vite port).

---

## Explicit do-not list

- Do not implement WhatsApp/PSTN/payments.
- Do not build clinician summary before E2E.
- Do not rename enum strings casually.
- Do not block on perfect OCR — paste path first.
