"""Impacto counterfactual de cada categoría sobre el NPS (M3).

Por cada `CAUSE_BUCKET` calcula cuántos puntos subiría el NPS si los
detractores asociados a ese bucket pasaran a Pasivo (conservador: no se
promueve a Promotor). Referencias: 00 §16, 05_M3 §impact_by_category.
"""

from __future__ import annotations

from typing import Literal

from core.models_db import Classification, Verbalization
from engine.ui_buckets import CAUSE_BUCKETS
from sqlalchemy import and_, distinct, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import ColumnElement

from .schemas import ImpactByCategory


def _scope_predicates(
    scope: Literal["national"] | str,
) -> list[ColumnElement[bool]]:
    if scope == "national":
        return []
    return [Verbalization.branch_id == scope]


def _scope_records(
    session: Session, scope: Literal["national"] | str
) -> list[Verbalization]:
    stmt = select(Verbalization)
    preds = _scope_predicates(scope)
    if preds:
        stmt = stmt.where(and_(*preds))
    return list(session.execute(stmt).scalars().all())


def _compute_nps(records: list[Verbalization]) -> float:
    if not records:
        return 0.0
    p = sum(1 for r in records if r.nps_group == "Promotor")
    d = sum(1 for r in records if r.nps_group == "Detractor")
    return (p - d) / len(records) * 100.0


def _detractor_ids_for_bucket(
    session: Session, bucket: str, scope: Literal["national"] | str
) -> set[str]:
    stmt = (
        select(distinct(Classification.record_id))
        .join(Verbalization, Classification.record_id == Verbalization.record_id)
        .where(Classification.ui_bucket == bucket)
        .where(Verbalization.nps_group == "Detractor")
    )
    preds = _scope_predicates(scope)
    if preds:
        stmt = stmt.where(and_(*preds))
    return {str(r) for r in session.execute(stmt).scalars().all()}


def _recompute_nps_treating_as_passive(
    records: list[Verbalization], affected: set[str]
) -> float:
    if not records:
        return 0.0
    p = 0
    d = 0
    for r in records:
        rid = str(r.record_id)
        group = r.nps_group
        if rid in affected and group == "Detractor":
            continue  # ahora es Pasivo
        if group == "Promotor":
            p += 1
        elif group == "Detractor":
            d += 1
    return (p - d) / len(records) * 100.0


def impact_by_category(
    session: Session, scope: Literal["national"] | str = "national"
) -> list[ImpactByCategory]:
    records = _scope_records(session, scope)
    if not records:
        return []
    nps_actual = _compute_nps(records)
    out: list[ImpactByCategory] = []
    for bucket in CAUSE_BUCKETS:
        affected = _detractor_ids_for_bucket(session, bucket, scope)
        nps_sim = _recompute_nps_treating_as_passive(records, affected)
        out.append(
            ImpactByCategory(bucket=bucket, impact_points=nps_sim - nps_actual)
        )
    out.sort(key=lambda x: x.impact_points, reverse=True)
    return out
