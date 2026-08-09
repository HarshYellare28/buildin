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

The real path is:

```text
extract -> confirm/activate -> trigger dose -> voice outcome
        -> caregiver packet + backend ledger
```

`NEXT_PUBLIC_DEV_MODE=1` exposes a clearly labelled disaster fallback. It runs
the fixed demo utterance through the real voice classifier and completion API;
it is not the judged phone-call path.

## Important boundary

`Call Lakshmi` creates the dose and DAWA voice session. A real phone ring still
requires a telephony transport (LiveKit/Twilio or Exotel) connected to the
Sarvam STT/TTS pipeline. Do not replace that with a patient web microphone.
