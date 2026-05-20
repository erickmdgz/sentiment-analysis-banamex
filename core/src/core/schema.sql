-- ===========================================================
-- Schema SQLite autoritativo — sentiment-analysis-banamex
-- Fuente de verdad: docs/plan_implementacion/01_contratos_compartidos.md §2
-- Sin migraciones: si el schema cambia, se borra banamex.db y se regenera.
-- ===========================================================

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
    ui_bucket TEXT NOT NULL,                     -- ver §6 de contratos
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
