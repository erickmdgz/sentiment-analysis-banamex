#!/usr/bin/env python3
"""Orquestador idempotente del pipeline offline.

Ejecuta, en orden, las fases que producen `data/processed/banamex.db`
y `data/models/classifier.joblib` a partir de los corpora crudos en
`data/raw/*.txt`. Diseñado según `docs/plan_implementacion/08_M6_integracion.md`.

Fases:
    1. init_schema (M1)            — siempre, idempotente.
    2. load_corpora (M1)           — carga TSV; salta archivos cuyo sha256 ya existe.
    3. generate_targets (M1)       — genera targets sintéticos por sucursal.
    4. annotate (M2a)              — llama LLM local (requiere Ollama).
    5. train (M2b)                 — entrena clasificador sobre el golden set.
    6. predict_all (M2b)           — clasifica las verbalizations restantes.
    7. extract_metadata (M2a)      — corre los 4 extractores rule-based.
    8. summary report              — imprime tabla con totales.

Cada fase chequea si su trabajo ya está hecho antes de correr. Con `--force-*`
se fuerza la re-ejecución de una fase. `--skip-*` la omite. `--skip-classifier`
es un alias para `--skip-train --skip-predict`. `--skip-llm` es alias para
`--skip-annotation`.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW_DIR = REPO_ROOT / "data" / "raw"
DEFAULT_DB_PATH = REPO_ROOT / "data" / "processed" / "banamex.db"
DEFAULT_MODEL_PATH = REPO_ROOT / "data" / "models" / "classifier.joblib"


# ---------------------------------------------------------------------------
# Reporte
# ---------------------------------------------------------------------------


@dataclass
class PhaseResult:
    name: str
    status: str  # "done", "skipped", "already_done", "failed"
    detail: str = ""
    extra: dict = field(default_factory=dict)


def _print_phase(result: PhaseResult) -> None:
    marker = {
        "done": "✓",
        "skipped": "·",
        "already_done": "↺",
        "failed": "✗",
    }.get(result.status, "?")
    print(f"  {marker} {result.name:<22} [{result.status}]  {result.detail}")


# ---------------------------------------------------------------------------
# Conexión directa para chequeos rápidos sin cargar SQLAlchemy
# ---------------------------------------------------------------------------


def _sqlite_count(db_path: Path, sql: str) -> int | None:
    if not db_path.exists():
        return None
    try:
        with sqlite3.connect(db_path) as conn:
            return int(conn.execute(sql).fetchone()[0])
    except sqlite3.OperationalError:
        return None


# ---------------------------------------------------------------------------
# Fases
# ---------------------------------------------------------------------------


def phase_init_schema(db_path: Path) -> PhaseResult:
    os.environ["CORE_DB_PATH"] = str(db_path)
    from core.db import init_schema, reset_engine

    reset_engine()
    init_schema()
    return PhaseResult("init_schema", "done", f"db={db_path}")


def phase_load_corpora(raw_dir: Path, db_path: Path) -> PhaseResult:
    os.environ["CORE_DB_PATH"] = str(db_path)
    from core.db import reset_engine
    from core.loader import load_file

    reset_engine()
    if not raw_dir.exists():
        return PhaseResult(
            "load_corpora",
            "failed",
            f"No existe {raw_dir} — coloca los .txt en data/raw/",
        )
    files = sorted(raw_dir.glob("*.txt"))
    if not files:
        return PhaseResult(
            "load_corpora",
            "failed",
            f"No hay .txt en {raw_dir}",
        )

    total_inserted = 0
    total_duplicated = 0
    already_count = 0
    branches: set[str] = set()
    for path in files:
        report = load_file(path)
        total_inserted += report.rows_inserted
        total_duplicated += report.rows_duplicated
        if report.already_processed:
            already_count += 1
        branches.update(report.branches_detected)
    detail = (
        f"{len(files)} archivos · insertadas={total_inserted} "
        f"duplicadas={total_duplicated} ya_procesados={already_count} "
        f"sucursales={len(branches)}"
    )
    status = "already_done" if already_count == len(files) and total_inserted == 0 else "done"
    return PhaseResult("load_corpora", status, detail, {"branches": len(branches)})


def phase_generate_targets(db_path: Path, *, force: bool) -> PhaseResult:
    os.environ["CORE_DB_PATH"] = str(db_path)
    from core.db import reset_engine
    from core.targets import generate_all

    reset_engine()
    existing = _sqlite_count(db_path, "SELECT COUNT(*) FROM branch_targets") or 0
    if existing > 0 and not force:
        return PhaseResult("generate_targets", "already_done", f"{existing} targets")
    targets = generate_all(seed=42, force=force)
    return PhaseResult("generate_targets", "done", f"{len(targets)} targets")


def phase_annotate(
    db_path: Path,
    *,
    force: bool,
    size: int,
    model: str | None,
) -> PhaseResult:
    n_done = _sqlite_count(
        db_path, "SELECT COUNT(*) FROM annotation_runs WHERE status='done'"
    )
    if n_done and not force:
        return PhaseResult("annotate", "already_done", f"{n_done} runs done")

    db_url = f"sqlite:///{db_path}"
    cmd = [
        sys.executable,
        "-m",
        "engine.cli",
        "annotate-sample",
        "--size",
        str(size),
        "--seed",
        "42",
        "--db-url",
        db_url,
        "--persist-db",
    ]
    if model:
        cmd.extend(["--model", model])
    rc = subprocess.call(cmd, cwd=REPO_ROOT)
    if rc != 0:
        return PhaseResult(
            "annotate",
            "failed",
            "engine.cli annotate-sample falló — verifica Ollama (`ollama serve`, `ollama pull <model>`)",
        )
    new_count = _sqlite_count(
        db_path, "SELECT COUNT(*) FROM annotation_runs WHERE status='done'"
    ) or 0
    return PhaseResult("annotate", "done", f"runs done={new_count}")


def phase_train(
    db_path: Path,
    model_path: Path,
    *,
    force: bool,
) -> PhaseResult:
    if model_path.exists() and not force:
        return PhaseResult(
            "train",
            "already_done",
            f"{model_path} ({model_path.stat().st_size / 1e6:.1f} MB)",
        )

    last_run_id = _sqlite_count(
        db_path, "SELECT COALESCE(MAX(id),0) FROM annotation_runs WHERE status='done'"
    )
    if not last_run_id:
        return PhaseResult(
            "train",
            "failed",
            "No hay annotation_runs status=done — corre la fase annotate primero",
        )

    db_url = f"sqlite:///{db_path}"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "engine.cli",
        "train",
        "--annotation-run-id",
        str(last_run_id),
        "--db-url",
        db_url,
        "--model-path",
        str(model_path),
    ]
    rc = subprocess.call(cmd, cwd=REPO_ROOT)
    if rc != 0:
        return PhaseResult("train", "failed", "engine.cli train falló")
    return PhaseResult("train", "done", f"trained on run_id={last_run_id}")


def phase_predict_all(
    db_path: Path,
    model_path: Path,
    *,
    force: bool,
) -> PhaseResult:
    if not model_path.exists():
        return PhaseResult(
            "predict_all", "failed", f"No existe {model_path} — corre train primero"
        )

    pending = _sqlite_count(
        db_path,
        "SELECT COUNT(*) FROM verbalizations v "
        "LEFT JOIN classifications c ON v.record_id = c.record_id "
        "WHERE c.id IS NULL",
    ) or 0
    if pending == 0 and not force:
        return PhaseResult("predict_all", "already_done", "0 pendientes")

    db_url = f"sqlite:///{db_path}"
    cmd = [
        sys.executable,
        "-m",
        "engine.cli",
        "predict-all",
        "--db-url",
        db_url,
        "--model-path",
        str(model_path),
    ]
    rc = subprocess.call(cmd, cwd=REPO_ROOT)
    if rc != 0:
        return PhaseResult("predict_all", "failed", "engine.cli predict-all falló")
    return PhaseResult("predict_all", "done", f"procesadas≈{pending}")


def phase_extract_metadata(db_path: Path, *, force: bool) -> PhaseResult:
    pending = _sqlite_count(
        db_path,
        "SELECT COUNT(*) FROM verbalizations v "
        "LEFT JOIN metadata_extractions m ON v.record_id = m.record_id "
        "WHERE v.has_verbatim = 1 AND m.record_id IS NULL",
    )
    if pending is not None and pending == 0 and not force:
        return PhaseResult("extract_metadata", "already_done", "0 pendientes")

    db_url = f"sqlite:///{db_path}"
    cmd = [
        sys.executable,
        "-m",
        "engine.cli",
        "extract-metadata",
        "--db-url",
        db_url,
    ]
    rc = subprocess.call(cmd, cwd=REPO_ROOT)
    if rc != 0:
        return PhaseResult("extract_metadata", "failed", "engine.cli extract-metadata falló")
    return PhaseResult("extract_metadata", "done", f"procesadas≈{pending or 0}")


# ---------------------------------------------------------------------------
# Reporte final
# ---------------------------------------------------------------------------


def final_report(db_path: Path) -> dict:
    if not db_path.exists():
        return {"db_exists": False}
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()

        def scalar(sql: str) -> int:
            try:
                return int(cur.execute(sql).fetchone()[0])
            except sqlite3.OperationalError:
                return 0

        total = scalar("SELECT COUNT(*) FROM verbalizations")
        sources: dict[str, int] = {}
        try:
            for src, n in cur.execute(
                "SELECT source, COUNT(*) FROM classifications GROUP BY source"
            ):
                sources[src] = int(n)
        except sqlite3.OperationalError:
            pass
        with_meta = scalar("SELECT COUNT(*) FROM metadata_extractions")
        branches = scalar("SELECT COUNT(DISTINCT branch_id) FROM verbalizations")
        date_min = ""
        date_max = ""
        try:
            row = cur.execute(
                "SELECT MIN(response_date), MAX(response_date) FROM verbalizations"
            ).fetchone()
            date_min, date_max = (row[0] or ""), (row[1] or "")
        except sqlite3.OperationalError:
            pass
        months = scalar(
            "SELECT COUNT(DISTINCT substr(response_date,1,7)) FROM verbalizations"
        )
    total_classified = sum(sources.values()) or 0
    coverage = (total_classified / total * 100.0) if total else 0.0
    return {
        "db_exists": True,
        "verbalizations": total,
        "classifications_by_source": sources,
        "metadata_extractions": with_meta,
        "branches": branches,
        "date_range": (date_min, date_max),
        "months": months,
        "coverage_pct": round(coverage, 2),
    }


def print_report_table(report: dict) -> None:
    print()
    print("─" * 60)
    print("  Reporte final")
    print("─" * 60)
    if not report.get("db_exists"):
        print("  DB no existe — nada que reportar.")
        return
    print(f"  Verbalizaciones totales:      {report['verbalizations']:>10,}")
    print(f"  Clasificadas por fuente:")
    for src, n in sorted(report["classifications_by_source"].items()):
        print(f"      {src:<20} {n:>10,}")
    print(f"  Con metadata extraída:        {report['metadata_extractions']:>10,}")
    print(f"  Cobertura clasificación:      {report['coverage_pct']:>10.2f} %")
    print(f"  Sucursales detectadas:        {report['branches']:>10,}")
    print(f"  Meses cubiertos:              {report['months']:>10,}")
    print(
        f"  Rango de fechas:              "
        f"{report['date_range'][0]} → {report['date_range'][1]}"
    )
    print("─" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="preprocess_corpora",
        description="Orquesta el pipeline offline M1→M2a→M2b. Idempotente.",
    )
    p.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    p.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    p.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    p.add_argument("--annotate-size", type=int, default=5000)
    p.add_argument(
        "--annotate-model",
        type=str,
        default=None,
        help="Modelo de Ollama (default: $OLLAMA_MODEL del entorno)",
    )
    p.add_argument("--format", choices=("table", "json"), default="table")

    # Skip flags
    p.add_argument("--skip-load", action="store_true")
    p.add_argument("--skip-targets", action="store_true")
    p.add_argument("--skip-annotation", "--skip-annotate", action="store_true")
    p.add_argument("--skip-llm", action="store_true", help="Alias de --skip-annotation")
    p.add_argument("--skip-train", action="store_true")
    p.add_argument("--skip-predict", action="store_true")
    p.add_argument(
        "--skip-classifier",
        action="store_true",
        help="Alias de --skip-train --skip-predict",
    )
    p.add_argument("--skip-metadata", action="store_true")

    # Force flags
    p.add_argument("--force-targets", action="store_true")
    p.add_argument("--force-annotate", action="store_true")
    p.add_argument("--force-train", action="store_true")
    p.add_argument("--force-predict", action="store_true")
    p.add_argument("--force-metadata", action="store_true")
    p.add_argument(
        "--force-all",
        action="store_true",
        help="Equivale a --force-targets --force-annotate --force-train --force-predict --force-metadata",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.force_all:
        args.force_targets = True
        args.force_annotate = True
        args.force_train = True
        args.force_predict = True
        args.force_metadata = True
    if args.skip_llm:
        args.skip_annotation = True
    if args.skip_classifier:
        args.skip_train = True
        args.skip_predict = True

    db_path: Path = args.db_path.resolve()
    model_path: Path = args.model_path.resolve()
    raw_dir: Path = args.raw_dir.resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    print("─" * 60)
    print("  preprocess_corpora — pipeline offline")
    print("─" * 60)
    print(f"  raw_dir   : {raw_dir}")
    print(f"  db_path   : {db_path}")
    print(f"  model_path: {model_path}")
    print()

    results: list[PhaseResult] = []

    def run(label: str, fn: Callable[[], PhaseResult]) -> bool:
        result = fn()
        result.name = label
        _print_phase(result)
        results.append(result)
        return result.status != "failed"

    if not run("init_schema", lambda: phase_init_schema(db_path)):
        return _finalize(results, args, db_path, exit_code=1)

    if args.skip_load:
        results.append(PhaseResult("load_corpora", "skipped"))
        _print_phase(results[-1])
    else:
        if not run("load_corpora", lambda: phase_load_corpora(raw_dir, db_path)):
            return _finalize(results, args, db_path, exit_code=1)

    if args.skip_targets:
        results.append(PhaseResult("generate_targets", "skipped"))
        _print_phase(results[-1])
    else:
        run(
            "generate_targets",
            lambda: phase_generate_targets(db_path, force=args.force_targets),
        )

    if args.skip_annotation:
        results.append(PhaseResult("annotate", "skipped"))
        _print_phase(results[-1])
    else:
        run(
            "annotate",
            lambda: phase_annotate(
                db_path,
                force=args.force_annotate,
                size=args.annotate_size,
                model=args.annotate_model,
            ),
        )

    if args.skip_train:
        results.append(PhaseResult("train", "skipped"))
        _print_phase(results[-1])
    else:
        run(
            "train",
            lambda: phase_train(db_path, model_path, force=args.force_train),
        )

    if args.skip_predict:
        results.append(PhaseResult("predict_all", "skipped"))
        _print_phase(results[-1])
    else:
        run(
            "predict_all",
            lambda: phase_predict_all(db_path, model_path, force=args.force_predict),
        )

    if args.skip_metadata:
        results.append(PhaseResult("extract_metadata", "skipped"))
        _print_phase(results[-1])
    else:
        run(
            "extract_metadata",
            lambda: phase_extract_metadata(db_path, force=args.force_metadata),
        )

    return _finalize(results, args, db_path, exit_code=0)


def _finalize(
    results: list[PhaseResult],
    args: argparse.Namespace,
    db_path: Path,
    *,
    exit_code: int,
) -> int:
    report = final_report(db_path)
    if args.format == "json":
        print(
            json.dumps(
                {
                    "phases": [
                        {"name": r.name, "status": r.status, "detail": r.detail}
                        for r in results
                    ],
                    "report": report,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print_report_table(report)
    failed = [r for r in results if r.status == "failed"]
    if failed:
        return max(exit_code, 1)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
