"""Durable lifecycle for all generation operations and chat checkpoints."""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from typing import Any, TypeVar

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from server.agent import run_agent, set_client
from server.documents import validate_editor_document
from server.models import ConversationRecord, GenerationJobRecord, utcnow
from server.runtime import GenerationClient

T = TypeVar("T", bound=dict[str, Any])

#: Upper bound on jobs scanned when aggregating :meth:`job_stats`, so a long
#: history cannot make the stats endpoint unboundedly expensive.
STATS_WINDOW = 1000

FAILURE_PROVIDER = "provider"
FAILURE_TIMEOUT = "timeout"
FAILURE_VALIDATION = "validation"
FAILURE_INTERRUPTED = "interrupted"
FAILURE_INTERNAL = "internal"


class ConversationValidationError(ValueError):
    pass


def _summarize(records: list[GenerationJobRecord]) -> dict[str, Any]:
    succeeded = sum(1 for item in records if item.status == "succeeded")
    failed = sum(1 for item in records if item.status == "failed")
    running = sum(1 for item in records if item.status == "running")
    # Latency is only meaningful for jobs that ran to completion; a failure can
    # return in milliseconds and would otherwise flatter the percentiles.
    durations = [
        item.duration_ms
        for item in records
        if item.status == "succeeded" and item.duration_ms is not None
    ]
    settled = succeeded + failed
    return {
        "total": len(records),
        "succeeded": succeeded,
        "failed": failed,
        "running": running,
        "success_rate": round(succeeded / settled, 4) if settled else None,
        "p50_ms": _percentile(durations, 50),
        "p95_ms": _percentile(durations, 95),
    }


def classify_failure(exc: BaseException) -> str:
    """Bucket a generation failure by cause.

    The exit metric for Phase 3 is a failure *rate*, which is only actionable
    when a provider outage can be told apart from a rejected document. Provider
    errors reach us as an HTTP 502 raised by the route, because
    ``src.generation`` converts provider exceptions into an ``API error:``
    string rather than propagating them.
    """
    message = str(getattr(exc, "detail", None) or exc)
    lowered = message.lower()
    if "timed out" in lowered or "timeout" in lowered:
        return FAILURE_TIMEOUT
    status = getattr(exc, "status_code", None)
    if status == 502 or lowered.startswith("api error:"):
        return FAILURE_PROVIDER
    if isinstance(exc, ValueError) or status == 400:
        return FAILURE_VALIDATION
    return FAILURE_INTERNAL


def _result_metrics(result: Any) -> dict[str, int]:
    """Summarize a generation result into counters worth trending over time."""
    if not isinstance(result, dict):
        return {}
    notes = result.get("notes") or result.get("validation_notes") or []
    return {
        "output_chars": len(result.get("html") or ""),
        "note_count": len(notes) if isinstance(notes, list) else 0,
        "safety_alert_count": len(result.get("safety_alerts") or []),
        "validation_error_count": len(result.get("validation_errors") or []),
    }


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _percentile(values: list[int], percentile: float) -> int | None:
    """Nearest-rank percentile — exact for the small samples we aggregate."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile / 100 * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]


def _thread_id(value: str) -> str:
    clean = value.strip()
    if not clean or len(clean) > 64:
        raise ConversationValidationError("Conversation ID must be 1 to 64 characters")
    return clean


def _message_snapshot(message: Any) -> dict[str, str]:
    if isinstance(message, dict):
        role = str(message.get("role", "assistant"))
        content = str(message.get("content", ""))
    else:
        role = str(getattr(message, "type", "assistant"))
        content = str(getattr(message, "content", ""))
    normalized_role = {"ai": "assistant", "human": "user"}.get(role, role)
    return {"role": normalized_role, "content": content}


class GenerationOrchestrator:
    def __init__(self, sessions: sessionmaker[Session]):
        self._sessions = sessions

    def execute(
        self,
        owner_id: str,
        operation: str,
        request: dict[str, Any],
        work: Callable[[], T],
        *,
        conversation_id: str | None = None,
    ) -> T:
        job_id = self._start_job(owner_id, operation, request, conversation_id)
        started = time.perf_counter()
        try:
            result = work()
        except Exception as exc:
            self._finish_job(
                job_id,
                status="failed",
                error=str(getattr(exc, "detail", None) or exc),
                failure_kind=classify_failure(exc),
                duration_ms=_elapsed_ms(started),
            )
            raise
        self._finish_job(
            job_id,
            status="succeeded",
            result=result,
            duration_ms=_elapsed_ms(started),
            metrics=_result_metrics(result),
        )
        return result

    def recover_interrupted_jobs(self) -> int:
        """Mark jobs left running by a stopped process as failed."""
        with self._sessions.begin() as session:
            result = session.execute(
                update(GenerationJobRecord)
                .where(GenerationJobRecord.status == "running")
                .values(
                    status="failed",
                    error="Generation interrupted by server restart",
                    failure_kind=FAILURE_INTERRUPTED,
                    finished_at=utcnow(),
                    updated_at=utcnow(),
                )
            )
            return result.rowcount

    def chat(
        self,
        owner_id: str,
        thread_id: str,
        user_input: str,
        current_code: str | None,
        settings: dict[str, Any],
        client: GenerationClient,
        target_node_id: str | None = None,
    ) -> dict[str, Any]:
        clean_thread_id = _thread_id(thread_id)
        conversation = self._get_or_create_conversation(owner_id, clean_thread_id)
        set_client(client)

        def work() -> dict[str, Any]:
            state = run_agent(
                user_input,
                thread_id=clean_thread_id,
                current_code=current_code or conversation.current_code,
                settings=settings,
                history=list(conversation.messages),
                target_node_id=target_node_id,
            )
            messages = [
                snapshot
                for item in state.get("messages", [])
                if (snapshot := _message_snapshot(item))["role"]
                in {"user", "assistant"}
            ]
            next_code = state.get("current_code")
            self._save_conversation(
                conversation.id,
                messages,
                next_code,
                (
                    conversation.document_json
                    if next_code == conversation.current_code
                    else None
                ),
            )
            return {
                "html": state.get("current_code"),
                "message": self._last_assistant_message(messages),
                "intent": state.get("intent"),
                "validation_errors": state.get("validation_errors", []),
                "validation_notes": state.get("validation_notes", []),
                "error": state.get("error"),
            }

        return self.execute(
            owner_id,
            "chat",
            {
                "thread_id": clean_thread_id,
                "message": user_input,
                "target_node_id": target_node_id,
            },
            work,
            conversation_id=conversation.id,
        )

    def get_conversation(self, owner_id: str, thread_id: str) -> dict[str, Any] | None:
        with self._sessions() as session:
            record = session.scalar(
                select(ConversationRecord).where(
                    ConversationRecord.owner_id == owner_id,
                    ConversationRecord.thread_id == _thread_id(thread_id),
                )
            )
            if record is None:
                return None
            return {
                "thread_id": record.thread_id,
                "messages": record.messages,
                "current_code": record.current_code,
                "document": record.document_json,
            }

    def checkpoint_document(
        self,
        owner_id: str,
        thread_id: str,
        user_message: str,
        assistant_message: str,
        code: str,
    ) -> str:
        conversation = self._get_or_create_conversation(owner_id, _thread_id(thread_id))
        messages = [
            *conversation.messages,
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_message},
        ]
        self._save_conversation(conversation.id, messages, code)
        return conversation.id

    def update_document(
        self,
        owner_id: str,
        thread_id: str,
        code: str,
        document: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        conversation = self._get_or_create_conversation(owner_id, _thread_id(thread_id))
        clean_document = validate_editor_document(document)
        if clean_document is None and conversation.current_code == code:
            clean_document = conversation.document_json
        self._save_conversation(
            conversation.id,
            list(conversation.messages),
            code,
            clean_document,
        )
        return {"thread_id": conversation.thread_id, "saved": True}

    def list_jobs(self, owner_id: str) -> list[dict[str, Any]]:
        with self._sessions() as session:
            records = session.scalars(
                select(GenerationJobRecord)
                .where(GenerationJobRecord.owner_id == owner_id)
                .order_by(GenerationJobRecord.created_at.desc())
                .limit(50)
            )
            return [
                {
                    "id": item.id,
                    "operation": item.operation,
                    "status": item.status,
                    "error": item.error,
                    "failure_kind": item.failure_kind,
                    "duration_ms": item.duration_ms,
                    "metrics": item.metrics,
                }
                for item in records
            ]

    def job_stats(self, owner_id: str) -> dict[str, Any]:
        """Aggregate outcome and latency metrics over this owner's recent jobs.

        Reported per operation as well as overall, because the Phase 3 latency
        targets are provider- and operation-specific: a section regeneration and
        a full-page generation are not comparable.
        """
        with self._sessions() as session:
            records = list(
                session.scalars(
                    select(GenerationJobRecord)
                    .where(GenerationJobRecord.owner_id == owner_id)
                    .order_by(GenerationJobRecord.created_at.desc())
                    .limit(STATS_WINDOW)
                )
            )

        by_operation: dict[str, list[GenerationJobRecord]] = {}
        failure_kinds: dict[str, int] = {}
        for item in records:
            by_operation.setdefault(item.operation, []).append(item)
            if item.failure_kind:
                failure_kinds[item.failure_kind] = (
                    failure_kinds.get(item.failure_kind, 0) + 1
                )

        return {
            "window": STATS_WINDOW,
            "totals": _summarize(records),
            "operations": [
                {"operation": operation, **_summarize(items)}
                for operation, items in sorted(by_operation.items())
            ],
            "failure_kinds": failure_kinds,
        }

    def _get_or_create_conversation(
        self, owner_id: str, thread_id: str
    ) -> ConversationRecord:
        with self._sessions.begin() as session:
            record = session.scalar(
                select(ConversationRecord).where(
                    ConversationRecord.owner_id == owner_id,
                    ConversationRecord.thread_id == thread_id,
                )
            )
            if record is None:
                record = ConversationRecord(
                    owner_id=owner_id,
                    thread_id=thread_id,
                    messages=[],
                )
                session.add(record)
                session.flush()
            session.expunge(record)
            return record

    def _save_conversation(
        self,
        conversation_id: str,
        messages: list[dict[str, str]],
        code: str | None,
        document: dict[str, Any] | None = None,
    ) -> None:
        with self._sessions.begin() as session:
            record = session.get(ConversationRecord, conversation_id)
            if record is not None:
                record.messages = messages
                record.current_code = code
                record.document_json = document
                record.updated_at = utcnow()

    def _start_job(
        self,
        owner_id: str,
        operation: str,
        request: dict[str, Any],
        conversation_id: str | None,
    ) -> str:
        with self._sessions.begin() as session:
            job = GenerationJobRecord(
                owner_id=owner_id,
                conversation_id=conversation_id,
                operation=operation,
                status="running",
                request=request,
            )
            session.add(job)
            session.flush()
            return job.id

    def _finish_job(
        self,
        job_id: str,
        *,
        status: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
        failure_kind: str | None = None,
        duration_ms: int | None = None,
        metrics: dict[str, int] | None = None,
    ) -> None:
        with self._sessions.begin() as session:
            job = session.get(GenerationJobRecord, job_id)
            if job is not None:
                now = utcnow()
                job.status = status
                job.result = result
                job.error = error
                job.failure_kind = failure_kind
                job.duration_ms = duration_ms
                job.metrics = metrics
                job.finished_at = now
                job.updated_at = now

    @staticmethod
    def _last_assistant_message(messages: list[dict[str, str]]) -> str:
        for message in reversed(messages):
            if message["role"] == "assistant":
                return message["content"]
        return "Done."
