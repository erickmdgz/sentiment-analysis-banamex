"""Router nacional (11 endpoints).

Cada handler es un wrapper delgado sobre `analytics.*` con scope `"national"`.
La lógica de NPS, agregaciones y rankings vive íntegra en M3.
"""

from __future__ import annotations

import re
from typing import Literal

from analytics.actions import suggested_actions_national
from analytics.impact import impact_by_category
from analytics.insights import national_insights
from analytics.nps import national_ytd_summary
from analytics.ranking import critical_branches, rankings_bundle
from analytics.topics import passive_analysis, top_causes, top_strengths
from analytics.trends import compare_months, monthly_trend
from core.models_db import BranchTarget, Verbalization
from fastapi import APIRouter, Depends, Query
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..dtos import PassiveAnalysisResponse
from ..models_api import (
    CauseBucket,
    CriticalBranch,
    ImpactByCategory,
    Insight,
    MonthlyComparison,
    MonthlyTrend,
    NationalYTD,
    Rankings,
    StrengthBucket,
    SuggestedAction,
    UserInfo,
)

router = APIRouter(prefix="/national", tags=["national"])

_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


@router.get("/ytd", response_model=NationalYTD)
def national_ytd(
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> NationalYTD:
    """Compone `NationalYTD` combinando todas las agregaciones nacionales (`01 §4`)."""
    nps = national_ytd_summary(session)
    trend = monthly_trend(session, "national")
    causes = top_causes(session, "national", group="Detractor")
    strengths = top_strengths(session, "national")
    crit = critical_branches(session)
    rankings = rankings_bundle(session)
    actions = suggested_actions_national(session)
    impact = impact_by_category(session)
    insights = national_insights(session)
    branches_total = int(
        session.execute(select(func.count(distinct(Verbalization.branch_id)))).scalar_one()
    )
    branches_with_target = int(
        session.execute(select(func.count()).select_from(BranchTarget)).scalar_one()
    )
    return NationalYTD(
        nps=nps,
        trend=trend,
        causes=causes,
        strengths=strengths,
        critical_branches=crit,
        rankings=rankings,
        actions=actions,
        impact=impact,
        insights=insights,
        branches_total=branches_total,
        branches_with_target=branches_with_target,
    )


@router.get("/trend", response_model=MonthlyTrend)
def national_trend(
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> MonthlyTrend:
    return monthly_trend(session, "national")


@router.get("/compare", response_model=MonthlyComparison)
def national_compare(
    month_a: str = Query(..., description="YYYY-MM"),
    month_b: str = Query(..., description="YYYY-MM"),
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> MonthlyComparison:
    _validate_month_format(month_a, "month_a")
    _validate_month_format(month_b, "month_b")
    return compare_months(session, month_a, month_b, scope="national")


@router.get("/critical-branches", response_model=list[CriticalBranch])
def national_critical_branches(
    limit: int = Query(10, ge=1, le=100),
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> list[CriticalBranch]:
    return critical_branches(session, limit=limit)


@router.get("/rankings", response_model=Rankings)
def national_rankings(
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> Rankings:
    return rankings_bundle(session)


@router.get("/causes", response_model=list[CauseBucket])
def national_causes(
    group: Literal["Promotor", "Pasivo", "Detractor"] = Query("Detractor"),
    limit: int = Query(10, ge=1, le=50),
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> list[CauseBucket]:
    return top_causes(session, "national", group=group, limit=limit)


@router.get("/strengths", response_model=list[StrengthBucket])
def national_strengths(
    group: Literal["Promotor", "Pasivo", "Detractor"] = Query("Promotor"),
    limit: int = Query(10, ge=1, le=50),
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> list[StrengthBucket]:
    # `top_strengths` ya filtra Promotor internamente; ignoramos `group` salvo
    # para mantener simetría con `/causes` y exponerlo como parámetro del API.
    _ = group
    return top_strengths(session, "national", limit=limit)


@router.get("/actions", response_model=list[SuggestedAction])
def national_actions(
    limit: int = Query(10, ge=1, le=50),
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> list[SuggestedAction]:
    return suggested_actions_national(session)[:limit]


@router.get("/impact", response_model=list[ImpactByCategory])
def national_impact(
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> list[ImpactByCategory]:
    return impact_by_category(session)


@router.get("/insights", response_model=list[Insight])
def national_insights_endpoint(
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> list[Insight]:
    return national_insights(session)


@router.get("/passive-analysis", response_model=PassiveAnalysisResponse)
def national_passive_analysis(
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> PassiveAnalysisResponse:
    data = passive_analysis(session, "national")
    return PassiveAnalysisResponse(
        near_promoter=data.get("near_promoter", []),
        near_detractor=data.get("near_detractor", []),
    )


def _validate_month_format(value: str, field: str) -> None:
    if not _MONTH_RE.match(value):
        raise ValueError(
            f"Parámetro {field}={value!r} no tiene formato YYYY-MM."
        )
