#!/usr/bin/env bash
# Levanta el stack completo (api + web) en Docker.
#
# Hace en orden:
#   1. Verifica que existe la BD (data/processed/banamex.db). Si no, instruye
#      cómo crearla (scripts/preprocess_corpora.py o scripts/seed_db.py).
#   2. Si Docker daemon no está corriendo, lanza Docker Desktop y espera.
#   3. docker compose up -d   (añade --build si pasas la flag --build).
#   4. Espera hasta que /healthz responda y reporte classifier_loaded.
#   5. Imprime URL y credenciales demo.
#
# Uso:
#   bash scripts/start.sh           # arranque normal (reusa imágenes)
#   bash scripts/start.sh --build   # fuerza rebuild antes de levantar
#   bash scripts/start.sh --stop    # baja el stack (docker compose down)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

DB_PATH="data/processed/banamex.db"
API_URL="${API_URL:-http://localhost:8000}"
WEB_URL="${WEB_URL:-http://localhost:3000}"

# --- flags ---
BUILD_FLAG=""
case "${1:-}" in
  --build) BUILD_FLAG="--build" ;;
  --stop)
    echo "→ Bajando stack…"
    docker compose down
    echo "✓ Stack detenido."
    exit 0
    ;;
  "" ) ;;
  * ) echo "ERROR: flag desconocida '$1'. Usa --build o --stop." >&2; exit 1 ;;
esac

# --- 1. BD existe ---
if [ ! -f "$DB_PATH" ]; then
  echo "ERROR: no existe $DB_PATH" >&2
  echo "" >&2
  echo "Opciones para generarla:" >&2
  echo "  - Pipeline desde corpora crudos (Ollama necesario, varias horas):" >&2
  echo "      python scripts/preprocess_corpora.py" >&2
  echo "  - Distribuible pre-generado (rápido):" >&2
  echo "      coloca data/processed/banamex.db.gz y corre" >&2
  echo "      python scripts/seed_db.py" >&2
  exit 1
fi

# --- 2. Docker daemon ---
if ! docker info >/dev/null 2>&1; then
  echo "→ Docker daemon no responde. Lanzando Docker Desktop…"
  if [[ "$(uname)" == "Darwin" ]]; then
    open -a Docker
  else
    echo "ERROR: arranca el Docker daemon manualmente en este sistema y reintenta." >&2
    exit 1
  fi
  echo -n "→ Esperando daemon"
  until docker info >/dev/null 2>&1; do
    echo -n "."
    sleep 2
  done
  echo " listo."
fi

# --- 3. docker compose up ---
echo "→ docker compose up -d $BUILD_FLAG"
# shellcheck disable=SC2086
docker compose up -d $BUILD_FLAG

# --- 4. esperar health del API ---
echo -n "→ Esperando API"
for _ in $(seq 1 60); do
  if curl -fsS --max-time 2 "$API_URL/healthz" >/dev/null 2>&1; then
    echo " listo."
    break
  fi
  echo -n "."
  sleep 1
done

HEALTH_JSON="$(curl -fsS --max-time 5 "$API_URL/healthz" 2>/dev/null || echo '{}')"
if ! echo "$HEALTH_JSON" | grep -q '"status"'; then
  echo "ERROR: el API no responde tras 60s. Revisa 'docker compose logs api'." >&2
  exit 1
fi

CLASSIFIER_OK=$(echo "$HEALTH_JSON" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('classifier_loaded'))" 2>/dev/null || echo "?")
if [ "$CLASSIFIER_OK" != "True" ]; then
  echo "⚠ Atención: classifier_loaded=$CLASSIFIER_OK (esperado True)."
  echo "  El dashboard funciona pero las clasificaciones recién subidas no tendrán modelo."
  echo "  Para entrenar uno: python -m engine.cli train --annotation-run-id <N>"
fi

# --- 5. Resumen ---
echo ""
echo "═══ Stack listo ═══"
echo "  Web:        $WEB_URL"
echo "  API:        $API_URL"
echo "  Docs API:   $API_URL/docs"
echo "  Login demo: demo / demo"
echo ""
echo "Comandos útiles:"
echo "  Smoke test:  bash scripts/smoke_test.sh"
echo "  Logs API:    docker compose logs -f api"
echo "  Bajar:       bash scripts/start.sh --stop"
