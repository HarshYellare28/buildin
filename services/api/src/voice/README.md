# Voice module (Jyotir) — M6, M7, M8

Live dose-time call: **Sarvam Saaras STT → policy-bound dialogue → Sarvam Bulbul TTS**, with the
outcome written through Barkha's `POST /doses/{dose_id}/complete`.

See [team/Jyotir.md](../../../../team/Jyotir.md) and [docs/DEMO_SCRIPT.md](../../../../docs/DEMO_SCRIPT.md).

---

## Design rule that matters

**The agent's speech is never model-generated.** Every line is a template in `prompts.py` with the
medication name injected from the med graph. A model cannot invent a drug name or give medical
advice on the judged path because it never writes the words that get spoken.

The LLM has exactly one job: classify the patient's transcript into strict JSON. A regex layer runs
first and is sufficient on its own — if Sarvam's LLM endpoint is slow or down mid-demo, the call
still completes correctly. Regex is authoritative for anything safety-relevant; the model can raise
a refusal flag but never clear one.

```
GREET_DOSE ─→ ASK_TAKEN ─→ WAIT_SYMPTOM ─→ CONFIRM_READBACK ─→ END
                  └── one re-ask on unclear, then hand to a human ──┘
```

---

## Files

| File | Role |
| --- | --- |
| `config.py` | Env + model ids. Loads `.env` from the repo root |
| `sarvam_client.py` | `transcribe()` / `synthesize()` / `classify_json()` |
| `prompts.py` | **Every spoken line.** Arnav: retune wording here, nowhere else |
| `classify.py` | Regex (Latin + Devanagari) → optional LLM refinement |
| `dialogue.py` | The 5-state machine |
| `session.py` | Turns, merged outcome, complete payload |
| `complete_client.py` | Barkha's `/doses/{id}/complete` and `/policy/check` |
| `router.py` | `APIRouter(prefix="/voice")` — the mount point |
| `dev_app.py` | Standalone harness app |
| `static/mic.html` | Dev mic page (not the product UI) |
| `verify_sarvam.py` | L0 live check |

---

## Env

All optional except the key; defaults are in `config.py`.

| Var | Default | Note |
| --- | --- | --- |
| `SARVAM_API_KEY` | — | **Required.** Server-side only, never sent to the browser |
| `SARVAM_API_BASE` | `https://api.sarvam.ai` | |
| `SARVAM_STT_MODEL` | `saaras:v3` | |
| `SARVAM_TTS_MODEL` | `bulbul:v3` | |
| `SARVAM_TTS_SPEAKER` | `ritu` | Female voice — the templates use feminine forms (`rahi hoon`) |
| `SARVAM_LLM_MODEL` | `sarvam-105b-conversations` | `sarvam-m` is deprecated; plain `sarvam-105b` reasons for ~10s |
| `DEMO_PATIENT_LANG` | `hi-IN` | |
| `DAWA_API_URL` | `http://127.0.0.1:8000` | Barkha's API. Keep the IP form — see Latency |
| `VOICE_LLM_CLASSIFY` | `1` | Set `0` to run regex-only if the LLM is flaky on demo day |
| `VOICE_LLM_TIMEOUT` | `8` | Short on purpose — a slow classifier must not stall a live call |

---

## Run

```bash
pip install -r requirements.txt          # unified, at the repo root
cd services/api/src
uvicorn voice.dev_app:app --reload --port 8100
```

Then open <http://localhost:8100> for the mic page.

```bash
# L0 — proves the key and both speech APIs are live
cd services/api/src && python -m voice.verify_sarvam
```

---

## For Barkha — mounting

One line in your app:

```python
from voice.router import router as voice_router
app.include_router(voice_router)
```

Everything is namespaced under `/voice/*`, so nothing collides with `docs/API_CONTRACT.md`.

What I need from you:

1. `POST /doses/trigger` returning `dose_id` + the `Medication` object — the web app passes both
   straight into `POST /voice/sessions`. No import-time coupling either way.
2. CORS open for the web origin.
3. **One contract question:** when the patient asks for a double dose, I refuse in dialogue and call
   your `POST /policy/check`. But the complete payload has no field to carry "an extra dose was
   requested and refused" — right now it only reaches you inside `transcript_summary`. If the
   caregiver packet should surface it, we need a contract change; I did not invent a field.

## For Harsh — the voice panel

Three calls, all JSON except the audio turn:

| Call | Purpose |
| --- | --- |
| `POST /voice/sessions` | Start. Body: `{dose_id, medication, patient_name, caregiver_name}` |
| `POST /voice/sessions/{id}/turn` | multipart `audio` (WebM from `MediaRecorder`, no transcoding) |
| `GET  /voice/sessions/{id}` | Poll state / payload |

Every response carries `assistant_text`, `audio_b64` (WAV, play as `data:audio/wav;base64,…`),
`state`, `outcome`, and `complete_payload`. `static/mic.html` is a working reference — copy from it.

`POST /voice/sessions/{id}/turn-text` is the typed disaster fallback. Keep it off the judged path.

---

## Latency

Every `/turn` response carries `timings_ms`. Watch it during rehearsal — ">8s per turn" is a
stated lose condition in `docs/WIN_LOSE_TEST.md`.

Measured on a real audio turn (14s WAV in, full readback out):

| Stage | Now | Note |
| --- | --- | --- |
| `stt` | ~0.5s | Saaras, pooled connection |
| `dialogue` | ~2.0s | **Entirely the failed POST to Barkha's absent API.** ~0ms once it exists |
| `tts` | ~5.8s | Bulbul. Scales with *text length*, not codec or sample rate |
| **total** | **~8.0s** | → **~6.3s** once the backend is up |

Two things learned the hard way, so nobody re-derives them:

- **Codec and sample rate do not affect TTS latency.** wav/mp3 at 16k/24k all generated the same
  200-char line in 6.2–6.3s. Only length matters: 198 chars → 6.2s, 154 → 4.5s, 112 → 4.2s.
  If a turn needs to be faster, shorten the line in `prompts.py`; nothing else moves the needle.
- **`DAWA_API_URL` must be `127.0.0.1`, not `localhost`.** httpx applies its connect timeout per
  address family, so `localhost` burns a wasted IPv6 attempt before IPv4 when the backend is down
  — 4.6s of dead air inside a live call.

## Status

| Verified live against Sarvam | |
| --- | --- |
| Bulbul TTS + Saaras STT round-trip (`verify_sarvam.py`) | ✅ |
| Full audio turn: WAV → STT → dialogue → TTS → contract payload | ✅ |
| Real STT output classifies to `taken` / `side_effect` / `abdominal_burning` | ✅ |
| Devanagari **and** Latin transcripts classify identically | ✅ |
| Double-dose refusal; never recorded as a dose taken | ✅ |
| Mumble → re-asks exactly once → hands to human | ✅ |
| LLM classifier returns valid JSON (`sarvam-105b-conversations`, ~3.4s) | ✅ |

Saaras transcribes the demo line as `हाँ लीली, लेकिन पेट में जलन हो रही है।` — note it renders
"le li" as the single word लीली, and spells jalan as both जलन and जलान across runs. The regexes
cover all of it; do not "tidy" them without re-running `verify_sarvam.py`.

**Not verified:** `POST /doses/{dose_id}/complete` — Barkha's endpoint does not exist yet, so the
write path returns `complete_posted: false` with the connection error on the session. The call
still completes and the payload is correct and waiting.
