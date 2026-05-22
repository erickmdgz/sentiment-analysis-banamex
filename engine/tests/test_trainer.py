"""Tests del trainer M2b (§test 4-6).

Construye una DB SQLite temporal con golden set sintético (200 filas, 5 etiquetas),
corre `engine.trainer.train`, verifica métricas, persistencia del `.joblib` y de la
fila en `classifier_runs`.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import pytest
from sqlalchemy import Engine, text

from _synthetic_golden import init_sqlite, make_synthetic_records, seed_golden_set
from engine import trainer
from engine.embeddings import get_default_embedder, reset_default_embedder


@pytest.fixture(scope="module")
def trained_bundle(tmp_path_factory: pytest.TempPathFactory) -> dict:
    """Entrena una sola vez por sesión de tests; comparte resultado."""
    tmp_dir = tmp_path_factory.mktemp("trainer")
    db_path = tmp_dir / "test.db"
    engine = init_sqlite(db_path)
    records = make_synthetic_records()
    seed_golden_set(engine, records)

    reset_default_embedder()
    embedder = get_default_embedder()

    model_path = tmp_dir / "classifier.joblib"
    run = trainer.train(
        annotation_run_id=1,
        seed=42,
        engine=engine,
        embedder=embedder,
        model_path=model_path,
    )
    return {
        "engine": engine,
        "run": run,
        "model_path": model_path,
        "embedder": embedder,
        "n_records": len(records),
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_train_produces_joblib_loadable(trained_bundle: dict) -> None:
    """§test 5: el .joblib existe y se carga sin error."""
    model_path: Path = trained_bundle["model_path"]
    assert model_path.exists()
    bundle = joblib.load(model_path)
    assert set(bundle.keys()) >= {
        "embedder_name",
        "binarizer",
        "clf",
        "label_codes",
        "trained_at",
        "metrics",
    }
    assert len(bundle["label_codes"]) == 5


def test_train_inserts_row_in_classifier_runs(trained_bundle: dict) -> None:
    """§test 6: una fila nueva en classifier_runs con campos poblados."""
    engine: Engine = trained_bundle["engine"]
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT * FROM classifier_runs")).all()
    assert len(rows) == 1
    row = rows[0]._mapping
    assert row["model_path"]
    assert row["n_samples"] == trained_bundle["n_records"]
    assert row["n_labels"] == 5
    assert row["f1_micro"] is not None
    assert row["f1_macro"] is not None
    assert row["hamming_loss"] is not None
    assert row["trained_on_run_id"] == 1


def test_train_f1_micro_above_threshold(trained_bundle: dict) -> None:
    """§test 4: con dataset sintético separable, f1_micro > 0.4."""
    run = trained_bundle["run"]
    assert run.f1_micro is not None
    assert run.f1_micro > 0.4, (
        f"f1_micro={run.f1_micro:.3f} demasiado bajo para un dataset sintético "
        "claramente separable"
    )
