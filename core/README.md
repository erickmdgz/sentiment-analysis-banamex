# core — Núcleo de datos

Parser TSV, persistencia SQLite, deduplicación y generación de objetivos NPS
sintéticos para el reto Banamex. Es la base sobre la que corren M2 (motor),
M3 (analytics) y M4 (API): nadie más toca los corpora directamente.

Schema, DTOs y ORM siguen al pie de la letra `docs/plan_implementacion/01_contratos_compartidos.md` (§2–§4).

## Instalación

Desde la raíz del repo:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -e ./core
```

Para correr los tests:

```bash
.venv/bin/pip install pytest
.venv/bin/pytest core/tests
```

## Comandos disponibles

`core` no expone CLI propia (los entregables CLI son de M2a/M2b/M6). Su API
pública vive en Python:

| Símbolo | Qué hace |
|---|---|
| `core.db.init_schema()` | Aplica `schema.sql` sobre `data/processed/banamex.db`. Idempotente. |
| `core.db.get_engine()` / `get_session()` | Engine y session factory SQLAlchemy 2.x. |
| `core.parser.parse_tsv(path)` | Iter de `ParsedRow` (válidas e inválidas) sobre un TSV. |
| `core.loader.file_sha256(path)` | Hash SHA-256 del archivo (chunks de 64 KB). |
| `core.loader.load_file(path)` | Parsea, deduplica y persiste. Devuelve `LoadReport`. |
| `core.targets.generate_all(seed=42, force=False)` | Llena `branch_targets` para todas las sucursales. Idempotente. |
| `core.targets.regenerate_for_branches([...])` | Borra y regenera targets puntuales. |
| `core.targets.compute_branch_nps(branch_id)` / `compute_national_nps()` | NPS por sucursal y nacional, basado en `verbalizations`. |

## Ejemplos

### Inicializar la DB y cargar un corpus

```python
from pathlib import Path
from core.db import init_schema
from core.loader import load_file

init_schema()  # crea data/processed/banamex.db con todas las tablas
report = load_file(Path("data/raw/1_mitad_2026.txt"))
print(report)
# LoadReport(file_id=1, filename='1_mitad_2026.txt', rows_total=..., rows_inserted=..., ...)
```

### Generar objetivos NPS sintéticos

```python
from core.targets import generate_all

targets = generate_all(seed=42)
print(f"{len(targets)} sucursales tienen objetivo anual")
print(targets[0])
# BranchTargetRow(branch_id='A-100', nps_target_annual=67, is_synthetic=True)
```

### Configurar otra ubicación para la DB (útil en tests)

```bash
export CORE_DB_PATH=/tmp/banamex_test.db
```

## Notas de implementación

- **Encoding**: los `.txt` se leen como `latin-1` y se normalizan a UTF-8 en
  memoria (decisión `00_decisiones_tecnicas.md §23`). Persistencia SQLite es UTF-8.
- **Line terminators**: el parser tolera LF, CRLF y NEL (U+0085). NEL se
  normaliza a `\n` antes de feed al módulo `csv`, porque `csv` no lo trata
  como terminator por defecto.
- **Formato de fecha**: se autodetecta DD/MM/YYYY vs MM/DD/YYYY sobre una
  muestra de 100 filas. Si la primera posición tiene algún día > 12 → DD/MM;
  si la segunda lo tiene → MM/DD; ambiguo → DD/MM (convención latina). Las
  fechas que no parsean con el formato detectado se reintentan con el
  contrario antes de marcar la fila como inválida.
- **Dedup**: a nivel archivo por `sha256` (tabla `files`), a nivel registro por
  `record_id` (PK en `verbalizations`). `load_file` también deduplica
  ocurrencias repetidas del mismo `record_id` dentro del mismo archivo.
- **Filas inválidas**: el parser yield-ea `ParsedRow` con `is_valid=False` y un
  motivo (menos de 6 columnas, `nps_rate` fuera de rango, `nps_group` con
  typo, fecha no parseable, `record_id`/`branch_id` vacíos). El loader las
  cuenta en `LoadReport.rows_invalid`. Esta divergencia con la firma teórica
  `parse_tsv -> Iterator[VerbalizationRow]` está anotada en
  `docs/plan_implementacion/contracts_issues.md`.
- **Targets**: el seed efectivo de la fórmula §15 sale de `branch_id` (no del
  parámetro `seed` global), así que los valores son deterministas entre
  corridas sin depender de `PYTHONHASHSEED`. El parámetro `seed=42` se
  conserva en la firma por compatibilidad.
- **Concurrencia**: `core` NO soporta escritura concurrente desde múltiples
  procesos. Sólo M1 escribe en `verbalizations`. SQLite usa `PRAGMA
  journal_mode=WAL` para que las lecturas no bloqueen escrituras.

## Estructura interna

```
core/
├── pyproject.toml
├── README.md
├── src/core/
│   ├── __init__.py
│   ├── db.py            # engine, session factory, init_schema
│   ├── schema.sql       # CREATE TABLE literales (fuente de verdad §2)
│   ├── models_db.py     # SQLAlchemy ORM
│   ├── parser.py        # parse_tsv → ParsedRow
│   ├── loader.py        # load_file → LoadReport
│   ├── targets.py       # generate_all, compute_branch_nps, …
│   └── schemas.py       # DTOs Pydantic compartidos
└── tests/
    ├── conftest.py
    ├── fixtures/
    │   ├── build_sample.py   # generador determinístico del .tsv
    │   └── sample.tsv        # 100 filas sintéticas latin-1
    ├── test_parser.py
    ├── test_loader.py
    └── test_targets.py
```
