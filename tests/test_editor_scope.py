from __future__ import annotations

import pytest

from server.editor_scope import apply_scoped_generation, find_editor_element


def test_finds_nested_and_void_editor_elements() -> None:
    html = (
        '<main data-mwb-id="main"><section><strong data-mwb-id="target">'
        'Old</strong></section><img data-mwb-id="image"></main>'
    )

    assert find_editor_element(html, "target").html == (
        '<strong data-mwb-id="target">Old</strong>'
    )
    assert find_editor_element(html, "image").html == '<img data-mwb-id="image">'


def test_scoped_generation_replaces_only_the_selected_subtree() -> None:
    current = (
        '<html><body><header>Keep</header><main data-mwb-id="target">'
        "<h1>Old</h1></main><footer>Keep too</footer></body></html>"
    )
    generated = (
        '<html><body><header>Changed outside</header><main data-mwb-id="target" '
        'style="color: red"><h1>New</h1></main><footer>Changed</footer></body></html>'
    )

    result = apply_scoped_generation(current, generated, "target")

    assert "<header>Keep</header>" in result
    assert "<footer>Keep too</footer>" in result
    assert 'style="color: red"><h1>New</h1>' in result
    assert "Changed outside" not in result


def test_scoped_generation_rejects_a_removed_target() -> None:
    with pytest.raises(ValueError, match="removed"):
        apply_scoped_generation(
            '<main data-mwb-id="target">Old</main>',
            "<main>New</main>",
            "target",
        )
