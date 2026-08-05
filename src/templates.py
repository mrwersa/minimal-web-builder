from __future__ import annotations

import re
from pathlib import Path

MAX_TEMPLATE_NAME_CHARS = 64
_TEMPLATE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def sanitize_template_name(name: str) -> str:
    """Validate and normalize a template name for safe local storage."""
    cleaned = name.strip()
    if cleaned.lower().endswith(".html"):
        cleaned = cleaned[: -len(".html")].rstrip()
    if not cleaned:
        raise ValueError("Template name cannot be empty.")
    if len(cleaned) > MAX_TEMPLATE_NAME_CHARS:
        raise ValueError(
            f"Template name must be at most {MAX_TEMPLATE_NAME_CHARS} characters."
        )
    if cleaned in (".", "..") or not _TEMPLATE_NAME_RE.match(cleaned):
        raise ValueError(
            "Template name may only contain letters, digits, dots, dashes, and underscores."
        )
    return cleaned


def list_templates(templates_dir: str | Path) -> list[str]:
    templates_dir = Path(templates_dir)
    if not templates_dir.is_dir():
        return []
    return sorted(p.stem for p in templates_dir.glob("*.html") if p.is_file())


def save_template(
    templates_dir: str | Path,
    name: str,
    html: str,
) -> Path:
    safe_name = sanitize_template_name(name)
    templates_dir = Path(templates_dir)
    templates_dir.mkdir(parents=True, exist_ok=True)
    path = templates_dir / f"{safe_name}.html"
    path.write_text(html, encoding="utf-8")
    return path


def load_template(templates_dir: str | Path, name: str) -> str:
    safe_name = sanitize_template_name(name)
    path = Path(templates_dir) / f"{safe_name}.html"
    return path.read_text(encoding="utf-8")


def delete_template(templates_dir: str | Path, name: str) -> None:
    safe_name = sanitize_template_name(name)
    path = Path(templates_dir) / f"{safe_name}.html"
    if path.exists():
        path.unlink()
