from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class AppConfig:
    api_key: str
    model: str
    temperature: float
    max_output_tokens: int


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def load_config() -> AppConfig:
    load_dotenv()
    return AppConfig(
        api_key=os.getenv("GEMINI_API_KEY", ""),
        model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        temperature=_float_env("GEMINI_TEMPERATURE", 0.2),
        max_output_tokens=_int_env("GEMINI_MAX_OUTPUT_TOKENS", 1500),
    )
