import json
from pathlib import Path

import pytest

from src.generation import build_generation_prompt, build_section_regeneration_prompt
from src.profiles import (
    CUSTOM_PROFILE_ID,
    GenerationProfile,
    get_profile,
    load_profiles,
    profile_options,
)
from src.sections import PageSection


def _write_profile(tmp_path: Path, name: str, data: dict) -> Path:
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_load_profiles_discovers_and_sorts_json_files(tmp_path: Path) -> None:
    _write_profile(tmp_path, "minimal", {"label": "Minimal"})
    _write_profile(
        tmp_path,
        "portfolio",
        {"tone_key": "portfolio", "complexity_key": "balanced"},
    )

    profiles = load_profiles(tmp_path)

    assert [p.id for p in profiles] == ["minimal", "portfolio"]
    assert profiles[0].label == "Minimal"


def test_load_profiles_uses_defaults_for_optional_fields(tmp_path: Path) -> None:
    _write_profile(tmp_path, "basic", {})

    profile = load_profiles(tmp_path)[0]

    assert profile.id == "basic"
    assert profile.label == "basic"
    assert profile.description == ""
    assert profile.tone_key == "minimal"
    assert profile.complexity_key == "balanced"
    assert profile.strict_minimal is False
    assert profile.extra_guidance == ""


def test_load_profiles_reads_full_config(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "landing",
        {
            "label": "Startup Landing",
            "description": "hero, features, pricing",
            "tone_key": "landing",
            "complexity_key": "detailed",
            "strict_minimal": True,
            "extra_guidance": "Add a final CTA.",
        },
    )

    profile = load_profiles(tmp_path)[0]

    assert isinstance(profile, GenerationProfile)
    assert profile.label == "Startup Landing"
    assert profile.description == "hero, features, pricing"
    assert profile.tone_key == "landing"
    assert profile.complexity_key == "detailed"
    assert profile.strict_minimal is True
    assert profile.extra_guidance == "Add a final CTA."


def test_load_profiles_rejects_unknown_tone_key(tmp_path: Path) -> None:
    _write_profile(tmp_path, "bad", {"tone_key": "fancy"})

    with pytest.raises(ValueError, match="tone_key"):
        load_profiles(tmp_path)


def test_load_profiles_rejects_unknown_complexity_key(tmp_path: Path) -> None:
    _write_profile(tmp_path, "bad", {"complexity_key": "huge"})

    with pytest.raises(ValueError, match="complexity_key"):
        load_profiles(tmp_path)


def test_load_profiles_rejects_invalid_json(tmp_path: Path) -> None:
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid profile file"):
        load_profiles(tmp_path)


def test_load_profiles_rejects_non_dict_json(tmp_path: Path) -> None:
    (tmp_path / "list.json").write_text("[1, 2, 3]", encoding="utf-8")

    with pytest.raises(TypeError, match="Invalid profile file"):
        load_profiles(tmp_path)


def test_get_profile_returns_matching_profile(tmp_path: Path) -> None:
    _write_profile(tmp_path, "minimal", {"label": "Minimal"})
    profiles = load_profiles(tmp_path)

    assert get_profile(profiles, "minimal").label == "Minimal"


def test_get_profile_missing_returns_none(tmp_path: Path) -> None:
    _write_profile(tmp_path, "minimal", {})
    profiles = load_profiles(tmp_path)

    assert get_profile(profiles, "nope") is None


def test_profile_options_starts_with_custom(tmp_path: Path) -> None:
    _write_profile(tmp_path, "minimal", {})
    _write_profile(tmp_path, "portfolio", {})

    options = profile_options(load_profiles(tmp_path))

    assert options == [CUSTOM_PROFILE_ID, "minimal", "portfolio"]


def test_repo_profiles_are_valid() -> None:
    profiles_dir = Path(__file__).resolve().parents[1] / "profiles"
    profiles = load_profiles(profiles_dir)

    assert {p.id for p in profiles} == {"minimal", "startup-landing", "portfolio"}
    assert all(p.label for p in profiles)


def test_build_generation_prompt_includes_profile_guidance() -> None:
    prompt = build_generation_prompt(
        [{"role": "user", "content": "hello"}],
        tone_key="landing",
        complexity_key="detailed",
        extra_guidance="Structure: hero, features, pricing, CTA.",
    )

    assert "Additional style constraints:" in prompt
    assert "Structure: hero, features, pricing, CTA." in prompt


def test_build_section_regeneration_prompt_includes_profile_guidance() -> None:
    section = PageSection(
        index=0,
        tag="main",
        snippet="x",
        start=0,
        end=len("<main>x</main>"),
        html="<main>x</main>",
    )
    prompt = build_section_regeneration_prompt(
        "<html><body><main>x</main></body></html>",
        section,
        "keep it consistent",
        extra_guidance="Match the startup landing tone.",
    )

    assert "Match the startup landing tone." in prompt
