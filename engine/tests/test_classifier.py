"""Tests del Classifier (M2b §test 7-8).

Reusa el `.joblib` producido por `test_trainer.trained_bundle` para no
re-entrenar. Si `test_trainer` no corrió antes en la misma sesión, este
módulo entrena su propio mini-bundle.
"""

from __future__ import annotations

import pytest

from _synthetic_golden import init_sqlite, make_synthetic_records, seed_golden_set
from engine.classifier import (
    THRESHOLD,
    Classifier,
    reset_default_classifier,
)
from engine.embeddings import get_default_embedder, reset_default_embedder


@pytest.fixture(scope="module")
def classifier(tmp_path_factory: pytest.TempPathFactory) -> Classifier:
    from engine import trainer

    tmp_dir = tmp_path_factory.mktemp("classifier_module")
    db_path = tmp_dir / "test.db"
    engine = init_sqlite(db_path)
    seed_golden_set(engine, make_synthetic_records())
    reset_default_embedder()
    reset_default_classifier()
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


def test_classifier_predict_deterministic(classifier: Classifier) -> None:
    """§test 7: misma entrada → misma salida (orden incluido)."""
    texts = ["el personal fue muy amable", "la app no funciona"]
    a = classifier.predict(texts)
    b = classifier.predict(texts)
    assert a == b


def test_classifier_returns_high_confidence_in_distribution(classifier: Classifier) -> None:
    """§test 8: textos in-distribution → al menos una etiqueta con conf>0.5."""
    in_dist = [
        "el personal fue muy amable y atento",
        "la fila fue interminable",
        "la sucursal está muy limpia",
        "el cajero automático no me dio mi dinero",
        "la app no funciona en mi celular",
    ]
    predictions = classifier.predict(in_dist)
    assert len(predictions) == len(in_dist)
    has_high_conf = any(
        any(cat["confidence"] > THRESHOLD for cat in preds) for preds in predictions
    )
    assert has_high_conf


def test_classifier_predict_empty_returns_empty(classifier: Classifier) -> None:
    """`predict([])` no rompe y devuelve lista vacía."""
    assert classifier.predict([]) == []


def test_classifier_out_of_distribution_may_be_empty(classifier: Classifier) -> None:
    """Texto fuera de distribución puede devolver `[]` — comportamiento válido."""
    preds = classifier.predict(["xkjasdh poiqwerty asdfghjkl"])
    # No asserción dura sobre vacío; sólo verificamos la forma (lista de lista).
    assert isinstance(preds, list) and len(preds) == 1
    assert isinstance(preds[0], list)


def test_classifier_category_structure(classifier: Classifier) -> None:
    """Cada CategoryPrediction tiene las 7 claves del TypedDict."""
    preds = classifier.predict(["el personal fue muy amable y atento"])
    if preds and preds[0]:
        cat = preds[0][0]
        assert set(cat.keys()) == {
            "l1_code",
            "l1_name",
            "l2_code",
            "l2_name",
            "l3_code",
            "l3_name",
            "confidence",
        }
        assert cat["l3_code"] is None
        assert cat["l3_name"] is None
