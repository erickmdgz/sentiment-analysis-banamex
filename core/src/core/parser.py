"""Parser TSV con encoding ``latin-1``.

Los TSV de Banamex vienen en ISO-8859 (latin-1). Se leen con
``open(path, encoding='latin-1', newline='')`` y el módulo ``csv``
maneja line terminators LF/CRLF/NEL gracias a ``newline=''``.

Schema esperado de cada fila (6 columnas separadas por TAB):

    0. record_id
    1. response_date         (DD/MM/YYYY o MM/DD/YYYY)
    2. nps_group             ('Promotor' | 'Pasivo' | 'Detractor')
    3. nps_rate              (entero 0..10)
    4. verbatim              (puede contener tabs accidentales)
    5. branch_id

Si una fila trae más de 6 columnas (tabs accidentales dentro del verbatim),
las columnas ``4..-2`` se unen como verbatim, preservando ``branch_id`` en
``-1``. Si trae menos de 6, se marca inválida.

El parser yield-ea objetos ``ParsedRow``: la versión válida lleva un
``VerbalizationRow`` (DTO público) más campos derivados que el loader
necesita (``response_date_iso``, ``verbatim_clean``); la inválida lleva
``error`` con el motivo y se cuenta en ``rows_invalid``.

Nota de contrato: ``02_M1_datos.md`` declara ``parse_tsv -> Iterator[VerbalizationRow]``,
pero la propia spec exige reportar filas inválidas (no descartarlas en
silencio). Devolver ``ParsedRow`` permite esa contabilidad sin romper el
DTO público; el detalle se anota en ``docs/plan_implementacion/contracts_issues.md``.
"""

from __future__ import annotations

import csv
import io
import re
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast

from .schemas import NPSGroup, VerbalizationRow

VALID_NPS_GROUPS: frozenset[str] = frozenset({"Promotor", "Pasivo", "Detractor"})

_DATE_FMT_DMY = "%d/%m/%Y"
_DATE_FMT_MDY = "%m/%d/%Y"
_DATE_SAMPLE_SIZE = 100
_WS_RE = re.compile(r"\s+")
_DATE_RE = re.compile(r"^\s*(\d{1,2})/(\d{1,2})/\d{2,4}\s*$")

# Orden de columnas. La fixture sintética de M1 (sample.tsv) usa el orden
# "record_id-first"; los corpora reales de Banamex usan el orden "date-first"
# con un header. El parser detecta automáticamente cuál es y skipea header
# cuando aplique. Ver `contracts_issues.md` entrada 2026-05-21 (M6) sobre
# discrepancia en orden de columnas entre fixture y datos reales.
_ORDER_RECORD_FIRST = ("record_id", "date", "nps_group", "nps_rate", "verbatim", "branch_id")
_ORDER_DATE_FIRST = ("date", "nps_group", "nps_rate", "verbatim", "record_id", "branch_id")
_HEADER_TOKENS = {
    "fecha", "fecha respuesta", "fecha_respuesta",
    "recordid", "record_id", "id_record",
    "nps_group", "nps_rate", "nps",
    "verbalizacion", "verbatim",
    "id_branch", "branch", "branch_id",
}


@dataclass(slots=True)
class ParsedRow:
    """Resultado de parsear una línea del TSV.

    Si ``is_valid`` es ``True``, ``row``/``response_date_iso``/``verbatim_clean``
    están poblados. Si es ``False``, ``error`` lleva una descripción breve.
    """

    row_num: int
    is_valid: bool
    error: str | None = None
    row: VerbalizationRow | None = None
    response_date_iso: str | None = None
    verbatim_clean: str | None = None


def _detect_date_format(sample_dates: list[str]) -> str:
    first_over_12 = False
    second_over_12 = False
    for d in sample_dates:
        m = _DATE_RE.match(d)
        if not m:
            continue
        a, b = int(m.group(1)), int(m.group(2))
        if a > 12:
            first_over_12 = True
        if b > 12:
            second_over_12 = True
    if first_over_12:
        return _DATE_FMT_DMY
    if second_over_12:
        return _DATE_FMT_MDY
    return _DATE_FMT_DMY


def _read_normalized(path: Path) -> str:
    """Lee el archivo en latin-1 y normaliza NEL (U+0085) a ``\\n``.

    El módulo ``csv`` maneja LF/CRLF de forma nativa con ``newline=''``,
    pero **no** trata NEL como terminator. Como NEL aparece (raro pero
    posible) en los corpora reales — y la spec exige tolerarlo — se
    pre-procesa aquí antes de feed al reader.
    """
    text_content = path.read_text(encoding="latin-1")
    return text_content.replace("", "\n")


def _is_header_row(row: list[str]) -> bool:
    """Heurística: una fila es header si todos sus tokens (lower, stripped)
    coinciden con tokens conocidos de header, y ningún campo parece dato real
    (sin dígitos, sin record_id reconocible).
    """
    if not row:
        return False
    norm = [c.strip().lower() for c in row]
    if any(_DATE_RE.match(c) for c in norm):
        return False
    return all(c in _HEADER_TOKENS for c in norm if c)


def _detect_order(rows_sample: list[list[str]]) -> tuple[int, int]:
    """Devuelve ``(verbatim_idx, fixed_tail_len)`` según el orden detectado.

    Si la columna 0 luce fecha (DD/MM/YYYY o MM/DD/YYYY) en la mayoría de filas
    del sample → orden "date-first" (corpora reales): verbatim en idx 3,
    cola fija de 2 (record_id, branch_id). De lo contrario → orden
    "record_id-first" (fixture sintética): verbatim en idx 4, cola fija de 1
    (branch_id).
    """
    if not rows_sample:
        return 4, 1
    date_first = 0
    for r in rows_sample:
        if r and _DATE_RE.match(r[0]):
            date_first += 1
    if date_first * 2 >= len(rows_sample):  # mayoría
        return 3, 2
    return 4, 1


def _scan_corpus(path: Path) -> tuple[int, int, bool]:
    """Pre-scan: determina ``(verbatim_idx, fixed_tail_len, has_header)``.

    Lee hasta ``_DATE_SAMPLE_SIZE`` filas; ignora la primera si parece header.
    """
    reader = csv.reader(io.StringIO(_read_normalized(path)), delimiter="\t", quoting=csv.QUOTE_MINIMAL)
    first_row: list[str] | None = None
    samples: list[list[str]] = []
    for raw in reader:
        if first_row is None:
            first_row = raw
            continue
        if raw:
            samples.append(raw)
        if len(samples) >= _DATE_SAMPLE_SIZE:
            break
    has_header = bool(first_row) and _is_header_row(first_row)
    if not has_header and first_row is not None:
        samples.insert(0, first_row)
    verbatim_idx, fixed_tail_len = _detect_order(samples[:_DATE_SAMPLE_SIZE])
    return verbatim_idx, fixed_tail_len, has_header


def _detect_date_format_from_file(
    path: Path, verbatim_idx: int, fixed_tail_len: int, has_header: bool
) -> str:
    """Resuelve el formato de fecha. ``date_col`` es ``0`` si es date-first
    o ``1`` si es record-first."""
    samples: list[str] = []
    date_col = 0 if (verbatim_idx == 3) else 1
    reader = csv.reader(io.StringIO(_read_normalized(path)), delimiter="\t", quoting=csv.QUOTE_MINIMAL)
    skipped = False
    for raw in reader:
        if has_header and not skipped:
            skipped = True
            continue
        row = _coerce_to_six_columns(raw, verbatim_idx, fixed_tail_len)
        if row is None or len(row) <= date_col:
            continue
        if row[date_col].strip():
            samples.append(row[date_col])
        if len(samples) >= _DATE_SAMPLE_SIZE:
            break
    return _detect_date_format(samples)


def _coerce_to_six_columns(
    row: list[str], verbatim_idx: int = 4, fixed_tail_len: int = 1
) -> list[str] | None:
    """Devuelve una fila de exactamente 6 columnas o ``None`` si imposible.

    Si la fila trae más de 6 columnas, une las posiciones desde
    ``verbatim_idx`` hasta ``-fixed_tail_len`` (exclusivo) con TAB como
    verbatim y preserva los últimos ``fixed_tail_len`` campos. ``verbatim_idx``
    es 4 / ``fixed_tail_len`` 1 para el orden "record_id-first" (fixture);
    ``verbatim_idx`` 3 / ``fixed_tail_len`` 2 para el orden "date-first" de
    los corpora reales (record_id y branch_id al final).
    """
    if len(row) < 6:
        return None
    if len(row) == 6:
        return row
    head = row[:verbatim_idx]
    tail = row[-fixed_tail_len:]
    verbatim = "\t".join(row[verbatim_idx : -fixed_tail_len])
    return [*head, verbatim, *tail]


def _parse_date(date_str: str, fmt: str) -> str | None:
    try:
        dt = datetime.strptime(date_str.strip(), fmt)
    except ValueError:
        return None
    return dt.strftime("%Y-%m-%d")


def _clean_verbatim(s: str) -> str:
    s = unicodedata.normalize("NFC", s.strip())
    return _WS_RE.sub(" ", s)


def _normalize_row(
    raw: list[str],
    row_num: int,
    date_fmt: str,
    verbatim_idx: int = 4,
    fixed_tail_len: int = 1,
) -> ParsedRow:
    coerced = _coerce_to_six_columns(raw, verbatim_idx, fixed_tail_len)
    if coerced is None:
        return ParsedRow(row_num=row_num, is_valid=False, error="menos de 6 columnas")

    if verbatim_idx == 3:
        # Orden date-first (corpora reales): date, group, rate, verbatim, record_id, branch_id
        date_str = coerced[0].strip()
        nps_group = coerced[1].strip()
        nps_rate_str = coerced[2].strip()
        verbatim_raw = coerced[3] if coerced[3] is not None else ""
        record_id = coerced[4].strip()
        branch_id = coerced[5].strip()
    else:
        # Orden record-first (fixture sintética): record_id, date, group, rate, verbatim, branch_id
        record_id = coerced[0].strip()
        date_str = coerced[1].strip()
        nps_group = coerced[2].strip()
        nps_rate_str = coerced[3].strip()
        verbatim_raw = coerced[4] if coerced[4] is not None else ""
        branch_id = coerced[5].strip()

    if not record_id:
        return ParsedRow(row_num=row_num, is_valid=False, error="record_id vacío")
    if not branch_id:
        return ParsedRow(row_num=row_num, is_valid=False, error="branch_id vacío")
    if nps_group not in VALID_NPS_GROUPS:
        return ParsedRow(
            row_num=row_num, is_valid=False, error=f"nps_group inválido: {nps_group!r}"
        )
    try:
        nps_rate = int(nps_rate_str)
    except ValueError:
        return ParsedRow(row_num=row_num, is_valid=False, error="nps_rate no entero")
    if not (0 <= nps_rate <= 10):
        return ParsedRow(row_num=row_num, is_valid=False, error="nps_rate fuera de rango")

    iso = _parse_date(date_str, date_fmt)
    if iso is None:
        # Fallback al otro formato común — algunos archivos mezclan.
        other = _DATE_FMT_MDY if date_fmt == _DATE_FMT_DMY else _DATE_FMT_DMY
        iso = _parse_date(date_str, other)
        if iso is None:
            return ParsedRow(
                row_num=row_num, is_valid=False, error=f"fecha inválida: {date_str!r}"
            )

    has_verbatim = bool(verbatim_raw.strip())
    verbatim_clean = _clean_verbatim(verbatim_raw) if has_verbatim else None
    verbatim_value = verbatim_raw if has_verbatim else None

    return ParsedRow(
        row_num=row_num,
        is_valid=True,
        row=VerbalizationRow(
            record_id=record_id,
            response_date=iso,
            nps_group=cast(NPSGroup, nps_group),
            nps_rate=nps_rate,
            verbatim=verbatim_value,
            branch_id=branch_id,
        ),
        response_date_iso=iso,
        verbatim_clean=verbatim_clean,
    )


def parse_tsv(path: Path) -> Iterator[ParsedRow]:
    """Itera filas del TSV (válidas e inválidas) en orden de archivo.

    Pre-scan: detecta orden de columnas (date-first vs record-first),
    presencia de header y formato de fecha. Skipea el header si lo detecta.
    """
    path = Path(path)
    verbatim_idx, fixed_tail_len, has_header = _scan_corpus(path)
    date_fmt = _detect_date_format_from_file(path, verbatim_idx, fixed_tail_len, has_header)
    reader = csv.reader(io.StringIO(_read_normalized(path)), delimiter="\t", quoting=csv.QUOTE_MINIMAL)
    skipped_header = False
    for row_num, raw in enumerate(reader, start=1):
        if has_header and not skipped_header:
            skipped_header = True
            continue
        yield _normalize_row(raw, row_num, date_fmt, verbatim_idx, fixed_tail_len)


__all__ = ["ParsedRow", "VALID_NPS_GROUPS", "parse_tsv"]
