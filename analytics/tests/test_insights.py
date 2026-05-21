"""Tests para analytics.insights."""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from analytics.insights import branch_insights, national_insights
from core.models_db import Branch, BranchTarget, File, Verbalization


def test_national_insights_basic_categories(session: Session) -> None:
    insights = national_insights(session)
    categories = {i.category for i in insights}
    assert "nps" in categories
    assert "brecha" in categories
    assert "fricción" in categories or "fortaleza" in categories


def test_branch_insights_no_target_emits_cobertura(
    session_factory: sessionmaker[Session],
) -> None:
    sess = session_factory()
    sess.add(File(
        id=1, filename="f", sha256="x", rows_total=0, rows_inserted=0,
        rows_duplicated=0, rows_invalid=0, uploaded_at="2026-01-01",
    ))
    sess.add(Branch(branch_id="B-NO", first_seen_at="2026-01-01"))
    for i in range(30):
        sess.add(Verbalization(
            record_id=f"R{i}", file_id=1, response_date="2026-01-01",
            response_year=2026, response_month=1, nps_group="Promotor",
            nps_rate=9, verbatim="", verbatim_clean="", branch_id="B-NO",
            has_verbatim=0,
        ))
    sess.commit()

    out = branch_insights(sess, "B-NO")
    assert any(i.category == "cobertura" for i in out)


def test_national_insights_insufficient_data_fallback(
    session_factory: sessionmaker[Session],
) -> None:
    sess = session_factory()
    sess.add(File(
        id=1, filename="f", sha256="x", rows_total=0, rows_inserted=0,
        rows_duplicated=0, rows_invalid=0, uploaded_at="2026-01-01",
    ))
    sess.add(Branch(branch_id="B-MINI", first_seen_at="2026-01-01"))
    sess.add(BranchTarget(
        branch_id="B-MINI", nps_target_annual=50,
        generated_at="2026-01-01", is_synthetic=1,
    ))
    for i in range(3):
        sess.add(Verbalization(
            record_id=f"R{i}", file_id=1, response_date="2026-01-01",
            response_year=2026, response_month=1, nps_group="Promotor",
            nps_rate=9, verbatim="", verbatim_clean="", branch_id="B-MINI",
            has_verbatim=0,
        ))
    sess.commit()

    out = national_insights(sess)
    assert any("Datos insuficientes" in i.text for i in out)
