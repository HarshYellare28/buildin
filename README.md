# DAWA

**Medication execution OS for Indian families after a hospital or clinic visit.**

Tagline: Hospitals write prescriptions. Families guess. DAWA runs the meds.

Hackathon constraint: **under 8 hours, 4 people.**
Read this file, then your personal playbook in `team/`.

### Product pivot (locked)

- **Patient:** phone only via **Sarvam calling agents**. **No patient UI.**
- **Caregiver / operator:** full cockpit (plan, call trigger, packets, ledger).
- Details: [docs/PIVOT.md](docs/PIVOT.md)

---

## Team map (locked)

| Person | Role | Own these paths | Playbook |
| --- | --- | --- | --- |
| **Arnav** | Product, demo, fixtures, merge gate, agent script | `docs/`, `fixtures/`, `scripts/`, `team/` | [team/Arnav.md](team/Arnav.md) |
| **Barkha** | Backend, med graph, policy, **call webhook** | `services/api/` | [team/Barkha.md](team/Barkha.md) |
| **Jyotir** | **Sarvam calling agent** (patient voice only) | agent config + call trigger glue | [team/Jyotir.md](team/Jyotir.md) |
| **Harsh** | **Caregiver cockpit only** (no patient screens) | `cockpit/` | [team/Harsh.md](team/Harsh.md) |

Shared contracts (everyone reads, nobody freelances):

- [docs/PIVOT.md](docs/PIVOT.md) — patient = call only
- [docs/MVP.md](docs/MVP.md) — what ships, what is cut
- [docs/API_CONTRACT.md](docs/API_CONTRACT.md) — endpoints + JSON shapes
- [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) — second-by-second demo
- [docs/GIT_AND_AGENTS.md](docs/GIT_AND_AGENTS.md) — branches, merge rules, agent prompts
- [docs/WIN_LOSE_TEST.md](docs/WIN_LOSE_TEST.md) — how to test, what wins, what loses
- [docs/DAWA.md](docs/DAWA.md) — full product brief (background only)

---

## Repo layout

**This folder (`buildin/`) is the git root.** Clone it, push to it, open it as the project.

```text
buildin/                      # git repository root
├── README.md                 # you are here
├── .env.example
├── DAWA.md                   # full product brief (also docs/DAWA.md)
├── features.md               # feature map → points at docs/MVP.md
├── docs/                     # MVP, contract, demo, git rules (Arnav)
├── team/                     # personal playbooks
├── fixtures/                 # discharge text, formulary, sample packet
├── scripts/                  # seed + demo-reset
├── cockpit/                  # Next.js caregiver cockpit (Harsh)
├── apps/web/                 # deprecated pointer; no patient app
├── services/
│   └── api/                  # FastAPI backend (Barkha + Jyotir voice)
└── packages/shared/          # optional shared schemas later
```

---

## Win condition (one sentence)

Caregiver cockpit activates plan → **patient’s phone rings** (calling agent) → taken + side effect on call → **caregiver English card + ledger update** (no patient UI, no hand-edited card).

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

# terminal 2 — caregiver cockpit (Harsh)
cd cockpit && npm ci && npm run dev

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
- Product vision: `DAWA.md` / `docs/DAWA.md`.
- Execution truth: `docs/MVP.md` + team playbooks.
- Git root: this directory (`buildin/`).
