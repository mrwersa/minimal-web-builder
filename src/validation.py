from __future__ import annotations

from typing import Optional, Tuple


def validate_user_prompt(prompt: str, max_prompt_chars: int) -> Tuple[Optional[str], Optional[str]]:
    normalized = prompt.strip()
    if not normalized:
        return None, "Please enter a prompt before generating a website."

    if len(normalized) > max_prompt_chars:
        return (
            None,
            f"Prompt is too long ({len(normalized)}/{max_prompt_chars} chars). Please shorten it.",
        )

    return normalized, None
