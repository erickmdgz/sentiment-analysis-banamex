"""Router de sucursales (11 endpoints).

`/branches?q=...` busca; los demás endpoints son análogos a `/national/*`
pero con `scope=branch_id`. Si el `branch_id` no existe en la tabla
`branches` se devuelve 404 con `code="branch_not_found"` (`06_M4_api.md`).
"""

from __future__ import annotations

import re
from typing import Literal

from analytics.actions import suggested_actions_branch
from analytics.insights import branch_insights
from analytics.nps import branch_ytd_summary
from analytics.personnel import mentions as personnel_mentions
from analytics.representatives import pick_representatives
from analytics.topics import top_causes, top_strengths
from analytics.trends import compare_months, monthly_trend
from analytics.words import top_words
from core.models_db import Branch, BranchTarget, Verbalization
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..dtos import BranchSearchResult
from ..models_api import (
    BranchYTD,
    CauseBucket,
    Insight,
    MonthlyComparison,
    MonthlyTrend,
    PersonnelMention,
    RepresentativeComment,
    StrengthBucket,
    SuggestedAction,
    UserInfo,
    WordFrequency,
)

router = APIRouter(prefix="/branches", tags=["branches"])

_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


@router.get("", response_model=list[BranchSearchResult])
def search_branches(
    q: str | None = Query(None, description="Substring de branch_id"),
    limit: int = Query(50, ge=1, le=500),
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> list[BranchSearchResult]:
    """Lista las sucursales que matchean `q` con `LIKE %q%`."""
    stmt = (
        select(
            Branch.branch_id,
            func.count(Verbalization.record_id).label("responses"),
        )
        .outerjoin(Verbalization, Verbalization.branch_id == Branch.branch_id)
        .group_by(Branch.branch_id)
        .order_by(Branch.branch_id)
    )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(Branch.branch_id.like(like))
    stmt = stmt.limit(limit)

    targets = {
        r[0]
        for r in session.execute(select(BranchTarget.branch_id)).all()
    }

    rows = session.execute(stmt).all()
    return [
        BranchSearchResult(
            branch_id=str(bid),
            response_count=int(rcount),
            has_target=str(bid) in targets,
        )
        for bid, rcount in rows
    ]


@router.get("/{branch_id}/ytd", response_model=BranchYTD)
def branch_ytd(
    branch_id: str,
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> BranchYTD:
    _ensure_branch_exists(session, branch_id)
    nps = branch_ytd_summary(session, branch_id)
    trend = monthly_trend(session, branch_id)
    causes = top_causes(session, branch_id, group="Detractor")
    strengths = top_strengths(session, branch_id)
    actions = suggested_actions_branch(session, branch_id)
    insights = branch_insights(session, branch_id)
    words = top_words(session, branch_id)
    reps = pick_representatives(session, branch_id)
    personnel = personnel_mentions(session, branch_id)
    return BranchYTD(
        branch_id=branch_id,
        nps=nps,
        trend=trend,
        causes=causes,
        strengths=strengths,
        actions=actions,
        insights=insights,
        top_words=words,
        representatives=reps,
        personnel=personnel,
    )


@router.get("/{branch_id}/trend", response_model=MonthlyTrend)
def branch_trend(
    branch_id: str,
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> MonthlyTrend:
    _ensure_branch_exists(session, branch_id)
    return monthly_trend(session, branch_id)


@router.get("/{branch_id}/compare", response_model=MonthlyComparison)
def branch_compare(
    branch_id: str,
    month_a: str = Query(..., description="YYYY-MM"),
    month_b: str = Query(..., description="YYYY-MM"),
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> MonthlyComparison:
    _ensure_branch_exists(session, branch_id)
    _validate_month_format(month_a, "month_a")
    _validate_month_format(month_b, "month_b")
    return compare_months(session, month_a, month_b, scope=branch_id)


@router.get("/{branch_id}/causes", response_model=list[CauseBucket])
def branch_causes(
    branch_id: str,
    group: Literal["Promotor", "Pasivo", "Detractor"] = Query("Detractor"),
    limit: int = Query(10, ge=1, le=50),
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> list[CauseBucket]:
    _ensure_branch_exists(session, branch_id)
    return top_causes(session, branch_id, group=group, limit=limit)


@router.get("/{branch_id}/strengths", response_model=list[StrengthBucket])
def branch_strengths(
    branch_id: str,
    limit: int = Query(10, ge=1, le=50),
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> list[StrengthBucket]:
    _ensure_branch_exists(session, branch_id)
    return top_strengths(session, branch_id, limit=limit)


@router.get("/{branch_id}/words", response_model=list[WordFrequency])
def branch_words(
    branch_id: str,
    group: Literal["Promotor", "Pasivo", "Detractor"] | None = Query(None),
    top_n: int = Query(30, ge=1, le=200),
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> list[WordFrequency]:
    _ensure_branch_exists(session, branch_id)
    return top_words(session, branch_id, group=group, top_n=top_n)


@router.get("/{branch_id}/representatives", response_model=list[RepresentativeComment])
def branch_representatives(
    branch_id: str,
    n_per_topic: int = Query(2, ge=1, le=10),
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> list[RepresentativeComment]:
    _ensure_branch_exists(session, branch_id)
    return pick_representatives(session, branch_id, n_per_topic=n_per_topic)


@router.get("/{branch_id}/personnel", response_model=list[PersonnelMention])
def branch_personnel(
    branch_id: str,
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> list[PersonnelMention]:
    _ensure_branch_exists(session, branch_id)
    return personnel_mentions(session, branch_id)


@router.get("/{branch_id}/actions", response_model=list[SuggestedAction])
def branch_actions(
    branch_id: str,
    limit: int = Query(10, ge=1, le=50),
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> list[SuggestedAction]:
    _ensure_branch_exists(session, branch_id)
    return suggested_actions_branch(session, branch_id)[:limit]


@router.get("/{branch_id}/insights", response_model=list[Insight])
def branch_insights_endpoint(
    branch_id: str,
    session: Session = Depends(get_db),
    user: UserInfo = Depends(get_current_user),
) -> list[Insight]:
    _ensure_branch_exists(session, branch_id)
    return branch_insights(session, branch_id)


def _ensure_branch_exists(session: Session, branch_id: str) -> None:
    found = session.execute(
        select(Branch.branch_id).where(Branch.branch_id == branch_id)
    ).scalar_one_or_none()
    if found is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "detail": f"Sucursal {branch_id!r} no existe.",
                "code": "branch_not_found",
            },
        )


def _validate_month_format(value: str, field: str) -> None:
    if not _MONTH_RE.match(value):
        raise ValueError(
            f"Parámetro {field}={value!r} no tiene formato YYYY-MM."
        )
