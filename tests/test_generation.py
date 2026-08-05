import json
from types import SimpleNamespace

from src.generation import (
    BASE_PROMPT,
    build_generation_prompt,
    call_gemini,
    strip_html_code_fence,
)
from src.theme import DEFAULT_TONE_KEY, STRICT_MINIMAL_GUIDANCE


class _FakeGenaiTypes:
    class GenerationConfig:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs


class _FakeGenai:
    types = _FakeGenaiTypes


class _FakeModel:
    def __init__(self, text: str | None = None, error: str | None = None) -> None:
        self._text = text
        self._error = error
        self.last_prompt = None

    def generate_content(self, prompt: str, generation_config=None):
        self.last_prompt = prompt
        if self._error is not None:
            raise RuntimeError(self._error)
        return SimpleNamespace(text=self._text)


def test_strip_html_code_fence_html_block() -> None:
    raw = "```html\n<div>Hello</div>\n```"
    assert strip_html_code_fence(raw) == "<div>Hello</div>"


def test_strip_html_code_fence_generic_block() -> None:
    raw = "```\n<section>Hi</section>\n```"
    assert strip_html_code_fence(raw) == "<section>Hi</section>"


def test_build_generation_prompt_includes_roles_and_content() -> None:
    prompt = build_generation_prompt(
        [
            {"role": "assistant", "content": "previous html"},
            {"role": "user", "content": "build a portfolio"},
        ]
    )
    assert "Conversation:" in prompt
    assert "ASSISTANT: previous html" in prompt
    assert "USER: build a portfolio" in prompt


def test_build_generation_prompt_default_tone_is_minimal() -> None:
    prompt = build_generation_prompt([{"role": "user", "content": "hello"}])
    assert DEFAULT_TONE_KEY == "minimal"
    assert "Style direction:" in prompt


def test_build_generation_prompt_uses_tone_guidance() -> None:
    prompt = build_generation_prompt(
        [{"role": "user", "content": "hello"}],
        tone_key="editorial",
    )
    assert "Style direction:" in prompt
    assert "Serif headlines" in prompt
    assert "Monochrome" not in prompt


def test_build_generation_prompt_strict_minimal_adds_guidance() -> None:
    prompt = build_generation_prompt(
        [{"role": "user", "content": "hello"}],
        strict_minimal=True,
    )
    assert STRICT_MINIMAL_GUIDANCE in prompt


def test_build_generation_prompt_unknown_tone_omits_guidance() -> None:
    prompt = build_generation_prompt(
        [{"role": "user", "content": "hello"}],
        tone_key="not-a-real-tone",
    )
    assert "Style direction:" not in prompt


def test_build_generation_prompt_default_complexity_is_balanced() -> None:
    prompt = build_generation_prompt([{"role": "user", "content": "hello"}])
    assert "Complexity:" in prompt
    assert "essential sections" in prompt


def test_build_generation_prompt_uses_complexity_guidance() -> None:
    compact = build_generation_prompt(
        [{"role": "user", "content": "hello"}],
        complexity_key="compact",
    )
    assert "smallest possible page" in compact
    detailed = build_generation_prompt(
        [{"role": "user", "content": "hello"}],
        complexity_key="detailed",
    )
    assert "richer page" in detailed


def test_build_generation_prompt_unknown_complexity_omits_guidance() -> None:
    prompt = build_generation_prompt(
        [{"role": "user", "content": "hello"}],
        complexity_key="not-a-real-level",
    )
    assert "Complexity:" not in prompt


def test_base_prompt_contains_accessibility_guardrails() -> None:
    assert "WCAG AA" in BASE_PROMPT
    assert "focus indicators" in BASE_PROMPT
    assert "single <h1>" in BASE_PROMPT


def test_call_gemini_returns_model_text() -> None:
    model = _FakeModel(text="<div>ok</div>")
    out = call_gemini(
        model,
        _FakeGenai(),
        [{"role": "user", "content": "hi"}],
        temperature=0.2,
        max_output_tokens=100,
    )

    assert out == "<div>ok</div>"
    assert "Conversation:" in model.last_prompt


def test_call_gemini_surfaces_api_error() -> None:
    out = call_gemini(
        _FakeModel(error="boom"),
        _FakeGenai(),
        [{"role": "user", "content": "hi"}],
        temperature=0.2,
        max_output_tokens=100,
    )

    assert out.startswith("API error:")
    assert "boom" in out


def test_call_gemini_records_success_event(tmp_path) -> None:
    analytics = tmp_path / "events.jsonl"
    out = call_gemini(
        _FakeModel(text="ok"),
        _FakeGenai(),
        [{"role": "user", "content": "hi"}],
        temperature=0.2,
        max_output_tokens=100,
        tone_key="minimal",
        complexity_key="compact",
        strict_minimal=True,
        analytics_file=str(analytics),
    )

    assert out == "ok"
    payload = json.loads(analytics.read_text(encoding="utf-8").splitlines()[0])
    assert payload["event"] == "generation.success"
    assert payload["output_chars"] == 2
    assert payload["tone_key"] == "minimal"
    assert payload["complexity_key"] == "compact"
    assert payload["strict_minimal"] is True
    assert payload["duration_ms"] is not None


def test_call_gemini_records_error_event(tmp_path) -> None:
    analytics = tmp_path / "events.jsonl"
    out = call_gemini(
        _FakeModel(error="boom"),
        _FakeGenai(),
        [{"role": "user", "content": "hi"}],
        temperature=0.2,
        max_output_tokens=100,
        analytics_file=str(analytics),
    )

    assert out.startswith("API error:")
    payload = json.loads(analytics.read_text(encoding="utf-8").splitlines()[0])
    assert payload["event"] == "generation.error"
    assert "boom" in payload["error"]


def test_call_gemini_without_analytics_file_writes_nothing(tmp_path) -> None:
    call_gemini(
        _FakeModel(text="ok"),
        _FakeGenai(),
        [{"role": "user", "content": "hi"}],
        temperature=0.2,
        max_output_tokens=100,
    )

    assert not list(tmp_path.iterdir())
