#!/usr/bin/env bash
# Único test E2E del stack (decisión §24 de 00_decisiones_tecnicas.md).
# Valida los endpoints clave de la API contra un stack ya levantado.
#
# Uso:
#   bash scripts/smoke_test.sh
#   API=http://localhost:8000 bash scripts/smoke_test.sh

set -euo pipefail

API="${API:-http://localhost:8000}"

echo "→ Smoke test contra $API"

echo "→ /healthz"
curl -fsS "$API/healthz" | jq -e '.status == "ok"' >/dev/null

echo "→ /auth/login"
TOKEN=$(curl -fsS -X POST "$API/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo"}' | jq -r '.token')
[ -n "$TOKEN" ] && [ "$TOKEN" != "null" ] || { echo "ERROR: no token"; exit 1; }

AUTH="Authorization: Bearer $TOKEN"

echo "→ /national/ytd"
curl -fsS -H "$AUTH" "$API/national/ytd" | jq -e '.nps.nps_actual != null' >/dev/null

echo "→ /branches"
BRANCH=$(curl -fsS -H "$AUTH" "$API/branches" | jq -r '.[0].branch_id')
[ -n "$BRANCH" ] && [ "$BRANCH" != "null" ] || { echo "ERROR: no branches"; exit 1; }

echo "→ /branches/$BRANCH/ytd"
curl -fsS -H "$AUTH" "$API/branches/$BRANCH/ytd" | jq -e '.branch_id != null' >/dev/null

echo "→ /national/critical-branches"
curl -fsS -H "$AUTH" "$API/national/critical-branches?limit=5" \
  | jq -e 'length >= 0' >/dev/null

echo "✓ Smoke test pasó"
