"""API pública del motor (M2b).

Funciones consumidas por `analytics/`, `api/` y los scripts de preprocess:

- `classify(record_id, text, nps_group) -> ClassificationResult`
- `classify_batch(items) -> list[ClassificationResult]`
- `persist_classification(result, *, engine=None) -> None`

Lógica clave (`04_M2b §Pipeline público` + decisiones §8 / §11):

- Polaridad heredada del NPS: Detractor→neg, Pasivo→neu, Promotor→pos.
- Textos con `len(strip) < 5` se marcan `is_classifiable=False`. Igualmente
  se les asigna una categoría de fallback para que el universo de
  `verbalizations` quede cubierto al 100 % (KPI duro del reto).
- Si el clasificador no devuelve ninguna etiqueta sobre el umbral 0.5, se
  aplica la rama de fallback (§11):
    * `len(strip) < 10`               → L1=15 / L2=15.1 (No clasificable).
    * `nps_group ∈ {Promotor, Pasivo}` → L1=14 / L2=14.1 (Elogio genérico).
    * `nps_group == 'Detractor'`     → L1=14 / L2=14.2 (Queja genérica).
- Metadata transversal: siempre se ejecuta `engine.extractors.extract_all`
  sobre el texto crudo (los extractores manejan `text=""` y devuelven shape
  válido).
"""

from __future__ import annotations

import json
import logging
from typing import Literal, TypedDict

from sqlalchemy import Engine, text as sql_text

from .classifier import CategoryPrediction, Classifier, get_default_classifier
from .extractors import Metadata, extract_all
from .taxonomy import get_l1_name, get_l2_name
from .ui_buckets import assign_ui_bucket

logger = logging.getLogger(__name__)


Polarity = Literal["pos", "neu", "neg"]

NPS_TO_POLARITY: dict[str, Polarity] = {
    "Detractor": "neg",
    "Pasivo": "neu",
    "Promotor": "pos",
}

MIN_TEXT_LEN_CLASSIFIABLE = 5
MIN_TEXT_LEN_FOR_GENERIC_FALLBACK = 10


class ClassificationResult(TypedDict):
    """Coincide con `01_contratos_compartidos.md §4`."""

    record_id: str
    is_classifiable: bool
    categories: list[CategoryPrediction]
    polarity: Polarity
    metadata: Metadata


# ============================================================================
# Construcción de fallback
# ============================================================================


def _fallback_category(text_clean: str, polarity: Polarity) -> CategoryPrediction:
    """Aplica la regla §11 sobre `text_clean` y `polarity`.

    Devuelve siempre un `CategoryPrediction` con `confidence=0.0`.
    """
    if len(text_clean) < MIN_TEXT_LEN_FOR_GENERIC_FALLBACK:
        l1_code, l2_code, l2_name_fallback = "15", "15.1", "No clasificable"
    elif polarity == "neg":
        l1_code, l2_code, l2_name_fallback = "14", "14.2", "Queja genérica"
    else:
        l1_code, l2_code, l2_name_fallback = "14", "14.1", "Elogio genérico"

    # Lookup tolerante: si la taxonomía no tiene el L2 (caso de 15.1, sintético),
    # caemos al nombre por defecto declarado arriba.
    try:
        l1_name = get_l1_name(l1_code)
    except KeyError:
        l1_name = ""
    try:
        l2_name = get_l2_name(l1_code, l2_code)
    except KeyError:
        l2_name = l2_name_fallback

    return {
        "l1_code": l1_code,
        "l1_name": l1_name,
        "l2_code": l2_code,
        "l2_name": l2_name,
        "l3_code": None,
        "l3_name": None,
        "confidence": 0.0,
    }


def _empty_metadata() -> Metadata:
    return {
        "personnel_named": False,
        "personnel_name": None,
        "personnel_polarity": None,
        "explicit_recommendation": None,
        "mentions_other_bank": False,
        "other_bank_names": [],
        "channels_mentioned": [],
    }


# ============================================================================
# API pública
# ============================================================================


def classify(
    record_id: str,
    text: str | None,
    nps_group: str,
    *,
    classifier: Classifier | None = None,
) -> ClassificationResult:
    """Versión unitaria de `classify_batch`."""
    return classify_batch([(record_id, text or "", nps_group)], classifier=classifier)[0]


def classify_batch(
    items: list[tuple[str, str, str]],
    *,
    classifier: Classifier | None = None,
) -> list[ClassificationResult]:
    """Clasifica un lote de verbalizaciones en una sola pasada.

    `items` es una lista de `(record_id, text, nps_group)`. Devuelve una lista
    del mismo largo con el `ClassificationResult` correspondiente a cada
    entrada y en el mismo orden.

    El embedding y la inferencia se hacen en bloque sobre los textos
    procesables (`is_classifiable=True`); los demás reciben categoría de
    fallback inmediatamente sin pagar el costo de embedding.

    El parámetro keyword-only `classifier` permite inyectar un clasificador
    en tests sin tocar el singleton global; en producción siempre se omite.
    """
    if not items:
        return []

    results: list[ClassificationResult] = []
    texts_to_predict: list[str] = []
    indices_to_predict: list[int] = []

    for idx, (record_id, raw_text, nps_group) in enumerate(items):
        if nps_group not in NPS_TO_POLARITY:
            raise ValueError(
                f"nps_group inválido {nps_group!r}; esperado uno de {list(NPS_TO_POLARITY)}"
            )
        polarity = NPS_TO_POLARITY[nps_group]
        text_clean = (raw_text or "").strip()
        is_classifiable = len(text_clean) >= MIN_TEXT_LEN_CLASSIFIABLE
        if is_classifiable:
            metadata = extract_all(raw_text or "")
            texts_to_predict.append(text_clean)
            indices_to_predict.append(idx)
        else:
            metadata = _empty_metadata()

        results.append(
            {
                "record_id": record_id,
                "is_classifiable": is_classifiable,
                "categories": [],
                "polarity": polarity,
                "metadata": metadata,
            }
        )

    if texts_to_predict:
        cls = classifier if classifier is not None else get_default_classifier()
        predictions = cls.predict(texts_to_predict)
        for result_idx, preds in zip(indices_to_predict, predictions):
            results[result_idx]["categories"] = list(preds)

    # Aplicar fallback en todo registro que quedó sin categoría.
    for result_idx, result in enumerate(results):
        if not result["categories"]:
            text_clean = (items[result_idx][1] or "").strip()
            result["categories"] = [_fallback_category(text_clean, result["polarity"])]

    return results


# ============================================================================
# Persistencia
# ============================================================================


def persist_classification(
    result: ClassificationResult,
    *,
    engine: Engine | None = None,
) -> None:
    """Inserta el `result` en `classifications` y `metadata_extractions`.

    - Una fila por categoría en `classifications` (multilabel).
    - `source = 'fallback'` si `confidence == 0.0`, si no `'classifier'`.
    - `metadata_extractions` se hace upsert por `record_id`.
    """
    if engine is None:
        from core.db import get_engine

        engine = get_engine()

    record_id = result["record_id"]
    polarity = result["polarity"]
    categories = result["categories"]
    metadata = result["metadata"]

    with engine.begin() as conn:
        for cat in categories:
            source = "fallback" if cat["confidence"] == 0.0 else "classifier"
            conn.execute(
                sql_text(
                    "INSERT INTO classifications "
                    "(record_id, l1_code, l1_name, l2_code, l2_name, l3_code, l3_name, "
                    " confidence, source, polarity, ui_bucket) VALUES "
                    "(:record_id, :l1_code, :l1_name, :l2_code, :l2_name, :l3_code, :l3_name, "
                    " :confidence, :source, :polarity, :ui_bucket)"
                ),
                {
                    "record_id": record_id,
                    "l1_code": cat["l1_code"],
                    "l1_name": cat["l1_name"],
                    "l2_code": cat["l2_code"],
                    "l2_name": cat["l2_name"],
                    "l3_code": cat["l3_code"],
                    "l3_name": cat["l3_name"],
                    "confidence": float(cat["confidence"]),
                    "source": source,
                    "polarity": polarity,
                    "ui_bucket": assign_ui_bucket(cat["l1_code"]),
                },
            )

        conn.execute(
            sql_text(
                "INSERT OR REPLACE INTO metadata_extractions "
                "(record_id, personnel_named, personnel_name, personnel_polarity, "
                " explicit_recommendation, mentions_other_bank, other_bank_names, "
                " channels_mentioned) VALUES "
                "(:record_id, :personnel_named, :personnel_name, :personnel_polarity, "
                " :explicit_recommendation, :mentions_other_bank, :other_bank_names, "
                " :channels_mentioned)"
            ),
            {
                "record_id": record_id,
                "personnel_named": int(bool(metadata["personnel_named"])),
                "personnel_name": metadata["personnel_name"],
                "personnel_polarity": metadata["personnel_polarity"],
                "explicit_recommendation": metadata["explicit_recommendation"],
                "mentions_other_bank": int(bool(metadata["mentions_other_bank"])),
                "other_bank_names": json.dumps(
                    list(metadata["other_bank_names"]), ensure_ascii=False
                ),
                "channels_mentioned": json.dumps(
                    list(metadata["channels_mentioned"]), ensure_ascii=False
                ),
            },
        )


# Re-export tipo público para conveniencia de imports.
__all__ = [
    "ClassificationResult",
    "NPS_TO_POLARITY",
    "classify",
    "classify_batch",
    "persist_classification",
]
