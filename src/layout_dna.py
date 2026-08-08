from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from src.js_analysis import inline_script_statement_count
from src.sections import extract_sections

MAX_DNA_NAME_CHARS = 80


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


def suggest_dna_name(dna: LayoutDNA) -> str:
    """Create a stable, storage-neutral name from a layout grammar."""
    signature = grammar_signature(dna)
    stem = re.sub(r"[^A-Za-z0-9]+", "_", signature).strip("_")
    return (stem[:MAX_DNA_NAME_CHARS].rstrip("_") or "layout").lower()
