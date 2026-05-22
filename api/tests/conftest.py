"""Fixtures compartidos para los smoke tests del API.

- `tmp_db`: DB SQLite temporal (autouse, redirige `CORE_DB_PATH`).
- `seeded_db`: DB con datos sintéticos suficientes para todos los routers.
- `client`: `TestClient` con la app real (sin auth).
- `auth_client`: cliente con `Authorization: Bearer <token>` ya seteado.
- `tsv_path`: path a un TSV sintético válido (`tests/fixtures/sample.tsv`).
"""

from __future__ import annotations

import json
import os
import random
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

FIXTURE_TSV = Path(__file__).resolve().parent / "fixtures" / "sample.tsv"


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Crea una DB SQLite vacía y la inyecta vía `CORE_DB_PATH`.

    Resetea el engine cacheado de `core.db` para que la nueva ruta tenga
    efecto en la sesión de tests.
    """
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("CORE_DB_PATH", str(db_path))
    from core import db as core_db

    core_db.reset_engine()
    core_db.init_schema()
    yield db_path
    core_db.reset_engine()


@pytest.fixture
def seeded_db(tmp_db):
    """Carga datos sintéticos suficientes para todos los routers.

    - 3 sucursales: A-101, A-102, A-103.
    - 9 meses cubiertos (2026-01..2026-09 en parte; 2025-12 para compare).
    - ~180 verbalizaciones repartidas en P/Pa/D.
    - classifications/metadata_extractions sintéticas que cubren varios buckets.
    - branch_targets para las 3.
    """
    from core.db import get_engine

    engine = get_engine()
    rng = random.Random(42)

    # 1 archivo de origen
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO files (filename, sha256, rows_total, rows_inserted,
                                   rows_duplicated, rows_invalid)
                VALUES ('seed.txt', :sha, 180, 180, 0, 0)
                """
            ),
            {"sha": "0" * 64},
        )
        file_id = conn.execute(text("SELECT id FROM files")).scalar_one()

    branches = ["A-101", "A-102", "A-103"]
    verbalizations: list[dict] = []
    classifications: list[dict] = []
    metadata: list[dict] = []

    months = [
        (2025, 12),
        (2026, 1),
        (2026, 2),
        (2026, 3),
        (2026, 4),
        (2026, 5),
        (2026, 6),
        (2026, 7),
        (2026, 8),
    ]
    nps_options: list[tuple[str, int]] = [
        ("Detractor", 2),
        ("Detractor", 4),
        ("Pasivo", 7),
        ("Pasivo", 8),
        ("Promotor", 9),
        ("Promotor", 10),
    ]
    buckets = [
        ("1", "Atención al cliente", "1.1", "Trato del personal", "Atención del personal"),
        ("2", "Tiempos y operación", "2.1", "Tiempo de espera", "Tiempos y espera"),
        (
            "5",
            "Canales digitales",
            "5.1",
            "App móvil",
            "Canales digitales",
        ),
        (
            "4",
            "Cajeros automáticos (ATM)",
            "4.1",
            "Disponibilidad de cajeros",
            "Cajeros (ATM)",
        ),
    ]

    counter = 0
    for branch in branches:
        for year, month in months:
            for _ in range(6):
                counter += 1
                rid = f"REC-{counter:05d}"
                nps_group, rate = rng.choice(nps_options)
                day = rng.randint(1, 27)
                d = date(year, month, day).isoformat()
                verbatim = f"Comentario {counter} sobre experiencia en {branch}."
                verbalizations.append(
                    {
                        "record_id": rid,
                        "file_id": file_id,
                        "response_date": d,
                        "response_year": year,
                        "response_month": month,
                        "nps_group": nps_group,
                        "nps_rate": rate,
                        "verbatim": verbatim,
                        "verbatim_clean": verbatim,
                        "branch_id": branch,
                        "has_verbatim": 1,
                    }
                )
                polarity = (
                    "pos"
                    if nps_group == "Promotor"
                    else "neu"
                    if nps_group == "Pasivo"
                    else "neg"
                )
                l1, l1n, l2, l2n, bucket = buckets[counter % len(buckets)]
                classifications.append(
                    {
                        "record_id": rid,
                        "l1_code": l1,
                        "l1_name": l1n,
                        "l2_code": l2,
                        "l2_name": l2n,
                        "l3_code": None,
                        "l3_name": None,
                        "confidence": 0.8,
                        "source": "classifier",
                        "polarity": polarity,
                        "ui_bucket": bucket,
                    }
                )
                personnel_name = "Maria" if counter % 5 == 0 else None
                personnel_pol = (
                    ("pos" if nps_group == "Promotor" else "neg")
                    if personnel_name
                    else None
                )
                metadata.append(
                    {
                        "record_id": rid,
                        "personnel_named": 1 if personnel_name else 0,
                        "personnel_name": personnel_name,
                        "personnel_polarity": personnel_pol,
                        "explicit_recommendation": None,
                        "mentions_other_bank": 0,
                        "other_bank_names": json.dumps([]),
                        "channels_mentioned": json.dumps([]),
                    }
                )

    with engine.begin() as conn:
        for branch in branches:
            conn.execute(
                text("INSERT OR IGNORE INTO branches (branch_id) VALUES (:bid)"),
                {"bid": branch},
            )
        for i, branch in enumerate(branches):
            conn.execute(
                text(
                    """
                    INSERT OR REPLACE INTO branch_targets
                        (branch_id, nps_target_annual, is_synthetic)
                    VALUES (:bid, :tgt, 1)
                    """
                ),
                {"bid": branch, "tgt": 60 + i * 3},
            )
        conn.execute(
            text(
                """
                INSERT INTO verbalizations (
                    record_id, file_id, response_date, response_year, response_month,
                    nps_group, nps_rate, verbatim, verbatim_clean, branch_id, has_verbatim
                ) VALUES (
                    :record_id, :file_id, :response_date, :response_year, :response_month,
                    :nps_group, :nps_rate, :verbatim, :verbatim_clean, :branch_id, :has_verbatim
                )
                """
            ),
            verbalizations,
        )
        conn.execute(
            text(
                """
                INSERT INTO classifications (
                    record_id, l1_code, l1_name, l2_code, l2_name, l3_code, l3_name,
                    confidence, source, polarity, ui_bucket
                ) VALUES (
                    :record_id, :l1_code, :l1_name, :l2_code, :l2_name, :l3_code, :l3_name,
                    :confidence, :source, :polarity, :ui_bucket
                )
                """
            ),
            classifications,
        )
        conn.execute(
            text(
                """
                INSERT OR REPLACE INTO metadata_extractions (
                    record_id, personnel_named, personnel_name, personnel_polarity,
                    explicit_recommendation, mentions_other_bank, other_bank_names,
                    channels_mentioned
                ) VALUES (
                    :record_id, :personnel_named, :personnel_name, :personnel_polarity,
                    :explicit_recommendation, :mentions_other_bank, :other_bank_names,
                    :channels_mentioned
                )
                """
            ),
            metadata,
        )

    return tmp_db


@pytest.fixture
def client(tmp_db):
    """`TestClient` con la app real apuntando a la DB temporal."""
    from api.main import app

    return TestClient(app)


@pytest.fixture
def auth_client(client):
    """`TestClient` con `Authorization: Bearer <token>` ya seteado."""
    resp = client.post("/auth/login", json={"username": "demo", "password": "demo"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def seeded_client(seeded_db, client):
    """`TestClient` con DB sembrada + token de auth seteado."""
    resp = client.post("/auth/login", json={"username": "demo", "password": "demo"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def tsv_path(tmp_path):
    """Crea un TSV sintético en `tmp_path/sample.txt` con 5 filas válidas."""
    path = tmp_path / "sample.txt"
    rows = [
        ("UPLD-001", "01/03/2026", "Promotor", "10", "Excelente atención hoy", "A-201"),
        ("UPLD-002", "15/03/2026", "Detractor", "2", "Cajero descompuesto, muy mal", "A-201"),
        ("UPLD-003", "20/03/2026", "Pasivo", "7", "Servicio normal, sin más", "A-202"),
        ("UPLD-004", "21/03/2026", "Promotor", "9", "Personal amable, todo bien", "A-202"),
        ("UPLD-005", "22/03/2026", "Detractor", "3", "Tiempo de espera larguísimo", "A-203"),
    ]
    with open(path, "w", encoding="latin-1") as f:
        for r in rows:
            f.write("\t".join(r) + "\n")
    return path


@pytest.fixture(autouse=True)
def _stub_classifier(monkeypatch):
    """Reemplaza el clasificador supervisado de M2b por un stub vacío.

    `Classifier.predict` retorna `[]` para cada texto, así `engine.pipeline.
    classify_batch` cae a la rama de fallback (`_fallback_category`) para todos
    los registros — los tests del API se ejercen end-to-end sin requerir un
    `.joblib` entrenado.
    """

    class _StubClassifier:
        def predict(self, texts):
            return [[] for _ in texts]

    from engine import classifier as engine_classifier
    from engine import pipeline as engine_pipeline

    stub = _StubClassifier()
    monkeypatch.setattr(
        engine_pipeline, "get_default_classifier", lambda *a, **kw: stub
    )
    monkeypatch.setattr(
        engine_classifier, "get_default_classifier", lambda *a, **kw: stub
    )
    yield
    engine_classifier.reset_default_classifier()
