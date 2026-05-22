"""Inferencia del clasificador supervisado L1+L2 (M2b).

Carga el `.joblib` producido por `engine.trainer.train` y expone
`Classifier.predict(texts) -> list[list[CategoryPrediction]]`.

Contrato (`04_M2b_clasificador.md §Inferencia` + `01 §4`):
- Una entrada `texts` → una lista de listas. Cada sublista contiene las
  etiquetas que superaron `THRESHOLD` (=0.5) ordenadas por confianza
  descendente y, en caso de empate, por código de etiqueta ascendente
  (determinismo).
- `l3_code` y `l3_name` siempre `None` en inferencia (decisión §7).
- `confidence` redondeada a 4 decimales.
- Si ninguna etiqueta supera el umbral, la sublista correspondiente es `[]`
  y el caller (pipeline.classify) decide el fallback.

El singleton `get_default_classifier()` cachea la instancia para que la API y
los scripts no paguen la carga en cada llamada.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, TypedDict

import joblib
import numpy as np

from .embeddings import Embedder, get_default_embedder
from .taxonomy import get_l1_name, get_l2_name

logger = logging.getLogger(__name__)


DEFAULT_MODEL_PATH = Path("data/models/classifier.joblib")
THRESHOLD = 0.5


class CategoryPrediction(TypedDict):
    """Coincide con `01_contratos_compartidos.md §4`."""

    l1_code: str
    l1_name: str
    l2_code: str
    l2_name: str
    l3_code: str | None
    l3_name: str | None
    confidence: float


class Classifier:
    """Wrapper de inferencia sobre el dict serializado por `engine.trainer`."""

    def __init__(
        self,
        bundle: dict[str, Any],
        *,
        embedder: Embedder | None = None,
    ) -> None:
        self._validate_bundle(bundle)
        self.embedder_name: str = bundle["embedder_name"]
        self.binarizer = bundle["binarizer"]
        self.clf = bundle["clf"]
        self.label_codes: list[str] = list(bundle["label_codes"])
        self.trained_at: str = bundle.get("trained_at", "")
        self.metrics: dict[str, Any] = bundle.get("metrics", {})
        self._embedder = embedder

    @staticmethod
    def _validate_bundle(bundle: dict[str, Any]) -> None:
        required = {"embedder_name", "binarizer", "clf", "label_codes"}
        missing = required - bundle.keys()
        if missing:
            raise ValueError(
                f"Bundle del clasificador inválido: faltan claves {sorted(missing)}"
            )

    @classmethod
    def load(
        cls, path: str | Path = DEFAULT_MODEL_PATH, *, embedder: Embedder | None = None
    ) -> Classifier:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(
                f"No se encontró el modelo en {p}. "
                "Corre `python -m engine.cli train --annotation-run-id <N>` primero."
            )
        bundle = joblib.load(p)
        return cls(bundle, embedder=embedder)

    @property
    def embedder(self) -> Embedder:
        if self._embedder is None:
            self._embedder = get_default_embedder()
        return self._embedder

    def predict(self, texts: list[str]) -> list[list[CategoryPrediction]]:
        """Predice etiquetas L1+L2 para cada texto.

        Devuelve siempre una lista del mismo largo que `texts`. Cada elemento
        es una lista (posiblemente vacía) de `CategoryPrediction` ordenadas
        por `confidence` descendente.
        """
        if not texts:
            return []

        embeddings = self.embedder.encode(texts)
        proba = self._predict_proba(embeddings)

        out: list[list[CategoryPrediction]] = []
        for row in proba:
            out.append(self._select_categories(row))
        return out

    def _predict_proba(self, embeddings: np.ndarray) -> np.ndarray:
        """Devuelve la matriz `(n, n_labels)` de probabilidades.

        `predict_proba` en `OneVsRestClassifier` devuelve un ndarray
        directo si la base es scikit; lo normalizamos en cualquier caso.
        """
        raw = self.clf.predict_proba(embeddings)
        arr = np.asarray(raw)
        if arr.ndim != 2 or arr.shape[1] != len(self.label_codes):
            raise RuntimeError(
                f"predict_proba devolvió shape inesperada {arr.shape}; "
                f"se esperaba (_, {len(self.label_codes)})"
            )
        return arr

    def _select_categories(self, probas: np.ndarray) -> list[CategoryPrediction]:
        """Selecciona etiquetas > THRESHOLD y construye CategoryPrediction."""
        hits: list[tuple[float, str]] = []
        for idx, p in enumerate(probas):
            if p > THRESHOLD:
                hits.append((float(p), self.label_codes[idx]))
        if not hits:
            return []
        # Orden determinístico: confianza desc, código asc en empates.
        hits.sort(key=lambda x: (-x[0], x[1]))
        return [_build_category(label, prob) for prob, label in hits]


def _build_category(label_code: str, confidence: float) -> CategoryPrediction:
    """Construye un CategoryPrediction a partir de `'l1.l2'` y su probabilidad."""
    parts = label_code.split(".")
    if len(parts) < 2:
        raise ValueError(f"Etiqueta inválida: {label_code!r} (esperado 'L1.L2')")
    l1_code = parts[0]
    l2_code = ".".join(parts[:2])
    try:
        l1_name = get_l1_name(l1_code)
    except KeyError:
        l1_name = ""
    try:
        l2_name = get_l2_name(l1_code, l2_code)
    except KeyError:
        l2_name = ""
    return {
        "l1_code": l1_code,
        "l1_name": l1_name,
        "l2_code": l2_code,
        "l2_name": l2_name,
        "l3_code": None,
        "l3_name": None,
        "confidence": round(float(confidence), 4),
    }


_default_classifier: Classifier | None = None


def get_default_classifier(
    path: str | Path | None = None, *, refresh: bool = False
) -> Classifier:
    """Devuelve la instancia singleton del Classifier.

    Si `refresh=True` o si el path cambia, recarga.
    `path` puede venir del env `CLASSIFIER_MODEL_PATH`.
    """
    global _default_classifier
    target = Path(path or os.getenv("CLASSIFIER_MODEL_PATH") or DEFAULT_MODEL_PATH)
    if refresh or _default_classifier is None:
        _default_classifier = Classifier.load(target)
    return _default_classifier


def reset_default_classifier() -> None:
    """Reinicia el singleton. Útil sólo para tests."""
    global _default_classifier
    _default_classifier = None
