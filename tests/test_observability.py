import json
import logging
from pathlib import Path

from src.observability import GenerationEvent, record


def test_record_writes_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "events.jsonl"

    record(
        GenerationEvent(event="generation.success", duration_ms=12, output_chars=40),
        analytics_file=path,
    )

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["event"] == "generation.success"
    assert payload["duration_ms"] == 12
    assert payload["output_chars"] == 40


def test_record_appends_multiple_events(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    record(GenerationEvent(event="a"), analytics_file=path)
    record(GenerationEvent(event="b"), analytics_file=path)

    events = [json.loads(line) for line in path.read_text().splitlines()]
    assert [e["event"] for e in events] == ["a", "b"]


def test_record_logs_structured_payload(caplog) -> None:
    with caplog.at_level(logging.INFO, logger="minimal_web_builder"):
        record(GenerationEvent(event="generation.error", error="boom"))

    assert any(
        json.loads(r.message)["event"] == "generation.error"
        for r in caplog.records
        if r.name == "minimal_web_builder"
    )


def test_generation_event_to_dict_includes_all_fields() -> None:
    payload = GenerationEvent(
        event="x",
        tone_key="landing",
        complexity_key="detailed",
        strict_minimal=True,
        provider="openrouter",
    ).to_dict()

    assert payload["event"] == "x"
    assert payload["tone_key"] == "landing"
    assert payload["complexity_key"] == "detailed"
    assert payload["strict_minimal"] is True
    assert payload["provider"] == "openrouter"
    assert "timestamp" in payload
