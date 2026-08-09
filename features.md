# DAWA — Features

**Execution truth for the hackathon:** [docs/MVP.md](docs/MVP.md)

This file remains the product feature map.
For the under-8-hour build, only **SHIP** items are in scope.

---

## SHIP (8h MVP)

1. **Rx ingest (paste-first)** — paste discharge text; photo optional stretch.
2. **Med graph extraction** — 3–5 meds into draft graph (demo formulary).
3. **Human confirm step** — editable review; activate blocked until confirm.
4. **Role linking** — one patient + one caregiver, languages locked.
5. **Demo dose trigger** — jump to evening dose (not full cron).
6. **Live dose call** — STT → policy-bound LLM → TTS (in-app OK).
7. **Adherence verification** — conversational taken path.
8. **Exception (one path)** — side effect: pet mein jalan.
9. **Policy kernel** — no invented Rx; no silent stop high-critical; refuse double dose; escalate side effect.
10. **Caregiver packet** — structured English alert card from API.
11. **Event ledger** — timeline of dose events and system actions.

## Stretch (after two green E2Es)

- Clinician summary
- Real PSTN outbound calling
- Second caregiver with scoped permissions
- Allowlisted refill + Razorpay payment
- Small hardcoded drug-interaction table
- Blister-strip photo verification
- WhatsApp caregiver channel
- Multi-day timeline scrubber
- Photo Rx as primary ingest

## Out of scope

Diagnosis, autonomous prescription changes, EHR integration, ambient always-on mic, full Indian formulary coverage.

---

## Team ownership

| Area | Person | Playbook |
| --- | --- | --- |
| Product / demo / merge | Arnav | [team/Arnav.md](team/Arnav.md) |
| Backend / policy | Barkha | [team/Barkha.md](team/Barkha.md) |
| Voice | Jyotir | [team/Jyotir.md](team/Jyotir.md) |
| Web cockpit | Harsh | [team/Harsh.md](team/Harsh.md) |
