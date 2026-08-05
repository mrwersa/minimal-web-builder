from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TonePreset:
    key: str
    label: str
    style_guidance: str
    accent_hex: str


TONE_PRESETS = [
    TonePreset(
        key="minimal",
        label="Minimal",
        style_guidance=(
            "Monochromatic neutral palette with at most one subtle accent, "
            "generous whitespace, thin borders, flat surfaces, and no decorative gradients or shadows."
        ),
        accent_hex="#111827",
    ),
    TonePreset(
        key="editorial",
        label="Editorial",
        style_guidance=(
            "Serif headlines over clean body text, high-contrast black on warm off-white, "
            "elegant generous spacing, restrained color, magazine-like hierarchy."
        ),
        accent_hex="#1a1a1a",
    ),
    TonePreset(
        key="product",
        label="Product",
        style_guidance=(
            "Modern SaaS landing feel with one strong accent color, card-based layout, "
            "subtle shadows, crisp utility-driven typography, clear call-to-action hierarchy."
        ),
        accent_hex="#2563eb",
    ),
    TonePreset(
        key="portfolio",
        label="Portfolio",
        style_guidance=(
            "Personal and creative, asymmetric layout with strong typographic moments, "
            "expressive accent color, generous whitespace, distinctive but tasteful."
        ),
        accent_hex="#e11d48",
    ),
    TonePreset(
        key="landing",
        label="Landing",
        style_guidance=(
            "High-converting landing page: clear headline, hero with value proposition, "
            "social proof section, pricing or feature grid, and a prominent final call-to-action."
        ),
        accent_hex="#0ea5e9",
    ),
]

TONE_PRESETS_BY_KEY: dict[str, TonePreset] = {t.key: t for t in TONE_PRESETS}

DEFAULT_TONE_KEY = "minimal"


@dataclass(frozen=True)
class ComplexityLevel:
    key: str
    label: str
    guidance: str


COMPLEXITY_LEVELS = [
    ComplexityLevel(
        key="compact",
        label="Compact",
        guidance=(
            "Build the smallest possible page: 1-2 sections, short copy, and no optional features. "
            "Every element must earn its place."
        ),
    ),
    ComplexityLevel(
        key="balanced",
        label="Balanced",
        guidance=(
            "Build a focused page with the essential sections (hero, content, and a footer) "
            "and moderate copy length. Avoid optional extras."
        ),
    ),
    ComplexityLevel(
        key="detailed",
        label="Detailed",
        guidance=(
            "Build a richer page with additional sections and features, longer copy, and tasteful "
            "enhancements, while still keeping the overall design minimal."
        ),
    ),
]

COMPLEXITY_BY_KEY: dict[str, ComplexityLevel] = {c.key: c for c in COMPLEXITY_LEVELS}

DEFAULT_COMPLEXITY_KEY = "balanced"

STRICT_MINIMAL_GUIDANCE = (
    "Strict minimal mode: use ONLY a neutral monochrome palette with at most one accent color, "
    "maximal whitespace, flat surfaces, no gradients, no drop shadows, no animations or decorative "
    "effects, and limit the page to the fewest sections needed to communicate clearly."
)


@dataclass(frozen=True)
class RefineAspect:
    key: str
    label: str
    guidance: str


REFINE_ASPECTS = [
    RefineAspect(
        key="general",
        label="General",
        guidance=(
            "Make a broad improvement while staying consistent with the rest of the page."
        ),
    ),
    RefineAspect(
        key="spacing",
        label="Spacing",
        guidance=(
            "Adjust spacing only: padding, margins, gaps, and whitespace for better rhythm "
            "and breathing room. Do not change colors, typography, or content."
        ),
    ),
    RefineAspect(
        key="typography",
        label="Typography",
        guidance=(
            "Adjust typography only: font sizes, weights, line-height, letter-spacing, and "
            "heading hierarchy. Do not change colors, spacing, or content."
        ),
    ),
    RefineAspect(
        key="layout",
        label="Layout",
        guidance=(
            "Adjust layout only: the arrangement, ordering, alignment, and responsiveness of "
            "the section's blocks. Do not change colors, typography, or content."
        ),
    ),
    RefineAspect(
        key="color",
        label="Color",
        guidance=(
            "Adjust color only: palette, contrast, and accents while keeping WCAG AA contrast. "
            "Do not change layout, typography, or content."
        ),
    ),
]

REFINE_ASPECTS_BY_KEY: dict[str, RefineAspect] = {a.key: a for a in REFINE_ASPECTS}

DEFAULT_REFINE_ASPECT_KEY = "general"

# Shared UI design tokens (Streamlit theme consistency).
COLORS = {
    "bg": "#f7f9fb",
    "surface": "#ffffff",
    "border": "#e3e8ee",
    "text": "#222222",
    "muted": "#78909c",
    "accent": "#1976d2",
    "accent_soft": "#e3f2fd",
    "disabled": "#b0b8c1",
}

SPACING = {"xs": 4, "sm": 8, "md": 16, "lg": 24, "xl": 32}

TYPE_SCALE = {"sm": 13, "base": 14, "lg": 16, "xl": 20, "xxl": 28}


def tone_options() -> list[str]:
    return [t.key for t in TONE_PRESETS]


def complexity_options() -> list[str]:
    return [c.key for c in COMPLEXITY_LEVELS]
