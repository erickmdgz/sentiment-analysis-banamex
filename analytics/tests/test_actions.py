"""Tests para analytics.actions."""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from analytics.actions import suggested_actions_national
from core.models_db import (
    Branch,
    BranchTarget,
    Classification,
    File,
    Verbalization,
)


def _seed(sess: Session, bucket: str) -> None:
    sess.add(File(
        id=1, filename="f", sha256="x", rows_total=0, rows_inserted=0,
        rows_duplicated=0, rows_invalid=0, uploaded_at="2026-01-01",
    ))
    sess.add(Branch(branch_id="B-T", first_seen_at="2026-01-01"))
    sess.add(BranchTarget(
        branch_id="B-T", nps_target_annual=50,
        generated_at="2026-01-01", is_synthetic=1,
    ))
    # 20 detractores con el bucket dado
    for i in range(20):
        rid = f"D{i}"
        sess.add(Verbalization(
            record_id=rid, file_id=1, response_date="2026-01-01",
            response_year=2026, response_month=1, nps_group="Detractor",
            nps_rate=2, verbatim="", verbatim_clean="", branch_id="B-T",
            has_verbatim=0,
        ))
        sess.add(Classification(
            record_id=rid, l1_code="2", l1_name="L1",
            l2_code="2.1", l2_name="L2",
            l3_code=None, l3_name=None, confidence=0.9, source="classifier",
            polarity="neg", ui_bucket=bucket,
            created_at="2026-01-01",
        ))


def test_action_tiempos_y_espera_fires_when_top_cause(
    session_factory: sessionmaker[Session],
) -> None:
    sess = session_factory()
    _seed(sess, "Tiempos y espera")
    sess.commit()
    actions = suggested_actions_national(sess)
    assert any(a.related_bucket == "Tiempos y espera" for a in actions)


def test_action_tiempos_y_espera_not_when_other_top(
    session_factory: sessionmaker[Session],
) -> None:
    sess = session_factory()
    _seed(sess, "Cajeros (ATM)")
    sess.commit()
    actions = suggested_actions_national(sess)
    # No debe disparar la regla de Tiempos y espera porque no es top cause.
    tiempos = [
        a for a in actions
        if a.related_bucket == "Tiempos y espera"
        and "turnos" in a.text.lower()
    ]
    assert not tiempos


def test_action_priority_order(session: Session) -> None:
    actions = suggested_actions_national(session)
    order = {"alta": 0, "media": 1, "baja": 2}
    priorities = [order[a.priority] for a in actions]
    assert priorities == sorted(priorities)
