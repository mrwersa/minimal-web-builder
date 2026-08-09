"""Database engine and session construction for the modular monolith."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    """Shared SQLAlchemy metadata imported by models and Alembic."""


class SchemaOutOfDateError(RuntimeError):
    """The live database is missing structure the running code expects."""


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


def find_schema_drift(engine: Engine) -> list[str]:
    """Describe structure the models require that the database does not have.

    ``create_all`` only ever adds missing *tables*, so a database created by an
    earlier version keeps its old columns forever. Extra columns are ignored:
    only what the running code would actually reference is a problem.
    """
    import server.models  # noqa: F401 - register the mapped tables on Base

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    drift: list[str] = []
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            drift.append(f"table '{table.name}' is missing")
            continue
        existing = {column["name"] for column in inspector.get_columns(table.name)}
        missing = sorted(
            column.name for column in table.columns if column.name not in existing
        )
        if missing:
            drift.append(
                f"table '{table.name}' is missing column(s): {', '.join(missing)}"
            )
    return drift


def verify_schema(engine: Engine) -> None:
    """Fail fast, and legibly, when the database predates the running code.

    Without this the first query touching a new column dies deep inside
    SQLAlchemy with ``no such column``, which says nothing about the fix.
    """
    drift = find_schema_drift(engine)
    if drift:
        details = "\n".join(f"  - {item}" for item in drift)
        raise SchemaOutOfDateError(
            f"The database schema is out of date:\n{details}\n"
            "Run `alembic upgrade head` to apply pending migrations."
        )


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
        verify_schema(engine)
        return cls(engine)

    def close(self) -> None:
        self.engine.dispose()
