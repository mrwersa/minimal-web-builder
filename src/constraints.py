from __future__ import annotations

from dataclasses import dataclass

from src.theme import COMPLEXITY_BY_KEY, DEFAULT_COMPLEXITY_KEY


@dataclass(frozen=True)
class SectionOption:
    key: str
    label: str


SECTION_OPTIONS = [
    SectionOption(key="hero", label="Hero"),
    SectionOption(key="features", label="Features"),
    SectionOption(key="about", label="About"),
    SectionOption(key="portfolio", label="Work / Portfolio"),
    SectionOption(key="pricing", label="Pricing"),
    SectionOption(key="testimonials", label="Testimonials"),
    SectionOption(key="faq", label="FAQ"),
    SectionOption(key="contact", label="Contact"),
    SectionOption(key="footer", label="Footer"),
]

SECTION_OPTIONS_BY_KEY: dict[str, SectionOption] = {s.key: s for s in SECTION_OPTIONS}


@dataclass(frozen=True)
class ColorLimit:
    key: str
    label: str
    description: str


COLOR_LIMITS = [
    ColorLimit(
        key="monochrome",
        label="Monochrome",
        description="grayscale only, with subtle tonal variation",
    ),
    ColorLimit(
        key="single-accent",
        label="Single accent",
        description="a neutral palette with exactly one accent color",
    ),
    ColorLimit(
        key="two-tone",
        label="Two-tone",
        description="a two-color palette used consistently",
    ),
]

COLOR_LIMITS_BY_KEY: dict[str, ColorLimit] = {c.key: c for c in COLOR_LIMITS}

DEFAULT_COLOR_LIMIT_KEY = "single-accent"


def build_constraints_prompt(
    sections: list[str],
    color_limit_key: str = DEFAULT_COLOR_LIMIT_KEY,
    density_key: str = DEFAULT_COMPLEXITY_KEY,
) -> str:
    """Compose a generation prompt from constraints; the model fills in the details."""
    section_names = ", ".join(sections) if sections else "any that fit the purpose"
    color = COLOR_LIMITS_BY_KEY.get(
        color_limit_key, COLOR_LIMITS_BY_KEY[DEFAULT_COLOR_LIMIT_KEY]
    )
    density = COMPLEXITY_BY_KEY.get(
        density_key, COMPLEXITY_BY_KEY[DEFAULT_COMPLEXITY_KEY]
    )
    return (
        "Generate a complete website from these constraints only; invent all content, "
        "copy, and details yourself.\n"
        f"- Required sections: {section_names}.\n"
        f"- Color limit: {color.description}.\n"
        f"- Density: {density.label.lower()} (controls page richness and copy length)."
    )
