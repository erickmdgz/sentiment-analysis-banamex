"""DTOs Pydantic compartidos por todos los módulos del proyecto.

Fuente: docs/plan_implementacion/01_contratos_compartidos.md §4 (DTOs base).
Estos tipos son consumidos por engine, analytics, api y los scripts.
"""

from __future__ import annotations

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
