"""Durable project, page, and immutable revision persistence.

The service uses SQLAlchemy so local development can use SQLite while production
uses PostgreSQL through ``DATABASE_URL``. API code depends on this service rather
than on a particular database engine.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import (
    Engine,
    func,
    select,
    update,
)
from sqlalchemy.orm import Session, sessionmaker

from server.database import (
    Base,
    create_database_engine,
    create_session_factory,
    is_sqlite_url,
)
from server.models import (
    MAX_PROJECT_NAME_CHARS,
    PageRecord,
    ProjectRecord,
    RevisionRecord,
    isoformat_utc,
    new_id,
    utcnow,
)

MAX_DOCUMENT_CHARS = 2_000_000
_REVISION_SOURCES = {
    "create",
    "duplicate",
    "autosave",
    "manual",
    "generation",
    "restore",
}


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


def _copy_name(name: str) -> str:
    suffix = " Copy"
    return f"{name[: MAX_PROJECT_NAME_CHARS - len(suffix)].rstrip()}{suffix}"


class ProjectService:
    def __init__(self, sessions: sessionmaker[Session], engine: Engine):
        self._sessions = sessions
        self._engine = engine

    def close(self) -> None:
        """Release pooled database connections during application shutdown."""
        self._engine.dispose()

    @classmethod
    def from_url(
        cls, database_url: str, *, create_schema: bool | None = None
    ) -> ProjectService:
        engine = create_database_engine(database_url)
        if create_schema is None:
            create_schema = is_sqlite_url(database_url)
        if create_schema:
            Base.metadata.create_all(engine)
        return cls(create_session_factory(engine), engine)

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

    def list_projects(
        self, *, include_archived: bool = False, search: str = ""
    ) -> list[dict[str, Any]]:
        with self._sessions() as session:
            page_count = (
                select(func.count(PageRecord.id))
                .where(PageRecord.project_id == ProjectRecord.id)
                .correlate(ProjectRecord)
                .scalar_subquery()
            )
            query = select(ProjectRecord, page_count).order_by(
                ProjectRecord.updated_at.desc()
            )
            if not include_archived:
                query = query.where(ProjectRecord.archived_at.is_(None))
            clean_search = search.strip().lower()
            if clean_search:
                query = query.where(
                    func.lower(ProjectRecord.name).contains(clean_search)
                )
            return [
                self._project_summary(project, count)
                for project, count in session.execute(query)
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
            if project.name == clean_name:
                return self._project_snapshot(session, project)
            project.name = clean_name
            project.updated_at = utcnow()
            return self._project_snapshot(session, project)

    def duplicate_project(
        self, project_id: str, *, name: str | None = None
    ) -> dict[str, Any]:
        with self._sessions.begin() as session:
            source = session.get(ProjectRecord, project_id)
            if source is None:
                raise ProjectNotFoundError("Project not found")
            duplicate_name = (
                _project_name(name) if name is not None else _copy_name(source.name)
            )
            duplicate = ProjectRecord(name=duplicate_name)
            session.add(duplicate)
            session.flush()

            pages = list(
                session.scalars(
                    select(PageRecord)
                    .where(PageRecord.project_id == source.id)
                    .order_by(PageRecord.created_at)
                )
            )
            for source_page in pages:
                page = PageRecord(
                    project_id=duplicate.id,
                    name=source_page.name,
                    slug=source_page.slug,
                )
                session.add(page)
                session.flush()
                revision = self._current_revision(session, source_page)
                self._append_revision(
                    session, page, revision.html if revision else "", "duplicate"
                )
            return self._project_snapshot(session, duplicate)

    def archive_project(self, project_id: str) -> dict[str, Any]:
        with self._sessions.begin() as session:
            project = session.get(ProjectRecord, project_id)
            if project is None:
                raise ProjectNotFoundError("Project not found")
            if project.archived_at is not None:
                return self._project_snapshot(session, project)
            project.archived_at = utcnow()
            project.updated_at = project.archived_at
            return self._project_snapshot(session, project)

    def get_page(self, page_id: str) -> dict[str, Any]:
        with self._sessions() as session:
            page = session.get(PageRecord, page_id)
            if page is None:
                raise ProjectNotFoundError("Page not found")
            return self._page_snapshot(session, page)

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
            page = session.get(PageRecord, page_id)
            if page is None:
                raise ProjectNotFoundError("Page not found")
            if page.version != expected_version:
                raise VersionConflictError(page.version)
            current = self._current_revision(session, page)
            if current is not None and current.html == clean_html:
                return self._page_snapshot(session, page)
            self._append_revision(session, page, clean_html, clean_source)
            self._touch_project(session, page)
            return self._page_snapshot(session, page)

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
            page = session.get(PageRecord, page_id)
            if page is None:
                raise ProjectNotFoundError("Page not found")
            if page.version != expected_version:
                raise VersionConflictError(page.version)
            revision = session.get(RevisionRecord, revision_id)
            if revision is None or revision.page_id != page.id:
                raise ProjectNotFoundError("Revision not found")
            self._append_revision(session, page, revision.html, "restore")
            self._touch_project(session, page)
            return self._page_snapshot(session, page)

    @staticmethod
    def _touch_project(session: Session, page: PageRecord) -> None:
        project = session.get(ProjectRecord, page.project_id)
        if project is not None:
            project.updated_at = page.updated_at

    @staticmethod
    def _append_revision(
        session: Session, page: PageRecord, html: str, source: str
    ) -> RevisionRecord:
        expected_version = page.version
        next_version = expected_version + 1
        revision_id = new_id()
        created_at = utcnow()
        revision = RevisionRecord(
            id=revision_id,
            page_id=page.id,
            sequence=next_version,
            html=html,
            source=source,
            parent_revision_id=page.current_revision_id,
            created_at=created_at,
        )
        result = session.execute(
            update(PageRecord)
            .where(PageRecord.id == page.id, PageRecord.version == expected_version)
            .values(
                version=next_version,
                current_revision_id=revision_id,
                updated_at=created_at,
            )
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            current_version = session.scalar(
                select(PageRecord.version).where(PageRecord.id == page.id)
            )
            raise VersionConflictError(current_version or expected_version)
        session.add(revision)
        page.version = next_version
        page.current_revision_id = revision_id
        page.updated_at = created_at
        return revision

    @staticmethod
    def _current_revision(session: Session, page: PageRecord) -> RevisionRecord | None:
        return (
            session.get(RevisionRecord, page.current_revision_id)
            if page.current_revision_id
            else None
        )

    @staticmethod
    def _project_summary(project: ProjectRecord, page_count: int) -> dict[str, Any]:
        return {
            "id": project.id,
            "name": project.name,
            "page_count": page_count,
            "created_at": isoformat_utc(project.created_at),
            "updated_at": isoformat_utc(project.updated_at),
            "archived_at": (
                isoformat_utc(project.archived_at) if project.archived_at else None
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
            **self._project_summary(project, len(pages)),
            "pages": [self._page_snapshot(session, page) for page in pages],
        }

    def _page_snapshot(self, session: Session, page: PageRecord) -> dict[str, Any]:
        revision = self._current_revision(session, page)
        result: dict[str, Any] = {
            "id": page.id,
            "project_id": page.project_id,
            "name": page.name,
            "slug": page.slug,
            "version": page.version,
            "current_revision_id": page.current_revision_id,
            "created_at": isoformat_utc(page.created_at),
            "updated_at": isoformat_utc(page.updated_at),
        }
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
            "created_at": isoformat_utc(revision.created_at),
        }
