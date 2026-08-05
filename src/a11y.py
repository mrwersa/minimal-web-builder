from __future__ import annotations

from html.parser import HTMLParser
from typing import Dict, List, Set


class _A11yAuditor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.alerts: List[str] = []
        self._stack: List[str] = []
        self._h1_count = 0
        self._label_for: Set[str] = set()

    def _inside_label(self) -> bool:
        return "label" in self._stack

    @staticmethod
    def _attrs(attrs) -> Dict[str, str]:
        return {key: value for key, value in attrs}

    def handle_starttag(self, tag: str, attrs) -> None:
        self._stack.append(tag)
        attrs_dict = self._attrs(attrs)

        if tag == "img":
            if attrs_dict.get("alt") is None:
                self.alerts.append("Found an <img> without an alt attribute.")
        elif tag == "h1":
            self._h1_count += 1
        elif tag == "label":
            for_id = attrs_dict.get("for")
            if for_id:
                self._label_for.add(for_id)
        elif tag in ("input", "select", "textarea"):
            self._check_form_control(tag, attrs_dict)
            self._check_tabindex(attrs_dict)

    def handle_startendtag(self, tag: str, attrs) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if self._stack and self._stack[-1] == tag:
            self._stack.pop()

    def _check_form_control(self, tag: str, attrs_dict: Dict[str, str]) -> None:
        has_aria_name = bool(
            attrs_dict.get("aria-label") or attrs_dict.get("aria-labelledby")
        )
        element_id = attrs_dict.get("id")
        labelled = (
            has_aria_name
            or self._inside_label()
            or (element_id is not None and element_id in self._label_for)
        )
        if not labelled:
            self.alerts.append(
                f"Found a <{tag}> control without an accessible name (add aria-label or a <label>)."
            )

    def _check_tabindex(self, attrs_dict: Dict[str, str]) -> None:
        tabindex = attrs_dict.get("tabindex")
        if tabindex is None:
            return
        try:
            if int(tabindex) > 0:
                self.alerts.append("Found tabindex > 0, which disrupts the natural tab order.")
        except ValueError:
            return

    def finish(self) -> List[str]:
        if self._h1_count > 1:
            self.alerts.append(
                "Found more than one <h1> heading; use a single <h1> for the page title."
            )
        return self.alerts


def audit_generated_html(html: str) -> List[str]:
    """Run lightweight static accessibility checks on generated HTML."""
    auditor = _A11yAuditor()
    auditor.feed(html)
    return auditor.finish()
