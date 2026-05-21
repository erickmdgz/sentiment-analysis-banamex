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


def _detect_date_format_from_file(path: Path) -> str:
    samples: list[str] = []
    reader = csv.reader(io.StringIO(_read_normalized(path)), delimiter="\t", quoting=csv.QUOTE_MINIMAL)
    for raw in reader:
        row = _coerce_to_six_columns(raw)
        if row is None or len(row) < 2:
            continue
        if row[1].strip():
            samples.append(row[1])
        if len(samples) >= _DATE_SAMPLE_SIZE:
            break
    return _detect_date_format(samples)


def _coerce_to_six_columns(row: list[str]) -> list[str] | None:
    """Devuelve una fila de exactamente 6 columnas o ``None`` si imposible.

    Si la fila trae más de 6 columnas, une las posiciones ``4..-2`` con TAB
    como verbatim y preserva ``-1`` como branch_id. Si trae menos de 6,
    devuelve ``None``.
    """
    if len(row) < 6:
        return None
    if len(row) == 6:
        return row
    head = row[:4]
    branch_id = row[-1]
    verbatim = "\t".join(row[4:-1])
    return [*head, verbatim, branch_id]


def _parse_date(date_str: str, fmt: str) -> str | None:
    try:
        dt = datetime.strptime(date_str.strip(), fmt)
    except ValueError:
        return None
    return dt.strftime("%Y-%m-%d")


def _clean_verbatim(s: str) -> str:
    s = unicodedata.normalize("NFC", s.strip())
    return _WS_RE.sub(" ", s)


def _normalize_row(raw: list[str], row_num: int, date_fmt: str) -> ParsedRow:
    coerced = _coerce_to_six_columns(raw)
    if coerced is None:
        return ParsedRow(row_num=row_num, is_valid=False, error="menos de 6 columnas")

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

    Resuelve el formato de fecha con un sample de 100 filas antes de iniciar
    la iteración principal.
    """
    path = Path(path)
    date_fmt = _detect_date_format_from_file(path)
    reader = csv.reader(io.StringIO(_read_normalized(path)), delimiter="\t", quoting=csv.QUOTE_MINIMAL)
    for row_num, raw in enumerate(reader, start=1):
        yield _normalize_row(raw, row_num, date_fmt)


__all__ = ["ParsedRow", "VALID_NPS_GROUPS", "parse_tsv"]
