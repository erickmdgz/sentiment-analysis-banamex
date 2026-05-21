"""CLI del paquete engine.

Subcomandos M2a:
    annotate-sample    Anota una muestra estratificada con el LLM local.
    extract-metadata   Corre los 4 extractores rule-based sobre todas
                       las verbalizaciones sin metadata.

Diseño:
- Cargar verbalizaciones desde un fixture CSV o desde la DB de M1 (vía
  `--db-url`). El fixture es lo que usan los tests; la DB es el flujo
  real de producción.
- `annotate-sample --dry-run` imprime el sample sin llamar al LLM.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from .annotator import (
    AnnotationCache,
    REQUIRED_COLUMNS,
    _default_cache_dir,
    run_annotation,
    sample_records,
)
from .extractors import extract_all

logger = logging.getLogger("engine.cli")


# ============================================================================
# Carga de datos
# ============================================================================


def _load_dataframe(*, db_url: str | None, fixture: str | None) -> pd.DataFrame:
    """Carga verbalizations desde fixture CSV o desde la DB.

    Prioridad: si se pasa `fixture`, se usa el CSV; si se pasa `db_url`, la DB.
    Si ninguno se pasa, intenta `DATABASE_URL` del entorno; si tampoco existe,
    falla con mensaje claro.
    """
    if fixture:
        path = Path(fixture)
        if not path.exists():
            raise FileNotFoundError(f"Fixture no encontrado: {path}")
        df = pd.read_csv(path)
        return _normalize_df(df)

    url = db_url or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "No se pasó --fixture ni --db-url, y DATABASE_URL no está en el entorno. "
            "Para tests usa: --fixture engine/tests/fixtures/verbalizations.csv"
        )

    # Importación tardía para no requerir SQLAlchemy si sólo se usa fixture.
    from sqlalchemy import create_engine, text

    engine = create_engine(url)
    with engine.connect() as conn:
        df = pd.read_sql(
            text(
                "SELECT record_id, verbatim, verbatim_clean, nps_group, "
                "response_year, response_month, has_verbatim, branch_id "
                "FROM verbalizations"
            ),
            conn,
        )
    return _normalize_df(df)


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Asegura columnas requeridas con tipos correctos."""
    if "verbatim_clean" not in df.columns and "verbatim" in df.columns:
        df["verbatim_clean"] = df["verbatim"]
    if "has_verbatim" not in df.columns:
        df["has_verbatim"] = (
            df["verbatim_clean"].fillna("").str.strip().str.len() > 0
        ).astype(int)
    if "response_year" not in df.columns and "response_date" in df.columns:
        dt = pd.to_datetime(df["response_date"], errors="coerce")
        df["response_year"] = dt.dt.year
        df["response_month"] = dt.dt.month
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {missing}")
    return df


# ============================================================================
# Subcomandos
# ============================================================================


def cmd_annotate_sample(args: argparse.Namespace) -> int:
    df = _load_dataframe(db_url=args.db_url, fixture=args.fixture)

    if args.dry_run:
        sampled = sample_records(df, target_size=args.size, seed=args.seed)
        print(f"# Muestra estratificada ({len(sampled)} records, seed={args.seed})")
        sub = df[df["record_id"].isin(sampled)][
            ["record_id", "nps_group", "response_year", "response_month"]
        ].sort_values("record_id")
        for _, row in sub.iterrows():
            print(
                f"{row['record_id']}\t{row['nps_group']}\t"
                f"{int(row['response_year'])}-{int(row['response_month']):02d}"
            )
        groups = sub["nps_group"].value_counts().to_dict()
        print(f"# Resumen por grupo: {groups}")
        return 0

    cache_dir = Path(args.cache_dir) if args.cache_dir else _default_cache_dir()
    if args.clear_cache:
        removed = AnnotationCache(cache_dir).clear()
        logger.info("cache limpiado: %d archivos", removed)
    cache = AnnotationCache(cache_dir)

    run = asyncio.run(
        run_annotation(
            df,
            sample_size=args.size,
            model=args.model,
            seed=args.seed,
            concurrency=args.concurrency,
            cache=cache,
            skip_preflight=args.skip_preflight,
        )
    )

    print(
        json.dumps(
            {
                "status": run.status,
                "sample_size": run.sample_size,
                "processed": run.processed,
                "failed": run.failed,
                "unclassifiable": len(run.unclassifiable),
                "classifications_rows": len(run.classifications),
                "runtime_seconds": round(run.runtime_seconds or 0.0, 2),
                "model": run.model,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    if args.persist_db and args.db_url:
        _persist_run_to_db(args.db_url, run)
    return 0 if run.status == "done" else 1


def cmd_extract_metadata(args: argparse.Namespace) -> int:
    df = _load_dataframe(db_url=args.db_url, fixture=args.fixture)

    if args.all_records:
        target = df
    else:
        # Por default sólo verbalizations con texto.
        target = df[df["has_verbatim"] == 1]

    rows: list[dict[str, Any]] = []
    for _, row in target.iterrows():
        text = str(row.get("verbatim_clean") or row.get("verbatim") or "")
        meta = extract_all(text)
        rows.append(
            {
                "record_id": row["record_id"],
                "personnel_named": int(meta["personnel_named"]),
                "personnel_name": meta["personnel_name"],
                "personnel_polarity": meta["personnel_polarity"],
                "explicit_recommendation": meta["explicit_recommendation"],
                "mentions_other_bank": int(meta["mentions_other_bank"]),
                "other_bank_names": json.dumps(
                    meta["other_bank_names"], ensure_ascii=False
                ),
                "channels_mentioned": json.dumps(
                    meta["channels_mentioned"], ensure_ascii=False
                ),
            }
        )

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(out_path, index=False)
        print(f"Extracciones guardadas en {out_path} ({len(rows)} filas)")
    elif args.db_url:
        _persist_metadata_to_db(args.db_url, rows)
        print(f"Extracciones persistidas en {args.db_url} ({len(rows)} filas)")
    else:
        # stdout JSONL para inspección.
        for row in rows[: args.limit]:
            print(json.dumps(row, ensure_ascii=False))
    return 0


# ============================================================================
# Persistencia (opcional, sólo cuando hay DB de M1)
# ============================================================================


def _persist_run_to_db(db_url: str, run: Any) -> None:
    from sqlalchemy import create_engine, text

    engine = create_engine(db_url)
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "INSERT INTO annotation_runs "
                "(sample_size, model, started_at, finished_at, runtime_seconds, status) "
                "VALUES (:sample_size, :model, :started_at, :finished_at, :runtime_seconds, :status)"
            ),
            {
                "sample_size": run.sample_size,
                "model": run.model,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
                "runtime_seconds": run.runtime_seconds,
                "status": run.status,
            },
        )
        run_id = result.lastrowid  # noqa: F841
        for row in run.classifications:
            conn.execute(
                text(
                    "INSERT INTO classifications "
                    "(record_id, l1_code, l1_name, l2_code, l2_name, l3_code, l3_name, "
                    "confidence, source, polarity, ui_bucket) VALUES "
                    "(:record_id, :l1_code, :l1_name, :l2_code, :l2_name, :l3_code, :l3_name, "
                    ":confidence, :source, :polarity, :ui_bucket)"
                ),
                {
                    "record_id": row.record_id,
                    "l1_code": row.l1_code,
                    "l1_name": row.l1_name,
                    "l2_code": row.l2_code,
                    "l2_name": row.l2_name,
                    "l3_code": row.l3_code,
                    "l3_name": row.l3_name,
                    "confidence": row.confidence,
                    "source": row.source,
                    "polarity": row.polarity,
                    "ui_bucket": row.ui_bucket,
                },
            )


def _persist_metadata_to_db(db_url: str, rows: list[dict[str, Any]]) -> None:
    from sqlalchemy import create_engine, text

    engine = create_engine(db_url)
    with engine.begin() as conn:
        for r in rows:
            conn.execute(
                text(
                    "INSERT OR REPLACE INTO metadata_extractions "
                    "(record_id, personnel_named, personnel_name, personnel_polarity, "
                    "explicit_recommendation, mentions_other_bank, other_bank_names, "
                    "channels_mentioned) VALUES "
                    "(:record_id, :personnel_named, :personnel_name, :personnel_polarity, "
                    ":explicit_recommendation, :mentions_other_bank, :other_bank_names, "
                    ":channels_mentioned)"
                ),
                r,
            )


# ============================================================================
# Parser
# ============================================================================


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="engine",
        description="Motor de anotación y extracción para sentiment-analysis-banamex.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    # ------ annotate-sample ------
    sa = sub.add_parser(
        "annotate-sample",
        help="Anota una muestra estratificada con el LLM local (M2a).",
    )
    sa.add_argument("--size", type=int, default=5000)
    sa.add_argument("--seed", type=int, default=42)
    sa.add_argument("--concurrency", type=int, default=4)
    sa.add_argument("--model", type=str, default=None, help="default: $OLLAMA_MODEL")
    sa.add_argument("--db-url", type=str, default=None)
    sa.add_argument("--fixture", type=str, default=None, help="CSV de verbalizations")
    sa.add_argument("--cache-dir", type=str, default=None)
    sa.add_argument("--clear-cache", action="store_true")
    sa.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra el sample sin llamar al LLM",
    )
    sa.add_argument(
        "--skip-preflight",
        action="store_true",
        help="Salta el chequeo de Ollama (útil para tests).",
    )
    sa.add_argument(
        "--persist-db",
        action="store_true",
        help="Persiste el run y las classifications en --db-url.",
    )
    sa.set_defaults(func=cmd_annotate_sample)

    # ------ extract-metadata ------
    em = sub.add_parser(
        "extract-metadata",
        help="Aplica los 4 extractores rule-based sobre todas las verbalizations.",
    )
    em.add_argument("--db-url", type=str, default=None)
    em.add_argument("--fixture", type=str, default=None)
    em.add_argument(
        "--all",
        dest="all_records",
        action="store_true",
        help="Incluye verbalizations sin texto (has_verbatim=0).",
    )
    em.add_argument("--output", type=str, default=None, help="Ruta a CSV de salida.")
    em.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Filas a imprimir en stdout cuando no hay --output ni --db-url.",
    )
    em.set_defaults(func=cmd_extract_metadata)

    return p


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
