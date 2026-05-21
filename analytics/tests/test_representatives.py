"""Tests para analytics.representatives."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from analytics.representatives import pick_representatives, _percentile
from core.models_db import Verbalization


def test_representatives_branch_match(session: Session) -> None:
    out = pick_representatives(session, "B-0001", n_per_topic=2)
    assert out
    for rep in out:
        verb = session.execute(
            select(Verbalization).where(Verbalization.record_id == rep.record_id)
        ).scalar_one()
        assert verb.branch_id == "B-0001"


def test_representatives_length_in_p25_p75(session: Session) -> None:
    lengths_all = [
        len(v.verbatim_clean or "")
        for v in session.execute(
            select(Verbalization).where(Verbalization.branch_id == "B-0001")
        )
        .scalars()
        .all()
    ]
    p25 = _percentile(lengths_all, 25.0)
    p75 = _percentile(lengths_all, 75.0)
    out = pick_representatives(session, "B-0001", n_per_topic=2)
    for rep in out:
        assert p25 <= len(rep.verbatim) <= p75


def test_representatives_unknown_branch(session: Session) -> None:
    assert pick_representatives(session, "B-DOESNT-EXIST", n_per_topic=2) == []
