from src.rendering import (
    EMPTY_STATE_HTML,
    NO_CODE_PLACEHOLDER,
    PREVIEW_LOADER_OVERLAY_HTML,
    build_app_styles,
    build_sandboxed_preview_html,
    preview_container_class,
)
from src.theme import COLORS


def test_preview_container_class_states() -> None:
    assert preview_container_class(False) == "preview-container"
    assert preview_container_class(True) == "preview-container blur"


def test_loader_overlay_markup_contains_message() -> None:
    assert "Generating your minimalist website" in PREVIEW_LOADER_OVERLAY_HTML


def test_empty_state_markup_contains_cta() -> None:
    assert "Start your creative journey" in EMPTY_STATE_HTML


def test_code_placeholder_value() -> None:
    assert NO_CODE_PLACEHOLDER == "<!-- No code generated yet -->"


def test_sandboxed_preview_wrapper_has_expected_iframe_guards() -> None:
    html_output = build_sandboxed_preview_html("<h1>Hello</h1>")

    assert 'sandbox="allow-scripts allow-forms"' in html_output
    assert 'referrerpolicy="no-referrer"' in html_output
    assert "Content-Security-Policy" in html_output


def test_sandboxed_preview_wrapper_escapes_srcdoc() -> None:
    html_output = build_sandboxed_preview_html('<h1>"Hi" & test</h1>')

    assert "&lt;h1&gt;&quot;Hi&quot; &amp; test&lt;/h1&gt;" in html_output


def test_app_styles_consume_design_tokens() -> None:
    styles = build_app_styles()

    assert "$" not in styles
    assert COLORS["bg"] in styles
    assert COLORS["accent"] in styles
    assert COLORS["surface"] in styles


def test_app_styles_contain_key_selectors() -> None:
    styles = build_app_styles()

    assert "stChatInput" in styles
    assert "preview-container" in styles
    assert "stTabs" in styles
