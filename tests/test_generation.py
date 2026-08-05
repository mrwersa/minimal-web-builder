from src.generation import build_generation_prompt, strip_html_code_fence


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
