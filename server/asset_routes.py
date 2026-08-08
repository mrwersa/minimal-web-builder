"""Authenticated HTTP contracts for reusable templates and layout DNA."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from server.assets import ReusableAssetService
from server.auth_routes import Authenticated
from server.concurrency import offload
from src.layout_dna import extract_layout_dna

router = APIRouter(prefix="/api", tags=["reusable-assets"])


class TemplateSaveRequest(BaseModel):
    name: str
    html: str


class SaveDnaRequest(BaseModel):
    html: str


def _assets(request: Request) -> ReusableAssetService:
    return request.app.state.assets


@router.get("/templates")
async def templates_list(request: Request, principal: Authenticated) -> dict[str, Any]:
    templates = await offload(_assets(request).list_templates, principal.id)
    return {"templates": templates}


@router.post("/templates")
async def templates_save(
    request: Request, body: TemplateSaveRequest, principal: Authenticated
) -> dict[str, str]:
    saved = await offload(
        _assets(request).save_template, principal.id, body.name, body.html
    )
    return {"saved": saved}


@router.get("/templates/{name}")
async def templates_load(
    request: Request, name: str, principal: Authenticated
) -> dict[str, str]:
    html = await offload(_assets(request).load_template, principal.id, name)
    return {"name": name, "html": html}


@router.delete("/templates/{name}")
async def templates_delete(
    request: Request, name: str, principal: Authenticated
) -> dict[str, str]:
    await offload(_assets(request).delete_template, principal.id, name)
    return {"deleted": name}


@router.get("/layout-dnas")
async def dnas_list(request: Request, principal: Authenticated) -> dict[str, Any]:
    return {"dnas": await offload(_assets(request).list_dnas, principal.id)}


@router.post("/layout-dnas")
async def dnas_save(
    request: Request, body: SaveDnaRequest, principal: Authenticated
) -> dict[str, Any]:
    dna = await offload(extract_layout_dna, body.html)
    return await offload(_assets(request).save_dna, principal.id, dna)
