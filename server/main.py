"""FastAPI backend for the Minimal Web Builder React frontend.

Reuses the existing ``src/*`` modules (generation, safety, a11y, sections,
export, layout_dna, profiles, theme, constraints) as a service
layer, plus a LangGraph conversational agent (/api/chat).
"""

from __future__ import annotations

import typing
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from server.agent import run_agent
from server.agent import set_client as set_agent_client
from server.asset_routes import router as asset_router
from server.assets import (
    ReusableAssetNotFoundError,
    ReusableAssetService,
    ReusableAssetValidationError,
)
from server.auth import AuthService
from server.auth_routes import router as auth_router
from server.concurrency import offload
from server.content import DocumentValidationError
from server.database import Database
from server.project_routes import router as project_router
from server.projects import (
    ProjectNotFoundError,
    ProjectService,
    ProjectValidationError,
    VersionConflictError,
)
from server.runtime import GenerationClient, build_client, generate, regenerate_section
from src.a11y import audit_generated_html
from src.config import cors_origins_from_env
from src.constraints import (
    COLOR_LIMITS,
    SECTION_OPTIONS,
    build_constraints_prompt,
)
from src.export import split_document
from src.generation import strip_html_code_fence
from src.js_analysis import audit_inline_scripts
from src.profiles import (
    CUSTOM_PROFILE_ID,
    get_profile,
    load_profiles,
)
from src.safety import apply_output_safety_policy
from src.sections import extract_first_top_level, extract_sections, replace_section
from src.theme import (
    COLORS,
    COMPLEXITY_BY_KEY,
    REFINE_ASPECTS,
    TONE_PRESETS_BY_KEY,
    complexity_options,
    tone_options,
)
from src.validation import validate_user_prompt

REPO_ROOT = Path(__file__).resolve().parent.parent
PROFILES_DIR = REPO_ROOT / "profiles"
WEB_DIST = REPO_ROOT / "web" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI) -> typing.AsyncIterator[None]:
    app.state.client = build_client()
    app.state.database = Database.from_url(app.state.client.config.database_url)
    app.state.auth = AuthService(
        app.state.database.sessions,
        session_hours=app.state.client.config.session_hours,
    )
    app.state.projects = ProjectService(app.state.database.sessions)
    app.state.assets = ReusableAssetService(app.state.database.sessions)
    try:
        app.state.profiles = load_profiles(PROFILES_DIR)
    except (ValueError, TypeError):
        app.state.profiles = []
    try:
        yield
    finally:
        app.state.database.close()


app = FastAPI(title="Minimal Web Builder API", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(cors_origins_from_env()),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(asset_router)
app.include_router(project_router)


@app.exception_handler(ProjectNotFoundError)
async def project_not_found_handler(
    _request: Request, exc: ProjectNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ProjectValidationError)
async def project_validation_handler(
    _request: Request, exc: ProjectValidationError
) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(ReusableAssetNotFoundError)
async def reusable_asset_not_found_handler(
    _request: Request, exc: ReusableAssetNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ReusableAssetValidationError)
@app.exception_handler(DocumentValidationError)
async def content_validation_handler(
    _request: Request, exc: ValueError
) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(VersionConflictError)
async def version_conflict_handler(
    _request: Request, exc: VersionConflictError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "detail": {
                "message": "Page has a newer revision",
                "current_version": exc.current_version,
            }
        },
    )


def _client() -> GenerationClient:
    return app.state.client


def _profiles():
    return app.state.profiles


def _sanitize_output(raw: str) -> tuple[str, list[str], list[str]]:
    sanitized, safety_alerts = apply_output_safety_policy(raw)
    a11y = audit_generated_html(sanitized)
    js = audit_inline_scripts(sanitized)
    return sanitized, safety_alerts, a11y + js


class GenerateRequest(BaseModel):
    prompt: str | None = None
    tone: str = "minimal"
    complexity: str = "balanced"
    strict_minimal: bool = False
    profile: str | None = None
    current_code: str | None = None
    layout_dna_guidance: str = ""
    constraints: dict[str, Any] | None = None


class SectionRegenRequest(BaseModel):
    code: str
    section_index: int
    instructions: str = ""
    tone: str = "minimal"
    complexity: str = "balanced"
    strict_minimal: bool = False
    profile: str | None = None
    layout_dna_guidance: str = ""
    refine_aspect: str | None = None


class ExportRequest(BaseModel):
    html: str
    mode: str = "single"  # "single" | "split"


# ---- routes ----


@app.get("/api/health")
async def health() -> dict[str, Any]:
    cfg = _client().config
    return {
        "ok": True,
        "provider": cfg.provider,
        "model": cfg.openrouter_model if cfg.provider == "openrouter" else cfg.model,
        "has_key": bool(cfg.openrouter_api_key or cfg.api_key),
        "max_prompt_chars": cfg.max_prompt_chars,
    }


@app.get("/api/options")
async def options() -> dict[str, Any]:
    profiles = _profiles()
    return {
        "profiles": [
            {"id": p.id, "label": p.label, "description": p.description}
            for p in profiles
        ],
        "custom_profile_id": CUSTOM_PROFILE_ID,
        "tones": [
            {"key": k, "label": TONE_PRESETS_BY_KEY[k].label} for k in tone_options()
        ],
        "complexities": [
            {"key": k, "label": COMPLEXITY_BY_KEY[k].label}
            for k in complexity_options()
        ],
        "refine_aspects": [{"key": a.key, "label": a.label} for a in REFINE_ASPECTS],
        "sections": [{"key": s.key, "label": s.label} for s in SECTION_OPTIONS],
        "color_limits": [{"key": c.key, "label": c.label} for c in COLOR_LIMITS],
        "tokens": COLORS,
    }


def _effective_settings(req: GenerateRequest | SectionRegenRequest) -> dict[str, Any]:
    profile = get_profile(_profiles(), req.profile) if req.profile else None
    if profile:
        return {
            "tone_key": profile.tone_key,
            "complexity_key": profile.complexity_key,
            "strict_minimal": profile.strict_minimal,
            "extra_guidance": profile.extra_guidance,
        }
    return {
        "tone_key": req.tone,
        "complexity_key": req.complexity,
        "strict_minimal": req.strict_minimal,
        "extra_guidance": "",
    }


@app.post("/api/generate")
async def generate_page(req: GenerateRequest) -> JSONResponse:
    cfg = _client().config
    s = _effective_settings(req)

    if req.constraints:
        prompt = build_constraints_prompt(
            req.constraints.get("sections", []),
            req.constraints.get("color_limit", "single-accent"),
            req.constraints.get("density", s["complexity_key"]),
        )
    else:
        validated, err = validate_user_prompt(
            req.prompt or "", max_prompt_chars=cfg.max_prompt_chars
        )
        if err:
            raise HTTPException(status_code=400, detail=err)
        prompt = validated

    messages: list[dict[str, str]] = []
    if req.current_code:
        messages.append(
            {
                "role": "assistant",
                "content": f"Here is the current version of the website code:\n\n{req.current_code.strip()}",
            }
        )
    messages.append({"role": "user", "content": prompt})

    extra = s["extra_guidance"]
    if req.layout_dna_guidance:
        extra = f"{extra}\n{req.layout_dna_guidance}".strip()

    raw = await offload(
        generate,
        _client(),
        messages=messages,
        tone_key=s["tone_key"],
        strict_minimal=s["strict_minimal"],
        complexity_key=s["complexity_key"],
        extra_guidance=extra,
    )
    if raw.startswith("API error:"):
        raise HTTPException(status_code=502, detail=raw)

    sanitized, safety_alerts, notes = _sanitize_output(strip_html_code_fence(raw))
    return JSONResponse(
        {
            "html": sanitized,
            "safety_alerts": safety_alerts,
            "notes": notes,
            "settings": {
                "tone": s["tone_key"],
                "complexity": s["complexity_key"],
                "strict_minimal": s["strict_minimal"],
                "profile": req.profile,
            },
        }
    )


class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"
    current_code: str | None = None
    tone: str = "minimal"
    complexity: str = "balanced"
    strict_minimal: bool = False
    profile: str | None = None
    layout_dna_guidance: str = ""


@app.post("/api/chat")
async def chat(req: ChatRequest) -> JSONResponse:
    """Conversational agent endpoint powered by LangGraph.

    Maintains conversation memory per ``thread_id`` across turns. The agent
    classifies intent (generate / refine / answer), calls the LLM, validates
    output through safety + a11y guardrails, and returns the updated page.
    """
    cfg = _client().config
    validated, err = validate_user_prompt(
        req.message, max_prompt_chars=cfg.max_prompt_chars
    )
    if err:
        raise HTTPException(status_code=400, detail=err)

    # Wire the agent's LLM client to the app's configured client
    set_agent_client(_client())

    # Resolve effective settings (profile overrides)
    profile = get_profile(_profiles(), req.profile) if req.profile else None
    if profile:
        settings = {
            "tone": profile.tone_key,
            "complexity": profile.complexity_key,
            "strict_minimal": profile.strict_minimal,
            "extra_guidance": profile.extra_guidance,
        }
    else:
        settings = {
            "tone": req.tone,
            "complexity": req.complexity,
            "strict_minimal": req.strict_minimal,
            "extra_guidance": "",
        }
    if req.layout_dna_guidance:
        settings["extra_guidance"] = (
            f"{settings.get('extra_guidance', '')}\n{req.layout_dna_guidance}".strip()
        )

    result = await offload(
        run_agent,
        validated,
        thread_id=req.thread_id,
        current_code=req.current_code,
        settings=settings,
    )

    # Extract the assistant's response message (handle both dicts and langchain msgs)
    messages = result.get("messages", [])
    assistant_msg = {"role": "assistant", "content": "Done."}
    for m in reversed(messages):
        role = (
            getattr(m, "type", None) or m.get("role")
            if isinstance(m, dict)
            else getattr(m, "type", None)
        )
        content = (
            getattr(m, "content", None) if not isinstance(m, dict) else m.get("content")
        )
        if role in ("assistant", "ai"):
            assistant_msg = {"role": "assistant", "content": content or ""}
            break

    return JSONResponse(
        {
            "html": result.get("current_code"),
            "message": assistant_msg.get("content", ""),
            "intent": result.get("intent"),
            "validation_errors": result.get("validation_errors", []),
            "validation_notes": result.get("validation_notes", []),
            "error": result.get("error"),
        }
    )


class SectionsRequest(BaseModel):
    code: str


@app.post("/api/sections")
async def list_sections(req: SectionsRequest) -> dict[str, Any]:
    sections = extract_sections(req.code)
    return {
        "sections": [
            {"index": s.index, "tag": s.tag, "snippet": s.snippet} for s in sections
        ]
    }


@app.post("/api/generate-section")
async def generate_section(req: SectionRegenRequest) -> JSONResponse:
    s = _effective_settings(req)
    sections = extract_sections(req.code)
    if req.section_index < 0 or req.section_index >= len(sections):
        raise HTTPException(status_code=400, detail="Invalid section index")
    section = sections[req.section_index]

    extra = s["extra_guidance"]
    if req.layout_dna_guidance:
        extra = f"{extra}\n{req.layout_dna_guidance}".strip()

    raw = await offload(
        regenerate_section,
        _client(),
        current_code=req.code,
        section=section,
        instructions=req.instructions,
        tone_key=s["tone_key"],
        strict_minimal=s["strict_minimal"],
        complexity_key=s["complexity_key"],
        extra_guidance=extra,
        refine_aspect_key=req.refine_aspect,
    )
    if raw.startswith("API error:"):
        raise HTTPException(status_code=502, detail=raw)

    sanitized, safety_alerts, notes = _sanitize_output(raw)
    replacement = extract_first_top_level(strip_html_code_fence(sanitized))
    if not replacement:
        raise HTTPException(
            status_code=422, detail="Could not parse regenerated section"
        )
    updated = replace_section(req.code, section, replacement)
    return JSONResponse(
        {
            "html": updated,
            "safety_alerts": safety_alerts,
            "notes": notes,
        }
    )


# ---- export ----


@app.post("/api/export")
async def export(req: ExportRequest) -> dict[str, Any]:
    if req.mode == "split":
        split = split_document(req.html)
        return {
            "mode": "split",
            "files": {
                "index.html": split.index_html,
                "styles.css": split.styles_css,
                "app.js": split.app_js,
            },
        }
    return {"mode": "single", "files": {"index.html": req.html}}


# ---- serve built frontend in production ----


if WEB_DIST.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIST), html=True), name="web")
