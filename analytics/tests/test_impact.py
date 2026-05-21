"""Tests para analytics.impact."""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from analytics.impact import impact_by_category
from core.models_db import Branch, Classification, File, Verbalization


def test_impact_positive_when_detractors_concentrate(
    session_factory: sessionmaker[Session],
) -> None:
    sess = session_factory()
    sess.add(File(
        id=1, filename="f", sha256="x", rows_total=0, rows_inserted=0,
        rows_duplicated=0, rows_invalid=0, uploaded_at="2026-01-01",
    ))
    sess.add(Branch(branch_id="B-IMP", first_seen_at="2026-01-01"))
    # 20 promotores y 20 detractores. Todos los detractores asignados a
    # "Tiempos y espera". Mover detractores a pasivos sube NPS.
    for i in range(20):
        sess.add(Verbalization(
            record_id=f"P{i}", file_id=1, response_date="2026-01-01",
            response_year=2026, response_month=1, nps_group="Promotor",
            nps_rate=9, verbatim="", verbatim_clean="", branch_id="B-IMP",
            has_verbatim=0,
        ))
    for i in range(20):
        rid = f"D{i}"
        sess.add(Verbalization(
            record_id=rid, file_id=1, response_date="2026-01-01",
            response_year=2026, response_month=1, nps_group="Detractor",
            nps_rate=2, verbatim="", verbatim_clean="", branch_id="B-IMP",
            has_verbatim=0,
        ))
        sess.add(Classification(
            record_id=rid, l1_code="2", l1_name="Tiempos y operación",
            l2_code="2.1", l2_name="Tiempo de espera",
            l3_code=None, l3_name=None, confidence=0.9, source="classifier",
            polarity="neg", ui_bucket="Tiempos y espera",
            created_at="2026-01-01",
        ))
    sess.commit()

    impact = impact_by_category(sess, "national")
    tiempos = next(i for i in impact if i.bucket == "Tiempos y espera")
    assert tiempos.impact_points > 0


def test_impact_sorted_descending(session: Session) -> None:
    impact = impact_by_category(session, "national")
    values = [i.impact_points for i in impact]
    assert values == sorted(values, reverse=True)
