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
