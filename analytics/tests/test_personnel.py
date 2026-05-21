"""Tests para analytics.personnel."""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from analytics.personnel import mentions
from core.models_db import (
    Branch,
    File,
    MetadataExtraction,
    Verbalization,
)


def test_mentions_same_name_two_polarities(
    session_factory: sessionmaker[Session],
) -> None:
    sess = session_factory()
    sess.add(File(
        id=1, filename="f", sha256="x", rows_total=0, rows_inserted=0,
        rows_duplicated=0, rows_invalid=0, uploaded_at="2026-01-01",
    ))
    sess.add(Branch(branch_id="B-PER", first_seen_at="2026-01-01"))

    # Mismo nombre Ana con polaridades distintas
    cases = [
        ("R1", "Promotor", 9, "pos"),
        ("R2", "Promotor", 9, "pos"),
        ("R3", "Detractor", 2, "neg"),
    ]
    for rid, group, rate, polarity in cases:
        sess.add(Verbalization(
            record_id=rid, file_id=1, response_date="2026-01-01",
            response_year=2026, response_month=1, nps_group=group,
            nps_rate=rate, verbatim=f"Ana fue {polarity}",
            verbatim_clean=f"Ana fue {polarity}",
            branch_id="B-PER", has_verbatim=1,
        ))
        sess.add(MetadataExtraction(
            record_id=rid, personnel_named=1, personnel_name="Ana",
            personnel_polarity=polarity, explicit_recommendation=None,
            mentions_other_bank=0, other_bank_names=None,
            channels_mentioned=None, extracted_at="2026-01-01",
        ))
    sess.commit()

    out = mentions(sess, "B-PER")
    by_pol = {m.polarity: m for m in out if m.name == "Ana"}
    assert "pos" in by_pol
    assert "neg" in by_pol
    assert by_pol["pos"].count == 2
    assert by_pol["neg"].count == 1


def test_mentions_filters_unrelated_branches(
    session_factory: sessionmaker[Session],
) -> None:
    sess = session_factory()
    sess.add(File(
        id=1, filename="f", sha256="x", rows_total=0, rows_inserted=0,
        rows_duplicated=0, rows_invalid=0, uploaded_at="2026-01-01",
    ))
    sess.add(Branch(branch_id="B-A", first_seen_at="2026-01-01"))
    sess.add(Branch(branch_id="B-B", first_seen_at="2026-01-01"))
    sess.add(Verbalization(
        record_id="RA", file_id=1, response_date="2026-01-01",
        response_year=2026, response_month=1, nps_group="Promotor",
        nps_rate=9, verbatim="", verbatim_clean="", branch_id="B-A",
        has_verbatim=0,
    ))
    sess.add(MetadataExtraction(
        record_id="RA", personnel_named=1, personnel_name="Luis",
        personnel_polarity="pos", explicit_recommendation=None,
        mentions_other_bank=0, other_bank_names=None,
        channels_mentioned=None, extracted_at="2026-01-01",
    ))
    sess.commit()

    assert mentions(sess, "B-A")
    assert mentions(sess, "B-B") == []
