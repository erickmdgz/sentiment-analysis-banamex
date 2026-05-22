"""CLI del paquete engine.

Subcomandos M2a:
    annotate-sample    Anota una muestra estratificada con el LLM local.
    extract-metadata   Corre los 4 extractores rule-based sobre todas
                       las verbalizaciones sin metadata.

Subcomandos M2b:
    train              Entrena el clasificador supervisado sobre el golden set
                       de una corrida de anotación y persiste el `.joblib`.
    predict-all        Corre el clasificador sobre toda verbalization sin
                       clasificación previa (batches de 1000).
    predict-one        Utilidad de debug: clasifica un texto suelto y lo
                       imprime como JSON.

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
import time
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
# Subcomandos M2b
# ============================================================================


def cmd_train(args: argparse.Namespace) -> int:
    """Entrena el clasificador supervisado sobre el golden set."""
    from . import trainer

    engine_obj = _build_db_engine(args.db_url)
    model_path = Path(args.model_path) if args.model_path else None
    run = trainer.train(
        annotation_run_id=args.annotation_run_id,
        seed=args.seed,
        engine=engine_obj,
        model_path=model_path,
    )
    print(
        json.dumps(
            {
                "classifier_run_id": run.id,
                "model_path": run.model_path,
                "trained_on_run_id": run.trained_on_run_id,
                "trained_at": run.trained_at,
                "n_samples": run.n_samples,
                "n_labels": run.n_labels,
                "n_samples_train": run.n_samples_train,
                "n_samples_test": run.n_samples_test,
                "f1_micro": run.f1_micro,
                "f1_macro": run.f1_macro,
                "hamming_loss": run.hamming_loss,
                "subset_accuracy": run.subset_accuracy,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_predict_all(args: argparse.Namespace) -> int:
    """Clasifica todas las verbalizations sin fila en `classifications`."""
    from sqlalchemy import text as sql_text

    from .classifier import Classifier, get_default_classifier

    engine_obj = _build_db_engine(args.db_url)
    model_path = Path(args.model_path) if args.model_path else None
    if model_path is not None:
        classifier = Classifier.load(model_path)
    else:
        classifier = get_default_classifier()

    batch_size = args.batch_size
    report_every = args.report_every

    pending_query = (
        "SELECT v.record_id, v.verbatim_clean, v.nps_group "
        "FROM verbalizations v "
        "LEFT JOIN classifications c ON v.record_id = c.record_id "
        "WHERE c.id IS NULL "
        "ORDER BY v.record_id"
    )

    with engine_obj.connect() as conn:
        total_pending = conn.execute(
            sql_text(
                "SELECT COUNT(*) FROM verbalizations v "
                "LEFT JOIN classifications c ON v.record_id = c.record_id "
                "WHERE c.id IS NULL"
            )
        ).scalar_one()

    print(f"# pendientes: {total_pending}")

    processed = 0
    start = time.time()
    with engine_obj.connect() as conn:
        result = conn.execution_options(stream_results=True).execute(sql_text(pending_query))
        batch: list[tuple[str, str, str]] = []
        for record_id, verbatim_clean, nps_group in result:
            batch.append((record_id, verbatim_clean or "", nps_group))
            if len(batch) >= batch_size:
                _process_batch(batch, classifier, engine_obj)
                processed += len(batch)
                batch = []
                if processed % report_every == 0:
                    _log_progress(processed, total_pending, start)
        if batch:
            _process_batch(batch, classifier, engine_obj)
            processed += len(batch)
            _log_progress(processed, total_pending, start)

    elapsed = time.time() - start
    print(
        json.dumps(
            {
                "processed": processed,
                "elapsed_seconds": round(elapsed, 1),
                "throughput_per_sec": round(processed / elapsed, 1) if elapsed > 0 else 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _process_batch(batch: list[tuple[str, str, str]], classifier: Any, engine_obj: Any) -> None:
    from .pipeline import classify_batch, persist_classification

    results = classify_batch(batch, classifier=classifier)
    for result in results:
        persist_classification(result, engine=engine_obj)


def _log_progress(processed: int, total: int, start: float) -> None:
    elapsed = max(time.time() - start, 1e-6)
    rate = processed / elapsed
    remaining = max(total - processed, 0)
    eta = remaining / rate if rate > 0 else float("inf")
    print(
        f"[{processed}/{total}] {processed / max(total, 1) * 100:5.1f}% "
        f"throughput={rate:6.1f} rec/s ETA={eta / 60:6.1f} min"
    )


def cmd_predict_one(args: argparse.Namespace) -> int:
    """Clasifica un solo texto pasado por CLI (debug)."""
    from .classifier import Classifier, get_default_classifier
    from .pipeline import classify

    if args.model_path:
        classifier = Classifier.load(args.model_path)
    else:
        classifier = get_default_classifier()
    result = classify(
        record_id=args.record_id,
        text=args.text,
        nps_group=args.nps_group,
        classifier=classifier,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _build_db_engine(db_url: str | None):  # noqa: ANN202
    """Construye un engine SQLAlchemy. Usa `core.db.get_engine()` si no se pasa URL."""
    if db_url:
        from sqlalchemy import create_engine

        return create_engine(db_url)
    from core.db import get_engine

    return get_engine()


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

    # ------ train (M2b) ------
    tr = sub.add_parser(
        "train",
        help="Entrena el clasificador supervisado sobre el golden set (M2b).",
    )
    tr.add_argument(
        "--annotation-run-id",
        type=int,
        default=None,
        help="ID en annotation_runs para trazabilidad (clasificator_runs.trained_on_run_id).",
    )
    tr.add_argument("--seed", type=int, default=42)
    tr.add_argument("--db-url", type=str, default=None)
    tr.add_argument(
        "--model-path",
        type=str,
        default=None,
        help="Ruta destino del .joblib. Default: data/models/classifier.joblib.",
    )
    tr.set_defaults(func=cmd_train)

    # ------ predict-all (M2b) ------
    pa = sub.add_parser(
        "predict-all",
        help="Clasifica toda verbalization sin fila en classifications (M2b).",
    )
    pa.add_argument("--db-url", type=str, default=None)
    pa.add_argument(
        "--model-path",
        type=str,
        default=None,
        help="Ruta al .joblib. Default: el singleton de engine.classifier.",
    )
    pa.add_argument("--batch-size", type=int, default=1000)
    pa.add_argument("--report-every", type=int, default=10000)
    pa.set_defaults(func=cmd_predict_all)

    # ------ predict-one (M2b) ------
    po = sub.add_parser(
        "predict-one",
        help="Clasifica un texto individual (debug).",
    )
    po.add_argument("--text", type=str, required=True)
    po.add_argument(
        "--nps-group",
        type=str,
        required=True,
        choices=("Promotor", "Pasivo", "Detractor"),
    )
    po.add_argument("--record-id", type=str, default="debug-1")
    po.add_argument("--model-path", type=str, default=None)
    po.set_defaults(func=cmd_predict_one)

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
