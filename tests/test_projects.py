from __future__ import annotations

import pytest

from server.projects import (
    ProjectService,
    ProjectValidationError,
    VersionConflictError,
)


@pytest.fixture()
def projects(tmp_path) -> ProjectService:
    service = ProjectService.from_url(f"sqlite:///{tmp_path / 'projects.db'}")
    try:
        yield service
    finally:
        service.close()


def test_create_and_list_project(projects: ProjectService) -> None:
    created = projects.create_project("Launch site", "<html>one</html>")

    assert created["name"] == "Launch site"
    assert created["page_count"] == 1
    assert created["pages"][0]["html"] == "<html>one</html>"
    assert created["pages"][0]["version"] == 1
    assert projects.list_projects()[0]["id"] == created["id"]


def test_project_survives_service_restart(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'projects.db'}"
    first = ProjectService.from_url(url)
    created = first.create_project("Persistent", "<main>saved</main>")

    restarted = ProjectService.from_url(url)

    assert restarted.get_project(created["id"])["pages"][0]["html"] == (
        "<main>saved</main>"
    )


def test_save_page_creates_immutable_revision(projects: ProjectService) -> None:
    page = projects.create_project("History", "v1")["pages"][0]

    saved = projects.save_page(page["id"], "v2", expected_version=1, source="autosave")

    assert saved["version"] == 2
    assert saved["html"] == "v2"
    revisions = projects.list_revisions(page["id"])
    assert [revision["sequence"] for revision in revisions] == [2, 1]
    assert revisions[0]["source"] == "autosave"


def test_noop_save_does_not_create_revision(projects: ProjectService) -> None:
    page = projects.create_project("No-op", "same")["pages"][0]

    saved = projects.save_page(page["id"], "same", expected_version=1)

    assert saved["version"] == 1
    assert len(projects.list_revisions(page["id"])) == 1


def test_stale_save_reports_current_version(projects: ProjectService) -> None:
    page = projects.create_project("Conflict", "v1")["pages"][0]
    projects.save_page(page["id"], "v2", expected_version=1)

    with pytest.raises(VersionConflictError) as exc:
        projects.save_page(page["id"], "stale", expected_version=1)

    assert exc.value.current_version == 2
    assert projects.get_page(page["id"])["html"] == "v2"


def test_restore_creates_a_new_revision(projects: ProjectService) -> None:
    page = projects.create_project("Restore", "v1")["pages"][0]
    first_revision = projects.list_revisions(page["id"])[0]
    projects.save_page(page["id"], "v2", expected_version=1)

    restored = projects.restore_revision(
        page["id"], first_revision["id"], expected_version=2
    )

    assert restored["html"] == "v1"
    assert restored["version"] == 3
    assert projects.list_revisions(page["id"])[0]["source"] == "restore"


def test_project_name_validation(projects: ProjectService) -> None:
    with pytest.raises(ProjectValidationError):
        projects.create_project("   ")


def test_archive_hides_project_by_default(projects: ProjectService) -> None:
    created = projects.create_project("Archive")

    archived = projects.archive_project(created["id"])

    assert archived["archived_at"] is not None
    assert projects.list_projects() == []
    assert len(projects.list_projects(include_archived=True)) == 1
