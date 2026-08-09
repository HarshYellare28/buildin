# DAWA — Demo script (~5 minutes)

**Pivot:** patient has **no UI**. Only the **phone**. Big screen = caregiver cockpit.

Cast:

- **Patient:** teammate with a **phone** (elder persona: Lakshmi) — answers the call only
- **Caregiver:** teammate/judge in English (daughter Ananya) — watches cockpit
- **Operator:** Arnav (minimal talk) — clicks through cockpit

Props:

- Fixture discharge text on caregiver screen
- Laptop/projector: **caregiver cockpit only** (med graph + ledger + packet)
- Patient phone with working number for outbound agent
- No patient laptop UI

---

## Second-by-second

| Time | Action | System must show |
| --- | --- | --- |
| 0:00–0:20 | Hook: WhatsApp chaos. “This is how post-discharge India runs.” | Optional slide |
| 0:20–0:40 | Pitch: execution OS. Patient never opens an app — we call them. | Title: DAWA |
| 0:40–1:20 | Caregiver: paste discharge. Extract. | Draft med graph 3–5 meds |
| 1:20–1:50 | Caregiver confirms. Activate. | Status = active |
| 1:50–2:00 | Click **Call Lakshmi** (evening dose). | Calling… on cockpit |
| 2:00–2:50 | Patient phone rings. Hindi agent. Taken + pet mein jalan. | Live phone audio |
| 2:50–3:20 | Call ends. Webhook. Policy: no new Rx, escalate. | Cockpit updates |
| 3:20–3:50 | English caregiver packet. | Card from API |
| 3:50–4:20 | Event ledger trail. | Events list |
| 4:20–4:50 | Optional stretch only if solid. | Else skip |
| 4:50–5:10 | Closing lines. Stop talking. | See below |

---

## Closing lines (on screen)

```text
She took the medicine.
The family finally knows what changed.

Discharge is not the end of care. Execution is.
```

---

## Spoken lines (patient — Hindi example)

Agent (TTS):

> Namaste Lakshmi ji. Raat ki BP dawai Amlodipine 5mg lene ka samay ho gaya hai. Kya aapne dawai le li?

Patient (live):

> Haan, le li. Lekin pet mein jalan ho rahi hai.

Agent:

> Samajh gayi. Aapne Amlodipine le li, aur pet mein jalan batayi. Main yeh baat Ananya ko bhej rahi hoon. Kripya dohra mat lena. Agar jalan tez ho ya ulti ho to clinic se baat karein.

Do not let the model invent a new medicine in this turn.
Policy refuses prescription changes.

---

## Caregiver card (English — must match system)

- Med: Amlodipine 5mg
- Status: taken
- Exception: side effect — abdominal burning (“pet mein jalan”)
- Action: logged and escalated
- Suggestions: severity check; clinic if severe; do not double dose

---

## Kill switches (Arnav owns)

1. **Extract fails:** paste pre-extracted JSON via confirm UI or seed activated plan.
2. **STT fails:** retry once; if dead, Jyotir uses typed fallback into complete API (label as degraded, not ideal).
3. **Card empty:** show last packet from fixtures only as disaster recovery — prefer fail honestly and reset.

Never puppet the happy path if live path works in rehearsal.
