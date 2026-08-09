# Arnav — Product, demo, fixtures, merge gate

**Role:** Person A — product owner + integration owner + demo operator  
**Time budget:** under 8 hours with 3 other builders  
**You are the glue.** If E2E is broken, it is your problem to sequence the fix — not necessarily to write all the code.

---

## Read first (30 min max)

1. [docs/MVP.md](../docs/MVP.md)
2. [docs/DEMO_SCRIPT.md](../docs/DEMO_SCRIPT.md)
3. [docs/API_CONTRACT.md](../docs/API_CONTRACT.md)
4. [docs/GIT_AND_AGENTS.md](../docs/GIT_AND_AGENTS.md)
5. [docs/WIN_LOSE_TEST.md](../docs/WIN_LOSE_TEST.md)
6. Background only: [docs/DAWA.md](../docs/DAWA.md)

---

## You own (edit freely)

```text
docs/**
fixtures/**
scripts/**
team/**
README.md
.env.example
```

## You may touch with a shout

```text
apps/web/**          # copy, empty states, demo labels only
services/api/**      # seed data paths, demo reset behavior only
```

## You do not own

- Voice STT/TTS implementation (Jyotir)
- API business logic beyond demo seed/reset (Barkha)
- Full cockpit UI (Harsh)

---

## Branch + where to push

| Item | Value |
| --- | --- |
| Branch | `feat/fixtures-demo` for bulk doc/fixture work |
| After freeze | Prefer tiny PRs straight into `main` for docs |
| Remote | origin (create GitHub repo ASAP; push `main` first) |
| Merge authority | **You gate `main` after hour 4** |

### Commands

```bash
git checkout main && git pull
git checkout -b feat/fixtures-demo
# work...
git add docs fixtures scripts team README.md
git commit -m "docs: lock demo fixtures and team playbooks"
git push -u origin feat/fixtures-demo
# open PR → merge early
```

---

## MVP IDs you are responsible for

| ID | What you deliver |
| --- | --- |
| — | Locked formulary, people, discharge text |
| — | Demo script spoken lines final |
| — | Kill switches documented and rehearsed |
| — | Contract change control |
| — | Scoreboard + E2E runs |
| M10/M11 quality | Packet/ledger **content** quality (copy), not React |

You do not implement M6 voice, but you accept or reject “voice is demo-ready.”

---

## Hour-by-hour plan

### Hour 0–1 — Freeze

- [ ] Confirm languages: patient **Hindi**, caregiver **English** (or freeze Kannada — one only)
- [ ] Confirm formulary in `fixtures/formulary.json`
- [ ] Confirm discharge text in `fixtures/discharge-messy.txt`
- [ ] Confirm sample packet copy
- [ ] Create GitHub remote; everyone clones
- [ ] Distribute Sarvam API keys via secure channel; never commit
- [ ] Everyone pastes their agent plan and starts

### Hour 1–4 — Unblock others

- [ ] Keep contract stable
- [ ] Help Barkha seed `POST /demo/reset` to load fixtures
- [ ] Write caregiver packet English copy (suggestions list)
- [ ] Prepare one-slide differentiator (not Rakshak / not Yaadein)
- [ ] Wire `scripts/smoke-api.sh` once API stubs exist
- [ ] Merge Barkha stubs early so Harsh is not blocked

### Hour 4–6 — Integration

- [ ] Run smoke-api
- [ ] Run full demo path with team
- [ ] Log blockers on a shared checklist (`docs/WIN_LOSE_TEST.md` scoreboard)
- [ ] Only allow merges that fix the path

### Hour 6–7 — Polish theatre

- [ ] Closing lines on screen (Harsh implements; you provide text)
- [ ] Failure handling known (extract fail, STT fail)
- [ ] Policy double-dose refuse demonstrated once

### Hour 7–8 — Freeze + rehearse

- [ ] Feature freeze
- [ ] E2E twice after reset
- [ ] Chaos drill once
- [ ] Assign who sits where in demo
- [ ] You speak minimal operator lines only

---

## Agent system plan (paste this whole block)

```text
You are Arnav's coding agent for the DAWA hackathon monorepo.

MISSION
- Own product docs, fixtures, scripts, team playbooks, demo reliability.
- Do NOT build the full backend, voice stack, or React cockpit unless explicitly asked for a tiny unblock.

OWNED PATHS (only edit these by default)
- docs/**
- fixtures/**
- scripts/**
- team/**
- README.md
- .env.example
- .gitignore

READ-ONLY CONTEXT
- docs/MVP.md
- docs/API_CONTRACT.md
- docs/DEMO_SCRIPT.md
- docs/WIN_LOSE_TEST.md
- docs/DAWA.md

HARD SCOPE
- SHIP list only from docs/MVP.md.
- One exception path: side_effect / pet mein jalan.
- Paste-first ingest. No PSTN, WhatsApp, Razorpay, clinician summary unless team says stretch is open.
- Never commit .env or API keys.
- Never invent a second API shape. Contract is law.

DELIVERABLES THIS SESSION
1) Keep fixtures consistent with API_CONTRACT CarePacket + formulary.
2) Keep demo-reset and smoke-api scripts working against local API.
3) Keep docs accurate when the team freezes a decision.
4) Produce clear PR-sized commits.

WHEN BLOCKED
- Stub content in fixtures; ping Barkha/Harsh/Jyotir with exact missing endpoint/field.
- Do not reimplement their stack under docs/.

DONE CHECK
- Fixtures loadable; demo script match formulary; smoke script matches contract paths.
```

---

## How you test

| Test | Pass |
| --- | --- |
| Fixtures valid JSON | `python3 -m json.tool fixtures/*.json` |
| Reset script | API up → `./scripts/demo-reset.sh` exits 0 |
| Smoke | `./scripts/smoke-api.sh` exits 0 |
| E2E | Full demo script twice — see WIN_LOSE_TEST L4 |
| Judge attack answers | You can answer the 5 questions in docs/DAWA.md §21 without freezing |

---

## What “done” means for you

- Team is not confused about scope.
- `main` is the demo.
- Kill switches rehearsed.
- You can run the 5-minute path as operator without coding live.

---

## What wins / loses (your lens)

**You win if:** the story is crisp, the path is boringly reliable, and stretch does not eat the demo.

**You lose if:** scope creeps, two API shapes exist, or the last hour is spent adding WhatsApp.

---

## Communication

- Announce contract freezes in chat.
- After each merge to `main`, ping: “main advanced: &lt;what works now&gt;”.
- Maintain the scoreboard in WIN_LOSE_TEST.

---

## Explicit do-not list

- Do not let anyone expand formulary mid-demo-day.
- Do not accept hardcoded caregiver outcomes on `main` for the judged path.
- Do not start GTM slides before E2E green.
- Do not change role assignments without rewriting playbooks.
