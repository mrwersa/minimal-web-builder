"""User credentials and opaque server-side session management."""

from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from server.models import (
    LEGACY_OWNER_ID,
    ProjectRecord,
    UserRecord,
    UserSessionRecord,
    utcnow,
)

SESSION_COOKIE = "mwb_session"
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_PASSWORD_HASHER = PasswordHasher(time_cost=2, memory_cost=19_456, parallelism=1)


class AuthenticationError(ValueError):
    pass


class EmailAlreadyRegisteredError(AuthenticationError):
    pass


@dataclass(frozen=True)
class Principal:
    id: str
    email: str


def _normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if len(normalized) > 320 or not _EMAIL_RE.fullmatch(normalized):
        raise AuthenticationError("Enter a valid email address")
    return normalized


def _validate_password(password: str) -> str:
    if len(password) < 12:
        raise AuthenticationError("Password must be at least 12 characters")
    if len(password) > 128:
        raise AuthenticationError("Password must be at most 128 characters")
    return password


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class AuthService:
    def __init__(self, sessions: sessionmaker[Session], *, session_hours: int = 168):
        self._sessions = sessions
        self._session_lifetime = timedelta(hours=session_hours)

    def register(self, email: str, password: str) -> tuple[Principal, str]:
        normalized_email = _normalize_email(email)
        clean_password = _validate_password(password)
        try:
            with self._sessions.begin() as session:
                user = UserRecord(
                    email=normalized_email,
                    password_hash=_PASSWORD_HASHER.hash(clean_password),
                )
                session.add(user)
                session.flush()
                session.execute(
                    update(ProjectRecord)
                    .where(ProjectRecord.owner_id == LEGACY_OWNER_ID)
                    .values(owner_id=user.id)
                )
                token = self._create_session(session, user)
                return self._principal(user), token
        except IntegrityError as exc:
            raise EmailAlreadyRegisteredError("Email is already registered") from exc

    def login(self, email: str, password: str) -> tuple[Principal, str]:
        normalized_email = _normalize_email(email)
        with self._sessions.begin() as session:
            user = session.scalar(
                select(UserRecord).where(UserRecord.email == normalized_email)
            )
            if user is None or not self._password_matches(user.password_hash, password):
                raise AuthenticationError("Invalid email or password")
            if _PASSWORD_HASHER.check_needs_rehash(user.password_hash):
                user.password_hash = _PASSWORD_HASHER.hash(password)
            token = self._create_session(session, user)
            return self._principal(user), token

    def authenticate(self, token: str | None) -> Principal | None:
        if not token:
            return None
        with self._sessions.begin() as session:
            record = session.scalar(
                select(UserSessionRecord).where(
                    UserSessionRecord.token_hash == _token_hash(token)
                )
            )
            if record is None:
                return None
            if _as_utc(record.expires_at) <= utcnow():
                session.delete(record)
                return None
            user = session.get(UserRecord, record.user_id)
            return self._principal(user) if user else None

    def logout(self, token: str | None) -> None:
        if not token:
            return
        with self._sessions.begin() as session:
            session.execute(
                delete(UserSessionRecord).where(
                    UserSessionRecord.token_hash == _token_hash(token)
                )
            )

    def _create_session(self, session: Session, user: UserRecord) -> str:
        token = secrets.token_urlsafe(32)
        session.add(
            UserSessionRecord(
                user_id=user.id,
                token_hash=_token_hash(token),
                expires_at=utcnow() + self._session_lifetime,
            )
        )
        return token

    @staticmethod
    def _password_matches(password_hash: str, password: str) -> bool:
        if len(password) > 128:
            return False
        try:
            return _PASSWORD_HASHER.verify(password_hash, password)
        except VerificationError:
            return False

    @staticmethod
    def _principal(user: UserRecord) -> Principal:
        return Principal(id=user.id, email=user.email)


def principal_snapshot(principal: Principal) -> dict[str, str]:
    return {"id": principal.id, "email": principal.email}
