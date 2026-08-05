from __future__ import annotations

from pathlib import Path

import pytest

from src.wysiwyg import (
    CSP_META_MARKER_NAME,
    EDITOR_SHIM_ID,
    EDITOR_STYLE_ID,
    SEL_CLASS,
    TOOLBAR_ID,
    build_editable_preview_document,
    consume_edit_message,
    is_full_document,
    strip_editor_injected_markup,
)

_FULL_DOC = (
    "<!doctype html><html lang='en'><head><title>x</title>"
    "<style>h1{color:red}</style></head><body><h1>Hi</h1><p>text</p></body></html>"
)
_FRAGMENT = "<div><p>hi</p></div>"


def test_is_full_document_detects_doctype_and_html_root() -> None:
    assert is_full_document(_FULL_DOC) is True
    assert is_full_document("<html><body>x</body></html>") is True
    assert is_full_document("   <!doctype html><html></html>") is True
    assert is_full_document(_FRAGMENT) is False
    assert is_full_document("") is False


def test_build_preview_document_injects_shim_only_when_editing() -> None:
    editing = build_editable_preview_document(_FULL_DOC, editing=True)
    assert EDITOR_SHIM_ID in editing
    assert EDITOR_STYLE_ID in editing
    assert CSP_META_MARKER_NAME in editing
    # original head content preserved
    assert "<title>x</title>" in editing
    assert "h1{color:red}" in editing

    not_editing = build_editable_preview_document(_FULL_DOC, editing=False)
    assert EDITOR_SHIM_ID not in not_editing
    assert EDITOR_STYLE_ID not in not_editing
    # CSP is still injected for sandbox safety, even when not editing
    assert CSP_META_MARKER_NAME in not_editing
    assert "<h1>Hi</h1>" in not_editing


def test_build_preview_document_wraps_fragments() -> None:
    doc = build_editable_preview_document(_FRAGMENT, editing=True)
    assert doc.startswith("<!doctype html>")
    assert EDITOR_SHIM_ID in doc
    assert "<p>hi</p>" in doc


def test_strip_editor_injected_markup_removes_all_markers() -> None:
    edited = build_editable_preview_document(_FULL_DOC, editing=True)
    cleaned = strip_editor_injected_markup(edited)
    assert EDITOR_SHIM_ID not in cleaned
    assert EDITOR_STYLE_ID not in cleaned
    assert CSP_META_MARKER_NAME not in cleaned
    assert SEL_CLASS not in cleaned
    assert TOOLBAR_ID not in cleaned
    # user content survives
    assert "<h1>Hi</h1>" in cleaned
    assert "<title>x</title>" in cleaned
    assert "h1{color:red}" in cleaned


def test_strip_is_idempotent() -> None:
    once = strip_editor_injected_markup(
        build_editable_preview_document(_FULL_DOC, editing=True)
    )
    assert strip_editor_injected_markup(once) == once


def test_consume_edit_message_applies_once_then_ignores_replay() -> None:
    state = {"last_edit_nonce": 0, "last_app_code": None}
    payload_html = build_editable_preview_document(_FULL_DOC, editing=True)
    msg = {"type": "mwb:edits", "nonce": 7, "html": payload_html}

    assert consume_edit_message(state, msg) is True
    assert state["last_edit_nonce"] == 7
    assert state["last_app_code"] is not None
    # editor markup stripped before storage
    assert EDITOR_SHIM_ID not in state["last_app_code"]
    assert "<h1>Hi</h1>" in state["last_app_code"]

    # replaying the same nonce is ignored
    assert consume_edit_message(state, msg) is False
    # a newer nonce applies again
    assert (
        consume_edit_message(
            state, {"type": "mwb:edits", "nonce": 8, "html": payload_html}
        )
        is True
    )
    assert state["last_edit_nonce"] == 8


def test_consume_edit_message_ignores_non_edit_messages_and_empty_html() -> None:
    state = {"last_edit_nonce": 0, "last_app_code": None}
    assert consume_edit_message(state, {"type": "mwb:none"}) is False
    assert (
        consume_edit_message(state, {"type": "mwb:edits", "nonce": 1, "html": ""})
        is False
    )
    assert state["last_app_code"] is None


def test_full_document_with_no_head_injects_before_body() -> None:
    no_head = "<html><body><h1>x</h1></body></html>"
    doc = build_editable_preview_document(no_head, editing=True)
    assert EDITOR_SHIM_ID in doc
    assert "<h1>x</h1>" in doc


def test_app_runs_headlessly_without_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("GENERATION_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    app = AppTest.from_file(
        str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=15
    ).run(timeout=15)

    assert not app.exception
