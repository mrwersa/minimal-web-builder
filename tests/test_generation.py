import json
from types import SimpleNamespace

from src.generation import (
    BASE_PROMPT,
    DEFAULT_GENERATION_TIMEOUT_SECONDS,
    ProviderError,
    build_generation_prompt,
    build_section_regeneration_prompt,
    call_gemini,
    call_gemini_for_section,
    strip_html_code_fence,
)
from src.sections import PageSection
from src.theme import DEFAULT_TONE_KEY, STRICT_MINIMAL_GUIDANCE


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> bool:
        return False

    def read(self) -> bytes:
        return self._body


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


def test_strip_html_code_fence_uppercase_language() -> None:
    raw = "```HTML\n<div>Hello</div>\n```"
    assert strip_html_code_fence(raw) == "<div>Hello</div>"


def test_strip_html_code_fence_other_language_tokens() -> None:
    for lang in ("python", "html5"):
        assert strip_html_code_fence(f"```{lang}\n<div>x</div>\n```") == "<div>x</div>"


def test_strip_html_code_fence_keeps_first_content_line() -> None:
    raw = "```\nHello world\n<div>x</div>\n```"
    assert strip_html_code_fence(raw) == "Hello world\n<div>x</div>"


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


def test_call_gemini_for_section_returns_model_text() -> None:
    model = _FakeModel(text="<main>new</main>")
    out = call_gemini_for_section(
        model,
        _FakeGenai(),
        "<html><body><main>x</main></body></html>",
        _section(),
        "tighten it up",
        temperature=0.2,
        max_output_tokens=100,
        refine_aspect_key="color",
    )

    assert out == "<main>new</main>"
    assert "tighten it up" in model.last_prompt
    assert "Section to replace" in model.last_prompt
    assert "Adjust color only" in model.last_prompt


def test_call_gemini_for_section_surfaces_api_error() -> None:
    out = call_gemini_for_section(
        _FakeModel(error="boom"),
        _FakeGenai(),
        "<main>x</main>",
        _section(),
        "fix it",
        temperature=0.2,
        max_output_tokens=100,
    )

    assert out.startswith("API error:")
    assert "boom" in out


def test_call_gemini_for_section_records_success_event(tmp_path) -> None:
    analytics = tmp_path / "events.jsonl"
    out = call_gemini_for_section(
        _FakeModel(text="<main>new</main>"),
        _FakeGenai(),
        "<main>x</main>",
        _section(),
        "fix it",
        temperature=0.2,
        max_output_tokens=100,
        tone_key="editorial",
        strict_minimal=True,
        complexity_key="compact",
        analytics_file=str(analytics),
    )

    assert out == "<main>new</main>"
    payload = json.loads(analytics.read_text(encoding="utf-8").splitlines()[0])
    assert payload["event"] == "generation.success"
    assert payload["output_chars"] == len("<main>new</main>")
    assert payload["tone_key"] == "editorial"
    assert payload["complexity_key"] == "compact"
    assert payload["strict_minimal"] is True


def test_call_gemini_for_section_records_error_event(tmp_path) -> None:
    analytics = tmp_path / "events.jsonl"
    out = call_gemini_for_section(
        _FakeModel(error="boom"),
        _FakeGenai(),
        "<main>x</main>",
        _section(),
        "fix it",
        temperature=0.2,
        max_output_tokens=100,
        analytics_file=str(analytics),
    )

    assert out.startswith("API error:")
    payload = json.loads(analytics.read_text(encoding="utf-8").splitlines()[0])
    assert payload["event"] == "generation.error"
    assert "boom" in payload["error"]


def test_call_gemini_openrouter_posts_chat_completion(monkeypatch) -> None:
    captured: dict = {}

    def fake_urlopen(request, timeout=None):
        captured["request"] = request
        captured["timeout"] = timeout
        body = json.dumps(
            {"choices": [{"message": {"content": "<main>hi</main>"}}]}
        ).encode("utf-8")
        return _FakeResponse(body)

    monkeypatch.setattr("src.generation.urllib.request.urlopen", fake_urlopen)

    out = call_gemini(
        model="google/gemini-2.0-flash",
        genai=None,
        messages=[{"role": "user", "content": "hi"}],
        temperature=0.3,
        max_output_tokens=200,
        provider="openrouter",
        api_key="or-key",
        base_url="https://openrouter.ai/api/v1",
    )

    assert out == "<main>hi</main>"
    request = captured["request"]
    assert request.full_url == "https://openrouter.ai/api/v1/chat/completions"
    assert request.get_header("Authorization") == "Bearer or-key"
    assert request.headers["Content-type"] == "application/json"
    payload = json.loads(request.data)
    assert payload["model"] == "google/gemini-2.0-flash"
    assert payload["temperature"] == 0.3
    assert payload["max_tokens"] == 200
    assert payload["messages"][0]["role"] == "user"
    assert payload["messages"][0]["content"].startswith("You are an expert web app")
    assert captured["timeout"] is not None


def test_call_gemini_openrouter_surfaces_http_error(monkeypatch) -> None:
    def fake_urlopen(request, timeout=None):
        raise RuntimeError("HTTP 401 Unauthorized")

    monkeypatch.setattr("src.generation.urllib.request.urlopen", fake_urlopen)

    out = call_gemini(
        model="m",
        genai=None,
        messages=[{"role": "user", "content": "hi"}],
        temperature=0.2,
        max_output_tokens=100,
        provider="openrouter",
        api_key="or-key",
    )

    assert out.startswith("API error:")
    assert "401" in out


def test_call_gemini_openrouter_records_provider_event(tmp_path, monkeypatch) -> None:
    analytics = tmp_path / "events.jsonl"

    def fake_urlopen(request, timeout=None):
        body = json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode("utf-8")
        return _FakeResponse(body)

    monkeypatch.setattr("src.generation.urllib.request.urlopen", fake_urlopen)

    call_gemini(
        model="m",
        genai=None,
        messages=[{"role": "user", "content": "hi"}],
        temperature=0.2,
        max_output_tokens=100,
        provider="openrouter",
        api_key="or-key",
        analytics_file=str(analytics),
    )

    payload = json.loads(analytics.read_text(encoding="utf-8").splitlines()[0])
    assert payload["event"] == "generation.success"
    assert payload["provider"] == "openrouter"


def test_call_gemini_default_provider_is_gemini(tmp_path) -> None:
    model = _FakeModel(text="<div>ok</div>")
    call_gemini(
        model,
        _FakeGenai(),
        [{"role": "user", "content": "hi"}],
        temperature=0.2,
        max_output_tokens=100,
    )

    assert "Conversation:" in model.last_prompt


def _section() -> PageSection:
    return PageSection(
        index=0,
        tag="main",
        snippet="x",
        start=0,
        end=len("<main>x</main>"),
        html="<main>x</main>",
    )


def test_section_prompt_includes_refine_aspect_guidance() -> None:
    prompt = build_section_regeneration_prompt(
        "<html><body><main>x</main></body></html>",
        _section(),
        "tighten it up",
        refine_aspect_key="spacing",
    )

    assert "Adjust spacing only" in prompt


def test_section_prompt_omits_general_and_unknown_aspect_guidance() -> None:
    plain = build_section_regeneration_prompt(
        "<html><body><main>x</main></body></html>",
        _section(),
        "tighten it up",
    )
    general = build_section_regeneration_prompt(
        "<html><body><main>x</main></body></html>",
        _section(),
        "tighten it up",
        refine_aspect_key="general",
    )
    unknown = build_section_regeneration_prompt(
        "<html><body><main>x</main></body></html>",
        _section(),
        "tighten it up",
        refine_aspect_key="not-a-focus",
    )

    assert "Adjust " not in plain
    assert general == plain
    assert unknown == plain


def test_section_prompt_refine_aspects_are_distinct() -> None:
    prompts = [
        build_section_regeneration_prompt(
            "<html><body><main>x</main></body></html>",
            _section(),
            "change it",
            refine_aspect_key=key,
        )
        for key in ("spacing", "typography", "layout", "color")
    ]

    assert len(set(prompts)) == len(prompts)


def test_call_gemini_openrouter_uses_the_configured_timeout(monkeypatch) -> None:
    captured: dict = {}

    def fake_urlopen(request, timeout=None):
        captured["timeout"] = timeout
        body = json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode("utf-8")
        return _FakeResponse(body)

    monkeypatch.setattr("src.generation.urllib.request.urlopen", fake_urlopen)

    call_gemini(
        model="google/gemini-2.0-flash",
        genai=None,
        messages=[{"role": "user", "content": "hi"}],
        temperature=0.3,
        max_output_tokens=200,
        provider="openrouter",
        api_key="or-key",
        timeout_seconds=7,
    )

    assert captured["timeout"] == 7


def test_call_gemini_openrouter_defaults_the_timeout(monkeypatch) -> None:
    captured: dict = {}

    def fake_urlopen(request, timeout=None):
        captured["timeout"] = timeout
        body = json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode("utf-8")
        return _FakeResponse(body)

    monkeypatch.setattr("src.generation.urllib.request.urlopen", fake_urlopen)

    call_gemini(
        model="google/gemini-2.0-flash",
        genai=None,
        messages=[{"role": "user", "content": "hi"}],
        temperature=0.3,
        max_output_tokens=200,
        provider="openrouter",
        api_key="or-key",
    )

    assert captured["timeout"] == DEFAULT_GENERATION_TIMEOUT_SECONDS


def test_call_gemini_for_section_uses_the_configured_timeout(monkeypatch) -> None:
    captured: dict = {}

    def fake_urlopen(request, timeout=None):
        captured["timeout"] = timeout
        body = json.dumps({"choices": [{"message": {"content": "<hr>"}}]}).encode(
            "utf-8"
        )
        return _FakeResponse(body)

    monkeypatch.setattr("src.generation.urllib.request.urlopen", fake_urlopen)

    call_gemini_for_section(
        model="google/gemini-2.0-flash",
        genai=None,
        current_code="<html><body><main>x</main></body></html>",
        section=_section(),
        instructions="tighten it",
        temperature=0.3,
        max_output_tokens=200,
        provider="openrouter",
        api_key="or-key",
        timeout_seconds=11,
    )

    assert captured["timeout"] == 11


def _openrouter_call(**overrides):
    kwargs = {
        "model": "google/gemini-2.0-flash",
        "genai": None,
        "messages": [{"role": "user", "content": "hi"}],
        "temperature": 0.3,
        "max_output_tokens": 200,
        "provider": "openrouter",
        "api_key": "or-key",
        "retry_backoff_seconds": 0,
    }
    kwargs.update(overrides)
    return call_gemini(**kwargs)


def _flaky_urlopen(failures: int, error: str = "HTTP 503 Service Unavailable"):
    state = {"calls": 0}

    def fake_urlopen(request, timeout=None):
        state["calls"] += 1
        if state["calls"] <= failures:
            raise RuntimeError(error)
        body = json.dumps({"choices": [{"message": {"content": "<main>ok</main>"}}]})
        return _FakeResponse(body.encode("utf-8"))

    return fake_urlopen, state


def test_generation_does_not_retry_by_default(monkeypatch) -> None:
    """src defaults stay at one attempt; only the server opts into retries."""
    fake_urlopen, state = _flaky_urlopen(failures=1)
    monkeypatch.setattr("src.generation.urllib.request.urlopen", fake_urlopen)

    out = _openrouter_call()

    assert out.startswith("API error:")
    assert state["calls"] == 1


def test_generation_retries_transient_failures(monkeypatch) -> None:
    fake_urlopen, state = _flaky_urlopen(failures=2)
    monkeypatch.setattr("src.generation.urllib.request.urlopen", fake_urlopen)

    out = _openrouter_call(max_attempts=3)

    assert out == "<main>ok</main>"
    assert state["calls"] == 3


def test_generation_gives_up_after_max_attempts(monkeypatch) -> None:
    fake_urlopen, state = _flaky_urlopen(failures=99)
    monkeypatch.setattr("src.generation.urllib.request.urlopen", fake_urlopen)

    out = _openrouter_call(max_attempts=3)

    assert out.startswith("API error:")
    assert "503" in out
    assert state["calls"] == 3


def test_generation_does_not_retry_a_rejected_key(monkeypatch) -> None:
    """Retrying a permanent auth failure only multiplies latency."""
    fake_urlopen, state = _flaky_urlopen(failures=99, error="HTTP 401 Unauthorized")
    monkeypatch.setattr("src.generation.urllib.request.urlopen", fake_urlopen)

    out = _openrouter_call(max_attempts=5)

    assert out.startswith("API error:")
    assert state["calls"] == 1


def test_retry_backoff_grows_exponentially(monkeypatch) -> None:
    fake_urlopen, _state = _flaky_urlopen(failures=99)
    monkeypatch.setattr("src.generation.urllib.request.urlopen", fake_urlopen)
    slept: list[float] = []
    monkeypatch.setattr("src.generation.time.sleep", slept.append)

    _openrouter_call(max_attempts=4, retry_backoff_seconds=0.5)

    # Backoff happens between attempts, never after the last one: four attempts
    # sleep three times, doubling each round.
    assert slept == [0.5, 1.0, 2.0]


def test_each_attempt_records_its_own_event(tmp_path, monkeypatch) -> None:
    analytics = tmp_path / "events.jsonl"
    fake_urlopen, _state = _flaky_urlopen(failures=1)
    monkeypatch.setattr("src.generation.urllib.request.urlopen", fake_urlopen)

    _openrouter_call(max_attempts=2, analytics_file=str(analytics))

    events = [
        json.loads(line) for line in analytics.read_text(encoding="utf-8").splitlines()
    ]
    assert [event["event"] for event in events] == [
        "generation.error",
        "generation.success",
    ]
    assert [event["attempt"] for event in events] == [1, 2]


def test_permanent_and_transient_errors_are_classified() -> None:
    assert ProviderError("HTTP 503 Service Unavailable").retryable is True
    assert ProviderError("<urlopen error timed out>").retryable is True
    assert ProviderError("HTTP 401 Unauthorized").retryable is False
    assert ProviderError("API key not valid").retryable is False
