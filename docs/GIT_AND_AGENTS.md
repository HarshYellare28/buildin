# Git workflow + agent discipline

4 people.
Under 8 hours.
Merge often or die in integration hell.

---

## Branch map

| Branch | Owner | Contains |
| --- | --- | --- |
| `main` | Arnav (gate) | Always the demo candidate after first green E2E |
| `feat/api` | Barkha | `services/api/**` except pure voice experiments |
| `feat/voice` | Jyotir | `services/api/src/voice/**` + voice UI hooks agreed with Harsh |
| `feat/web` | Harsh | `apps/web/**` |
| `feat/fixtures-demo` | Arnav | `docs/`, `fixtures/`, `scripts/`, team playbooks |

### Rules

1. Branch from latest `main` every time you start a chunk of work.
2. Open PRs small: prefer 30–60 minute slices over end-of-day dumps.
3. **Directory ownership is sacred.** Cross-directory edits need a ping and a focused PR.
4. Contract changes (`docs/API_CONTRACT.md`) merge **before** code that depends on them.
5. After first full E2E is green on `main`, no force-push to `main`.
6. No long-lived “rewrite everything” branches.

---

## When to merge

### Merge immediately (fast lane)

- Docs / fixtures / sample JSON
- API stubs that match contract (even if LLM extract is fake)
- UI shells that render mock data **behind a flag** only if labeled; prefer hitting real API early
- Health checks, seed scripts, reset scripts

### Merge when green (normal lane)

| Merge candidate | Required checks |
| --- | --- |
| Barkha API | `/health`, extract→activate→trigger→complete→events→packet with curl or script |
| Jyotir voice | One live STT→TTS dialogue; complete API called with correct payload |
| Harsh web | Can drive paste→confirm→activate→trigger→show packet/ledger against local API |
| Full E2E | `docs/WIN_LOSE_TEST.md` checklist pass **twice** |

### Do not merge

- Half-renamed contract fields
- Secrets in `.env`
- Stretch features before E2E green
- “Temporary” hardcoded caregiver card presented as live on `main`
- Refactors that do not help the demo path

---

## Suggested merge order (clock)

| Window | Merge focus |
| --- | --- |
| Hour 0–1 | Scaffold, contract, fixtures, empty apps on `main` |
| Hour 1–3 | Barkha stubs + seed; Harsh shell; Jyotir voice loop alone |
| Hour 3–5 | Extract/activate real; UI wired; voice calls complete |
| Hour 5–6 | E2E #1; fix only blockers |
| Hour 6–7 | Policy polish, failure handling, UI theatre |
| Hour 7–8 | **Freeze features.** Rehearse. Merge only crash fixes |

---

## Commit hygiene

```text
feat(api): activate plan endpoint
feat(web): med graph confirm panel
feat(voice): hindi dose dialogue loop
fix(policy): refuse double dose on high criticality
chore(fixtures): messy discharge text
docs: lock caregiver packet schema
```

Do not put agent co-author noise in commits unless the team wants it.
Keep messages short and true.

---

## Conflict avoidance

| Hotspot | Rule |
| --- | --- |
| Types / JSON shapes | `docs/API_CONTRACT.md` + `fixtures/*.json` only |
| Event type strings | Use enums from contract |
| Policy decisions | Backend only; UI displays results |
| Ledger writes | Backend only via complete / activate / trigger |
| Voice transcript → outcome | Jyotir may guess; Barkha complete endpoint validates + policies |

---

## PR template (paste into every PR)

```markdown
## Slice
What MVP ID does this advance? (M1–M11)

## Paths touched
List directories.

## How to test
Commands + expected result.

## Demo impact
Does this help the 5-minute path? Yes/No.

## Risk
Anything that can break main E2E?
```

---

## Agent rules (all people)

Every person pastes their playbook’s **Agent system plan** into Cursor / Claude / Codex / Grok at session start.

Global agent constraints:

1. Only edit files under your owned paths unless the playbook says otherwise.
2. Read `docs/MVP.md` and `docs/API_CONTRACT.md` before writing code.
3. Do not add dependencies without asking the owner of that package.
4. Do not build stretch features.
5. Prefer working vertical slices over perfect architecture.
6. After each slice: run the tests listed in your playbook.
7. If blocked on another person, implement a stub behind the contract and ping them — do not invent a second protocol.
8. Never commit `.env` or API keys.
9. Never silently remove policy refusals to “make demo smoother.”
10. When unsure, implement the demo path, not a general platform.

---

## Integration owner

**Arnav** is merge gate after hour 4.

Meaning:

- Arnav can block merges that threaten demo reliability.
- Arnav runs `demo-reset` + full path before calling “E2E green.”
- Others do not merge large PRs in the last hour without Arnav ack.
