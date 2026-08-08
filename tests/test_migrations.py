from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from server.database import create_database_engine
from server.projects import ProjectService


def test_initial_migration_builds_service_schema(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    database_url = f"sqlite:///{tmp_path / 'migrated.db'}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "head")
    command.check(config)

    engine = create_database_engine(database_url)
    assert set(inspect(engine).get_table_names()) == {
        "alembic_version",
        "pages",
        "projects",
        "revisions",
    }
    engine.dispose()

    service = ProjectService.from_url(database_url, create_schema=False)
    try:
        assert service.create_project("Migrated")["name"] == "Migrated"
    finally:
        service.close()
