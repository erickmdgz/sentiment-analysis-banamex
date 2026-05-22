"""Tests del singleton Embedder (M2b §test 1-3)."""

from __future__ import annotations

import numpy as np
import pytest

from engine.embeddings import (
    DEFAULT_DIM,
    Embedder,
    get_default_embedder,
    reset_default_embedder,
)


@pytest.fixture(scope="module")
def embedder() -> Embedder:
    # Reusar el singleton entre tests del módulo para no recargar el modelo (~3-5 s).
    reset_default_embedder()
    return get_default_embedder()


def test_encode_empty_returns_shape_zero_dim(embedder: Embedder) -> None:
    arr = embedder.encode([])
    assert arr.shape == (0, embedder.dim)


def test_encode_repeated_texts_bit_identical(embedder: Embedder) -> None:
    arr = embedder.encode(["hola", "hola"])
    assert arr.shape == (2, embedder.dim)
    np.testing.assert_array_equal(arr[0], arr[1])


def test_encode_normalized_unit_norm(embedder: Embedder) -> None:
    arr = embedder.encode(["hola amigo", "buen servicio"])
    norms = np.linalg.norm(arr, axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-5)


def test_default_dim_is_384() -> None:
    # Verifica que el modelo elegido coincida con la decisión §9.
    emb = get_default_embedder()
    assert emb.dim == DEFAULT_DIM


def test_singleton_returns_same_instance() -> None:
    a = get_default_embedder()
    b = get_default_embedder()
    assert a is b
