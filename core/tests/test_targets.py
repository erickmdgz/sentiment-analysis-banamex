"""Tests de la generación de objetivos NPS sintéticos.

Cubren §13 (10), (11), (14) del plan M1.
"""

from __future__ import annotations

import io
import csv
from pathlib import Path

import pytest
from sqlalchemy import text

from core.db import get_engine
from core.loader import load_file
from core.targets import (
    compute_branch_nps,
    compute_national_nps,
    generate_all,
    generate_target_for_branch,
    regenerate_for_branches,
)


def _make_tsv(path: Path, rows: list[list[str]]) -> Path:
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter="\t", quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    for row in rows:
        writer.writerow(row)
    path.write_bytes(buf.getvalue().encode("latin-1"))
    return path


# ---------- generate_target_for_branch (pura) ----------


def test_target_determinista_para_mismo_branch() -> None:
    a = generate_target_for_branch("A-123", 40.0)
    b = generate_target_for_branch("A-123", 40.0)
    assert a == b


def test_target_dentro_del_rango_50_85_para_cualquier_input() -> None:
    casos: list[float | None] = [-100.0, -50.0, 0.0, 25.0, 50.0, 75.0, 100.0, 150.0, None]
    for bid in ("A-1", "A-99", "A-1234", "branch-xyz"):
        for nps in casos:
            t = generate_target_for_branch(bid, nps)
            assert 50 <= t <= 85, f"bid={bid!r} nps={nps!r} target={t}"


def test_target_branch_id_no_numerico_usa_fallback_hash() -> None:
    # No debe levantar y debe ser determinístico
    a = generate_target_for_branch("branch-xyz", 40.0)
    b = generate_target_for_branch("branch-xyz", 40.0)
    assert a == b
    assert 50 <= a <= 85


# ---------- compute_*_nps ----------


def test_compute_national_nps_vacio_devuelve_none(temp_db: Path) -> None:
    from core.db import init_schema
    init_schema()
    assert compute_national_nps() is None


def test_compute_branch_nps_menos_de_10_respuestas_cae_a_nacional(
    temp_db: Path, tmp_path: Path
) -> None:
    # Cargamos 20 respuestas en A-NAT (todas Promotor, NPS = 100)
    # y 3 respuestas en A-SUC (todas Detractor; <10 → debe caer al nacional)
    rows = []
    for i in range(1, 21):
        rows.append([f"NAT-{i}", "01/01/2025", "Promotor", "10", f"v{i}", "A-NAT"])
    for i in range(1, 4):
        rows.append([f"SUC-{i}", "02/01/2025", "Detractor", "0", f"v{i}", "A-SUC"])
    p = _make_tsv(tmp_path / "nps.tsv", rows)
    load_file(p)

    nat = compute_national_nps()
    assert nat is not None
    # nacional = (20 promotores - 3 detractores) / 23 * 100
    expected = (20 - 3) / 23 * 100
    assert abs(nat - expected) < 1e-6

    suc = compute_branch_nps("A-SUC")
    # Cae al nacional porque sólo tiene 3 respuestas (<10)
    assert suc is not None
    assert abs(suc - expected) < 1e-6

    # Con >=10 respuestas usa su propio NPS
    nat_nps = compute_branch_nps("A-NAT")
    assert nat_nps == 100.0


# ---------- generate_all / regenerate_for_branches ----------


def test_generate_all_genera_un_target_por_sucursal(
    temp_db: Path, fixtures_dir: Path
) -> None:
    load_file(fixtures_dir / "sample.tsv")
    targets = generate_all(seed=42)
    assert len(targets) > 0
    branches_with_target = {t.branch_id for t in targets}

    engine = get_engine()
    with engine.connect() as conn:
        all_branches = {r[0] for r in conn.execute(text("SELECT branch_id FROM branches")).all()}
        persisted = {
            r[0]
            for r in conn.execute(text("SELECT branch_id FROM branch_targets")).all()
        }
    assert branches_with_target == all_branches
    assert branches_with_target == persisted
    for t in targets:
        assert 50 <= t.nps_target_annual <= 85
        assert t.is_synthetic is True


def test_generate_all_es_idempotente(temp_db: Path, fixtures_dir: Path) -> None:
    load_file(fixtures_dir / "sample.tsv")
    first = generate_all(seed=42)
    second = generate_all(seed=42)  # no debe regenerar
    assert {(t.branch_id, t.nps_target_annual) for t in first} == {
        (t.branch_id, t.nps_target_annual) for t in second
    }


def test_generate_all_force_regenera(temp_db: Path, fixtures_dir: Path) -> None:
    load_file(fixtures_dir / "sample.tsv")
    first = generate_all(seed=42)
    second = generate_all(seed=42, force=True)
    # Mismas branches, mismos valores (porque la fórmula es determinística)
    assert {(t.branch_id, t.nps_target_annual) for t in first} == {
        (t.branch_id, t.nps_target_annual) for t in second
    }


def test_regenerate_for_branches_solo_afecta_indicadas(
    temp_db: Path, fixtures_dir: Path
) -> None:
    load_file(fixtures_dir / "sample.tsv")
    generate_all(seed=42)
    engine = get_engine()
    with engine.connect() as conn:
        all_branches = [r[0] for r in conn.execute(text("SELECT branch_id FROM branches ORDER BY branch_id")).all()]
    target_bid = all_branches[0]
    untouched_bid = all_branches[-1]

    before = {
        r[0]: r[1]
        for r in engine.connect()
        .execute(text("SELECT branch_id, nps_target_annual FROM branch_targets"))
        .all()
    }

    regenerate_for_branches([target_bid])
    after = {
        r[0]: r[1]
        for r in engine.connect()
        .execute(text("SELECT branch_id, nps_target_annual FROM branch_targets"))
        .all()
    }

    # La sucursal intacta no cambió
    assert before[untouched_bid] == after[untouched_bid]
    # Las sucursales pedidas siguen presentes y dentro de rango
    assert 50 <= after[target_bid] <= 85
