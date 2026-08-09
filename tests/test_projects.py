from __future__ import annotations

import pytest

from server.database import Database
from server.models import UserRecord
from server.projects import (
    ProjectService,
    ProjectValidationError,
    VersionConflictError,
)

OWNER_ID = "00000000-0000-0000-0000-000000000010"


def _add_owner(database: Database, owner_id: str = OWNER_ID) -> None:
    with database.sessions.begin() as session:
        session.add(
            UserRecord(
                id=owner_id,
                email=f"{owner_id}@example.test",
                password_hash="!test-account",
            )
        )


@pytest.fixture()
def projects(tmp_path) -> ProjectService:
    database = Database.from_url(f"sqlite:///{tmp_path / 'projects.db'}")
    _add_owner(database)
    service = ProjectService(database.sessions)
    try:
        yield service
    finally:
        database.close()


def test_create_and_list_project(projects: ProjectService) -> None:
    created = projects.create_project(OWNER_ID, "Launch site", "<html>one</html>")

    assert created["name"] == "Launch site"
    assert created["page_count"] == 1
    assert created["pages"][0]["html"] == "<html>one</html>"
    assert created["pages"][0]["version"] == 1
    assert projects.list_projects(OWNER_ID)[0]["id"] == created["id"]


def test_project_survives_service_restart(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'projects.db'}"
    first_database = Database.from_url(url)
    _add_owner(first_database)
    first = ProjectService(first_database.sessions)
    created = first.create_project(OWNER_ID, "Persistent", "<main>saved</main>")

    restarted_database = Database.from_url(url)
    restarted = ProjectService(restarted_database.sessions)

    assert restarted.get_project(OWNER_ID, created["id"])["pages"][0]["html"] == (
        "<main>saved</main>"
    )
    first_database.close()
    restarted_database.close()


def test_save_page_creates_immutable_revision(projects: ProjectService) -> None:
    page = projects.create_project(OWNER_ID, "History", "v1")["pages"][0]

    saved = projects.save_page(
        OWNER_ID, page["id"], "v2", expected_version=1, source="autosave"
    )

    assert saved["version"] == 2
    assert saved["html"] == "v2"
    revisions = projects.list_revisions(OWNER_ID, page["id"])
    assert [revision["sequence"] for revision in revisions] == [2, 1]
    assert revisions[0]["source"] == "autosave"


def test_noop_save_does_not_create_revision(projects: ProjectService) -> None:
    page = projects.create_project(OWNER_ID, "No-op", "same")["pages"][0]

    saved = projects.save_page(OWNER_ID, page["id"], "same", expected_version=1)

    assert saved["version"] == 1
    assert len(projects.list_revisions(OWNER_ID, page["id"])) == 1


def test_stale_save_reports_current_version(projects: ProjectService) -> None:
    page = projects.create_project(OWNER_ID, "Conflict", "v1")["pages"][0]
    projects.save_page(OWNER_ID, page["id"], "v2", expected_version=1)

    with pytest.raises(VersionConflictError) as exc:
        projects.save_page(OWNER_ID, page["id"], "stale", expected_version=1)

    assert exc.value.current_version == 2
    assert projects.get_page(OWNER_ID, page["id"])["html"] == "v2"


def test_restore_creates_a_new_revision(projects: ProjectService) -> None:
    page = projects.create_project(OWNER_ID, "Restore", "v1")["pages"][0]
    first_revision = projects.list_revisions(OWNER_ID, page["id"])[0]
    projects.save_page(OWNER_ID, page["id"], "v2", expected_version=1)

    restored = projects.restore_revision(
        OWNER_ID, page["id"], first_revision["id"], expected_version=2
    )

    assert restored["html"] == "v1"
    assert restored["version"] == 3
    assert projects.list_revisions(OWNER_ID, page["id"])[0]["source"] == "restore"


def test_project_name_validation(projects: ProjectService) -> None:
    with pytest.raises(ProjectValidationError):
        projects.create_project(OWNER_ID, "   ")


def test_search_and_rename_projects(projects: ProjectService) -> None:
    launch = projects.create_project(OWNER_ID, "Launch Site")
    projects.create_project(OWNER_ID, "Portfolio")

    renamed = projects.rename_project(OWNER_ID, launch["id"], "Product Launch")

    assert renamed["name"] == "Product Launch"
    assert [
        item["id"] for item in projects.list_projects(OWNER_ID, search="LAUNCH")
    ] == [launch["id"]]


def test_duplicate_project_copies_current_page_state(projects: ProjectService) -> None:
    source = projects.create_project(OWNER_ID, "Original", "v1")
    source_page = source["pages"][0]
    projects.save_page(OWNER_ID, source_page["id"], "v2", expected_version=1)

    duplicate = projects.duplicate_project(OWNER_ID, source["id"])
    duplicate_page = duplicate["pages"][0]

    assert duplicate["name"] == "Original Copy"
    assert duplicate["id"] != source["id"]
    assert duplicate_page["id"] != source_page["id"]
    assert duplicate_page["html"] == "v2"
    assert duplicate_page["version"] == 1
    assert (
        projects.list_revisions(OWNER_ID, duplicate_page["id"])[0]["source"]
        == "duplicate"
    )


def test_archive_hides_project_by_default(projects: ProjectService) -> None:
    created = projects.create_project(OWNER_ID, "Archive")

    archived = projects.archive_project(OWNER_ID, created["id"])

    assert archived["archived_at"] is not None
    assert projects.list_projects(OWNER_ID) == []
    assert len(projects.list_projects(OWNER_ID, include_archived=True)) == 1
    assert (
        projects.archive_project(OWNER_ID, created["id"])["archived_at"]
        == archived["archived_at"]
    )


def test_projects_and_pages_are_isolated_by_owner(tmp_path) -> None:
    database = Database.from_url(f"sqlite:///{tmp_path / 'isolation.db'}")
    other_id = "00000000-0000-0000-0000-000000000011"
    _add_owner(database)
    _add_owner(database, other_id)
    projects = ProjectService(database.sessions)
    created = projects.create_project(OWNER_ID, "Private", "secret")

    assert projects.list_projects(other_id) == []
    with pytest.raises(LookupError):
        projects.get_project(other_id, created["id"])
    with pytest.raises(LookupError):
        projects.get_page(other_id, created["pages"][0]["id"])
    database.close()


def test_named_checkpoint_and_duplicate_from_revision(
    projects: ProjectService,
) -> None:
    page = projects.create_project(OWNER_ID, "Source", "v1")["pages"][0]
    projects.save_page(OWNER_ID, page["id"], "v2", expected_version=1)
    checkpoint_page = projects.create_checkpoint(
        OWNER_ID, page["id"], "Before launch", expected_version=2
    )
    checkpoint = projects.list_revisions(OWNER_ID, page["id"])[0]

    assert checkpoint_page["version"] == 3
    assert checkpoint["name"] == "Before launch"
    assert checkpoint["source"] == "checkpoint"
    duplicate = projects.duplicate_from_revision(
        OWNER_ID,
        page["id"],
        checkpoint["id"],
        name="Launch branch",
    )
    assert duplicate["name"] == "Launch branch"
    assert duplicate["pages"][0]["html"] == "v2"
    assert duplicate["pages"][0]["version"] == 1
