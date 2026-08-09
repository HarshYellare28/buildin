#!/usr/bin/env bash
# Contract smoke path without voice. Barkha/Arnav use this before calling E2E green.
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEXT="$(cat "${ROOT}/fixtures/discharge-messy.txt")"

echo "[smoke] health"
curl -sf "${API_URL}/health" | grep -q ok

echo "[smoke] reset"
curl -sf -X POST "${API_URL}/demo/reset" >/dev/null

echo "[smoke] extract"
PLAN_JSON=$(curl -sf -X POST "${API_URL}/plans/extract" \
  -H 'Content-Type: application/json' \
  -d "$(python3 -c "import json,sys; print(json.dumps({'text': sys.stdin.read(), 'source': 'paste'}))" <<<"${TEXT}")")
PLAN_ID=$(python3 -c "import json,sys; print(json.load(sys.stdin)['plan_id'])" <<<"${PLAN_JSON}")
echo "  plan_id=${PLAN_ID}"

echo "[smoke] activate"
curl -sf -X POST "${API_URL}/plans/${PLAN_ID}/activate" >/dev/null

echo "[smoke] trigger"
DOSE_JSON=$(curl -sf -X POST "${API_URL}/doses/trigger" \
  -H 'Content-Type: application/json' \
  -d "{\"plan_id\": \"${PLAN_ID}\", \"medication_id\": \"med_amlodipine\", \"simulate_time\": \"evening\"}")
DOSE_ID=$(python3 -c "import json,sys; print(json.load(sys.stdin)['dose_id'])" <<<"${DOSE_JSON}")
echo "  dose_id=${DOSE_ID}"

echo "[smoke] complete side_effect"
curl -sf -X POST "${API_URL}/doses/${DOSE_ID}/complete" \
  -H 'Content-Type: application/json' \
  -d '{
    "adherence": "taken",
    "exception_type": "side_effect",
    "patient_reported": "pet mein jalan",
    "normalized_symptom": "abdominal_burning",
    "transcript_summary": "Patient confirmed Amlodipine taken; reported burning in stomach.",
    "confidence": 0.86
  }' >/dev/null

echo "[smoke] packet"
curl -sf "${API_URL}/packets/latest?plan_id=${PLAN_ID}" | grep -q side_effect

echo "[smoke] events"
curl -sf "${API_URL}/events?plan_id=${PLAN_ID}" | grep -q plan_activated

echo "[smoke] PASS"
