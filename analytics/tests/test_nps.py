"""Tests para analytics.nps."""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from analytics.nps import (
    branch_ytd_summary,
    compute_distribution,
    compute_nps,
    national_ytd_summary,
)
from core.models_db import Branch, BranchTarget, File, Verbalization

EPSILON = 1e-6


def _make_verb(
    record_id: str,
    branch_id: str,
    group: str,
    rate: int,
    year: int = 2026,
    month: int = 1,
) -> Verbalization:
    return Verbalization(
        record_id=record_id,
        file_id=1,
        response_date=f"{year:04d}-{month:02d}-01",
        response_year=year,
        response_month=month,
        nps_group=group,
        nps_rate=rate,
        verbatim="",
        verbatim_clean="",
        branch_id=branch_id,
        has_verbatim=0,
    )


def test_compute_nps_basic() -> None:
    records = (
        [_make_verb(f"P{i}", "B-0001", "Promotor", 9) for i in range(50)]
        + [_make_verb(f"S{i}", "B-0001", "Pasivo", 7) for i in range(30)]
        + [_make_verb(f"D{i}", "B-0001", "Detractor", 5) for i in range(20)]
    )
    assert abs(compute_nps(records) - 30.0) < EPSILON


def test_compute_nps_empty_returns_zero() -> None:
    assert compute_nps([]) == 0.0


def test_compute_distribution_sums_to_100() -> None:
    records = (
        [_make_verb(f"P{i}", "B-0001", "Promotor", 9) for i in range(7)]
        + [_make_verb(f"S{i}", "B-0001", "Pasivo", 7) for i in range(2)]
        + [_make_verb(f"D{i}", "B-0001", "Detractor", 5) for i in range(11)]
    )
    dist = compute_distribution(records)
    assert (
        abs(dist.promoters_pct + dist.passives_pct + dist.detractors_pct - 100.0)
        < EPSILON
    )
    assert dist.promoters_count == 7
    assert dist.passives_count == 2
    assert dist.detractors_count == 11


def test_national_ytd_summary_structure(session: Session) -> None:
    summary = national_ytd_summary(session)
    assert summary.total_responses > 0
    assert summary.nps_target is not None
    assert summary.gap is not None
    assert summary.distribution.promoters_count >= 0
    assert summary.distribution.passives_count >= 0
    assert summary.distribution.detractors_count >= 0


def test_branch_ytd_summary_with_and_without_target(
    session_factory: sessionmaker[Session],
) -> None:
    sess = session_factory()
    sess.add(File(
        id=1, filename="f", sha256="x", rows_total=0, rows_inserted=0,
        rows_duplicated=0, rows_invalid=0, uploaded_at="2026-01-01",
    ))
    sess.add(Branch(branch_id="B-WITH", first_seen_at="2026-01-01"))
    sess.add(Branch(branch_id="B-NO", first_seen_at="2026-01-01"))
    sess.add(BranchTarget(
        branch_id="B-WITH", nps_target_annual=40,
        generated_at="2026-01-01", is_synthetic=1,
    ))
    for i in range(5):
        sess.add(_make_verb(f"W{i}", "B-WITH", "Promotor", 9))
    for i in range(5):
        sess.add(_make_verb(f"N{i}", "B-NO", "Promotor", 9))
    sess.commit()

    with_summary = branch_ytd_summary(sess, "B-WITH")
    assert with_summary.nps_target == 40.0
    assert with_summary.gap is not None

    no_summary = branch_ytd_summary(sess, "B-NO")
    assert no_summary.nps_target is None
    assert no_summary.gap is None
