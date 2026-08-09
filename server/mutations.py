"""Shared authenticated mutation execution at the HTTP boundary."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from fastapi import Request

from server.auth import Principal
from server.concurrency import offload
from server.controls import RequestControlService

T = TypeVar("T", bound=dict[str, Any])


async def run_idempotent(
    request: Request,
    principal: Principal,
    scope: str,
    payload: dict[str, Any],
    work: Callable[[], T],
) -> T:
    controls: RequestControlService = request.app.state.controls
    return await offload(
        controls.execute_idempotent,
        principal.id,
        scope,
        request.headers.get("Idempotency-Key"),
        payload,
        work,
    )
