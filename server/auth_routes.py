"""HTTP boundary for first-party account and session authentication."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from server.auth import (
    SESSION_COOKIE,
    AuthenticationError,
    AuthService,
    EmailAlreadyRegisteredError,
    Principal,
    principal_snapshot,
)
from server.concurrency import offload

router = APIRouter(prefix="/api/auth", tags=["auth"])


class CredentialsRequest(BaseModel):
    email: str
    password: str


def _auth(request: Request) -> AuthService:
    return request.app.state.auth


def _set_session_cookie(response: Response, request: Request, token: str) -> None:
    config = request.app.state.client.config
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        secure=config.session_cookie_secure,
        samesite="lax",
        max_age=config.session_hours * 60 * 60,
        path="/",
    )


async def require_principal(request: Request) -> Principal:
    principal = await offload(
        _auth(request).authenticate, request.cookies.get(SESSION_COOKIE)
    )
    if principal is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return principal


Authenticated = Annotated[Principal, Depends(require_principal)]


@router.post("/register", status_code=201)
async def register(
    request: Request, response: Response, body: CredentialsRequest
) -> dict[str, str]:
    try:
        principal, token = await offload(
            _auth(request).register, body.email, body.password
        )
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AuthenticationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _set_session_cookie(response, request, token)
    return principal_snapshot(principal)


@router.post("/login")
async def login(
    request: Request, response: Response, body: CredentialsRequest
) -> dict[str, str]:
    try:
        principal, token = await offload(
            _auth(request).login, body.email, body.password
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    _set_session_cookie(response, request, token)
    return principal_snapshot(principal)


@router.get("/me")
async def current_user(
    principal: Authenticated,
) -> dict[str, str]:
    return principal_snapshot(principal)


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response) -> None:
    await offload(_auth(request).logout, request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE, path="/", samesite="lax")
