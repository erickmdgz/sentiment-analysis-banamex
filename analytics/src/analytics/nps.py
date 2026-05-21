"""Cálculo de NPS y distribuciones (M3).

Funciones puras sobre `Verbalization` (iterables o `Session`). El redondeo y la
presentación quedan fuera de esta capa — `compute_nps` devuelve `float` crudo.

Referencias: 05_M3_analytics.md §Cálculo de NPS, §national_ytd_summary, §branch_ytd_summary.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import cast

from core.models_db import BranchTarget, Verbalization
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .schemas import NPSDistribution, NPSSummary


def compute_nps(records: Iterable[Verbalization]) -> float:
    """NPS = (n_promotores − n_detractores) / n_total × 100.

    Sobre iterable vacío devuelve 0.0 (decisión documentada: el dashboard
    nunca debe romperse por scope sin datos).
    """
    n_promotor = 0
    n_detractor = 0
    n_total = 0
    for r in records:
        n_total += 1
        if r.nps_group == "Promotor":
            n_promotor += 1
        elif r.nps_group == "Detractor":
            n_detractor += 1
    if n_total == 0:
        return 0.0
    return (n_promotor - n_detractor) / n_total * 100.0


def compute_distribution(records: Iterable[Verbalization]) -> NPSDistribution:
    """Cuenta P/Pa/D y devuelve porcentajes (suman 100 ± epsilon)."""
    promotores = 0
    pasivos = 0
    detractores = 0
    for r in records:
        if r.nps_group == "Promotor":
            promotores += 1
        elif r.nps_group == "Pasivo":
            pasivos += 1
        elif r.nps_group == "Detractor":
            detractores += 1
    total = promotores + pasivos + detractores
    if total == 0:
        return NPSDistribution(
            promoters_pct=0.0,
            passives_pct=0.0,
            detractors_pct=0.0,
            promoters_count=0,
            passives_count=0,
            detractors_count=0,
        )
    return NPSDistribution(
        promoters_pct=promotores / total * 100.0,
        passives_pct=pasivos / total * 100.0,
        detractors_pct=detractores / total * 100.0,
        promoters_count=promotores,
        passives_count=pasivos,
        detractors_count=detractores,
    )


def _max_year(session: Session) -> int | None:
    """Año máximo presente en `verbalizations`; None si la tabla está vacía."""
    result = session.execute(select(func.max(Verbalization.response_year))).scalar()
    if result is None:
        return None
    return int(result)


def _ytd_filter_year(session: Session) -> int | None:
    """Año a usar como YTD (regla operativa MVP: el más reciente disponible)."""
    return _max_year(session)


def national_ytd_summary(session: Session) -> NPSSummary:
    """NPS nacional YTD sobre el año más reciente disponible.

    `nps_target` = promedio simple de los `nps_target_annual` declarados en
    `branch_targets` (decisión `00 §15`).
    """
    year = _ytd_filter_year(session)
    if year is None:
        return NPSSummary(
            nps_actual=0.0,
            nps_target=None,
            gap=None,
            total_responses=0,
            distribution=compute_distribution([]),
        )
    rows = session.execute(
        select(Verbalization).where(Verbalization.response_year == year)
    ).scalars().all()
    actual = compute_nps(rows)
    distribution = compute_distribution(rows)

    target_avg = session.execute(
        select(func.avg(BranchTarget.nps_target_annual))
    ).scalar()
    nps_target: float | None = float(target_avg) if target_avg is not None else None
    gap: float | None = actual - nps_target if nps_target is not None else None
    return NPSSummary(
        nps_actual=actual,
        nps_target=nps_target,
        gap=gap,
        total_responses=len(rows),
        distribution=distribution,
    )


def branch_ytd_summary(session: Session, branch_id: str) -> NPSSummary:
    """NPS por sucursal en YTD. `nps_target` viene de `branch_targets`."""
    year = _ytd_filter_year(session)
    if year is None:
        return NPSSummary(
            nps_actual=0.0,
            nps_target=None,
            gap=None,
            total_responses=0,
            distribution=compute_distribution([]),
        )
    rows = session.execute(
        select(Verbalization).where(
            Verbalization.response_year == year,
            Verbalization.branch_id == branch_id,
        )
    ).scalars().all()
    actual = compute_nps(rows)
    distribution = compute_distribution(rows)

    target_val = session.execute(
        select(BranchTarget.nps_target_annual).where(
            BranchTarget.branch_id == branch_id
        )
    ).scalar()
    if target_val is None:
        return NPSSummary(
            nps_actual=actual,
            nps_target=None,
            gap=None,
            total_responses=len(rows),
            distribution=distribution,
        )
    nps_target = float(cast(int, target_val))
    return NPSSummary(
        nps_actual=actual,
        nps_target=nps_target,
        gap=actual - nps_target,
        total_responses=len(rows),
        distribution=distribution,
    )
