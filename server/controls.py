"""Cross-cutting request controls: idempotency, rate limits, and audit events."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any, TypeVar

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from server.models import (
    AuditEventRecord,
    IdempotencyRecord,
    RateLimitRecord,
    utcnow,
)

T = TypeVar("T", bound=dict[str, Any])


class IdempotencyConflictError(RuntimeError):
    pass


class RateLimitExceededError(RuntimeError):
    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__("Too many requests; try again shortly")


def _payload_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _window_start(now: datetime) -> datetime:
    value = now.astimezone(UTC)
    return value.replace(second=0, microsecond=0)


class RequestControlService:
    def __init__(self, sessions: sessionmaker[Session]):
        self._sessions = sessions

    def execute_idempotent(
        self,
        owner_id: str,
        scope: str,
        key: str | None,
        payload: dict[str, Any],
        work: Callable[[], T],
    ) -> T:
        if not key:
            return work()
        clean_key = key.strip()
        if not clean_key or len(clean_key) > 128:
            raise IdempotencyConflictError(
                "Idempotency-Key must be 1 to 128 characters"
            )
        request_hash = _payload_hash(payload)
        existing = self._reserve(owner_id, scope, clean_key, request_hash)
        if existing is not None:
            return existing
        try:
            response = work()
        except Exception:
            self._release(owner_id, scope, clean_key)
            raise
        with self._sessions.begin() as session:
            record = self._idempotency_record(session, owner_id, scope, clean_key)
            if record is not None:
                record.status = "completed"
                record.response = response
                record.updated_at = utcnow()
        return response

    def recover_stale_records(self) -> None:
        """Release interrupted reservations and prune expired control windows."""
        now = utcnow()
        with self._sessions.begin() as session:
            session.execute(
                delete(IdempotencyRecord).where(
                    (IdempotencyRecord.status == "pending")
                    | (IdempotencyRecord.created_at < now - timedelta(hours=24))
                )
            )
            session.execute(
                delete(RateLimitRecord).where(
                    RateLimitRecord.window_start < now - timedelta(minutes=2)
                )
            )

    def check_rate_limit(
        self, scope: str, identity: str, limit: int, *, now: datetime | None = None
    ) -> None:
        window = _window_start(now or utcnow())
        try:
            with self._sessions.begin() as session:
                record = session.scalar(
                    select(RateLimitRecord)
                    .where(
                        RateLimitRecord.scope == scope,
                        RateLimitRecord.identity == identity,
                        RateLimitRecord.window_start == window,
                    )
                    .with_for_update()
                )
                if record is None:
                    session.add(
                        RateLimitRecord(
                            scope=scope,
                            identity=identity,
                            window_start=window,
                            count=1,
                        )
                    )
                elif record.count >= limit:
                    raise RateLimitExceededError()
                else:
                    record.count += 1
        except IntegrityError:
            # A concurrent first request created the window; retry against that row.
            self.check_rate_limit(scope, identity, limit, now=now)

    def audit(
        self,
        owner_id: str | None,
        action: str,
        status_code: int,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self._sessions.begin() as session:
            session.add(
                AuditEventRecord(
                    owner_id=owner_id,
                    action=action[:160],
                    status_code=status_code,
                    metadata_json=metadata or {},
                )
            )

    def list_audit_events(self, owner_id: str) -> list[dict[str, Any]]:
        with self._sessions() as session:
            records = session.scalars(
                select(AuditEventRecord)
                .where(AuditEventRecord.owner_id == owner_id)
                .order_by(AuditEventRecord.created_at.desc())
                .limit(100)
            )
            return [
                {
                    "action": record.action,
                    "status_code": record.status_code,
                    "metadata": record.metadata_json,
                }
                for record in records
            ]

    def _reserve(
        self, owner_id: str, scope: str, key: str, request_hash: str
    ) -> dict[str, Any] | None:
        try:
            with self._sessions.begin() as session:
                existing = self._idempotency_record(session, owner_id, scope, key)
                if existing is not None:
                    return self._replay(existing, request_hash)
                session.add(
                    IdempotencyRecord(
                        owner_id=owner_id,
                        scope=scope,
                        key=key,
                        request_hash=request_hash,
                        status="pending",
                    )
                )
            return None
        except IntegrityError:
            with self._sessions() as session:
                existing = self._idempotency_record(session, owner_id, scope, key)
                if existing is None:  # pragma: no cover - defensive database anomaly
                    raise
                return self._replay(existing, request_hash)

    @staticmethod
    def _replay(record: IdempotencyRecord, request_hash: str) -> dict[str, Any]:
        if record.request_hash != request_hash:
            raise IdempotencyConflictError(
                "Idempotency-Key was already used with a different request"
            )
        if record.status != "completed" or record.response is None:
            raise IdempotencyConflictError("A request with this key is still running")
        return record.response

    def _release(self, owner_id: str, scope: str, key: str) -> None:
        with self._sessions.begin() as session:
            session.execute(
                delete(IdempotencyRecord).where(
                    IdempotencyRecord.owner_id == owner_id,
                    IdempotencyRecord.scope == scope,
                    IdempotencyRecord.key == key,
                )
            )

    @staticmethod
    def _idempotency_record(
        session: Session, owner_id: str, scope: str, key: str
    ) -> IdempotencyRecord | None:
        return session.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.owner_id == owner_id,
                IdempotencyRecord.scope == scope,
                IdempotencyRecord.key == key,
            )
        )
