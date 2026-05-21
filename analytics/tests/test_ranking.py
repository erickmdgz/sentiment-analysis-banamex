"""Tests para analytics.ranking."""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from analytics.ranking import (
    branches_by_most_detractors,
    branches_by_worst_gap,
    branches_by_worst_nps,
    critical_branches,
    rankings_bundle,
)
from core.models_db import Branch, BranchTarget, File, Verbalization


def _seed(sess: Session) -> None:
    sess.add(File(
        id=1, filename="f", sha256="x", rows_total=0, rows_inserted=0,
        rows_duplicated=0, rows_invalid=0, uploaded_at="2026-01-01",
    ))


def _add_branch(sess: Session, bid: str, target: int | None) -> None:
    sess.add(Branch(branch_id=bid, first_seen_at="2026-01-01"))
    if target is not None:
        sess.add(BranchTarget(
            branch_id=bid, nps_target_annual=target,
            generated_at="2026-01-01", is_synthetic=1,
        ))


def _add_records(
    sess: Session,
    bid: str,
    n_promotor: int,
    n_pasivo: int,
    n_detractor: int,
    year: int = 2026,
    month: int = 1,
    base: int = 0,
) -> None:
    counter = base
    for _ in range(n_promotor):
        counter += 1
        sess.add(Verbalization(
            record_id=f"{bid}-P{counter}",
            file_id=1,
            response_date=f"{year:04d}-{month:02d}-01",
            response_year=year,
            response_month=month,
            nps_group="Promotor",
            nps_rate=9,
            verbatim="",
            verbatim_clean="",
            branch_id=bid,
            has_verbatim=0,
        ))
    for _ in range(n_pasivo):
        counter += 1
        sess.add(Verbalization(
            record_id=f"{bid}-S{counter}",
            file_id=1,
            response_date=f"{year:04d}-{month:02d}-01",
            response_year=year,
            response_month=month,
            nps_group="Pasivo",
            nps_rate=7,
            verbatim="",
            verbatim_clean="",
            branch_id=bid,
            has_verbatim=0,
        ))
    for _ in range(n_detractor):
        counter += 1
        sess.add(Verbalization(
            record_id=f"{bid}-D{counter}",
            file_id=1,
            response_date=f"{year:04d}-{month:02d}-01",
            response_year=year,
            response_month=month,
            nps_group="Detractor",
            nps_rate=2,
            verbatim="",
            verbatim_clean="",
            branch_id=bid,
            has_verbatim=0,
        ))


def test_critical_branches_condition1_only(
    session_factory: sessionmaker[Session],
) -> None:
    """Sucursal A: NPS < target − 5, sin >=30% detractores, sin deterioro MoM."""
    sess = session_factory()
    _seed(sess)
    _add_branch(sess, "B-COND1", 50)
    # 60 promotores, 20 pasivos, 20 detractores → 80%P, 20%D, NPS=40, target=50 → gap=-10
    # gap dispara cond(1) (40 < 50-5). Detractores 20% < 30%, no dispara (3).
    _add_records(sess, "B-COND1", 60, 20, 20)
    # Otra sucursal para que el percentil 10 no atrape a B-COND1 sola
    _add_branch(sess, "B-OK", 30)
    _add_records(sess, "B-OK", 90, 5, 5)
    sess.commit()

    result = critical_branches(sess, limit=10)
    by_id = {c.branch_id: c for c in result}
    assert "B-COND1" in by_id
    assert "NPS < objetivo − 5" in by_id["B-COND1"].triggered_conditions
    assert "≥30% detractores" not in by_id["B-COND1"].triggered_conditions


def test_critical_branches_condition3_only(
    session_factory: sessionmaker[Session],
) -> None:
    """Sucursal B: detractores ≥ 30% pero NPS ≥ target − 5."""
    sess = session_factory()
    _seed(sess)
    _add_branch(sess, "B-COND3", 0)  # target 0, fácil de cumplir
    # 35%P, 30%Pa, 35%D → NPS = 0, gap = 0 (no cond 1/2)
    _add_records(sess, "B-COND3", 7, 6, 7)
    _add_branch(sess, "B-FILL", 0)
    _add_records(sess, "B-FILL", 20, 0, 0)
    sess.commit()

    result = critical_branches(sess, limit=10)
    by_id = {c.branch_id: c for c in result}
    assert "B-COND3" in by_id
    assert "≥30% detractores" in by_id["B-COND3"].triggered_conditions
    assert "NPS < objetivo − 5" not in by_id["B-COND3"].triggered_conditions


def test_critical_branches_no_target_only_3_and_4(
    session_factory: sessionmaker[Session],
) -> None:
    """Una sucursal sin target nunca debe disparar (1) ni (2)."""
    sess = session_factory()
    _seed(sess)
    _add_branch(sess, "B-NOTGT", None)
    _add_records(sess, "B-NOTGT", 2, 1, 7)  # 70% detractores
    _add_branch(sess, "B-FILL", 0)
    _add_records(sess, "B-FILL", 20, 0, 0)
    sess.commit()

    result = critical_branches(sess, limit=10)
    by_id = {c.branch_id: c for c in result}
    assert "B-NOTGT" in by_id
    triggers = by_id["B-NOTGT"].triggered_conditions
    assert "NPS < objetivo − 5" not in triggers
    assert "brecha en percentil 10 peor" not in triggers
    assert "≥30% detractores" in triggers
    assert by_id["B-NOTGT"].nps_target is None
    assert by_id["B-NOTGT"].gap is None


def test_rankings_bundle_no_duplicates_within_list(session: Session) -> None:
    bundle = rankings_bundle(session)
    for ranking in (
        bundle.worst_nps,
        bundle.worst_gap,
        bundle.most_detractors,
        bundle.worsened,
        bundle.improved,
    ):
        seen: set[str] = set()
        for item in ranking.items:
            assert item["branch_id"] not in seen
            seen.add(str(item["branch_id"]))


def test_rankings_bundle_lists_present(session: Session) -> None:
    bundle = rankings_bundle(session)
    assert bundle.worst_nps.items
    assert bundle.most_detractors.items
    # Pueden estar vacíos en datasets degenerados; aquí esperamos contenido.
    assert isinstance(bundle.worst_gap.items, list)
    assert isinstance(bundle.worsened.items, list)
    assert isinstance(bundle.improved.items, list)


def test_branches_by_worst_gap_excludes_no_target(
    session_factory: sessionmaker[Session],
) -> None:
    sess = session_factory()
    _seed(sess)
    _add_branch(sess, "B-TGT", 60)
    _add_records(sess, "B-TGT", 10, 5, 5)
    _add_branch(sess, "B-NO", None)
    _add_records(sess, "B-NO", 10, 5, 5)
    sess.commit()
    out = branches_by_worst_gap(sess)
    assert all(c.branch_id != "B-NO" for c in out)


def test_branches_by_most_detractors_order(session: Session) -> None:
    out = branches_by_most_detractors(session)
    detractors = [c.detractors_pct for c in out]
    assert detractors == sorted(detractors, reverse=True)


def test_branches_by_worst_nps_order(session: Session) -> None:
    out = branches_by_worst_nps(session)
    values = [c.nps_actual for c in out]
    assert values == sorted(values)
