"""Tests de los 4 extractores rule-based (`engine.extractors`).

Cubre los casos enumerados en `03_M2a_anotador.md §Tests requeridos` (#12-22).
"""

from __future__ import annotations

from engine.extractors import (
    extract_all,
    extract_channels,
    extract_explicit_recommendation,
    extract_other_bank,
    extract_personnel,
)


# ---------- Personnel ----------


def test_personnel_srita_diana_positiva() -> None:
    r = extract_personnel("la srita Diana fue muy amable")
    assert r["personnel_named"] is True
    assert r["personnel_name"] == "Diana"
    assert r["personnel_polarity"] == "pos"


def test_personnel_gerente_grosero() -> None:
    r = extract_personnel("el gerente fue grosero")
    assert r["personnel_named"] is True
    assert r["personnel_name"] is None
    assert r["personnel_polarity"] == "neg"


def test_personnel_banamex_blacklisted() -> None:
    r = extract_personnel("Banamex no me ayudó")
    assert r["personnel_name"] != "Banamex"
    assert r["personnel_name"] is None


def test_personnel_mexico_blacklisted() -> None:
    r = extract_personnel("En México todo es lento")
    assert r["personnel_name"] != "México"
    assert r["personnel_name"] is None


def test_personnel_ana_cordial() -> None:
    r = extract_personnel("La cajera Ana fue cordial y paciente")
    assert r["personnel_named"] is True
    assert r["personnel_name"] == "Ana"
    assert r["personnel_polarity"] == "pos"


def test_personnel_empty_text() -> None:
    r = extract_personnel("")
    assert r == {
        "personnel_named": False,
        "personnel_name": None,
        "personnel_polarity": None,
    }


# ---------- Explicit recommendation ----------


def test_recommendation_positive() -> None:
    assert extract_explicit_recommendation("lo recomiendo a todos") == "pos"


def test_recommendation_negative_priority() -> None:
    assert extract_explicit_recommendation("no lo recomiendo a nadie") == "neg"


def test_recommendation_none_without_first_person() -> None:
    assert extract_explicit_recommendation("deberían recomendar la sucursal") is None


def test_recommendation_amply() -> None:
    assert extract_explicit_recommendation("lo recomiendo ampliamente") == "pos"


def test_recommendation_se_lo_negative() -> None:
    assert (
        extract_explicit_recommendation("no se lo recomendaría a nadie") == "neg"
    )


# ---------- Other bank ----------


def test_other_bank_bbva_detected() -> None:
    assert extract_other_bank("tengo cuenta en BBVA también") == ["BBVA"]


def test_other_bank_cajero_no_match() -> None:
    assert extract_other_bank("el cajero falló") == []


def test_other_bank_multiple_in_order() -> None:
    assert extract_other_bank("cambié a Santander porque BBVA cobra mucho") == [
        "Santander",
        "BBVA",
    ]


def test_other_bank_banamex_citi_adjacent_excluded() -> None:
    # 'Citi' inmediatamente adyacente a 'Banamex' debe descartarse.
    assert extract_other_bank("Banamex Citi me dio servicio") == []


# ---------- Channels ----------


def test_channels_app_and_atm() -> None:
    assert extract_channels("la app no funciona y el cajero tampoco") == [
        "app",
        "atm",
    ]


def test_channels_sucursal() -> None:
    assert extract_channels("fui a la sucursal") == ["sucursal"]


def test_channels_cajero_automatico_preferred_over_cajero() -> None:
    # La keyword más larga ("cajero automatico") debe ganar y producir 'atm' una sola vez.
    assert extract_channels("el cajero automatico tampoco funciona") == ["atm"]


def test_channels_whatsapp_to_chat() -> None:
    assert extract_channels("escribí por whatsapp y no me respondieron") == ["chat"]


def test_channels_normalization_no_accent() -> None:
    # 'aplicacion' sin acento también debe matchear 'app'.
    assert extract_channels("la aplicacion crashea") == ["app"]


# ---------- Composition ----------


def test_extract_all_composition() -> None:
    text = "La srita Diana fue muy amable, lo recomiendo. Mejor que BBVA en la app."
    meta = extract_all(text)
    assert meta["personnel_named"] is True
    assert meta["personnel_name"] == "Diana"
    assert meta["personnel_polarity"] == "pos"
    assert meta["explicit_recommendation"] == "pos"
    assert meta["mentions_other_bank"] is True
    assert meta["other_bank_names"] == ["BBVA"]
    assert meta["channels_mentioned"] == ["app"]
