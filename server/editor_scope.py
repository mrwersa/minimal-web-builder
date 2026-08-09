"""Exact, stable-node scoping for AI editor refinements."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser

_VOID_ELEMENTS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


@dataclass(frozen=True)
class EditorElement:
    start: int
    end: int
    html: str


class _EditorElementScanner(HTMLParser):
    def __init__(self, source: str, node_id: str) -> None:
        super().__init__(convert_charrefs=False)
        self._source = source
        self._node_id = node_id
        self._line_starts = [0]
        self._line_starts.extend(
            index + 1 for index, character in enumerate(source) if character == "\n"
        )
        self._stack: list[str] = []
        self._target_tag: str | None = None
        self._target_depth: int | None = None
        self._target_start: int | None = None
        self.element: EditorElement | None = None

    def _offset(self) -> int:
        line, column = self.getpos()
        return self._line_starts[line - 1] + column

    def _start(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
        *,
        self_closing: bool = False,
    ) -> None:
        start = self._offset()
        if self._target_start is None and dict(attrs).get("data-mwb-id") == self._node_id:
            raw = self.get_starttag_text() or f"<{tag}>"
            if self_closing or tag in _VOID_ELEMENTS:
                end = start + len(raw)
                self.element = EditorElement(start, end, self._source[start:end])
            else:
                self._target_tag = tag
                self._target_depth = len(self._stack)
                self._target_start = start
        if not self_closing and tag not in _VOID_ELEMENTS:
            self._stack.append(tag)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._start(tag, attrs)

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self._start(tag, attrs, self_closing=True)

    def handle_endtag(self, tag: str) -> None:
        if (
            self.element is None
            and self._target_start is not None
            and tag == self._target_tag
            and len(self._stack) - 1 == self._target_depth
        ):
            end = self._offset() + len(f"</{tag}>")
            self.element = EditorElement(
                self._target_start,
                end,
                self._source[self._target_start : end],
            )
        if tag in self._stack:
            matching_index = len(self._stack) - 1 - self._stack[::-1].index(tag)
            del self._stack[matching_index:]


def find_editor_element(html: str, node_id: str) -> EditorElement | None:
    scanner = _EditorElementScanner(html, node_id)
    scanner.feed(html)
    return scanner.element


def apply_scoped_generation(current_html: str, generated_html: str, node_id: str) -> str:
    current = find_editor_element(current_html, node_id)
    generated = find_editor_element(generated_html, node_id)
    if current is None:
        raise ValueError("Selected element is missing from the current document")
    if generated is None:
        raise ValueError("Generated result removed the selected element")
    return current_html[: current.start] + generated.html + current_html[current.end :]
