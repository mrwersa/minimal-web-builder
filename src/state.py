from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from src.theme import DEFAULT_COMPLEXITY_KEY, DEFAULT_TONE_KEY

MAX_INSTRUCTION_HISTORY = 8


def init_session_state(state: MutableMapping[str, Any]) -> None:
    state.setdefault("messages", [])
    state.setdefault("last_app_code", None)
    state.setdefault("is_generating", False)
    state.setdefault("is_regenerating_section", False)
    state.setdefault("pending_section_index", None)
    state.setdefault("show_preview", True)
    state.setdefault("generation_tone", DEFAULT_TONE_KEY)
    state.setdefault("strict_minimal_mode", False)
    state.setdefault("generation_complexity", DEFAULT_COMPLEXITY_KEY)
    state.setdefault("layout_dna_guidance", "")
    state.setdefault("wysiwyg_editing", False)
    state.setdefault("last_edit_nonce", 0)


def add_user_message_and_start_generation(
    state: MutableMapping[str, Any],
    message: str,
) -> None:
    state["messages"].append({"role": "user", "content": message})
    state["is_generating"] = True


def build_generation_messages(state: MutableMapping[str, Any]) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []

    last_app_code = state.get("last_app_code")
    if last_app_code:
        messages.append(
            {
                "role": "assistant",
                "content": f"Here is the current version of the website code:\n\n{str(last_app_code).strip()}",
            }
        )

    user_history = [
        item.get("content", "")
        for item in state.get("messages", [])
        if item.get("role") == "user"
    ]
    for content in user_history[-MAX_INSTRUCTION_HISTORY:]:
        messages.append({"role": "user", "content": content})

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


def last_user_message(state: MutableMapping[str, Any]) -> str:
    for item in reversed(state.get("messages", [])):
        if item.get("role") == "user":
            return item.get("content", "")
    return ""


def request_section_regeneration(
    state: MutableMapping[str, Any],
    section_index: int,
) -> None:
    state["pending_section_index"] = section_index
    state["is_regenerating_section"] = True


def apply_section_regeneration_result(
    state: MutableMapping[str, Any],
    updated_code: str,
) -> None:
    state["last_app_code"] = updated_code
    state["is_regenerating_section"] = False
    state["pending_section_index"] = None


def apply_section_regeneration_error(state: MutableMapping[str, Any]) -> None:
    state["is_regenerating_section"] = False
    state["pending_section_index"] = None


def seed_from_template(state: MutableMapping[str, Any], html: str) -> None:
    """Start a fresh conversation seeded with an existing page as the baseline."""
    state["messages"] = []
    state["last_app_code"] = html
    state["is_generating"] = False
    state["is_regenerating_section"] = False
    state["pending_section_index"] = None
    state["layout_dna_guidance"] = ""
