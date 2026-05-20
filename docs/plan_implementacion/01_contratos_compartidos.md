# 01 — Contratos compartidos

Este archivo es la **fuente única de verdad** para todos los contratos entre módulos: estructura de carpetas, schema SQLite, schemas Pydantic/TypeScript compartidos, schema JSON del motor, API Python pública del motor, endpoints HTTP, y el mapeo taxonomía → buckets UI.

Toda sesión de implementación lo lee antes de empezar. **Si una sesión cree que un contrato es incorrecto, no lo modifica**: anota la duda en `docs/plan_implementacion/contracts_issues.md` (crear si no existe) y continúa con el contrato vigente. El usuario integra los issues al final.

---

## §1. Estructura del proyecto

```
sentiment-analysis-banamex/
├── api/                              # Backend HTTP (M4)
│   ├── pyproject.toml
│   ├── src/api/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app, registro de routers, middleware
│   │   ├── settings.py               # Pydantic Settings (.env)
│   │   ├── deps.py                   # Dependencias: get_db, get_current_user
│   │   ├── auth.py                   # JWT encode/decode
│   │   ├── errors.py                 # Exception handlers
│   │   ├── models_api.py             # Pydantic request/response (re-exporta de analytics)
│   │   ├── export_openapi.py         # Script export openapi.json
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       ├── upload.py
│   │       ├── validation.py
│   │       ├── national.py
│   │       ├── branches.py
│   │       └── admin.py
│   ├── tests/
│   └── Dockerfile
├── core/                             # Núcleo de datos (M1)
│   ├── pyproject.toml
│   ├── src/core/
│   │   ├── __init__.py
│   │   ├── db.py                     # Engine SQLAlchemy, session, init_schema()
│   │   ├── schema.sql                # CREATE TABLE literales (fuente de verdad)
│   │   ├── models_db.py              # SQLAlchemy ORM mapeado al schema
│   │   ├── parser.py                 # Parser TSV
│   │   ├── loader.py                 # Carga incremental + dedup
│   │   ├── targets.py                # Generación objetivos sintéticos
│   │   └── schemas.py                # Pydantic DTOs compartidos
│   └── tests/
│       ├── fixtures/
│       │   └── sample.tsv            # 100 filas sintéticas
│       ├── test_parser.py
│       ├── test_loader.py
│       └── test_targets.py
├── engine/                           # Motor de análisis (M2a + M2b)
│   ├── pyproject.toml
│   ├── src/engine/
│   │   ├── __init__.py
│   │   ├── taxonomy.py               # Parsea docs/taxonomia_revisada.md → dict
│   │   ├── prompts.py                # SYSTEM_PROMPT, OUTPUT_SCHEMA (M2a)
│   │   ├── annotator.py              # Cliente Ollama local (M2a)
│   │   ├── extractors.py             # 4 extractores rule-based (M2a)
│   │   ├── embeddings.py             # Embedder cacheado (M2b)
│   │   ├── trainer.py                # Entrenamiento clasificador (M2b)
│   │   ├── classifier.py             # Inferencia clasificador (M2b)
│   │   ├── pipeline.py               # API pública classify() (M2b)
│   │   ├── ui_buckets.py             # Mapeo L1 → bucket UI (M2b)
│   │   ├── mocks.py                  # Mocks determinísticos para consumidores
│   │   ├── cli.py                    # Comandos CLI
│   │   └── data/
│   │       ├── spanish_names.txt
│   │       ├── mexican_banks.txt
│   │       └── channel_keywords.txt
│   └── tests/
├── analytics/                        # Agregaciones y análisis (M3)
│   ├── pyproject.toml
│   ├── src/analytics/
│   │   ├── __init__.py
│   │   ├── schemas.py                # DTOs Pydantic (la API los re-exporta)
│   │   ├── nps.py
│   │   ├── ranking.py
│   │   ├── trends.py
│   │   ├── topics.py
│   │   ├── words.py
│   │   ├── representatives.py
│   │   ├── insights.py
│   │   ├── impact.py
│   │   ├── personnel.py
│   │   └── data/
│   │       └── stopwords_es_banking.txt
│   └── tests/
├── web/                              # Frontend SPA (M5)
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   ├── index.html
│   ├── public/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── routes.tsx
│   │   ├── api/
│   │   │   ├── client.ts             # Cliente generado de OpenAPI
│   │   │   └── queryClient.ts        # TanStack Query setup
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx
│   │   │   ├── UploadPage.tsx
│   │   │   ├── NationalYTDPage.tsx
│   │   │   ├── NationalComparePage.tsx
│   │   │   ├── BranchYTDPage.tsx
│   │   │   ├── BranchComparePage.tsx
│   │   │   └── AdminPage.tsx
│   │   ├── components/
│   │   │   ├── Layout.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── NPSCard.tsx
│   │   │   ├── DistributionChart.tsx
│   │   │   ├── TrendChart.tsx
│   │   │   ├── CausesPanel.tsx
│   │   │   ├── StrengthsPanel.tsx
│   │   │   ├── CriticalBranchesTable.tsx
│   │   │   ├── RankingsPanel.tsx
│   │   │   ├── ActionsPanel.tsx
│   │   │   ├── BranchSelector.tsx
│   │   │   ├── WordsCloud.tsx
│   │   │   ├── RepresentativeComments.tsx
│   │   │   ├── PersonnelTable.tsx
│   │   │   └── InsightsList.tsx
│   │   ├── hooks/
│   │   │   ├── useAuth.ts
│   │   │   └── useBranch.ts
│   │   ├── lib/
│   │   │   ├── format.ts
│   │   │   └── colors.ts
│   │   └── mocks/
│   │       ├── handlers.ts           # MSW handlers
│   │       └── fixtures.ts           # Data sintética
│   ├── tests/
│   └── Dockerfile
├── scripts/
│   ├── preprocess_corpora.py         # Pipeline completo offline
│   ├── seed_db.py                    # Copia DB pre-generada
│   ├── smoke_test.sh                 # E2E HTTP test
│   └── generate_openapi_client.sh    # openapi → cliente TS
├── data/
│   ├── raw/                          # gitignored, ya existe
│   ├── processed/
│   │   └── banamex.db
│   └── models/
│       └── classifier.joblib
├── docker-compose.yml
├── .env.example
├── README_DEMO.md
├── pyproject.toml                    # Workspace root opcional
└── docs/                             # ya existe
```

Cada paquete Python tiene su `pyproject.toml` y se instala localmente con `pip install -e ./core ./engine ./analytics ./api` desde la raíz. Esto permite imports limpios entre módulos sin trucos de `sys.path`.

---

## §2. Schema SQLite completo

El siguiente SQL es **autoritativo**. Vive en `core/src/core/schema.sql` y `core.db.init_schema()` lo ejecuta literalmente. Cualquier cambio se aplica re-creando el archivo `.db` (no hay migraciones).

```sql
-- ===========================
-- TABLA: files
-- Registra cada archivo cargado. Permite dedup a nivel archivo por sha256.
-- ===========================
CREATE TABLE files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    sha256 TEXT NOT NULL UNIQUE,
    rows_total INTEGER NOT NULL,
    rows_inserted INTEGER NOT NULL,
    rows_duplicated INTEGER NOT NULL,
    rows_invalid INTEGER NOT NULL,
    uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ===========================
-- TABLA: verbalizations
-- Cada fila = una respuesta de encuesta. record_id es PK por garantía del corpus.
-- ===========================
CREATE TABLE verbalizations (
    record_id TEXT PRIMARY KEY,
    file_id INTEGER NOT NULL REFERENCES files(id),
    response_date TEXT NOT NULL,                 -- ISO 8601 YYYY-MM-DD
    response_year INTEGER NOT NULL,
    response_month INTEGER NOT NULL,             -- 1..12
    nps_group TEXT NOT NULL CHECK (nps_group IN ('Promotor','Pasivo','Detractor')),
    nps_rate INTEGER NOT NULL CHECK (nps_rate BETWEEN 0 AND 10),
    verbatim TEXT,                               -- texto original (puede ser NULL/vacío)
    verbatim_clean TEXT,                         -- normalizado (strip, NFC)
    branch_id TEXT NOT NULL,
    has_verbatim INTEGER NOT NULL                -- 0/1, derivado
);

CREATE INDEX idx_verb_branch ON verbalizations(branch_id);
CREATE INDEX idx_verb_date ON verbalizations(response_year, response_month);
CREATE INDEX idx_verb_nps_group ON verbalizations(nps_group);
CREATE INDEX idx_verb_has_verbatim ON verbalizations(has_verbatim);

-- ===========================
-- TABLA: branches
-- Catálogo de sucursales detectadas. Se inserta al cargar archivos.
-- ===========================
CREATE TABLE branches (
    branch_id TEXT PRIMARY KEY,                  -- formato "A-1234"
    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ===========================
-- TABLA: branch_targets
-- Objetivos NPS anuales sintéticos. is_synthetic siempre 1 en MVP.
-- ===========================
CREATE TABLE branch_targets (
    branch_id TEXT PRIMARY KEY REFERENCES branches(branch_id),
    nps_target_annual INTEGER NOT NULL,
    generated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_synthetic INTEGER NOT NULL DEFAULT 1
);

-- ===========================
-- TABLA: classifications
-- Multilabel: una verbalización puede tener N filas (una por par L1/L2 asignado).
-- L3 solo viene del golden set (source='llm_annotation').
-- ===========================
CREATE TABLE classifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT NOT NULL REFERENCES verbalizations(record_id),
    l1_code TEXT NOT NULL,                       -- "1".."15"
    l1_name TEXT NOT NULL,
    l2_code TEXT NOT NULL,                       -- "1.1", "1.2", ...
    l2_name TEXT NOT NULL,
    l3_code TEXT,                                -- "1.1.1" o NULL
    l3_name TEXT,
    confidence REAL NOT NULL,                    -- 0.0..1.0
    source TEXT NOT NULL CHECK (source IN ('llm_annotation','classifier','fallback')),
    polarity TEXT NOT NULL CHECK (polarity IN ('pos','neu','neg')),
    ui_bucket TEXT NOT NULL,                     -- ver §6
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_class_record ON classifications(record_id);
CREATE INDEX idx_class_l1 ON classifications(l1_code);
CREATE INDEX idx_class_bucket ON classifications(ui_bucket);
CREATE INDEX idx_class_polarity ON classifications(polarity);
CREATE INDEX idx_class_source ON classifications(source);

-- ===========================
-- TABLA: metadata_extractions
-- 1:1 con verbalizations. Producida por extractores rule-based de M2a.
-- ===========================
CREATE TABLE metadata_extractions (
    record_id TEXT PRIMARY KEY REFERENCES verbalizations(record_id),
    personnel_named INTEGER NOT NULL DEFAULT 0,  -- 0/1
    personnel_name TEXT,                         -- nombre extraído o NULL
    personnel_polarity TEXT CHECK (personnel_polarity IN ('pos','neg')),
    explicit_recommendation TEXT CHECK (explicit_recommendation IN ('pos','neg')),
    mentions_other_bank INTEGER NOT NULL DEFAULT 0,
    other_bank_names TEXT,                       -- JSON array (string)
    channels_mentioned TEXT,                     -- JSON array (string)
    extracted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_meta_personnel ON metadata_extractions(personnel_named);
CREATE INDEX idx_meta_recommendation ON metadata_extractions(explicit_recommendation);

-- ===========================
-- TABLA: annotation_runs
-- Trazabilidad de corridas del anotador LLM.
-- ===========================
CREATE TABLE annotation_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_size INTEGER NOT NULL,
    model TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    runtime_seconds REAL,
    status TEXT NOT NULL CHECK (status IN ('running','done','failed'))
);

-- ===========================
-- TABLA: classifier_runs
-- Trazabilidad de entrenamientos del clasificador.
-- ===========================
CREATE TABLE classifier_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_path TEXT NOT NULL,
    trained_on_run_id INTEGER REFERENCES annotation_runs(id),
    trained_at TEXT NOT NULL,
    n_samples INTEGER NOT NULL,
    n_labels INTEGER NOT NULL,
    f1_micro REAL,
    f1_macro REAL,
    hamming_loss REAL
);
```

---

## §3. Modelos SQLAlchemy ORM

`core/src/core/models_db.py` declara los modelos ORM mapeados al schema. Convención: nombre Python `CamelCase` singular, tabla SQL `snake_case` plural.

```python
from datetime import datetime
from sqlalchemy import String, Integer, Float, ForeignKey, CheckConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class File(Base):
    __tablename__ = "files"
    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str]
    sha256: Mapped[str] = mapped_column(unique=True)
    rows_total: Mapped[int]
    rows_inserted: Mapped[int]
    rows_duplicated: Mapped[int]
    rows_invalid: Mapped[int]
    uploaded_at: Mapped[str]

class Verbalization(Base):
    __tablename__ = "verbalizations"
    record_id: Mapped[str] = mapped_column(primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"))
    response_date: Mapped[str]
    response_year: Mapped[int]
    response_month: Mapped[int]
    nps_group: Mapped[str]
    nps_rate: Mapped[int]
    verbatim: Mapped[str | None]
    verbatim_clean: Mapped[str | None]
    branch_id: Mapped[str]
    has_verbatim: Mapped[int]

class Branch(Base):
    __tablename__ = "branches"
    branch_id: Mapped[str] = mapped_column(primary_key=True)
    first_seen_at: Mapped[str]

class BranchTarget(Base):
    __tablename__ = "branch_targets"
    branch_id: Mapped[str] = mapped_column(ForeignKey("branches.branch_id"), primary_key=True)
    nps_target_annual: Mapped[int]
    generated_at: Mapped[str]
    is_synthetic: Mapped[int]

class Classification(Base):
    __tablename__ = "classifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    record_id: Mapped[str] = mapped_column(ForeignKey("verbalizations.record_id"))
    l1_code: Mapped[str]
    l1_name: Mapped[str]
    l2_code: Mapped[str]
    l2_name: Mapped[str]
    l3_code: Mapped[str | None]
    l3_name: Mapped[str | None]
    confidence: Mapped[float]
    source: Mapped[str]
    polarity: Mapped[str]
    ui_bucket: Mapped[str]
    created_at: Mapped[str]

class MetadataExtraction(Base):
    __tablename__ = "metadata_extractions"
    record_id: Mapped[str] = mapped_column(ForeignKey("verbalizations.record_id"), primary_key=True)
    personnel_named: Mapped[int]
    personnel_name: Mapped[str | None]
    personnel_polarity: Mapped[str | None]
    explicit_recommendation: Mapped[str | None]
    mentions_other_bank: Mapped[int]
    other_bank_names: Mapped[str | None]   # JSON string
    channels_mentioned: Mapped[str | None] # JSON string
    extracted_at: Mapped[str]

class AnnotationRun(Base):
    __tablename__ = "annotation_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    sample_size: Mapped[int]
    model: Mapped[str]
    started_at: Mapped[str]
    finished_at: Mapped[str | None]
    runtime_seconds: Mapped[float | None]
    status: Mapped[str]

class ClassifierRun(Base):
    __tablename__ = "classifier_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    model_path: Mapped[str]
    trained_on_run_id: Mapped[int | None] = mapped_column(ForeignKey("annotation_runs.id"))
    trained_at: Mapped[str]
    n_samples: Mapped[int]
    n_labels: Mapped[int]
    f1_micro: Mapped[float | None]
    f1_macro: Mapped[float | None]
    hamming_loss: Mapped[float | None]
```

---

## §4. Pydantic DTOs compartidos

`core/src/core/schemas.py` declara los DTOs usados por M1 y consumidos por todos los demás. `analytics/src/analytics/schemas.py` declara los DTOs adicionales de M3 que la API re-exporta a M4.

### DTOs base (en `core.schemas`)

```python
from typing import Literal
from pydantic import BaseModel, Field

NPSGroup = Literal["Promotor", "Pasivo", "Detractor"]
Polarity = Literal["pos", "neu", "neg"]
ClassificationSource = Literal["llm_annotation", "classifier", "fallback"]

class VerbalizationRow(BaseModel):
    record_id: str
    response_date: str  # ISO 8601
    nps_group: NPSGroup
    nps_rate: int = Field(ge=0, le=10)
    verbatim: str | None = None
    branch_id: str

class LoadReport(BaseModel):
    file_id: int
    filename: str
    rows_total: int
    rows_inserted: int
    rows_duplicated: int
    rows_invalid: int
    branches_detected: list[str]
    date_range: tuple[str, str]  # (min_date, max_date)
    months_available: list[str]  # ["2025-01", "2025-02", ...]

class BranchTargetRow(BaseModel):
    branch_id: str
    nps_target_annual: int
    is_synthetic: bool = True
```

### DTOs de motor (en `engine.pipeline`)

```python
from typing import TypedDict, Literal

class CategoryPrediction(TypedDict):
    l1_code: str
    l1_name: str
    l2_code: str
    l2_name: str
    l3_code: str | None
    l3_name: str | None
    confidence: float

class Metadata(TypedDict):
    personnel_named: bool
    personnel_name: str | None
    personnel_polarity: Literal["pos", "neg"] | None
    explicit_recommendation: Literal["pos", "neg"] | None
    mentions_other_bank: bool
    other_bank_names: list[str]
    channels_mentioned: list[str]

class ClassificationResult(TypedDict):
    record_id: str
    is_classifiable: bool
    categories: list[CategoryPrediction]
    polarity: Literal["pos", "neu", "neg"]
    metadata: Metadata
```

### DTOs de analytics (en `analytics.schemas`)

```python
from pydantic import BaseModel
from typing import Literal

NPSGroup = Literal["Promotor", "Pasivo", "Detractor"]

class NPSDistribution(BaseModel):
    promoters_pct: float
    passives_pct: float
    detractors_pct: float
    promoters_count: int
    passives_count: int
    detractors_count: int

class NPSSummary(BaseModel):
    nps_actual: float
    nps_target: float | None
    gap: float | None
    total_responses: int
    distribution: NPSDistribution

class MonthlyPoint(BaseModel):
    month: str  # "2026-01"
    nps: float
    responses: int

class MonthlyTrend(BaseModel):
    points: list[MonthlyPoint]

class CauseBucket(BaseModel):
    bucket: str          # nombre UI
    count: int           # menciones
    pct_of_group: float  # % de detractores que mencionan
    sample_l2: list[str] # L2 más representativas dentro del bucket

class StrengthBucket(BaseModel):
    bucket: str
    count: int
    pct_of_group: float
    sample_l2: list[str]

class CriticalBranch(BaseModel):
    branch_id: str
    nps_actual: float
    nps_target: int | None
    gap: float | None
    detractors_pct: float
    triggered_conditions: list[str]  # cuáles de las 4 condiciones disparó

class Ranking(BaseModel):
    name: str
    items: list[dict]  # {branch_id, value, label}

class Rankings(BaseModel):
    worst_nps: Ranking
    worst_gap: Ranking
    most_detractors: Ranking
    worsened: Ranking
    improved: Ranking

class SuggestedAction(BaseModel):
    text: str
    priority: Literal["alta", "media", "baja"]
    related_bucket: str | None
    related_branches: list[str] = []

class ImpactByCategory(BaseModel):
    bucket: str
    impact_points: float  # cuántos puntos de NPS subiría si se elimina la categoría

class Insight(BaseModel):
    text: str
    category: Literal["nps","brecha","fortaleza","fricción","personal","comparación","cobertura"]

class WordFrequency(BaseModel):
    word: str
    count: int
    group: NPSGroup | None = None

class RepresentativeComment(BaseModel):
    record_id: str
    verbatim: str
    nps_rate: int
    nps_group: NPSGroup
    response_date: str
    bucket: str

class PersonnelMention(BaseModel):
    name: str
    polarity: Literal["pos","neg"]
    count: int
    example_record_id: str
    example_verbatim: str

class NationalYTD(BaseModel):
    nps: NPSSummary
    trend: MonthlyTrend
    causes: list[CauseBucket]
    strengths: list[StrengthBucket]
    critical_branches: list[CriticalBranch]
    rankings: Rankings
    actions: list[SuggestedAction]
    impact: list[ImpactByCategory]
    insights: list[Insight]
    branches_total: int
    branches_with_target: int

class BranchYTD(BaseModel):
    branch_id: str
    nps: NPSSummary
    trend: MonthlyTrend
    causes: list[CauseBucket]
    strengths: list[StrengthBucket]
    actions: list[SuggestedAction]
    insights: list[Insight]
    top_words: list[WordFrequency]
    representatives: list[RepresentativeComment]
    personnel: list[PersonnelMention]

class MonthlyComparison(BaseModel):
    month_a: str
    month_b: str
    nps_a: float
    nps_b: float
    nps_change: float
    distribution_a: NPSDistribution
    distribution_b: NPSDistribution
    causes_a: list[CauseBucket]
    causes_b: list[CauseBucket]
    causes_increased: list[str]
    causes_decreased: list[str]
    strengths_a: list[StrengthBucket]
    strengths_b: list[StrengthBucket]
    strengths_increased: list[str]
    strengths_decreased: list[str]
    branches_improved: list[CriticalBranch]
    branches_worsened: list[CriticalBranch]
    actions: list[SuggestedAction]

class ValidationSummary(BaseModel):
    files_processed: int
    rows_loaded: int
    rows_new: int
    rows_duplicated_ignored: int
    branches_detected: int
    period_available: tuple[str, str]
    months_available: list[str]
    columns_detected: list[str]
    rows_valid: int
    rows_empty_verbatim: int
    rows_invalid_nps: int
    rows_missing_branch: int
    rows_duplicate_record_id: int
    rows_invalid_date: int

class CoverageSummary(BaseModel):
    branches_detected: int
    branches_with_target: int
    branches_without_target: list[str]
    branches_with_target_no_responses: list[str]
    invalid_targets: list[str]
    duplicate_targets: list[str]
```

---

## §5. Schema JSON del output del LLM anotador

`engine/src/engine/prompts.py` define `OUTPUT_SCHEMA` literal. El cliente Ollama lo pasa como `format=OUTPUT_SCHEMA` en cada request (constrained decoding nativo desde Ollama 0.5). El modelo está obligado a producir JSON que valide.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "VerbalizationClassification",
  "type": "object",
  "required": ["record_id", "is_classifiable", "categories"],
  "additionalProperties": false,
  "properties": {
    "record_id": {
      "type": "string",
      "description": "El record_id de la verbalización a clasificar"
    },
    "is_classifiable": {
      "type": "boolean",
      "description": "false si el texto está vacío, es ininteligible, o no contiene contenido temático"
    },
    "categories": {
      "type": "array",
      "minItems": 0,
      "maxItems": 5,
      "items": {
        "type": "object",
        "required": ["l1_code", "l1_name", "l2_code", "l2_name", "confidence"],
        "additionalProperties": false,
        "properties": {
          "l1_code": {
            "type": "string",
            "enum": ["1","2","3","4","5","6","7","8","9","10","11","12","13","14","15"]
          },
          "l1_name": {"type": "string"},
          "l2_code": {"type": "string"},
          "l2_name": {"type": "string"},
          "l3_code": {"type": ["string", "null"]},
          "l3_name": {"type": ["string", "null"]},
          "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Confianza subjetiva del clasificador en esta etiqueta"
          }
        }
      }
    }
  }
}
```

El SYSTEM_PROMPT incluye la taxonomía completa serializada a partir de `docs/taxonomia_revisada.md` (M2a parsea el markdown para extraer la jerarquía).

---

## §6. Mapeo taxonomía L1 → buckets UI

Tabla autoritativa. `engine/src/engine/ui_buckets.py` la implementa como dict. La columna `classifications.ui_bucket` se llena con este mapeo.

| `ui_bucket` | L1 incluido(s) | Para causas | Para fortalezas |
|---|---|:---:|:---:|
| `Atención del personal` | 1. Atención al cliente | ✓ | ✓ |
| `Tiempos y espera` | 2. Tiempos y operación | ✓ | ✓ |
| `Sucursal física` | 3. Sucursal física | ✓ | ✓ |
| `Cajeros (ATM)` | 4. Cajeros automáticos | ✓ | ✓ |
| `Canales digitales` | 5. Canales digitales | ✓ | ✓ |
| `Productos y promociones` | 6. Productos, 11. Programas y beneficios | ✓ | ✓ |
| `Operaciones transaccionales` | 7. Operaciones transaccionales | ✓ | ✓ |
| `Costos` | 8. Costos | ✓ | ✗ |
| `Aclaraciones, quejas y fraude` | 9. Aclaraciones, quejas y fraude | ✓ | ✗ |
| `Procesos y requisitos` | 10. Procesos y requisitos | ✓ | ✗ |
| `Otros` | 12. Comunicación, 13. Marca y confianza, 14. Genérico, 15. No clasificable | ✗ | ✗ |

```python
# engine/src/engine/ui_buckets.py
UI_BUCKETS_BY_L1: dict[str, str] = {
    "1":  "Atención del personal",
    "2":  "Tiempos y espera",
    "3":  "Sucursal física",
    "4":  "Cajeros (ATM)",
    "5":  "Canales digitales",
    "6":  "Productos y promociones",
    "7":  "Operaciones transaccionales",
    "8":  "Costos",
    "9":  "Aclaraciones, quejas y fraude",
    "10": "Procesos y requisitos",
    "11": "Productos y promociones",  # se une con 6
    "12": "Otros",
    "13": "Otros",
    "14": "Otros",
    "15": "Otros",
}

# Cuáles buckets aparecen en cada vista
CAUSE_BUCKETS = ["Atención del personal", "Tiempos y espera", "Sucursal física",
                 "Cajeros (ATM)", "Canales digitales", "Productos y promociones",
                 "Operaciones transaccionales", "Costos",
                 "Aclaraciones, quejas y fraude", "Procesos y requisitos"]

STRENGTH_BUCKETS = ["Atención del personal", "Tiempos y espera", "Sucursal física",
                    "Cajeros (ATM)", "Canales digitales", "Productos y promociones",
                    "Operaciones transaccionales"]

def assign_ui_bucket(l1_code: str) -> str:
    return UI_BUCKETS_BY_L1.get(l1_code, "Otros")
```

---

## §7. API Python pública del motor

Lo que `analytics/`, `api/` y los scripts importan de `engine`:

```python
# engine.pipeline
def classify(record_id: str, text: str, nps_group: str) -> ClassificationResult: ...
def classify_batch(items: list[tuple[str, str, str]]) -> list[ClassificationResult]: ...

# engine.extractors (uso directo en preprocessing)
def extract_all(text: str) -> Metadata: ...

# engine.taxonomy (acceso a la taxonomía cargada)
def load_taxonomy() -> dict: ...  # estructura: {l1_code: {name, l2: {l2_code: {name, l3: {...}}}}}
def get_l2_name(l1_code: str, l2_code: str) -> str: ...
```

Antes de que M2b esté listo, M3, M4 y M5 pueden importar de `engine.mocks`:

```python
# engine.mocks
def classify_mock(record_id: str, text: str, nps_group: str) -> ClassificationResult:
    """Devuelve clasificación determinística basada en hash del texto."""
```

---

## §8. Endpoints FastAPI

Lista exhaustiva. Cada endpoint produce un schema Pydantic ya definido en §4.

### Auth

```
POST   /auth/login
       Request:  {username: str, password: str}
       Response: {token: str, expires_at: str}
       Errors:   ninguno relevante en MVP

GET    /auth/me
       Headers:  Authorization: Bearer <token>
       Response: {username: str}
       Errors:   401 si token inválido o ausente
```

### Upload y validación

```
POST   /upload
       Headers:  Authorization: Bearer <token>
       Body:     multipart/form-data, file: .txt
       Response: {file_id: int, validation_summary: ValidationSummary,
                  already_processed: bool}
       Errors:   400 si archivo no es .txt o > 50 MB
                 422 si parsing falla

GET    /upload/{file_id}/status
       Response: {file_id, status: 'parsing'|'classifying'|'done'|'error',
                  progress: float, error: str | null}

GET    /validation
       Response: ValidationSummary (agregado de todos los archivos)

GET    /validation/coverage
       Response: CoverageSummary
```

### Nacional

```
GET    /national/ytd
       Response: NationalYTD

GET    /national/trend
       Response: MonthlyTrend

GET    /national/compare?month_a=2026-01&month_b=2026-02
       Response: MonthlyComparison
       Errors:   422 si algún mes no existe; el detalle lista meses válidos

GET    /national/critical-branches?limit=10
       Response: list[CriticalBranch]

GET    /national/rankings
       Response: Rankings

GET    /national/causes?group=Detractor&limit=10
       Response: list[CauseBucket]

GET    /national/strengths?group=Promotor&limit=10
       Response: list[StrengthBucket]

GET    /national/actions?limit=10
       Response: list[SuggestedAction]

GET    /national/impact
       Response: list[ImpactByCategory]

GET    /national/insights
       Response: list[Insight]

GET    /national/passive-analysis
       Response: {near_promoter: list[CauseBucket], near_detractor: list[CauseBucket]}
```

### Sucursales

```
GET    /branches?q=A-1
       Response: list[{branch_id, response_count, has_target}]

GET    /branches/{branch_id}/ytd
       Response: BranchYTD
       Errors:   404 si la sucursal no existe en la base

GET    /branches/{branch_id}/trend
       Response: MonthlyTrend

GET    /branches/{branch_id}/compare?month_a=&month_b=
       Response: MonthlyComparison

GET    /branches/{branch_id}/causes
       Response: list[CauseBucket]

GET    /branches/{branch_id}/strengths
       Response: list[StrengthBucket]

GET    /branches/{branch_id}/words?group=Detractor&top_n=30
       Response: list[WordFrequency]

GET    /branches/{branch_id}/representatives?n_per_topic=2
       Response: list[RepresentativeComment]

GET    /branches/{branch_id}/personnel
       Response: list[PersonnelMention]

GET    /branches/{branch_id}/actions
       Response: list[SuggestedAction]

GET    /branches/{branch_id}/insights
       Response: list[Insight]
```

### Administración (POC)

```
GET    /admin/files
       Response: list[{id, filename, sha256, rows_inserted, uploaded_at}]

GET    /admin/runs
       Response: {annotation_runs: list[...], classifier_runs: list[...]}
```

### Salud

```
GET    /healthz
       Response: {status: 'ok', db_path: str, classifier_loaded: bool}
       Auth:     no requiere
```

---

## §9. Convención de errores HTTP

Toda respuesta de error es JSON con la estructura:

```json
{
  "detail": "Mensaje legible en español para el usuario final.",
  "code": "string_snake_case_para_logging",
  "hint": "Sugerencia accionable (opcional)."
}
```

Códigos HTTP:

- **200**: éxito.
- **400**: error del cliente (request mal formada).
- **401**: no autenticado o token inválido/expirado.
- **404**: recurso no existe (e.g., `branch_id` desconocido).
- **422**: validación de Pydantic falló (e.g., `month` con formato inválido o mes inexistente).
- **500**: error inesperado (handler global serializa con `detail="Error interno"`, log completo).

---

## §10. Cliente API en frontend

`web/src/api/client.ts` se genera con `openapi-typescript` desde `openapi.json` que produce M4. Script en `scripts/generate_openapi_client.sh`:

```bash
#!/usr/bin/env bash
set -e
cd web
npx openapi-typescript ../api/openapi.json --output src/api/schema.d.ts
```

`web/src/api/client.ts` envuelve fetch con tipado:

```ts
import type { paths } from "./schema";
// Cliente generado: cada endpoint tiene un wrapper tipado.
```

Mientras M4 no haya exportado `openapi.json`, M5 trabaja contra MSW handlers (`web/src/mocks/handlers.ts`) que devuelven respuestas estáticas según los DTOs de §4.

---

## §11. Convenciones de nombres

- **Archivos**: kebab-case en disco (`upload-page.tsx` ❌ — preferir CamelCase para componentes React, kebab-case para scripts y docs).
- **Componentes React**: PascalCase (`NPSCard.tsx`).
- **Variables Python**: snake_case.
- **Variables TS**: camelCase.
- **Constantes**: SCREAMING_SNAKE_CASE.
- **Funciones**: verbo en infinitivo (`compute_nps`, `load_file`, `classify`).
- **Tests**: `test_<modulo>.py` (Python), `<componente>.test.ts` (TS).
- **Branches git** (si se reactiva git): `feat/m1-datos`, `feat/m2a-anotador`, etc.

---

## §12. Quién manda en caso de discrepancia

- **Schema SQLite vs ORM**: el SQL de §2 manda. Si el ORM no concuerda, se ajusta el ORM.
- **DTOs de analytics vs respuestas de API**: los DTOs de `analytics.schemas` mandan. La API los re-exporta sin cambios.
- **OpenAPI vs cliente TS**: el OpenAPI manda. M5 regenera el cliente.
- **Decisiones técnicas vs implementación**: `00_decisiones_tecnicas.md` manda. Si una decisión es incorrecta, se anota en `contracts_issues.md` pero **no se cambia en código sin pasar por el usuario**.

---

## §13. Tests requeridos por convención

Cada paquete entrega tests verdes localmente como parte de su DoD. Se ejecutan con:

```bash
# Python
cd <paquete> && pytest

# Frontend
cd web && npm test
```

No hay CI en hackathon. Una sesión puede romper tests de otro paquete temporalmente si su contrato cambia, pero debe arreglarlos antes de marcar su módulo como DoD.

---

## §14. Definitions of Done compartidas

Todo módulo entrega:

1. Código del paquete completo según su carpeta declarada en §1.
2. `pyproject.toml` (Python) o `package.json` (TS).
3. Tests propios verdes.
4. README de paquete con: cómo instalar, cómo correr, qué expone.
5. CLI ejecutable si su módulo lo declara como entregable (M2a, M2b, M6).
6. Sin secrets en archivos commiteables.
