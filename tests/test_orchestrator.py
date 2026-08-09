from __future__ import annotations

import threading
import time

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
    TERMINAL_STATUSES,
    GenerationOrchestrator,
    JobNotFoundError,
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


def wait_for_job(service, job_id: str, timeout: float = 10.0) -> dict:
    """Block until a submitted job reaches a terminal state."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = service.get_job(OWNER_ID, job_id)
        if job is not None and job["status"] in TERMINAL_STATUSES:
            return job
        time.sleep(0.01)
    raise AssertionError(f"job {job_id} never settled")


def run_job(service, work, operation: str = "generate") -> dict:
    return wait_for_job(service, service.submit(OWNER_ID, operation, {}, work))


def test_submit_persists_success_and_failure(orchestrator) -> None:
    service, _database = orchestrator

    succeeded = run_job(service, lambda _token: {"html": "ok"})
    assert succeeded["status"] == "succeeded"
    assert succeeded["result"] == {"html": "ok"}

    def fail(_token):
        raise RuntimeError("provider unavailable")

    failed = run_job(service, fail)
    assert failed["status"] == "failed"
    assert failed["error"] == "provider unavailable"

    jobs = service.list_jobs(OWNER_ID)
    assert [job["status"] for job in jobs] == ["failed", "succeeded"]


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

    job = wait_for_job(
        service,
        service.submit_chat(
            OWNER_ID,
            "scoped-thread",
            "make it warmer",
            html,
            {},
            None,  # type: ignore[arg-type]
            "target",
        ),
    )

    assert job["result"]["intent"] == "refine"
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


def test_submit_records_duration_and_result_metrics(orchestrator) -> None:
    service, database = orchestrator

    run_job(
        service,
        lambda _token: {
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


def test_submit_classifies_and_times_failures(orchestrator) -> None:
    service, database = orchestrator

    def fail(_token):
        raise HTTPException(status_code=502, detail="API error: upstream refused")

    run_job(service, fail)

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
    run_job(service, lambda _token: {"html": "ok"})

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


def test_cancel_discards_a_result_that_arrives_after_the_client_gave_up(
    orchestrator,
) -> None:
    """A provider call cannot be interrupted, so the result is dropped instead."""
    service, _database = orchestrator
    started = threading.Event()
    release = threading.Event()

    def slow(_token):
        started.set()
        release.wait(timeout=5)
        return {"html": "<main>too late</main>"}

    job_id = service.submit(OWNER_ID, "generate", {}, slow)
    assert started.wait(timeout=5)

    service.request_cancel(OWNER_ID, job_id)
    release.set()

    job = wait_for_job(service, job_id)
    assert job["status"] == "cancelled"
    assert job["result"] is None


def test_cancelling_a_queued_job_settles_it_without_running_it(orchestrator) -> None:
    """The pool is full, so this job must never reach the provider at all."""
    _service, database = orchestrator
    # A single worker makes "still queued" deterministic rather than a race.
    service = GenerationOrchestrator(database.sessions, max_workers=1)
    release = threading.Event()
    ran = threading.Event()

    def block(_token):
        release.wait(timeout=5)
        return {"html": "first"}

    def should_not_run(_token):
        ran.set()
        return {"html": "second"}

    first = service.submit(OWNER_ID, "generate", {}, block)
    queued = service.submit(OWNER_ID, "generate", {}, should_not_run)

    cancelled = service.request_cancel(OWNER_ID, queued)
    assert cancelled["status"] == "cancelled"

    release.set()
    wait_for_job(service, first)
    assert wait_for_job(service, queued)["status"] == "cancelled"
    assert not ran.is_set()
    service.shutdown()


def test_work_can_abandon_itself_at_a_cancellation_checkpoint(orchestrator) -> None:
    service, _database = orchestrator
    committed = threading.Event()
    job_id: dict[str, str] = {}

    def work(token):
        # Simulate a cancel landing while the provider was responding.
        service.request_cancel(OWNER_ID, job_id["id"])
        token.raise_if_cancelled()
        committed.set()
        return {"html": "never"}

    job_id["id"] = service.submit(OWNER_ID, "generate", {}, work)

    job = wait_for_job(service, job_id["id"])
    assert job["status"] == "cancelled"
    assert not committed.is_set()


def test_cancelling_a_finished_job_is_a_no_op(orchestrator) -> None:
    service, _database = orchestrator
    job_id = service.submit(OWNER_ID, "generate", {}, lambda _token: {"html": "ok"})
    wait_for_job(service, job_id)

    assert service.request_cancel(OWNER_ID, job_id)["status"] == "succeeded"


def test_cancel_rejects_another_owners_job(orchestrator) -> None:
    service, _database = orchestrator
    job_id = service.submit(OWNER_ID, "generate", {}, lambda _token: {"html": "ok"})
    wait_for_job(service, job_id)

    with pytest.raises(JobNotFoundError):
        service.request_cancel(OTHER_OWNER_ID, job_id)
    assert service.get_job(OTHER_OWNER_ID, job_id) is None


def test_active_job_is_what_a_reloaded_browser_reattaches_to(orchestrator) -> None:
    service, _database = orchestrator
    assert service.active_job(OWNER_ID) is None

    release = threading.Event()
    job_id = service.submit(
        OWNER_ID,
        "generate",
        {},
        lambda _token: release.wait(timeout=5) or {"html": "x"},
    )

    active = service.active_job(OWNER_ID)
    assert active is not None and active["id"] == job_id

    release.set()
    wait_for_job(service, job_id)
    assert service.active_job(OWNER_ID) is None


def test_recovery_settles_queued_jobs_a_restart_orphaned(orchestrator) -> None:
    """A queued job's worker never existed, so nothing would ever pick it up."""
    service, database = orchestrator
    with database.sessions.begin() as session:
        session.add(
            GenerationJobRecord(
                owner_id=OWNER_ID, operation="chat", status="queued", request={}
            )
        )

    assert service.recover_interrupted_jobs() == 1
    with database.sessions() as session:
        job = session.scalar(select(GenerationJobRecord))
        assert job is not None
        assert job.status == "failed"
        assert job.failure_kind == FAILURE_INTERRUPTED


def test_cancelled_jobs_stay_out_of_the_success_rate(orchestrator) -> None:
    service, database = orchestrator
    _seed_job(database, OWNER_ID, duration_ms=10)
    _seed_job(database, OWNER_ID, status="cancelled")

    totals = service.job_stats(OWNER_ID)["totals"]

    assert totals["cancelled"] == 1
    # One success, no failures: a user changing their mind is not a defect.
    assert totals["success_rate"] == 1.0
