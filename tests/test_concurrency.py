from __future__ import annotations

import asyncio
import threading

import pytest

from server.concurrency import GenerationLimiter, offload


def test_offload_runs_blocking_work_off_the_event_loop() -> None:
    thread_names: list[str] = []

    def blocking(value: int, *, factor: int) -> int:
        thread_names.append(threading.current_thread().name)
        return value * factor

    async def scenario() -> int:
        return await offload(blocking, 21, factor=2)

    assert asyncio.run(scenario()) == 42
    assert thread_names[0] != threading.main_thread().name


def test_limiter_caps_simultaneous_work() -> None:
    limiter = GenerationLimiter(2)
    active = 0
    peak = 0

    async def scenario() -> list[str]:
        release = asyncio.Event()

        async def work() -> str:
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await release.wait()
            active -= 1
            return "done"

        tasks = [asyncio.create_task(limiter.run(work)) for _ in range(5)]
        # Yield until the first batch has claimed every available slot, then
        # assert that the queued tasks are genuinely held back.
        for _ in range(5):
            await asyncio.sleep(0)
        assert peak == 2
        release.set()
        return await asyncio.gather(*tasks)

    assert asyncio.run(scenario()) == ["done"] * 5
    assert peak == 2
    assert limiter.available == 2


def test_limiter_releases_its_slot_when_work_raises() -> None:
    limiter = GenerationLimiter(1)

    async def scenario() -> str:
        async def boom() -> str:
            raise RuntimeError("provider exploded")

        with pytest.raises(RuntimeError, match="provider exploded"):
            await limiter.run(boom)
        assert limiter.available == 1

        async def ok() -> str:
            return "recovered"

        return await limiter.run(ok)

    assert asyncio.run(scenario()) == "recovered"
    assert limiter.available == 1


def test_limiter_clamps_a_nonpositive_limit() -> None:
    assert GenerationLimiter(0).limit == 1
    assert GenerationLimiter(-5).limit == 1
