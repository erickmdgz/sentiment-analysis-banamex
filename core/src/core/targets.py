"""Generación de objetivos NPS anuales sintéticos.

Implementa la regla declarada en ``00_decisiones_tecnicas.md §15``:

- Por cada sucursal: ``target = NPS_historico + N(μ=3, σ=4)`` clipeado a ``[50, 85]``.
- Si la sucursal no tiene NPS histórico (o tiene <10 respuestas y no hay NPS
  nacional), se usa ``target = 65 + N(μ=0, σ=5)`` clipeado igual.
- La aleatoriedad usa un seed derivado del propio ``branch_id`` para que el
  resultado sea determinístico entre corridas (test §13.10).

``generate_all`` es idempotente: si ya hay filas en ``branch_targets`` y
``force=False``, no hace nada. ``regenerate_for_branches`` borra y regenera
puntualmente las sucursales indicadas.
"""

from __future__ import annotations

import hashlib

import numpy as np
from sqlalchemy import text

from .db import get_engine, init_schema
from .schemas import BranchTargetRow


def _deterministic_seed(branch_id: str) -> int:
    seed_source = branch_id.removeprefix("A-") if branch_id.startswith("A-") else branch_id
    try:
        return int(seed_source)
    except ValueError:
        return int.from_bytes(hashlib.sha256(branch_id.encode("utf-8")).digest()[:4], "big")


def generate_target_for_branch(branch_id: str, nps_historico: float | None) -> int:
    """Aplica la fórmula §15 a una sucursal individual. Pura, sin DB."""
    rng = np.random.default_rng(seed=_deterministic_seed(branch_id))
    if nps_historico is None:
        base = 65 + rng.normal(0, 5)
    else:
        perturbacion = rng.normal(loc=3, scale=4)
        base = float(nps_historico) + perturbacion
    return int(np.clip(base, 50, 85))


def compute_national_nps() -> float | None:
    """NPS nacional (% promotores − % detractores). ``None`` si no hay filas."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                    SUM(CASE WHEN nps_group = 'Promotor' THEN 1 ELSE 0 END),
                    SUM(CASE WHEN nps_group = 'Detractor' THEN 1 ELSE 0 END),
                    COUNT(*)
                FROM verbalizations
                """
            )
        ).one()
    promoters, detractors, total = row
    if not total:
        return None
    return (float(promoters or 0) - float(detractors or 0)) / float(total) * 100.0


def compute_branch_nps(branch_id: str) -> float | None:
    """NPS histórico de una sucursal (% promotores − % detractores).

    Si la sucursal tiene menos de 10 respuestas, devuelve el NPS nacional
    como base. Si tampoco hay datos nacionales, devuelve ``None``.
    """
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                    SUM(CASE WHEN nps_group = 'Promotor' THEN 1 ELSE 0 END),
                    SUM(CASE WHEN nps_group = 'Detractor' THEN 1 ELSE 0 END),
                    COUNT(*)
                FROM verbalizations WHERE branch_id = :bid
                """
            ),
            {"bid": branch_id},
        ).one()
    promoters, detractors, total = row
    if not total or int(total) < 10:
        return compute_national_nps()
    return (float(promoters or 0) - float(detractors or 0)) / float(total) * 100.0


def _list_branches() -> list[str]:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT branch_id FROM branches ORDER BY branch_id")).all()
    return [r[0] for r in rows]


def _upsert_targets(targets: list[BranchTargetRow]) -> None:
    if not targets:
        return
    engine = get_engine()
    payload = [
        {"bid": t.branch_id, "target": t.nps_target_annual, "syn": 1 if t.is_synthetic else 0}
        for t in targets
    ]
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT OR REPLACE INTO branch_targets
                    (branch_id, nps_target_annual, is_synthetic)
                VALUES (:bid, :target, :syn)
                """
            ),
            payload,
        )


def generate_all(seed: int = 42, force: bool = False) -> list[BranchTargetRow]:
    """Genera targets para todas las sucursales.

    Idempotente: si ya hay filas en ``branch_targets`` y ``force=False``,
    devuelve la lista actual sin regenerar. Con ``force=True`` borra y
    regenera para todas las sucursales.

    ``seed`` se acepta por compatibilidad de firma; el seed efectivo de cada
    sucursal sale de su ``branch_id`` (ver ``_deterministic_seed``).
    """
    init_schema()
    engine = get_engine()
    with engine.begin() as conn:
        existing = int(conn.execute(text("SELECT COUNT(*) FROM branch_targets")).scalar() or 0)
        if existing > 0 and not force:
            rows = conn.execute(
                text("SELECT branch_id, nps_target_annual, is_synthetic FROM branch_targets")
            ).all()
            return [
                BranchTargetRow(
                    branch_id=r[0], nps_target_annual=int(r[1]), is_synthetic=bool(r[2])
                )
                for r in rows
            ]
        if force:
            conn.execute(text("DELETE FROM branch_targets"))

    branches = _list_branches()
    targets = [
        BranchTargetRow(
            branch_id=bid,
            nps_target_annual=generate_target_for_branch(bid, compute_branch_nps(bid)),
            is_synthetic=True,
        )
        for bid in branches
    ]
    _upsert_targets(targets)
    return targets


def regenerate_for_branches(branch_ids: list[str]) -> list[BranchTargetRow]:
    """Borra y regenera los targets sólo para las sucursales indicadas."""
    init_schema()
    if not branch_ids:
        return []
    engine = get_engine()
    placeholders = ",".join(f":b{i}" for i in range(len(branch_ids)))
    params = {f"b{i}": bid for i, bid in enumerate(branch_ids)}
    with engine.begin() as conn:
        conn.execute(
            text(f"DELETE FROM branch_targets WHERE branch_id IN ({placeholders})"), params
        )
    targets = [
        BranchTargetRow(
            branch_id=bid,
            nps_target_annual=generate_target_for_branch(bid, compute_branch_nps(bid)),
            is_synthetic=True,
        )
        for bid in branch_ids
    ]
    _upsert_targets(targets)
    return targets


__all__ = [
    "compute_branch_nps",
    "compute_national_nps",
    "generate_all",
    "generate_target_for_branch",
    "regenerate_for_branches",
]
