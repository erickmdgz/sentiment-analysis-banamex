"""Carga incremental de TSV a SQLite con deduplicación.

Estrategia:
1. ``sha256`` del archivo → llave única en ``files``. Si ya existe, devuelve
   ``LoadReport`` con ``rows_inserted=0``, ``rows_duplicated=rows_total``.
2. ``parse_tsv`` produce filas válidas e inválidas. Las inválidas se cuentan.
3. Dedup por ``record_id``: las que ya existen en la DB o se repiten dentro
   del archivo cuentan como duplicadas (no se insertan).
4. ``branches_detected`` se llena con ``INSERT OR IGNORE INTO branches``.
5. ``LoadReport`` se construye con los conteos finales y los rangos de fecha.

Para 100K+ filas se hacen inserts en lotes de ``_INSERT_BATCH`` con una
sola transacción por carga.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Connection

from .db import get_engine, init_schema
from .parser import ParsedRow, parse_tsv
from .schemas import LoadReport

_LOOKUP_CHUNK = 500
_INSERT_BATCH = 1000


def file_sha256(path: Path) -> str:
    """Hash sha256 del archivo, leído en chunks de 64KB."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _existing_record_ids(conn: Connection, record_ids: Iterable[str]) -> set[str]:
    record_ids = list(record_ids)
    if not record_ids:
        return set()
    existing: set[str] = set()
    for i in range(0, len(record_ids), _LOOKUP_CHUNK):
        chunk = record_ids[i : i + _LOOKUP_CHUNK]
        placeholders = ",".join(f":r{j}" for j in range(len(chunk)))
        params = {f"r{j}": rid for j, rid in enumerate(chunk)}
        rows = conn.execute(
            text(f"SELECT record_id FROM verbalizations WHERE record_id IN ({placeholders})"),
            params,
        ).all()
        existing.update(r[0] for r in rows)
    return existing


def _insert_branches(conn: Connection, branch_ids: Iterable[str]) -> None:
    branches = sorted(set(branch_ids))
    if not branches:
        return
    conn.execute(
        text("INSERT OR IGNORE INTO branches (branch_id) VALUES (:bid)"),
        [{"bid": b} for b in branches],
    )


def _insert_verbalizations(conn: Connection, rows: list[ParsedRow], file_id: int) -> None:
    if not rows:
        return
    sql = text(
        """
        INSERT INTO verbalizations (
            record_id, file_id, response_date, response_year, response_month,
            nps_group, nps_rate, verbatim, verbatim_clean, branch_id, has_verbatim
        ) VALUES (
            :record_id, :file_id, :response_date, :response_year, :response_month,
            :nps_group, :nps_rate, :verbatim, :verbatim_clean, :branch_id, :has_verbatim
        )
        """
    )
    for i in range(0, len(rows), _INSERT_BATCH):
        batch = rows[i : i + _INSERT_BATCH]
        params = []
        for pr in batch:
            assert pr.row is not None and pr.response_date_iso is not None
            year, month = int(pr.response_date_iso[:4]), int(pr.response_date_iso[5:7])
            params.append(
                {
                    "record_id": pr.row.record_id,
                    "file_id": file_id,
                    "response_date": pr.response_date_iso,
                    "response_year": year,
                    "response_month": month,
                    "nps_group": pr.row.nps_group,
                    "nps_rate": pr.row.nps_rate,
                    "verbatim": pr.row.verbatim,
                    "verbatim_clean": pr.verbatim_clean,
                    "branch_id": pr.row.branch_id,
                    "has_verbatim": 1 if pr.row.verbatim and pr.row.verbatim.strip() else 0,
                }
            )
        conn.execute(sql, params)


def _months_from_dates(dates: Iterable[str]) -> list[str]:
    return sorted({d[:7] for d in dates})


def _build_report_for_existing(conn: Connection, file_id: int, filename: str) -> LoadReport:
    row = conn.execute(
        text(
            """
            SELECT rows_total, rows_inserted, rows_duplicated, rows_invalid
            FROM files WHERE id = :id
            """
        ),
        {"id": file_id},
    ).one()
    rows_total = int(row[0])
    rows_invalid = int(row[3])
    branches = [
        b[0]
        for b in conn.execute(
            text("SELECT DISTINCT branch_id FROM verbalizations WHERE file_id = :id ORDER BY branch_id"),
            {"id": file_id},
        ).all()
    ]
    dates = [
        d[0]
        for d in conn.execute(
            text("SELECT response_date FROM verbalizations WHERE file_id = :id"),
            {"id": file_id},
        ).all()
    ]
    if dates:
        date_range = (min(dates), max(dates))
        months = _months_from_dates(dates)
    else:
        date_range = ("", "")
        months = []
    return LoadReport(
        file_id=file_id,
        filename=filename,
        rows_total=rows_total,
        rows_inserted=0,
        rows_duplicated=rows_total,
        rows_invalid=rows_invalid,
        branches_detected=branches,
        date_range=date_range,
        months_available=months,
    )


def load_file(path: Path) -> LoadReport:
    """Carga un TSV en la DB y devuelve un ``LoadReport``.

    Idempotente a nivel archivo: si el ``sha256`` ya existe en ``files``,
    no se reinserta nada y el reporte refleja ``rows_inserted=0``.
    """
    path = Path(path)
    init_schema()
    engine = get_engine()
    sha = file_sha256(path)
    filename = path.name

    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id FROM files WHERE sha256 = :sha"), {"sha": sha}
        ).one_or_none()
        if existing is not None:
            return _build_report_for_existing(conn, int(existing[0]), filename)

    # Parsear todo el archivo en memoria (manejable: <500K filas por corpus).
    valid_rows: list[ParsedRow] = []
    rows_total = 0
    rows_invalid = 0
    for pr in parse_tsv(path):
        rows_total += 1
        if pr.is_valid:
            valid_rows.append(pr)
        else:
            rows_invalid += 1

    with engine.begin() as conn:
        existing_ids = _existing_record_ids(
            conn, (pr.row.record_id for pr in valid_rows if pr.row is not None)
        )
        seen_in_file: set[str] = set()
        to_insert: list[ParsedRow] = []
        for pr in valid_rows:
            assert pr.row is not None
            rid = pr.row.record_id
            if rid in existing_ids or rid in seen_in_file:
                continue
            seen_in_file.add(rid)
            to_insert.append(pr)

        rows_inserted = len(to_insert)
        rows_duplicated = len(valid_rows) - rows_inserted

        file_id = int(
            conn.execute(
                text(
                    """
                    INSERT INTO files (filename, sha256, rows_total, rows_inserted,
                                       rows_duplicated, rows_invalid)
                    VALUES (:filename, :sha, :rt, :ri, :rd, :rinv)
                    """
                ),
                {
                    "filename": filename,
                    "sha": sha,
                    "rt": rows_total,
                    "ri": rows_inserted,
                    "rd": rows_duplicated,
                    "rinv": rows_invalid,
                },
            ).lastrowid
        )

        _insert_branches(conn, (pr.row.branch_id for pr in valid_rows if pr.row is not None))
        _insert_verbalizations(conn, to_insert, file_id)

        branches_detected = sorted({pr.row.branch_id for pr in valid_rows if pr.row is not None})
        dates = [pr.response_date_iso for pr in valid_rows if pr.response_date_iso]
        if dates:
            date_range = (min(dates), max(dates))
            months = _months_from_dates(dates)
        else:
            date_range = ("", "")
            months = []

    return LoadReport(
        file_id=file_id,
        filename=filename,
        rows_total=rows_total,
        rows_inserted=rows_inserted,
        rows_duplicated=rows_duplicated,
        rows_invalid=rows_invalid,
        branches_detected=branches_detected,
        date_range=date_range,
        months_available=months,
    )


__all__ = ["file_sha256", "load_file"]
