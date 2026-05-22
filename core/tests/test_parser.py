"""Tests del parser TSV. Cubren §13 (1)-(7) del plan M1."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.parser import parse_tsv


def _write(p: Path, lines: list[bytes]) -> Path:
    p.write_bytes(b"".join(lines))
    return p


def test_parser_tolera_latin1_con_acentos(tmp_path: Path) -> None:
    # Ñ, ñ, á, é, í, ó, ú en latin-1
    content = (
        "REC-1\t01/01/2025\tPromotor\t10\tMaría y Ñoño excelentísimos á é í ó ú\tA-1\n"
    ).encode("latin-1")
    p = _write(tmp_path / "ac.tsv", [content])
    rows = list(parse_tsv(p))
    assert len(rows) == 1
    assert rows[0].is_valid is True
    assert rows[0].row is not None
    assert "María" in (rows[0].row.verbatim or "")
    assert "Ñoño" in (rows[0].row.verbatim or "")


def test_parser_tolera_crlf_lf_nel(tmp_path: Path) -> None:
    # NEL = 0x85 en latin-1
    lf = b"REC-1\t01/01/2025\tPromotor\t10\tlf\tA-1\n"
    crlf = b"REC-2\t02/01/2025\tDetractor\t3\tcrlf\tA-2\r\n"
    nel = b"REC-3\t03/01/2025\tPasivo\t7\tnel\tA-3\x85"
    last = b"REC-4\t04/01/2025\tPromotor\t9\tlast\tA-4"
    p = _write(tmp_path / "mix.tsv", [lf, crlf, nel, last])
    rows = list(parse_tsv(p))
    valid = [r for r in rows if r.is_valid]
    assert len(valid) == 4
    record_ids = {r.row.record_id for r in valid if r.row}
    assert record_ids == {"REC-1", "REC-2", "REC-3", "REC-4"}


def test_parser_tolera_comillas_dobles_en_verbatim(tmp_path: Path) -> None:
    # Comillas escapadas: "texto con ""comillas"" dentro"
    line = b'REC-1\t01/01/2025\tPromotor\t10\t"texto con ""comillas"" dentro"\tA-1\n'
    p = _write(tmp_path / "q.tsv", [line])
    rows = list(parse_tsv(p))
    assert len(rows) == 1
    assert rows[0].is_valid is True
    assert rows[0].row is not None
    assert rows[0].row.verbatim == 'texto con "comillas" dentro'


def test_parser_tolera_tabs_accidentales_en_verbatim(tmp_path: Path) -> None:
    # 8 columnas físicas; col 4..-2 deben unirse como verbatim, col -1 es branch_id.
    line = b"REC-1\t01/01/2025\tPromotor\t10\tparte1\tparte2\tparte3\tA-99\n"
    p = _write(tmp_path / "t.tsv", [line])
    rows = list(parse_tsv(p))
    assert len(rows) == 1
    assert rows[0].is_valid is True
    assert rows[0].row is not None
    assert rows[0].row.branch_id == "A-99"
    assert rows[0].row.verbatim is not None
    # Las tres partes deben aparecer en el verbatim final
    for token in ("parte1", "parte2", "parte3"):
        assert token in rows[0].row.verbatim


def test_parser_marca_invalida_fila_con_menos_de_6_columnas(tmp_path: Path) -> None:
    line = b"REC-1\t01/01/2025\tPromotor\t10\tcorto\n"  # 5 columnas
    p = _write(tmp_path / "short.tsv", [line])
    rows = list(parse_tsv(p))
    assert len(rows) == 1
    assert rows[0].is_valid is False
    assert rows[0].error is not None
    assert "6 col" in rows[0].error


def test_parser_marca_invalida_nps_rate_fuera_de_rango(tmp_path: Path) -> None:
    line = b"REC-1\t01/01/2025\tPromotor\t11\ttexto\tA-1\n"
    p = _write(tmp_path / "rate.tsv", [line])
    rows = list(parse_tsv(p))
    assert len(rows) == 1
    assert rows[0].is_valid is False
    assert "rango" in (rows[0].error or "")


def test_parser_marca_invalida_nps_group_typo(tmp_path: Path) -> None:
    line = b"REC-1\t01/01/2025\tPasivos\t7\ttexto\tA-1\n"  # 'Pasivos' con s
    p = _write(tmp_path / "typo.tsv", [line])
    rows = list(parse_tsv(p))
    assert len(rows) == 1
    assert rows[0].is_valid is False
    assert "nps_group" in (rows[0].error or "")


def test_parser_marca_invalida_fecha_no_parseable(tmp_path: Path) -> None:
    line = b"REC-1\tno-es-fecha\tPromotor\t10\ttexto\tA-1\n"
    p = _write(tmp_path / "date.tsv", [line])
    rows = list(parse_tsv(p))
    assert len(rows) == 1
    assert rows[0].is_valid is False
    assert "fecha" in (rows[0].error or "")


def test_parser_marca_invalida_branch_id_vacio(tmp_path: Path) -> None:
    line = b"REC-1\t01/01/2025\tPromotor\t10\ttexto\t\n"
    p = _write(tmp_path / "br.tsv", [line])
    rows = list(parse_tsv(p))
    assert len(rows) == 1
    assert rows[0].is_valid is False
    assert "branch_id" in (rows[0].error or "")


def test_parser_normaliza_fecha_a_iso(tmp_path: Path) -> None:
    # Día > 12 en primera posición → DD/MM/YYYY se autodetecta
    line = b"REC-1\t25/03/2025\tPromotor\t10\ttexto\tA-1\n"
    p = _write(tmp_path / "iso.tsv", [line])
    rows = list(parse_tsv(p))
    assert rows[0].is_valid is True
    assert rows[0].response_date_iso == "2025-03-25"
    assert rows[0].row is not None
    assert rows[0].row.response_date == "2025-03-25"


def test_parser_verbatim_vacio_da_has_verbatim_false(tmp_path: Path) -> None:
    line = b"REC-1\t01/01/2025\tPromotor\t10\t\tA-1\n"
    p = _write(tmp_path / "ev.tsv", [line])
    rows = list(parse_tsv(p))
    assert rows[0].is_valid is True
    assert rows[0].row is not None
    assert rows[0].row.verbatim is None
    assert rows[0].verbatim_clean is None


# --- Auto-detect de orden de columnas + skip de header (ajuste M6) ---


def test_parser_orden_date_first_con_header_y_record_id_al_final(tmp_path: Path) -> None:
    """Corpora reales de Banamex: header + filas date-first (date, group, rate, verbatim, record_id, branch_id)."""
    header = b"fecha\tnps_group\tnps_rate\tverbatim\trecord_id\tbranch_id\n"
    r1 = b"01/03/2026\tPromotor\t10\tExcelente servicio\tREC-100\tA-201\n"
    r2 = b"15/03/2026\tDetractor\t2\tCajero descompuesto\tREC-101\tA-202\n"
    p = _write(tmp_path / "real.tsv", [header, r1, r2])
    rows = list(parse_tsv(p))
    assert len(rows) == 2
    assert all(r.is_valid for r in rows)
    assert rows[0].row is not None and rows[1].row is not None
    assert rows[0].row.record_id == "REC-100"
    assert rows[0].row.branch_id == "A-201"
    assert rows[0].row.verbatim == "Excelente servicio"
    assert rows[1].row.record_id == "REC-101"
    assert rows[1].row.branch_id == "A-202"
    assert rows[1].row.response_date == "2026-03-15"


def test_parser_date_first_tolera_tabs_accidentales_en_verbatim(tmp_path: Path) -> None:
    """En orden date-first, verbatim multi-tab se une preservando record_id y branch_id finales."""
    header = b"fecha\tnps_group\tnps_rate\tverbatim\trecord_id\tbranch_id\n"
    # 8 columnas físicas: date, group, rate, v1, v2, v3, record_id, branch_id
    line = b"01/03/2026\tPasivo\t7\tparte1\tparte2\tparte3\tREC-200\tA-303\n"
    p = _write(tmp_path / "real_tabs.tsv", [header, line])
    rows = list(parse_tsv(p))
    assert len(rows) == 1
    assert rows[0].is_valid is True
    assert rows[0].row is not None
    assert rows[0].row.record_id == "REC-200"
    assert rows[0].row.branch_id == "A-303"
    assert rows[0].row.verbatim is not None
    for token in ("parte1", "parte2", "parte3"):
        assert token in rows[0].row.verbatim


def test_parser_header_se_skipea_sin_contar_como_invalida(tmp_path: Path) -> None:
    """El header detectado (tokens reconocidos) no aparece en el yield ni se cuenta como inválida."""
    header = b"fecha\tnps_group\tnps_rate\tverbatim\trecord_id\tbranch_id\n"
    r1 = b"01/03/2026\tPromotor\t10\ttexto\tREC-1\tA-1\n"
    p = _write(tmp_path / "h.tsv", [header, r1])
    rows = list(parse_tsv(p))
    assert len(rows) == 1
    assert sum(1 for r in rows if not r.is_valid) == 0
    assert rows[0].is_valid is True
