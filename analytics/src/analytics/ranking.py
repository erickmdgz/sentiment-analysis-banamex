"""Rankings de sucursales y detección de sucursales críticas.

Referencias: 05_M3 §Sucursales críticas, §Rankings; 00 §14.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from core.models_db import BranchTarget, Verbalization
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from .nps import _nps_from_counts, _ytd_filter_year, branch_ytd_summary
from .schemas import CriticalBranch, Ranking, Rankings

CONDITION_LABELS = {
    "nps_below_target_5": "NPS < objetivo − 5",
    "gap_in_worst_decile": "brecha en percentil 10 peor",
    "detractors_high": "≥30% detractores",
    "mom_drop_5": "deterioro mes-a-mes ≥ 5",
}


@dataclass
class _BranchSnapshot:
    branch_id: str
    nps_actual: float
    nps_target: int | None
    gap: float | None
    detractors_pct: float


def _branch_snapshots(session: Session) -> list[_BranchSnapshot]:
    """Snapshot YTD por sucursal con responses > 0.

    Antes: 1 query por sucursal × 1298 sucursales = 2596+ queries y materializaba
    ~473k ORM objects, tardaba 60-90s sobre el dataset real. Ahora: 2 queries
    agregadas (counts por (branch_id, nps_group) + targets), agrupación en Python.
    """
    year = _ytd_filter_year(session)
    if year is None:
        return []
    grouped = session.execute(
        select(Verbalization.branch_id, Verbalization.nps_group, func.count())
        .where(Verbalization.response_year == year)
        .group_by(Verbalization.branch_id, Verbalization.nps_group)
    ).all()
    targets: dict[str, int] = dict(
        session.execute(
            select(BranchTarget.branch_id, BranchTarget.nps_target_annual)
        ).all()
    )
    by_branch: dict[str, dict[str, int]] = {}
    for bid, group, cnt in grouped:
        by_branch.setdefault(str(bid), {})[str(group)] = int(cnt)
    snapshots: list[_BranchSnapshot] = []
    for bid, counts in by_branch.items():
        actual, total, distribution = _nps_from_counts(counts)
        if total == 0:
            continue
        target_val = targets.get(bid)
        target_int: int | None = int(target_val) if target_val is not None else None
        gap: float | None = (
            actual - float(target_val) if target_val is not None else None
        )
        snapshots.append(
            _BranchSnapshot(
                branch_id=bid,
                nps_actual=actual,
                nps_target=target_int,
                gap=gap,
                detractors_pct=distribution.detractors_pct,
            )
        )
    return snapshots


def _last_two_months_nps(
    session: Session, branch_id: str
) -> tuple[float, float] | None:
    """Devuelve (nps_previo, nps_ultimo) sobre el año YTD si hay ≥ 2 meses.

    Antes: 1 query para meses + 2 queries SELECT * que materializaban filas.
    Ahora: 1 query agregada por (month, nps_group) y agrupación en Python.
    """
    year = _ytd_filter_year(session)
    if year is None:
        return None
    grouped = session.execute(
        select(
            Verbalization.response_month,
            Verbalization.nps_group,
            func.count(),
        )
        .where(
            Verbalization.response_year == year,
            Verbalization.branch_id == branch_id,
        )
        .group_by(Verbalization.response_month, Verbalization.nps_group)
    ).all()
    by_month: dict[int, dict[str, int]] = {}
    for month, group, cnt in grouped:
        by_month.setdefault(int(month), {})[str(group)] = int(cnt)
    months_desc = sorted(by_month.keys(), reverse=True)
    if len(months_desc) < 2:
        return None
    last, prev = months_desc[0], months_desc[1]

    def _nps_for(month: int) -> float:
        c = by_month.get(month, {})
        p = int(c.get("Promotor", 0))
        d = int(c.get("Detractor", 0))
        total = p + int(c.get("Pasivo", 0)) + d
        return (p - d) / total * 100.0 if total > 0 else 0.0

    return _nps_for(prev), _nps_for(last)


def _percentile_threshold(values: Sequence[float], pct: float) -> float | None:
    """Calcula el percentil pct (0-100) sin numpy (interpolación lineal)."""
    if not values:
        return None
    sorted_vals = sorted(values)
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    rank = (pct / 100.0) * (len(sorted_vals) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = rank - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def critical_branches(session: Session, limit: int = 10) -> list[CriticalBranch]:
    """Sucursales críticas según las 4 condiciones de `00 §14`."""
    snapshots = _branch_snapshots(session)
    if not snapshots:
        return []

    # Percentil 10 peor sobre las brechas (gaps) no nulas.
    gaps_with_target = [s.gap for s in snapshots if s.gap is not None]
    worst_decile_gap = _percentile_threshold(gaps_with_target, 10.0)

    # Pre-cargar todos los conteos mensuales en 1 query agregada (en vez de
    # llamar _last_two_months_nps por sucursal — eran 1298 queries × snapshots).
    year = _ytd_filter_year(session)
    mom_data: dict[str, dict[int, dict[str, int]]] = {}
    if year is not None:
        for bid, month, group, cnt in session.execute(
            select(
                Verbalization.branch_id,
                Verbalization.response_month,
                Verbalization.nps_group,
                func.count(),
            )
            .where(Verbalization.response_year == year)
            .group_by(
                Verbalization.branch_id,
                Verbalization.response_month,
                Verbalization.nps_group,
            )
        ).all():
            mom_data.setdefault(str(bid), {}).setdefault(int(month), {})[
                str(group)
            ] = int(cnt)

    def _mom_drop(branch_id: str) -> float | None:
        by_month = mom_data.get(branch_id, {})
        months_desc = sorted(by_month.keys(), reverse=True)
        if len(months_desc) < 2:
            return None

        def _nps(m: int) -> float:
            c = by_month[m]
            p = int(c.get("Promotor", 0))
            d = int(c.get("Detractor", 0))
            total = p + int(c.get("Pasivo", 0)) + d
            return (p - d) / total * 100.0 if total > 0 else 0.0

        return _nps(months_desc[1]) - _nps(months_desc[0])

    items: list[CriticalBranch] = []
    for s in snapshots:
        conds: list[str] = []
        # (1) NPS por debajo de target − 5
        if s.nps_target is not None and s.nps_actual < (s.nps_target - 5):
            conds.append(CONDITION_LABELS["nps_below_target_5"])
        # (2) Brecha en percentil 10 peor (sólo si hay target)
        if (
            s.gap is not None
            and worst_decile_gap is not None
            and s.gap <= worst_decile_gap
        ):
            conds.append(CONDITION_LABELS["gap_in_worst_decile"])
        # (3) Detractores >= 30% (siempre aplicable)
        if s.detractors_pct >= 30.0:
            conds.append(CONDITION_LABELS["detractors_high"])
        # (4) Deterioro MoM >= 5
        drop = _mom_drop(s.branch_id)
        if drop is not None and drop >= 5.0:
            conds.append(CONDITION_LABELS["mom_drop_5"])

        if conds:
            items.append(
                CriticalBranch(
                    branch_id=s.branch_id,
                    nps_actual=s.nps_actual,
                    nps_target=s.nps_target,
                    gap=s.gap,
                    detractors_pct=s.detractors_pct,
                    triggered_conditions=conds,
                )
            )

    # Orden: (a) número de condiciones desc, (b) gap asc cuando aplique,
    # (c) detractors_pct desc.
    items.sort(
        key=lambda x: (
            -len(x.triggered_conditions),
            x.gap if x.gap is not None else 0.0,
            -x.detractors_pct,
        )
    )
    return items[:limit]


def _to_critical(snapshot: _BranchSnapshot, condition: str) -> CriticalBranch:
    return CriticalBranch(
        branch_id=snapshot.branch_id,
        nps_actual=snapshot.nps_actual,
        nps_target=snapshot.nps_target,
        gap=snapshot.gap,
        detractors_pct=snapshot.detractors_pct,
        triggered_conditions=[condition],
    )


def branches_by_worst_nps(session: Session, limit: int = 20) -> list[CriticalBranch]:
    snapshots = _branch_snapshots(session)
    snapshots.sort(key=lambda s: s.nps_actual)
    return [_to_critical(s, "peor NPS") for s in snapshots[:limit]]


def branches_by_worst_gap(session: Session, limit: int = 20) -> list[CriticalBranch]:
    snapshots = [s for s in _branch_snapshots(session) if s.gap is not None]
    snapshots.sort(key=lambda s: s.gap if s.gap is not None else 0.0)
    return [_to_critical(s, "peor brecha contra objetivo") for s in snapshots[:limit]]


def branches_by_most_detractors(
    session: Session, limit: int = 20
) -> list[CriticalBranch]:
    snapshots = _branch_snapshots(session)
    snapshots.sort(key=lambda s: s.detractors_pct, reverse=True)
    return [_to_critical(s, "más detractores") for s in snapshots[:limit]]


def _branch_nps_for_month(
    session: Session, branch_id: str, year: int, month: int
) -> float | None:
    rows = session.execute(
        select(Verbalization).where(
            Verbalization.response_year == year,
            Verbalization.response_month == month,
            Verbalization.branch_id == branch_id,
        )
    ).scalars().all()
    if not rows:
        return None
    p = sum(1 for r in rows if r.nps_group == "Promotor")
    d = sum(1 for r in rows if r.nps_group == "Detractor")
    return (p - d) / len(rows) * 100.0


def _parse_month(month_str: str) -> tuple[int, int]:
    year_part, month_part = month_str.split("-")
    return int(year_part), int(month_part)


def _branch_delta_between_months(
    session: Session, month_a: str, month_b: str
) -> list[tuple[str, float]]:
    """Lista de (branch_id, delta_nps) entre month_b y month_a (b − a).

    Antes: 1 query por sucursal × 1298 sucursales × 2 meses = 2596 queries
    materializando rows en Python (~19s para /national/compare).
    Ahora: 2 queries agregadas (1 por mes) sobre (branch_id, nps_group).
    """
    ya, ma = _parse_month(month_a)
    yb, mb = _parse_month(month_b)

    def _branch_counts_for(year: int, month: int) -> dict[str, dict[str, int]]:
        result: dict[str, dict[str, int]] = {}
        for bid, group, cnt in session.execute(
            select(
                Verbalization.branch_id,
                Verbalization.nps_group,
                func.count(),
            )
            .where(
                Verbalization.response_year == year,
                Verbalization.response_month == month,
            )
            .group_by(Verbalization.branch_id, Verbalization.nps_group)
        ).all():
            result.setdefault(str(bid), {})[str(group)] = int(cnt)
        return result

    def _nps_of(counts: dict[str, int]) -> float | None:
        p = int(counts.get("Promotor", 0))
        d = int(counts.get("Detractor", 0))
        total = p + int(counts.get("Pasivo", 0)) + d
        return (p - d) / total * 100.0 if total > 0 else None

    counts_a = _branch_counts_for(ya, ma)
    counts_b = _branch_counts_for(yb, mb)
    out: list[tuple[str, float]] = []
    for bid in set(counts_a) | set(counts_b):
        nps_a = _nps_of(counts_a.get(bid, {}))
        nps_b = _nps_of(counts_b.get(bid, {}))
        if nps_a is None or nps_b is None:
            continue
        out.append((bid, nps_b - nps_a))
    return out


def _snapshot_for_branch(
    session: Session, branch_id: str
) -> _BranchSnapshot | None:
    summary = branch_ytd_summary(session, branch_id)
    if summary.total_responses == 0:
        return None
    target_int = int(summary.nps_target) if summary.nps_target is not None else None
    return _BranchSnapshot(
        branch_id=branch_id,
        nps_actual=summary.nps_actual,
        nps_target=target_int,
        gap=summary.gap,
        detractors_pct=summary.distribution.detractors_pct,
    )


def branches_worsened(
    session: Session, month_a: str, month_b: str, limit: int = 20
) -> list[CriticalBranch]:
    deltas = _branch_delta_between_months(session, month_a, month_b)
    deltas.sort(key=lambda x: x[1])  # más negativos primero
    out: list[CriticalBranch] = []
    for bid, delta in deltas:
        if delta >= 0:
            continue
        snap = _snapshot_for_branch(session, bid)
        if snap is None:
            continue
        cb = _to_critical(snap, f"deterioro {delta:+.1f} pts entre {month_a} y {month_b}")
        out.append(cb)
        if len(out) >= limit:
            break
    return out


def branches_improved(
    session: Session, month_a: str, month_b: str, limit: int = 20
) -> list[CriticalBranch]:
    deltas = _branch_delta_between_months(session, month_a, month_b)
    deltas.sort(key=lambda x: x[1], reverse=True)
    out: list[CriticalBranch] = []
    for bid, delta in deltas:
        if delta <= 0:
            continue
        snap = _snapshot_for_branch(session, bid)
        if snap is None:
            continue
        cb = _to_critical(snap, f"mejora {delta:+.1f} pts entre {month_a} y {month_b}")
        out.append(cb)
        if len(out) >= limit:
            break
    return out


def _last_two_months_national(session: Session) -> tuple[str, str] | None:
    year = _ytd_filter_year(session)
    if year is None:
        return None
    months = session.execute(
        select(distinct(Verbalization.response_month))
        .where(Verbalization.response_year == year)
        .order_by(Verbalization.response_month.desc())
    ).scalars().all()
    if len(months) < 2:
        return None
    last = f"{year:04d}-{int(months[0]):02d}"
    prev = f"{year:04d}-{int(months[1]):02d}"
    return prev, last


def rankings_bundle(session: Session) -> Rankings:
    """Empaqueta los 5 rankings definidos en 05_M3 §Rankings."""
    worst_nps = branches_by_worst_nps(session)
    worst_gap = branches_by_worst_gap(session)
    most_detractors = branches_by_most_detractors(session)

    mom = _last_two_months_national(session)
    worsened: list[CriticalBranch]
    improved: list[CriticalBranch]
    if mom is None:
        worsened = []
        improved = []
    else:
        prev_m, last_m = mom
        worsened = branches_worsened(session, prev_m, last_m)
        improved = branches_improved(session, prev_m, last_m)

    def _to_ranking(name: str, label: str, items: list[CriticalBranch]) -> Ranking:
        return Ranking(
            name=name,
            items=[
                {
                    "branch_id": cb.branch_id,
                    "value": (
                        cb.gap if name == "worst_gap" and cb.gap is not None
                        else cb.detractors_pct if name == "most_detractors"
                        else cb.nps_actual
                    ),
                    "label": label,
                }
                for cb in items
            ],
        )

    return Rankings(
        worst_nps=_to_ranking("worst_nps", "peor NPS YTD", worst_nps),
        worst_gap=_to_ranking("worst_gap", "peor brecha contra objetivo", worst_gap),
        most_detractors=_to_ranking(
            "most_detractors", "mayor % de detractores", most_detractors
        ),
        worsened=Ranking(
            name="worsened",
            items=[
                {"branch_id": cb.branch_id, "value": cb.nps_actual, "label": cb.triggered_conditions[0]}
                for cb in worsened
            ],
        ),
        improved=Ranking(
            name="improved",
            items=[
                {"branch_id": cb.branch_id, "value": cb.nps_actual, "label": cb.triggered_conditions[0]}
                for cb in improved
            ],
        ),
    )
