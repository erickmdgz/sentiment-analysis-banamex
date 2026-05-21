"""Tendencia mensual de NPS y comparación entre meses (M3).

Referencias: 05_M3 §Tendencia mensual, §compare_months.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from core.models_db import Verbalization
from sqlalchemy import distinct, select
from sqlalchemy.orm import Session

from .nps import compute_distribution, compute_nps
from .ranking import branches_improved, branches_worsened
from .schemas import (
    CauseBucket,
    CriticalBranch,
    MonthlyComparison,
    MonthlyPoint,
    MonthlyTrend,
    NPSDistribution,
    StrengthBucket,
    SuggestedAction,
)

# Umbral mínimo de respuestas para no marcar un punto como parcial.
PARTIAL_THRESHOLD = 50


def _format_month(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def _filter_scope(scope: Literal["national"] | str) -> str | None:
    """Devuelve `branch_id` filtrado, o None para scope nacional."""
    if scope == "national":
        return None
    return scope


def available_months(session: Session) -> list[str]:
    """Lista cronológica de meses 'YYYY-MM' presentes en `verbalizations`."""
    rows = session.execute(
        select(distinct(Verbalization.response_year), Verbalization.response_month)
        .order_by(Verbalization.response_year, Verbalization.response_month)
    ).all()
    seen: set[tuple[int, int]] = set()
    for r in rows:
        seen.add((int(r[0]), int(r[1])))
    return [_format_month(y, m) for y, m in sorted(seen)]


def monthly_trend(
    session: Session, scope: Literal["national"] | str
) -> MonthlyTrend:
    """Serie cronológica ascendente de NPS por mes en el scope solicitado.

    Cada punto incluye `responses`. La capa de presentación decide si oculta
    puntos con `responses < PARTIAL_THRESHOLD`.
    """
    branch_filter = _filter_scope(scope)
    stmt = select(Verbalization)
    if branch_filter is not None:
        stmt = stmt.where(Verbalization.branch_id == branch_filter)
    rows = session.execute(stmt).scalars().all()
    buckets: dict[tuple[int, int], list[Verbalization]] = {}
    for r in rows:
        key = (int(r.response_year), int(r.response_month))
        buckets.setdefault(key, []).append(r)
    points = [
        MonthlyPoint(
            month=_format_month(y, m),
            nps=compute_nps(items),
            responses=len(items),
        )
        for (y, m), items in sorted(buckets.items())
    ]
    return MonthlyTrend(points=points)


def _month_filter(
    stmt_records: Iterable[Verbalization], year: int, month: int
) -> list[Verbalization]:
    return [
        r for r in stmt_records
        if int(r.response_year) == year and int(r.response_month) == month
    ]


def _parse_month_str(month: str) -> tuple[int, int]:
    year, m = month.split("-")
    return int(year), int(m)


def _scope_records(
    session: Session, scope: Literal["national"] | str
) -> list[Verbalization]:
    branch_filter = _filter_scope(scope)
    stmt = select(Verbalization)
    if branch_filter is not None:
        stmt = stmt.where(Verbalization.branch_id == branch_filter)
    return list(session.execute(stmt).scalars().all())


def compare_months(
    session: Session,
    month_a: str,
    month_b: str,
    scope: Literal["national"] | str = "national",
) -> MonthlyComparison:
    """Comparación entre dos meses en el scope solicitado.

    Lanza `ValueError` si alguno de los meses no existe en
    `available_months(session)`.
    """
    months = available_months(session)
    missing = [m for m in (month_a, month_b) if m not in months]
    if missing:
        raise ValueError(
            f"Meses no disponibles: {missing}. Meses válidos: {months}"
        )

    # Para evitar import circular con topics.py, lo importamos aquí.
    from .topics import top_causes, top_strengths  # noqa: WPS433

    records = _scope_records(session, scope)
    ya, ma = _parse_month_str(month_a)
    yb, mb = _parse_month_str(month_b)
    rows_a = _month_filter(records, ya, ma)
    rows_b = _month_filter(records, yb, mb)
    nps_a = compute_nps(rows_a)
    nps_b = compute_nps(rows_b)
    dist_a: NPSDistribution = compute_distribution(rows_a)
    dist_b: NPSDistribution = compute_distribution(rows_b)

    causes_a = top_causes(session, scope, group="Detractor", month=month_a)
    causes_b = top_causes(session, scope, group="Detractor", month=month_b)
    strengths_a = top_strengths(session, scope, month=month_a)
    strengths_b = top_strengths(session, scope, month=month_b)

    def _delta_names(
        list_a: list[CauseBucket] | list[StrengthBucket],
        list_b: list[CauseBucket] | list[StrengthBucket],
    ) -> tuple[list[str], list[str]]:
        map_a = {b.bucket: b.count for b in list_a}
        map_b = {b.bucket: b.count for b in list_b}
        buckets = set(map_a) | set(map_b)
        deltas = [(b, map_b.get(b, 0) - map_a.get(b, 0)) for b in buckets]
        inc = [b for b, d in sorted(deltas, key=lambda x: -x[1]) if d > 0]
        dec = [b for b, d in sorted(deltas, key=lambda x: x[1]) if d < 0]
        return inc, dec

    causes_inc, causes_dec = _delta_names(causes_a, causes_b)
    strengths_inc, strengths_dec = _delta_names(strengths_a, strengths_b)

    improved: list[CriticalBranch] = branches_improved(session, month_a, month_b)
    worsened: list[CriticalBranch] = branches_worsened(session, month_a, month_b)

    actions: list[SuggestedAction] = []

    return MonthlyComparison(
        month_a=month_a,
        month_b=month_b,
        nps_a=nps_a,
        nps_b=nps_b,
        nps_change=nps_b - nps_a,
        distribution_a=dist_a,
        distribution_b=dist_b,
        causes_a=causes_a,
        causes_b=causes_b,
        causes_increased=causes_inc,
        causes_decreased=causes_dec,
        strengths_a=strengths_a,
        strengths_b=strengths_b,
        strengths_increased=strengths_inc,
        strengths_decreased=strengths_dec,
        branches_improved=improved,
        branches_worsened=worsened,
        actions=actions,
    )
