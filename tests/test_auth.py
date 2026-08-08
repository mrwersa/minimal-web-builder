from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select

from server.auth import (
    AuthenticationError,
    AuthService,
    EmailAlreadyRegisteredError,
)
from server.database import Database
from server.models import UserRecord, UserSessionRecord, utcnow


@pytest.fixture()
def auth(tmp_path):
    database = Database.from_url(f"sqlite:///{tmp_path / 'auth.db'}")
    try:
        yield AuthService(database.sessions), database
    finally:
        database.close()


def test_registration_hashes_password_and_session_token(auth) -> None:
    service, database = auth

    principal, token = service.register(" Owner@Example.Test ", "correct horse battery")

    assert principal.email == "owner@example.test"
    assert service.authenticate(token) == principal
    with database.sessions() as session:
        user = session.scalar(select(UserRecord).where(UserRecord.id == principal.id))
        stored_session = session.scalar(select(UserSessionRecord))
        assert user is not None
        assert user.password_hash.startswith("$argon2id$")
        assert "correct horse battery" not in user.password_hash
        assert stored_session is not None
        assert stored_session.token_hash != token


def test_login_uses_generic_error_and_logout_revokes_session(auth) -> None:
    service, _database = auth
    principal, _ = service.register("owner@example.test", "correct horse battery")

    with pytest.raises(AuthenticationError, match="Invalid email or password"):
        service.login("unknown@example.test", "correct horse battery")
    with pytest.raises(AuthenticationError, match="Invalid email or password"):
        service.login("owner@example.test", "incorrect password")

    logged_in, token = service.login("OWNER@example.test", "correct horse battery")
    assert logged_in == principal
    service.logout(token)
    assert service.authenticate(token) is None


def test_registration_validates_credentials_and_email_uniqueness(auth) -> None:
    service, _database = auth

    with pytest.raises(AuthenticationError, match="valid email"):
        service.register("not-an-email", "correct horse battery")
    with pytest.raises(AuthenticationError, match="at least 12"):
        service.register("owner@example.test", "short")

    service.register("owner@example.test", "correct horse battery")
    with pytest.raises(EmailAlreadyRegisteredError):
        service.register("OWNER@example.test", "another secure password")


def test_expired_session_is_deleted(auth) -> None:
    service, database = auth
    _principal, token = service.register("owner@example.test", "correct horse battery")
    with database.sessions.begin() as session:
        record = session.scalar(select(UserSessionRecord))
        assert record is not None
        record.expires_at = utcnow() - timedelta(seconds=1)

    assert service.authenticate(token) is None
    with database.sessions() as session:
        assert session.scalar(select(UserSessionRecord)) is None
