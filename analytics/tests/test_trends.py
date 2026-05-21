"""Tests para analytics.trends."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from analytics.trends import available_months, compare_months, monthly_trend


def test_monthly_trend_chronological(session: Session) -> None:
    trend = monthly_trend(session, "national")
    months = [p.month for p in trend.points]
    assert months == sorted(months)


def test_monthly_trend_includes_responses(session: Session) -> None:
    trend = monthly_trend(session, "national")
    assert all(p.responses > 0 for p in trend.points)


def test_monthly_trend_branch_scope(session: Session) -> None:
    trend = monthly_trend(session, "B-0020")
    # B-0020 fue diseñada con muy pocas respuestas (~15)
    total = sum(p.responses for p in trend.points)
    assert total < 50


def test_compare_months_missing_raises(session: Session) -> None:
    with pytest.raises(ValueError) as ei:
        compare_months(session, "1999-01", "2026-01")
    msg = str(ei.value)
    assert "1999-01" in msg
    assert "Meses válidos" in msg or "v" in msg  # mensaje en español


def test_compare_months_happy_path(session: Session) -> None:
    months = available_months(session)
    assert "2026-01" in months
    assert "2026-02" in months
    comparison = compare_months(session, "2026-01", "2026-02", "national")
    assert comparison.month_a == "2026-01"
    assert comparison.month_b == "2026-02"
    assert isinstance(comparison.nps_change, float)


def test_available_months_format(session: Session) -> None:
    months = available_months(session)
    for m in months:
        assert len(m) == 7
        assert m[4] == "-"
