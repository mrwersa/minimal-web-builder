# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

A `.venv/` exists at the repo root; prefix Python commands with `.venv/bin/python -m` (CI uses the bare commands after installing into the runner).

```bash
# Backend
.venv/bin/python -m pytest -q                                    # all tests
.venv/bin/python -m pytest tests/test_runtime.py -q               # one file
.venv/bin/python -m pytest tests/test_runtime.py::test_name -q    # one test
.venv/bin/python -m coverage run -m pytest -q
.venv/bin/python -m coverage report --include="src/*,server/*" --fail-under=70
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .

# Frontend (from web/)
npm run typecheck
npm test                                 # vitest, all
npx vitest run src/store.test.ts         # one file
npx vitest run -t "substring of name"    # one test
npm run build

# Browser smoke (from web/; starts its own dev server on :4173)
npx playwright install chromium          # once
npm run test:e2e
npx playwright test -g "substring"       # one test

# Migrations
alembic upgrade head
```

Dev servers: `uvicorn server.main:app --port 8000 --reload` plus `cd web && npm run dev` (Vite on :5173 proxies `/api` to :8000). After `npm run build`, the API serves `web/dist/` at :8000 as a single process.

CI runs four required jobs — `lint` (ruff check + format), `validate` (compileall, pytest, coverage ≥70%), `frontend` (`npm audit --audit-level=high`, typecheck, test, build), and `browser-smoke` (Playwright/Chromium). Run the matching gate locally before pushing.

## Governance

Direct pushes to `main` are blocked. Work happens on a branch → PR → 1 approval + CODEOWNERS → all checks green → squash/rebase merge (linear history required). Never commit to `main` directly.

## Architecture

### Two backend layers

`src/*` is pure generation logic — provider calls, tone/complexity presets, constraints, safety policy, a11y audit, JS analysis, section extraction, export splitting. It imports no FastAPI and no database. `server/*` is the HTTP, persistence, and orchestration layer that consumes it. Keep `src/` importable standalone; new business rules belong there, new wiring belongs in `server/`.

`server/runtime.py` is the only seam that unpacks `AppConfig` into provider call arguments, and it abstracts over both Gemini and OpenRouter (`GENERATION_PROVIDER`). Services are constructed once in the `lifespan` handler in `server/main.py` and hang off `app.state`.

### The document model is the core contract

`web/src/editor/document.ts` owns `EditorDocumentV1` and is the single source of truth for the editable page. `parseEditorDocument(html)` lifts an HTML string into a structured tree; `compileDocument(doc)` renders it back. Every element carries a stable ID under the `data-mwb-id` attribute.

Three things about this file are easy to break:

1. **The compiler is deterministic by design** — attributes and CSS declarations are sorted before serialization. Round-trip and export tests depend on exact output; don't introduce ordering that varies.

2. **Compilation has two modes.** `includeEditorIds: true` (canvas and preview) emits `data-mwb-id` attributes. `includeEditorIds: false` (export) strips them and rewrites responsive selectors from `[data-mwb-id="x"]` to a `.mwb-node-x` class, injecting that class onto the affected elements. Exported HTML must contain `mwb-node-` and must *not* contain `data-mwb-id`.

3. **Parse and compile are a matched pair for CSS.** `extractDesignTokens` pulls `--mwb-*` custom properties out of `:root`, and `extractResponsiveStyles` pulls `@media (max-width: 1023px|639px)` blocks out into the structured `responsiveStyles` map — both keyed to node IDs. The extraction regexes match exactly what `compileDesignTokenCss` and `compileResponsiveCss` emit. Change the emitted format without changing the matching parser and round trips silently drop styling.

`server/documents.py` re-validates the same schema server-side: version, node-ID pattern, ID uniqueness, node count/depth/size caps, and the rule that responsive styles must reference an existing node. The node-ID regex is deliberately duplicated in TypeScript and Python — keep both in sync.

The visual editor (GrapeJS) is a *canvas adapter*, not the persistence format. `replaceCanvas()` takes body HTML back from the canvas, reparses it, and prunes responsive styles whose nodes no longer exist. Never let canvas-specific structure leak into the stored document.

### Generation flow

All three generation entry points — `/api/generate`, `/api/generate-section`, `/api/chat` — funnel through `GenerationOrchestrator` (`server/orchestrator.py`). They **return `202` with a `job_id`, not a result**: work runs on a bounded `ThreadPoolExecutor` whose size is the generation concurrency limit, and the client polls `GET /api/generation-jobs/{id}`, cancels via `POST /api/generation-jobs/{id}/cancel`, or reattaches through `GET /api/generation-jobs/active` after a reload.

Cancellation is **cooperative**: an in-flight provider call cannot be interrupted, so work receives a `CancellationToken` and calls `raise_if_cancelled()` where abandoning is still clean — in practice immediately before committing a side effect such as the conversation checkpoint. A cancel landing after the provider responded still discards the result rather than applying a change the user has moved on from. Status flows `queued → running → succeeded | failed | cancelled`, and `recover_interrupted_jobs()` settles both queued and running jobs at startup, since after a restart no worker will ever pick them up.

`/api/chat` runs a LangGraph agent (`server/agent.py`): `classify_intent` routes to `generate`/`refine`/`answer`, output passes a `validate` guardrail node (safety policy + a11y audit + inline-JS audit + a `<body>` presence check), then `apply`, `retry` (capped at `MAX_RETRIES = 2`), or `error_fallback`. Nodes are pure `(state) -> partial_state` functions, so the graph is testable without an LLM by injecting a fake client via `set_client()`.

Element-scoped AI editing (`server/editor_scope.py`) asks the model for a full document but splices only the target `data-mwb-id` subtree into the current HTML by byte offset. This is the existing step toward Phase 3's typed patches.

### Persistence and request handling

`projects → pages → revisions`, where revisions are immutable and append-only. `save_page` takes an expected version and raises `VersionConflictError` for optimistic concurrency; the frontend surfaces this as a `"conflict"` save state. Restore and checkpoint both append new revisions rather than mutating history.

Blocking provider, database, and filesystem calls must cross the async boundary through `offload()` (`server/concurrency.py`). Authenticated mutations go through `run_idempotent()` (`server/mutations.py`) so `Idempotency-Key` is honored. Rate limits are applied by the `enforce_request_controls` middleware against explicit path sets in `server/request_controls.py` — new generation or auth routes must be added to those sets.

Schema changes need an Alembic migration in `migrations/versions/`. Runtime `create_all` is deliberately limited to local SQLite; migrations are the canonical schema history.

### Frontend

**Layout** is canvas-centric (`web/src/components/layout/`): `TopBar` over a left rail (layers / project / setup), `CanvasStage` in the middle, `RightPanel` (inspector / chat) on the right. `CanvasStage` chooses between the sandboxed `Preview` iframe and the lazy-loaded `GrapeJSEditor`, and suspends editing while a generation runs so the canvas cannot fight an incoming document.

**Components** are Radix primitives styled with CVA in the shadcn/ui pattern, in `web/src/components/ui/` (lowercase filenames). Every colour resolves through a CSS variable in `index.css`, so light/dark is a token swap — never hardcode a colour in a component. `ThemeProvider` (`web/src/theme.tsx`) follows the system preference and persists an explicit override. One deliberate exception: `select.tsx` is a styled **native** `<select>`, because the inspector renders a dozen in a narrow column where native keyboard and mobile behaviour wins.

**State** is one Zustand store (`web/src/store.ts`) holding settings, editor state, projects, chat, canvas framing (`viewport`/`zoom`), and `activeJobId`. Undo/redo are stacks of whole `EditorDocumentV1` snapshots, which is *why* AI and manual edits share one history — anything that mutates the document must push a snapshot through the same path or it becomes unreversible.

Generation calls in `web/src/api.ts` hide the submit-and-poll loop: they take an optional `onJob(jobId)` callback so the store can record the job for cancellation, and throw `GenerationCancelledError` when a job ends by cancellation. The store treats that as a stop rather than a failure, matched **by name** rather than `instanceof`, because the class identity is not stable across module boundaries.

## Conventions

- `ROADMAP.md` is the source of truth for phase status and is governed by exit metrics, not feature count. Update it and the README's current-priorities block together — they have drifted before.
- No roadmap item is complete until its user-visible workflow is verified end to end; the Playwright spec in `web/e2e/builder.spec.ts` is that verification and covers the whole loop in one test.
- Generated output must stay self-contained (no external frontend dependencies at runtime). That constrains the *generated page*, not the builder app, which uses npm dependencies freely.
- Behavior changes carry proportional tests and a README update when user-facing.
