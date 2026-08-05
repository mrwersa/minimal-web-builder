from src.theme import (
    COLORS,
    DEFAULT_TONE_KEY,
    SPACING,
    STRICT_MINIMAL_GUIDANCE,
    TONE_PRESETS,
    TONE_PRESETS_BY_KEY,
    TYPE_SCALE,
    TonePreset,
    tone_options,
)


def test_default_tone_is_minimal() -> None:
    assert DEFAULT_TONE_KEY == "minimal"


def test_tone_presets_are_unique_and_keyed() -> None:
    keys = [t.key for t in TONE_PRESETS]
    assert len(keys) == len(set(keys))
    assert set(keys) == set(TONE_PRESETS_BY_KEY)
    assert all(isinstance(t, TonePreset) for t in TONE_PRESETS)


def test_tone_options_returns_ordered_keys() -> None:
    assert tone_options() == [t.key for t in TONE_PRESETS]


def test_tone_labels_include_roadmap_presets() -> None:
    labels = {t.label for t in TONE_PRESETS}
    assert {"Editorial", "Product", "Portfolio", "Landing"} <= labels


def test_required_tone_guidance_present() -> None:
    assert all(t.style_guidance for t in TONE_PRESETS)
    assert all(t.accent_hex for t in TONE_PRESETS)


def test_strict_minimal_guidance_defined() -> None:
    assert "monochrome" in STRICT_MINIMAL_GUIDANCE.lower()


def test_design_tokens_have_expected_keys() -> None:
    assert {"bg", "surface", "border", "text", "muted", "accent", "accent_soft"} <= set(COLORS)
    assert {"xs", "sm", "md", "lg", "xl"} <= set(SPACING)
    assert {"sm", "base", "lg", "xl", "xxl"} <= set(TYPE_SCALE)
