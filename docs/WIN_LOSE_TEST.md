# What wins, what loses, how to test

---

## What wins (judges leave saying)

1. “They actually ran a live patient voice session and the family state updated.”
2. “It’s not another elder chatbot.”
3. “I would enroll my parents.”

Product signals that create that reaction:

- Med graph as source of truth (visible)
- Live Indic STT/TTS (not a pre-recorded clip as the only path)
- Side-effect exception with **policy** (no invented Rx)
- Caregiver English structured packet
- Audit ledger of what happened

---

## What loses (judges leave saying)

1. “Cute reminders.”
2. “Rakshak with a prescription photo.”
3. “What if it gives medical advice wrong?” and you freeze.
4. “Wrapper on Sarvam Voice.”

Anti-signals:

- Tap-yes adherence with no conversation
- Caregiver card hardcoded in the frontend for the live demo
- Model freestyles a new medicine
- OCR chaos with no confirm step
- Beautiful UI, dead voice
- Feature tour instead of one irreversible story

---

## Differentiation one-liner (memorize)

> Rakshak observes. Yaadein remembers. **DAWA executes.**

---

## Test levels

### L0 — Smoke (each person, every slice)

| Owner | Command / action | Pass |
| --- | --- | --- |
| Barkha | `curl localhost:8000/health` | `ok: true` |
| Harsh | Web loads without console red errors | Cockpit shell visible |
| Jyotir | 20s mic round-trip STT→TTS | Heard intelligible Hindi/EN |
| Arnav | `./scripts/demo-reset.sh` | Clean seed, no crash |

### L1 — Contract tests (Barkha, before UI depends)

Run in order (script these as soon as possible):

```bash
# 1 extract
# 2 patch optional
# 3 activate
# 4 trigger dose
# 5 complete with side_effect
# 6 GET /events
# 7 GET /packets/latest
```

Pass criteria:

- Plan status becomes `active`
- Packet `exception.type` is `side_effect`
- Packet language `en-IN`
- Events include `plan_activated`, `dose_triggered`, `dose_completed`, `packet_sent` (names per contract)
- Double-dose policy check returns `allowed: false`

### L2 — UI drive (Harsh + Barkha)

Without voice:

1. Reset
2. Paste `fixtures/discharge-messy.txt`
3. Confirm meds
4. Activate
5. Jump to evening
6. (Dev tool) POST complete payload or temporary “simulate complete” button **only if labeled DEV**
7. Packet + ledger panels update from GET

Pass: no manual JSON edit in the card component for the outcome.

### L3 — Voice (Jyotir)

1. Dose session active
2. Speak: taken + pet mein jalan
3. System completes dose with correct payload
4. Packet/ledger update

Pass: no typed puppeting in the judged path.
Typed fallback is disaster-only.

### L4 — Full E2E (Arnav runs, all present)

Do the full `docs/DEMO_SCRIPT.md` twice.

| Run | Required |
| --- | --- |
| Run 1 | Complete path works |
| Run 2 | After `demo-reset`, works again |

Chaos drills (at least one):

- Mumble once → agent asks to confirm (or retry)
- Ask “should I take two?” → refuse + escalate (policy)
- Kill mic mid-way → recovery path understood

---

## Scoreboard (internal, track on a whiteboard)

| Checkpoint | Owner | Done? |
| --- | --- | --- |
| Contract frozen | Arnav | |
| Seed people + formulary | Arnav + Barkha | |
| Extract + activate API | Barkha | |
| Confirm UI | Harsh | |
| Ledger + packet UI | Harsh | |
| Policy refuse double dose | Barkha | |
| Live voice loop | Jyotir | |
| Voice → complete wired | Jyotir + Barkha | |
| E2E #1 | All | |
| E2E #2 | All | |
| Rehearsal freeze | Arnav | |

---

## Demo-day preflight (T-30 min)

- [ ] `.env` present on demo machine
- [ ] API + web running
- [ ] `demo-reset` once
- [ ] Mic permission granted
- [ ] Network stable / Sarvam key valid
- [ ] Backup: activated plan seed if extract flakes
- [ ] Backup: known-good complete payload only for disaster
- [ ] One slide: not Rakshak / not Yaadein
- [ ] Closing lines ready on screen

---

## Stop-doing list (last 90 minutes)

- New endpoints not on the critical path
- Visual redesigns
- Extra languages
- WhatsApp / payments / PSTN
- Refactors “for cleanliness”
- Expanding formulary

Only crash fixes and latency fixes.
