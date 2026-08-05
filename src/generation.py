from __future__ import annotations

from typing import Any, Dict, List

from src.theme import DEFAULT_TONE_KEY, STRICT_MINIMAL_GUIDANCE, TONE_PRESETS_BY_KEY

BASE_PROMPT = (
    "You are an expert web app developer and UI designer specializing in minimalist, clean designs.\n"
    "Your task: Generate a beautiful, modern, and minimalistic single-page web app using only HTML, CSS, and minimal JavaScript.\n"
    "Requirements:\n"
    "- Create a MINIMALIST design with clean typography, ample whitespace, and subtle effects\n"
    "- Use best practices for accessibility, responsiveness, and performance\n"
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
    guidance: List[str] = []
    preset = TONE_PRESETS_BY_KEY.get(tone_key)
    if preset is not None:
        guidance.append(f"Style direction: {preset.style_guidance}")
    if strict_minimal:
        guidance.append(STRICT_MINIMAL_GUIDANCE)
    return "\n".join(guidance)


def build_generation_prompt(
    messages: List[Dict[str, str]],
    tone_key: str = DEFAULT_TONE_KEY,
    strict_minimal: bool = False,
) -> str:
    conversation = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
    base_prompt = BASE_PROMPT
    guidance = _style_guidance(tone_key, strict_minimal)
    if guidance:
        base_prompt = f"{base_prompt}\n\nAdditional style constraints:\n{guidance}"
    return f"{base_prompt}\n\nConversation:\n{conversation}"


def strip_html_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```html"):
        stripped = stripped[len("```html"):].lstrip()
    elif stripped.startswith("```"):
        stripped = stripped[len("```"):].lstrip()

    if stripped.endswith("```"):
        stripped = stripped[:-3].rstrip()
    return stripped


def call_gemini(
    model: Any,
    genai: Any,
    messages: List[Dict[str, str]],
    temperature: float,
    max_output_tokens: int,
    tone_key: str = DEFAULT_TONE_KEY,
    strict_minimal: bool = False,
) -> str:
    try:
        prompt = build_generation_prompt(
            messages,
            tone_key=tone_key,
            strict_minimal=strict_minimal,
        )
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            ),
        )
        return response.text
    except Exception as exc:
        return f"API error: {exc}"
