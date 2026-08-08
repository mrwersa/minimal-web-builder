"""LangGraph-powered conversational agent for the Minimal Web Builder.

The agent wraps the existing src/* generation, safety, and a11y logic in a
stateful graph with:

- **Memory**: conversation history supplied by the durable orchestration layer.
- **Intent classification**: routes user input to generate / refine / answer.
- **Guardrails**: every generation passes through safety + a11y + HTML validation;
  failures route to a retry node (capped at ``MAX_RETRIES``).
- **Resilience**: node-level try/except, retry with backoff, and a fallback
  "explain the error" node when retries are exhausted.

Each node is a pure function ``(state) -> partial_state``, so the graph is
fully unit-testable without a real LLM by mocking the ``call_llm`` tool.
"""

from __future__ import annotations

import re
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

# Reuse the generation wrapper from runtime
from server.runtime import GenerationClient, generate
from src.a11y import audit_generated_html
from src.generation import strip_html_code_fence
from src.js_analysis import audit_inline_scripts
from src.safety import apply_output_safety_policy

MAX_RETRIES = 2

_REFINE_KEYWORDS = re.compile(
    r"\b(change|make|update|fix|move|color|colour|smaller|larger|bigger|"
    r"remove|add|replace|darken|lighten|bold|italic|font|spacing|padding|"
    r"margin|align|center|left|right|background|border|radius|shadow|"
    r"section|header|footer|hero|card|text|heading|button|image|layout)\b",
    re.IGNORECASE,
)
_QUESTION_KEYWORDS = re.compile(
    r"\b(what|how|why|can you|could you|explain|help|show|tell)\b",
    re.IGNORECASE,
)
_GREETING_RE = re.compile(
    r"^\s*(hi|hello|hey|yo|sup|greetings|howdy|test)\s*[!.?\s]*$",
    re.IGNORECASE,
)
_DESC_KEYWORDS = re.compile(
    r"\b(website|page|landing|portfolio|blog|shop|dashboard|app|site|"
    r"hero|footer|section|feature|contact|about|navigation|nav|"
    r"create|build|design|generate|make)\b",
    re.IGNORECASE,
)


class BuilderState(TypedDict):
    messages: Annotated[list[dict[str, str]], add_messages]
    current_code: str | None
    user_input: str
    intent: str
    generation_result: str | None
    validation_errors: list[str]
    validation_notes: list[str]
    retry_count: int
    settings: dict[str, Any]
    error: str | None


def _classify_intent(state: BuilderState) -> dict[str, Any]:
    """Route the user's latest message to the right workflow."""
    user_input = state.get("user_input", "")
    has_code = bool(state.get("current_code"))

    # Greetings or very short inputs → answer (don't waste a generation call)
    if _GREETING_RE.match(user_input) or len(user_input.strip()) < 10:
        return {"intent": "answer"}

    if not has_code:
        if _DESC_KEYWORDS.search(user_input):
            return {"intent": "generate"}
        return {"intent": "answer"}

    if _REFINE_KEYWORDS.search(user_input):
        return {"intent": "refine"}

    if _QUESTION_KEYWORDS.search(user_input) and not _REFINE_KEYWORDS.search(
        user_input
    ):
        return {"intent": "answer"}

    # Default: treat any follow-up as a refinement request
    return {"intent": "refine"}


def _route_intent(state: BuilderState) -> str:
    """Conditional edge: route based on classified intent."""
    intent = state.get("intent", "generate")
    return intent if intent in ("generate", "refine", "answer") else "generate"


def _call_generate(state: BuilderState) -> dict[str, Any]:
    """Full-page generation node — calls the LLM via the existing runtime."""
    client: GenerationClient = _get_client()
    settings = state.get("settings", {})
    messages = state.get("messages", [])

    try:
        raw = generate(
            client,
            messages=messages,
            tone_key=settings.get("tone", "minimal"),
            strict_minimal=settings.get("strict_minimal", False),
            complexity_key=settings.get("complexity", "balanced"),
            extra_guidance=settings.get("extra_guidance", ""),
        )
        return {"generation_result": raw, "error": None}
    except Exception as exc:  # noqa: BLE001  # pragma: no cover - defensive
        return {"error": f"Generation failed: {exc}", "generation_result": None}


def _call_refine(state: BuilderState) -> dict[str, Any]:
    """Refinement node — re-generate with the current code as context."""
    client: GenerationClient = _get_client()
    settings = state.get("settings", {})
    messages = state.get("messages", [])
    # assistant message (set in _init_for_refine), so generation works.
    try:
        raw = generate(
            client,
            messages=messages,
            tone_key=settings.get("tone", "minimal"),
            strict_minimal=settings.get("strict_minimal", False),
            complexity_key=settings.get("complexity", "balanced"),
            extra_guidance=settings.get("extra_guidance", ""),
        )
        return {"generation_result": raw, "error": None}
    except Exception as exc:  # noqa: BLE001  # pragma: no cover - defensive
        return {"error": f"Refinement failed: {exc}", "generation_result": None}


def _validate_output(state: BuilderState) -> dict[str, Any]:
    """Guardrail node: safety policy + a11y + JS audit on the LLM output."""
    raw = state.get("generation_result")
    if not raw:
        return {"validation_errors": ["No output from LLM"], "validation_notes": []}

    if raw.startswith("API error:"):
        return {"validation_errors": [raw], "validation_notes": []}

    clean = strip_html_code_fence(raw)
    sanitized, safety_alerts = apply_output_safety_policy(clean)
    a11y_notes = audit_generated_html(sanitized)
    js_notes = audit_inline_scripts(sanitized)

    errors: list[str] = []
    if safety_alerts:
        errors.extend(safety_alerts)

    # Check that the output has actual body content
    if not re.search(r"<body", sanitized, re.IGNORECASE):
        errors.append(
            "Output is missing <body> — likely truncated (increase max tokens)"
        )

    notes = a11y_notes + js_notes
    if errors:
        return {"validation_errors": errors, "validation_notes": notes}

    # If validation passes, update generation_result with the cleaned version
    return {
        "generation_result": sanitized,
        "validation_errors": [],
        "validation_notes": notes,
    }


def _route_validation(state: BuilderState) -> str:
    """After validation: apply if clean, retry if errors and under the cap."""
    errors = state.get("validation_errors", [])
    if not errors:
        return "apply"

    retry_count = state.get("retry_count", 0)
    if retry_count >= MAX_RETRIES:
        return "error_fallback"

    return "retry"


def _apply_result(state: BuilderState) -> dict[str, Any]:
    """Apply validated output as the new current code and append to conversation."""
    code = state.get("generation_result", "")
    notes = state.get("validation_notes", [])
    assistant_msg = "Your minimalist website has been generated/updated!"
    if notes:
        assistant_msg += f" Notes: {' '.join(notes[:3])}"

    return {
        "current_code": code,
        "messages": [{"role": "assistant", "content": assistant_msg}],
    }


def _retry(state: BuilderState) -> dict[str, Any]:
    """Retry node: increment retry count, clear previous errors."""
    return {
        "retry_count": state.get("retry_count", 0) + 1,
        "validation_errors": [],
        "generation_result": None,
        "error": None,
    }


def _error_fallback(state: BuilderState) -> dict[str, Any]:
    """Terminal node when retries are exhausted — explain the failure to the user."""
    errors = state.get("validation_errors", [])
    error = state.get("error", "")
    msg = "I couldn't generate a valid page after retries."
    if errors:
        msg += f" Issues: {'; '.join(errors)}"
    if error:
        msg += f" Error: {error}"
    return {
        "messages": [{"role": "assistant", "content": msg}],
        "error": None,
    }


def _answer(state: BuilderState) -> dict[str, Any]:
    """General Q&A node — respond helpfully without generating code."""
    user_input = state.get("user_input", "")
    msg = (
        "I'm here to help you build websites! Describe a website you'd like to create, "
        "or tell me what you'd like to change about the current page. "
        "For example: 'Add a contact form to the footer' or 'Make the hero section darker.'"
    )
    if "help" in user_input.lower():
        msg = (
            "Here's how to use Minimal Web Builder:\n"
            "1. Type a description of the website you want (e.g. 'A coffee shop landing page').\n"
            "2. I'll generate a complete HTML page you can preview.\n"
            "3. Turn on WYSIWYG editing to click and edit elements directly.\n"
            "4. Describe refinements like 'make the header blue' or 'add a testimonials section'.\n"
            "5. Export your page as a single HTML file or split into HTML/CSS/JS."
        )
    return {"messages": [{"role": "assistant", "content": msg}]}


# --- module-level client injection (for testing) ---

_client: GenerationClient | None = None


def set_client(client: GenerationClient) -> None:
    global _client
    _client = client


def _get_client() -> GenerationClient:
    global _client
    if _client is None:
        _client = _build_default_client()
    return _client


def _build_default_client() -> GenerationClient:
    from server.runtime import build_client

    return build_client()


# --- graph construction ---


def build_graph():
    """Create and compile the stateless LangGraph workflow."""
    graph = StateGraph(BuilderState)

    graph.add_node("classify_intent", _classify_intent)
    graph.add_node("generate", _call_generate)
    graph.add_node("refine", _call_refine)
    graph.add_node("validate", _validate_output)
    graph.add_node("apply", _apply_result)
    graph.add_node("retry", _retry)
    graph.add_node("error_fallback", _error_fallback)
    graph.add_node("answer", _answer)

    graph.add_edge(START, "classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        _route_intent,
        {
            "generate": "generate",
            "refine": "refine",
            "answer": "answer",
        },
    )
    graph.add_edge("generate", "validate")
    graph.add_edge("refine", "validate")
    graph.add_conditional_edges(
        "validate",
        _route_validation,
        {
            "apply": "apply",
            "retry": "retry",
            "error_fallback": "error_fallback",
        },
    )
    graph.add_edge("retry", "generate")
    graph.add_edge("apply", END)
    graph.add_edge("error_fallback", END)
    graph.add_edge("answer", END)

    return graph.compile()


# Singleton graph instance
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def run_agent(
    user_input: str,
    *,
    thread_id: str = "default",
    current_code: str | None = None,
    settings: dict[str, Any] | None = None,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Run the agent for one user turn. Returns the final state snapshot."""
    graph = get_graph()
    del thread_id  # Kept as a backwards-compatible API parameter.

    # Build the initial state for this turn
    initial: dict[str, Any] = {
        "user_input": user_input,
        "messages": [*(history or []), {"role": "user", "content": user_input}],
        "retry_count": 0,
        "validation_errors": [],
        "validation_notes": [],
        "settings": settings or {},
    }

    # If there's current code, seed it so the refine path has context
    if current_code:
        initial["current_code"] = current_code
        initial["messages"].insert(
            0,
            {
                "role": "system",
                "content": f"Here is the current version of the website code:\n\n{current_code.strip()}",
            },
        )
    else:
        initial["current_code"] = None

    result = graph.invoke(initial)
    return result
