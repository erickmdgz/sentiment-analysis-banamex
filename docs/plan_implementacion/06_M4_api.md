---
tipo: m-doc
modulo: M4
estado: en-progreso
paquete: api
depende_de:
  - M3
  - M2b
tags:
  - plan-implementacion
  - modulo-m4
---

# M4 — API HTTP (FastAPI)

Este documento describe el módulo M4, que expone la API HTTP del MVP. Se apoya en `00_decisiones_tecnicas.md` (en adelante `00`) y `01_contratos_compartidos.md` (en adelante `01`) como fuentes de verdad.

---

## Responsabilidad

M4 expone los endpoints HTTP declarados en `01 §8`. Es un wrapper delgado sobre M3 (analytics) y sobre M2b (`engine.pipeline`) para uploads. Sus responsabilidades concretas:

- Recibir requests, validar inputs con Pydantic y autenticar con JWT mock (`00 §18`).
- Delegar toda lógica de cómputo a M3 (consultas analíticas) y a M2b/M1 (pipeline de upload).
- Aplicar la política de CORS de `00 §19`.
- Serializar respuestas conforme a los DTOs de `01 §4`.
- Producir errores en el formato único de `01 §9`.
- Exportar el `openapi.json` consumido por M5 (`01 §10`).

M4 **no** contiene lógica de NPS, agregaciones, clasificación, parsing ni acceso directo al schema SQLite. Todo eso vive en M1, M2b y M3. M4 organiza, valida, autentica y responde.

---

## Entregables

- App FastAPI completa en `api/src/api/main.py` con registro de routers y middleware (`01 §1`).
- Routers en `api/src/api/routes/`:
  - `auth.py` — `/auth/login`, `/auth/me`.
  - `upload.py` — `/upload`, `/upload/{file_id}/status`.
  - `validation.py` — `/validation`, `/validation/coverage`.
  - `national.py` — endpoints `/national/*` de `01 §8`.
  - `branches.py` — endpoints `/branches/*` de `01 §8`.
  - `admin.py` — `/admin/files`, `/admin/runs`.
- `api/src/api/auth.py`: encode/decode JWT con `python-jose` (HS256, `00 §18`).
- `api/src/api/deps.py`: dependencias `get_db` (yield de `Session` de SQLAlchemy) y `get_current_user` (decodifica token).
- `api/src/api/settings.py`: Pydantic Settings que lee `.env` (`JWT_SECRET`, `JWT_EXPIRATION_HOURS`, `DATABASE_URL`, `API_PORT`). No requiere variables del motor LLM porque la API no invoca al anotador (solo M2a lo hace, offline).
- `api/src/api/errors.py`: handlers globales que producen `{detail, code, hint}` (`01 §9`).
- `api/src/api/models_api.py`: re-exporta DTOs de `analytics.schemas` y declara DTOs propios del API (`LoginRequest`, `TokenResponse`, `UploadResponse`).
- `api/src/api/export_openapi.py`: script invocable como `python -m api.export_openapi` que escribe `api/openapi.json`.
- `api/Dockerfile` y `api/pyproject.toml`.
- README del paquete (en español) con instrucciones de instalación, arranque y export del OpenAPI.

---

## Contratos consumidos

- **M1** (`core`): sesión de DB vía `core.db` (engine SQLAlchemy y `Session`), modelos ORM de `core.models_db` (`01 §3`), funciones de carga (`core.loader.load_file`, `core.parser.parse_tsv`) para el endpoint `/upload`.
- **M2b** (`engine`): `engine.pipeline.classify_batch` para clasificar las filas nuevas en uploads (`00 §22`). Para metadatos, `engine.extractors.extract_all`. Para fallback determinístico mientras M2b no esté listo, `engine.mocks.classify_mock` (`01 §7`).
- **M3** (`analytics`): todas las funciones de agregación expuestas en los endpoints (`nps`, `trends`, `topics`, `ranking`, `actions`, `impact`, `insights`, `words`, `representatives`, `personnel`).

Mientras M2b o M3 no estén listos, M4 importa de `engine.mocks` y de stubs en `analytics/mocks.py` para permitir desarrollo en paralelo.

---

## Contratos producidos

- `api/openapi.json` exportado por `python -m api.export_openapi`. Es el contrato consumido por M5 para generar el cliente TS (`01 §10`).
- Respuestas HTTP JSON conformes a los DTOs de `01 §4` y la lista de endpoints de `01 §8`.
- Errores JSON conformes a `01 §9`.

---

## Estructura de archivos esperada

Sub-árbol del paquete `api/` tal como aparece en `01 §1`:

```
api/
├── pyproject.toml
├── src/api/
│   ├── __init__.py
│   ├── main.py
│   ├── settings.py
│   ├── deps.py
│   ├── auth.py
│   ├── errors.py
│   ├── models_api.py
│   ├── export_openapi.py
│   └── routes/
│       ├── __init__.py
│       ├── auth.py
│       ├── upload.py
│       ├── validation.py
│       ├── national.py
│       ├── branches.py
│       └── admin.py
├── tests/
└── Dockerfile
```

---

## Detalles de implementación clave

### Bootstrap de la app

```python
# api/src/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .settings import settings
from .errors import register_exception_handlers
from .routes import auth, upload, validation, national, branches, admin

app = FastAPI(title="Banamex CX MVP", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(validation.router)
app.include_router(national.router)
app.include_router(branches.router)
app.include_router(admin.router)

@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "db_path": settings.database_url,
        "classifier_loaded": classifier_is_loaded(),
    }
```

`CORSMiddleware` se configura con la lista cerrada de orígenes de `00 §19` (no se usa wildcard).

### Settings

```python
# api/src/api/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    jwt_secret: str = "demo-secret-change-in-prod"
    jwt_expiration_hours: int = 24
    database_url: str = "sqlite:///./data/processed/banamex.db"
    api_port: int = 8000

    class Config:
        env_file = ".env"

settings = Settings()
```

Las variables están definidas en `00 Anexo A`. `JWT_SECRET` con default visible solo aplica en demo; nunca debe commitearse un `.env` real.

### Auth JWT (decisión `00 §18`)

- `POST /auth/login`: acepta `{username, password}`. Ignora password (cualquier combinación es válida). Devuelve `{token, expires_at}`.
- Token: `jose.jwt.encode({"sub": username, "exp": now + JWT_EXPIRATION_HOURS}, JWT_SECRET, algorithm="HS256")`.
- Middleware: `get_current_user(token: str = Depends(oauth2_scheme))` decodifica el token y devuelve `{username}`.
- Endpoints excluidos del middleware: `/auth/login`, `/healthz`, `/docs`, `/openapi.json`, `/redoc`.
- Si el token está ausente, es inválido o está expirado: 401 con `code="token_invalid"` y `detail` en español.

### Errores (`01 §9`)

- Handler de `HTTPException`: envoltura sobre el default de FastAPI para producir el formato `{detail, code, hint}`.
- Handler de `ValueError` (e.g., mes inexistente lanzado desde M3): 422 con `detail` legible y `hint` que liste los meses válidos cuando aplique.
- Handler de `Exception` (catch-all): 500 con `detail="Error interno"`, `code="internal_error"`, log completo con `structlog` (`00 §25`).
- Handler de `RequestValidationError` de FastAPI: 422 con el formato unificado, sin filtrar la estructura interna de Pydantic.

### Upload endpoint

- `POST /upload`: recibe `UploadFile`, valida extensión `.txt` (400 con `code="invalid_extension"`) y tamaño `≤ 50 MB` (400 con `code="file_too_large"`).
- Calcula `sha256` del archivo en streaming (sin cargar todo en memoria).
- Si `sha256` ya existe en `files.sha256` (única por `01 §2`): retorna `{file_id, validation_summary, already_processed: True}` con HTTP 200.
- Si no existe: parsea con `core.parser.parse_tsv`, persiste con `core.loader.load_file`, dispara clasificación inline con `engine.pipeline.classify_batch` sobre las filas nuevas, persiste clasificaciones, computa `ValidationSummary` (`01 §4`) y devuelve `{file_id, validation_summary, already_processed: False}`.
- Procesamiento síncrono por defecto (≤ 30k filas tarda 1-2 minutos, `00 §22`).
- Si archivo > 30k filas: usar `BackgroundTasks` de FastAPI y exponer `GET /upload/{file_id}/status` con progreso. Status posibles: `parsing | classifying | done | error` (`01 §8`).

### Validation

- `GET /validation`: agrega sobre todos los `files` el `ValidationSummary` (sumas) y combina con métricas de validez derivadas de M1.
- `GET /validation/coverage`: devuelve `CoverageSummary` calculado en M3 (`01 §4`).

### National

- Cada endpoint de la sección "Nacional" de `01 §8` es un wrap directo a su función de M3 con scope nacional.
- `GET /national/ytd`: compone `NationalYTD` (`01 §4`) llamando a `nps.national_ytd_summary`, `trends.monthly_trend("national")`, `topics.top_causes`, `topics.top_strengths`, `ranking.critical_branches`, `ranking.rankings_bundle`, `actions.suggested_actions_national`, `impact.impact_by_category`, `insights.national_insights`.
- `GET /national/compare`: valida query params `month_a`, `month_b` con formato `YYYY-MM` (regex). Llama `trends.compare_months`. Si algún mes no existe en la base, M3 lanza `ValueError` con la lista de meses válidos, que el handler convierte a 422.

### Branches

- `GET /branches?q=...`: filtra `branches` con `LIKE %q%`.
- `GET /branches/{branch_id}/ytd`: si `branch_id` no existe en la tabla `branches` (`01 §2`) → 404 con `code="branch_not_found"`.
- Endpoints análogos a national pero con `scope=branch_id`. Reutilizan las mismas funciones de M3 con argumento de scope.

### Admin (POC)

- `GET /admin/files`: `SELECT * FROM files ORDER BY uploaded_at DESC`.
- `GET /admin/runs`: une `annotation_runs` y `classifier_runs` (`01 §2`).
- Solo lectura, sin escritura, sin operaciones administrativas reales.

### Export OpenAPI

Script `python -m api.export_openapi`:

```python
# api/src/api/export_openapi.py
import json
from api.main import app

def main() -> None:
    with open("api/openapi.json", "w", encoding="utf-8") as f:
        json.dump(app.openapi(), f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
```

Se ejecuta como parte del build del Dockerfile y manualmente cada vez que cambian endpoints. M5 consume `openapi.json` para regenerar el cliente TS (`01 §10`).

### Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY core/ core/
COPY engine/ engine/
COPY analytics/ analytics/
COPY api/ api/
RUN pip install -e ./core -e ./engine -e ./analytics -e ./api
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

El Dockerfile copia los cuatro paquetes Python e instala todos en modo editable, manteniendo la estructura de imports definida en `01 §1`.

---

## Tests requeridos

Mínimo 20 tests en `api/tests/`, ejecutables con `pytest api/tests`:

1. `POST /auth/login` con cualquier `username/password` → 200 + `token` válido.
2. `GET /auth/me` con token válido → 200 + `username`.
3. `GET /auth/me` con token inválido → 401 con `code="token_invalid"`.
4. `GET /auth/me` con token expirado → 401.
5. `GET /healthz` sin auth → 200.
6. `POST /upload` con archivo `.txt` válido → 200 + `file_id`.
7. `POST /upload` con archivo duplicado (mismo sha256) → 200 + `already_processed=True`.
8. `POST /upload` con extensión distinta a `.txt` → 400.
9. `POST /upload` con archivo > 50 MB → 400.
10. `GET /national/ytd` con base sembrada → estructura completa con todos los campos de `NationalYTD`.
11. `GET /national/compare?month_a=2026-01&month_b=2026-02` con datos existentes → 200.
12. `GET /national/compare?month_a=2030-01&month_b=2026-02` (mes inexistente) → 422 con lista de meses válidos en `hint`.
13. `GET /branches?q=A-1` → lista filtrada.
14. `GET /branches/A-9999` (inexistente) → 404 con `code="branch_not_found"`.
15. `GET /branches/{valid}/ytd` → estructura completa con todos los campos de `BranchYTD`.
16. `GET /admin/files` → 200 con lista.
17. CORS preflight `OPTIONS` responde correctamente para `http://localhost:5173`.
18. Endpoint protegido sin header `Authorization` → 401.
19. `python -m api.export_openapi` genera `openapi.json` parseable y con paths de `01 §8`.
20. Handler de `Exception` no controlado → 500 con `detail="Error interno"`.

Tests usan `TestClient` de FastAPI sobre una DB SQLite temporal sembrada con fixtures de M1.

---

## Definition of Done

- `pytest api/tests` pasa al 100% localmente.
- `docker build -t banamex-api ./api` exitoso.
- `uvicorn api.main:app --host 0.0.0.0 --port 8000` arranca y queda escuchando.
- `http://localhost:8000/docs` muestra Swagger con todos los endpoints de `01 §8`.
- `python -m api.export_openapi` produce `api/openapi.json` válido (parseable por `openapi-typescript`).
- Smoke test desde shell funciona: `login → upload → /national/ytd → /branches/{id}/ytd` con assertions de estructura JSON.
- README del paquete escrito en español, con secciones de instalación, comandos, env vars y export del OpenAPI.
- Sin secrets en archivos commiteables (`.env` ausente del paquete, plantilla en `.env.example` en la raíz, `00 Anexo A`).

---

## Riesgos específicos del módulo

- **Timeout en upload síncrono**: archivos cercanos al límite de 30k filas pueden rozar el timeout por default de uvicorn/cliente. Mitigación: pasar a `BackgroundTasks` con polling vía `/upload/{file_id}/status` cuando se detecte tamaño > 30k filas (`00 §22`).
- **`JWT_SECRET` commiteado por error**: `.env.example` con valor dummy, `.env` en `.gitignore` si hay git (`00 §26` aclara que el repo puede no estar inicializado). Validar antes del primer commit.
- **`python-jose` sin extras cripto**: instalar como `python-jose[cryptography]` en `pyproject.toml` para evitar fallos en runtime de HS256.
- **Upload de 50 MB consume RAM**: leer en streaming (`async for chunk in file`) y nunca hacer `await file.read()` completo; calcular `sha256` incrementalmente.
- **Sesión de DB compartida entre requests**: siempre usar `Depends(get_db)` con patrón `yield` y `session.close()` en `finally`. Nunca instanciar `Session` directamente en handlers.
- **Acoplamiento a M3 antes de tiempo**: si M3 no está listo, importar `analytics.mocks` y dejar TODOs marcados; documentar el reemplazo en el README del paquete.
- **OpenAPI desactualizado**: cada cambio de endpoint o DTO debe re-exportar `openapi.json`; idealmente ejecutar el script como parte del flujo de PR/commit. M5 falla en build si los tipos no coinciden.
- **CORS demasiado abierto**: mantener la lista cerrada de `00 §19`; resistir la tentación de usar `allow_origins=["*"]` aun en demo.
