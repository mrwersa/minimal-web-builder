from src.rendering import (
    build_sandboxed_preview_html,
    EMPTY_STATE_HTML,
    NO_CODE_PLACEHOLDER,
    PREVIEW_LOADER_OVERLAY_HTML,
    preview_container_class,
)


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
