from __future__ import annotations

import re

_INLINE_SCRIPT_RE = re.compile(
    r"<script\b(?![^>]*\bsrc\s*=)[^>]*>(.*?)</script\s*>",
    re.IGNORECASE | re.DOTALL,
)

MAX_SCRIPT_STATEMENTS = 60
MAX_SCRIPT_LINES = 200

_DANGEROUS_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\beval\s*\(", "uses eval()"),
    (r"\bnew\s+Function\s*\(", "uses new Function()"),
    (r"\bdocument\.write\s*\(", "uses document.write()"),
)


def extract_inline_scripts(html: str) -> list[str]:
    """Return the bodies of inline <script> blocks, skipping external (src=) ones."""
    return [m.group(1) for m in _INLINE_SCRIPT_RE.finditer(html)]


def _strip_comments_and_literals(code: str) -> str:
    code = re.sub(r"//[^\n]*|/\*.*?\*/", "", code, flags=re.DOTALL)
    code = re.sub(r"<!--.*?-->", "", code, flags=re.DOTALL)
    code = re.sub(r"'(?:[^'\\]|\\.)*'", "", code)
    code = re.sub(r'"(?:[^"\\]|\\.)*"', "", code)
    code = re.sub(r"`(?:[^`\\]|\\.)*`", "", code)
    return code


def _statement_count(code: str) -> int:
    return _strip_comments_and_literals(code).count(";")


def inline_script_statement_count(html: str) -> int:
    """Total inline JS statement count across all inline <script> blocks."""
    return sum(_statement_count(code) for code in extract_inline_scripts(html))


def audit_inline_scripts(html: str) -> list[str]:
    """Run lightweight static checks on inline scripts (complexity, unsafe calls)."""
    alerts: list[str] = []
    for code in extract_inline_scripts(html):
        cleaned = _strip_comments_and_literals(code)
        if not cleaned.strip():
            alerts.append("Found an empty <script> block.")
            continue
        for pattern, description in _DANGEROUS_PATTERNS:
            if re.search(pattern, code):
                alerts.append(f"Found a <script> that {description}.")
        statements = _statement_count(code)
        if statements > MAX_SCRIPT_STATEMENTS:
            alerts.append(
                f"Found a <script> with {statements} statements; simplify it."
            )
        lines = sum(1 for line in code.splitlines() if line.strip())
        if lines > MAX_SCRIPT_LINES:
            alerts.append(
                f"Found a <script> with {lines} lines; consider splitting it."
            )
    return alerts
