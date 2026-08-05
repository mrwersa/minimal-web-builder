from src.state import (
    add_user_message_and_start_generation,
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


def test_build_generation_messages_prefers_last_user_message() -> None:
    state = {
        "messages": [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "ok"},
            {"role": "user", "content": "second"},
        ],
        "last_app_code": "<div>v1</div>",
    }

    msgs = build_generation_messages(state)

    assert msgs[0]["role"] == "assistant"
    assert "<div>v1</div>" in msgs[0]["content"]
    assert msgs[1] == {"role": "user", "content": "second"}


def test_generation_state_transitions() -> None:
    state = {"messages": [], "is_generating": False, "last_app_code": None}

    add_user_message_and_start_generation(state, "build a page")
    assert state["is_generating"] is True
    assert state["messages"][-1]["role"] == "user"

    apply_generation_result(state, "<html></html>")
    assert state["is_generating"] is False
    assert state["last_app_code"] == "<html></html>"
    assert state["messages"][-1]["role"] == "assistant"
