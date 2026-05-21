"""Tests del loader y del init de schema. Cubren §13 (8), (9), (12), (13) del plan M1."""

from __future__ import annotations

import io
import csv
from pathlib import Path

import pytest
from sqlalchemy import text

from core.db import get_engine, init_schema
from core.loader import file_sha256, load_file


def _make_tsv(path: Path, rows: list[list[str]]) -> Path:
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter="\t", quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    for row in rows:
        writer.writerow(row)
    path.write_bytes(buf.getvalue().encode("latin-1"))
    return path


def test_init_schema_es_idempotente(temp_db: Path) -> None:
    init_schema()
    init_schema()  # segunda llamada no debe levantar
    engine = get_engine()
    with engine.connect() as conn:
        names = {r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
    assert {
        "files",
        "verbalizations",
        "branches",
        "branch_targets",
        "classifications",
        "metadata_extractions",
        "annotation_runs",
        "classifier_runs",
    }.issubset(names)


def test_init_schema_crea_archivo_default_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "explicit.db"
    monkeypatch.setenv("CORE_DB_PATH", str(target))
    from core import db as core_db
    core_db.reset_engine()
    init_schema()
    assert target.exists()
    core_db.reset_engine()


def test_fixture_sample_se_carga_sin_errores(temp_db: Path, fixtures_dir: Path) -> None:
    report = load_file(fixtures_dir / "sample.tsv")
    assert report.rows_total == 100
    assert report.rows_invalid == 0
    assert report.rows_inserted == 100
    assert report.rows_duplicated == 0
    assert len(report.branches_detected) > 0
    assert len(report.months_available) > 0


def test_cargar_mismo_archivo_dos_veces(temp_db: Path, fixtures_dir: Path) -> None:
    first = load_file(fixtures_dir / "sample.tsv")
    assert first.rows_inserted == 100
    assert first.already_processed is False

    second = load_file(fixtures_dir / "sample.tsv")
    assert second.rows_total == 100
    assert second.rows_inserted == 0
    assert second.rows_duplicated == second.rows_total
    assert second.already_processed is True
    # file_id es el mismo (no se duplica la fila en files)
    assert second.file_id == first.file_id
    engine = get_engine()
    with engine.connect() as conn:
        nfiles = conn.execute(text("SELECT COUNT(*) FROM files")).scalar()
        nverb = conn.execute(text("SELECT COUNT(*) FROM verbalizations")).scalar()
    assert nfiles == 1
    assert nverb == 100


def test_cargar_archivos_con_overlap_parcial(temp_db: Path, tmp_path: Path) -> None:
    # Archivo A: REC-1..REC-10
    a = _make_tsv(
        tmp_path / "a.tsv",
        [
            [f"REC-{i}", "01/01/2025", "Promotor", "10", f"texto {i}", "A-1"]
            for i in range(1, 11)
        ],
    )
    # Archivo B: REC-6..REC-15 → 50% overlap
    b = _make_tsv(
        tmp_path / "b.tsv",
        [
            [f"REC-{i}", "02/01/2025", "Detractor", "3", f"otro {i}", "A-2"]
            for i in range(6, 16)
        ],
    )
    ra = load_file(a)
    assert ra.rows_inserted == 10
    assert ra.rows_duplicated == 0

    rb = load_file(b)
    assert rb.rows_total == 10
    assert rb.rows_inserted == 5  # REC-11..REC-15
    assert rb.rows_duplicated == 5  # REC-6..REC-10 ya estaban


def test_dedup_intra_archivo_de_record_id(temp_db: Path, tmp_path: Path) -> None:
    # Mismo record_id repetido dentro del archivo → segunda ocurrencia es duplicado
    p = _make_tsv(
        tmp_path / "dup.tsv",
        [
            ["REC-1", "01/01/2025", "Promotor", "10", "primera", "A-1"],
            ["REC-1", "02/01/2025", "Detractor", "3", "segunda", "A-1"],
            ["REC-2", "03/01/2025", "Pasivo", "7", "otra", "A-2"],
        ],
    )
    r = load_file(p)
    assert r.rows_total == 3
    assert r.rows_inserted == 2
    assert r.rows_duplicated == 1
    assert r.rows_invalid == 0


def test_sha256_se_computa_y_es_unico(temp_db: Path, fixtures_dir: Path) -> None:
    sha = file_sha256(fixtures_dir / "sample.tsv")
    assert len(sha) == 64
    load_file(fixtures_dir / "sample.tsv")
    engine = get_engine()
    with engine.connect() as conn:
        stored = conn.execute(text("SELECT sha256 FROM files")).scalar()
    assert stored == sha


def test_load_report_rangos_de_fecha_y_meses(temp_db: Path, tmp_path: Path) -> None:
    p = _make_tsv(
        tmp_path / "dates.tsv",
        [
            ["REC-1", "15/01/2025", "Promotor", "10", "x", "A-1"],
            ["REC-2", "20/03/2025", "Detractor", "3", "y", "A-2"],
            ["REC-3", "01/06/2025", "Pasivo", "7", "z", "A-3"],
        ],
    )
    r = load_file(p)
    assert r.date_range == ("2025-01-15", "2025-06-01")
    assert r.months_available == ["2025-01", "2025-03", "2025-06"]


def test_branches_se_insertan_con_ignore(temp_db: Path, tmp_path: Path) -> None:
    p = _make_tsv(
        tmp_path / "br.tsv",
        [
            ["REC-1", "01/01/2025", "Promotor", "10", "x", "A-1"],
            ["REC-2", "02/01/2025", "Promotor", "10", "y", "A-1"],
            ["REC-3", "03/01/2025", "Detractor", "3", "z", "A-2"],
        ],
    )
    load_file(p)
    engine = get_engine()
    with engine.connect() as conn:
        names = {r[0] for r in conn.execute(text("SELECT branch_id FROM branches")).all()}
    assert names == {"A-1", "A-2"}
