from src.validation import validate_user_prompt


def test_validate_user_prompt_rejects_blank() -> None:
    prompt, error = validate_user_prompt("   ", max_prompt_chars=100)
    assert prompt is None
    assert error is not None


def test_validate_user_prompt_rejects_too_long() -> None:
    prompt, error = validate_user_prompt("a" * 6, max_prompt_chars=5)
    assert prompt is None
    assert error is not None
    assert "6/5" in error


def test_validate_user_prompt_returns_trimmed_text() -> None:
    prompt, error = validate_user_prompt("  build landing page  ", max_prompt_chars=100)
    assert error is None
    assert prompt == "build landing page"
