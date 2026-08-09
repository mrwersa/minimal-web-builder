from __future__ import annotations

import asyncio
import threading

from server.concurrency import offload


def test_offload_runs_blocking_work_off_the_event_loop() -> None:
    thread_names: list[str] = []

    def blocking(value: int, *, factor: int) -> int:
        thread_names.append(threading.current_thread().name)
        return value * factor

    async def scenario() -> int:
        return await offload(blocking, 21, factor=2)

    assert asyncio.run(scenario()) == 42
    assert thread_names[0] != threading.main_thread().name
