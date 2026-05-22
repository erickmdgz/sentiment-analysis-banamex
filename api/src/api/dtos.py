"""DTOs adicionales del API que no viven en `models_api.py` (stub congelado).

`models_api.py` re-exporta DTOs de `analytics.schemas` y declara los DTOs
estables de auth/health. Los DTOs específicos de upload se mantienen aquí
para no tocar el stub.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from .models_api import ValidationSummary


class UploadResponse(BaseModel):
    file_id: int
    validation_summary: ValidationSummary
    already_processed: bool


class UploadStatusResponse(BaseModel):
    file_id: int
    status: Literal["parsing", "classifying", "done", "error"]
    progress: float
    error: str | None = None


class BranchSearchResult(BaseModel):
    branch_id: str
    response_count: int
    has_target: bool


class PassiveAnalysisResponse(BaseModel):
    near_promoter: list  # list[CauseBucket]
    near_detractor: list  # list[CauseBucket]


class FileRecord(BaseModel):
    id: int
    filename: str
    sha256: str
    rows_inserted: int
    uploaded_at: str


class AnnotationRunRecord(BaseModel):
    id: int
    sample_size: int
    model: str
    started_at: str
    finished_at: str | None
    runtime_seconds: float | None
    status: str


class ClassifierRunRecord(BaseModel):
    id: int
    model_path: str
    trained_on_run_id: int | None
    trained_at: str
    n_samples: int
    n_labels: int
    f1_micro: float | None
    f1_macro: float | None
    hamming_loss: float | None


class RunsResponse(BaseModel):
    annotation_runs: list[AnnotationRunRecord]
    classifier_runs: list[ClassifierRunRecord]


__all__ = [
    "AnnotationRunRecord",
    "BranchSearchResult",
    "ClassifierRunRecord",
    "FileRecord",
    "PassiveAnalysisResponse",
    "RunsResponse",
    "UploadResponse",
    "UploadStatusResponse",
]
