# DAWA caregiver cockpit

This is the only product UI. The patient never opens a web page; the patient
interaction belongs to the phone voice agent.

## Run

```bash
cp .env.example .env.local
npm ci
npm run dev
```

Open <http://localhost:3000>. Run the FastAPI service on port 8000 first.

The production path is:

```text
extract -> confirm/activate -> Sarvam Instant Outbound -> patient phone
        -> authenticated webhook -> caregiver packet + backend ledger
```

`NEXT_PUBLIC_DEV_MODE=1` exposes a clearly labelled disaster fallback. It runs
the fixed demo utterance through the real voice classifier and completion API;
it is not the judged phone-call path.

## Important boundary

With `NEXT_PUBLIC_DEV_MODE=0`, `Call Lakshmi` creates a dose and asks the DAWA
API to place the configured Sarvam Instant Outbound call. The patient still has
no web microphone or patient UI. The typed voice session exists only as the
explicitly labelled disaster fallback.

The caregiver chooses any active-plan medication and can call immediately;
this is not restricted to the medication's scheduled time. After Sarvam posts
the completion webhook, **Check outcome & transcript** loads the complete set
of transcript lines delivered by Sarvam alongside the packet and ledger.
