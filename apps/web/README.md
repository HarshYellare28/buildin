# DAWA Web cockpit (Harsh)

## Owner

**Harsh** — `apps/web/**` only.

## Run (fill in once scaffolded)

```bash
cd apps/web
npm install
cp ../../.env.example ../../.env   # ensure NEXT_PUBLIC_API_URL
npm run dev
```

Open http://localhost:3000

## Panels required

1. Ingest (paste + extract)
2. Med graph confirm + activate
3. Roles
4. Jump to evening dose
5. Voice slot (Jyotir)
6. Caregiver packet
7. Event ledger
8. Reset demo

## Branch

`feat/web`

## Rule

Packet and ledger data come from the API on the real path.
No silent hardcoded happy-path card on `main`.
