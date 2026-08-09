"""HTTP middleware for rate limiting, request IDs, and mutation auditing."""

from __future__ import annotations

import logging
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse

from server.auth import SESSION_COOKIE, AuthService
from server.concurrency import offload
from server.controls import RateLimitExceededError, RequestControlService

logger = logging.getLogger(__name__)
_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_AUTH_RATE_PATHS = {"/api/auth/login", "/api/auth/register"}
_GENERATION_RATE_PATHS = {"/api/generate", "/api/generate-section", "/api/chat"}


async def enforce_request_controls(request: Request, call_next):
    controls: RequestControlService | None = getattr(
        request.app.state, "controls", None
    )
    auth: AuthService | None = getattr(request.app.state, "auth", None)
    principal = None
    if auth is not None:
        principal = await offload(
            auth.authenticate, request.cookies.get(SESSION_COOKIE)
        )
    request.state.principal = principal
    path = request.url.path
    request_id = (request.headers.get("X-Request-ID") or str(uuid.uuid4()))[:128]
    config = getattr(getattr(request.app.state, "client", None), "config", None)
    try:
        if controls is not None and config is not None:
            if path in _AUTH_RATE_PATHS:
                identity = request.client.host if request.client else "unknown"
                await offload(
                    controls.check_rate_limit,
                    "auth",
                    identity,
                    config.auth_rate_limit_per_minute,
                )
            elif path in _GENERATION_RATE_PATHS:
                identity = (
                    principal.id
                    if principal
                    else (request.client.host if request.client else "unknown")
                )
                await offload(
                    controls.check_rate_limit,
                    "generation",
                    identity,
                    config.generation_rate_limit_per_minute,
                )
    except RateLimitExceededError as exc:
        response = JSONResponse(
            status_code=429,
            content={"detail": str(exc)},
            headers={"Retry-After": str(exc.retry_after)},
        )
    else:
        response = await call_next(request)

    response.headers["X-Request-ID"] = request_id
    if controls is not None and request.method in _MUTATING_METHODS:
        try:
            await offload(
                controls.audit,
                principal.id if principal else None,
                f"{request.method} {path}",
                response.status_code,
                {
                    "request_id": request_id,
                    "idempotency_key": (request.headers.get("Idempotency-Key") or "")[
                        :128
                    ]
                    or None,
                },
            )
        except Exception:
            logger.exception("Failed to persist audit event")
    return response
