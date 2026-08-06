"""Build a generation client once at backend startup.

The existing ``src.generation`` module does the real work; here we only assemble
the provider-specific ``model`` / ``genai`` handles and config so the API layer
can call ``call_gemini`` / ``call_gemini_for_section`` unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.config import OPENROUTER_PROVIDER, AppConfig, load_config
from src.generation import (
    call_gemini,
    call_gemini_for_section,
)


@dataclass
class GenerationClient:
    config: AppConfig
    model: Any
    genai: Any


def build_client() -> GenerationClient:
    cfg = load_config()
    if cfg.provider == OPENROUTER_PROVIDER:
        return GenerationClient(config=cfg, model=cfg.openrouter_model, genai=None)
    try:
        import google.generativeai as genai  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - env dependent
        raise RuntimeError(
            "Module 'google.generativeai' not installed. "
            "Run `pip install google-generativeai`."
        ) from exc
    genai.configure(api_key=cfg.api_key)
    return GenerationClient(
        config=cfg, model=genai.GenerativeModel(cfg.model), genai=genai
    )


def generate(
    client: GenerationClient,
    *,
    messages: list[dict[str, str]],
    tone_key: str,
    strict_minimal: bool,
    complexity_key: str,
    extra_guidance: str = "",
) -> str:
    return call_gemini(
        model=client.model,
        genai=client.genai,
        messages=messages,
        temperature=client.config.temperature,
        max_output_tokens=client.config.max_output_tokens,
        tone_key=tone_key,
        strict_minimal=strict_minimal,
        complexity_key=complexity_key,
        extra_guidance=extra_guidance,
        analytics_file=client.config.analytics_file,
        provider=client.config.provider,
        api_key=client.config.openrouter_api_key or "",
        base_url=client.config.openrouter_base_url,
    )


def regenerate_section(
    client: GenerationClient,
    *,
    current_code: str,
    section,
    instructions: str,
    tone_key: str,
    strict_minimal: bool,
    complexity_key: str,
    extra_guidance: str = "",
    refine_aspect_key: str | None = None,
) -> str:
    return call_gemini_for_section(
        model=client.model,
        genai=client.genai,
        current_code=current_code,
        section=section,
        instructions=instructions,
        temperature=client.config.temperature,
        max_output_tokens=client.config.max_output_tokens,
        tone_key=tone_key,
        strict_minimal=strict_minimal,
        complexity_key=complexity_key,
        extra_guidance=extra_guidance,
        analytics_file=client.config.analytics_file,
        refine_aspect_key=refine_aspect_key,
        provider=client.config.provider,
        api_key=client.config.openrouter_api_key or "",
        base_url=client.config.openrouter_base_url,
    )
