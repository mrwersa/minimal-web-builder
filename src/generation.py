from __future__ import annotations

from typing import Any, Dict, List

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


def build_generation_prompt(messages: List[Dict[str, str]]) -> str:
    conversation = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
    return f"{BASE_PROMPT}\n\nConversation:\n{conversation}"


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
) -> str:
    try:
        prompt = build_generation_prompt(messages)
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
