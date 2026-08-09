# DAWA — Demo script (~5 minutes)

Cast:

- **Patient:** teammate speaking Hindi (elder persona: Lakshmi)
- **Caregiver:** teammate/judge in English (daughter Ananya in Mumbai)
- **Operator:** Arnav (minimal talk)

Props:

- Fixture discharge text on screen (messy Hindi/English mix)
- Laptop: cockpit (med graph + ledger + caregiver card)
- Mic for live patient voice

---

## Second-by-second

| Time | Action | System must show |
| --- | --- | --- |
| 0:00–0:20 | Hook: chaotic family WhatsApp / verbal chaos. “This is how post-discharge India runs.” | Optional static slide |
| 0:20–0:40 | One breath pitch: execution OS, not companion. | Title: DAWA |
| 0:40–1:20 | Paste discharge fixture. Extract runs. | Draft med graph 3–5 meds |
| 1:20–1:50 | Human confirm. Activate. Caregiver already linked. | Status = active |
| 1:50–2:00 | Jump clock to evening dose. | Dose session starts |
| 2:00–2:50 | Live call in Hindi: confirm Amlodipine. Patient: took it, pet mein jalan. | Real STT/TTS |
| 2:50–3:20 | Exception protocol. No new Rx. Escalate. | Policy actions visible if possible |
| 3:20–3:50 | Caregiver card in English. | Card from API |
| 3:50–4:20 | Show ledger trail. | Events list |
| 4:20–4:50 | Optional stretch only if solid. | Else skip |
| 4:50–5:10 | Closing lines on screen. Stop talking. | See below |

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
