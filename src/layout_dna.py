from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from src.js_analysis import inline_script_statement_count
from src.sections import extract_sections

MAX_DNA_NAME_CHARS = 80
_DNA_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


@dataclass(frozen=True)
class LayoutDNA:
    """Compact structural fingerprint of an accepted page layout."""

    section_tags: tuple[str, ...]
    script_statement_count: int = 0

    @property
    def section_count(self) -> int:
        return len(self.section_tags)


def extract_layout_dna(html: str) -> LayoutDNA:
    """Extract the layout grammar of a page from its top-level sections and JS weight."""
    section_tags = tuple(section.tag for section in extract_sections(html))
    return LayoutDNA(
        section_tags=section_tags,
        script_statement_count=inline_script_statement_count(html),
    )


def grammar_signature(dna: LayoutDNA) -> str:
    """Human-readable grammar string, e.g. 'header/hero/features/footer'."""
    return "/".join(dna.section_tags) if dna.section_tags else "empty"


def to_guidance(dna: LayoutDNA) -> str:
    """Turn a layout into prompt guidance that tells the model to reuse its grammar."""
    script_note = (
        f" Keep inline JavaScript minimal (at most ~{dna.script_statement_count} "
        "statements total)."
        if dna.script_statement_count
        else " Do not add any JavaScript."
    )
    return (
        f"Reuse this layout grammar and page rhythm: {grammar_signature(dna)}. "
        f"Keep the same section order and overall structure.{script_note}"
    )


def combine_guidance(*parts: str) -> str:
    """Join non-empty guidance fragments with blank lines."""
    return "\n\n".join(part for part in parts if part and part.strip())


def to_dict(dna: LayoutDNA) -> dict:
    return asdict(dna)


def from_dict(data: dict) -> LayoutDNA:
    return LayoutDNA(
        section_tags=tuple(data.get("section_tags", ())),
        script_statement_count=int(data.get("script_statement_count", 0)),
    )


def _dna_stem(signature: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9]+", "_", signature).strip("_")
    return (stem[:MAX_DNA_NAME_CHARS].rstrip("_") or "layout").lower()


def save_dna(dna_dir: str | Path, dna: LayoutDNA) -> Path:
    """Persist a layout DNA to a JSON file with a unique name based on its grammar."""
    dna_dir = Path(dna_dir)
    dna_dir.mkdir(parents=True, exist_ok=True)
    stem = _dna_stem(grammar_signature(dna))
    path = dna_dir / f"{stem}.json"
    counter = 2
    while path.exists():
        path = dna_dir / f"{stem}-{counter}.json"
        counter += 1
    path.write_text(
        json.dumps(to_dict(dna), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def list_saved_dnas(dna_dir: str | Path) -> list[tuple[str, LayoutDNA]]:
    """Return [(stem, LayoutDNA), ...] for valid saved layouts, ordered by name."""
    dna_dir = Path(dna_dir)
    if not dna_dir.is_dir():
        return []
    saved: list[tuple[str, LayoutDNA]] = []
    for path in sorted(dna_dir.glob("*.json")):
        try:
            dna = from_dict(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
        saved.append((path.stem, dna))
    return saved


def load_dna(dna_dir: str | Path, name: str) -> LayoutDNA | None:
    """Load a saved layout by stem, guarding against unsafe names."""
    if not _DNA_NAME_RE.match(name):
        return None
    path = Path(dna_dir) / f"{name}.json"
    try:
        return from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (FileNotFoundError, json.JSONDecodeError, TypeError, ValueError):
        return None
