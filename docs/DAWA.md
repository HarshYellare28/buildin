# DAWA

**Medication execution OS for Indian families after a hospital or clinic visit.**

Tagline: Hospitals write prescriptions. Families guess. DAWA runs the meds.

---

## 1. One-line pitch

After a visit, DAWA turns messy discharge advice into a living medication plan that coordinates the patient, caregiver, and refill path - in the languages they actually speak - and only marks "done" when the right action happened.

---

## 2. 15-second pitch

Hospitals write prescriptions.
Families guess.
DAWA runs the medication after the visit - patient, caregiver, chemist, and the exceptions - in the languages they actually speak.

---

## 3. 60-second pitch

India does not fail healthcare only in the consultation room.
It fails in the 72 hours after, when a scribbled discharge note meets polypharmacy, code-mixed instructions, a daughter in another city, chemist substitutions, and a missed evening dose.

DAWA is not a wellness companion and not a diagnosis bot.
It is a medication execution system.

You photograph the discharge summary or speak what the doctor said.
DAWA builds a living med graph: drug, dose, timing, with or without food, duration, warnings.
It assigns roles - patient takes, caregiver oversees, clinician receives deltas only.
It calls the patient in their language at dose time.
If something is wrong - side effect, missed dose, confusion - it escalates to the caregiver with a structured packet, not a raw transcript dump.
It can trigger an allowlisted refill path and payment when the family authorizes it.

Rakshak remembered trends for the doctor.
Yaadein held memories for the family.
DAWA makes the medication plan actually execute across people who do not share a language or a city.

---

## 4. Why this wins (vs previous Top 15 and gallery)

### What already won in health / elder

| Project | Shape | What it owned |
| --- | --- | --- |
| Rakshak | Daily voice check-in | Longitudinal clinical signal for doctor |
| Yaadein | Memory companion | Emotional continuity for elder + family |
| Drishti | Accessibility | Dignity through audio description |

### Why DAWA is not a clone

| Dimension | Rakshak | Yaadein | DAWA |
| --- | --- | --- | --- |
| Core job | Observe health trend | Hold life memories | Execute medication plan |
| Primary user loop | Elder → doctor | Elder → family emotional load | Patient + caregiver + (optional) chemist/clinic |
| Output | Trend / alert | Memory continuity | Dose events, exceptions, refills, audit trail |
| Multi-human | Light | Light | Core product |
| Money / logistics | No | No | Optional but natural (refill pay) |
| Failure it prevents | Silent clinical drift | Lost stories / burnout | Wrong dose, missed dose, unread discharge, family chaos |

### Saturated ideas we refuse

- Daily friendly chat companion
- "Memory so family doesn't have to" (Yaadein)
- Pure symptom diary without execution (Rakshak-shaped)
- AI doctor / diagnosis bot
- Wellness coach
- Generic appointment booking agent
- "Call dadi every morning" with no med graph

### Gallery lesson we are using

Winners had: one human job, vernacular voice, grounded state, irreversible outcome.
Wrappers had: talk → answer.

DAWA's irreversible outcomes:

- Med schedule exists
- Dose event logged
- Caregiver escalated with structured delta
- Refill paid / ordered (if in scope)
- Clinician packet generated

---

## 5. Problem

### The real failure mode

Post-visit medication collapse in Indian homes:

1. Discharge notes are handwritten, bilingual, incomplete, or verbal only.
2. Patients leave confused; caregivers were outside or on a call.
3. Multiple medicines, timings, food rules, duration.
4. Patient speaks Kannada/Hindi/Tamil; adult child speaks English in another city.
5. Chemist substitutes brands; packaging looks different; trust breaks.
6. Missed evening dose or "pet mein jalan" gets handled ad hoc on WhatsApp.
7. Doctor never sees execution reality - only the next visit story.

### Who hurts

- Elderly patients on 4–10 meds
- Post-discharge cardiac / diabetes / infection patients
- Sandwich-generation caregivers coordinating from another city
- Small clinics and hospitals with no adherence infrastructure
- Chemists stuck in chaotic family clarification calls

### Why existing tools fail

| Tool | Gap |
| --- | --- |
| Phone alarms | No understanding of "with food", interactions, side effects, multi-person roles |
| English health apps | Wrong language, wrong literacy, wrong family structure |
| WhatsApp family groups | Chaos, no source of truth, no audit, no structured escalation |
| Hospital apps | Rarely used post-discharge; not vernacular-first |
| Pill boxes | Physical only; no caregiver loop |
| ChatGPT | Advice without accountable multi-party execution state |

### Why now

- Sarvam-class Indic STT/TTS makes code-mixed dose conversations reliable enough to productize.
- Families already coordinate care by voice notes - we structure that behaviour instead of replacing love with a dashboard.
- Agentic payments (Razorpay) make caregiver-authorized refill spend possible without forcing elders through UPI UI.
- Hackathon and market both reward agents that **do**, not answer.

---

## 6. Product definition

### What DAWA is

A **medication execution OS** with:

1. **Ingest** - photo of Rx / discharge + spoken clarification
2. **Med graph** - structured schedule and constraints
3. **Role graph** - patient, caregiver(s), optional clinician
4. **Execution loop** - dose-time voice sessions
5. **Exception protocol** - side effect, miss, confusion, substitution
6. **Escalation packet** - caregiver / clinician gets deltas, not surveillance
7. **Optional fulfillment** - allowlisted refill + payment
8. **Audit ledger** - what was said, decided, done

### What DAWA is not

- Not a diagnostic doctor
- Not autonomous prescription changing
- Not continuous home mic surveillance
- Not a wellness / meditation product
- Not "another reminder app with Hindi TTS"

### North-star user moment

> Amma took the evening BP medicine.
> She mentioned acidity.
> I got a 20-second brief in English on my phone with what changed and what to do next - without listening to a 4-minute voice note dump.
> Tomorrow's schedule already adjusted pending doctor flag.

---

## 7. Users and roles

| Role | Needs | Interface |
| --- | --- | --- |
| **Patient** | Simple voice, mother tongue, minimal UI | Inbound/outbound voice call or push-to-talk |
| **Primary caregiver** | Oversight, exceptions, payments, appointments | App / WhatsApp / voice summary |
| **Secondary family** | Limited visibility | Invite-only summary |
| **Clinician** (stretch) | Trend + adherence exceptions, not chat logs | Dashboard packet / PDF |
| **Chemist** (stretch) | Clear refill list | Call or structured order |

### Design principle

The patient never has to "use an app well."
The caregiver never has to re-explain the discharge note every night.
The system never improvises clinical decisions outside policy.

---

## 8. Core primitive

**Unstructured clinical instruction + multi-human household → executable medication world state → verified real-world actions.**

Sub-primitives:

- Document/voice → med graph
- One plan → many role-specific interfaces
- Dose time → conversational verification
- Exception → structured multi-party response
- Authorization → money/refill movement
- Episode history → clinician-readable delta

---

## 9. Holy shit demo (live)

### Cast

- **Patient:** teammate speaking Kannada or Hindi (elder persona)
- **Caregiver:** teammate/judge in English, "daughter in Mumbai"
- **Operator:** demo narrator (minimal talking)
- Optional: chemist persona on a second phone

### Props

- Printed messy discharge summary (Hindi/English mix)
- Phone for patient call
- Phone/laptop for caregiver alerts
- Big screen: med graph + event timeline + role panel

### Second-by-second (about 5 minutes)

| Time | Action |
| --- | --- |
| 0:00–0:20 | Hook: show chaotic family WhatsApp about meds. "This is how post-discharge India runs." |
| 0:20–0:40 | Pitch in one breath: execution OS, not companion. |
| 0:40–1:20 | Photo discharge sheet. Patient adds by voice: doctor also said skip antibiotic if stomach upset. |
| 1:20–1:50 | Screen builds med graph live (3–5 meds, times, food rules, duration). Caregiver linked. |
| 1:50–2:00 | Jump clock to evening dose. |
| 2:00–2:50 | DAWA calls patient in Kannada/Hindi. Confirms BP pill. Patient: took it, but pet mein jalan. |
| 2:50–3:20 | Exception protocol: mark side effect, do **not** invent a new prescription. Flag interaction / food guidance from allowlisted rules. |
| 3:20–3:50 | Caregiver gets English voice or card: what happened, which med, confidence, suggested next step (observe / call clinic / hold X only if policy allows). |
| 3:50–4:20 | Stretch: caregiver authorizes refill/OTC antacid from allowlist OR books callback. Razorpay tiny payment optional. |
| 4:20–4:50 | Show audit ledger + clinician packet: 1-page delta, not full audio dump. |
| 4:50–5:10 | Close line on screen. Stop talking. |

### Closing line on screen

# She took the medicine.
# The family finally knows what changed.

Subtitle: **Discharge is not the end of care. Execution is.**

---

## 10. Why Sarvam is load-bearing

If you replace Sarvam with English-only STT/TTS, DAWA dies for the real user.

| Capability | Use in DAWA |
| --- | --- |
| Saaras streaming STT | Dose calls, code-mix, noisy home audio |
| Speaker-aware / multi-turn voice | Patient vs caregiver sessions |
| Bulbul TTS | Natural outbound dose calls in Indic languages |
| Docs / Vision | Discharge sheets, Rx photos, medicine strips |
| Translation | Patient language ↔ caregiver language packets |
| Sarvam LLM (30B/105B) | Extraction, exception classification, packet writing under policy |

Sarvam is not a skin.
It is how clinical-adjacent household speech becomes structured state.

---

## 11. Agentic execution (what it actually DOES)

1. Extracts meds and constraints from image + speech
2. Builds and version-controls a med graph
3. Schedules dose sessions
4. Places or receives voice interactions at dose time
5. Verifies adherence conversationally (not only "tap yes")
6. Classifies exceptions against a policy ruleset
7. Notifies caregiver with structured delta
8. Optionally triggers refill / payment / clinic callback
9. Writes immutable event log
10. Compiles clinician-facing summary on demand

---

## 12. OpenClaw test

**Why isn't this OpenClaw + reminders?**

OpenClaw can set timers and send messages.
It does not own:

- A medication ontology with safety gates
- Multi-role care authorization (who can change what)
- Exception protocols that refuse unsafe improvisation
- Cross-language caregiver packets
- Audit-grade clinical-adjacent event ledger
- Policy kernel between model and action ("never autonomously stop cardiac med without clinician path")

DAWA is a **vertical care execution system** with voice limbs.
Not a general agent with a pill plugin.

---

## 13. Privacy and safety architecture

### Privacy principles

- Explicit enrollment by patient or legal caregiver
- No continuous ambient mic
- Session-bound listening (dose window / user initiated)
- Role-based visibility (elder can hide topics from some family members later)
- Caregiver invite links, not phonebook scraping
- Raw audio retention policy: short by default; derived events kept longer
- No selling health data

### Safety principles (non-negotiable)

- DAWA does **not** diagnose
- DAWA does **not** invent new prescriptions
- DAWA does **not** silently stop critical meds
- Model suggestions are filtered by a **policy kernel** (deterministic rules where possible)
- High-risk exceptions → human caregiver / clinician path
- Demo uses allowlisted meds + clearly labeled simulated clinical rules
- Always show uncertainty ("I heard X with medium confidence - confirm")

### Policy kernel examples

| Event | Allowed autonomous action | Must escalate |
| --- | --- | --- |
| Confirmed dose taken | Log event, thank patient | No |
| Missed dose (non-critical, policy) | Reschedule guidance if rules allow | Caregiver notify |
| Side effect reported | Log + caregiver packet + "contact clinic if..." | Yes |
| Patient asks "should I double dose?" | Refuse; explain; escalate | Yes |
| Brand substitution at chemist | Map if in equivalence table; else hold + ask caregiver | Often yes |

---

## 14. Existing alternatives and difference

| Alternative | Difference |
| --- | --- |
| Medisafe / reminder apps | English-first, single user, weak Indian discharge reality |
| Hospital apps | Low post-discharge engagement; not multi-language family ops |
| WhatsApp families | No structure, no verification, no audit |
| Rakshak-like products | Observation, not medication execution graph |
| Nurse care management (human) | Works but does not scale; expensive; not always vernacular-matched |
| ChatGPT health chat | Advice without accountable multi-party state machine |

---

## 15. Technical architecture

```text
[Ingest]
  Rx / discharge photo → Sarvam Vision / Docs
  Spoken clarification → Saaras STT
        ↓
[Extraction Agent]
  meds, dose, route, frequency, duration, food rules, warnings
  confidence per field
        ↓
[Med Graph Store]  (source of truth)
  Medication nodes + schedule + constraints + version history
        ↓
[Role & Auth Service]
  patient, caregivers, clinician; permissions; contacts
        ↓
[Scheduler]
  dose windows, timezone, quiet hours, retry policy
        ↓
[Voice Runtime]
  outbound/inbound call or in-app voice
  Saaras STT + policy-bound LLM + Bulbul TTS
        ↓
[Exception Classifier + Policy Kernel]
  taken / missed / partial / side_effect / confused / refused
  deterministic allow/deny on actions
        ↓
[Orchestrator]
  caregiver notify, clinic flag, refill flow, payment
        ↓
[Ledger + Packets]
  immutable events
  caregiver cards
  clinician summary
```

### Suggested stack (hackathon-realistic)

| Layer | Choice |
| --- | --- |
| Speech | Sarvam Saaras + Bulbul |
| LLM | Sarvam 30B/105B (or Indus) for extraction + dialogue under policy |
| Docs | Sarvam Vision / Docs AI |
| Backend | FastAPI or Node (TypeScript) |
| DB | Postgres (med graph + events) |
| Realtime | WebSocket for demo board |
| Voice transport | WebRTC in-app **or** Exotel/Twilio/Vobiz for phone calls |
| Caregiver channel | WhatsApp Business **or** web push + voice note |
| Payments (stretch) | Razorpay payment links / agentic pay for refill |
| Frontend | Next.js demo cockpit (med graph + timeline) |

### Data models (MVP)

**Medication**

- id, name_raw, name_normalized, dose, unit, route
- schedule (cron-like or explicit times)
- food_rule, duration_days, start_at, end_at
- criticality (low/med/high)
- source (ocr | voice | manual), confidence

**Person / Role**

- id, display_name, languages[], phone
- role: patient | caregiver | clinician
- permissions

**DoseEvent**

- medication_id, scheduled_at, status
- transcript_summary, exception_type
- confidence, notified_roles[]

**CarePacket**

- event_ids[], language, channel, content_structured

---

## 16. Hard engineering problems (proof of depth)

1. **Reliable extraction** from ugly Indian discharge sheets + code-mixed speech
2. **Number and drug-name fidelity** (never turn 25mg into 250mg)
3. **Policy kernel** that blocks unsafe model improvisation
4. **Multi-party state** consistent across patient call and caregiver alert
5. **Latency** on live dose call with STT → reason → TTS
6. **Exception dialogue** that feels human but stays inside rails
7. **Demo reliability** under noisy speech and telephony

These are the components that make judges say "they actually built a system," not a wrapper.

---

## 17. MVP vs stretch

### MVP (hackathon must-ship)

1. Upload / photo discharge OR paste text + voice clarification
2. Extract 3–5 meds into editable med graph (human confirm step)
3. Link one patient + one caregiver
4. Trigger one live dose session (call or in-app voice)
5. Patient confirms taken + reports one side effect in Indic language
6. Caregiver receives structured English (or chosen language) alert card
7. Event ledger on screen
8. Clinician-style 1-page summary generation

### Stretch (only if MVP solid)

- True PSTN outbound calls
- Second caregiver permissions
- Allowlisted refill + Razorpay
- Drug interaction table (small, hardcoded for demo set)
- Strip photo verification ("show the blister")
- Multi-day simulated timeline scrubber
- WhatsApp caregiver channel
- Offline SMS fallback

### Explicitly out of scope for hackathon

- Autonomous Rx changes
- Full EHR integrations
- Legal medical device claims
- Diagnosing conditions
- Supporting all of India's formulary perfectly

---

## 18. 24-hour team execution plan

Assume 4 people: **A** product/demo, **B** speech/voice, **C** backend/graph, **D** UI/packets.

### Hour 0–2: Freeze

- Demo script locked
- 1 discharge sheet designed (readable but messy)
- 4-med demo formulary locked
- Exception path locked: acidity after BP med
- Languages locked: patient Hindi/Kannada, caregiver English
- Success definition: live patient voice → caregiver packet without manual puppeting of content

### Hour 2–6

- C: Postgres schema + med graph API
- B: Sarvam STT/TTS loop working on one dialogue
- D: Cockpit UI skeleton (graph + timeline)
- A: discharge fixtures + caregiver card copy templates

### Hour 6–12

- Extraction pipeline (OCR/Vision + LLM → JSON meds)
- Confirm/edit UI for med graph (safety: human-in-loop before activation)
- Dose session state machine
- Caregiver alert generation

### Hour 12–16

- Full E2E dry run
- Policy kernel v1 (refuse double-dose, escalate side effect)
- Number fidelity tests
- Demo clock jump ("simulate evening")

### Hour 16–20

- Polish UI theatre (phase change is half the win)
- Failure handling: STT miss → confirm repeat
- Recording backup only as disaster recovery (prefer live)

### Hour 20–24

- 10 rehearsals
- Chaos drills: patient mumbles, says wrong drug, caregiver offline
- One person owns the "kill switch" to manual confirm med graph if OCR fails live

---

## 19. What must be real vs mocked

| Component | Status |
| --- | --- |
| Sarvam STT on patient speech | **REAL** |
| Sarvam TTS on agent speech | **REAL** |
| Med graph as source of truth | **REAL** |
| Exception → caregiver structured packet | **REAL** |
| Human confirm of extracted meds before activation | **REAL** (feature, not shame) |
| Full pharmacy network | **MOCK** |
| EHR writeback | **MOCK** |
| Exhaustive drug interaction DB | **MOCK** small table |
| PSTN calling | Prefer real; in-app voice acceptable if clearly live |
| Payment | Optional real small Razorpay |
| "Doctor on backend" | Simulated clinic policy, labeled honestly |

---

## 20. Failure modes (and pre-emptive fixes)

| Failure | Fix |
| --- | --- |
| OCR wrong dose | Mandatory confirm step; highlight low-confidence fields in red |
| Judges say "it's just reminders" | Show exception multi-party packet + med graph versioning |
| Judges say "medical liability" | Policy kernel + no autonomous Rx change + escalation |
| Judges say "Rakshak 2.0" | One slide: observe vs execute comparison |
| STT fails live | Confirmation read-back every critical field |
| Looks like WhatsApp summary bot | Live patient call must be the centrepiece |
| Over-scoped formulary | Only demo drugs exist in system |
| Creepy surveillance read | Explicit session windows; show privacy panel |

---

## 21. Judge attack questions and killer answers

### 1) "Isn't this just Rakshak / a reminder app?"

Rakshak observes health trends for a clinician.
Reminder apps beep.
DAWA maintains a medication world state and runs multi-person execution: verification, exceptions, caregiver packets, optional fulfillment.
The demo ends with an audit of what was taken and what changed for the family - not a chat log.

### 2) "What if the model gives dangerous medical advice?"

The model is not allowed to freely practice medicine.
A policy kernel sits between dialogue and actions.
It can log, remind, escalate, and explain.
It cannot invent prescriptions or silently stop high-criticality meds.
Unsafe requests are refused and escalated.

### 3) "Why can't the daughter just call her mother?"

She can - until she is in 12 meetings, two siblings contradict each other, the discharge paper is lost, and nobody knows whether the evening dose happened.
DAWA is the shared execution layer so love does not have to also be project management.

### 4) "Why Sarvam?"

Because the patient will not adhere in English UI English TTS.
Dose confirmation, side-effect description, and discharge speech are code-mixed Indic reality.
If speech fails, the product fails.

### 5) "Is this a wrapper on Sarvam Voice?"

Sarvam is the speech layer.
The product is the med graph, roles, policy kernel, scheduler, escalation packets, and ledger.
Without those, voice is a gimmick.

---

## 22. GTM sketch (secondary to demo, but real)

### Beachhead

- Post-discharge cardiac / diabetes elderly + one urban caregiver child
- Private hospitals / nursing homes wanting differentiation on aftercare
- Multi-city families (parent in tier-2, kids in Bengaluru/Mumbai)

### Wedge

- Start with **episode mode**: 14 days after discharge, not lifetime companion
- Hospital or clinic enrolls family at discharge desk in 3 minutes
- Caregiver pays subscription or hospital bundles into package

### Why it can expand

- From meds → labs → follow-up visits → insurance documents
- From one caregiver → full RISHTA-like family care graph later
- B2B2C through hospitals beats pure consumer download

Do not pitch GTM longer than 20 seconds in the hackathon unless asked.

---

## 23. Scoring (internal)

| Dimension | Score / 10 | Note |
| --- | --- | --- |
| Novelty | 8 | Execution OS is fresher than companion |
| Wow factor | 9 | Live call + caregiver packet is memorable |
| Technical depth | 9 | Graph + policy + multi-party voice |
| Sarvam fit | 10 | Existential |
| Real value | 10 | National-scale aftercare failure |
| Demo reliability | 7 | Needs disciplined MVP |
| Defensibility | 8 | Data + protocol + hospital wedge |
| Saturation risk | 6 | Must constantly differentiate from Rakshak |

---

## 24. Positioning vs other ideas we considered

| Idea | Relation to DAWA |
| --- | --- |
| BOLI / live vendor market | Stronger pure market wow; different domain |
| RISHTA (family care governance) | Broader family politics; DAWA can be the med module inside RISHTA later |
| ROUND (OPD triage) | Facility-side; DAWA is home-side aftercare |
| JACHA (72h discharge OS) | DAWA is the sharpest wedge of JACHA focused on meds |
| MORPH | Not health; different thesis |

**Decision:** Build DAWA as the sharp product.
Keep RISHTA/JACHA as future platform story only if judges ask "what's next?"

---

## 25. Brand and naming

**DAWA** works in India immediately (medicine / treatment).

Alternatives if trademark / conflict:

- Matra
- Sevan
- Aushadh
- AfterCare (too English)
- DoseSaathi (more companion-coded - weaker)

Recommended demo identity:

- Product: **DAWA**
- Line: **Medication, executed.**
- Color/UI: clinical calm, not consumer gimmick neon

---

## 26. Success criteria for the hackathon

We win the room if judges leave saying:

1. "They actually called the patient and the family state updated."
2. "It's not another elder chatbot."
3. "I would enroll my parents."

We fail if they leave saying:

1. "Cute reminders."
2. "Rakshak with a prescription photo."
3. "What if it gives medical advice wrong?" and we freeze.

---

## 27. Immediate next actions for the team

1. Lock demo languages and 4-med formulary today.
2. Draft the discharge sheet PDF/photo asset.
3. Implement med graph schema + confirm UI first (safety spine).
4. Get Sarvam STT/TTS API keys and a 60-second dose dialogue working.
5. Write policy kernel as plain rules before fancy agent reasoning.
6. Build caregiver packet template (structured JSON → pretty card).
7. Rehearse the side-effect exception until it is boringly reliable.
8. Prepare the one-slide "not Rakshak / not Yaadein" comparison.

---

## 28. Appendix A - Demo formulary (example)

Use a small fixed set so extraction and policy stay reliable.

| Med (demo) | Schedule | Notes |
| --- | --- | --- |
| Amlodipine 5mg | Night | Criticality high; do not double |
| Metformin 500mg | Morning + night with food | Acidity complaint path |
| Atorvastatin 10mg | Night | |
| Antibiotic (demo) | 5 days | Patient may report stomach upset → escalate, do not freestyle stop without protocol |
| Paracetamol 500mg | SOS fever | Allowlisted OTC path optional |

Exact names can be localized.
Keep the count small.

---

## 29. Appendix B - Caregiver packet schema (example)

```json
{
  "patient_name": "Lakshmi",
  "event_time": "2026-08-09T20:05:00+05:30",
  "medication": "Amlodipine 5mg",
  "status": "taken",
  "exception": {
    "type": "side_effect",
    "patient_reported": "pet mein jalan",
    "normalized": "abdominal_burning"
  },
  "system_action": "logged_and_escalated",
  "suggested_caregiver_actions": [
    "Ask if burning is severe or with vomiting",
    "If severe, contact clinic on-call",
    "Do not double next dose"
  ],
  "confidence": 0.86,
  "needs_clinician": false
}
```

---

## 30. Appendix C - One-slide differentiators

**DAWA is medication execution.**

- Not diagnosis
- Not memory companion
- Not trend-only check-ins
- Multi-human by default
- Policy-bounded agent
- Audit ledger you can show a doctor

---

## Document status

- **Status:** Working product brief for build
- **Intent:** Align team on scope, demo, architecture, and kill criteria
- **Next doc to add if needed:** API contracts, prompt library, exact demo script with spoken lines in Hindi/Kannada/English
