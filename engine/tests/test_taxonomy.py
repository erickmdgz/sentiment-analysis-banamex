"""Tests del parser de taxonomía (`engine.taxonomy`).

Contratos verificados:
- 15 L1, 48 L2, ~90 L3 (umbral 85-95).
- `get_l2_name('1', '1.1') == 'Trato del personal'`.
- Códigos clave para reglas de desambiguación (1.2.2, 2.2.3, 6.5.1, 14.1, 14.2)
  están presentes.
"""

from __future__ import annotations

import pytest

from engine.taxonomy import (
    count_levels,
    get_l1_name,
    get_l2_name,
    l3_belongs_to_l2,
    load_taxonomy,
    serialize_for_prompt,
)


def test_l1_count_is_exactly_15() -> None:
    n_l1, _, _ = count_levels(load_taxonomy())
    assert n_l1 == 15, f"Esperaba 15 L1, obtuve {n_l1}"


def test_l2_count_is_exactly_48() -> None:
    _, n_l2, _ = count_levels(load_taxonomy())
    assert n_l2 == 48, f"Esperaba 48 L2, obtuve {n_l2}"


def test_l3_count_in_85_95_band() -> None:
    _, _, n_l3 = count_levels(load_taxonomy())
    assert 85 <= n_l3 <= 95, f"Esperaba ~90 L3 (85-95), obtuve {n_l3}"


def test_get_l2_name_canonical() -> None:
    assert get_l2_name("1", "1.1") == "Trato del personal"


def test_get_l1_name() -> None:
    assert get_l1_name("1") == "Atención al cliente"
    assert get_l1_name("2") == "Tiempos y operación"


def test_disambiguation_codes_present() -> None:
    tax = load_taxonomy()
    assert "1.2" in tax["1"]["l2"]
    assert "1.2.2" in tax["1"]["l2"]["1.2"]["l3"]
    assert "2.2.3" in tax["2"]["l2"]["2.2"]["l3"]
    assert "6.5.1" in tax["6"]["l2"]["6.5"]["l3"]
    assert "10.3" in tax["10"]["l2"]
    assert "14.1" in tax["14"]["l2"]
    assert "14.2" in tax["14"]["l2"]


def test_unknown_codes_raise() -> None:
    with pytest.raises(KeyError):
        get_l1_name("99")
    with pytest.raises(KeyError):
        get_l2_name("1", "1.99")


def test_l3_belongs_to_l2() -> None:
    assert l3_belongs_to_l2("1.1.1", "1.1")
    assert not l3_belongs_to_l2("1.1.1", "1.2")
    assert not l3_belongs_to_l2("1.1", "1.1")  # L2 no es hijo de sí mismo


def test_serialize_for_prompt_is_non_empty_and_includes_l1() -> None:
    s = serialize_for_prompt()
    assert s
    assert "1. Atención al cliente" in s
    assert "1.1 Trato del personal" in s
    assert "1.1.1" in s  # al menos un L3
