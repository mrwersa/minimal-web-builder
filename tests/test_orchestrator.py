from __future__ import annotations

import pytest
from sqlalchemy import select

from server.database import Database
from server.models import GenerationJobRecord, UserRecord
from server.orchestrator import GenerationOrchestrator

OWNER_ID = "00000000-0000-0000-0000-000000000030"


@pytest.fixture()
def orchestrator(tmp_path):
    database = Database.from_url(f"sqlite:///{tmp_path / 'orchestrator.db'}")
    with database.sessions.begin() as session:
        session.add(
            UserRecord(
                id=OWNER_ID,
                email="owner@example.test",
                password_hash="!test-account",
            )
        )
    try:
        yield GenerationOrchestrator(database.sessions), database
    finally:
        database.close()


def test_execute_persists_success_and_failure(orchestrator) -> None:
    service, _database = orchestrator

    result = service.execute(
        OWNER_ID, "generate", {"prompt": "x"}, lambda: {"html": "ok"}
    )
    assert result == {"html": "ok"}

    def fail():
        raise RuntimeError("provider unavailable")

    with pytest.raises(RuntimeError, match="provider unavailable"):
        service.execute(OWNER_ID, "generate", {"prompt": "x"}, fail)

    jobs = service.list_jobs(OWNER_ID)
    assert [job["status"] for job in jobs] == ["failed", "succeeded"]
    assert jobs[0]["error"] == "provider unavailable"


def test_recover_interrupted_jobs(orchestrator) -> None:
    service, database = orchestrator
    with database.sessions.begin() as session:
        session.add(
            GenerationJobRecord(
                owner_id=OWNER_ID,
                operation="chat",
                status="running",
                request={},
            )
        )

    assert service.recover_interrupted_jobs() == 1
    assert service.recover_interrupted_jobs() == 0
    with database.sessions() as session:
        job = session.scalar(select(GenerationJobRecord))
        assert job is not None
        assert job.status == "failed"
        assert job.error == "Generation interrupted by server restart"
