from src.constraints import (
    COLOR_LIMITS,
    COLOR_LIMITS_BY_KEY,
    DEFAULT_COLOR_LIMIT_KEY,
    SECTION_OPTIONS,
    SECTION_OPTIONS_BY_KEY,
    build_constraints_prompt,
)


def test_section_options_unique_and_keyed() -> None:
    keys = [s.key for s in SECTION_OPTIONS]
    assert len(keys) == len(set(keys))
    assert set(keys) == set(SECTION_OPTIONS_BY_KEY)
    assert all(s.label for s in SECTION_OPTIONS)
    assert {"hero", "features", "footer", "contact"} <= set(keys)


def test_color_limits_unique_and_keyed() -> None:
    keys = [c.key for c in COLOR_LIMITS]
    assert len(keys) == len(set(keys))
    assert set(keys) == set(COLOR_LIMITS_BY_KEY)
    assert all(c.description for c in COLOR_LIMITS)
    assert {"monochrome", "single-accent", "two-tone"} <= set(keys)
    assert DEFAULT_COLOR_LIMIT_KEY in COLOR_LIMITS_BY_KEY


def test_build_constraints_prompt_includes_sections() -> None:
    prompt = build_constraints_prompt(["hero", "contact"])
    assert "hero, contact" in prompt
    assert "Required sections" in prompt


def test_build_constraints_prompt_defaults_to_any_sections() -> None:
    prompt = build_constraints_prompt([])
    assert "any that fit the purpose" in prompt


def test_build_constraints_prompt_includes_color_limit() -> None:
    prompt = build_constraints_prompt(["hero"], color_limit_key="monochrome")
    assert "grayscale only" in prompt
    assert "Color limit" in prompt


def test_build_constraints_prompt_includes_density() -> None:
    prompt = build_constraints_prompt(["hero"], density_key="compact")
    assert "compact" in prompt
    assert "Density" in prompt


def test_build_constraints_prompt_falls_back_on_unknown_keys() -> None:
    prompt = build_constraints_prompt(
        ["hero"], color_limit_key="nope", density_key="nope"
    )
    assert "grayscale only" not in prompt
    assert "Color limit" in prompt
    assert "Density" in prompt
