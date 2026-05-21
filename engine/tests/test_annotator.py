"""Tests del anotador LLM (`engine.annotator`).

Estrategia:
- No depende de Ollama. Inyectamos un cliente mock con `client.chat` async.
- Carga el fixture CSV (200 filas) y muestrea con seeds fijos.
- Verifica:
  - persistencia in-memory de `classifications` con `source='llm_annotation'`
    y `polarity` heredada del `nps_group`.
  - is_classifiable=false → 0 filas.
  - JSON malformado dispara retry con feedback explícito.
  - Cache en disco se respeta (2da corrida hace 0 llamadas al LLM).
- Muestreo: cuotas ±5%, determinismo entre dos invocaciones, filtra verbatim vacíos.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from engine.annotator import (
    AnnotationCache,
    REQUIRED_COLUMNS,
    run_annotation,
    sample_records,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "verbalizations.csv"


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    return pd.read_csv(FIXTURE_PATH)


# ============================================================================
# Mock client para Ollama
# ============================================================================


class FakeOllama:
    """Cliente async fake con `.chat()` y `.list()`.

    `responses` es una secuencia de payloads dict que se devuelven en orden;
    si se agotan, se reusa el último. Cada llamada incrementa `n_calls`.
    """

    def __init__(self, responses: list[dict[str, Any]] | None = None) -> None:
        self.responses = responses or []
        self.n_calls = 0
        self.last_messages: list[dict[str, Any]] | None = None

    async def chat(self, **kwargs: Any) -> dict[str, Any]:
        self.n_calls += 1
        self.last_messages = kwargs.get("messages")
        idx = min(self.n_calls - 1, len(self.responses) - 1) if self.responses else 0
        if not self.responses:
            payload = {"record_id": "x", "is_classifiable": False, "categories": []}
        else:
            payload = self.responses[idx]
        return {"message": {"content": json.dumps(payload)}}

    async def list(self) -> dict[str, Any]:
        return {"models": []}


# ============================================================================
# Muestreo
# ============================================================================


def test_sample_records_filters_empty_verbatim(df: pd.DataFrame) -> None:
    sampled = sample_records(df, target_size=50, seed=42)
    by_id = df.set_index("record_id")
    for rid in sampled:
        row = by_id.loc[rid]
        assert row["has_verbatim"] == 1
        text = str(row["verbatim_clean"] or "").strip()
        assert len(text) >= 5, f"{rid!r} → {text!r}"


def test_sample_records_deterministic(df: pd.DataFrame) -> None:
    a = sample_records(df, target_size=50, seed=42)
    b = sample_records(df, target_size=50, seed=42)
    assert a == b, "Misma seed debe producir el mismo conjunto"


def test_sample_records_different_seed_yields_different_set(df: pd.DataFrame) -> None:
    a = sample_records(df, target_size=50, seed=42)
    b = sample_records(df, target_size=50, seed=99)
    assert a != b


def test_sample_records_quotas_within_band(df: pd.DataFrame) -> None:
    """Comprueba cuotas ±5% sobre target_size=100 (fixture pequeño).

    Cuotas teóricas: 35 D, 25 P, 40 Pr. Banda ±5: D∈[30,40], P∈[20,30], Pr∈[35,45].
    """
    target = 100
    sampled = sample_records(df, target_size=target, seed=42)
    by_id = df.set_index("record_id")
    groups = pd.Series(
        [by_id.loc[r, "nps_group"] for r in sampled]
    ).value_counts()
    d, p, pr = groups.get("Detractor", 0), groups.get("Pasivo", 0), groups.get(
        "Promotor", 0
    )
    assert 30 <= d <= 40, f"Detractor={d} fuera de banda [30,40]"
    assert 20 <= p <= 30, f"Pasivo={p} fuera de banda [20,30]"
    assert 35 <= pr <= 45, f"Promotor={pr} fuera de banda [35,45]"


# ============================================================================
# run_annotation con mock
# ============================================================================


def _valid_two_cat_payload(record_id: str) -> dict[str, Any]:
    return {
        "record_id": record_id,
        "is_classifiable": True,
        "categories": [
            {
                "l1_code": "1",
                "l1_name": "Atención al cliente",
                "l2_code": "1.1",
                "l2_name": "Trato del personal",
                "l3_code": "1.1.1",
                "l3_name": "Amabilidad y cortesía",
                "confidence": 0.85,
            },
            {
                "l1_code": "2",
                "l1_name": "Tiempos y operación",
                "l2_code": "2.1",
                "l2_name": "Tiempo de espera",
                "l3_code": None,
                "l3_name": None,
                "confidence": 0.6,
            },
        ],
    }


def test_valid_two_cat_response_produces_two_rows(df: pd.DataFrame, tmp_path: Path) -> None:
    rid = df[df["nps_group"] == "Promotor"]["record_id"].iloc[0]
    fake = FakeOllama(responses=[_valid_two_cat_payload(rid)])
    cache = AnnotationCache(tmp_path / "cache")

    run = asyncio.run(
        run_annotation(
            df,
            record_ids=[rid],
            cache=cache,
            client=fake,
            skip_preflight=True,
            sample_size=1,
        )
    )

    assert run.status == "done"
    assert run.processed == 1
    assert len(run.classifications) == 2
    for row in run.classifications:
        assert row.record_id == rid
        assert row.source == "llm_annotation"
        # nps_group=Promotor → polarity=pos.
        assert row.polarity == "pos"
        # ui_bucket asignado.
        assert row.ui_bucket  # no vacío


def test_unclassifiable_response_produces_no_rows(df: pd.DataFrame, tmp_path: Path) -> None:
    rid = df["record_id"].iloc[0]
    fake = FakeOllama(
        responses=[{"record_id": rid, "is_classifiable": False, "categories": []}]
    )
    run = asyncio.run(
        run_annotation(
            df,
            record_ids=[rid],
            cache=AnnotationCache(tmp_path / "cache"),
            client=fake,
            skip_preflight=True,
            sample_size=1,
        )
    )
    assert run.status == "done"
    assert len(run.classifications) == 0
    assert rid in run.unclassifiable


def test_polarity_inherits_from_nps_group(df: pd.DataFrame, tmp_path: Path) -> None:
    """Detractor → neg, Pasivo → neu, Promotor → pos."""
    expectations = {"Detractor": "neg", "Pasivo": "neu", "Promotor": "pos"}
    for group, expected in expectations.items():
        rid = df[df["nps_group"] == group]["record_id"].iloc[0]
        fake = FakeOllama(responses=[_valid_two_cat_payload(rid)])
        run = asyncio.run(
            run_annotation(
                df,
                record_ids=[rid],
                cache=AnnotationCache(tmp_path / f"cache_{group}"),
                client=fake,
                skip_preflight=True,
                sample_size=1,
            )
        )
        assert run.classifications, f"esperaba clasificaciones para {group}"
        for row in run.classifications:
            assert row.polarity == expected


class MalformedThenValidOllama:
    """Primera llamada devuelve JSON inválido; segunda devuelve uno válido."""

    def __init__(self, valid: dict[str, Any]) -> None:
        self.valid = valid
        self.n_calls = 0
        self.last_messages: list[dict[str, Any]] = []

    async def chat(self, **kwargs: Any) -> dict[str, Any]:
        self.n_calls += 1
        self.last_messages = kwargs.get("messages", [])
        if self.n_calls == 1:
            return {"message": {"content": "this is not json {"}}
        return {"message": {"content": json.dumps(self.valid)}}

    async def list(self) -> dict[str, Any]:
        return {"models": []}


def test_malformed_json_triggers_retry_with_feedback(
    df: pd.DataFrame, tmp_path: Path
) -> None:
    rid = df["record_id"].iloc[0]
    fake = MalformedThenValidOllama(_valid_two_cat_payload(rid))
    run = asyncio.run(
        run_annotation(
            df,
            record_ids=[rid],
            cache=AnnotationCache(tmp_path / "cache"),
            client=fake,
            skip_preflight=True,
            sample_size=1,
        )
    )
    assert run.status == "done"
    assert fake.n_calls == 2
    # El feedback al modelo debe aparecer en la segunda llamada.
    feedback_msgs = [
        m for m in fake.last_messages if m.get("role") == "user"
    ]
    contents = [m["content"] for m in feedback_msgs]
    assert any(
        "tu última respuesta no fue JSON válido" in c for c in contents
    ), f"Feedback de reintento no encontrado en {contents!r}"


def test_cache_is_respected_second_run(df: pd.DataFrame, tmp_path: Path) -> None:
    rid = df["record_id"].iloc[0]
    cache = AnnotationCache(tmp_path / "cache")
    fake1 = FakeOllama(responses=[_valid_two_cat_payload(rid)])
    asyncio.run(
        run_annotation(
            df,
            record_ids=[rid],
            cache=cache,
            client=fake1,
            skip_preflight=True,
            sample_size=1,
        )
    )
    assert fake1.n_calls == 1

    # Segunda corrida: nueva instancia de fake, NO debe invocarse.
    fake2 = FakeOllama(responses=[_valid_two_cat_payload(rid)])
    run2 = asyncio.run(
        run_annotation(
            df,
            record_ids=[rid],
            cache=cache,
            client=fake2,
            skip_preflight=True,
            sample_size=1,
        )
    )
    assert fake2.n_calls == 0, "el cache debió evitar la llamada al LLM"
    assert run2.processed == 1
    assert len(run2.classifications) == 2


def test_l3_inconsistent_with_l2_is_dropped(df: pd.DataFrame, tmp_path: Path) -> None:
    """Si el LLM devuelve un L3 que no pertenece al L2, debe descartarse."""
    rid = df["record_id"].iloc[0]
    bad = {
        "record_id": rid,
        "is_classifiable": True,
        "categories": [
            {
                "l1_code": "1",
                "l1_name": "Atención al cliente",
                "l2_code": "1.1",
                "l2_name": "Trato del personal",
                "l3_code": "9.9.9",  # no pertenece a 1.1
                "l3_name": "ruido",
                "confidence": 0.5,
            }
        ],
    }
    fake = FakeOllama(responses=[bad])
    run = asyncio.run(
        run_annotation(
            df,
            record_ids=[rid],
            cache=AnnotationCache(tmp_path / "cache"),
            client=fake,
            skip_preflight=True,
            sample_size=1,
        )
    )
    assert len(run.classifications) == 1
    assert run.classifications[0].l3_code is None
    assert run.classifications[0].l3_name is None


def test_required_columns_constant_matches_df(df: pd.DataFrame) -> None:
    for col in REQUIRED_COLUMNS:
        assert col in df.columns, f"falta {col} en fixture"
