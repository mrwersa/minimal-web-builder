from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser


@dataclass(frozen=True)
class SplitDocument:
    index_html: str
    styles_css: str
    app_js: str


class _SplitScanner(HTMLParser):
    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=True)
        self._source = source
        self._line_starts: list[int] = [0]
        for i, char in enumerate(source):
            if char == "\n":
                self._line_starts.append(i + 1)
        self._stack: list[str] = []
        self._open_style_start: int | None = None
        self._open_script: dict[str, int | bool] | None = None
        self.style_blocks: list[tuple[int, int]] = []
        self.script_blocks: list[tuple[int, int]] = []

    def _offset(self) -> int:
        line, col = self.getpos()
        return self._line_starts[line - 1] + col

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "style" and self._open_style_start is None:
            self._open_style_start = self._offset()
        elif tag == "script" and self._open_script is None:
            self._open_script = {
                "start": self._offset(),
                "has_src": any(key == "src" for key, _ in attrs),
            }
        self._stack.append(tag)

    def handle_startendtag(self, tag: str, attrs) -> None:
        pass

    def handle_endtag(self, tag: str) -> None:
        if self._stack and self._stack[-1] == tag:
            self._stack.pop()
        if tag == "style" and self._open_style_start is not None:
            self.style_blocks.append(
                (self._open_style_start, self._offset() + len("</style>"))
            )
            self._open_style_start = None
        elif tag == "script" and self._open_script is not None:
            if not self._open_script["has_src"]:
                self.script_blocks.append(
                    (self._open_script["start"], self._offset() + len("</script>"))
                )
            self._open_script = None


def _inner_content(source: str, start: int, end: int, tag: str) -> str:
    open_end = source.index(">", start) + 1
    close = f"</{tag}>"
    return source[open_end : end - len(close)]


def split_document(html: str) -> SplitDocument:
    """Split a self-contained page into index.html, styles.css, and app.js.

    Inline ``<style>`` blocks are extracted into ``styles_css`` and inline
    ``<script>`` blocks into ``app_js``; each is replaced in ``index_html`` by a
    ``<link>``/``<script src>`` reference. Scripts that already carry a ``src``
    attribute (external) are left untouched. Blocks without content are skipped.
    """
    scanner = _SplitScanner(html)
    scanner.feed(html)

    styles = "\n".join(
        _inner_content(html, start, end, "style") for start, end in scanner.style_blocks
    ).strip()
    scripts = "\n".join(
        _inner_content(html, start, end, "script")
        for start, end in scanner.script_blocks
    ).strip()

    index_html = html
    replacements: list[tuple[int, int, str]] = []
    if styles:
        for i, (start, end) in enumerate(scanner.style_blocks):
            ref = '<link rel="stylesheet" href="styles.css">' if i == 0 else ""
            replacements.append((start, end, ref))
    if scripts:
        for i, (start, end) in enumerate(scanner.script_blocks):
            ref = '<script src="app.js"></script>' if i == 0 else ""
            replacements.append((start, end, ref))
    for start, end, replacement in sorted(replacements, reverse=True):
        index_html = index_html[:start] + replacement + index_html[end:]

    return SplitDocument(
        index_html=index_html,
        styles_css=styles,
        app_js=scripts,
    )
