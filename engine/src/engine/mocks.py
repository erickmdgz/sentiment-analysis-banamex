"""Mock determinístico de `engine.pipeline.classify` (M2b).

Permite que `M3 / analytics`, `M4 / api` y `scripts/preprocess_corpora`
escriban tests y demos sin entrenar el clasificador real ni cargar los
~120 MB del modelo de embeddings.

Contrato:
- Misma firma y mismo tipo de retorno que `engine.pipeline.classify`.
- Determinístico: mismo `(text, nps_group)` → misma salida exacta.
- Sin dependencias del paquete (no carga embeddings, no toca DB, no lee
  los archivos en `engine/data/`). Detecta metadata con keywords mínimas.

Recetas:
- L1 elegido por hash MD5 de `text.strip().lower()` módulo 10 (decisión §13
  de `00_decisiones_tecnicas.md` mapea L1=1..10 a los 10 buckets visibles).
- L2 sintética del estilo "{l1_code}.1".
- Texto vacío o muy corto → fallback §11 idéntico al real.
- Confidence: 0.85 fija para resultados "reales" del mock, 0.0 para fallback.
"""

from __future__ import annotations

import hashlib
from typing import Literal

from .extractors import Metadata
from .pipeline import (
    ClassificationResult,
    NPS_TO_POLARITY,
    _empty_metadata,
    _fallback_category,
)
from .taxonomy import get_l1_name, get_l2_name
from .ui_buckets import UI_BUCKETS_BY_L1


MOCK_CONFIDENCE = 0.85

# L1 reales y "cause-able" (no caen en bucket "Otros"). Recorremos por
# hash para distribuir mocks entre buckets visibles.
_PRIMARY_L1_CODES: list[str] = [
    code
    for code, bucket in UI_BUCKETS_BY_L1.items()
    if bucket != "Otros" and int(code) <= 11
]


def _detect_metadata(text: str) -> Metadata:
    """Detección naive basada en `in text.lower()` (no usa los .txt del paquete)."""
    if not text:
        return _empty_metadata()
    lower = text.lower()

    personnel_named = any(
        kw in lower
        for kw in (" sr ", " sr.", "srita", "srta", "señora", "señor", "gerente", "cajero", "cajera", "ejecutivo")
    )

    explicit: Literal["pos", "neg"] | None = None
    if "no lo recomiendo" in lower or "no se lo recomendaría" in lower:
        explicit = "neg"
    elif "lo recomiendo" in lower or "lo recomendaría" in lower:
        explicit = "pos"

    other_banks: list[str] = []
    for bank in ("BBVA", "Banorte", "Santander", "HSBC", "Scotiabank"):
        if bank.lower() in lower:
            other_banks.append(bank)

    channels: list[str] = []
    if "app" in lower or "aplicación" in lower:
        channels.append("app")
    if "atm" in lower or "cajero automático" in lower:
        channels.append("atm")

    return {
        "personnel_named": personnel_named,
        "personnel_name": None,
        "personnel_polarity": None,
        "explicit_recommendation": explicit,
        "mentions_other_bank": bool(other_banks),
        "other_bank_names": other_banks,
        "channels_mentioned": channels,
    }


def _pick_l1(text: str) -> str:
    """Hash determinístico → L1 del subconjunto primario."""
    digest = hashlib.md5(text.strip().lower().encode("utf-8")).hexdigest()
    idx = int(digest[:8], 16) % len(_PRIMARY_L1_CODES)
    return _PRIMARY_L1_CODES[idx]


def classify_mock(
    record_id: str,
    text: str | None,
    nps_group: str,
) -> ClassificationResult:
    """Mock determinístico del pipeline público.

    Garantiza:
    - `polarity` heredada del `nps_group` (mismo mapeo que el real).
    - `metadata` con las 4 claves del TypedDict `Metadata`.
    - `categories` no vacío para texto procesable; fallback §11 si len<5.
    """
    if nps_group not in NPS_TO_POLARITY:
        raise ValueError(f"nps_group inválido {nps_group!r}")
    polarity = NPS_TO_POLARITY[nps_group]

    text_clean = (text or "").strip()
    if len(text_clean) < 5:
        return {
            "record_id": record_id,
            "is_classifiable": False,
            "categories": [_fallback_category(text_clean, polarity)],
            "polarity": polarity,
            "metadata": _empty_metadata(),
        }

    l1_code = _pick_l1(text_clean)
    l2_code = f"{l1_code}.1"
    try:
        l1_name = get_l1_name(l1_code)
    except KeyError:
        l1_name = ""
    try:
        l2_name = get_l2_name(l1_code, l2_code)
    except KeyError:
        l2_name = "Subcategoría mock"

    category = {
        "l1_code": l1_code,
        "l1_name": l1_name,
        "l2_code": l2_code,
        "l2_name": l2_name,
        "l3_code": None,
        "l3_name": None,
        "confidence": MOCK_CONFIDENCE,
    }

    return {
        "record_id": record_id,
        "is_classifiable": True,
        "categories": [category],
        "polarity": polarity,
        "metadata": _detect_metadata(text or ""),
    }
