"""Acciones sugeridas a partir de reglas declarativas (M3).

Cada regla es una función pura que recibe un `_Context` con datos ya calculados
y devuelve `SuggestedAction | None`. La función pública compone, filtra y ordena.

Referencias: 05_M3 §Suggested actions.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from core.models_db import BranchTarget, MetadataExtraction, Verbalization
from sqlalchemy import distinct, select
from sqlalchemy.orm import Session

from .nps import branch_ytd_summary
from .ranking import _branch_snapshots, critical_branches
from .schemas import CauseBucket, CriticalBranch, StrengthBucket, SuggestedAction
from .topics import top_causes, top_strengths

Priority = Literal["alta", "media", "baja"]
_PRIORITY_ORDER: dict[Priority, int] = {"alta": 0, "media": 1, "baja": 2}


@dataclass
class _Context:
    scope: str
    top_causes_detractor: list[CauseBucket]
    top_strengths_promotor: list[StrengthBucket]
    critical: list[CriticalBranch]
    branches_no_target: list[str]
    branches_negative_personnel: list[str] = field(default_factory=list)
    branches_with_wide_gap: list[str] = field(default_factory=list)


def _build_national_context(session: Session) -> _Context:
    causes = top_causes(session, "national", group="Detractor", limit=10)
    strengths = top_strengths(session, "national", limit=10)
    critical = critical_branches(session, limit=100)

    branch_ids = session.execute(
        select(distinct(Verbalization.branch_id))
    ).scalars().all()
    targets = session.execute(
        select(BranchTarget.branch_id)
    ).scalars().all()
    targets_set = {str(t) for t in targets}
    no_target = [str(b) for b in branch_ids if str(b) not in targets_set]

    # Branches con menciones de personal negativas
    rows_personnel = session.execute(
        select(distinct(Verbalization.branch_id))
        .join(
            MetadataExtraction, MetadataExtraction.record_id == Verbalization.record_id
        )
        .where(MetadataExtraction.personnel_named == 1)
        .where(MetadataExtraction.personnel_polarity == "neg")
    ).scalars().all()
    neg_personnel = [str(b) for b in rows_personnel]

    # Branches con gap < -10. Usa _branch_snapshots (1 query agregada)
    # en vez de iterar branch_ytd_summary por sucursal (1298 × 2 queries → 29s).
    snapshots = _branch_snapshots(session)
    wide_gap = [s.branch_id for s in snapshots if s.gap is not None and s.gap < -10]

    return _Context(
        scope="national",
        top_causes_detractor=causes,
        top_strengths_promotor=strengths,
        critical=critical,
        branches_no_target=no_target,
        branches_negative_personnel=neg_personnel,
        branches_with_wide_gap=wide_gap,
    )


def _build_branch_context(session: Session, branch_id: str) -> _Context:
    causes = top_causes(session, branch_id, group="Detractor", limit=10)
    strengths = top_strengths(session, branch_id, limit=10)
    summary = branch_ytd_summary(session, branch_id)

    wide_gap = (
        [branch_id]
        if summary.gap is not None and summary.gap < -10
        else []
    )

    has_target = session.execute(
        select(BranchTarget.branch_id).where(BranchTarget.branch_id == branch_id)
    ).scalar_one_or_none()
    no_target = [] if has_target is not None else [branch_id]

    rows_personnel = session.execute(
        select(distinct(Verbalization.branch_id))
        .join(
            MetadataExtraction, MetadataExtraction.record_id == Verbalization.record_id
        )
        .where(MetadataExtraction.personnel_named == 1)
        .where(MetadataExtraction.personnel_polarity == "neg")
        .where(Verbalization.branch_id == branch_id)
    ).scalars().all()
    neg_personnel = [str(b) for b in rows_personnel]

    return _Context(
        scope=branch_id,
        top_causes_detractor=causes,
        top_strengths_promotor=strengths,
        critical=[],
        branches_no_target=no_target,
        branches_negative_personnel=neg_personnel,
        branches_with_wide_gap=wide_gap,
    )


# --------- Reglas ---------


def _rule_tiempos_y_espera(ctx: _Context) -> SuggestedAction | None:
    if not ctx.top_causes_detractor:
        return None
    if ctx.top_causes_detractor[0].bucket != "Tiempos y espera":
        return None
    return SuggestedAction(
        text="Revisar operación de turnos en sucursales con alta espera.",
        priority="alta",
        related_bucket="Tiempos y espera",
        related_branches=[],
    )


def _rule_many_critical_branches(ctx: _Context) -> SuggestedAction | None:
    if len(ctx.critical) < 10:
        return None
    return SuggestedAction(
        text="Priorizar intervención en sucursales críticas.",
        priority="alta",
        related_bucket=None,
        related_branches=[cb.branch_id for cb in ctx.critical[:10]],
    )


def _rule_negative_personnel(ctx: _Context) -> SuggestedAction | None:
    if not ctx.branches_negative_personnel:
        return None
    return SuggestedAction(
        text="Atender menciones negativas hacia personal.",
        priority="media",
        related_bucket="Atención del personal",
        related_branches=ctx.branches_negative_personnel,
    )


def _rule_canales_digitales(ctx: _Context) -> SuggestedAction | None:
    for cause in ctx.top_causes_detractor:
        if cause.bucket == "Canales digitales" and cause.count >= 5:
            return SuggestedAction(
                text=(
                    "Reforzar capacitación en resolución de problemas de "
                    "app / NetKey."
                ),
                priority="media",
                related_bucket="Canales digitales",
                related_branches=[],
            )
    return None


def _rule_branches_without_target(ctx: _Context) -> SuggestedAction | None:
    if not ctx.branches_no_target:
        return None
    return SuggestedAction(
        text=(
            "Revisar sucursales sin objetivo configurado en la fuente interna."
        ),
        priority="baja",
        related_bucket=None,
        related_branches=ctx.branches_no_target,
    )


def _rule_procesos(ctx: _Context) -> SuggestedAction | None:
    for cause in ctx.top_causes_detractor:
        if cause.bucket == "Procesos y requisitos" and cause.count >= 5:
            return SuggestedAction(
                text="Revisar procesos que generan vueltas innecesarias.",
                priority="media",
                related_bucket="Procesos y requisitos",
                related_branches=[],
            )
    return None


def _rule_wide_gap(ctx: _Context) -> SuggestedAction | None:
    if not ctx.branches_with_wide_gap:
        return None
    return SuggestedAction(
        text="Auditar sucursales con brecha negativa amplia (gap < −10).",
        priority="alta",
        related_bucket=None,
        related_branches=ctx.branches_with_wide_gap,
    )


def _rule_replicate_strengths(ctx: _Context) -> SuggestedAction | None:
    if not ctx.top_strengths_promotor:
        return None
    if ctx.top_strengths_promotor[0].bucket != "Atención del personal":
        return None
    if ctx.top_strengths_promotor[0].pct_of_group < 0.3:
        return None
    return SuggestedAction(
        text="Replicar prácticas de personal con menciones positivas.",
        priority="baja",
        related_bucket="Atención del personal",
        related_branches=[],
    )


def _rule_costos(ctx: _Context) -> SuggestedAction | None:
    for cause in ctx.top_causes_detractor:
        if cause.bucket == "Costos" and cause.count >= 5:
            return SuggestedAction(
                text="Revisar transparencia y comunicación de comisiones.",
                priority="media",
                related_bucket="Costos",
                related_branches=[],
            )
    return None


def _rule_atm(ctx: _Context) -> SuggestedAction | None:
    for cause in ctx.top_causes_detractor:
        if cause.bucket == "Cajeros (ATM)" and cause.count >= 5:
            return SuggestedAction(
                text="Reforzar mantenimiento preventivo de cajeros.",
                priority="media",
                related_bucket="Cajeros (ATM)",
                related_branches=[],
            )
    return None


def _rule_fraude(ctx: _Context) -> SuggestedAction | None:
    for cause in ctx.top_causes_detractor:
        if cause.bucket == "Aclaraciones, quejas y fraude" and cause.count >= 3:
            return SuggestedAction(
                text="Acelerar tiempos de aclaración y resolución de fraudes.",
                priority="alta",
                related_bucket="Aclaraciones, quejas y fraude",
                related_branches=[],
            )
    return None


_RULES: list[Callable[[_Context], SuggestedAction | None]] = [
    _rule_tiempos_y_espera,
    _rule_many_critical_branches,
    _rule_negative_personnel,
    _rule_canales_digitales,
    _rule_branches_without_target,
    _rule_procesos,
    _rule_wide_gap,
    _rule_replicate_strengths,
    _rule_costos,
    _rule_atm,
    _rule_fraude,
]


def _compose(ctx: _Context) -> list[SuggestedAction]:
    out: list[SuggestedAction] = []
    for rule in _RULES:
        action = rule(ctx)
        if action is not None:
            out.append(action)
    out.sort(key=lambda a: _PRIORITY_ORDER[a.priority])
    return out[:10]


def suggested_actions_national(session: Session) -> list[SuggestedAction]:
    return _compose(_build_national_context(session))


def suggested_actions_branch(session: Session, branch_id: str) -> list[SuggestedAction]:
    return _compose(_build_branch_context(session, branch_id))
