---
tipo: m-doc
modulo: M1
estado: completado
paquete: core
pr: 2
tags:
  - plan-implementacion
  - modulo-m1
---

# M1 — Núcleo de datos

## Responsabilidad

M1 parsea los archivos TSV ISO-8859 de encuestas NPS de Banamex, persiste cada respuesta en SQLite con deduplicación por `record_id`, genera objetivos NPS anuales sintéticos por sucursal y expone una librería Python instalable (`core`) que los módulos M2/M3/M4 consumen como única puerta de entrada a los datos crudos. No clasifica contenido, no realiza llamadas HTTP, no entrena modelos.

Es el cimiento de datos de todo el sistema: si M1 falla o produce datos inconsistentes, el resto del pipeline no puede operar. Por ello tiene tests exhaustivos y un contrato estable declarado en `01_contratos_compartidos.md §2`, `§3` y `§4`.

## Entregables

- [ ] Paquete `core/` instalable con `pip install -e ./core` desde la raíz del repo.
- [ ] `core.db.init_schema()` aplica el SQL literal de `01_contratos_compartidos.md §2`.
- [ ] `core.db.get_session()` factory de sesión SQLAlchemy 2.x sobre `data/processed/banamex.db`.
- [ ] `core.parser.parse_tsv(path: Path) -> Iterator[ParsedRow]`. `ParsedRow` es un dataclass interno de `core.parser` con campos `row_num`, `is_valid`, `error: str | None`, `row: VerbalizationRow | None`, `response_date_iso: str | None`, `verbatim_clean: str | None`. La firma original prometía `Iterator[VerbalizationRow]` pero el contrato también exigía contabilizar inválidas en `rows_invalid`; `ParsedRow` resuelve ambos requisitos sin filtrar silenciosamente. El DTO público `VerbalizationRow` (en `schemas.py`) no se modifica — sigue siendo el tipo expuesto en `ParsedRow.row` cuando `is_valid=True`.
- [ ] `core.loader.load_file(path: Path) -> LoadReport` con dedup por `record_id`, cómputo de `sha256` del archivo y persistencia de filas válidas.
- [ ] `core.targets.generate_all(seed=42)` siguiendo la regla del `00_decisiones_tecnicas.md §15`.
- [ ] `core.targets.regenerate_for_branches(branch_ids: list[str])` para regeneración puntual.
- [ ] Fixture `core/tests/fixtures/sample.tsv` con 100 filas sintéticas (NO datos reales de Banamex), en encoding `latin-1` y schema idéntico a los corpora reales.
- [ ] README del paquete `core/README.md` en español: instalación, comandos disponibles, ejemplos de uso.

## Contratos consumidos

Ninguno. M1 es el módulo base del sistema; no depende de otros paquetes del workspace. Solo consume las decisiones de `00_decisiones_tecnicas.md` y los contratos de `01_contratos_compartidos.md`.

## Contratos producidos

- Tablas SQLite definidas en `01_contratos_compartidos.md §2`: `files`, `verbalizations`, `branches`, `branch_targets`. Las tablas `classifications`, `metadata_extractions`, `annotation_runs` y `classifier_runs` también se crean (parte del schema único) pero las llenan M2a/M2b.
- Modelos SQLAlchemy ORM declarados en `core/src/core/models_db.py` según `01_contratos_compartidos.md §3`.
- DTOs Pydantic declarados en `core/src/core/schemas.py` según `01_contratos_compartidos.md §4`: `VerbalizationRow`, `LoadReport`, `BranchTargetRow`, `NPSGroup`, `Polarity`, `ClassificationSource`.

## Estructura de archivos esperada

Réplica de `01_contratos_compartidos.md §1` para el subárbol `core/`:

```
core/
├── pyproject.toml
├── README.md
├── src/core/
│   ├── __init__.py
│   ├── db.py            # Engine SQLAlchemy, session factory, init_schema()
│   ├── schema.sql       # CREATE TABLE literales (fuente de verdad)
│   ├── models_db.py     # SQLAlchemy ORM mapeado al schema
│   ├── parser.py        # Parser TSV con tolerancia a encoding/quoting
│   ├── loader.py        # Carga incremental, dedup por sha256 y record_id
│   ├── targets.py       # Generación de objetivos NPS sintéticos
│   └── schemas.py       # DTOs Pydantic compartidos
└── tests/
    ├── fixtures/
    │   └── sample.tsv   # 100 filas sintéticas en latin-1
    ├── test_parser.py
    ├── test_loader.py
    └── test_targets.py
```

## Detalles de implementación clave

**Encoding (`00_decisiones_tecnicas.md §23`)**: los archivos `.txt` se abren con `open(path, encoding='latin-1', newline='')`. NUNCA UTF-8 a la lectura: los corpora vienen en ISO-8859 y UTF-8 fallaría con bytes no válidos. Internamente todo se normaliza a UTF-8 y SQLite persiste UTF-8.

**Parser TSV**: usar `csv.reader(file, delimiter='\t', quoting=csv.QUOTE_MINIMAL)`. Tolerar:

- Verbatim con comillas dobles (incluyendo escapadas `""`).
- Tabs accidentales dentro del verbatim: si una fila tiene más de 6 columnas, las columnas desde la 4 hasta `-2` se unen como verbatim, preservando el resto del schema.
- Line terminators `LF`, `CRLF` y `NEL` (por `newline=''` el módulo `csv` los maneja correctamente).

```python
import csv
from collections.abc import Iterator
from pathlib import Path

def parse_tsv(path: Path) -> Iterator[ParsedRow]:
    with open(path, encoding='latin-1', newline='') as f:
        reader = csv.reader(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
        for row_num, row in enumerate(reader, start=1):
            yield _normalize_row(row, row_num)  # devuelve ParsedRow (válida o no)
```

**Detección de filas inválidas**: se cuentan en `rows_invalid` (campo del `LoadReport`):

- Filas con menos de 6 columnas tras el split robusto.
- Fechas no parseables con ninguno de los formatos esperados.
- `nps_rate` fuera del rango `0..10`.
- `branch_id` vacío, NULL o ausente.
- `nps_group` no perteneciente a `{Promotor, Pasivo, Detractor}` (typos como "Pasivos" se reportan como inválidos, no se normalizan ciegamente).

**Normalización de fecha**: el input puede venir como `1/1/2025` o `01/01/2025`. Output ISO 8601 `YYYY-MM-DD`. Al cargar el primer archivo, inspeccionar una muestra de 100 filas para decidir entre `'%d/%m/%Y'` y `'%m/%d/%Y'` (heurística: si algún día > 12 en la primera posición → DD/MM; si algún día > 12 en la segunda → MM/DD; ambiguo → asumir `'%d/%m/%Y'` por convención latina). Documentar la asunción en el log (`structlog`) y en el README.

**sha256 del archivo**: computado leyendo el archivo en chunks de 64 KB.

```python
import hashlib

def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(64 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()
```

Es la llave única en la tabla `files`. Si el mismo archivo se sube dos veces, `load_file` devuelve `already_processed=True` y no inserta filas; el `LoadReport` refleja `rows_inserted=0`, `rows_duplicated=rows_total`.

**Dedup a nivel registro**: si un `record_id` ya existe en `verbalizations`, no se inserta y cuenta como duplicado en `rows_duplicated`. Implementar con `INSERT OR IGNORE` (sqlite-native) o lookup previo en lotes. Esto cubre el caso de overlap parcial entre archivos.

**Campos derivados de cada fila**:

- `has_verbatim`: `1` si `verbatim.strip()` tiene longitud `> 0`, `0` en caso contrario.
- `verbatim_clean`: aplicar `unicodedata.normalize('NFC', verbatim.strip())` y colapsar secuencias de espacios en blanco a un solo espacio (`re.sub(r'\s+', ' ', ...)`).
- `response_year`, `response_month`: derivados de `response_date` ya parseado.

**Catálogo de sucursales**: al cargar, hacer `INSERT OR IGNORE INTO branches(branch_id) VALUES (...)` por cada `branch_id` detectado en el archivo. No se asume prefijo (`branch_id` con o sin `A-` se acepta tal cual; sólo se valida que no sea vacío).

**Generación de objetivos sintéticos (`00_decisiones_tecnicas.md §15`)**: implementar la fórmula exacta.

```python
import numpy as np

def generate_target_for_branch(branch_id: str, nps_historico: float | None) -> int:
    seed_source = branch_id.removeprefix('A-') if branch_id.startswith('A-') else branch_id
    try:
        seed = int(seed_source)
    except ValueError:
        seed = abs(hash(branch_id)) % (2**31)
    rng = np.random.default_rng(seed=seed)
    if nps_historico is None:
        base = 65 + rng.normal(0, 5)
    else:
        perturbacion = rng.normal(loc=3, scale=4)
        base = nps_historico + perturbacion
    return int(np.clip(base, 50, 85))
```

Para el NPS histórico de cada sucursal, implementar `compute_branch_nps(branch_id)` que devuelve `(% promotores − % detractores)` calculado solo sobre filas existentes en `verbalizations`. Si la sucursal tiene `< 10` respuestas, se usa el NPS nacional como base. Persistir en `branch_targets` con `is_synthetic=1`.

La función `generate_all` es **idempotente**: si ya existen filas en `branch_targets`, no las regenera salvo flag `force=True`. `regenerate_for_branches(branch_ids)` elimina y regenera solo las sucursales indicadas.

**Engine SQLAlchemy y PRAGMA**: usar el patrón moderno de SQLAlchemy 2.x.

```python
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

engine = create_engine("sqlite:///./data/processed/banamex.db", future=True)

@event.listens_for(engine, "connect")
def _enable_fk(dbapi_connection, _):
    cur = dbapi_connection.cursor()
    cur.execute("PRAGMA foreign_keys = ON")
    cur.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, future=True)
```

`init_schema()` lee `schema.sql` y ejecuta cada statement con `engine.begin()`. Es idempotente: las sentencias `CREATE TABLE` no usan `IF NOT EXISTS` en el contrato de `§2`, así que `init_schema()` envuelve la ejecución en try/except por `OperationalError "already exists"` o, alternativamente, verifica con `sqlalchemy.inspect(engine).get_table_names()` antes de aplicar.

**`LoadReport`**: incluye todos los campos del Pydantic definido en `01_contratos_compartidos.md §4`: `file_id`, `filename`, `rows_total`, `rows_inserted`, `rows_duplicated`, `rows_invalid`, `branches_detected`, `date_range`, `months_available` y `already_processed: bool` (campo del DTO, no del schema persistido; lo pobla `load_file` con `True` cuando el `sha256` ya existía en `files`).

## Tests requeridos

Mínimo 12 casos en `core/tests/`:

1. **Parser tolera encoding `latin-1`** con acentos (`á é í ó ú`) y `ñ`/`Ñ` sin pérdida ni `UnicodeDecodeError`.
2. **Parser tolera CRLF, LF y NEL** como line terminators en el mismo archivo.
3. **Parser tolera verbatim con comillas dobles**, incluyendo escapadas: `"texto con ""comillas"" internas"`.
4. **Parser tolera tabs accidentales dentro del verbatim**: una fila con 8 columnas físicas se reagrupa a 6 lógicas uniendo las columnas centrales como verbatim.
5. **Parser reporta como inválida** una fila con menos de 6 columnas.
6. **Parser reporta como inválida** una fila con `nps_rate=11` (fuera de rango).
7. **Parser reporta como inválida** una fila con `nps_group="Pasivos"` (typo).
8. **Loader: cargar el mismo archivo dos veces** → segunda llamada devuelve `rows_inserted=0`, `rows_duplicated=rows_total`, `already_processed=True`.
9. **Loader: cargar archivo con 50% de overlap de `record_id`** con un archivo previo → `rows_inserted` = mitad nueva, `rows_duplicated` = mitad existente.
10. **Targets: generar dos veces con misma seed** produce los mismos números para cada `branch_id` (determinismo).
11. **Targets: el `nps_target_annual` siempre cae en `[50, 85]`** para cualquier `nps_historico` de entrada.
12. **Schema init es idempotente**: ejecutar `init_schema()` dos veces consecutivas no levanta excepción y deja la DB en el mismo estado.
13. **Fixture `sample.tsv` de 100 filas se carga sin errores**: `load_file('core/tests/fixtures/sample.tsv')` reporta `rows_invalid=0`, `rows_inserted=100`, `branches_detected` no vacío.
14. **`compute_branch_nps` con `<10` respuestas** cae al NPS nacional como base.

## Definition of Done

- `pytest core/tests` pasa al 100% sin warnings críticos.
- `python -c "from core.db import init_schema; init_schema()"` crea el archivo `data/processed/banamex.db` con todas las tablas del `§2`.
- Smoke:

  ```bash
  python -c "from core.loader import load_file; print(load_file('data/raw/1_mitad_2026.txt'))"
  ```

  reporta `rows_total ≈ 102,378`.
- Cargar los 3 corpora reales (`1_mitad_2025c.txt`, `2_mitad_2025.txt`, `1_mitad_2026.txt`) termina en `< 30s` en máquina del usuario y el total agregado es `≈ 474,026 filas` (el número exacto puede variar por dedup interna del corpus).
- `core/README.md` escrito en español con secciones: Instalación, Comandos, Ejemplos, Notas.
- `core/tests/fixtures/sample.tsv` existe con 100 filas sintéticas en encoding `latin-1`, mismo schema y separador que los corpora reales, sin contener datos reales de Banamex.
- Cumple `01_contratos_compartidos.md §14` (DoD compartidas): `pyproject.toml`, tests verdes, README, sin secrets.

## Riesgos específicos del módulo

- **Encoding atípico en algunas líneas**: pese a abrir como `latin-1`, líneas con bytes corruptos pueden romper la decodificación. Mitigación: fallback `errors='replace'` al decodificar con `structlog` log de warning incluyendo número de línea; no abortar la carga.
- **Tab dentro de verbatim sin escapar**: al menos una línea de los corpora reales lo tiene. Mitigación: split robusto con conteo de columnas — si una fila tiene `>6` columnas, las columnas `4` hasta `-2` se unen como verbatim y se preserva la columna `-1` como `branch_id`.
- **Fechas en formato ambiguo**: `1/1/2025` admite DD/MM y MM/DD. Mitigación: inspección de muestra al cargar el primer archivo para fijar el formato, decisión registrada en log; si se detecta cambio de formato en archivos posteriores, abortar con error explícito.
- **`nps_group` con typos** (e.g., `"Pasivos"` con `s`, `"Promotores"`): no aplicar normalización ciega. Reportar la fila como inválida (`rows_invalid`) y emitir log con conteo agregado al final del `load_file`.
- **`branch_id` con prefijo distinto a `"A-"`**: aceptar cualquier formato no vacío. No asumir el prefijo en validaciones del parser. La función de targets maneja el caso con un fallback a `hash(branch_id)` cuando `removeprefix('A-')` no produce un entero.
- **DB corrupta o lockeada** al ejecutar en paralelo: SQLite con WAL ayuda; documentar en el README que `core` no soporta acceso concurrente desde múltiples procesos en escritura (solo M1 escribe en `verbalizations`).
