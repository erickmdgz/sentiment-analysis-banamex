"""Fixtures de pytest compartidas: aísla la DB por test."""

from __future__ import annotations

from pathlib import Path

import pytest

from core import db as core_db


@pytest.fixture
def temp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("CORE_DB_PATH", str(db_path))
    core_db.reset_engine()
    yield db_path
    core_db.reset_engine()


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"
