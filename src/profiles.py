from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from src.theme import (
    COMPLEXITY_BY_KEY,
    DEFAULT_COMPLEXITY_KEY,
    DEFAULT_TONE_KEY,
    TONE_PRESETS_BY_KEY,
)

CUSTOM_PROFILE_ID = "custom"


@dataclass(frozen=True)
class GenerationProfile:
    id: str
    label: str
    description: str
    tone_key: str
    complexity_key: str
    strict_minimal: bool
    extra_guidance: str


def load_profiles(profiles_dir: str | Path) -> list[GenerationProfile]:
    """Load all ``*.json`` generation profiles from a directory, sorted by id."""
    profiles_dir = Path(profiles_dir)
    return [_load_profile_file(path) for path in sorted(profiles_dir.glob("*.json"))]


def _load_profile_file(path: Path) -> GenerationProfile:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid profile file: {path.name}") from exc
    if not isinstance(data, dict):
        raise TypeError(f"Invalid profile file: {path.name}")

    profile_id = path.stem
    tone_key = data.get("tone_key", DEFAULT_TONE_KEY)
    complexity_key = data.get("complexity_key", DEFAULT_COMPLEXITY_KEY)
    if tone_key not in TONE_PRESETS_BY_KEY:
        raise ValueError(f"Unknown tone_key '{tone_key}' in {path.name}")
    if complexity_key not in COMPLEXITY_BY_KEY:
        raise ValueError(f"Unknown complexity_key '{complexity_key}' in {path.name}")

    return GenerationProfile(
        id=profile_id,
        label=str(data.get("label", profile_id)),
        description=str(data.get("description", "")),
        tone_key=tone_key,
        complexity_key=complexity_key,
        strict_minimal=bool(data.get("strict_minimal", False)),
        extra_guidance=str(data.get("extra_guidance", "")),
    )


def get_profile(
    profiles: list[GenerationProfile],
    profile_id: str,
) -> GenerationProfile | None:
    for profile in profiles:
        if profile.id == profile_id:
            return profile
    return None


def profile_options(profiles: list[GenerationProfile]) -> list[str]:
    """Sidebar options: the manual 'Custom' control plus every profile id."""
    return [CUSTOM_PROFILE_ID, *[profile.id for profile in profiles]]
