from __future__ import annotations

import json
import random
import re
import time
import urllib.error
import urllib.request
from typing import Any

from src.config import DEFAULT_OPENROUTER_BASE_URL, OPENROUTER_PROVIDER
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

_LANGUAGE_FENCE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+#.-]*$")

DEFAULT_GENERATION_TIMEOUT_SECONDS = 120
#: Ceiling on one whole call including retries. ``timeout_seconds`` bounds a
#: single attempt, so without this a hung provider multiplies straight through
#: the attempt count while holding a concurrency slot.
DEFAULT_GENERATION_TOTAL_TIMEOUT_SECONDS = 300
#: Attempts default to 1 so importing this module changes nothing on its own;
#: the server passes its configured value from AppConfig.
DEFAULT_GENERATION_MAX_ATTEMPTS = 1
DEFAULT_RETRY_BACKOFF_SECONDS = 0.5
MAX_RETRY_BACKOFF_SECONDS = 30.0

#: Status codes that cannot succeed on a retry: bad request, rejected or unpaid
#: credentials, unknown model, wrong base URL.
_PERMANENT_STATUS_CODES = frozenset({400, 401, 402, 403, 404, 405, 413, 422})

#: Fallback classification for providers that raise without a status code. The
#: status codes are word-bounded so an unrelated number ("failed after 4013ms")
#: is not mistaken for an auth failure and denied its retries.
_PERMANENT_ERROR_RE = re.compile(
    r"\b(?:401|403)\b"
    r"|unauthorized"
    r"|forbidden"
    r"|invalid[ _-]?api[ _-]?key"
    r"|api[ _-]?key[ _-]?(?:not[ _-]?valid|invalid)"
    # Gemini raises this from `response.text` when it blocks a candidate. The
    # same prompt is blocked every time, so retrying only re-bills the tokens.
    r"|finish_reason"
    r"|requires the response to contain a valid",
    re.IGNORECASE,
)

#: Indirections so tests can control timing without patching the stdlib globally.
_sleep = time.sleep
_jitter = random.uniform


class ProviderError(RuntimeError):
    """A generation provider call failed.

    Raised internally so the retry loop can see failures; the public
    ``call_gemini`` functions still return an ``API error:`` string.
    """

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        if status_code is not None:
            # A real status beats guessing from prose, which can match text the
            # provider echoed back from the user's own prompt.
            self.retryable = status_code not in _PERMANENT_STATUS_CODES
        else:
            self.retryable = _PERMANENT_ERROR_RE.search(message) is None


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
    if stripped.startswith("```"):
        stripped = stripped[len("```") :].lstrip()
        first_line, sep, rest = stripped.partition("\n")
        if sep and _LANGUAGE_FENCE_RE.fullmatch(first_line):
            stripped = rest

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
) -> str:
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            ),
        )
        return response.text
    except Exception as exc:
        raise ProviderError(str(exc)) from exc


def _generate_content_openrouter(
    prompt: str,
    temperature: float,
    max_output_tokens: int,
    *,
    api_key: str,
    model: str,
    base_url: str = DEFAULT_OPENROUTER_BASE_URL,
    timeout_seconds: int = DEFAULT_GENERATION_TIMEOUT_SECONDS,
) -> str:
    """Generate via OpenRouter's OpenAI-compatible chat completions endpoint."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_output_tokens,
    }
    request = urllib.request.Request(
        url=f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as exc:
        raise ProviderError(
            f"HTTP Error {exc.code}: {exc.reason}", status_code=exc.code
        ) from exc
    except Exception as exc:
        raise ProviderError(str(exc)) from exc


def _backoff_delay(base_seconds: float, attempt: int) -> float:
    """Exponential backoff with equal jitter, capped.

    The jitter matters under a provider-wide incident: without it every queued
    generation retries on the same schedule and lands as a synchronized burst on
    a provider that is trying to recover.
    """
    capped = min(base_seconds * (2 ** (attempt - 1)), MAX_RETRY_BACKOFF_SECONDS)
    return capped / 2 + _jitter(0, capped / 2)


def _invoke_provider(
    provider: str,
    prompt: str,
    temperature: float,
    max_output_tokens: int,
    *,
    model: Any,
    genai: Any,
    api_key: str,
    base_url: str,
    timeout_seconds: int,
) -> str:
    if provider == OPENROUTER_PROVIDER:
        return _generate_content_openrouter(
            prompt,
            temperature,
            max_output_tokens,
            api_key=api_key,
            model=str(model),
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )
    return _generate_content(model, genai, prompt, temperature, max_output_tokens)


def _generate(
    provider: str,
    prompt: str,
    temperature: float,
    max_output_tokens: int,
    *,
    model: Any,
    genai: Any,
    api_key: str,
    base_url: str,
    analytics_file: str | None,
    event_meta: dict[str, str | bool | None] | None,
    timeout_seconds: int = DEFAULT_GENERATION_TIMEOUT_SECONDS,
    max_attempts: int = DEFAULT_GENERATION_MAX_ATTEMPTS,
    retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS,
    total_timeout_seconds: int = DEFAULT_GENERATION_TOTAL_TIMEOUT_SECONDS,
) -> str:
    """Call the provider, retrying transient failures with exponential backoff.

    Retries that are not going to fit inside ``total_timeout_seconds`` are not
    started: ``timeout_seconds`` bounds one attempt, and without an overall
    deadline a hung provider would multiply straight through the attempt count
    while holding a concurrency slot.

    Non-final failures are recorded as ``generation.retry`` so that counting
    ``generation.success`` against ``generation.error`` still yields the rate of
    generations that failed, not the rate of attempts that failed.
    """
    meta = dict(event_meta or {})
    attempts = max(1, max_attempts)
    deadline = time.monotonic() + max(0, total_timeout_seconds)
    last_error = "generation did not run"
    for attempt in range(1, attempts + 1):
        start = time.perf_counter()
        try:
            text = _invoke_provider(
                provider,
                prompt,
                temperature,
                max_output_tokens,
                model=model,
                genai=genai,
                api_key=api_key,
                base_url=base_url,
                timeout_seconds=timeout_seconds,
            )
        except ProviderError as exc:
            last_error = str(exc)
            backoff = _backoff_delay(retry_backoff_seconds, attempt)
            give_up = (
                not exc.retryable
                or attempt == attempts
                or time.monotonic() + backoff >= deadline
            )
            record(
                GenerationEvent(
                    event="generation.error" if give_up else "generation.retry",
                    duration_ms=int((time.perf_counter() - start) * 1000),
                    error=last_error,
                    attempt=attempt,
                    **meta,
                ),
                analytics_file=analytics_file,
            )
            if give_up:
                break
            _sleep(backoff)
            continue
        record(
            GenerationEvent(
                event="generation.success",
                duration_ms=int((time.perf_counter() - start) * 1000),
                output_chars=len(text),
                attempt=attempt,
                **meta,
            ),
            analytics_file=analytics_file,
        )
        return text
    return f"API error: {last_error}"


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
    *,
    provider: str = "gemini",
    api_key: str = "",
    base_url: str = DEFAULT_OPENROUTER_BASE_URL,
    timeout_seconds: int = DEFAULT_GENERATION_TIMEOUT_SECONDS,
    max_attempts: int = DEFAULT_GENERATION_MAX_ATTEMPTS,
    retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS,
    total_timeout_seconds: int = DEFAULT_GENERATION_TOTAL_TIMEOUT_SECONDS,
) -> str:
    prompt = build_generation_prompt(
        messages,
        tone_key=tone_key,
        strict_minimal=strict_minimal,
        complexity_key=complexity_key,
        extra_guidance=extra_guidance,
    )
    return _generate(
        provider,
        prompt,
        temperature,
        max_output_tokens,
        model=model,
        genai=genai,
        api_key=api_key,
        base_url=base_url,
        analytics_file=analytics_file,
        timeout_seconds=timeout_seconds,
        max_attempts=max_attempts,
        retry_backoff_seconds=retry_backoff_seconds,
        total_timeout_seconds=total_timeout_seconds,
        event_meta={
            "tone_key": tone_key,
            "complexity_key": complexity_key,
            "strict_minimal": strict_minimal,
            "provider": provider,
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
    *,
    provider: str = "gemini",
    api_key: str = "",
    base_url: str = DEFAULT_OPENROUTER_BASE_URL,
    timeout_seconds: int = DEFAULT_GENERATION_TIMEOUT_SECONDS,
    max_attempts: int = DEFAULT_GENERATION_MAX_ATTEMPTS,
    retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS,
    total_timeout_seconds: int = DEFAULT_GENERATION_TOTAL_TIMEOUT_SECONDS,
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
    return _generate(
        provider,
        prompt,
        temperature,
        max_output_tokens,
        model=model,
        genai=genai,
        api_key=api_key,
        base_url=base_url,
        analytics_file=analytics_file,
        timeout_seconds=timeout_seconds,
        max_attempts=max_attempts,
        retry_backoff_seconds=retry_backoff_seconds,
        total_timeout_seconds=total_timeout_seconds,
        event_meta={
            "tone_key": tone_key,
            "complexity_key": complexity_key,
            "strict_minimal": strict_minimal,
            "provider": provider,
        },
    )
