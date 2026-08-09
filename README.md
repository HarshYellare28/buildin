# DAWA

**Medication execution OS for Indian families after a hospital or clinic visit.**

Tagline: Hospitals write prescriptions. Families guess. DAWA runs the meds.

Hackathon constraint: **under 8 hours, 4 people.**
Read this file, then your personal playbook in `team/`.

---

## Team map (locked)

| Person | Role | Own these paths | Playbook |
| --- | --- | --- | --- |
| **Arnav** | Product, demo, fixtures, merge gate, integration | `docs/`, `fixtures/`, `scripts/`, `team/`, root README | [team/Arnav.md](team/Arnav.md) |
| **Barkha** | Backend, med graph, policy, APIs | `services/api/` | [team/Barkha.md](team/Barkha.md) |
| **Jyotir** | Voice: Sarvam STT → policy LLM → TTS | `services/api/src/voice/`, voice client under web if needed | [team/Jyotir.md](team/Jyotir.md) |
| **Harsh** | Frontend cockpit UI | `apps/web/` | [team/Harsh.md](team/Harsh.md) |

Shared contracts (everyone reads, nobody freelances):

- [docs/MVP.md](docs/MVP.md) — what ships, what is cut
- [docs/API_CONTRACT.md](docs/API_CONTRACT.md) — endpoints + JSON shapes
- [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) — second-by-second demo
- [docs/GIT_AND_AGENTS.md](docs/GIT_AND_AGENTS.md) — branches, merge rules, agent prompts
- [docs/WIN_LOSE_TEST.md](docs/WIN_LOSE_TEST.md) — how to test, what wins, what loses
- [docs/DAWA.md](docs/DAWA.md) — full product brief (background only)

---

## Repo layout

```text
sarvambuildin/
├── README.md                 # you are here
├── .env.example
├── docs/                     # product + contracts (Arnav)
├── team/                     # personal playbooks
├── fixtures/                 # discharge text, formulary, sample packet
├── scripts/                  # seed + demo-reset
├── apps/
│   └── web/                  # Next.js cockpit (Harsh)
├── services/
│   └── api/                  # FastAPI backend (Barkha + Jyotir voice module)
└── buildin/                  # original product notes
```

---

## Win condition (one sentence)

Paste Rx → confirm med graph → live Indic dose session → patient reports side effect → **caregiver English card + ledger update without hand-editing the card.**

If that path works twice in a row, you are demo-ready.
Everything else is stretch or noise.

---

## First 30 minutes (all four)

1. Clone / pull `main`.
2. Read `docs/MVP.md` and your `team/<Name>.md` only.
3. Copy `.env.example` → `.env` (Arnav distributes keys).
4. Create your branch from latest `main` (see GIT_AND_AGENTS).
5. Paste the **agent plan** from your playbook into your coding agent.
6. Do not invent extra features.

---

## Local run (target)

```bash
# terminal 1 — API (Barkha)
cd services/api && make dev   # or: uvicorn ...

# terminal 2 — Web (Harsh)
cd apps/web && npm run dev

# reset world state before every rehearsal
./scripts/demo-reset.sh
```

Exact commands land when scaffolding is filled in.
Until then, follow your playbook’s “Day-0 bootstrap” section.

---

## Branch names (required)

| Person | Branch |
| --- | --- |
| Arnav | `feat/fixtures-demo` (or work on `main` only for docs after freeze) |
| Barkha | `feat/api` |
| Jyotir | `feat/voice` |
| Harsh | `feat/web` |

Merge order and rules: [docs/GIT_AND_AGENTS.md](docs/GIT_AND_AGENTS.md).

---

## Hard rules

1. **Directory ownership.** Do not edit another person’s primary paths without a shout in chat and a tiny PR.
2. **Contract is law.** Change `docs/API_CONTRACT.md` only with team agreement.
3. **One exception path.** Side effect = acidity / pet mein jalan. No full taxonomy day-1.
4. **Paste-first ingest.** Photo is optional stretch.
5. **Backend writes the ledger.** UI never invents events locally for the demo path.
6. **Last hour is rehearsal**, not features.
7. **main must stay demoable** after first green E2E.

---

## Status

- Repo scaffolded for 8-hour hackathon execution.
- Product vision: `buildin/DAWA.md`.
- Execution truth: `docs/MVP.md` + team playbooks.
