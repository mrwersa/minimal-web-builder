from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from server.database import Database
from server.models import GenerationJobRecord, UserRecord
from server.orchestrator import (
    FAILURE_INTERNAL,
    FAILURE_INTERRUPTED,
    FAILURE_PROVIDER,
    FAILURE_TIMEOUT,
    FAILURE_VALIDATION,
    GenerationOrchestrator,
    _percentile,
    classify_failure,
)

OWNER_ID = "00000000-0000-0000-0000-000000000030"
OTHER_OWNER_ID = "00000000-0000-0000-0000-000000000031"


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
        session.add(
            UserRecord(
                id=OTHER_OWNER_ID,
                email="other@example.test",
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
        assert job.failure_kind == FAILURE_INTERRUPTED
        assert job.finished_at is not None


def test_chat_passes_scoped_target_to_agent_and_job(
    orchestrator, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, database = orchestrator
    captured: dict = {}

    def fake_run_agent(user_input, **kwargs):
        captured.update({"user_input": user_input, **kwargs})
        return {
            "messages": [
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": "Done"},
            ],
            "current_code": kwargs["current_code"],
            "intent": "refine",
        }

    monkeypatch.setattr("server.orchestrator.run_agent", fake_run_agent)
    html = '<main data-mwb-id="target">Old</main>'

    result = service.chat(
        OWNER_ID,
        "scoped-thread",
        "make it warmer",
        html,
        {},
        None,  # type: ignore[arg-type]
        "target",
    )

    assert result["intent"] == "refine"
    assert captured["target_node_id"] == "target"
    with database.sessions() as session:
        job = session.scalar(
            select(GenerationJobRecord).order_by(GenerationJobRecord.created_at.desc())
        )
        assert job is not None
        assert job.request["target_node_id"] == "target"


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (
            HTTPException(status_code=502, detail="API error: bad gateway"),
            FAILURE_PROVIDER,
        ),
        (RuntimeError("API error: provider exploded"), FAILURE_PROVIDER),
        (
            HTTPException(
                status_code=502, detail="API error: <urlopen error timed out>"
            ),
            FAILURE_TIMEOUT,
        ),
        (TimeoutError("the read operation timed out"), FAILURE_TIMEOUT),
        (
            HTTPException(status_code=400, detail="Invalid section index"),
            FAILURE_VALIDATION,
        ),
        (ValueError("Unsupported editor document schema"), FAILURE_VALIDATION),
        (RuntimeError("something else broke"), FAILURE_INTERNAL),
    ],
)
def test_classify_failure_buckets_by_cause(exc: BaseException, expected: str) -> None:
    assert classify_failure(exc) == expected


def test_classify_failure_prefers_timeout_over_provider() -> None:
    """A provider timeout is still a 502, but needs its own bucket to be actionable."""
    exc = HTTPException(status_code=502, detail="API error: <urlopen error timed out>")
    assert classify_failure(exc) == FAILURE_TIMEOUT


@pytest.mark.parametrize(
    ("values", "percentile", "expected"),
    [
        ([], 95, None),
        ([7], 50, 7),
        ([7], 95, 7),
        ([1, 2, 3, 4], 50, 2),
        (list(range(1, 101)), 95, 95),
        ([5, 1, 3], 100, 5),
    ],
)
def test_percentile_uses_nearest_rank(
    values: list[int], percentile: float, expected: int | None
) -> None:
    assert _percentile(values, percentile) == expected


def test_execute_records_duration_and_result_metrics(orchestrator) -> None:
    service, database = orchestrator

    service.execute(
        OWNER_ID,
        "generate",
        {"prompt": "x"},
        lambda: {
            "html": "<html>page</html>",
            "notes": ["a", "b"],
            "safety_alerts": ["stripped a script"],
        },
    )

    with database.sessions() as session:
        job = session.scalar(select(GenerationJobRecord))
        assert job is not None
        assert job.status == "succeeded"
        assert job.failure_kind is None
        assert job.finished_at is not None
        assert job.duration_ms is not None and job.duration_ms >= 0
        assert job.metrics == {
            "output_chars": len("<html>page</html>"),
            "note_count": 2,
            "safety_alert_count": 1,
            "validation_error_count": 0,
        }


def test_execute_classifies_and_times_failures(orchestrator) -> None:
    service, database = orchestrator

    def fail():
        raise HTTPException(status_code=502, detail="API error: upstream refused")

    with pytest.raises(HTTPException):
        service.execute(OWNER_ID, "generate", {"prompt": "x"}, fail)

    with database.sessions() as session:
        job = session.scalar(select(GenerationJobRecord))
        assert job is not None
        assert job.status == "failed"
        assert job.failure_kind == FAILURE_PROVIDER
        # The HTTPException detail is preserved rather than its repr.
        assert job.error == "API error: upstream refused"
        assert job.duration_ms is not None
        assert job.metrics is None


def test_list_jobs_exposes_metrics(orchestrator) -> None:
    service, _database = orchestrator
    service.execute(OWNER_ID, "generate", {}, lambda: {"html": "ok"})

    job = service.list_jobs(OWNER_ID)[0]

    assert job["failure_kind"] is None
    assert job["duration_ms"] is not None
    assert job["metrics"]["output_chars"] == 2


def _seed_job(database, owner_id: str, **values) -> None:
    with database.sessions.begin() as session:
        session.add(
            GenerationJobRecord(
                owner_id=owner_id,
                operation=values.pop("operation", "generate"),
                status=values.pop("status", "succeeded"),
                request={},
                **values,
            )
        )


def test_job_stats_aggregates_by_operation_and_failure_kind(orchestrator) -> None:
    service, database = orchestrator
    for duration in (100, 200, 300, 400):
        _seed_job(database, OWNER_ID, operation="generate", duration_ms=duration)
    _seed_job(
        database,
        OWNER_ID,
        operation="generate",
        status="failed",
        failure_kind=FAILURE_PROVIDER,
        duration_ms=5,
    )
    _seed_job(database, OWNER_ID, operation="chat", duration_ms=50)
    _seed_job(
        database,
        OWNER_ID,
        operation="chat",
        status="failed",
        failure_kind=FAILURE_TIMEOUT,
    )

    stats = service.job_stats(OWNER_ID)

    assert stats["totals"]["total"] == 7
    assert stats["totals"]["succeeded"] == 5
    assert stats["totals"]["failed"] == 2
    assert stats["failure_kinds"] == {FAILURE_PROVIDER: 1, FAILURE_TIMEOUT: 1}

    by_operation = {item["operation"]: item for item in stats["operations"]}
    assert set(by_operation) == {"chat", "generate"}
    generate = by_operation["generate"]
    assert generate["total"] == 5
    assert generate["success_rate"] == 0.8
    # Percentiles cover successful jobs only, so the 5ms failure is excluded.
    assert generate["p50_ms"] == 200
    assert generate["p95_ms"] == 400
    assert by_operation["chat"]["success_rate"] == 0.5


def test_job_stats_excludes_running_jobs_from_success_rate(orchestrator) -> None:
    service, database = orchestrator
    _seed_job(database, OWNER_ID, duration_ms=10)
    _seed_job(database, OWNER_ID, status="running")

    totals = service.job_stats(OWNER_ID)["totals"]

    assert totals["total"] == 2
    assert totals["running"] == 1
    assert totals["success_rate"] == 1.0


def test_job_stats_is_empty_without_jobs(orchestrator) -> None:
    service, _database = orchestrator

    stats = service.job_stats(OWNER_ID)

    assert stats["operations"] == []
    assert stats["failure_kinds"] == {}
    assert stats["totals"]["success_rate"] is None
    assert stats["totals"]["p95_ms"] is None


def test_job_stats_is_scoped_to_the_owner(orchestrator) -> None:
    service, database = orchestrator
    _seed_job(database, OWNER_ID, duration_ms=10)
    _seed_job(database, OTHER_OWNER_ID, duration_ms=99)
    _seed_job(
        database,
        OTHER_OWNER_ID,
        status="failed",
        failure_kind=FAILURE_PROVIDER,
    )

    stats = service.job_stats(OWNER_ID)

    assert stats["totals"]["total"] == 1
    assert stats["failure_kinds"] == {}
