# DAWA API (Barkha + Jyotir voice module)

## Owner

- **Barkha:** routes, models, policy, ledger, packets, extract
- **Jyotir:** `src/voice/**`

## Contract

Implement [docs/API_CONTRACT.md](../../docs/API_CONTRACT.md) exactly.

## Run (fill in once scaffolded)

```bash
cd services/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../../.env.example ../../.env   # if not already
uvicorn src.main:app --reload --port 8000
```

## Smoke

From repo root, with API up:

```bash
./scripts/demo-reset.sh
./scripts/smoke-api.sh
```

## Branch

`feat/api` (Barkha), `feat/voice` (Jyotir for voice paths).
