from __future__ import annotations

import sys
import types
from dataclasses import replace
from typing import Any

from server import runtime
from src.config import GEMINI_PROVIDER, OPENROUTER_PROVIDER, AppConfig

_CONFIG = AppConfig(
    api_key="gemini-key",
    model="gemini-2.5-flash",
    temperature=0.35,
    max_output_tokens=2048,
    max_prompt_chars=900,
    analytics_file="data/events.jsonl",
    provider=GEMINI_PROVIDER,
    openrouter_api_key="or-key",
    openrouter_model="anthropic/claude-3.5-haiku",
    openrouter_base_url="https://proxy.example/v1",
)


class _FakeGenerativeModel:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name


class _FakeGenai:
    def __init__(self) -> None:
        self.configured_key: str | None = None

    def configure(self, api_key: str) -> None:
        self.configured_key = api_key

    def GenerativeModel(self, model: str) -> _FakeGenerativeModel:
        return _FakeGenerativeModel(model)


def test_build_client_uses_openrouter_model_without_gemini_sdk(monkeypatch) -> None:
    config = replace(_CONFIG, provider=OPENROUTER_PROVIDER)
    monkeypatch.setattr(runtime, "load_config", lambda: config)

    client = runtime.build_client()

    assert client.config is config
    assert client.model == "anthropic/claude-3.5-haiku"
    assert client.genai is None


def test_build_client_configures_gemini_sdk(monkeypatch) -> None:
    fake_genai = _FakeGenai()
    monkeypatch.setattr(runtime, "load_config", lambda: _CONFIG)
    # Stub the SDK so the test never needs `google-generativeai` installed.
    google_package = types.ModuleType("google")
    google_package.__path__ = []  # type: ignore[attr-defined]
    google_package.generativeai = fake_genai  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "google", google_package)
    monkeypatch.setitem(sys.modules, "google.generativeai", fake_genai)

    client = runtime.build_client()

    assert client.config is _CONFIG
    assert fake_genai.configured_key == "gemini-key"
    assert isinstance(client.model, _FakeGenerativeModel)
    assert client.model.model_name == "gemini-2.5-flash"
    assert client.genai is fake_genai


def test_generate_forwards_client_config(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_call_gemini(**kwargs: Any) -> str:
        captured.update(kwargs)
        return "<html>page</html>"

    monkeypatch.setattr(runtime, "call_gemini", fake_call_gemini)
    client = runtime.GenerationClient(config=_CONFIG, model="model-handle", genai=None)

    result = runtime.generate(
        client,
        messages=[{"role": "user", "content": "Coffee shop"}],
        tone_key="minimal",
        strict_minimal=True,
        complexity_key="balanced",
        extra_guidance="Keep it flat",
    )

    assert result == "<html>page</html>"
    assert captured["model"] == "model-handle"
    assert captured["genai"] is None
    assert captured["messages"] == [{"role": "user", "content": "Coffee shop"}]
    assert captured["temperature"] == 0.35
    assert captured["max_output_tokens"] == 2048
    assert captured["tone_key"] == "minimal"
    assert captured["strict_minimal"] is True
    assert captured["complexity_key"] == "balanced"
    assert captured["extra_guidance"] == "Keep it flat"
    assert captured["analytics_file"] == "data/events.jsonl"
    assert captured["provider"] == GEMINI_PROVIDER
    assert captured["api_key"] == "or-key"
    assert captured["base_url"] == "https://proxy.example/v1"


def test_generate_sends_empty_api_key_when_openrouter_key_missing(
    monkeypatch,
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        runtime, "call_gemini", lambda **kwargs: captured.update(kwargs) or ""
    )
    client = runtime.GenerationClient(
        config=replace(_CONFIG, openrouter_api_key=None), model="m", genai=None
    )

    runtime.generate(
        client,
        messages=[],
        tone_key="minimal",
        strict_minimal=False,
        complexity_key="compact",
    )

    assert captured["api_key"] == ""


def test_regenerate_section_forwards_client_config(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_call_gemini_for_section(**kwargs: Any) -> str:
        captured.update(kwargs)
        return "<section>hero</section>"

    monkeypatch.setattr(
        runtime, "call_gemini_for_section", fake_call_gemini_for_section
    )
    client = runtime.GenerationClient(config=_CONFIG, model="model-handle", genai=None)
    section = object()

    result = runtime.regenerate_section(
        client,
        current_code="<html>old</html>",
        section=section,
        instructions="Tighten the spacing",
        tone_key="editorial",
        strict_minimal=False,
        complexity_key="detailed",
        extra_guidance="Reuse the palette",
        refine_aspect_key="spacing",
    )

    assert result == "<section>hero</section>"
    assert captured["model"] == "model-handle"
    assert captured["genai"] is None
    assert captured["current_code"] == "<html>old</html>"
    assert captured["section"] is section
    assert captured["instructions"] == "Tighten the spacing"
    assert captured["temperature"] == 0.35
    assert captured["max_output_tokens"] == 2048
    assert captured["tone_key"] == "editorial"
    assert captured["strict_minimal"] is False
    assert captured["complexity_key"] == "detailed"
    assert captured["extra_guidance"] == "Reuse the palette"
    assert captured["analytics_file"] == "data/events.jsonl"
    assert captured["refine_aspect_key"] == "spacing"
    assert captured["provider"] == GEMINI_PROVIDER
    assert captured["api_key"] == "or-key"
    assert captured["base_url"] == "https://proxy.example/v1"


def test_generate_forwards_the_configured_timeout(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        runtime, "call_gemini", lambda **kwargs: captured.update(kwargs) or ""
    )
    client = runtime.GenerationClient(
        config=replace(_CONFIG, generation_timeout_seconds=9), model="m", genai=None
    )

    runtime.generate(
        client,
        messages=[],
        tone_key="minimal",
        strict_minimal=False,
        complexity_key="balanced",
    )

    assert captured["timeout_seconds"] == 9


def test_regenerate_section_forwards_the_configured_timeout(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        runtime,
        "call_gemini_for_section",
        lambda **kwargs: captured.update(kwargs) or "",
    )
    client = runtime.GenerationClient(
        config=replace(_CONFIG, generation_timeout_seconds=13), model="m", genai=None
    )

    runtime.regenerate_section(
        client,
        current_code="<html></html>",
        section=object(),
        instructions="",
        tone_key="minimal",
        strict_minimal=False,
        complexity_key="balanced",
    )

    assert captured["timeout_seconds"] == 13


def test_generate_forwards_the_configured_retry_policy(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        runtime, "call_gemini", lambda **kwargs: captured.update(kwargs) or ""
    )
    client = runtime.GenerationClient(
        config=replace(
            _CONFIG, generation_max_attempts=4, generation_retry_backoff_seconds=0.25
        ),
        model="m",
        genai=None,
    )

    runtime.generate(
        client,
        messages=[],
        tone_key="minimal",
        strict_minimal=False,
        complexity_key="balanced",
    )

    assert captured["max_attempts"] == 4
    assert captured["retry_backoff_seconds"] == 0.25


def test_regenerate_section_forwards_the_configured_retry_policy(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        runtime,
        "call_gemini_for_section",
        lambda **kwargs: captured.update(kwargs) or "",
    )
    client = runtime.GenerationClient(
        config=replace(_CONFIG, generation_max_attempts=2), model="m", genai=None
    )

    runtime.regenerate_section(
        client,
        current_code="<html></html>",
        section=object(),
        instructions="",
        tone_key="minimal",
        strict_minimal=False,
        complexity_key="balanced",
    )

    assert captured["max_attempts"] == 2
