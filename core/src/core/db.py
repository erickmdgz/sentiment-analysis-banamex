"""Engine SQLAlchemy, session factory e init_schema().

Patrón SQLAlchemy 2.x sobre SQLite. La ruta por defecto es
``<repo_root>/data/processed/banamex.db`` y se calcula desde la ubicación
de este archivo, pero puede sobreescribirse con la variable de entorno
``CORE_DB_PATH`` (útil para tests).

``init_schema()`` aplica el SQL literal de ``schema.sql`` (fuente de verdad
según ``01_contratos_compartidos.md §2``) y es idempotente: si las tablas
ya existen, no hace nada.
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import Engine, create_engine, event, inspect, text
from sqlalchemy.orm import Session, sessionmaker

_PACKAGE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PACKAGE_DIR.parents[2]
DEFAULT_DB_PATH = _REPO_ROOT / "data" / "processed" / "banamex.db"
SCHEMA_SQL_PATH = _PACKAGE_DIR / "schema.sql"


def _resolve_db_path() -> Path:
    env = os.environ.get("CORE_DB_PATH")
    if env:
        return Path(env).expanduser().resolve()
    return DEFAULT_DB_PATH


def _build_engine(db_path: Path) -> Engine:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{db_path}"
    engine = create_engine(url, future=True)

    @event.listens_for(engine, "connect")
    def _enable_sqlite_pragmas(dbapi_connection, _):  # noqa: ANN001
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys = ON")
        cur.execute("PRAGMA journal_mode = WAL")
        cur.close()

    return engine


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Devuelve un engine cacheado a la DB activa."""
    global _engine, _session_factory
    if _engine is None:
        _engine = _build_engine(_resolve_db_path())
        _session_factory = sessionmaker(bind=_engine, autoflush=False, future=True)
    return _engine


def get_session() -> Session:
    """Factory de sesión SQLAlchemy 2.x."""
    get_engine()
    assert _session_factory is not None
    return _session_factory()


def reset_engine() -> None:
    """Descarta el engine cacheado. Usado por tests al cambiar ``CORE_DB_PATH``."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


def _split_statements(sql: str) -> list[str]:
    return [s.strip() for s in sql.split(";") if s.strip()]


def init_schema() -> None:
    """Aplica ``schema.sql`` sobre la DB activa.

    Idempotente: si las tablas ya existen, no hace nada. No usa
    ``IF NOT EXISTS`` porque el SQL del contrato §2 no lo declara.
    """
    engine = get_engine()
    expected_tables = {
        "files",
        "verbalizations",
        "branches",
        "branch_targets",
        "classifications",
        "metadata_extractions",
        "annotation_runs",
        "classifier_runs",
    }
    existing = set(inspect(engine).get_table_names())
    if expected_tables.issubset(existing):
        return

    sql = SCHEMA_SQL_PATH.read_text(encoding="utf-8")
    statements = _split_statements(sql)
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
