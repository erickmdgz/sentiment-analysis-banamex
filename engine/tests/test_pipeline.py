"""Tests del pipeline público (M2b §test 9-14).

Se inyecta un `Classifier` real entrenado sobre el golden set sintético del
módulo `test_trainer` y un `StubClassifier` para forzar el caso de
clasificador-sin-resultado.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from sqlalchemy import text

from _synthetic_golden import init_sqlite, make_synthetic_records, seed_golden_set
from engine.classifier import CategoryPrediction, Classifier
from engine.embeddings import get_default_embedder, reset_default_embedder
from engine.pipeline import (
    NPS_TO_POLARITY,
    classify,
    classify_batch,
    persist_classification,
)


class _StubClassifier:
    """Clasificador que devuelve lo que se le ordene; no carga modelo real."""

    def __init__(self, response: list[list[CategoryPrediction]] | None = None) -> None:
        self._response = response

    def predict(self, texts: list[str]) -> list[list[CategoryPrediction]]:
        if self._response is not None:
            assert len(self._response) == len(texts)
            return self._response
        return [[] for _ in texts]


@pytest.fixture(scope="module")
def real_classifier(tmp_path_factory: pytest.TempPathFactory) -> Classifier:
    from engine import trainer

    tmp_dir = tmp_path_factory.mktemp("pipeline_module")
    db_path = tmp_dir / "test.db"
    engine = init_sqlite(db_path)
    seed_golden_set(engine, make_synthetic_records())
    reset_default_embedder()
    embedder = get_default_embedder()
    model_path = tmp_dir / "classifier.joblib"
    trainer.train(
        annotation_run_id=1,
        seed=42,
        engine=engine,
        embedder=embedder,
        model_path=model_path,
    )
    return Classifier.load(model_path, embedder=embedder)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_empty_text_marks_not_classifiable() -> None:
    """§test 9: text="" → is_classifiable=False y fallback se materializa.

    El pipeline emite la categoría de fallback en `categories` (no espera a
    persist) para que cualquier consumidor downstream tenga cobertura 100%.
    """
    stub = _StubClassifier()
    result = classify("R1", "", "Detractor", classifier=stub)  # type: ignore[arg-type]
    assert result["is_classifiable"] is False
    assert len(result["categories"]) == 1
    assert result["categories"][0]["confidence"] == 0.0
    assert result["categories"][0]["l1_code"] == "15"


def test_normal_verbatim_returns_some_category(real_classifier: Classifier) -> None:
    """§test 10: text procesable → categories no vacía (real o fallback)."""
    result = classify(
        "R2",
        "el personal fue muy amable y atento",
        "Promotor",
        classifier=real_classifier,
    )
    assert result["is_classifiable"] is True
    assert len(result["categories"]) >= 1


@pytest.mark.parametrize(
    "nps_group, expected_polarity",
    [("Detractor", "neg"), ("Pasivo", "neu"), ("Promotor", "pos")],
)
def test_polarity_matches_nps_mapping(
    nps_group: str, expected_polarity: str
) -> None:
    """§test 11: polaridad siempre derivada del nps_group."""
    stub = _StubClassifier()
    result = classify("R3", "algún comentario procesable", nps_group, classifier=stub)  # type: ignore[arg-type]
    assert result["polarity"] == expected_polarity
    assert NPS_TO_POLARITY[nps_group] == expected_polarity


def test_metadata_has_required_keys() -> None:
    """§test 12: metadata incluye las 4 (en realidad 7) claves del TypedDict."""
    stub = _StubClassifier()
    result = classify(
        "R4",
        "la srita Diana fue muy amable, no como BBVA",
        "Promotor",
        classifier=stub,  # type: ignore[arg-type]
    )
    meta = result["metadata"]
    for key in (
        "personnel_named",
        "personnel_name",
        "personnel_polarity",
        "explicit_recommendation",
        "mentions_other_bank",
        "other_bank_names",
        "channels_mentioned",
    ):
        assert key in meta


def test_short_text_detractor_fallback_to_l15() -> None:
    """§test 13: verbatim corto ('x') + Detractor → fallback con l1_code='15'."""
    stub = _StubClassifier()
    result = classify("R5", "x", "Detractor", classifier=stub)  # type: ignore[arg-type]
    assert result["categories"][0]["l1_code"] == "15"
    assert result["categories"][0]["l2_code"] == "15.1"
    assert result["categories"][0]["confidence"] == 0.0


def test_long_text_classifier_empty_fallback_to_l14_detractor() -> None:
    """§test 14: text normal pero clasificador devuelve [] → fallback l1='14' (queja)."""
    stub = _StubClassifier(response=[[]])
    result = classify(
        "R6",
        "un comentario suficientemente largo para clasificarse",
        "Detractor",
        classifier=stub,  # type: ignore[arg-type]
    )
    assert result["is_classifiable"] is True
    assert result["categories"][0]["l1_code"] == "14"
    assert result["categories"][0]["l2_code"] == "14.2"
    assert result["categories"][0]["confidence"] == 0.0


def test_long_text_classifier_empty_fallback_to_l14_promoter() -> None:
    """Promotor / Pasivo con classifier vacío → fallback elogio 14.1."""
    stub = _StubClassifier(response=[[]])
    result = classify(
        "R7",
        "un comentario suficientemente largo para clasificarse",
        "Promotor",
        classifier=stub,  # type: ignore[arg-type]
    )
    assert result["categories"][0]["l1_code"] == "14"
    assert result["categories"][0]["l2_code"] == "14.1"


def test_classify_batch_preserves_order() -> None:
    """classify_batch mantiene el orden 1:1 con los inputs."""
    stub = _StubClassifier()
    items = [
        ("A", "el personal fue muy amable y atento", "Promotor"),
        ("B", "", "Detractor"),
        ("C", "no funciona la app del banco", "Detractor"),
    ]
    results = classify_batch(items, classifier=stub)  # type: ignore[arg-type]
    assert [r["record_id"] for r in results] == ["A", "B", "C"]


def test_invalid_nps_group_raises() -> None:
    stub = _StubClassifier()
    with pytest.raises(ValueError):
        classify("R8", "comentario", "Mecenas", classifier=stub)  # type: ignore[arg-type]


def test_persist_classification_writes_classifications_and_metadata(
    tmp_path: Path,
) -> None:
    """Verifica que persist_classification inserte en ambas tablas con los flags correctos."""
    db_path = tmp_path / "persist.db"
    engine = init_sqlite(db_path)
    # files row stub para la FK desde verbalizations.
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO files (id, filename, sha256, rows_total, rows_inserted, "
                "rows_duplicated, rows_invalid) VALUES (1, 'f.tsv', 'h', 1, 1, 0, 0)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO verbalizations "
                "(record_id, file_id, response_date, response_year, response_month, "
                " nps_group, nps_rate, verbatim, verbatim_clean, branch_id, has_verbatim) "
                "VALUES ('R001', 1, '2025-01-15', 2025, 1, 'Detractor', 5, 'x', 'x', 'A-1', 0)"
            )
        )

    stub = _StubClassifier()
    result = classify("R001", "x", "Detractor", classifier=stub)  # type: ignore[arg-type]
    persist_classification(result, engine=engine)

    with engine.connect() as conn:
        clf_rows = conn.execute(
            text("SELECT * FROM classifications WHERE record_id='R001'")
        ).all()
        meta_rows = conn.execute(
            text("SELECT * FROM metadata_extractions WHERE record_id='R001'")
        ).all()

    assert len(clf_rows) == 1
    row = clf_rows[0]._mapping
    assert row["l1_code"] == "15"
    assert row["source"] == "fallback"
    assert row["polarity"] == "neg"
    assert row["ui_bucket"] == "Otros"
    assert len(meta_rows) == 1


def test_persist_classification_classifier_source(tmp_path: Path) -> None:
    """Categoría con confidence>0 → source='classifier' al persistir."""
    db_path = tmp_path / "persist2.db"
    engine = init_sqlite(db_path)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO files (id, filename, sha256, rows_total, rows_inserted, "
                "rows_duplicated, rows_invalid) VALUES (1, 'f.tsv', 'h', 1, 1, 0, 0)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO verbalizations "
                "(record_id, file_id, response_date, response_year, response_month, "
                " nps_group, nps_rate, verbatim, verbatim_clean, branch_id, has_verbatim) "
                "VALUES ('R002', 1, '2025-01-15', 2025, 1, 'Promotor', 9, "
                " 'el personal fue muy amable', 'el personal fue muy amable', 'A-1', 1)"
            )
        )

    fake_category: CategoryPrediction = {
        "l1_code": "1",
        "l1_name": "Atención al cliente",
        "l2_code": "1.1",
        "l2_name": "Trato del personal",
        "l3_code": None,
        "l3_name": None,
        "confidence": 0.92,
    }
    stub = _StubClassifier(response=[[fake_category]])
    result = classify(
        "R002", "el personal fue muy amable", "Promotor", classifier=stub  # type: ignore[arg-type]
    )
    persist_classification(result, engine=engine)

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT source, ui_bucket, polarity FROM classifications WHERE record_id='R002'")
        ).one()
    assert row.source == "classifier"
    assert row.polarity == "pos"
    assert row.ui_bucket == "Atención del personal"
