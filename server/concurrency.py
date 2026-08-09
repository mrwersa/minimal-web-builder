"""Async boundaries for blocking provider, database, and filesystem calls."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from functools import partial
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


async def offload(function: Callable[P, R], /, *args: P.args, **kwargs: P.kwargs) -> R:
    return await asyncio.to_thread(partial(function, *args, **kwargs))
