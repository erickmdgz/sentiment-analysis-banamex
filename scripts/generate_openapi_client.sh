#!/usr/bin/env bash
# Regenera el cliente TypeScript del frontend desde `api/openapi.json`.
# Cita §10 de `01_contratos_compartidos.md`.
#
# Uso:
#   bash scripts/generate_openapi_client.sh
#
# Cuándo correrlo:
#   - Cada vez que cambien endpoints o DTOs en la API (M4) y haga falta sincronizar
#     el cliente TS de M5.
#   - Antes de `docker compose build web` si los contratos cambiaron.

set -euo pipefail

cd "$(dirname "$0")/.."  # raíz del repo

if [ ! -f api/openapi.json ]; then
  echo "ERROR: api/openapi.json no existe."
  echo "       Exporta el OpenAPI desde la API primero:"
  echo "         (cd api && python -m api.export_openapi)"
  exit 1
fi

cd web

if [ ! -d node_modules ]; then
  echo "→ Instalando dependencias del frontend (npm ci)…"
  npm ci --no-audit --no-fund
fi

echo "→ Regenerando web/src/api/schema.d.ts…"
npx --yes openapi-typescript ../api/openapi.json --output src/api/schema.d.ts

echo "✓ Cliente TS regenerado en web/src/api/schema.d.ts"
