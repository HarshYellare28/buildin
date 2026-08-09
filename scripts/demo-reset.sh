#!/usr/bin/env bash
# Reset demo world state. Safe to run anytime before a rehearsal.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_URL="${API_URL:-http://localhost:8000}"

echo "[dawa] demo-reset against ${API_URL}"

if curl -sf -X POST "${API_URL}/demo/reset" >/dev/null 2>&1; then
  echo "[dawa] API reset OK"
else
  echo "[dawa] WARN: API not up or /demo/reset missing."
  echo "[dawa] Start the API (Barkha), then re-run this script."
  exit 1
fi

echo "[dawa] World clean. Patient=Lakshmi Caregiver=Ananya. Ready for demo path."
