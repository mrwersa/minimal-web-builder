from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser

_INTERACTIVE_TAGS = ("a", "button", "input", "select", "textarea", "summary", "details")


@dataclass
class _FormControl:
    tag: str
    attrs: dict[str, str]
    inside_label: bool = False


class _A11yScanner(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._stack: list[str] = []
        self._h1_count = 0
        self._label_for: set[str] = set()
        self._form_controls: list[_FormControl] = []
        self._images_without_alt = 0
        self._positive_tabindex = False
        self._interactive_count = 0
        self._style_content: list[str] = []

    def _inside_label(self) -> bool:
        return "label" in self._stack

    def _inside_style(self) -> bool:
        return "style" in self._stack

    @staticmethod
    def _attrs(attrs) -> dict[str, str]:
        return {key: value for key, value in attrs}

    def handle_starttag(self, tag: str, attrs) -> None:
        self._stack.append(tag)
        attrs_dict = self._attrs(attrs)

        if tag == "img":
            if attrs_dict.get("alt") is None:
                self._images_without_alt += 1
        elif tag == "h1":
            self._h1_count += 1
        elif tag == "label":
            for_id = attrs_dict.get("for")
            if for_id:
                self._label_for.add(for_id)
        elif tag in ("input", "select", "textarea"):
            self._form_controls.append(
                _FormControl(tag, attrs_dict, self._inside_label())
            )
            self._check_tabindex(attrs_dict)
            self._interactive_count += 1
        elif tag in _INTERACTIVE_TAGS or "tabindex" in attrs_dict:
            self._interactive_count += 1

    def handle_startendtag(self, tag: str, attrs) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if self._stack and self._stack[-1] == tag:
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        if self._inside_style():
            self._style_content.append(data)

    def _check_tabindex(self, attrs_dict: dict[str, str]) -> None:
        tabindex = attrs_dict.get("tabindex")
        if tabindex is None:
            return
        try:
            if int(tabindex) > 0:
                self._positive_tabindex = True
        except ValueError:
            return

    def finish(self) -> list[str]:
        alerts: list[str] = []
        if self._images_without_alt:
            alerts.append("Found an <img> without an alt attribute.")
        if self._h1_count > 1:
            alerts.append(
                "Found more than one <h1> heading; use a single <h1> for the page title."
            )
        if self._positive_tabindex:
            alerts.append("Found tabindex > 0, which disrupts the natural tab order.")
        for control in self._form_controls:
            if not self._is_labelled(control):
                alerts.append(
                    f"Found a <{control.tag}> control without an accessible name "
                    "(add aria-label or a <label>)."
                )
        if self._interactive_count and not self._has_focus_style():
            alerts.append(
                "No visible keyboard focus styles detected; add :focus-visible styles "
                "for interactive elements."
            )
        return alerts

    def _has_focus_style(self) -> bool:
        css = "".join(self._style_content)
        return re.search(r":focus(?:-visible)?(?:::[-\w]+)?\s*\{", css) is not None

    def _is_labelled(self, control: _FormControl) -> bool:
        attrs = control.attrs
        has_aria_name = bool(attrs.get("aria-label") or attrs.get("aria-labelledby"))
        element_id = attrs.get("id")
        return (
            has_aria_name
            or control.inside_label
            or (element_id is not None and element_id in self._label_for)
        )


def audit_generated_html(html: str) -> list[str]:
    """Run lightweight static accessibility checks on generated HTML."""
    scanner = _A11yScanner()
    scanner.feed(html)
    return scanner.finish()
