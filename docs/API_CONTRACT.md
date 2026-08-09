# DAWA — API contract (hackathon)

**Owner of file:** Arnav (edits only with Barkha + affected person).
**Implementer:** Barkha.
**Consumers:** Harsh (web), Jyotir (voice complete).

Base URL: `http://localhost:8000`
Content-Type: `application/json`

If you need a field that is not here, propose it in chat and update this file **before** coding against a private shape.

---

## Enums (do not freestyle strings)

```text
PlanStatus:     draft | active
DoseStatus:     scheduled | calling | completed | failed
Adherence:      taken | missed | partial
ExceptionType:  none | side_effect | missed_dose | confusion | refused | other
Criticality:    low | med | high
EventType:
  plan_created | plan_activated | dose_triggered | dose_started
  | dose_completed | exception_logged | packet_sent | policy_refused
```

For MVP demo path you only need: `taken` + `side_effect`.

---

## Resources

### Health

```http
GET /health
→ { "ok": true }
```

### People (seeded)

```http
GET /people
→ {
  "patient": {
    "id": "p_lakshmi",
    "display_name": "Lakshmi",
    "role": "patient",
    "languages": ["hi-IN"],
    "phone": "+91..."
  },
  "caregiver": {
    "id": "c_ananya",
    "display_name": "Ananya",
    "role": "caregiver",
    "languages": ["en-IN"],
    "phone": "+91..."
  }
}
```

### Extract draft plan from text

```http
POST /plans/extract
{
  "text": "...discharge text...",
  "source": "paste"
}

→ {
  "plan_id": "plan_demo_1",
  "status": "draft",
  "medications": [ Medication, ... ]
}
```

### Get plan

```http
GET /plans/{plan_id}
→ Plan
```

### Patch draft meds (human edit)

```http
PATCH /plans/{plan_id}
{
  "medications": [ Medication, ... ]
}
→ Plan
```

### Activate (only after human confirm in UI)

```http
POST /plans/{plan_id}/activate
→ { "plan_id": "...", "status": "active", "event_id": "..." }
```

### Trigger evening dose (demo clock)

```http
POST /doses/trigger
{
  "plan_id": "plan_demo_1",
  "medication_id": "med_amlodipine",   // optional; default night high-criticality
  "simulate_time": "evening"
}

→ {
  "dose_id": "dose_1",
  "status": "calling",
  "medication": Medication,
  "event_id": "..."
}
```

### Voice turn (optional server path)

Jyotir may keep STT/TTS client-side or server-side.
If server-side:

```http
POST /doses/{dose_id}/voice-turn
{
  "user_text": "haan le liya, lekin pet mein jalan hai"
}

→ {
  "assistant_text": "...",
  "audio_url": null,
  "partial": {
    "adherence_guess": "taken",
    "exception_guess": "side_effect"
  }
}
```

### Complete dose (source of truth write)

**Only this endpoint** creates final adherence + exception + packet.

```http
POST /doses/{dose_id}/complete
{
  "adherence": "taken",
  "exception_type": "side_effect",
  "patient_reported": "pet mein jalan",
  "normalized_symptom": "abdominal_burning",
  "transcript_summary": "Patient confirmed Amlodipine taken; reported burning in stomach.",
  "confidence": 0.86
}

→ {
  "dose_id": "dose_1",
  "status": "completed",
  "policy": {
    "allowed": true,
    "actions": ["log", "escalate_caregiver"],
    "refused": []
  },
  "packet_id": "pkt_1",
  "event_ids": ["...", "..."]
}
```

Unsafe example the policy must handle if requested:

```http
POST /policy/check
{
  "intent": "double_dose",
  "medication_id": "med_amlodipine"
}
→ {
  "allowed": false,
  "reason": "Cannot double high-criticality medication",
  "must_escalate": true
}
```

### Events (ledger)

```http
GET /events?plan_id=plan_demo_1
→ { "events": [ Event, ... ] }
```

### Latest caregiver packet

```http
GET /packets/latest?plan_id=plan_demo_1
→ CarePacket
```

### Reset demo world

```http
POST /demo/reset
→ { "ok": true }
```

Also exposed via `./scripts/demo-reset.sh`.

---

## Shared types

### Medication

```json
{
  "id": "med_amlodipine",
  "name_raw": "Amlodipine 5mg",
  "name_normalized": "amlodipine",
  "dose": 5,
  "unit": "mg",
  "route": "oral",
  "schedule_text": "Night",
  "times": ["21:00"],
  "food_rule": "none",
  "duration_days": 30,
  "criticality": "high",
  "source": "ocr_or_paste",
  "confidence": 0.9
}
```

### Plan

```json
{
  "id": "plan_demo_1",
  "status": "draft",
  "patient_id": "p_lakshmi",
  "caregiver_id": "c_ananya",
  "medications": []
}
```

### Event

```json
{
  "id": "evt_1",
  "ts": "2026-08-09T20:05:00+05:30",
  "type": "dose_completed",
  "plan_id": "plan_demo_1",
  "dose_id": "dose_1",
  "payload": {}
}
```

### CarePacket

Must match `fixtures/sample-care-packet.json` shape:

```json
{
  "id": "pkt_1",
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
  "needs_clinician": false,
  "language": "en-IN"
}
```

---

## Policy kernel rules (MVP)

| Intent / event | Autonomous action | Escalate |
| --- | --- | --- |
| Confirmed taken | Log | No |
| Side effect reported | Log + caregiver packet | Yes |
| Double dose request | Refuse | Yes |
| Stop high-critical med | Refuse silent stop | Yes |
| Invent new prescription | Refuse | Yes |

Implement as plain functions in `services/api/src/policy/`.
Not free-form model decisions.

---

## Error shape

```json
{
  "error": {
    "code": "PLAN_NOT_ACTIVE",
    "message": "Activate plan before triggering dose"
  }
}
```

---

## Change control

1. Propose field change in team chat.
2. Arnav updates this file on `main` or merges contract PR first.
3. Barkha implements.
4. Harsh / Jyotir pull and adapt.

Do not ship UI against undocumented fields.
