from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import dotenv_values, load_dotenv

GEMINI_PROVIDER = "gemini"
OPENROUTER_PROVIDER = "openrouter"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_MODEL = "google/gemini-2.5-flash"


@dataclass(frozen=True)
class AppConfig:
    api_key: str
    model: str
    temperature: float
    max_output_tokens: int
    max_prompt_chars: int
    analytics_file: str | None = None
    provider: str = GEMINI_PROVIDER
    openrouter_api_key: str | None = None
    openrouter_model: str = DEFAULT_OPENROUTER_MODEL
    openrouter_base_url: str = DEFAULT_OPENROUTER_BASE_URL
    database_url: str = "sqlite:///./data/minimal-web-builder.db"
    session_cookie_secure: bool = False
    session_hours: int = 168
    cors_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )
    auth_rate_limit_per_minute: int = 10
    generation_rate_limit_per_minute: int = 30
    generation_timeout_seconds: int = 120
    generation_max_concurrency: int = 4


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


def _str_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def cors_origins_from_env(
    dotenv_path: str | os.PathLike | None = ".env",
) -> tuple[str, ...]:
    raw = os.getenv("CORS_ORIGINS")
    if raw is None and dotenv_path is not None:
        raw = dotenv_values(dotenv_path).get("CORS_ORIGINS")
    raw = (raw or "http://localhost:5173,http://127.0.0.1:5173").strip()
    return tuple(origin.strip() for origin in raw.split(",") if origin.strip())


def load_config(dotenv_path: str | os.PathLike | None = None) -> AppConfig:
    load_dotenv(dotenv_path)
    provider = _str_env("GENERATION_PROVIDER", GEMINI_PROVIDER).lower()
    if provider not in (GEMINI_PROVIDER, OPENROUTER_PROVIDER):
        provider = GEMINI_PROVIDER
    return AppConfig(
        api_key=_str_env("GEMINI_API_KEY"),
        model=_str_env("GEMINI_MODEL", "gemini-1.5-flash"),
        temperature=_float_env("GEMINI_TEMPERATURE", 0.2),
        max_output_tokens=_int_env("GEMINI_MAX_OUTPUT_TOKENS", 8192),
        max_prompt_chars=_int_env("GEMINI_MAX_PROMPT_CHARS", 1200),
        analytics_file=os.getenv("ANALYTICS_FILE") or None,
        provider=provider,
        openrouter_api_key=_str_env("OPENROUTER_API_KEY") or None,
        openrouter_model=_str_env("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL),
        openrouter_base_url=_str_env(
            "OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL
        ),
        database_url=_str_env(
            "DATABASE_URL", "sqlite:///./data/minimal-web-builder.db"
        ),
        session_cookie_secure=_bool_env("SESSION_COOKIE_SECURE", False),
        session_hours=max(1, _int_env("SESSION_HOURS", 168)),
        cors_origins=cors_origins_from_env(),
        auth_rate_limit_per_minute=max(1, _int_env("AUTH_RATE_LIMIT_PER_MINUTE", 10)),
        generation_rate_limit_per_minute=max(
            1, _int_env("GENERATION_RATE_LIMIT_PER_MINUTE", 30)
        ),
        generation_timeout_seconds=max(1, _int_env("GENERATION_TIMEOUT_SECONDS", 120)),
        generation_max_concurrency=max(1, _int_env("GENERATION_MAX_CONCURRENCY", 4)),
    )
