from __future__ import annotations

from datetime import UTC, datetime

import pytest

from server.controls import (
    IdempotencyConflictError,
    RateLimitExceededError,
    RequestControlService,
    _payload_hash,
)
from server.database import Database
from server.models import UserRecord

OWNER_ID = "00000000-0000-0000-0000-000000000040"


@pytest.fixture()
def controls(tmp_path):
    database = Database.from_url(f"sqlite:///{tmp_path / 'controls.db'}")
    with database.sessions.begin() as session:
        session.add(
            UserRecord(
                id=OWNER_ID,
                email="owner@example.test",
                password_hash="!test-account",
            )
        )
    try:
        yield RequestControlService(database.sessions)
    finally:
        database.close()


def test_idempotency_replays_completed_response(
    controls: RequestControlService,
) -> None:
    calls = 0

    def work():
        nonlocal calls
        calls += 1
        return {"id": "project-1"}

    first = controls.execute_idempotent(
        OWNER_ID, "project.create", "request-1", {"name": "One"}, work
    )
    replay = controls.execute_idempotent(
        OWNER_ID, "project.create", "request-1", {"name": "One"}, work
    )

    assert first == replay == {"id": "project-1"}
    assert calls == 1


def test_idempotency_rejects_key_reuse_with_different_payload(
    controls: RequestControlService,
) -> None:
    controls.execute_idempotent(
        OWNER_ID, "project.create", "request-1", {"name": "One"}, lambda: {"id": "1"}
    )

    with pytest.raises(IdempotencyConflictError, match="different request"):
        controls.execute_idempotent(
            OWNER_ID,
            "project.create",
            "request-1",
            {"name": "Two"},
            lambda: {"id": "2"},
        )


def test_failed_idempotent_work_can_be_retried(controls: RequestControlService) -> None:
    def fail():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        controls.execute_idempotent(OWNER_ID, "generation.chat", "request-1", {}, fail)

    assert controls.execute_idempotent(
        OWNER_ID, "generation.chat", "request-1", {}, lambda: {"ok": True}
    ) == {"ok": True}


def test_rate_limit_uses_fixed_minute_windows(controls: RequestControlService) -> None:
    now = datetime(2026, 8, 9, 12, 0, 10, tzinfo=UTC)
    controls.check_rate_limit("auth", "127.0.0.1", 2, now=now)
    controls.check_rate_limit("auth", "127.0.0.1", 2, now=now)
    with pytest.raises(RateLimitExceededError):
        controls.check_rate_limit("auth", "127.0.0.1", 2, now=now)

    controls.check_rate_limit(
        "auth", "127.0.0.1", 2, now=datetime(2026, 8, 9, 12, 1, tzinfo=UTC)
    )


def test_audit_events_are_owner_scoped(controls: RequestControlService) -> None:
    controls.audit(OWNER_ID, "POST /api/projects", 201, {"request_id": "one"})
    controls.audit(None, "POST /api/auth/login", 401)

    assert controls.list_audit_events(OWNER_ID) == [
        {
            "action": "POST /api/projects",
            "status_code": 201,
            "metadata": {"request_id": "one"},
        }
    ]


def test_startup_releases_pending_idempotency_reservations(
    controls: RequestControlService,
) -> None:
    with pytest.raises(IdempotencyConflictError, match="still running"):
        controls._reserve(OWNER_ID, "project.create", "pending", _payload_hash({}))
        controls.execute_idempotent(
            OWNER_ID,
            "project.create",
            "pending",
            {},
            lambda: {"id": "never"},
        )

    controls.recover_stale_records()
    assert controls.execute_idempotent(
        OWNER_ID, "project.create", "pending", {}, lambda: {"id": "created"}
    ) == {"id": "created"}
