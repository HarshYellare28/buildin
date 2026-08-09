# Product pivot (locked)

**Date:** mentor round after “product makes sense”

---

## New rule

| Role | Interface |
| --- | --- |
| **Patient** | **Voice only** — Sarvam calling agents (phone). **No patient app UI.** |
| **Caregiver / family / operator** | **All UI** — med graph, confirm, packets, ledger, trigger call |
| **Clinician** (stretch) | Summary from caregiver-side system |

Patient never logs in. Patient never taps “I took it.”  
Phone rings → talk → hang up. Family sees the outcome.

---

## Why this is better

- Matches real elders (low app literacy)
- Demo is visceral: **phone rings**
- Clear split: voice agent = patient limb; cockpit = family OS
- Mentor-friendly: not “another chatbot app for dadi”

---

## Full flow (simple)

```text
1. Caregiver/operator: paste Rx → extract → confirm → activate
2. Caregiver/operator: "Call for evening dose"
3. Sarvam calling agent dials PATIENT phone (Hindi)
4. Patient talks only on the phone
5. Call ends → webhook → our backend
6. Caregiver UI: packet + ledger update (English)
   No patient screen involved at any step
```

---

## What we build

| Surface | Who | What |
| --- | --- | --- |
| **Care cockpit UI** | Harsh | Ingest, graph, roles, trigger call, packet, ledger |
| **Backend** | Barkha | Plan, events, policy, webhook ingest, packet |
| **Calling agent** | Jyotir (+ Arnav agent script) | Dose dialogue, extract vars, hard safety rails |
| **Demo/fixtures** | Arnav | Numbers, script, kill switches |

**Out:** patient web/app screens, patient login, patient “tap taken”

---

## Data path

```text
Sarvam call
  → webhook (transcript + agent_variables + status)
  → DAWA API
  → events + caregiver packet
  → cockpit UI refreshes
```

Patient data on call: **Sarvam** (recording/transcript in their analytics).  
Care state of truth: **our DB** after webhook.

---

## Demo script change

- Patient actor only needs a **phone**
- Big screen = **caregiver cockpit only**
- Operator clicks “Call Lakshmi” → phone rings live

---

## Risk

| Risk | Mitigation |
| --- | --- |
| Call fails / NDNC / no answer | Pre-test numbers; backup: agent **test playground** or one recorded path labeled disaster-only |
| Agent invents meds | Hard system prompt + only allowlisted actions; map variables server-side with policy kernel |
| Webhook late | UI shows “calling…” then polls; timeout message |

---

## Judge line

> The patient never opens an app. DAWA calls them. The family runs care from the cockpit.
