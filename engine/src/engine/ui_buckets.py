"""Mapeo de las 15 categorías L1 a 10 buckets visibles en UI.

Cada fila de classifications tiene ui_bucket poblado por este mapeo.
Compartido entre M2a (anotador), M2b (clasificador supervisado) y M3 (analytics).

Fuente: docs/plan_implementacion/01_contratos_compartidos.md §6.
"""

from __future__ import annotations

UI_BUCKETS_BY_L1: dict[str, str] = {
    "1": "Atención del personal",
    "2": "Tiempos y espera",
    "3": "Sucursal física",
    "4": "Cajeros (ATM)",
    "5": "Canales digitales",
    "6": "Productos y promociones",
    "7": "Operaciones transaccionales",
    "8": "Costos",
    "9": "Aclaraciones, quejas y fraude",
    "10": "Procesos y requisitos",
    "11": "Productos y promociones",  # se une con 6
    "12": "Otros",
    "13": "Otros",
    "14": "Otros",
    "15": "Otros",
}

CAUSE_BUCKETS: list[str] = [
    "Atención del personal",
    "Tiempos y espera",
    "Sucursal física",
    "Cajeros (ATM)",
    "Canales digitales",
    "Productos y promociones",
    "Operaciones transaccionales",
    "Costos",
    "Aclaraciones, quejas y fraude",
    "Procesos y requisitos",
]

STRENGTH_BUCKETS: list[str] = [
    "Atención del personal",
    "Tiempos y espera",
    "Sucursal física",
    "Cajeros (ATM)",
    "Canales digitales",
    "Productos y promociones",
    "Operaciones transaccionales",
]


def assign_ui_bucket(l1_code: str) -> str:
    return UI_BUCKETS_BY_L1.get(l1_code, "Otros")
