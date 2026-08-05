from __future__ import annotations

import time
from typing import Any

from src.observability import GenerationEvent, record
from src.sections import PageSection
from src.theme import (
    COMPLEXITY_BY_KEY,
    DEFAULT_COMPLEXITY_KEY,
    DEFAULT_TONE_KEY,
    REFINE_ASPECTS_BY_KEY,
    STRICT_MINIMAL_GUIDANCE,
    TONE_PRESETS_BY_KEY,
)

BASE_PROMPT = (
    "You are an expert web app developer and UI designer specializing in minimalist, clean designs.\n"
    "Your task: Generate a beautiful, modern, and minimalistic single-page web app using only HTML, CSS, and minimal JavaScript.\n"
    "Requirements:\n"
    "- Create a MINIMALIST design with clean typography, ample whitespace, and subtle effects\n"
    "- Use best practices for accessibility, responsiveness, and performance\n"
    "- Accessibility: ensure text has sufficient contrast against its background (WCAG AA or better), "
    "provide visible focus indicators for keyboard navigation, use semantic HTML landmarks, "
    "label all form controls, and keep heading structure hierarchical with a single <h1>\n"
    "- Focus on simplicity, readability and usability\n"
    "- Use modern CSS (Flexbox/Grid) but keep visual elements minimal\n"
    "- Avoid unnecessary frameworks, libraries, or decorative elements\n"
    "- Use a monochromatic or limited color palette\n"
    "- ALL images/icons must be inline SVG (no external images or links)\n"
    "- The HTML must be fully self-contained with NO external dependencies or CDN links\n"
    "- If you generate navigation or tabs, do NOT use anchor links or change the URL. Use JavaScript to show/hide content sections for tab navigation. All navigation must be fully client-side and must not reload or redirect the page.\n"
    "- Return ONLY the complete HTML/CSS/JS code block, no explanations\n"
    "- The code should be ready to copy-paste and run"
)


def _style_guidance(tone_key: str, strict_minimal: bool) -> str:
    guidance: list[str] = []
    preset = TONE_PRESETS_BY_KEY.get(tone_key)
    if preset is not None:
        guidance.append(f"Style direction: {preset.style_guidance}")
    if strict_minimal:
        guidance.append(STRICT_MINIMAL_GUIDANCE)
    return "\n".join(guidance)


def _complexity_guidance(complexity_key: str) -> str:
    level = COMPLEXITY_BY_KEY.get(complexity_key)
    if level is None:
        return ""
    return f"Complexity: {level.guidance}"


def build_generation_prompt(
    messages: list[dict[str, str]],
    tone_key: str = DEFAULT_TONE_KEY,
    strict_minimal: bool = False,
    complexity_key: str = DEFAULT_COMPLEXITY_KEY,
    extra_guidance: str = "",
) -> str:
    conversation = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
    base_prompt = BASE_PROMPT
    guidance = _style_guidance(tone_key, strict_minimal)
    complexity = _complexity_guidance(complexity_key)
    if complexity:
        guidance = f"{guidance}\n{complexity}" if guidance else complexity
    if extra_guidance:
        guidance = f"{guidance}\n{extra_guidance}" if guidance else extra_guidance
    if guidance:
        base_prompt = f"{base_prompt}\n\nAdditional style constraints:\n{guidance}"
    return f"{base_prompt}\n\nConversation:\n{conversation}"


def strip_html_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```html"):
        stripped = stripped[len("```html") :].lstrip()
    elif stripped.startswith("```"):
        stripped = stripped[len("```") :].lstrip()

    if stripped.endswith("```"):
        stripped = stripped[:-3].rstrip()
    return stripped


SECTION_REGENERATION_INSTRUCTIONS = (
    "You are an expert web app developer and UI designer specializing in minimalist, clean designs.\n"
    "You are iterating on a single-page website. Regenerate ONLY the section described below.\n"
    "Rules:\n"
    "- Return ONLY the replacement section as a single top-level HTML element using the same tag as the original.\n"
    "- Match the existing class names, colors, and spacing so the section blends into the rest of the page.\n"
    "- Follow the original design intent and accessibility best practices (WCAG AA contrast, visible focus states).\n"
    "- ALL images/icons must be inline SVG; no external dependencies or CDN links.\n"
    "- No explanations; code only."
)


def _refine_aspect_guidance(refine_aspect_key: str | None) -> str:
    aspect = REFINE_ASPECTS_BY_KEY.get(refine_aspect_key or "")
    if aspect is None or aspect.key == "general":
        return ""
    return aspect.guidance


def build_section_regeneration_prompt(
    current_code: str,
    section: PageSection,
    instructions: str,
    tone_key: str = DEFAULT_TONE_KEY,
    strict_minimal: bool = False,
    complexity_key: str = DEFAULT_COMPLEXITY_KEY,
    extra_guidance: str = "",
    refine_aspect_key: str | None = None,
) -> str:
    extra = "\n".join(
        part
        for part in (
            _style_guidance(tone_key, strict_minimal),
            _complexity_guidance(complexity_key),
            _refine_aspect_guidance(refine_aspect_key),
            extra_guidance,
        )
        if part
    )
    prompt = (
        SECTION_REGENERATION_INSTRUCTIONS
        + "\n\nCurrent page code:\n"
        + current_code
        + f"\n\nSection to replace (position {section.index + 1}, <{section.tag}>):\n"
        + section.html
        + f"\n\nRegeneration instructions: {instructions or 'Match the existing design.'}"
    )
    if extra:
        prompt += "\n\nStyle constraints:\n" + extra
    return prompt


def _generate_content(
    model: Any,
    genai: Any,
    prompt: str,
    temperature: float,
    max_output_tokens: int,
    analytics_file: str | None = None,
    event_meta: dict[str, str | bool | None] | None = None,
) -> str:
    meta = dict(event_meta or {})
    start = time.perf_counter()
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            ),
        )
        text = response.text
    except Exception as exc:  # noqa: BLE001 - surface any provider error as a friendly message
        record(
            GenerationEvent(
                event="generation.error",
                duration_ms=int((time.perf_counter() - start) * 1000),
                error=str(exc),
                **meta,
            ),
            analytics_file=analytics_file,
        )
        return f"API error: {exc}"
    record(
        GenerationEvent(
            event="generation.success",
            duration_ms=int((time.perf_counter() - start) * 1000),
            output_chars=len(text),
            **meta,
        ),
        analytics_file=analytics_file,
    )
    return text


def call_gemini(
    model: Any,
    genai: Any,
    messages: list[dict[str, str]],
    temperature: float,
    max_output_tokens: int,
    tone_key: str = DEFAULT_TONE_KEY,
    strict_minimal: bool = False,
    complexity_key: str = DEFAULT_COMPLEXITY_KEY,
    extra_guidance: str = "",
    analytics_file: str | None = None,
) -> str:
    prompt = build_generation_prompt(
        messages,
        tone_key=tone_key,
        strict_minimal=strict_minimal,
        complexity_key=complexity_key,
        extra_guidance=extra_guidance,
    )
    return _generate_content(
        model,
        genai,
        prompt,
        temperature,
        max_output_tokens,
        analytics_file=analytics_file,
        event_meta={
            "tone_key": tone_key,
            "complexity_key": complexity_key,
            "strict_minimal": strict_minimal,
        },
    )


def call_gemini_for_section(
    model: Any,
    genai: Any,
    current_code: str,
    section: PageSection,
    instructions: str,
    temperature: float,
    max_output_tokens: int,
    tone_key: str = DEFAULT_TONE_KEY,
    strict_minimal: bool = False,
    complexity_key: str = DEFAULT_COMPLEXITY_KEY,
    extra_guidance: str = "",
    analytics_file: str | None = None,
    refine_aspect_key: str | None = None,
) -> str:
    prompt = build_section_regeneration_prompt(
        current_code,
        section,
        instructions,
        tone_key=tone_key,
        strict_minimal=strict_minimal,
        complexity_key=complexity_key,
        extra_guidance=extra_guidance,
        refine_aspect_key=refine_aspect_key,
    )
    return _generate_content(
        model,
        genai,
        prompt,
        temperature,
        max_output_tokens,
        analytics_file=analytics_file,
        event_meta={
            "tone_key": tone_key,
            "complexity_key": complexity_key,
            "strict_minimal": strict_minimal,
        },
    )
