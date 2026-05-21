"""Tests para analytics.words."""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from analytics.words import _load_stopwords, top_words
from core.models_db import Branch, File, Verbalization


def test_stopwords_filtered(session: Session) -> None:
    out = top_words(session, "B-0001", top_n=50)
    stopwords = _load_stopwords()
    words = {w.word for w in out}
    assert not (words & stopwords)


def test_tokenization_ignores_numbers_and_punctuation(
    session_factory: sessionmaker[Session],
) -> None:
    sess = session_factory()
    sess.add(File(
        id=1, filename="f", sha256="x", rows_total=0, rows_inserted=0,
        rows_duplicated=0, rows_invalid=0, uploaded_at="2026-01-01",
    ))
    sess.add(Branch(branch_id="B-W", first_seen_at="2026-01-01"))
    sess.add(Verbalization(
        record_id="R1", file_id=1, response_date="2026-01-01",
        response_year=2026, response_month=1, nps_group="Promotor",
        nps_rate=9,
        verbatim="¡Excelente! 1234, !!! atención, atención.",
        verbatim_clean="¡Excelente! 1234, !!! atención, atención.",
        branch_id="B-W", has_verbatim=1,
    ))
    sess.commit()
    out = top_words(sess, "B-W", top_n=10)
    words = {w.word for w in out}
    assert "1234" not in words
    assert "!!!" not in words
    # palabras válidas tokenizadas y minúsculas
    assert "atención" in words or "excelente" in words


def test_top_words_branch_scope(session: Session) -> None:
    out = top_words(session, "B-0001", group="Detractor", top_n=15)
    assert all(w.group == "Detractor" for w in out)
