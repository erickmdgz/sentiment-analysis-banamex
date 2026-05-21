"""Tests del parser de taxonomía (`engine.taxonomy`).

Contratos verificados contra la taxonomía real del cliente
(`docs/taxonomia_revisada.md`):
- 15 L1, 45 L2, 82 L3 (el resumen interno del propio doc dice 48/~90 pero el
  contenido sólo enumera 45/82 — discrepancia anotada en contracts_issues.md).
- `get_l2_name('1', '1.1') == 'Trato del personal'`.
- Códigos clave para reglas de desambiguación (1.2.2, 2.2.3, 6.5.1, 8.3, 9.1,
  9.2, 10.3, 14.1, 14.2) están presentes.
- L1=15 ("Otros / No clasificable") no tiene L2 hijos.
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


def test_l2_count_matches_taxonomy_content() -> None:
    """Cuenta real del contenido (no del summary del doc, que dice 48)."""
    _, n_l2, _ = count_levels(load_taxonomy())
    assert n_l2 == 45, f"Esperaba 45 L2 (contenido real), obtuve {n_l2}"


def test_l3_count_matches_taxonomy_content() -> None:
    """Cuenta real del contenido (no del summary del doc, que dice ~90)."""
    _, _, n_l3 = count_levels(load_taxonomy())
    assert n_l3 == 82, f"Esperaba 82 L3 (contenido real), obtuve {n_l3}"


def test_get_l2_name_canonical() -> None:
    assert get_l2_name("1", "1.1") == "Trato del personal"


def test_get_l1_name() -> None:
    assert get_l1_name("1") == "Atención al cliente"
    assert get_l1_name("2") == "Tiempos y operación"
    assert get_l1_name("4") == "Cajeros automáticos (ATM)"


def test_disambiguation_codes_present() -> None:
    """Cubre todas las reglas de desambiguación citadas en 03_M2a."""
    tax = load_taxonomy()
    # 1.2.2 vs 6.5.1: engaño vs venta cruzada
    assert "1.2.2" in tax["1"]["l2"]["1.2"]["l3"]
    assert "6.5.1" in tax["6"]["l2"]["6.5"]["l3"]
    # 2.2.3 vs 10.3: síntoma vueltas vs causa burocracia
    assert "2.2.3" in tax["2"]["l2"]["2.2"]["l3"]
    assert "10.3" in tax["10"]["l2"]
    # 8.3 vs 9.1 vs 9.2: cargo / aclaración / fraude
    assert "8.3" in tax["8"]["l2"]
    assert "9.1" in tax["9"]["l2"]
    assert "9.2" in tax["9"]["l2"]
    # Bolsa genérica
    assert "14.1" in tax["14"]["l2"]
    assert "14.2" in tax["14"]["l2"]


def test_l1_15_has_no_l2_children() -> None:
    """L1=15 ('Otros / No clasificable') no abre L2; es bolsa terminal."""
    tax = load_taxonomy()
    assert tax["15"]["l2"] == {}


def test_l2_without_l3_children_is_valid() -> None:
    """Varias L2 reales no abren L3 (ej. 8.2 'Tasas de interés', 9.2, 11.x)."""
    tax = load_taxonomy()
    assert tax["8"]["l2"]["8.2"]["l3"] == {}
    assert tax["9"]["l2"]["9.2"]["l3"] == {}


def test_l2_with_parenthetical_name_parses() -> None:
    """`- **14.1 Elogio genérico** ("excelente", "todo bien")` debe parsear."""
    tax = load_taxonomy()
    assert tax["14"]["l2"]["14.1"]["name"] == "Elogio genérico"


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
