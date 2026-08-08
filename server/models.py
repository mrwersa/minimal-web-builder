"""SQLAlchemy records for projects, pages, and immutable revisions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from server.database import Base

MAX_PROJECT_NAME_CHARS = 120


def utcnow() -> datetime:
    return datetime.now(UTC)


def isoformat_utc(value: datetime) -> str:
    """Serialize timestamps consistently even when SQLite drops timezone metadata."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def new_id() -> str:
    return str(uuid.uuid4())


class ProjectRecord(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(MAX_PROJECT_NAME_CHARS))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PageRecord(Base):
    __tablename__ = "pages"
    __table_args__ = (UniqueConstraint("project_id", "slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(MAX_PROJECT_NAME_CHARS))
    slug: Mapped[str] = mapped_column(String(MAX_PROJECT_NAME_CHARS))
    version: Mapped[int] = mapped_column(Integer, default=0)
    current_revision_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class RevisionRecord(Base):
    __tablename__ = "revisions"
    __table_args__ = (UniqueConstraint("page_id", "sequence"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    page_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pages.id", ondelete="CASCADE"), index=True
    )
    sequence: Mapped[int] = mapped_column(Integer)
    html: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(32))
    parent_revision_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
