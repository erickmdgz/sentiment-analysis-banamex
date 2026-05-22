"""Shim temporal: clasifica verbalizaciones del upload con un mock determinístico.

TODO: reemplazar por `engine.pipeline.classify_batch` cuando M2b se mergee.
Mientras tanto, `engine.mocks` declarado en `01_contratos_compartidos.md §7` no
existe en main (ver entrada en `contracts_issues.md` del 2026-05-21 — M4).
Este módulo respeta la firma y los DTOs declarados en `01 §4` (ClassificationResult).

Heurística: hash del verbatim → L1 ∈ {1..11} (los buckets de "causa/fortaleza").
Polaridad heredada del grupo NPS (`00 §8`). Si `verbatim` está vacío o muy
corto, se aplica fallback `15. Otros / No clasificable` (`00 §11`).
"""

from __future__ import annotations

import hashlib
from typing import Literal, TypedDict

from engine.extractors import extract_all
from engine.ui_buckets import assign_ui_bucket


class CategoryPrediction(TypedDict):
    l1_code: str
    l1_name: str
    l2_code: str
    l2_name: str
    l3_code: str | None
    l3_name: str | None
    confidence: float


class Metadata(TypedDict):
    personnel_named: bool
    personnel_name: str | None
    personnel_polarity: Literal["pos", "neg"] | None
    explicit_recommendation: Literal["pos", "neg"] | None
    mentions_other_bank: bool
    other_bank_names: list[str]
    channels_mentioned: list[str]


class ClassificationResult(TypedDict):
    record_id: str
    is_classifiable: bool
    categories: list[CategoryPrediction]
    polarity: Literal["pos", "neu", "neg"]
    metadata: Metadata


_L1_CANONICAL_NAMES: dict[str, str] = {
    "1": "Atención al cliente",
    "2": "Tiempos y operación",
    "3": "Sucursal física",
    "4": "Cajeros automáticos (ATM)",
    "5": "Canales digitales",
    "6": "Productos",
    "7": "Operaciones transaccionales",
    "8": "Costos",
    "9": "Aclaraciones, quejas y fraude",
    "10": "Procesos y requisitos",
    "11": "Programas y beneficios",
    "12": "Comunicación",
    "13": "Marca y confianza",
    "14": "Elogio o queja genérica",
    "15": "Otros / No clasificable",
}

_POLARITY_BY_NPS: dict[str, Literal["pos", "neu", "neg"]] = {
    "Promotor": "pos",
    "Pasivo": "neu",
    "Detractor": "neg",
}

_PRIMARY_L1S = [str(i) for i in range(1, 12)]


def _hash_to_l1(text: str) -> str:
    """Hash determinístico → uno de los 11 L1 primarios (buckets de causa/fortaleza)."""
    digest = hashlib.sha1(text.encode("utf-8")).digest()
    idx = digest[0] % len(_PRIMARY_L1S)
    return _PRIMARY_L1S[idx]


def _fallback_category(nps_group: str) -> CategoryPrediction:
    if nps_group == "Detractor":
        return CategoryPrediction(
            l1_code="14",
            l1_name=_L1_CANONICAL_NAMES["14"],
            l2_code="14.2",
            l2_name="Queja genérica",
            l3_code=None,
            l3_name=None,
            confidence=0.0,
        )
    return CategoryPrediction(
        l1_code="14",
        l1_name=_L1_CANONICAL_NAMES["14"],
        l2_code="14.1",
        l2_name="Elogio genérico",
        l3_code=None,
        l3_name=None,
        confidence=0.0,
    )


def classify_mock(record_id: str, text: str, nps_group: str) -> ClassificationResult:
    """Clasificación determinística para el endpoint `/upload`. Ver docstring del módulo."""
    polarity = _POLARITY_BY_NPS.get(nps_group, "neu")
    clean = (text or "").strip()
    metadata: Metadata = extract_all(clean)  # type: ignore[assignment]
    if len(clean) < 10:
        return ClassificationResult(
            record_id=record_id,
            is_classifiable=False,
            categories=[
                CategoryPrediction(
                    l1_code="15",
                    l1_name=_L1_CANONICAL_NAMES["15"],
                    l2_code="15.1",
                    l2_name="No clasificable",
                    l3_code=None,
                    l3_name=None,
                    confidence=0.0,
                )
            ],
            polarity=polarity,
            metadata=metadata,
        )

    l1 = _hash_to_l1(clean)
    category = CategoryPrediction(
        l1_code=l1,
        l1_name=_L1_CANONICAL_NAMES[l1],
        l2_code=f"{l1}.1",
        l2_name=f"{_L1_CANONICAL_NAMES[l1]} — subtema 1",
        l3_code=None,
        l3_name=None,
        confidence=0.6,
    )
    return ClassificationResult(
        record_id=record_id,
        is_classifiable=True,
        categories=[category],
        polarity=polarity,
        metadata=metadata,
    )


def classify_batch(
    items: list[tuple[str, str, str]],
) -> list[ClassificationResult]:
    """Wrapper batch sobre `classify_mock`. Mismo orden que el input."""
    return [classify_mock(rid, text, nps) for rid, text, nps in items]


def assign_bucket_for_l1(l1_code: str) -> str:
    """Atajo a `engine.ui_buckets.assign_ui_bucket` para los routers."""
    return assign_ui_bucket(l1_code)


__all__ = [
    "CategoryPrediction",
    "ClassificationResult",
    "Metadata",
    "assign_bucket_for_l1",
    "classify_batch",
    "classify_mock",
]
