"""Durable project, page, and immutable revision persistence.

The service uses SQLAlchemy so local development can use SQLite while production
uses PostgreSQL through ``DATABASE_URL``. API code depends on this service rather
than on a particular database engine.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    select,
)
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

MAX_PROJECT_NAME_CHARS = 120
MAX_DOCUMENT_CHARS = 2_000_000
_REVISION_SOURCES = {"create", "autosave", "manual", "generation", "restore"}


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class ProjectRecord(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String(MAX_PROJECT_NAME_CHARS))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PageRecord(Base):
    __tablename__ = "pages"
    __table_args__ = (UniqueConstraint("project_id", "slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(MAX_PROJECT_NAME_CHARS))
    slug: Mapped[str] = mapped_column(String(MAX_PROJECT_NAME_CHARS))
    version: Mapped[int] = mapped_column(Integer, default=0)
    current_revision_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )


class RevisionRecord(Base):
    __tablename__ = "revisions"
    __table_args__ = (UniqueConstraint("page_id", "sequence"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    page_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pages.id", ondelete="CASCADE"), index=True
    )
    sequence: Mapped[int] = mapped_column(Integer)
    html: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(32))
    parent_revision_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )


class ProjectNotFoundError(LookupError):
    pass


class VersionConflictError(RuntimeError):
    def __init__(self, current_version: int):
        self.current_version = current_version
        super().__init__(f"Page changed since version {current_version}")


class ProjectValidationError(ValueError):
    pass


def _project_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ProjectValidationError("Project name cannot be empty")
    if len(cleaned) > MAX_PROJECT_NAME_CHARS:
        raise ProjectValidationError(
            f"Project name must be at most {MAX_PROJECT_NAME_CHARS} characters"
        )
    return cleaned


def _document(html: str) -> str:
    if len(html) > MAX_DOCUMENT_CHARS:
        raise ProjectValidationError(
            f"Document must be at most {MAX_DOCUMENT_CHARS} characters"
        )
    return html


class ProjectService:
    def __init__(self, sessions: sessionmaker[Session]):
        self._sessions = sessions

    def close(self) -> None:
        """Release pooled database connections during application shutdown."""
        bind = self._sessions.kw.get("bind")
        if bind is not None:
            bind.dispose()

    @classmethod
    def from_url(cls, database_url: str, *, create_schema: bool = True):
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
        engine = create_engine(database_url, **engine_options)
        if create_schema:
            Base.metadata.create_all(engine)
        return cls(sessionmaker(engine, expire_on_commit=False))

    def create_project(self, name: str, html: str = "") -> dict[str, Any]:
        clean_name = _project_name(name)
        clean_html = _document(html)
        with self._sessions.begin() as session:
            project = ProjectRecord(name=clean_name)
            session.add(project)
            session.flush()
            page = PageRecord(
                project_id=project.id,
                name="Home",
                slug="home",
            )
            session.add(page)
            session.flush()
            self._append_revision(session, page, clean_html, "create")
            return self._project_snapshot(session, project)

    def list_projects(self, *, include_archived: bool = False) -> list[dict[str, Any]]:
        with self._sessions() as session:
            query = select(ProjectRecord).order_by(ProjectRecord.updated_at.desc())
            if not include_archived:
                query = query.where(ProjectRecord.archived_at.is_(None))
            return [
                self._project_summary(session, item) for item in session.scalars(query)
            ]

    def get_project(self, project_id: str) -> dict[str, Any]:
        with self._sessions() as session:
            project = session.get(ProjectRecord, project_id)
            if project is None:
                raise ProjectNotFoundError("Project not found")
            return self._project_snapshot(session, project)

    def rename_project(self, project_id: str, name: str) -> dict[str, Any]:
        clean_name = _project_name(name)
        with self._sessions.begin() as session:
            project = session.get(ProjectRecord, project_id)
            if project is None:
                raise ProjectNotFoundError("Project not found")
            project.name = clean_name
            project.updated_at = _utcnow()
            return self._project_snapshot(session, project)

    def archive_project(self, project_id: str) -> dict[str, Any]:
        with self._sessions.begin() as session:
            project = session.get(ProjectRecord, project_id)
            if project is None:
                raise ProjectNotFoundError("Project not found")
            project.archived_at = _utcnow()
            project.updated_at = project.archived_at
            return self._project_snapshot(session, project)

    def get_page(self, page_id: str) -> dict[str, Any]:
        with self._sessions() as session:
            page = session.get(PageRecord, page_id)
            if page is None:
                raise ProjectNotFoundError("Page not found")
            return self._page_snapshot(session, page, include_html=True)

    def save_page(
        self,
        page_id: str,
        html: str,
        *,
        expected_version: int,
        source: str = "autosave",
    ) -> dict[str, Any]:
        clean_html = _document(html)
        clean_source = source if source in _REVISION_SOURCES else "manual"
        with self._sessions.begin() as session:
            page = session.scalar(
                select(PageRecord).where(PageRecord.id == page_id).with_for_update()
            )
            if page is None:
                raise ProjectNotFoundError("Page not found")
            if page.version != expected_version:
                raise VersionConflictError(page.version)
            current = self._current_revision(session, page)
            if current is not None and current.html == clean_html:
                return self._page_snapshot(session, page, include_html=True)
            self._append_revision(session, page, clean_html, clean_source)
            project = session.get(ProjectRecord, page.project_id)
            if project is not None:
                project.updated_at = page.updated_at
            return self._page_snapshot(session, page, include_html=True)

    def list_revisions(self, page_id: str) -> list[dict[str, Any]]:
        with self._sessions() as session:
            if session.get(PageRecord, page_id) is None:
                raise ProjectNotFoundError("Page not found")
            query = (
                select(RevisionRecord)
                .where(RevisionRecord.page_id == page_id)
                .order_by(RevisionRecord.sequence.desc())
            )
            return [self._revision_snapshot(item) for item in session.scalars(query)]

    def restore_revision(
        self, page_id: str, revision_id: str, *, expected_version: int
    ) -> dict[str, Any]:
        with self._sessions.begin() as session:
            page = session.scalar(
                select(PageRecord).where(PageRecord.id == page_id).with_for_update()
            )
            if page is None:
                raise ProjectNotFoundError("Page not found")
            if page.version != expected_version:
                raise VersionConflictError(page.version)
            revision = session.get(RevisionRecord, revision_id)
            if revision is None or revision.page_id != page.id:
                raise ProjectNotFoundError("Revision not found")
            self._append_revision(session, page, revision.html, "restore")
            return self._page_snapshot(session, page, include_html=True)

    @staticmethod
    def _append_revision(
        session: Session, page: PageRecord, html: str, source: str
    ) -> RevisionRecord:
        revision = RevisionRecord(
            page_id=page.id,
            sequence=page.version + 1,
            html=html,
            source=source,
            parent_revision_id=page.current_revision_id,
        )
        session.add(revision)
        session.flush()
        page.version = revision.sequence
        page.current_revision_id = revision.id
        page.updated_at = _utcnow()
        return revision

    @staticmethod
    def _current_revision(session: Session, page: PageRecord) -> RevisionRecord | None:
        return (
            session.get(RevisionRecord, page.current_revision_id)
            if page.current_revision_id
            else None
        )

    def _project_summary(
        self, session: Session, project: ProjectRecord
    ) -> dict[str, Any]:
        page_count = len(
            list(
                session.scalars(
                    select(PageRecord.id).where(PageRecord.project_id == project.id)
                )
            )
        )
        return {
            "id": project.id,
            "name": project.name,
            "page_count": page_count,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
            "archived_at": (
                project.archived_at.isoformat() if project.archived_at else None
            ),
        }

    def _project_snapshot(
        self, session: Session, project: ProjectRecord
    ) -> dict[str, Any]:
        pages = list(
            session.scalars(
                select(PageRecord)
                .where(PageRecord.project_id == project.id)
                .order_by(PageRecord.created_at)
            )
        )
        return {
            **self._project_summary(session, project),
            "pages": [
                self._page_snapshot(session, page, include_html=True) for page in pages
            ],
        }

    def _page_snapshot(
        self, session: Session, page: PageRecord, *, include_html: bool
    ) -> dict[str, Any]:
        revision = self._current_revision(session, page)
        result: dict[str, Any] = {
            "id": page.id,
            "project_id": page.project_id,
            "name": page.name,
            "slug": page.slug,
            "version": page.version,
            "current_revision_id": page.current_revision_id,
            "created_at": page.created_at.isoformat(),
            "updated_at": page.updated_at.isoformat(),
        }
        if include_html:
            result["html"] = revision.html if revision else ""
        return result

    @staticmethod
    def _revision_snapshot(revision: RevisionRecord) -> dict[str, Any]:
        return {
            "id": revision.id,
            "page_id": revision.page_id,
            "sequence": revision.sequence,
            "source": revision.source,
            "parent_revision_id": revision.parent_revision_id,
            "created_at": revision.created_at.isoformat(),
        }
