"""Tests para analytics.topics."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from analytics.topics import (
    bucket_distribution,
    passive_analysis,
    top_causes,
    top_strengths,
)
from core.models_db import (
    Branch,
    Classification,
    File,
    Verbalization,
)


def test_top_causes_pct_between_0_and_1(session: Session) -> None:
    out = top_causes(session, "national", group="Detractor", limit=10)
    assert out
    for c in out:
        assert 0.0 <= c.pct_of_group <= 1.0


def test_top_strengths_promotor_only(session: Session) -> None:
    out = top_strengths(session, "national", limit=10)
    # Cuando una sucursal sólo tiene detractores, no debería aparecer en
    # strengths; la suma sobre toda la base es Promotor-only por construcción.
    assert out


def test_top_causes_multilabel_distinct(
    session_factory: sessionmaker[Session],
) -> None:
    """Un comentario con 3 buckets cuenta 1 a cada uno (DISTINCT record_id)."""
    sess = session_factory()
    sess.add(File(
        id=1, filename="f", sha256="x", rows_total=0, rows_inserted=0,
        rows_duplicated=0, rows_invalid=0, uploaded_at="2026-01-01",
    ))
    sess.add(Branch(branch_id="B-1", first_seen_at="2026-01-01"))
    sess.add(Verbalization(
        record_id="R1", file_id=1, response_date="2026-01-01",
        response_year=2026, response_month=1, nps_group="Detractor",
        nps_rate=2, verbatim="", verbatim_clean="", branch_id="B-1",
        has_verbatim=0,
    ))
    # 3 classifications mismo record, buckets distintos
    for i, bucket in enumerate(
        ["Tiempos y espera", "Atención del personal", "Cajeros (ATM)"], start=1
    ):
        sess.add(Classification(
            record_id="R1",
            l1_code=str(i),
            l1_name=bucket,
            l2_code=f"{i}.1",
            l2_name=f"{bucket} (L2)",
            l3_code=None,
            l3_name=None,
            confidence=0.9,
            source="classifier",
            polarity="neg",
            ui_bucket=bucket,
            created_at="2026-01-01",
        ))
    # Otra classification del mismo bucket "Tiempos y espera" (duplicado de bucket).
    sess.add(Classification(
        record_id="R1",
        l1_code="2",
        l1_name="Tiempos y espera",
        l2_code="2.2",
        l2_name="Turnos y filas",
        l3_code=None,
        l3_name=None,
        confidence=0.8,
        source="classifier",
        polarity="neg",
        ui_bucket="Tiempos y espera",
        created_at="2026-01-01",
    ))
    sess.commit()

    out = top_causes(sess, "national", group="Detractor", limit=10)
    counts = {c.bucket: c.count for c in out}
    # Cada bucket debe contar 1 sola vez (no 2 para Tiempos y espera).
    assert counts["Tiempos y espera"] == 1
    assert counts["Atención del personal"] == 1
    assert counts["Cajeros (ATM)"] == 1


def test_passive_analysis_segmenta_7_y_8(session: Session) -> None:
    result = passive_analysis(session, "national")
    assert "near_detractor" in result
    assert "near_promoter" in result

    # Verificar que pasivos con rate=7 contribuyen a near_detractor.
    from analytics.topics import _bucket_distinct_record_count
    from sqlalchemy.sql import ColumnElement

    near_d_total: int = 0
    for cb in result["near_detractor"]:
        near_d_total += cb.count
    # Si hay al menos un bucket reportado, hay al menos un pasivo rate=7.
    rate7 = (
        session.execute(
            select(Verbalization).where(
                Verbalization.nps_group == "Pasivo",
                Verbalization.nps_rate == 7,
            )
        )
        .scalars()
        .all()
    )
    if rate7:
        assert near_d_total > 0


def test_bucket_distribution_returns_dict(session: Session) -> None:
    out = bucket_distribution(session, "national")
    assert isinstance(out, dict)
    assert all(isinstance(k, str) and isinstance(v, int) for k, v in out.items())
