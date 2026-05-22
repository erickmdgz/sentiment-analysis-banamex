---
tipo: m-doc
modulo: M6
estado: en-progreso
paquete: scripts
depende_de:
  - M1
  - M2a
  - M2b
  - M3
  - M4
  - M5
tags:
  - plan-implementacion
  - modulo-m6
---

# M6 — Integración y demo

> Este módulo es la **última sesión** del plan. Se ejecuta cuando M1, M2a, M2b, M3, M4 y M5 ya entregaron. Antes de empezar, leer `00_decisiones_tecnicas.md` (especialmente §20 Empaquetado de demo, §21 Pre-procesamiento, §22 Upload en runtime, §24 Tests E2E, Anexo A variables de entorno) y `01_contratos_compartidos.md` (§1 estructura, §8 endpoints, §13 tests).

## Responsabilidad

M6 integra los cinco paquetes de M1-M5 en una **experiencia desplegable con un solo comando**: `docker compose up`. Es una sesión de plomería, no de lógica de dominio: **no modifica código de los otros módulos salvo arreglos menores de integración** (rutas, variables de entorno, imports rotos por desincronización de contratos).

Su trabajo es:

1. Escribir el `docker-compose.yml` de raíz (decisión §20 de `00_decisiones_tecnicas.md`).
2. Escribir el script orquestador `scripts/preprocess_corpora.py` que ejecuta el pipeline completo offline (decisión §21).
3. Escribir `scripts/seed_db.py` como atajo para máquinas sin tiempo de correr el preprocess (~4 horas).
4. Escribir `scripts/smoke_test.sh` como único test E2E del sistema (decisión §24).
5. Escribir `scripts/generate_openapi_client.sh` para regenerar el cliente TS de M5 desde el `openapi.json` de M4 (§10 de `01_contratos_compartidos.md`).
6. Escribir `README_DEMO.md` en español para audiencia no técnica (jurado o gerente CX).
7. Escribir `.env.example` con la plantilla de variables de entorno (Anexo A de `00_decisiones_tecnicas.md`).
8. Documentar cómo se enlazan los paquetes y qué órdenes ejecutar.

La sesión termina cuando, desde un clone limpio, `docker compose up` levanta la demo y la vista nacional carga datos no vacíos en menos de 2 minutos.

## Entregables

- `docker-compose.yml` en la raíz del repo, con servicios `api` y `web`, volumen para `./data` y montaje read-only de `./api/openapi.json`.
- `scripts/preprocess_corpora.py`: pipeline orquestado offline (M1 carga → M2a anotación → M2b train → M2b predict → M2a metadata extractors).
- `scripts/seed_db.py`: descomprime un `banamex.db.gz` ya generado a `data/processed/banamex.db` (alternativa rápida si no hay tiempo de correr el preprocess).
- `scripts/smoke_test.sh`: bash con `curl` + `jq` que valida los endpoints clave de M4.
- `scripts/generate_openapi_client.sh`: regenera `web/src/api/schema.d.ts` desde `api/openapi.json`.
- `README_DEMO.md` en raíz: pasos en español para preparar y ejecutar la demo.
- `.env.example` en raíz: plantilla de variables de entorno.
- Documentación de integración en el README (cómo se enlazan los paquetes, qué órdenes ejecutar y en qué orden).

## Contratos consumidos

M6 consume **todos** los entregables de M1-M5. Específicamente (de `01_contratos_compartidos.md §1` y los archivos `02_…` a `07_…`):

- **`core`** (M1): instalable como paquete Python (`pip install -e ./core`). Expone `core.db.init_schema()`, `core.loader.load_file(path)`, `core.targets.generate_all(seed=42)`.
- **`engine`** (M2a + M2b): instalable como paquete Python. Modelo entrenado en `data/models/classifier.joblib`. CLI `engine.cli` con subcomandos `annotate-sample`, `train`, `predict-all`, `extract-metadata`.
- **`analytics`** (M3): instalable como paquete Python. Lo consume M4, no M6 directamente.
- **`api`** (M4): instalable como paquete Python + `Dockerfile` en `api/Dockerfile` + `api/openapi.json` ya exportado (entregable de M4 según su DoD).
- **`web`** (M5): `Dockerfile` en `web/Dockerfile` + build estático que se sirve por nginx.
- **Schema SQLite** (§2 de `01_contratos_compartidos.md`): autoritativo. M6 no lo toca.
- **Variables de entorno** (Anexo A de `00_decisiones_tecnicas.md`): `JWT_SECRET`, `JWT_EXPIRATION_HOURS`, `API_PORT`, `DATABASE_URL`, `OLLAMA_HOST`, `OLLAMA_MODEL`, `VITE_API_URL`.

## Contratos producidos

- **Stack ejecutable**: `docker compose up` levanta `api` (puerto 8000) y `web` (puerto 3000) con todas las dependencias resueltas.
- **`data/processed/banamex.db`**: SQLite con las ~474k verbalizaciones de los 3 corpora del reto cargadas, clasificadas y con metadata extraída. Producto del `preprocess_corpora.py` o de `seed_db.py`.
- **`data/models/classifier.joblib`**: clasificador entrenado por M2b sobre el golden set de 5k anotaciones. Producto del `preprocess_corpora.py`.
- **Demo documentada**: pasos en `README_DEMO.md` permiten ejecutar la demo en < 2 min desde clone limpio (asumiendo `banamex.db.gz` empaquetado).

## Estructura de archivos esperada

```
sentiment-analysis-banamex/
├── docker-compose.yml                      # M6
├── README_DEMO.md                          # M6
├── .env.example                            # M6
├── scripts/
│   ├── preprocess_corpora.py               # M6
│   ├── seed_db.py                          # M6
│   ├── smoke_test.sh                       # M6
│   └── generate_openapi_client.sh          # M6
├── data/
│   ├── raw/                                # ya existe (gitignored)
│   ├── processed/
│   │   ├── banamex.db                      # producido por preprocess o seed
│   │   └── banamex.db.gz                   # (opcional) pre-empacado para seed
│   └── models/
│       └── classifier.joblib               # producido por preprocess
├── api/                                    # M4 (intacto)
│   ├── Dockerfile
│   └── openapi.json
├── web/                                    # M5 (intacto)
│   └── Dockerfile
├── core/                                   # M1 (intacto)
├── engine/                                 # M2a+M2b (intacto)
└── analytics/                              # M3 (intacto)
```

## Detalles de implementación clave

### `docker-compose.yml`

Refleja la decisión §20 de `00_decisiones_tecnicas.md`: dos servicios, volumen para `./data`, dependencia ordenada con healthcheck.

```yaml
version: "3.9"

services:
  api:
    build: ./api
    container_name: banamex-api
    ports:
      - "8000:8000"
    environment:
      - JWT_SECRET=${JWT_SECRET:-demo-secret-change-in-prod}
      - JWT_EXPIRATION_HOURS=${JWT_EXPIRATION_HOURS:-24}
      - DATABASE_URL=sqlite:////app/data/processed/banamex.db
    volumes:
      - ./data:/app/data:delegated
      - ./api/openapi.json:/app/api/openapi.json:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
      interval: 10s
      timeout: 3s
      retries: 5
      start_period: 15s

  web:
    build: ./web
    container_name: banamex-web
    ports:
      - "3000:80"
    depends_on:
      api:
        condition: service_healthy
    environment:
      - VITE_API_URL=${VITE_API_URL:-http://localhost:8000}
```

Notas:

- `delegated` en el mount de `./data` mitiga la lentitud de volúmenes Docker en macOS (riesgo identificado abajo).
- El frontend depende del healthcheck del backend (`/healthz` definido en §8 de `01_contratos_compartidos.md`) para no arrancar con la API aún levantando.
- `JWT_SECRET` tiene default funcional para que `docker compose up` no falle si el usuario olvidó copiar el `.env` (consistente con la decisión §18 de "cualquier user/pass vale" en MVP).

### `scripts/preprocess_corpora.py`

Orquesta el pipeline completo offline. **Idempotente**: detecta qué fases ya están hechas y las saltea. Tiempo total estimado: ~5-7 horas (2-4 horas anotación con LLM local + 3 horas inferencia CPU para 469k verbalizaciones). El paso 4 requiere Ollama corriendo en el host (no en contenedor).

Argumentos CLI:

- `--skip-annotation` / `--force-annotate`
- `--skip-train` / `--force-train`
- `--skip-predict` / `--force-predict`
- `--skip-metadata` / `--force-metadata`
- `--force-all`: combina los cuatro `--force-*`.
- `--raw-dir` (default `data/raw`), `--db-path` (default `data/processed/banamex.db`), `--model-path` (default `data/models/classifier.joblib`).

Secuencia ejecutada:

1. **Init schema**: `core.db.init_schema()` si la DB no existe.
2. **Carga de corpora**: para cada archivo en `data/raw/*.txt`: `core.loader.load_file(path)`. Reporta `LoadReport` por archivo (totales, dedup, branches detectadas). Las decisiones §23 (`latin-1`) y §3 (schema único) ya están internalizadas por M1.
3. **Generación de objetivos sintéticos**: `core.targets.generate_all(seed=42)` si `branch_targets` está vacía (decisión §15 de `00_decisiones_tecnicas.md`).
4. **Anotación LLM local (M2a)**: si no hay `annotation_runs` con `status='done'`, ejecuta `engine.cli annotate-sample --size 5000 --seed 42`. Reporta `runtime_seconds` final (decisión §5, sin costo monetario). Pre-flight: verifica que Ollama esté corriendo en `OLLAMA_HOST` (default `http://localhost:11434`) y que el modelo `OLLAMA_MODEL` esté descargado. Si falla cualquiera de las dos verificaciones → mensaje accionable (`'ollama serve'`, `'ollama pull <model>'`) y salida con código 1, sugiriendo `--skip-annotation` para correr solo con golden set sintético si M2a lo provee.
5. **Entrenamiento (M2b)**: si no hay `classifier_runs` y no existe `data/models/classifier.joblib`, ejecuta `engine.cli train --annotation-run-id <last>`. Reporta métricas internas (f1_micro, f1_macro, hamming_loss del `classifier_runs`).
6. **Inferencia (M2b)**: si quedan verbalizations sin clasificación (`source IN ('classifier','fallback')` no cubre el `record_id`), ejecuta `engine.cli predict-all`. Reporta totales clasificados. Si se interrumpe a mitad, al re-ejecutar **solo procesa las verbalizations sin clasificación** (gracias a la idempotencia del comando).
7. **Extracción de metadata (M2a extractores)**: si quedan verbalizations sin entrada en `metadata_extractions`, ejecuta `engine.cli extract-metadata --all`. Reporta totales (decisión §12).
8. **Reporte final**: imprime tabla resumen (con `rich` si está disponible, sino texto plano) con:
   - Total verbalizations cargadas.
   - Total clasificadas (por `source`: `llm_annotation`, `classifier`, `fallback`).
   - Total con metadata extraída.
   - Cobertura % (`clasificadas / total`).
   - Sucursales detectadas.
   - Meses disponibles (rango y conteo).

Output a stdout con `structlog` JSON o tabla `rich` según un flag `--format json|table` (default `table`).

### `scripts/seed_db.py`

Atajo para máquinas que no van a correr el preprocess. Lógica:

```python
# pseudo-código
gz_path = Path("data/processed/banamex.db.gz")
db_path = Path("data/processed/banamex.db")
if not gz_path.exists():
    print("DB no pre-generada. Ejecuta `python scripts/preprocess_corpora.py` (~4h).")
    print("Alternativamente, descarga banamex.db.gz desde el entregable del equipo.")
    sys.exit(1)
if db_path.exists():
    print(f"DB ya existe en {db_path}. Bórrala manualmente si quieres re-extraer.")
    sys.exit(0)
with gzip.open(gz_path, "rb") as src, open(db_path, "wb") as dst:
    shutil.copyfileobj(src, dst)
print(f"DB extraída en {db_path} ({db_path.stat().st_size / 1e6:.1f} MB).")
```

El `banamex.db.gz` se genera manualmente por el equipo después del primer `preprocess_corpora.py` exitoso, y se versiona como artefacto del entregable (no en git por tamaño; se distribuye fuera de banda según la decisión §26 de no reactivar git).

### `scripts/smoke_test.sh`

Único test E2E del sistema (decisión §24). Valida los endpoints clave de §8 de `01_contratos_compartidos.md` con `curl` + `jq`.

```bash
#!/usr/bin/env bash
set -euo pipefail

API="${API:-http://localhost:8000}"

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
curl -fsS -H "$AUTH" "$API/national/critical-branches?limit=5" | jq -e 'length >= 0' >/dev/null

echo "✓ Smoke test pasó"
```

Permisos: `chmod +x scripts/smoke_test.sh`. El script falla con código distinto de cero ante cualquier assertion que no se cumpla, permitiendo encadenarlo en pipelines locales.

### `scripts/generate_openapi_client.sh`

Regenera el cliente TS de M5 desde `api/openapi.json`. Cita §10 de `01_contratos_compartidos.md`.

```bash
#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."  # raíz del repo

if [ ! -f api/openapi.json ]; then
  echo "ERROR: api/openapi.json no existe. Ejecuta el export en api/ primero."
  exit 1
fi

cd web
npx openapi-typescript ../api/openapi.json --output src/api/schema.d.ts
echo "✓ Cliente TS regenerado en web/src/api/schema.d.ts"
```

Este script se corre **antes del `docker compose build`** si los contratos cambiaron, o como pre-build de M5. Riesgo identificado abajo: desincronización entre `openapi.json` y `web/`.

### `README_DEMO.md`

Audiencia: jurado del hackathon o gerente CX, no necesariamente técnico. Idioma: español (regla global del usuario). Estructura propuesta:

1. **¿Qué es esto?** Un párrafo: MVP de análisis de sentimientos sobre verbalizaciones de encuestas NPS de Banamex, con dashboard ejecutivo nacional y por sucursal.
2. **Requisitos**:
   - Docker Desktop (macOS, Linux o Windows con WSL2).
   - ~10 GB libres en disco.
   - Opcional: Ollama instalado y modelo `qwen2.5:7b-instruct` descargado (solo si se quiere regenerar las anotaciones LLM desde cero).
3. **Quick start con DB pre-generada (~2 min)**:
   ```bash
   git clone <repo> && cd sentiment-analysis-banamex
   cp .env.example .env
   python scripts/seed_db.py
   docker compose up
   # abrir http://localhost:3000
   ```
4. **Quick start desde cero (~5-7 horas, requiere Ollama)**:
   ```bash
   brew install ollama
   ollama serve &              # daemon en background
   ollama pull qwen2.5:7b-instruct
   cp .env.example .env
   pip install -e ./core ./engine ./analytics ./api
   python scripts/preprocess_corpora.py
   docker compose up
   ```
5. **Flujo de demo sugerido** (5-7 minutos frente al jurado):
   1. Login con cualquier usuario/password (decisión §18).
   2. Vista upload: el sistema ya tiene los 3 corpora cargados; se muestra carrusel ilustrativo de la carga.
   3. Vista nacional YTD: explicar NPS actual, brecha vs objetivo, top causas, top fortalezas, sucursales críticas.
   4. Click en sucursal crítica → vista de sucursal: comentarios representativos, personal mencionado, palabras top.
   5. Volver a vista nacional → vista de comparación de meses (M3 endpoint `/national/compare`).
   6. Mostrar sección admin (POC `/admin/files`, `/admin/runs`) para indicar capacidad de extensión.
6. **Troubleshooting**:
   - **Puerto 8000 ocupado**: editar `docker-compose.yml` y cambiar `8000:8000` por `<otro>:8000`, actualizar `VITE_API_URL` en `.env`.
   - **DB no encontrada**: correr `python scripts/seed_db.py` o `python scripts/preprocess_corpora.py`.
   - **Frontend no carga datos**: verificar `curl http://localhost:8000/healthz` y revisar logs con `docker compose logs api`.
   - **Ollama no corre o modelo faltante**: solo necesario para regenerar anotaciones. Verificar con `curl http://localhost:11434/api/tags`. Si se usa el seed pre-generado no aplica.
7. **Aviso de datos**: los corpora son **reales de Banamex** entregados en el marco del reto Tec de Monterrey. No compartir externamente (consistente con `CLAUDE.md` del proyecto).

### `.env.example`

Plantilla idéntica al Anexo A de `00_decisiones_tecnicas.md`, sin secrets reales:

```env
# API
JWT_SECRET=cambia-esto-en-produccion-pero-en-mvp-da-igual
JWT_EXPIRATION_HOURS=24
API_PORT=8000
DATABASE_URL=sqlite:///./data/processed/banamex.db

# Motor LLM local (solo M2a, fase de anotación, requiere Ollama corriendo)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b-instruct

# Frontend
VITE_API_URL=http://localhost:8000
```

`.env.example` se commitea; `.env` real va en `.gitignore` (regla global de secretos del usuario y decisión §26 sobre git).

### Dependencias de instalación

- **Workspace Python**: para MVP basta con `pip install -e ./core ./engine ./analytics ./api` desde la raíz. Un `pyproject.toml` workspace root con `tool.uv` o `tool.poetry.workspaces` es opcional y queda fuera del scope salvo que aparezca un problema concreto.
- **Frontend**: `cd web && npm install && npm run build` se ejecuta dentro del `Dockerfile` de M5; M6 no lo invoca directamente salvo para `generate_openapi_client.sh`.

## Tests requeridos

Por la decisión §24 de `00_decisiones_tecnicas.md`, M6 **no implementa tests con browser**. Los tests exigidos para cerrar el módulo son:

1. **Smoke test contra stack levantado**: `bash scripts/smoke_test.sh` pasa contra `docker compose up` corriendo localmente. Cubre el flujo login → vista nacional → vista de sucursal → endpoint de sucursales críticas.
2. **Preprocess idempotente — modo dry-load**: `python scripts/preprocess_corpora.py --skip-annotation --skip-train --skip-predict --skip-metadata` carga los corpora y genera objetivos sintéticos sin tocar el motor, sale con código 0 y reporte coherente.
3. **Seed extrae correctamente**: con un `data/processed/banamex.db.gz` válido presente, `python scripts/seed_db.py` produce `data/processed/banamex.db` con tamaño > 0 y `core.db` puede abrirlo (sanity check opcional con `sqlite3 banamex.db 'SELECT COUNT(*) FROM verbalizations;'`).
4. **Docker build desde clone limpio**: `docker compose build` exitoso sin errores. Verificar que ninguna capa rompe por archivo ausente.
5. **README_DEMO.md verificado**: alguien sin contexto del proyecto sigue los pasos del Quick start con DB pre-generada y llega a la vista nacional con datos en < 2 min. (Verificación manual; no automatizable en este scope.)

## Definition of Done

- Desde clone limpio + `cp .env.example .env` + `python scripts/seed_db.py` + `docker compose up`: en **≤ 2 minutos** el navegador carga `http://localhost:3000`, se hace login con cualquier credencial y la vista nacional muestra datos no vacíos (NPS actual, distribución, al menos 1 causa, al menos 1 sucursal crítica).
- `bash scripts/smoke_test.sh` pasa contra el stack corriendo.
- `python scripts/preprocess_corpora.py` ejecuta sin errores fatales sobre los 3 corpora reales (tiempo total documentado en el reporte de salida).
- `python scripts/preprocess_corpora.py --skip-*` (todas las fases salteadas tras una corrida exitosa) sale en segundos sin re-ejecutar nada (verificación de idempotencia).
- `bash scripts/generate_openapi_client.sh` regenera `web/src/api/schema.d.ts` sin errores, y `cd web && npm run build` sigue funcionando.
- `README_DEMO.md` está en español, escrito para audiencia no técnica, con los dos quick starts (con seed y desde cero) y el flujo de demo de 5-7 min.
- `.env.example` no contiene secrets reales (`JWT_SECRET` con string genérico documentado como "cambiar en producción"). Las variables `OLLAMA_HOST` y `OLLAMA_MODEL` son configuración pública, no secretos.
- `docker compose build` exitoso desde clone limpio.
- No se modificó código de M1-M5 más allá de ajustes mínimos de rutas/imports; cualquier cambio mayor se documenta en `contracts_issues.md` (regla de `00_decisiones_tecnicas.md` y `01_contratos_compartidos.md §12`).

## Riesgos específicos del módulo

- **Rutas `joblib` hardcoded en M2b**: si el paquete `engine` resuelve la ruta del modelo con una ruta relativa al cwd, dentro del contenedor falla. Mitigación: M2b debe resolver con `pathlib.Path(__file__).parent` o leer `MODEL_PATH` de env. Si llega a M6 hardcoded, anotar en `contracts_issues.md` y aplicar un patch mínimo (única excepción a la regla de no tocar otros módulos).
- **Volúmenes Docker en macOS lentos**: el mount `./data:/app/data` puede ser muy lento sin `delegated`. Ya documentado en el `docker-compose.yml`. Si persiste, alternativa: copiar el `.db` adentro de la imagen en build (rompe la idea de DB intercambiable; documentar trade-off).
- **Descarga de `sentence-transformers` durante build (~120 MB)**: el `Dockerfile` de M4 incluye `engine` y por transición descarga el modelo de embeddings. Mitigaciones por preferencia: (a) capa cacheada en el Dockerfile que pre-descarga el modelo con un `python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"` antes de copiar el resto del código; (b) montar `~/.cache/torch` como volumen para reusar entre builds. Documentado en troubleshooting del README.
- **`openapi.json` desincronizado entre `api` y `web`**: si M4 cambia un endpoint y M5 no regenera el cliente, fallan llamadas TS en runtime sin error de build. Mitigación: documentar que `scripts/generate_openapi_client.sh` se corre como pre-build de M5, y dejar el `openapi.json` montado read-only en el contenedor `api` para detectar drift.
- **Ollama no corriendo o modelo no descargado al regenerar anotaciones**: si alguien corre `preprocess_corpora.py` sin Ollama y sin `--skip-annotation`, el script debe detectar y mostrar mensaje accionable con los comandos `ollama serve` y `ollama pull <model>`. No debe quedar en estado inconsistente.
- **`preprocess_corpora.py` interrumpido a mitad de inferencia (paso 6)**: el comando `engine.cli predict-all` de M2b debe procesar **solo verbalizaciones sin clasificación** (consultando `classifications.record_id` para excluir). Si M2b no lo hace así, el script no es reanudable y una caída a las 2.5 horas obliga a empezar de cero. Verificar en handoff con M2b; si falta, anotar en `contracts_issues.md`.
- **Discrepancia entre puerto del frontend (`80` en contenedor vs `3000` en host) y `VITE_API_URL`**: si el usuario expone el frontend en otro puerto, la llamada al backend rompe porque `VITE_API_URL` apunta a `localhost:8000`. Mitigación: documentar en troubleshooting que si se cambia el puerto del backend hay que actualizar también `VITE_API_URL` antes de rebuildear el frontend (Vite inyecta el valor en build, no runtime).
- **Tamaño del `banamex.db` (~500 MB-1 GB estimado para 474k filas con clasificaciones y metadata)**: si el repo intenta versionarlo cae fuera de límites prácticos. Por eso `seed_db.py` espera un `.gz` distribuido fuera de banda y `data/processed/` está en `.gitignore`. Consistente con decisión §26 (sin git reinicializado).
- **Docker Compose v1 vs v2**: el `docker-compose.yml` usa `version: "3.9"` y sintaxis compatible con ambas, pero `docker compose` (v2, con espacio) es el comando moderno; macOS reciente lo trae por default. Documentar en README que se asume v2.
