# DAWA — Features

**Execution truth for the hackathon:** [docs/MVP.md](docs/MVP.md)  
**Pivot:** [docs/PIVOT.md](docs/PIVOT.md) — patient = calling agent only, **no patient UI**.

This file remains the product feature map.
For the under-8-hour build, only **SHIP** items are in scope.

---

## SHIP (8h MVP)

1. **Rx ingest (paste-first)** — caregiver/operator cockpit; photo optional stretch.
2. **Med graph extraction** — 3–5 meds into draft graph (demo formulary).
3. **Human confirm step** — caregiver reviews; activate blocked until confirm.
4. **Role linking** — patient (phone + language) + caregiver (cockpit).
5. **Dose call trigger** — caregiver clicks call for evening dose.
6. **Patient calling agent** — Sarvam outbound voice agent; **no patient app**.
7. **Adherence on call** — conversational taken path on the phone.
8. **Exception (one path)** — side effect: pet mein jalan.
9. **Policy kernel** — no invented Rx; no silent stop high-critical; refuse double dose; escalate side effect.
10. **Caregiver packet** — structured English alert card on cockpit.
11. **Event ledger** — timeline on cockpit.
12. **Webhook ingest** — call outcome → our state (not only Sarvam dashboard).

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
