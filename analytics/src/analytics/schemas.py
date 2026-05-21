"""DTOs Pydantic de la capa de analytics. La API los re-exporta sin cambios.

Fuente: docs/plan_implementacion/01_contratos_compartidos.md §4 (DTOs de analytics).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

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
    bucket: str
    count: int
    pct_of_group: float
    sample_l2: list[str]


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
    triggered_conditions: list[str]


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
    impact_points: float


class Insight(BaseModel):
    text: str
    category: Literal[
        "nps", "brecha", "fortaleza", "fricción", "personal", "comparación", "cobertura"
    ]


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
    polarity: Literal["pos", "neg"]
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
