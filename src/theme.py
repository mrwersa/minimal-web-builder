from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


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

TONE_PRESETS_BY_KEY: Dict[str, TonePreset] = {t.key: t for t in TONE_PRESETS}

DEFAULT_TONE_KEY = "minimal"

STRICT_MINIMAL_GUIDANCE = (
    "Strict minimal mode: use ONLY a neutral monochrome palette with at most one accent color, "
    "maximal whitespace, flat surfaces, no gradients, no drop shadows, no animations or decorative "
    "effects, and limit the page to the fewest sections needed to communicate clearly."
)

# Shared UI design tokens (Streamlit theme consistency).
COLORS = {
    "bg": "#f7f9fb",
    "surface": "#ffffff",
    "border": "#e3e8ee",
    "text": "#222222",
    "muted": "#78909c",
    "accent": "#1976d2",
    "accent_soft": "#e3f2fd",
}

SPACING = {"xs": 4, "sm": 8, "md": 16, "lg": 24, "xl": 32}

TYPE_SCALE = {"sm": 13, "base": 14, "lg": 16, "xl": 20, "xxl": 28}


def tone_options() -> list[str]:
    return [t.key for t in TONE_PRESETS]
