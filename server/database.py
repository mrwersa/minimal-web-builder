"""Database engine and session construction for the modular monolith."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    """Shared SQLAlchemy metadata imported by models and Alembic."""


def create_database_engine(database_url: str) -> Engine:
    """Build an engine with safe SQLite defaults and production-neutral behavior."""
    url = make_url(database_url)
    engine_options: dict[str, Any] = {}
    if url.get_backend_name() == "sqlite":
        engine_options["connect_args"] = {"check_same_thread": False}
        if url.database in (None, "", ":memory:"):
            engine_options["poolclass"] = StaticPool
        elif url.database:
            Path(url.database).expanduser().resolve().parent.mkdir(
                parents=True, exist_ok=True
            )
    return create_engine(database_url, **engine_options)


def is_sqlite_url(database_url: str) -> bool:
    return make_url(database_url).get_backend_name() == "sqlite"


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)


class Database:
    """Own the shared engine and session factory for one application process."""

    def __init__(self, engine: Engine):
        self.engine = engine
        self.sessions = create_session_factory(engine)

    @classmethod
    def from_url(
        cls, database_url: str, *, create_schema: bool | None = None
    ) -> Database:
        engine = create_database_engine(database_url)
        if create_schema is None:
            create_schema = is_sqlite_url(database_url)
        if create_schema:
            # Import models before creating metadata when this module is used directly.
            import server.models  # noqa: F401

            Base.metadata.create_all(engine)
        return cls(engine)

    def close(self) -> None:
        self.engine.dispose()
