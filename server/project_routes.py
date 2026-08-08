"""HTTP contracts for project and revision workflows."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from server.auth_routes import Authenticated
from server.concurrency import offload
from server.projects import ProjectService

router = APIRouter(prefix="/api", tags=["projects"])


class ProjectCreateRequest(BaseModel):
    name: str
    html: str = ""


class ProjectUpdateRequest(BaseModel):
    name: str


class ProjectDuplicateRequest(BaseModel):
    name: str | None = None


class PageSaveRequest(BaseModel):
    html: str
    expected_version: int
    source: str = "autosave"


class RevisionRestoreRequest(BaseModel):
    expected_version: int


def _projects(request: Request) -> ProjectService:
    return request.app.state.projects


@router.get("/projects")
async def projects_list(
    request: Request,
    principal: Authenticated,
    include_archived: bool = False,
    search: str = Query(default="", max_length=120),
) -> dict[str, Any]:
    projects = await offload(
        _projects(request).list_projects,
        principal.id,
        include_archived=include_archived,
        search=search,
    )
    return {"projects": projects}


@router.post("/projects", status_code=201)
async def projects_create(
    request: Request,
    body: ProjectCreateRequest,
    principal: Authenticated,
) -> dict[str, Any]:
    return await offload(
        _projects(request).create_project, principal.id, body.name, body.html
    )


@router.get("/projects/{project_id}")
async def projects_get(
    request: Request,
    project_id: str,
    principal: Authenticated,
) -> dict[str, Any]:
    return await offload(_projects(request).get_project, principal.id, project_id)


@router.patch("/projects/{project_id}")
async def projects_update(
    request: Request,
    project_id: str,
    body: ProjectUpdateRequest,
    principal: Authenticated,
) -> dict[str, Any]:
    return await offload(
        _projects(request).rename_project, principal.id, project_id, body.name
    )


@router.post("/projects/{project_id}/duplicate", status_code=201)
async def projects_duplicate(
    request: Request,
    project_id: str,
    body: ProjectDuplicateRequest,
    principal: Authenticated,
) -> dict[str, Any]:
    return await offload(
        _projects(request).duplicate_project, principal.id, project_id, name=body.name
    )


@router.delete("/projects/{project_id}")
async def projects_archive(
    request: Request,
    project_id: str,
    principal: Authenticated,
) -> dict[str, Any]:
    return await offload(_projects(request).archive_project, principal.id, project_id)


@router.get("/pages/{page_id}")
async def pages_get(
    request: Request,
    page_id: str,
    principal: Authenticated,
) -> dict[str, Any]:
    return await offload(_projects(request).get_page, principal.id, page_id)


@router.put("/pages/{page_id}/document")
async def pages_save(
    request: Request,
    page_id: str,
    body: PageSaveRequest,
    principal: Authenticated,
) -> dict[str, Any]:
    return await offload(
        _projects(request).save_page,
        principal.id,
        page_id,
        body.html,
        expected_version=body.expected_version,
        source=body.source,
    )


@router.get("/pages/{page_id}/revisions")
async def revisions_list(
    request: Request,
    page_id: str,
    principal: Authenticated,
) -> dict[str, Any]:
    revisions = await offload(_projects(request).list_revisions, principal.id, page_id)
    return {"revisions": revisions}


@router.post("/pages/{page_id}/revisions/{revision_id}/restore")
async def revisions_restore(
    request: Request,
    page_id: str,
    revision_id: str,
    body: RevisionRestoreRequest,
    principal: Authenticated,
) -> dict[str, Any]:
    return await offload(
        _projects(request).restore_revision,
        principal.id,
        page_id,
        revision_id,
        expected_version=body.expected_version,
    )
