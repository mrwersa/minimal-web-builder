from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser

SNIPPET_MAX_CHARS = 72

_WRAPPER_TAGS = ("html", "body")
_SKIP_TAGS = ("head", "script", "style", "noscript", "template")


@dataclass(frozen=True)
class PageSection:
    index: int
    tag: str
    snippet: str
    start: int
    end: int
    html: str


class _SectionScanner(HTMLParser):
    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=True)
        self._source = source
        self._line_starts: list[int] = [0]
        for i, char in enumerate(source):
            if char == "\n":
                self._line_starts.append(i + 1)
        self._stack: list[str] = []
        self.sections: list[PageSection] = []
        self._open_tag: str | None = None
        self._open_start: int | None = None
        self._snippet_parts: list[str] = []

    def _offset(self) -> int:
        line, col = self.getpos()
        return self._line_starts[line - 1] + col

    def _close_section(self, tag: str, end: int) -> None:
        section = PageSection(
            index=len(self.sections),
            tag=tag,
            snippet=" ".join(self._snippet_parts).strip()[:SNIPPET_MAX_CHARS],
            start=self._open_start or 0,
            end=end,
            html=self._source[(self._open_start or 0) : end],
        )
        self.sections.append(section)
        self._open_tag = None
        self._open_start = None
        self._snippet_parts = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if self._open_tag is None:
            self._open_tag = tag
            self._open_start = self._offset()
        self._stack.append(tag)

    def handle_startendtag(self, tag: str, attrs) -> None:
        raw = self.get_starttag_text() or f"<{tag}/>"
        if self._open_tag is None:
            start = self._offset()
            end = start + len(raw)
            self.sections.append(
                PageSection(
                    index=len(self.sections),
                    tag=tag,
                    snippet="",
                    start=start,
                    end=end,
                    html=self._source[start:end],
                )
            )

    def handle_data(self, data: str) -> None:
        if self._open_tag is not None:
            text = " ".join(data.split())
            if text:
                self._snippet_parts.append(text)

    def handle_endtag(self, tag: str) -> None:
        if self._stack and self._stack[-1] == tag:
            self._stack.pop()
        if tag == self._open_tag and self._open_tag is not None and not self._stack:
            self._close_section(tag, self._offset() + len(f"</{tag}>"))


def _unwrap(section: PageSection) -> str:
    """Return the inner content of a section, tolerating attributes on the open tag."""
    open_end = section.html.index(">") + 1
    close = f"</{section.tag}>"
    return section.html[open_end : len(section.html) - len(close)]


def _flatten(html: str, base: int) -> list[PageSection]:
    """Extract meaningful content sections, translating offsets to the full document."""
    scanner = _SectionScanner(html)
    scanner.feed(html)
    result: list[PageSection] = []
    for section in scanner.sections:
        if section.tag in _WRAPPER_TAGS:
            inner = _unwrap(section)
            inner_base = base + section.start + (section.html.index(">") + 1)
            result.extend(_flatten(inner, inner_base))
        elif section.tag in _SKIP_TAGS:
            continue
        else:
            result.append(
                PageSection(
                    index=len(result),
                    tag=section.tag,
                    snippet=section.snippet,
                    start=base + section.start,
                    end=base + section.end,
                    html=section.html,
                )
            )
    return result


def extract_sections(html: str) -> list[PageSection]:
    """Extract the meaningful top-level sections of a page with exact source ranges.

    Unwraps ``<html>``/``<body>`` containers and skips ``<head>``, ``<script>``,
    and other non-content subtrees, so hero/card/footer blocks surface as pickable
    sections while offsets remain usable against the original document.
    """
    return _flatten(html, 0)


def replace_section(html: str, section: PageSection, replacement: str) -> str:
    return html[: section.start] + replacement + html[section.end :]


def extract_first_top_level(html: str) -> str | None:
    """Return the first meaningful top-level element, skipping wrappers."""
    sections = extract_sections(html)
    if sections:
        return sections[0].html
    return None
