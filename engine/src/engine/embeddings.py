"""Embedder de sentencias multilingüe (M2b).

Wrapper delgado sobre `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
(decisión §9 de `00_decisiones_tecnicas.md`).

Inicialización lazy y singleton: la primera llamada a `get_default_embedder()`
construye la instancia; las siguientes devuelven la misma referencia. Esto
evita pagar la carga (~3-5 s en CPU) más de una vez dentro de la API o de
los scripts de preprocesamiento.

Convenciones de uso:
- `encode([])` devuelve `np.ndarray` de shape `(0, dim)` (no falla).
- `normalize_embeddings=True` por default — produce vectores unitarios,
  útiles para LogisticRegression downstream y para coseno trivial.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


DEFAULT_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_DIM = 384
DEFAULT_BATCH_SIZE = 64


class Embedder:
    """Encapsula un `SentenceTransformer` y expone `encode`.

    No es thread-safe a propósito: la carga del modelo se hace una sola
    vez por proceso y la instancia compartida se sirve con
    `get_default_embedder()`.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        *,
        device: str | None = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        from sentence_transformers import SentenceTransformer

        logger.info("cargando modelo de embeddings %s", model_name)
        self.model_name = model_name
        self.batch_size = batch_size
        self._model: SentenceTransformer = SentenceTransformer(
            model_name, device=device
        )
        dim = self._model.get_sentence_embedding_dimension()
        self.dim: int = int(dim) if dim is not None else DEFAULT_DIM

    def encode(
        self,
        texts: list[str],
        *,
        batch_size: int | None = None,
        show_progress_bar: bool = False,
        normalize_embeddings: bool = True,
    ) -> np.ndarray:
        """Codifica una lista de textos a una matriz `(n, dim)`.

        `encode([])` devuelve `np.zeros((0, dim))`, lo cual permite componer
        sin tener que añadir guards en el caller.
        """
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        bs = batch_size if batch_size is not None else self.batch_size
        result = self._model.encode(
            texts,
            batch_size=bs,
            show_progress_bar=show_progress_bar,
            normalize_embeddings=normalize_embeddings,
            convert_to_numpy=True,
        )
        return np.asarray(result, dtype=np.float32)


_default_embedder: Embedder | None = None


def get_default_embedder(
    model_name: str = DEFAULT_MODEL_NAME,
    *,
    device: str | None = None,
) -> Embedder:
    """Devuelve la instancia singleton del Embedder, construyéndola en el primer uso."""
    global _default_embedder
    if _default_embedder is None:
        _default_embedder = Embedder(model_name, device=device)
    return _default_embedder


def reset_default_embedder() -> None:
    """Reinicia el singleton. Útil sólo para tests."""
    global _default_embedder
    _default_embedder = None
