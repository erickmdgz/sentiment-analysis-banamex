"""Cliente async de Ollama + muestreo estratificado + caché en disco.

Responsabilidades (`03_M2a_anotador.md`):
- Construir el `SYSTEM_PROMPT` desde la taxonomía parseada.
- Muestrear 5,000 verbalizaciones estratificadas por `nps_group` × mes.
- Llamar a Ollama con `format=OUTPUT_SCHEMA` para constrained decoding.
- Reintentar con backoff exponencial si la respuesta no es JSON válido.
- Cachear cada respuesta en disco para reanudar tras Ctrl+C.

La persistencia en SQLite (tabla `classifications`) la hace el CLI a partir del
resultado in-memory que devuelve `run_annotation`. Esto facilita los tests sin
levantar DB.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Literal, Protocol

import pandas as pd

from .prompts import OUTPUT_SCHEMA, SYSTEM_PROMPT_TEMPLATE
from .taxonomy import (
    TaxonomyDict,
    l3_belongs_to_l2,
    load_taxonomy,
    serialize_for_prompt,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Tipos públicos
# ============================================================================


@dataclass
class ClassificationRow:
    """Una fila lista para persistir en la tabla `classifications`."""

    record_id: str
    l1_code: str
    l1_name: str
    l2_code: str
    l2_name: str
    l3_code: str | None
    l3_name: str | None
    confidence: float
    source: Literal["llm_annotation"] = "llm_annotation"
    polarity: Literal["pos", "neu", "neg"] = "neu"
    ui_bucket: str = "Otros"


@dataclass
class AnnotationRun:
    """Resultado in-memory de una corrida del anotador."""

    sample_size: int
    model: str
    started_at: str
    finished_at: str | None = None
    runtime_seconds: float | None = None
    status: Literal["running", "done", "failed"] = "running"
    processed: int = 0
    cached: int = 0
    failed: int = 0
    classifications: list[ClassificationRow] = field(default_factory=list)
    unclassifiable: list[str] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)


NPS_TO_POLARITY: dict[str, Literal["pos", "neu", "neg"]] = {
    "Detractor": "neg",
    "Pasivo": "neu",
    "Promotor": "pos",
}


# ============================================================================
# SYSTEM_PROMPT (se construye al vuelo a partir de la taxonomía)
# ============================================================================


def build_system_prompt(tax: TaxonomyDict | None = None) -> str:
    """Construye el SYSTEM_PROMPT inyectando la taxonomía serializada.

    Reglas de desambiguación citadas en `03_M2a §Detalles → Reglas de desambiguación`
    se incluyen como guía explícita.
    """
    body = SYSTEM_PROMPT_TEMPLATE.format(taxonomy=serialize_for_prompt(tax))
    return (
        body
        + """
Reglas operativas:
- Multiclase permitido hasta 5 etiquetas por verbalización.
- Pon is_classifiable=false sólo si el texto está vacío, ininteligible, o sin contenido temático.
- Devuelve l3_code y l3_name únicamente si la hoja es clara; si dudas, devuelve null.
- confidence debe ser honesta en [0.0, 1.0], no sesgada a 1.0.

Reglas de desambiguación clave:
- 1.2.2 vs 6.5.1: queja sobre cómo el personal ofrece/vende un producto → 1.2.2;
  queja sobre el producto/promoción en sí → 6.5.1.
- 2.2.3 vs 10.3: espera por proceso interno y pasos exigidos → 10.3;
  espera operativa por turnos/ventanilla/sistema → 2.2.3.
- 8.3 vs 9.1 vs 9.2: cuestiona un cobro pero no afirma error → 8.3;
  pide aclaración por cargo no reconocido → 9.1; denuncia fraude → 9.2.
"""
    )


def build_user_message(record_id: str, verbatim: str, nps_group: str) -> str:
    """Construye el mensaje 'user' por verbalización."""
    return (
        f"record_id: {record_id}\n"
        f"nps_group: {nps_group}\n"
        f"verbatim: {verbatim}\n"
        "Clasifica esta verbalización siguiendo el schema."
    )


# ============================================================================
# Muestreo estratificado
# ============================================================================


REQUIRED_COLUMNS = (
    "record_id",
    "verbatim_clean",
    "nps_group",
    "response_year",
    "response_month",
    "has_verbatim",
)


def sample_records(
    df: pd.DataFrame,
    target_size: int = 5000,
    seed: int = 42,
) -> list[str]:
    """Muestreo estratificado 35/25/40 por nps_group × mes.

    - Filtro previo: `has_verbatim == 1` y `len(verbatim_clean.strip()) >= 5`.
    - Cuotas: 35% Detractor, 25% Pasivo, 40% Promotor.
    - Distribuye uniforme entre los meses presentes.
    - Si una celda tiene menos filas que la cuota: toma todas las disponibles
      y compensa el déficit con detractores aleatorios extra (decisión `00 §6`).
    - Misma `seed` → mismo conjunto.
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas requeridas en df: {missing}")

    work = df.copy()
    work = work[work["has_verbatim"] == 1]
    work = work[work["verbatim_clean"].fillna("").str.strip().str.len() >= 5]
    if work.empty:
        return []

    quotas_pct: dict[str, float] = {"Detractor": 0.35, "Pasivo": 0.25, "Promotor": 0.40}
    quotas = {g: int(round(target_size * p)) for g, p in quotas_pct.items()}
    # Ajustar redondeo: que la suma sea exactamente target_size.
    diff = target_size - sum(quotas.values())
    if diff != 0:
        quotas["Detractor"] += diff  # ajusta sobre detractores

    # Meses presentes (year, month) ordenados.
    months = sorted(
        {(int(y), int(m)) for y, m in zip(work["response_year"], work["response_month"])}
    )
    if not months:
        return []

    rng_state = seed
    picked: list[str] = []

    for group, group_quota in quotas.items():
        gdf = work[work["nps_group"] == group]
        if gdf.empty or group_quota == 0:
            continue
        per_month = group_quota // len(months)
        remainder = group_quota - per_month * len(months)
        deficit = 0
        taken_ids: list[str] = []
        for i, (year, month) in enumerate(months):
            cell_quota = per_month + (1 if i < remainder else 0)
            cell = gdf[
                (gdf["response_year"] == year) & (gdf["response_month"] == month)
            ]
            if len(cell) >= cell_quota:
                sampled = cell.sample(n=cell_quota, random_state=rng_state)
            else:
                sampled = cell
                deficit += cell_quota - len(cell)
            rng_state += 1
            taken_ids.extend(sampled["record_id"].tolist())

        # Compensar déficit del grupo (no del grupo cruzado): toma del mismo grupo.
        if deficit > 0:
            remaining = gdf[~gdf["record_id"].isin(taken_ids)]
            if not remaining.empty:
                extra_n = min(deficit, len(remaining))
                extra = remaining.sample(n=extra_n, random_state=rng_state)
                rng_state += 1
                taken_ids.extend(extra["record_id"].tolist())
        picked.extend(taken_ids)

    # Si total < target_size, compensar con detractores aleatorios extra.
    if len(picked) < target_size:
        deficit = target_size - len(picked)
        pool = work[
            (work["nps_group"] == "Detractor") & (~work["record_id"].isin(picked))
        ]
        if not pool.empty:
            extra_n = min(deficit, len(pool))
            extra = pool.sample(n=extra_n, random_state=rng_state)
            picked.extend(extra["record_id"].tolist())

    # Determinismo: orden estable y reproducible.
    picked.sort()
    return picked


# ============================================================================
# Caché en disco
# ============================================================================


class AnnotationCache:
    """Caché en disco de respuestas válidas del LLM.

    Un archivo JSON por record_id en `cache_dir/{record_id}.json`. Permite
    reanudar tras Ctrl+C o falla intermedia sin re-procesar.
    """

    def __init__(self, cache_dir: str | Path) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, record_id: str) -> Path:
        safe = record_id.replace("/", "_").replace(os.sep, "_")
        return self.cache_dir / f"{safe}.json"

    def has(self, record_id: str) -> bool:
        return self._path(record_id).exists()

    def get(self, record_id: str) -> dict[str, Any] | None:
        p = self._path(record_id)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("cache corrupto para %s; se ignora", record_id)
            return None

    def put(self, record_id: str, payload: dict[str, Any]) -> None:
        self._path(record_id).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def clear(self) -> int:
        count = 0
        for p in self.cache_dir.glob("*.json"):
            p.unlink()
            count += 1
        return count


# ============================================================================
# Cliente Ollama (interfaz mínima para mockeo)
# ============================================================================


class OllamaLike(Protocol):
    async def chat(self, **kwargs: Any) -> dict[str, Any]: ...
    async def list(self) -> dict[str, Any]: ...


def make_default_client() -> OllamaLike:
    """Crea el `ollama.AsyncClient` real. Se aísla detrás de una función para
    que los tests puedan inyectar mocks sin importar el módulo `ollama`."""
    from ollama import AsyncClient

    return AsyncClient(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))  # type: ignore[return-value]


async def _preflight(client: OllamaLike, model: str) -> None:
    """Valida que Ollama responda y tenga el modelo descargado."""
    try:
        info = await client.list()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "No se pudo contactar Ollama. Asegúrate de que 'ollama serve' esté corriendo."
        ) from exc

    # ollama-python pre-0.5 devolvía dict; >=0.5 devuelve `ListResponse` Pydantic
    # con `info.models = list[Model]` donde cada Model expone `.model` (no `.name`).
    if isinstance(info, dict):
        raw_models = info.get("models", [])
    else:
        raw_models = getattr(info, "models", []) or []
    names: set[str] = set()
    for m in raw_models:
        if isinstance(m, dict):
            n = m.get("name") or m.get("model")
        else:
            n = getattr(m, "model", None) or getattr(m, "name", None)
        if n:
            names.add(n)
    # Algunas versiones devuelven `qwen2.5:7b-instruct` con sufijos como `:latest`.
    if model not in names and f"{model}:latest" not in names:
        raise RuntimeError(
            f"Modelo {model} no encontrado en Ollama. "
            f"Ejecuta 'ollama pull {model}' primero."
        )


# ============================================================================
# Validación de respuesta
# ============================================================================


def _validate_against_schema(payload: dict[str, Any]) -> None:
    """Validación defensiva además del constrained decoding."""
    import jsonschema  # importar tarde para que tests sin jsonschema usen el shim

    jsonschema.validate(payload, OUTPUT_SCHEMA)


def _coerce_classification_rows(
    payload: dict[str, Any],
    record_id: str,
    nps_group: str,
    tax: TaxonomyDict,
) -> list[ClassificationRow]:
    """Convierte la respuesta del LLM en filas listas para persistir."""
    from .ui_buckets import assign_ui_bucket

    if not payload.get("is_classifiable"):
        return []

    polarity = NPS_TO_POLARITY.get(nps_group, "neu")
    rows: list[ClassificationRow] = []
    for cat in payload.get("categories", []):
        l1_code = str(cat.get("l1_code"))
        l2_code = str(cat.get("l2_code"))
        l3_code = cat.get("l3_code")
        l3_name = cat.get("l3_name")
        # Coherencia L3 ⊂ L2: si el LLM devuelve un L3 que no pertenece al L2,
        # se descarta el L3 (queda NULL) y se loguea.
        if l3_code and not l3_belongs_to_l2(str(l3_code), l2_code):
            logger.warning(
                "record %s: l3_code %s no pertenece a l2_code %s; descartado",
                record_id,
                l3_code,
                l2_code,
            )
            l3_code, l3_name = None, None

        rows.append(
            ClassificationRow(
                record_id=record_id,
                l1_code=l1_code,
                l1_name=str(cat.get("l1_name", "")),
                l2_code=l2_code,
                l2_name=str(cat.get("l2_name", "")),
                l3_code=str(l3_code) if l3_code else None,
                l3_name=str(l3_name) if l3_name else None,
                confidence=float(cat.get("confidence", 0.0)),
                source="llm_annotation",
                polarity=polarity,
                ui_bucket=assign_ui_bucket(l1_code),
            )
        )
    return rows


# ============================================================================
# Annotation pipeline
# ============================================================================


async def _annotate_one(
    record_id: str,
    verbatim: str,
    nps_group: str,
    *,
    client: OllamaLike,
    model: str,
    system_prompt: str,
    cache: AnnotationCache | None,
    timeout_s: float = 60.0,
    max_retries: int = 3,
) -> tuple[str, dict[str, Any] | None, str | None]:
    """Anota una verbalización. Devuelve (record_id, payload, error_msg).

    `payload=None` y `error_msg` no nulo indican que el record_id falló tras retries.
    """
    if cache is not None:
        cached_payload = cache.get(record_id)
        if cached_payload is not None:
            return record_id, cached_payload, None

    base_messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": build_user_message(record_id, verbatim, nps_group),
        },
    ]
    messages = list(base_messages)
    last_error: str | None = None

    for attempt in range(max_retries):
        try:
            response = await asyncio.wait_for(
                client.chat(
                    model=model,
                    messages=messages,
                    format=OUTPUT_SCHEMA,
                    options={"temperature": 0.0, "seed": 42},
                ),
                timeout=timeout_s,
            )
        except asyncio.TimeoutError:
            last_error = f"timeout tras {timeout_s}s"
            await asyncio.sleep(2 ** attempt)
            continue
        except Exception as exc:  # noqa: BLE001
            last_error = f"exception {type(exc).__name__}: {exc}"
            await asyncio.sleep(2 ** attempt)
            continue

        content = _extract_response_content(response)
        try:
            payload = json.loads(content)
            _validate_against_schema(payload)
        except (json.JSONDecodeError, Exception) as exc:  # noqa: BLE001
            last_error = f"JSON/schema inválido: {exc}"
            messages = list(base_messages) + [
                {"role": "assistant", "content": content},
                {
                    "role": "user",
                    "content": "tu última respuesta no fue JSON válido, reintenta",
                },
            ]
            await asyncio.sleep(2 ** attempt)
            continue

        if cache is not None:
            cache.put(record_id, payload)
        return record_id, payload, None

    return record_id, None, last_error or "desconocido"


def _extract_response_content(response: Any) -> str:
    """Soporta tanto el formato dict (`response["message"]["content"]`) como
    objetos pydantic devueltos por ollama-python (`response.message.content`).
    """
    if isinstance(response, dict):
        msg = response.get("message")
        if isinstance(msg, dict):
            return str(msg.get("content", ""))
        return str(msg) if msg is not None else ""
    msg = getattr(response, "message", None)
    if msg is not None:
        content = getattr(msg, "content", None)
        if content is not None:
            return str(content)
    return ""


async def run_annotation(
    df: pd.DataFrame,
    *,
    sample_size: int = 5000,
    model: str | None = None,
    seed: int = 42,
    concurrency: int = 4,
    cache: AnnotationCache | None = None,
    client: OllamaLike | None = None,
    skip_preflight: bool = False,
    progress_every: int = 50,
    max_runtime_seconds: float = 12 * 3600,
    record_ids: Iterable[str] | None = None,
) -> AnnotationRun:
    """Corre el anotador end-to-end sobre `df`.

    `df` debe tener las columnas de `REQUIRED_COLUMNS` más `verbatim` o `verbatim_clean`.
    Si `record_ids` se pasa, se usan esos directamente (saltando el muestreo). Esto
    facilita los tests determinísticos.
    """
    model_name = model or os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
    client = client or make_default_client()
    cache = cache or AnnotationCache(_default_cache_dir())

    if not skip_preflight:
        await _preflight(client, model_name)

    tax = load_taxonomy()
    system_prompt = build_system_prompt(tax)

    if record_ids is None:
        sampled_ids = sample_records(df, target_size=sample_size, seed=seed)
    else:
        sampled_ids = list(record_ids)

    by_id = df.set_index("record_id")
    semaphore = asyncio.Semaphore(max(1, concurrency))
    started_at = datetime.now(timezone.utc).isoformat()
    t0 = time.monotonic()

    run = AnnotationRun(
        sample_size=len(sampled_ids),
        model=model_name,
        started_at=started_at,
        status="running",
    )

    async def worker(rid: str) -> None:
        async with semaphore:
            row = by_id.loc[rid]
            verbatim = row.get("verbatim_clean") or row.get("verbatim") or ""
            nps_group = str(row.get("nps_group", "Pasivo"))
            _, payload, err = await _annotate_one(
                rid,
                str(verbatim),
                nps_group,
                client=client,
                model=model_name,
                system_prompt=system_prompt,
                cache=cache,
            )
            if err is not None:
                run.failed += 1
                run.errors.append((rid, err))
                logger.warning("anotación fallida record=%s err=%s", rid, err)
                return
            assert payload is not None
            rows = _coerce_classification_rows(payload, rid, nps_group, tax)
            if not rows:
                run.unclassifiable.append(rid)
            run.classifications.extend(rows)
            run.processed += 1
            if run.processed % progress_every == 0:
                elapsed = time.monotonic() - t0
                rate = run.processed / max(elapsed, 1e-6)
                eta = (len(sampled_ids) - run.processed) / max(rate, 1e-6)
                logger.info(
                    "processed=%d total=%d elapsed=%.0fs ETA=%.0fs",
                    run.processed,
                    len(sampled_ids),
                    elapsed,
                    eta,
                )

    tasks = [worker(rid) for rid in sampled_ids if rid in by_id.index]
    # Cap defensivo de 12h.
    try:
        await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=False),
            timeout=max_runtime_seconds,
        )
        run.status = "done"
    except asyncio.TimeoutError:
        run.status = "failed"
        run.errors.append(
            ("__run__", f"runtime excedió {max_runtime_seconds}s; corrida abortada")
        )

    finished_at = datetime.now(timezone.utc).isoformat()
    run.finished_at = finished_at
    run.runtime_seconds = time.monotonic() - t0
    return run


def _default_cache_dir() -> Path:
    """`<repo>/data/cache/annotations/`."""
    here = Path(__file__).resolve()
    repo_root = here.parents[3]
    return repo_root / "data" / "cache" / "annotations"
