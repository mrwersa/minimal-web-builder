from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from server.auth import AuthService
from server.database import Database, create_database_engine
from server.models import LEGACY_OWNER_ID, UserRecord
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
        "conversations",
        "generation_jobs",
        "layout_dnas",
        "pages",
        "projects",
        "revisions",
        "templates",
        "user_sessions",
        "users",
    }
    engine.dispose()

    database = Database.from_url(database_url, create_schema=False)
    owner_id = "00000000-0000-0000-0000-000000000010"
    with database.sessions.begin() as session:
        session.add(
            UserRecord(
                id=owner_id,
                email="migration@example.test",
                password_hash="!test-account",
            )
        )
    service = ProjectService(database.sessions)
    try:
        assert service.create_project(owner_id, "Migrated")["name"] == "Migrated"
    finally:
        database.close()


def test_ownership_migration_backfills_existing_projects(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    database_url = f"sqlite:///{tmp_path / 'backfill.db'}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "20260808_0001")
    engine = create_database_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO projects "
                "(id, name, created_at, updated_at, archived_at) "
                "VALUES ('project-1', 'Existing', CURRENT_TIMESTAMP, "
                "CURRENT_TIMESTAMP, NULL)"
            )
        )
    engine.dispose()

    command.upgrade(config, "head")

    engine = create_database_engine(database_url)
    with engine.connect() as connection:
        owner_id = connection.scalar(
            text("SELECT owner_id FROM projects WHERE id = 'project-1'")
        )
    engine.dispose()
    assert owner_id == LEGACY_OWNER_ID

    database = Database.from_url(database_url, create_schema=False)
    principal, _token = AuthService(database.sessions).register(
        "owner@example.test", "correct horse battery"
    )
    service = ProjectService(database.sessions)
    assert service.get_project(principal.id, "project-1")["name"] == "Existing"
    database.close()
