"""Agregaciones de tópicos: causas, fortalezas, distribución por bucket y pasivos.

Referencias: 05_M3 §Top causes, §Top strengths, §passive_analysis.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from core.models_db import Classification, Verbalization
from engine.ui_buckets import CAUSE_BUCKETS, STRENGTH_BUCKETS
from sqlalchemy import and_, distinct, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import ColumnElement

from .schemas import CauseBucket, StrengthBucket


def _scope_predicates(
    scope: Literal["national"] | str,
    month: str | None = None,
) -> list[ColumnElement[bool]]:
    """Lista de predicados sobre `verbalizations` derivada del scope."""
    year = None
    if month is None:
        # Sin mes explícito, no aplicamos filtro YTD para mantener simetría con
        # otros usos (la API agrega el filtro YTD vía national_ytd_summary).
        pass
    predicates: list[ColumnElement[bool]] = []
    if month is not None:
        y, m = month.split("-")
        year = int(y)
        predicates.append(Verbalization.response_year == year)
        predicates.append(Verbalization.response_month == int(m))
    if scope != "national":
        predicates.append(Verbalization.branch_id == scope)
    return predicates


def _bucket_distinct_record_count(
    session: Session,
    bucket: str,
    nps_group: str | None,
    extra_predicates: Sequence[ColumnElement[bool]],
) -> int:
    stmt = (
        select(func.count(distinct(Classification.record_id)))
        .join(Verbalization, Classification.record_id == Verbalization.record_id)
        .where(Classification.ui_bucket == bucket)
    )
    if nps_group is not None:
        stmt = stmt.where(Verbalization.nps_group == nps_group)
    if extra_predicates:
        stmt = stmt.where(and_(*extra_predicates))
    return int(session.execute(stmt).scalar() or 0)


def _group_total(
    session: Session,
    nps_group: str | None,
    extra_predicates: Sequence[ColumnElement[bool]],
) -> int:
    stmt = select(func.count()).select_from(Verbalization)
    if nps_group is not None:
        stmt = stmt.where(Verbalization.nps_group == nps_group)
    if extra_predicates:
        stmt = stmt.where(and_(*extra_predicates))
    return int(session.execute(stmt).scalar() or 0)


def _sample_l2_for_bucket(
    session: Session,
    bucket: str,
    nps_group: str | None,
    extra_predicates: Sequence[ColumnElement[bool]],
    top_k: int = 3,
) -> list[str]:
    stmt = (
        select(
            Classification.l2_name,
            func.count(distinct(Classification.record_id)).label("c"),
        )
        .join(Verbalization, Classification.record_id == Verbalization.record_id)
        .where(Classification.ui_bucket == bucket)
        .group_by(Classification.l2_name)
        .order_by(func.count(distinct(Classification.record_id)).desc())
        .limit(top_k)
    )
    if nps_group is not None:
        stmt = stmt.where(Verbalization.nps_group == nps_group)
    if extra_predicates:
        stmt = stmt.where(and_(*extra_predicates))
    rows = session.execute(stmt).all()
    return [str(r[0]) for r in rows]


def top_causes(
    session: Session,
    scope: Literal["national"] | str = "national",
    group: str = "Detractor",
    limit: int = 10,
    month: str | None = None,
) -> list[CauseBucket]:
    """Top causes por `ui_bucket` para el grupo NPS solicitado.

    Multiclase: cada comentario cuenta UNA vez por bucket (DISTINCT record_id).
    Excluye `Otros`.
    """
    predicates = _scope_predicates(scope, month)
    total_group = _group_total(session, group, predicates)
    results: list[CauseBucket] = []
    for bucket in CAUSE_BUCKETS:
        count = _bucket_distinct_record_count(session, bucket, group, predicates)
        if count == 0:
            continue
        sample_l2 = _sample_l2_for_bucket(session, bucket, group, predicates)
        pct = count / total_group if total_group > 0 else 0.0
        results.append(
            CauseBucket(
                bucket=bucket,
                count=count,
                pct_of_group=pct,
                sample_l2=sample_l2,
            )
        )
    results.sort(key=lambda b: b.count, reverse=True)
    return results[:limit]


def top_strengths(
    session: Session,
    scope: Literal["national"] | str = "national",
    limit: int = 10,
    month: str | None = None,
) -> list[StrengthBucket]:
    """Top strengths por `ui_bucket` filtrando sólo Promotores."""
    predicates = _scope_predicates(scope, month)
    total_group = _group_total(session, "Promotor", predicates)
    results: list[StrengthBucket] = []
    for bucket in STRENGTH_BUCKETS:
        count = _bucket_distinct_record_count(session, bucket, "Promotor", predicates)
        if count == 0:
            continue
        sample_l2 = _sample_l2_for_bucket(
            session, bucket, "Promotor", predicates
        )
        pct = count / total_group if total_group > 0 else 0.0
        results.append(
            StrengthBucket(
                bucket=bucket,
                count=count,
                pct_of_group=pct,
                sample_l2=sample_l2,
            )
        )
    results.sort(key=lambda b: b.count, reverse=True)
    return results[:limit]


def bucket_distribution(
    session: Session, scope: Literal["national"] | str = "national"
) -> dict[str, int]:
    """Conteo DISTINCT record_id por bucket en el scope (sin filtro de grupo)."""
    predicates = _scope_predicates(scope, month=None)
    stmt = (
        select(
            Classification.ui_bucket,
            func.count(distinct(Classification.record_id)),
        )
        .join(Verbalization, Classification.record_id == Verbalization.record_id)
        .group_by(Classification.ui_bucket)
    )
    if predicates:
        stmt = stmt.where(and_(*predicates))
    return {str(r[0]): int(r[1]) for r in session.execute(stmt).all()}


def passive_analysis(
    session: Session, scope: Literal["national"] | str = "national"
) -> dict[str, list[CauseBucket]]:
    """Segmenta pasivos por `nps_rate` (7 vs 8) y reporta top causes."""
    predicates_base = _scope_predicates(scope, month=None)

    def _segment(rate: int) -> list[CauseBucket]:
        preds = list(predicates_base) + [Verbalization.nps_rate == rate]
        total = _group_total(session, "Pasivo", preds)
        # Para pasivos, reportamos sobre TODOS los buckets (no sólo causas),
        # según 05_M3 §passive_analysis.
        all_buckets = session.execute(
            select(distinct(Classification.ui_bucket))
        ).scalars().all()
        out: list[CauseBucket] = []
        for bucket in all_buckets:
            count = _bucket_distinct_record_count(session, bucket, "Pasivo", preds)
            if count == 0:
                continue
            sample_l2 = _sample_l2_for_bucket(session, bucket, "Pasivo", preds)
            pct = count / total if total > 0 else 0.0
            out.append(
                CauseBucket(
                    bucket=bucket,
                    count=count,
                    pct_of_group=pct,
                    sample_l2=sample_l2,
                )
            )
        out.sort(key=lambda b: b.count, reverse=True)
        return out

    return {
        "near_detractor": _segment(7),
        "near_promoter": _segment(8),
    }


__all__ = [
    "bucket_distribution",
    "passive_analysis",
    "top_causes",
    "top_strengths",
]
