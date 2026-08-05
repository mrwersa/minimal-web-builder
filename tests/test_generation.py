from src.generation import build_generation_prompt, strip_html_code_fence
from src.theme import DEFAULT_TONE_KEY, STRICT_MINIMAL_GUIDANCE


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
