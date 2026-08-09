"""Async boundaries for blocking provider, database, and filesystem calls."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from functools import partial
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


async def offload(function: Callable[P, R], /, *args: P.args, **kwargs: P.kwargs) -> R:
    return await asyncio.to_thread(partial(function, *args, **kwargs))


class GenerationLimiter:
    """Bound how many generations run at once.

    Every generation occupies a worker thread for the whole provider round trip,
    so an unbounded burst starves the pool that also serves database work and
    stalls unrelated requests. Queueing here keeps latency attributable to the
    provider rather than to thread-pool contention.
    """

    def __init__(self, limit: int) -> None:
        self.limit = max(1, limit)
        self._semaphore = asyncio.Semaphore(self.limit)
        self._in_flight = 0

    @property
    def available(self) -> int:
        """Slots not currently executing work."""
        return self.limit - self._in_flight

    async def run(self, work: Callable[[], Awaitable[R]]) -> R:
        async with self._semaphore:
            self._in_flight += 1
            try:
                return await work()
            finally:
                self._in_flight -= 1
