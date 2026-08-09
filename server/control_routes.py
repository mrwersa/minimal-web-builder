"""Owner-scoped inspection endpoints for request controls."""

from typing import Any

from fastapi import APIRouter, Request

from server.auth_routes import Authenticated
from server.concurrency import offload

router = APIRouter(prefix="/api", tags=["request-controls"])


@router.get("/audit-events")
async def audit_events(request: Request, principal: Authenticated) -> dict[str, Any]:
    return {
        "events": await offload(
            request.app.state.controls.list_audit_events, principal.id
        )
    }
