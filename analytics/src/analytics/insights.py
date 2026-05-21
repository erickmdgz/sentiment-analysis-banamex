"""Insights narrativos nacionales y por sucursal (M3).

Cada plantilla es una función privada que devuelve `Insight | None`. Las
funciones públicas componen y filtran los `None`. Cuando faltan datos
mínimos, se inserta un fallback `Datos insuficientes para ...`.

Referencias: 05_M3 §Insights narrativos.
"""

from __future__ import annotations

from typing import Literal

from sqlalchemy.orm import Session

from .nps import branch_ytd_summary, national_ytd_summary
from .ranking import critical_branches
from .schemas import Insight
from .topics import top_causes, top_strengths

InsightCategory = Literal[
    "nps", "brecha", "fortaleza", "fricción", "personal", "comparación", "cobertura"
]


def _gap_insight(session: Session) -> Insight | None:
    summary = national_ytd_summary(session)
    if summary.gap is None:
        return None
    if summary.gap >= 0:
        return Insight(
            text=(
                f"El NPS nacional YTD ({summary.nps_actual:.1f}) está al nivel "
                f"o por encima del objetivo ({summary.nps_target:.0f})."
            ),
            category="brecha",
        )
    return Insight(
        text=(
            f"El NPS nacional YTD está {abs(summary.gap):.0f} puntos por debajo "
            "del objetivo anual."
        ),
        category="brecha",
    )


def _top_causes_insight(session: Session) -> Insight | None:
    causes = top_causes(session, "national", group="Detractor", limit=3)
    if not causes:
        return None
    names = [c.bucket for c in causes]
    return Insight(
        text=f"Las principales causas de detracción son {', '.join(names)}.",
        category="fricción",
    )


def _top_strengths_insight(session: Session) -> Insight | None:
    strengths = top_strengths(session, "national", limit=3)
    if not strengths:
        return None
    names = [s.bucket for s in strengths]
    return Insight(
        text=f"Las principales fortalezas son {', '.join(names)}.",
        category="fortaleza",
    )


def _critical_count_insight(session: Session) -> Insight | None:
    critical = critical_branches(session, limit=100)
    if not critical:
        return None
    return Insight(
        text=(
            f"Hay {len(critical)} sucursales críticas por brecha negativa "
            "contra objetivo."
        ),
        category="brecha",
    )


def _nps_level_insight(session: Session) -> Insight | None:
    summary = national_ytd_summary(session)
    if summary.total_responses == 0:
        return None
    return Insight(
        text=f"El NPS nacional YTD es {summary.nps_actual:.1f}.",
        category="nps",
    )


def national_insights(session: Session) -> list[Insight]:
    summary = national_ytd_summary(session)
    candidates: list[Insight | None] = [
        _nps_level_insight(session),
        _gap_insight(session),
        _top_causes_insight(session),
        _top_strengths_insight(session),
        _critical_count_insight(session),
    ]
    out = [c for c in candidates if c is not None]
    if summary.total_responses < 50:
        out.append(
            Insight(
                text=(
                    "Datos insuficientes para conclusiones robustas a nivel nacional "
                    f"(solo {summary.total_responses} respuestas en el período YTD)."
                ),
                category="cobertura",
            )
        )
    return out


def _branch_gap_insight(session: Session, branch_id: str) -> Insight | None:
    summary = branch_ytd_summary(session, branch_id)
    if summary.total_responses == 0:
        return None
    if summary.nps_target is None:
        return Insight(
            text="Esta sucursal no tiene objetivo anual disponible en la fuente interna.",
            category="cobertura",
        )
    if summary.gap is not None and summary.gap < 0:
        return Insight(
            text=(
                f"La sucursal {branch_id} tiene un NPS YTD de "
                f"{summary.nps_actual:.0f} contra objetivo de {summary.nps_target:.0f}."
            ),
            category="brecha",
        )
    return Insight(
        text=(
            f"La sucursal {branch_id} cumple su objetivo (NPS YTD "
            f"{summary.nps_actual:.0f}, objetivo {summary.nps_target:.0f})."
        ),
        category="brecha",
    )


def _branch_top_cause_insight(session: Session, branch_id: str) -> Insight | None:
    causes = top_causes(session, branch_id, group="Detractor", limit=1)
    if not causes:
        return None
    return Insight(
        text=f"El principal motivo de detracción es {causes[0].bucket}.",
        category="fricción",
    )


def branch_insights(session: Session, branch_id: str) -> list[Insight]:
    summary = branch_ytd_summary(session, branch_id)
    candidates: list[Insight | None] = [
        _branch_gap_insight(session, branch_id),
        _branch_top_cause_insight(session, branch_id),
    ]
    out = [c for c in candidates if c is not None]
    if summary.total_responses < 20:
        out.append(
            Insight(
                text=(
                    "Datos insuficientes para conclusiones robustas en esta sucursal "
                    f"(solo {summary.total_responses} respuestas en el período YTD)."
                ),
                category="cobertura",
            )
        )
    return out
