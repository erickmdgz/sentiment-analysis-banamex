"""DTOs request/response específicos de la capa HTTP.

Re-exporta los DTOs de analytics sin cambios (los DTOs de analytics MANDAN
en caso de discrepancia, según §12 de contratos).

Fuente: docs/plan_implementacion/01_contratos_compartidos.md §8 (endpoints).
"""

from __future__ import annotations

from pydantic import BaseModel

from analytics.schemas import (  # noqa: F401  (re-export deliberado)
    BranchYTD,
    CauseBucket,
    CoverageSummary,
    CriticalBranch,
    ImpactByCategory,
    Insight,
    MonthlyComparison,
    MonthlyTrend,
    NationalYTD,
    NPSDistribution,
    NPSSummary,
    PersonnelMention,
    Ranking,
    Rankings,
    RepresentativeComment,
    StrengthBucket,
    SuggestedAction,
    ValidationSummary,
    WordFrequency,
)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    token: str
    expires_at: str  # ISO 8601


class UserInfo(BaseModel):
    username: str


class HealthResponse(BaseModel):
    status: str
    db_path: str
    classifier_loaded: bool


class ErrorResponse(BaseModel):
    detail: str
    code: str
    hint: str | None = None
