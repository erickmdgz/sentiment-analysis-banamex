# sentiment-analysis-banamex

> **Antes de actuar en una sesión nueva, lee `docs/ESTADO.md`** para conocer la etapa actual del proyecto, decisiones recientes que sobrescriben contratos, pendientes y convenciones operacionales aprendidas. CLAUDE.md describe **qué es** el proyecto (estable); `docs/ESTADO.md` describe **dónde va** (volátil, se actualiza después de cada milestone).

## Descripción

Reto de hackathon del Tec de Monterrey con caso real de **Banamex**: análisis de sentimientos sobre experiencia de cliente (CX) en sucursales, basado en corpora de texto entregados por el cliente del caso (~474k verbalizaciones de encuestas NPS).

El MVP procesa las verbalizaciones, las clasifica en una taxonomía de 15 L1 / 45 L2 / 82 L3 (autoritativa del cliente, en `docs/taxonomia_revisada.md`), extrae metadatos transversales (personal mencionado, recomendación explícita, otros bancos, canales), y los presenta en un dashboard ejecutivo (nacional + sucursal + comparación de meses).

No es un contrato facturable directo con Banamex — es un reto académico/competitivo con datos reales. Si llegara a derivar en un contrato, migrar a `clients/banamex/sentiment-analysis/`.

## Stack y versiones

- **Lenguaje backend**: Python 3.12 (usar `/opt/homebrew/bin/python3.12`, no el del sistema).
- **Frontend**: React 18 + Vite + TypeScript, sirve con nginx en producción.
- **API HTTP**: FastAPI + uvicorn + structlog. JWT via `python-jose`.
- **Base de datos**: SQLite (WAL activo por defecto en `core.db`). Vive en `data/processed/banamex.db`.
- **ML**:
  - Anotador LLM: Ollama local con `qwen2.5:7b-instruct` (opcional — solo para regenerar el golden set desde cero).
  - Clasificador supervisado: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` + scikit-learn `OneVsRestClassifier` multi-label, bundle serializado con joblib.
- **Orquestación**: Docker Compose (servicios `api` + `web`). Build context = raíz del repo.

## Estructura del repo

```
sentiment-analysis-banamex/
├── CLAUDE.md
├── README_DEMO.md            # Quick-start para jurado / no técnicos
├── docker-compose.yml        # api + web (build desde raíz)
├── .env.example
├── core/                     # DTOs, schema SQLite, loader, parser TSV
├── engine/                   # Anotador LLM, extractores, embeddings, clasificador, pipeline público
├── analytics/                # Agregaciones por bucket (causas, fortalezas, impacto, representativos)
├── api/                      # FastAPI: 31 endpoints (auth + upload + national + branches + admin + healthz)
├── web/                      # SPA React (7 pantallas)
├── scripts/
│   ├── preprocess_corpora.py # Orquestador idempotente: load → annotate → train → predict
│   ├── seed_db.py            # Descomprime banamex.db.gz a data/processed/
│   ├── smoke_test.sh         # Probes E2E contra el stack vivo
│   └── generate_openapi_client.sh   # Regenera web/src/api/schema.d.ts (fuera del build por ahora)
├── data/                     # Gitignored. raw/ = corpora Banamex; processed/ = SQLite; models/ = .joblib
└── docs/
    ├── ESTADO.md             # Fuente de verdad VIVA — leer primero
    ├── DASHBOARD.md          # Vista Dataview del plan (alimentada por frontmatter de M-docs)
    ├── plan_implementacion/  # Contratos congelados (00, 01) + M-docs (02-08) + contracts_issues
    ├── taxonomia_revisada.md # Taxonomía autoritativa del cliente
    └── originales/           # ZIP entregable (gitignored, respaldo inmutable)
```

## Comandos

```bash
# Setup venv global (para tests cross-package desde main).
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e core/ -e engine/ -e analytics/ -e api/
pip install pytest jsonschema

# Tests por paquete.
python -m pytest core/tests
python -m pytest engine/tests
python -m pytest analytics/tests
python -m pytest api/tests

# Levantar stack completo (requiere Docker daemon).
docker compose up -d
bash scripts/smoke_test.sh        # Smoke E2E
# Web en http://localhost:3000  ·  API en http://localhost:8000  ·  /docs en http://localhost:8000/docs

# Pipeline completo desde corpora crudos (lento; requiere Ollama si no se usa --skip-llm).
python scripts/preprocess_corpora.py            # Todo
python scripts/preprocess_corpora.py --skip-llm --skip-classifier   # Sólo load + extract_metadata
python scripts/preprocess_corpora.py --force-all                    # Re-correr todas las fases

# Pipeline manual del clasificador supervisado.
python -m engine.cli annotate-sample --size 5000 --persist-db   # Golden set vía Ollama
python -m engine.cli train --annotation-run-id <N>              # Entrena → data/models/classifier.joblib
python -m engine.cli predict-all                                # Clasifica todas las verbalizaciones

# Frontend dev (sin docker).
cd web && npm install && npm run dev
npm run typecheck && npm run test && npm run lint
```

## Notas para Claude

### Datos sensibles
- Los datos son **reales de Banamex** entregados en el marco del reto. Tratarlos como sensibles: nunca commitear los `.txt` de `data/raw/`, ni el `.db` resultante, ni pegarlos en herramientas externas.
- El `.zip` original en `docs/originales/` es el entregable inmutable — no modificar, solo conservar. Está gitignored.
- Fixtures de tests son **sintéticas y determinísticas**, nunca extractos de corpora reales.

### Convenciones permanentes
- **Idioma**: docs en español, código/identificadores en inglés (regla global del usuario). Mensajes de commit pueden mezclar.
- **Commits convencionales**: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`. Subscope opcional: `feat(api): ...`.
- **Worktrees viven fuera del repo padre**: `~/Documents/personal/sentiment-wt-<modulo>`. Git rechaza worktrees adentro.
- **Aislamiento entre sesiones paralelas**: cada sesión lee solo `README + 00 + 01 + su M-doc`. No tocar archivos fuera del paquete asignado. No modificar contratos congelados (`00`, `01`): anotar en `docs/plan_implementacion/contracts_issues.md`.

### Sincronización del DASHBOARD de Obsidian
- `docs/DASHBOARD.md` se renderiza con Dataview leyendo el **frontmatter YAML** de cada M-doc en `docs/plan_implementacion/`. Al mergear un PR de un módulo, actualizar también `estado:` (`pendiente` → `en-progreso` → `completado`) y añadir `pr: <N>`. Sin esto el dashboard miente.

### Mantener ESTADO.md al día
- Después de cada milestone (cerrar PR, cerrar etapa, decidir sobre un contrato, descubrir una convención operacional) actualizar `docs/ESTADO.md` con commit `docs(estado): ...`. Es responsabilidad de Claude — no esperar a que el usuario lo pida.

### Comandos destructivos
- Force-push, push a `main`, `rm -rf`, `git reset --hard`, `gh pr merge --delete-branch` sobre rama de otra sesión: **pedir confirmación al usuario** antes de ejecutar (regla global CLAUDE.md).
