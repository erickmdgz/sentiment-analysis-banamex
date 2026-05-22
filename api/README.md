# api — FastAPI HTTP wrapper

Paquete del módulo **M4**. Expone la API HTTP que consume el frontend (M5) y que se monta en Docker en la demo final (M6). Es un wrapper delgado sobre `analytics` (M3), `engine` (M2a/M2b) y `core` (M1).

## Stack

- Python ≥ 3.12
- FastAPI ≥ 0.110, Pydantic ≥ 2.6, Pydantic Settings, SQLAlchemy ≥ 2.0
- `python-jose[cryptography]` (JWT HS256), `python-multipart` (uploads), `structlog` (JSON logs)

## Instalación local

Desde la raíz del repo:

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ./core -e ./engine -e ./analytics -e ./api
pip install pytest httpx
```

## Cómo correr

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Documentación interactiva en `http://localhost:8000/docs`. El health-check en `http://localhost:8000/healthz` confirma el path de la DB y si el clasificador supervisado (M2b) está disponible.

## Variables de entorno

Definidas en `.env` (raíz del repo) y leídas por `api.settings.Settings`:

| Variable | Default | Descripción |
|---|---|---|
| `JWT_SECRET` | `demo-secret-change-in-prod` | Secreto HS256 para firmar tokens |
| `JWT_EXPIRATION_HOURS` | `24` | Validez del token |
| `DATABASE_URL` | `sqlite:///./data/processed/banamex.db` | Ruta SQLite |
| `API_PORT` | `8000` | Puerto donde corre uvicorn |

`CORE_DB_PATH` (sólo tests) sobrescribe la DB efectiva del paquete `core`.

## Endpoints

Listados exhaustivamente en `docs/plan_implementacion/01_contratos_compartidos.md §8`. Resumen por router:

- `auth`: `POST /auth/login`, `GET /auth/me`
- `upload`: `POST /upload`, `GET /upload/{id}/status`
- `validation`: `GET /validation`, `GET /validation/coverage`
- `national`: 11 endpoints `/national/*`
- `branches`: 11 endpoints `/branches/*`
- `admin`: `GET /admin/files`, `GET /admin/runs`
- `health`: `GET /healthz`

## Tests

```bash
cd api && pytest
```

Los tests usan `TestClient` de FastAPI sobre una SQLite temporal poblada con un fixture compartido (`tests/conftest.py`).

## Regenerar `openapi.json`

```bash
python -m api.export_openapi
```

El JSON queda en `api/openapi.json` y lo consume M5 con `openapi-typescript` (`01 §10`).

## Docker

Build desde la raíz del repo:

```bash
docker build -t banamex-api -f api/Dockerfile .
```

El Dockerfile copia los 4 paquetes (`core`, `engine`, `analytics`, `api`) y los instala en modo editable. La DB SQLite se monta como volumen en `/app/data`.

## Estado de M2b (mock temporal)

Mientras M2b no esté mergeado, el endpoint `/upload` usa `api._classifier_shim.classify_batch` (mock determinístico por hash) para poblar `classifications`. Para los metadatos transversales (`metadata_extractions`) usa la implementación real de `engine.extractors.extract_all`. Cuando M2b se mergee, sustituir el import de `_classifier_shim` por `engine.pipeline.classify_batch` (misma firma). Detalle en `docs/plan_implementacion/contracts_issues.md` (entrada 2026-05-21 — M4).

## Errores

Formato unificado `{detail, code, hint}` (`01 §9`). Códigos HTTP: 200, 400, 401, 404, 422, 500. Handlers globales en `api/src/api/errors.py`.

## Autenticación

JWT HS256 mock (`00 §18`): cualquier `{username, password}` produce un token válido por `JWT_EXPIRATION_HOURS`. El middleware exige `Authorization: Bearer <token>` en todos los endpoints excepto `/auth/login`, `/healthz`, `/docs`, `/openapi.json`, `/redoc`.
