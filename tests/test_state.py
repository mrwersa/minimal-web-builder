from src.state import (
    MAX_INSTRUCTION_HISTORY,
    add_user_message_and_start_generation,
    apply_generation_error,
    apply_generation_result,
    build_generation_messages,
    init_session_state,
)


def test_init_session_state_sets_defaults() -> None:
    state = {}
    init_session_state(state)

    assert state["messages"] == []
    assert state["last_app_code"] is None
    assert state["is_generating"] is False
    assert state["show_preview"] is True
    assert state["generation_tone"] == "minimal"
    assert state["strict_minimal_mode"] is False
    assert state["generation_complexity"] == "balanced"


def test_build_generation_messages_includes_instruction_history() -> None:
    state = {
        "messages": [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "ok"},
            {"role": "user", "content": "second"},
            {"role": "assistant", "content": "done"},
        ],
        "last_app_code": "<div>v1</div>",
    }

    msgs = build_generation_messages(state)

    assert msgs[0]["role"] == "assistant"
    assert "<div>v1</div>" in msgs[0]["content"]
    assert [m["content"] for m in msgs[1:]] == ["first", "second"]


def test_build_generation_messages_caps_instruction_history() -> None:
    state = {
        "messages": [
            {"role": "user", "content": f"prompt-{i}"}
            for i in range(MAX_INSTRUCTION_HISTORY + 3)
        ],
        "last_app_code": None,
    }

    msgs = build_generation_messages(state)

    assert len(msgs) == MAX_INSTRUCTION_HISTORY
    assert msgs[0]["content"] == "prompt-3"
    assert msgs[-1]["content"] == f"prompt-{MAX_INSTRUCTION_HISTORY + 2}"


def test_build_generation_messages_empty_without_history() -> None:
    assert build_generation_messages({"messages": [], "last_app_code": None}) == []


def test_generation_state_transitions() -> None:
    state = {"messages": [], "is_generating": False, "last_app_code": None}

    add_user_message_and_start_generation(state, "build a page")
    assert state["is_generating"] is True
    assert state["messages"][-1]["role"] == "user"

    apply_generation_result(state, "<html></html>")
    assert state["is_generating"] is False
    assert state["last_app_code"] == "<html></html>"
    assert state["messages"][-1]["role"] == "assistant"


def test_generation_error_does_not_override_last_code() -> None:
    state = {
        "messages": [{"role": "user", "content": "retry"}],
        "is_generating": True,
        "last_app_code": "<div>stable</div>",
    }

    apply_generation_error(state, "API error: timeout")

    assert state["is_generating"] is False
    assert state["last_app_code"] == "<div>stable</div>"
    assert "Generation failed" in state["messages"][-1]["content"]
