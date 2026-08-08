# Product Roadmap

Legend: ✅ done · 🔄 in progress · ⬜ planned

## Product focus

Build the fastest, safest AI-assisted builder for polished, responsive marketing
websites. The product should combine natural-language generation with precise direct
editing, durable revision history, and a trustworthy path from idea to published site.

The product is intentionally not a general-purpose application IDE. Self-contained,
portable HTML remains an important output, but the editable source of truth will move
from one mutable HTML string to a structured page document with stable element IDs.

## Architecture direction

- Keep a modular monolith: React client, FastAPI API, shared Python service modules.
- Add PostgreSQL for users, projects, pages, revisions, conversations, and jobs.
- Run provider calls, validation, screenshots, and publishing in durable workers.
- Store assets and published artifacts in object storage behind a CDN.
- Introduce a structured document model compiled to self-contained HTML.
- Make AI return typed document patches instead of rewriting the entire page.
- Keep the visual editor behind a canvas adapter; it must not become the persistence format.
- Avoid microservices, real-time multiplayer, and plugins until the core single-user loop is excellent.

## Phase 0: Product truth and reliability 🔄

Goal: make every documented workflow reliable before adding platform infrastructure.

- ✅ Allow constraint-only generation without a redundant prompt.
- ✅ Load saved templates into a fresh conversation, not only save/delete them.
- ✅ Put generation, chat, section regeneration, templates, and visual edits into one undo history.
- ✅ Debounce visual-editor updates and preserve metadata, styles, attributes, and scripts.
- ✅ Remove the obsolete iframe editor shim and pause visual editing during generation.
- ✅ Lazy-load the visual editor.
- ✅ Add frontend type-check, test, and build gates to CI.
- ✅ Add regression tests for constraint generation, template loading, revision history,
  and editor document round trips.
- ✅ Replace the legacy Streamlit-era roadmap and correct the user documentation.
- ⬜ Add browser-level smoke tests for generate → edit → undo → export.
- ⬜ Add explicit, actionable errors for failed sidebar data loads.

Exit metrics:

- Zero known broken documented workflows.
- All frontend and backend checks required on pull requests.
- Visual editing does not silently remove page metadata or JavaScript.
- Every meaningful document mutation is reversible.

## Phase 1: Projects and durable revisions 🔄

Goal: users can safely leave and return to their work.

- ✅ Add SQLAlchemy persistence with SQLite development and PostgreSQL production URLs.
- ✅ Add durable `projects`, `pages`, and immutable `revisions` records.
- ✅ Add project create/open controls backed by the API.
- ✅ Add debounced autosave with optimistic concurrency and visible conflict detection.
- ✅ Add revision history and restore-as-new-revision.
- ⬜ Add `users`, `conversations`, and `generation_jobs` persistence.
- ⬜ Add database migrations before production deployment.
- ⬜ Expand the project browser with rename, duplicate, archive, and search.
- ⬜ Add named checkpoints and duplicate-from-revision.
- Move templates and Layout DNA into owner-scoped records.
- Add authentication, project authorization, rate limits, and audit events.
- Unify `/generate`, `/generate-section`, and `/chat` behind one generation orchestrator.
- Persist conversation checkpoints instead of using process-local memory.

Exit metrics:

- Browser refresh and server restart do not lose work.
- Every document change is recoverable.
- No cross-user access to projects or reusable assets.
- Mutating API operations are idempotent where appropriate.

## Phase 2: A trustworthy visual editor ⬜

Goal: common changes are faster by direct manipulation than by prompting.

- Introduce a versioned structured document schema and deterministic HTML compiler.
- Add stable selection, breadcrumbs, layers, element tree, and property inspector.
- Add desktop, tablet, and mobile breakpoints with viewport presets and zoom.
- Add drag/reorder, spacing, typography, color, layout, visibility, and link controls.
- Add global design tokens for color, type, spacing, radius, and container width.
- Add element-scoped AI commands using stable node IDs.
- Add accessible keyboard navigation, shortcuts, and a command palette.
- Preserve custom CSS and JavaScript through explicit advanced escape hatches.

Exit metrics:

- No document loss after repeated edit/preview/export round trips.
- Undo/redo works across both AI and manual edits.
- A typical direct edit takes fewer than three interactions.
- Responsive problems can be fixed without regenerating the page.

## Phase 3: Reliable AI generation ⬜

Goal: generation is observable, cancellable, measurable, and structurally safe.

- Replace full-document rewrites with typed insert/update/move/delete patches.
- Stream job progress and support cancellation, retry, and recovery after navigation.
- Add durable workers, provider timeouts, fallback policy, and concurrency limits.
- Add visual-quality, responsiveness, accessibility, and instruction-following fixtures.
- Add screenshot and visual-regression checks for representative pages.
- Track latency, token usage, cost, acceptance, undo-after-generation, and failures.
- Add structured content and asset inputs instead of relying only on prompt inference.

Exit metrics:

- At least 95% of generations are technically valid.
- Fewer than 2% of generation jobs fail or become orphaned.
- Provider-specific P95 latency targets are measured and enforced.
- At least 70% of first results are accepted or refined rather than discarded.

## Phase 4: Complete website workflow ⬜

Goal: users can build and publish a complete professional website without leaving the product.

- Add multi-page sites, shared navigation, shared sections, and page settings.
- Add asset upload, optimization, alt text, and an owner-scoped media library.
- Add SEO metadata, sitemap, robots rules, and social preview cards.
- Add forms with spam protection, submissions, and notifications.
- Add preview URLs, one-click publish, custom domains, SSL, rollback, and unpublish.
- Add a pre-publish check for links, accessibility, responsive layout, SEO, and performance.
- Add ZIP and GitHub export as secondary delivery paths.

Exit metrics:

- A project can go from prompt to a live domain entirely in-product.
- Any published revision can be rolled back safely.
- Published pages meet defined accessibility and performance budgets.

## Phase 5: Collaboration and scale ⬜

Goal: add team and operational capabilities only after the single-user workflow has traction.

- Add invitations, roles, comments, presence, and approval workflows.
- Add real-time CRDT/OT editing only when usage demonstrates demand.
- Add queue autoscaling, backups, disaster recovery, quotas, billing, and support tooling.
- Add an extension/plugin API only after the document schema is stable.

## Product metrics

The roadmap is governed by outcomes rather than feature count:

- Time from first prompt to accepted page.
- First-generation acceptance and refinement rate.
- Undo/revert rate after AI and visual-editor changes.
- Generation success, cancellation, and latency percentiles.
- Autosave recovery and revision-restore success.
- Publish completion and rollback success.
- Accessibility, responsive-layout, and performance pass rates.

## Engineering principles

- One canonical document and one revision history.
- Stable contracts between canvas, document model, compiler, and generation system.
- Safe, reversible edits before clever automation.
- Modular monolith before microservices.
- Every behavior change includes proportional tests and documentation.
- No roadmap item is complete until its user-visible workflow is verified.
