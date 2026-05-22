"""Entrenamiento del clasificador supervisado L1+L2 (M2b).

Lee el golden set producido por M2a (`classifications.source = 'llm_annotation'`),
embebe los textos, entrena `OneVsRestClassifier(LogisticRegression)` con
`class_weight='balanced'`, evalúa con `f1_micro`, `f1_macro`, `hamming_loss`
y `subset_accuracy`, persiste el bundle a `data/models/classifier.joblib` e
inserta una fila de trazabilidad en `classifier_runs`.

Decisiones consumidas:
- §9: modelo de embeddings (vía `engine.embeddings.get_default_embedder`).
- §10: LogisticRegression OneVsRest balanced.
- §11: umbral 0.5 vive en `engine.classifier.THRESHOLD` (no se aplica aquí).

Contrato del `.joblib` (`04_M2b §Contratos producidos`):

    {
        "embedder_name": str,
        "binarizer": MultiLabelBinarizer,
        "clf": OneVsRestClassifier,
        "label_codes": list[str],     # ["1.1", "1.2", "2.1", ...]
        "trained_at": str,            # ISO 8601 UTC
        "metrics": {
            "f1_micro": float,
            "f1_macro": float,
            "hamming_loss": float,
            "subset_accuracy": float,
            "n_samples_train": int,
            "n_samples_test": int,
        },
    }
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sqlalchemy import Engine, text

from .embeddings import DEFAULT_MODEL_NAME, Embedder, get_default_embedder

logger = logging.getLogger(__name__)


DEFAULT_MODEL_PATH = Path("data/models/classifier.joblib")
MIN_SAMPLES_FOR_SPLIT = 20


@dataclass
class ClassifierRun:
    """Resultado in-memory de un entrenamiento. Refleja la fila de `classifier_runs`."""

    id: int | None
    model_path: str
    trained_on_run_id: int | None
    trained_at: str
    n_samples: int
    n_labels: int
    f1_micro: float | None
    f1_macro: float | None
    hamming_loss: float | None
    subset_accuracy: float | None = None
    n_samples_train: int = 0
    n_samples_test: int = 0
    label_codes: list[str] = field(default_factory=list)


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch_golden_set(
    engine: Engine,
) -> tuple[list[str], list[str], list[list[str]]]:
    """Lee el golden set y devuelve (record_ids, texts, labels_per_record).

    Cada fila de `classifications` con `source='llm_annotation'` es una
    categoría asignada; agrupamos por `record_id` para reconstruir multilabel.
    """
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT v.record_id, v.verbatim_clean, c.l1_code, c.l2_code "
                "FROM verbalizations v "
                "JOIN classifications c ON v.record_id = c.record_id "
                "WHERE c.source = 'llm_annotation' "
                "  AND v.verbatim_clean IS NOT NULL "
                "  AND length(trim(v.verbatim_clean)) >= 5"
            )
        ).all()

    text_by_record: dict[str, str] = {}
    labels_by_record: dict[str, list[str]] = defaultdict(list)
    for record_id, verbatim_clean, l1_code, l2_code in rows:
        text_by_record.setdefault(record_id, str(verbatim_clean))
        # Asegurar formato "L1.L2" — si la fila guardó l2_code completo, usarlo;
        # si guardó solo el sub-índice, anteponer L1.
        if "." in l2_code:
            label = l2_code
        else:
            label = f"{l1_code}.{l2_code}"
        if label not in labels_by_record[record_id]:
            labels_by_record[record_id].append(label)

    record_ids = list(text_by_record.keys())
    texts = [text_by_record[r] for r in record_ids]
    labels = [labels_by_record[r] for r in record_ids]
    return record_ids, texts, labels


def _stratify_key(labels_per_row: list[list[str]]) -> list[str]:
    """Devuelve la 'L1 dominante' por fila (primera etiqueta) para stratify.

    Si una clase tiene menos de 2 ejemplos, se colapsa a `"__rare__"` para no
    romper `train_test_split` con stratify.
    """
    keys = [labels[0].split(".")[0] if labels else "__empty__" for labels in labels_per_row]
    counts: dict[str, int] = defaultdict(int)
    for k in keys:
        counts[k] += 1
    return [k if counts[k] >= 2 else "__rare__" for k in keys]


def _split_indices(
    n_samples: int, stratify: list[str], seed: int
) -> tuple[list[int], list[int], list[int]]:
    """Divide indices en train / val / test (80/10/10) con stratify cuando es viable.

    Estrategia robusta a datasets chicos:
    - Si hay <20 muestras, todo va a train, val y test vacíos.
    - Si stratify no es viable (alguna clase con <2), se intenta sin stratify.
    """
    from sklearn.model_selection import train_test_split

    indices = list(range(n_samples))
    if n_samples < MIN_SAMPLES_FOR_SPLIT:
        return indices, [], []

    strat = stratify if len(set(stratify)) > 1 else None

    try:
        train_idx, holdout_idx = train_test_split(
            indices,
            test_size=0.2,
            random_state=seed,
            stratify=strat,
        )
    except ValueError:
        train_idx, holdout_idx = train_test_split(
            indices, test_size=0.2, random_state=seed
        )

    holdout_strat = (
        [stratify[i] for i in holdout_idx]
        if strat is not None and len(set(stratify[i] for i in holdout_idx)) > 1
        else None
    )
    try:
        val_idx, test_idx = train_test_split(
            holdout_idx,
            test_size=0.5,
            random_state=seed,
            stratify=holdout_strat,
        )
    except ValueError:
        val_idx, test_idx = train_test_split(
            holdout_idx, test_size=0.5, random_state=seed
        )

    return train_idx, val_idx, test_idx


def _compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    from sklearn.metrics import (
        accuracy_score,
        f1_score,
        hamming_loss,
    )

    return {
        "f1_micro": float(f1_score(y_true, y_pred, average="micro", zero_division=0)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "hamming_loss": float(hamming_loss(y_true, y_pred)),
        "subset_accuracy": float(accuracy_score(y_true, y_pred)),
    }


def _persist_classifier_run(
    engine: Engine,
    *,
    model_path: str,
    trained_on_run_id: int | None,
    trained_at: str,
    n_samples: int,
    n_labels: int,
    metrics: dict[str, float],
) -> int:
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "INSERT INTO classifier_runs "
                "(model_path, trained_on_run_id, trained_at, n_samples, n_labels, "
                " f1_micro, f1_macro, hamming_loss) "
                "VALUES (:model_path, :trained_on_run_id, :trained_at, :n_samples, "
                "        :n_labels, :f1_micro, :f1_macro, :hamming_loss)"
            ),
            {
                "model_path": model_path,
                "trained_on_run_id": trained_on_run_id,
                "trained_at": trained_at,
                "n_samples": n_samples,
                "n_labels": n_labels,
                "f1_micro": metrics.get("f1_micro"),
                "f1_macro": metrics.get("f1_macro"),
                "hamming_loss": metrics.get("hamming_loss"),
            },
        )
        return int(result.lastrowid or 0)


def train(
    annotation_run_id: int | None = None,
    *,
    seed: int = 42,
    engine: Engine | None = None,
    embedder: Embedder | None = None,
    model_path: str | Path | None = None,
) -> ClassifierRun:
    """Entrena el clasificador L1+L2 sobre el golden set activo.

    Args:
        annotation_run_id: ID del `annotation_runs` para trazabilidad. Puede
            ser `None` (se persiste como NULL en `classifier_runs`).
        seed: semilla para `train_test_split` y `LogisticRegression`.
        engine: engine SQLAlchemy a usar. Si None, usa `core.db.get_engine()`.
        embedder: instancia opcional para tests. Si None, usa el singleton.
        model_path: ruta destino del `.joblib`. Si None, `data/models/classifier.joblib`.

    Returns:
        `ClassifierRun` con los metadatos del entrenamiento (incluye `id` de la
        fila persistida en `classifier_runs`).
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.multiclass import OneVsRestClassifier
    from sklearn.preprocessing import MultiLabelBinarizer

    if engine is None:
        from core.db import get_engine

        engine = get_engine()

    out_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)

    record_ids, texts, labels = _fetch_golden_set(engine)
    if not record_ids:
        raise RuntimeError(
            "No hay filas en `classifications` con source='llm_annotation'. "
            "Corre `python -m engine.cli annotate-sample --persist-db` primero."
        )
    logger.info("golden set: %d records, %d filas de classifications", len(record_ids), sum(len(l) for l in labels))

    mlb = MultiLabelBinarizer()
    Y = mlb.fit_transform(labels)
    label_codes = list(mlb.classes_)
    logger.info("etiquetas únicas L1+L2: %d", len(label_codes))

    emb = embedder or get_default_embedder()
    X = emb.encode(texts, show_progress_bar=False)

    stratify_keys = _stratify_key(labels)
    train_idx, val_idx, test_idx = _split_indices(len(record_ids), stratify_keys, seed)

    X_train, Y_train = X[train_idx], Y[train_idx]
    X_test = X[test_idx] if test_idx else np.empty((0, X.shape[1]), dtype=X.dtype)
    Y_test = Y[test_idx] if test_idx else np.empty((0, Y.shape[1]), dtype=Y.dtype)

    clf = OneVsRestClassifier(
        LogisticRegression(
            max_iter=1000,
            C=1.0,
            class_weight="balanced",
            random_state=seed,
        )
    )
    clf.fit(X_train, Y_train)

    if len(test_idx) > 0:
        Y_pred = clf.predict(X_test)
        metrics = _compute_metrics(Y_test, Y_pred)
    else:
        metrics = {
            "f1_micro": 0.0,
            "f1_macro": 0.0,
            "hamming_loss": 0.0,
            "subset_accuracy": 0.0,
        }
    metrics["n_samples_train"] = len(train_idx)
    metrics["n_samples_test"] = len(test_idx)

    trained_at = _iso_now()
    bundle: dict[str, Any] = {
        "embedder_name": emb.model_name if hasattr(emb, "model_name") else DEFAULT_MODEL_NAME,
        "binarizer": mlb,
        "clf": clf,
        "label_codes": label_codes,
        "trained_at": trained_at,
        "metrics": metrics,
    }
    joblib.dump(bundle, out_path)
    logger.info(
        "modelo persistido en %s (f1_micro=%.3f, f1_macro=%.3f)",
        out_path,
        metrics["f1_micro"],
        metrics["f1_macro"],
    )

    run_id = _persist_classifier_run(
        engine,
        model_path=str(out_path),
        trained_on_run_id=annotation_run_id,
        trained_at=trained_at,
        n_samples=len(record_ids),
        n_labels=len(label_codes),
        metrics=metrics,
    )

    return ClassifierRun(
        id=run_id,
        model_path=str(out_path),
        trained_on_run_id=annotation_run_id,
        trained_at=trained_at,
        n_samples=len(record_ids),
        n_labels=len(label_codes),
        f1_micro=metrics["f1_micro"],
        f1_macro=metrics["f1_macro"],
        hamming_loss=metrics["hamming_loss"],
        subset_accuracy=metrics["subset_accuracy"],
        n_samples_train=metrics["n_samples_train"],
        n_samples_test=metrics["n_samples_test"],
        label_codes=label_codes,
    )
