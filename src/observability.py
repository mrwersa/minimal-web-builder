from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger("minimal_web_builder")


@dataclass
class GenerationEvent:
    event: str
    duration_ms: int | None = None
    output_chars: int | None = None
    tone_key: str | None = None
    complexity_key: str | None = None
    strict_minimal: bool | None = None
    provider: str | None = None
    error: str | None = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def record(
    event: GenerationEvent,
    analytics_file: str | Path | None = None,
) -> None:
    """Emit a structured event as JSON, optionally appending to a local JSONL file."""
    payload = event.to_dict()
    LOGGER.info(json.dumps(payload))
    if analytics_file:
        path = Path(analytics_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
