"""Durable lifecycle for all generation operations and chat checkpoints."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from server.agent import run_agent, set_client
from server.documents import validate_editor_document
from server.models import ConversationRecord, GenerationJobRecord, utcnow
from server.runtime import GenerationClient

T = TypeVar("T", bound=dict[str, Any])


class ConversationValidationError(ValueError):
    pass


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
        try:
            result = work()
        except Exception as exc:
            self._finish_job(job_id, status="failed", error=str(exc))
            raise
        self._finish_job(job_id, status="succeeded", result=result)
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
            {"thread_id": clean_thread_id, "message": user_input},
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
                }
                for item in records
            ]

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
    ) -> None:
        with self._sessions.begin() as session:
            job = session.get(GenerationJobRecord, job_id)
            if job is not None:
                job.status = status
                job.result = result
                job.error = error
                job.updated_at = utcnow()

    @staticmethod
    def _last_assistant_message(messages: list[dict[str, str]]) -> str:
        for message in reversed(messages):
            if message["role"] == "assistant":
                return message["content"]
        return "Done."
