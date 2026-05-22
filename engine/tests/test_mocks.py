"""Tests del mock determinístico (M2b §test 15)."""

from __future__ import annotations

from engine.mocks import classify_mock
from engine.pipeline import NPS_TO_POLARITY


def test_classify_mock_valid_shape() -> None:
    """§test 15: salida válida sin modelo entrenado ni embeddings."""
    result = classify_mock("R1", "atención excelente del personal", "Promotor")
    assert result["record_id"] == "R1"
    assert isinstance(result["categories"], list)
    assert result["polarity"] == "pos"
    assert "personnel_named" in result["metadata"]
    assert "explicit_recommendation" in result["metadata"]
    assert "mentions_other_bank" in result["metadata"]
    assert "channels_mentioned" in result["metadata"]


def test_classify_mock_deterministic() -> None:
    a = classify_mock("R2", "no funciona la app", "Detractor")
    b = classify_mock("R2", "no funciona la app", "Detractor")
    assert a == b


def test_classify_mock_short_text_fallback() -> None:
    result = classify_mock("R3", "x", "Detractor")
    assert result["is_classifiable"] is False
    assert result["categories"][0]["l1_code"] == "15"


def test_classify_mock_polarity_mapping() -> None:
    for nps, expected in NPS_TO_POLARITY.items():
        out = classify_mock("R4", "comentario suficiente para clasificar", nps)
        assert out["polarity"] == expected


def test_classify_mock_detects_bbva() -> None:
    out = classify_mock(
        "R5", "preferiría BBVA, la atención fue mala", "Detractor"
    )
    assert out["metadata"]["mentions_other_bank"] is True
    assert "BBVA" in out["metadata"]["other_bank_names"]


def test_classify_mock_detects_app_channel() -> None:
    out = classify_mock("R6", "la app del banco no funciona nunca", "Detractor")
    assert "app" in out["metadata"]["channels_mentioned"]


def test_classify_mock_categories_match_l1_l2_format() -> None:
    out = classify_mock("R7", "atención excelente del personal", "Promotor")
    cat = out["categories"][0]
    assert "." in cat["l2_code"]
    l1, *_ = cat["l2_code"].split(".")
    assert cat["l1_code"] == l1
