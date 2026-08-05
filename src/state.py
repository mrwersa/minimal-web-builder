from __future__ import annotations

from typing import Any, Dict, List, MutableMapping

from src.theme import DEFAULT_TONE_KEY


def init_session_state(state: MutableMapping[str, Any]) -> None:
    state.setdefault("messages", [])
    state.setdefault("last_app_code", None)
    state.setdefault("is_generating", False)
    state.setdefault("show_preview", True)
    state.setdefault("generation_tone", DEFAULT_TONE_KEY)
    state.setdefault("strict_minimal_mode", False)


def add_user_message_and_start_generation(
    state: MutableMapping[str, Any],
    message: str,
) -> None:
    state["messages"].append({"role": "user", "content": message})
    state["is_generating"] = True


def build_generation_messages(state: MutableMapping[str, Any]) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []

    last_app_code = state.get("last_app_code")
    if last_app_code:
        messages.append(
            {
                "role": "assistant",
                "content": f"Here is the current version of the website code:\n\n{str(last_app_code).strip()}",
            }
        )

    for item in reversed(state.get("messages", [])):
        if item.get("role") == "user":
            messages.append({"role": "user", "content": item.get("content", "")})
            break

    return messages


def apply_generation_result(state: MutableMapping[str, Any], output: str) -> None:
    state["messages"].append(
        {"role": "assistant", "content": "Your minimalist website has been generated!"}
    )
    state["last_app_code"] = output
    state["is_generating"] = False


def apply_generation_error(state: MutableMapping[str, Any], error_message: str) -> None:
    state["messages"].append(
        {
            "role": "assistant",
            "content": f"Generation failed. Please try again. ({error_message})",
        }
    )
    state["is_generating"] = False
