from __future__ import annotations

import pytest

from server.agent import (
    BuilderState,
    _apply_result,
    _classify_intent,
    _retry,
    _route_intent,
    _route_validation,
    _validate_output,
    build_graph,
    run_agent,
    set_client,
)
from server.runtime import GenerationClient
from src.config import AppConfig

_VALID_HTML = (
    "<!doctype html><html><head><title>x</title></head>"
    "<body><h1>Hello</h1><p>World</p></body></html>"
)
_NO_BODY_HTML = "<!doctype html><html><head><style>*{}</style></head></html>"


def _mock_client() -> GenerationClient:
    cfg = AppConfig(
        api_key="",
        model="g",
        temperature=0.7,
        max_output_tokens=8192,
        max_prompt_chars=1200,
        analytics_file=None,
        provider="openrouter",
        openrouter_api_key="k",
        openrouter_model="google/gemini-2.5-flash",
        openrouter_base_url="https://openrouter.ai/api/v1",
    )
    return GenerationClient(config=cfg, model="google/gemini-2.5-flash", genai=None)


# --- intent classification ---


def test_classify_greeting_routes_to_answer() -> None:
    s: BuilderState = {"user_input": "hello", "current_code": None}  # type: ignore
    assert _classify_intent(s)["intent"] == "answer"


def test_classify_short_input_routes_to_answer() -> None:
    s: BuilderState = {"user_input": "hi there", "current_code": None}  # type: ignore
    assert _classify_intent(s)["intent"] == "answer"


def test_classify_description_routes_to_generate() -> None:
    s: BuilderState = {
        "user_input": "Create a landing page for a coffee shop",
        "current_code": None,
    }  # type: ignore
    assert _classify_intent(s)["intent"] == "generate"


def test_classify_refine_keyword_routes_to_refine() -> None:
    s: BuilderState = {
        "user_input": "make the header blue",
        "current_code": "<html></html>",
    }  # type: ignore
    assert _classify_intent(s)["intent"] == "refine"


def test_selected_element_always_routes_to_refine() -> None:
    s: BuilderState = {
        "user_input": "fix it",
        "current_code": '<main data-mwb-id="target">Old</main>',
        "target_node_id": "target",
    }  # type: ignore
    assert _classify_intent(s)["intent"] == "refine"


def test_classify_question_routes_to_answer() -> None:
    s: BuilderState = {
        "user_input": "how do I export the page?",
        "current_code": "<html></html>",
    }  # type: ignore
    assert _classify_intent(s)["intent"] == "answer"


def test_route_intent_returns_correct_node() -> None:
    assert _route_intent({"intent": "generate"}) == "generate"
    assert _route_intent({"intent": "refine"}) == "refine"
    assert _route_intent({"intent": "answer"}) == "answer"
    assert _route_intent({"intent": "unknown"}) == "generate"


# --- validation ---


def test_validate_passes_on_valid_html() -> None:
    state: BuilderState = {"generation_result": _VALID_HTML}  # type: ignore
    result = _validate_output(state)
    assert result["validation_errors"] == []
    assert "<h1>Hello</h1>" in result["generation_result"]


def test_validate_scopes_generated_changes_to_selected_element() -> None:
    state: BuilderState = {
        "current_code": (
            '<!doctype html><html><body><header>Keep</header>'
            '<main data-mwb-id="target">Old</main></body></html>'
        ),
        "generation_result": (
            '<!doctype html><html><body><header>Changed</header>'
            '<main data-mwb-id="target">New</main></body></html>'
        ),
        "target_node_id": "target",
    }  # type: ignore

    result = _validate_output(state)

    assert result["validation_errors"] == []
    assert "<header>Keep</header>" in result["generation_result"]
    assert '<main data-mwb-id="target">New</main>' in result["generation_result"]


def test_validate_fails_on_missing_body() -> None:
    state: BuilderState = {"generation_result": _NO_BODY_HTML}  # type: ignore
    result = _validate_output(state)
    assert len(result["validation_errors"]) > 0
    assert any("body" in e.lower() for e in result["validation_errors"])


def test_validate_fails_on_api_error() -> None:
    state: BuilderState = {"generation_result": "API error: boom"}  # type: ignore
    result = _validate_output(state)
    assert len(result["validation_errors"]) > 0
    assert any("boom" in e for e in result["validation_errors"])


def test_validate_fails_on_empty_output() -> None:
    state: BuilderState = {"generation_result": None}  # type: ignore
    result = _validate_output(state)
    assert "No output from LLM" in result["validation_errors"]


# --- routing after validation ---


def test_route_validation_apply_on_success() -> None:
    assert _route_validation({"validation_errors": []}) == "apply"


def test_route_validation_retry_on_error() -> None:
    assert (
        _route_validation({"validation_errors": ["bad"], "retry_count": 0}) == "retry"
    )


def test_route_validation_fallback_after_max_retries() -> None:
    assert (
        _route_validation({"validation_errors": ["bad"], "retry_count": 99})
        == "error_fallback"
    )


# --- apply and retry nodes ---


def test_apply_result_updates_code() -> None:
    state: BuilderState = {"generation_result": _VALID_HTML, "validation_notes": []}  # type: ignore
    result = _apply_result(state)
    assert result["current_code"] == _VALID_HTML
    assert any(m.get("role") == "assistant" for m in result["messages"])


def test_retry_increments_count() -> None:
    state: BuilderState = {"retry_count": 1}  # type: ignore
    result = _retry(state)
    assert result["retry_count"] == 2
    assert result["validation_errors"] == []
    assert result["generation_result"] is None


# --- full graph with mocked LLM ---


def test_run_agent_answer_for_greeting(monkeypatch: pytest.MonkeyPatch) -> None:
    set_client(_mock_client())
    result = run_agent("hello", thread_id="test-greeting", current_code=None)
    assert result["intent"] == "answer"
    assert result["current_code"] is None


def test_run_agent_generate_with_mocked_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    set_client(_mock_client())
    monkeypatch.setattr("server.agent.generate", lambda *a, **k: _VALID_HTML)
    result = run_agent(
        "Create a minimal landing page for a coffee shop with a hero section",
        thread_id="test-gen",
        current_code=None,
        settings={
            "tone": "minimal",
            "complexity": "balanced",
            "strict_minimal": False,
            "extra_guidance": "",
        },
    )
    assert result["current_code"] is not None
    assert "<h1>Hello</h1>" in result["current_code"]
    assert result["validation_errors"] == []


def test_run_agent_refine_with_mocked_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    set_client(_mock_client())
    monkeypatch.setattr("server.agent.generate", lambda *a, **k: _VALID_HTML)
    result = run_agent(
        "make the header blue",
        thread_id="test-refine",
        current_code="<!doctype html><html><body><h1>Old</h1></body></html>",
        settings={
            "tone": "minimal",
            "complexity": "balanced",
            "strict_minimal": False,
            "extra_guidance": "",
        },
    )
    assert result["intent"] == "refine"
    assert result["current_code"] is not None
    assert "<h1>Hello</h1>" in result["current_code"]


def test_run_agent_routes_to_error_fallback_on_persistent_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_client(_mock_client())
    monkeypatch.setattr("server.agent.generate", lambda *a, **k: "API error: boom")
    result = run_agent(
        "Create a landing page for a coffee shop",
        thread_id="test-error",
        current_code=None,
        settings={
            "tone": "minimal",
            "complexity": "balanced",
            "strict_minimal": False,
            "extra_guidance": "",
        },
    )
    assert result["current_code"] is None
    assert len(result["validation_errors"]) > 0


def test_graph_can_be_built_and_compiled() -> None:
    graph = build_graph()
    assert graph is not None
