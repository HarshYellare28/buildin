# DAWA API (Barkha + Jyotir voice module)

## Owner

- **Barkha:** routes, models, policy, ledger, packets, extract
- **Jyotir:** `src/voice/**`

## Contract

Implement [docs/API_CONTRACT.md](../../docs/API_CONTRACT.md) exactly.

## Run

```bash
cd services/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill SARVAM_API_KEY
uvicorn src.main:app --reload --port 8000
```

Health check: `curl localhost:8000/health`

## What's implemented so far

- `GET /health`, `GET /people`, `POST /demo/reset`
- `POST /plans/extract` (multipart/form-data — see below)
- `GET /plans/{id}`, `PATCH /plans/{id}`, `POST /plans/{id}/activate`

Doses/events/packets/policy (M5–M11) are not implemented yet — the cockpit
still simulates that part of the flow client-side. This closes the loop for
**ingest only**: paste or photo → real med graph.

## Photo ingest (Sarvam Doc AI)

`POST /plans/extract` (multipart/form-data):
- `source=ocr`, `file=<image or pdf>` — calls Sarvam Doc AI
  (`POST /doc-ai/v1/job/extract`, polled via `GET /doc-ai/v1/job/{id}/results`)
  with a JSON schema asking for a `medications` array, then maps each
  extracted drug name onto `fixtures/formulary.json` for the clinical fields
  (criticality, food rule, route) the demo formulary already knows.
- `source=paste`, `text=<discharge text>` — matches formulary drug names
  found in the pasted text (no LLM call, keeps the paste path instant).

Drugs the OCR finds that aren't in the demo formulary are still returned
(as a low-confidence, flagged entry) rather than silently dropped — the
human-confirm step in the UI is the safety gate, not the extractor.

Note: this deviates slightly from `docs/API_CONTRACT.md`'s pure-JSON
`/plans/extract` body — file upload needs multipart, so both the `text` and
`source` fields moved to form fields too, for one consistent content type.
Flag in team chat if the JSON-only shape needs to be preserved for another
consumer.

## Smoke

From repo root, with API up:

```bash
./scripts/demo-reset.sh
./scripts/smoke-api.sh
```

## Branch

`feat/api` (Barkha), `feat/voice` (Jyotir for voice paths).
