"""SQLAlchemy ORM mapeado al schema autoritativo de schema.sql.

Convención: nombre Python CamelCase singular, tabla SQL snake_case plural.
Fuente: docs/plan_implementacion/01_contratos_compartidos.md §3.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey
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
    other_bank_names: Mapped[str | None]
    channels_mentioned: Mapped[str | None]
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
