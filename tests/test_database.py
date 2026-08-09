from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from server.database import (
    Database,
    SchemaOutOfDateError,
    create_database_engine,
    find_schema_drift,
    verify_schema,
)


def _migrated_url(tmp_path, revision: str) -> str:
    database_url = f"sqlite:///{tmp_path / 'schema.db'}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, revision)
    return database_url


def test_fresh_sqlite_database_has_no_drift(tmp_path) -> None:
    database = Database.from_url(f"sqlite:///{tmp_path / 'fresh.db'}")
    try:
        assert find_schema_drift(database.engine) == []
    finally:
        database.close()


def test_fully_migrated_database_has_no_drift(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    engine = create_database_engine(_migrated_url(tmp_path, "head"))
    try:
        assert find_schema_drift(engine) == []
        verify_schema(engine)
    finally:
        engine.dispose()


def test_database_predating_the_metrics_migration_is_reported(
    tmp_path, monkeypatch
) -> None:
    """A schema from before 0008 must be named, not surfaced as 'no such column'."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    engine = create_database_engine(_migrated_url(tmp_path, "20260809_0007"))
    try:
        drift = find_schema_drift(engine)
        assert len(drift) == 1
        assert "generation_jobs" in drift[0]
        for column in ("duration_ms", "failure_kind", "finished_at", "metrics"):
            assert column in drift[0]

        with pytest.raises(SchemaOutOfDateError) as excinfo:
            verify_schema(engine)
        assert "alembic upgrade head" in str(excinfo.value)
    finally:
        engine.dispose()


def test_missing_table_is_reported(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    engine = create_database_engine(_migrated_url(tmp_path, "head"))
    try:
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE audit_events"))
        assert find_schema_drift(engine) == ["table 'audit_events' is missing"]
    finally:
        engine.dispose()


def test_extra_columns_are_not_drift(tmp_path, monkeypatch) -> None:
    """Only structure the running code needs matters; spare columns are harmless."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    engine = create_database_engine(_migrated_url(tmp_path, "head"))
    try:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE projects ADD COLUMN legacy_note TEXT"))
        assert find_schema_drift(engine) == []
    finally:
        engine.dispose()


def test_opening_a_stale_database_fails_fast(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    database_url = _migrated_url(tmp_path, "20260809_0007")

    with pytest.raises(SchemaOutOfDateError):
        Database.from_url(database_url, create_schema=False)
