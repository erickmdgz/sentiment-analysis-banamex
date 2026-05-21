"""Configuración compartida de tests para analytics.

Carga el fixture sintético `synthetic_db.sql` sobre una SQLite in-memory y
expone una `Session` de SQLAlchemy por test (ámbito de función).
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "core" / "src" / "core" / "schema.sql"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "synthetic_db.sql"


def _read_sql(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _create_engine_with_schema(fixture_sql: str | None) -> Engine:
    # Tests no validan integridad referencial (SQLite la deja off por defecto);
    # las pruebas que arman datos ad hoc se centran en lógica de analytics.
    engine = create_engine("sqlite+pysqlite:///:memory:")

    with engine.begin() as conn:
        conn.connection.executescript(_read_sql(SCHEMA_PATH))
        if fixture_sql is not None:
            conn.connection.executescript(fixture_sql)
    return engine


@pytest.fixture(scope="session")
def fixture_sql() -> str:
    return _read_sql(FIXTURE_PATH)


@pytest.fixture()
def session(fixture_sql: str) -> Generator[Session, None, None]:
    engine = _create_engine_with_schema(fixture_sql)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    sess = factory()
    try:
        yield sess
    finally:
        sess.close()
        engine.dispose()


@pytest.fixture()
def empty_session() -> Generator[Session, None, None]:
    """Session sin datos (sólo schema)."""
    engine = _create_engine_with_schema(None)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    sess = factory()
    try:
        yield sess
    finally:
        sess.close()
        engine.dispose()


@pytest.fixture()
def session_factory() -> Generator[sessionmaker[Session], None, None]:
    """Factory para construir sesiones con datos ad hoc en tests."""
    engine = _create_engine_with_schema(None)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    engine.dispose()
