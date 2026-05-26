"""Tendencia mensual de NPS y comparación entre meses (M3).

Referencias: 05_M3 §Tendencia mensual, §compare_months.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from core.models_db import Verbalization
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from .nps import _nps_from_counts, compute_distribution, compute_nps
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

    Agregación en SQL (en vez de materializar 473k rows en Python) — bajó
    el endpoint de ~2.5s a sub-segundo sobre el dataset real.
    """
    branch_filter = _filter_scope(scope)
    stmt = select(
        Verbalization.response_year,
        Verbalization.response_month,
        Verbalization.nps_group,
        func.count(),
    ).group_by(
        Verbalization.response_year,
        Verbalization.response_month,
        Verbalization.nps_group,
    )
    if branch_filter is not None:
        stmt = stmt.where(Verbalization.branch_id == branch_filter)
    by_month: dict[tuple[int, int], dict[str, int]] = {}
    for y, m, g, c in session.execute(stmt).all():
        by_month.setdefault((int(y), int(m)), {})[str(g)] = int(c)
    points = []
    for (y, m), counts in sorted(by_month.items()):
        nps, total, _ = _nps_from_counts(counts)
        points.append(
            MonthlyPoint(month=_format_month(y, m), nps=nps, responses=total)
        )
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

    branch_filter = _filter_scope(scope)
    ya, ma = _parse_month_str(month_a)
    yb, mb = _parse_month_str(month_b)

    def _counts_for(year: int, month: int) -> dict[str, int]:
        # Agregación SQL en vez de cargar 473k rows + filtrar Python (antes
        # tardaba ~24s para el scope nacional; ahora sub-segundo).
        stmt = (
            select(Verbalization.nps_group, func.count())
            .where(
                Verbalization.response_year == year,
                Verbalization.response_month == month,
            )
            .group_by(Verbalization.nps_group)
        )
        if branch_filter is not None:
            stmt = stmt.where(Verbalization.branch_id == branch_filter)
        return {str(g): int(c) for g, c in session.execute(stmt).all()}

    nps_a, _, dist_a = _nps_from_counts(_counts_for(ya, ma))
    nps_b, _, dist_b = _nps_from_counts(_counts_for(yb, mb))

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
