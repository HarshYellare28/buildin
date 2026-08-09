# Harsh — Frontend cockpit (Next.js)

**Role:** Person D — demo theatre + human control surface  
**Stack target:** Next.js (App Router) + simple CSS/Tailwind  
**You make the system legible.** Judges look at your screen half the time.

---

## Read first

1. [docs/MVP.md](../docs/MVP.md)
2. [docs/API_CONTRACT.md](../docs/API_CONTRACT.md)
3. [docs/DEMO_SCRIPT.md](../docs/DEMO_SCRIPT.md)
4. [docs/WIN_LOSE_TEST.md](../docs/WIN_LOSE_TEST.md)
5. [docs/GIT_AND_AGENTS.md](../docs/GIT_AND_AGENTS.md)
6. `fixtures/sample-care-packet.json`

---

## You own (edit freely)

```text
apps/web/**
```

## You do not own

```text
services/api/**          # consume only
fixtures/**              # read for local mock if API down — prefer live API
services/api/src/voice/** # Jyotir; you only host mic UI shell
```

---

## Branch + where to push

| Item | Value |
| --- | --- |
| Branch | `feat/web` |
| Paths | `apps/web/**` |
| API URL | `NEXT_PUBLIC_API_URL=http://localhost:8000` |

```bash
git checkout main && git pull
git checkout -b feat/web
cd apps/web
# npx create-next-app .  (if not scaffolded) — TypeScript, App Router, no extra junk
git add apps/web
git commit -m "feat(web): cockpit graph confirm ledger packet"
git push -u origin feat/web
```

---

## MVP IDs you ship

| ID | UI |
| --- | --- |
| M1 | Paste textarea + Extract button |
| M2/M3 | Med graph table/cards editable + Confirm + Activate |
| M4 | Patient / caregiver chips (from GET /people) |
| M5 | **Jump to evening dose** big button |
| M6 | Voice panel shell (mic start/stop) — Jyotir fills behavior |
| M10 | Caregiver packet card (render API JSON) |
| M11 | Event ledger timeline |
| — | Closing lines / mode banners for demo |

Not day-1: multi-page marketing site, auth, dark-theme rewrite mid-day, WhatsApp mocks as primary.

---

## Screen layout (one page cockpit)

```text
┌─────────────────────────────────────────────────────────────┐
│ DAWA  ·  Medication executed          [Reset demo]          │
├──────────────────────┬──────────────────────────────────────┤
│ 1. INGEST            │ 3. LIVE DOSE                         │
│  paste discharge     │  status: idle/calling/done           │
│  [Extract]           │  [Jump to evening dose]              │
│                      │  [Mic] voice panel (Jyotir)          │
│ 2. MED GRAPH         │                                      │
│  list + edit         │ 4. CAREGIVER PACKET (EN)             │
│  confidence colors   │  card from GET /packets/latest       │
│  [Confirm & Activate]│                                      │
│                      │ 5. EVENT LEDGER                      │
│ Roles: Lakshmi/Ananya│  timeline from GET /events           │
└──────────────────────┴──────────────────────────────────────┘
```

Clinical calm UI.
Not neon consumer gimmick.

---

## Frontend rules

1. **All outcomes from API.** Do not hardcode the final caregiver card text for the happy path on `main`.
2. After Activate / Trigger / Complete, **refetch** events + packet.
3. Show plan status badge: `draft` | `active`.
4. Disable Activate until user checks “I reviewed the meds.”
5. Low confidence fields: red/amber border if API sends confidence.
6. Dev-only “Simulate complete” button allowed **with red DEV badge** if voice late — remove or hide for judged run if voice works.
7. Poll events every 2s during `calling` OR refetch on voice complete callback.

---

## Hour-by-hour plan

### Hour 0–1

- [ ] Scaffold Next.js in `apps/web`
- [ ] Three panels empty with titles
- [ ] Env `NEXT_PUBLIC_API_URL`
- [ ] Fetch `/health` and show green/red

### Hour 1–3

- [ ] Paste + extract → render medications
- [ ] Edit fields + activate
- [ ] People chips
- [ ] Ledger empty state

### Hour 3–5

- [ ] Jump to evening → shows dose calling
- [ ] Packet panel
- [ ] Wire mic slot for Jyotir
- [ ] Reset button → `POST /demo/reset` + clear local UI state

### Hour 5–7

- [ ] Polish: phase banners, closing lines component
- [ ] Loading/error toasts
- [ ] Disable illegal actions (trigger before activate)

### Hour 7–8

- [ ] Visual freeze
- [ ] Font size for projector
- [ ] Rehearse click path with Arnav

---

## Agent system plan (paste this whole block)

```text
You are Harsh's coding agent for DAWA web cockpit.

MISSION
Build a single-page Next.js demo cockpit that drives the DAWA API through the paste → confirm → activate → evening dose → packet/ledger path.

OWNED PATHS
- apps/web/** only

READ FIRST
- docs/API_CONTRACT.md
- docs/MVP.md
- docs/DEMO_SCRIPT.md
- fixtures/sample-care-packet.json (render shape)

HARD RULES
1. Do not invent backend endpoints. Use API_CONTRACT only.
2. Caregiver packet and ledger must be fetched from API for the real path.
3. No auth, no extra routes beyond the cockpit, no component library rabbit holes.
4. One page is enough. Huge design systems are out of scope.
5. Coordinate mic/voice components with Jyotir; leave clear props/callbacks.
6. Never commit .env.local with secrets.
7. Prefer simple fetch wrappers in lib/api.ts.
8. TypeScript types should mirror contract; if unknown, minimal interfaces.
9. If API is down, show error — optional fixture preview must be labeled MOCK.
10. SHIP MVP UI only. No WhatsApp panel, no payments, no multi-day scrubber.

UI SECTIONS
Ingest, MedGraphConfirm, Roles, DoseTrigger, VoiceSlot, CarePacketCard, EventLedger, DemoReset, ClosingLines.

DONE CHECK
- Click path without voice uses DEV simulate only if needed.
- With API smoke data, packet and ledger render correctly.
- Projector-readable typography.
```

---

## How you test

| Test | Pass |
| --- | --- |
| API down | Clear error, no silent fake success |
| Paste fixture text | Meds render after extract |
| Activate | Badge active; event appears after refetch |
| Trigger | Dose panel shows calling |
| After complete (voice or DEV) | Packet matches side_effect; ledger longer |
| Reset | Back to empty/draft world |
| Projector | Key text readable from 2m |

Manual click script (memorize):

1. Reset  
2. Paste `fixtures/discharge-messy.txt`  
3. Extract → skim meds → Confirm & Activate  
4. Jump to evening  
5. Voice (Jyotir)  
6. Point at packet + ledger  
7. Closing lines  

---

## Merge checklist

- [ ] `apps/web` runs with `npm run dev`
- [ ] README with install/run
- [ ] No hardcoded final packet on main happy path
- [ ] Env example documented
- [ ] Build does not need Barkha’s laptop-specific paths

---

## What wins / loses (your lens)

**Win:** Judges understand the system in 10 seconds of screen time; every phase change is obvious.

**Lose:** Pretty app that does not call the API; tiny font; five pages of navigation; card text typed into JSX for the demo.

---

## Coordination

| Person | Need |
| --- | --- |
| Barkha | CORS, stable JSON, reset |
| Jyotir | Mic component API: `doseId`, `onComplete()` |
| Arnav | Copy for closing lines, packet suggestion text QA |

Suggested VoiceSlot props:

```ts
type VoiceSlotProps = {
  doseId: string | null;
  disabled: boolean;
  onFinished: () => void; // parent refetches packet + events
};
```

Jyotir implements internals.

---

## Explicit do-not list

- Do not start a design system.
- Do not add routing for marketing pages.
- Do not block on perfect mobile responsive — desktop demo first.
- Do not duplicate policy logic in the client beyond disabling buttons.
