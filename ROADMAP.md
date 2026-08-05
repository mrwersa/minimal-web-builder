# Product Roadmap

This roadmap keeps the project a minimal web builder while raising quality, reliability, and extensibility.

Legend: ✅ done · 🔄 in progress · ⬜ not started

## North Star

Build the most reliable minimal web builder for self-contained, beautiful, responsive pages generated from natural language.

## Current State (v1)

- Modular architecture: `app.py` orchestrates UI; `src/` holds config, generation, rendering, state, validation, safety, theme, and a11y.
- Gemini prompt-to-HTML generation with sandboxed in-app preview.
- Session state lifecycle, input validation, output safety policy, and deterministic tests.
- Generation controls (tone presets, strict minimal mode, complexity slider) shipped as Phase 2 groundwork.
- Section-level regeneration: pick any top-level section and regenerate just that block in place.
- App UI styled from the shared design-token palette; accessibility guardrails in the prompt plus a static audit of generated HTML (incl. visible focus styles).
- Export modes: single `index.html` download or split export (`index.html` + `styles.css` + `app.js`).
- Generation profiles: `profiles/*.json` bundle tone, complexity, strict mode, and extra prompt guidance; a "Custom" option restores manual controls.
- Template memory: save the current page to a local `templates/` dir and seed a fresh conversation from any saved template.
- Observability: structured JSON events (latency, output size, failures) via the `minimal_web_builder` logger, with an opt-in local JSONL analytics hook (`ANALYTICS_FILE`).
- Refine mode: regenerate a section focused on a single aspect (spacing, typography, layout, or color).
- Constraint-first generation: build a page from required sections, a color limit, and density; the model fills in the details.
- Safety rails: empty inline `<script>` blocks are stripped by the output policy; inline scripts are audited for complexity and unsafe calls (`eval`, `new Function`, `document.write`).
- ~95% coverage on core non-UI modules; CI gates on lint + syntax + tests + coverage.

## Phase 1: Foundation ✅ (complete)

Goals:
- Stabilize runtime behavior and remove obvious implementation risks.
- Establish baseline testing and CI confidence.

Work items (all complete):
- ✅ Split app.py into modules:
  - ✅ src/config.py for env and model settings.
  - ✅ src/generation.py for Gemini adapter and prompt policies.
  - ✅ src/rendering.py for preview/code rendering helpers.
  - ✅ src/state.py for session state operations.
- ✅ Add input/output validation:
  - ✅ Guard against empty prompts.
  - ✅ Normalize code-fence stripping.
  - ✅ Add max prompt length and friendly errors.
- ✅ Harden generated output handling:
  - ✅ Keep iframe sandboxing strategy explicit.
  - ✅ Add a strict policy for disallowed tags/scripts where needed.
- ✅ Add tests:
  - ✅ Unit tests for prompt assembly and code extraction.
  - ✅ State transition tests for generation lifecycle.
  - ✅ Regression tests for API error handling.
- ✅ Add CI quality gates (already bootstrapped):
  - ✅ Lint, syntax check, tests on PRs.

Exit criteria (all met):
- ✅ No blocking lint/syntax issues.
- ✅ >= 70% coverage on core non-UI modules (95%).
- ✅ Stable PR checks and deterministic local runs.

## Phase 2: Usability + Design System ✅ (complete)

Goals:
- Improve design quality without losing minimalism.
- Increase user trust and control.

Work items:
- ✅ Introduce a small design token layer:
  - ✅ Typography scale, spacing scale, neutral + accent palette.
  - ✅ Shared UI constants for Streamlit theme consistency.
  - ✅ App CSS/Streamlit theme consumes the tokens via a single `build_app_styles()` entry point.
- ✅ Better generation controls:
  - ✅ Tone presets (minimal, editorial, product, portfolio, landing).
  - ✅ Optional strict minimal mode (fewer decorations).
  - ✅ Output complexity slider (compact / balanced / detailed).
- ✅ Prompt iteration UX:
  - ✅ Keep instruction history (last 8 user instructions are preserved across turns).
  - ✅ Regenerate section-level variants (hero, cards, footer) via an in-app section picker.
- ✅ Accessibility checks:
  - ✅ Contrast guardrails in generation prompt (WCAG AA baseline).
  - ✅ Keyboard navigation/structure audit of generated templates (alt, labels, h1, tabindex).
  - ✅ Visual focus-state verification in generated templates (:focus / :focus-visible detection).

Exit criteria:
- ✅ Reduced failed-generation rate (validation + friendly errors + safety policy cut failure modes; formal measurement deferred to Phase 3 observability).
- ✅ Faster time-to-usable-result for first prompt (single-prompt flow + presets reduce iterations; not yet benchmarked).
- ✅ Documented visual system and generation presets (design tokens consumed across the app; presets documented).

## Phase 3: Productization ✅ (complete)

Goals:
- Make the tool production-usable for repeated workflows.
- Keep architecture minimal but extensible.

Work items:
- ✅ Project export modes:
  - ✅ Single HTML export (restored; `index.html` download in the Code tab).
  - ✅ Optional split export (index.html, styles.css, app.js) via `src/export.py`.
- ✅ Configurable generation profiles:
  - ✅ profiles/minimal.json (strict default).
  - ✅ profiles/startup-landing.json, profiles/portfolio.json.
  - ✅ Profile selector in the sidebar; individual controls disabled while a profile is active.
- ✅ Template memory:
  - ✅ Save successful outputs as reusable local templates (`templates/`, git-ignored).
  - ✅ Let users seed new generations from a prior build (fresh conversation with the template as the baseline).
- ✅ Observability:
  - ✅ Structured logs around API latency and failures (`generation.success` / `generation.error` JSON events).
  - ✅ Lightweight analytics hooks (local-only, opt-in via `ANALYTICS_FILE` JSONL).

Exit criteria:
- ✅ Repeatable workflow for build -> revise -> export (chat build, section refine, profiles, template seed, single/split export).
- ✅ Strong reliability for long editing sessions (instruction history, stable session state, structured error/failure logging).

## Phase 4: Advanced Minimal Builder Ideas

Potential additions that preserve minimalism:
- ✅ Constraint-first generation:
  - ✅ Build a site from constraints only (required sections, color limit, density); the model fills in the details.
- Layout DNA:
  - Extract reusable layout grammar from accepted generations.
- ✅ Refine mode:
  - ✅ Aspect-focused section updates ("Improve only spacing / typography / layout / color") without major rewrites.
- ✅ Safety rails:
  - ✅ Validate generated JS complexity (statement/line heuristics) and flag unsafe calls.
  - ✅ Forbid unnecessary scripts (empty inline `<script>` blocks stripped by the output policy).

## Engineering Principles

- Minimal surface area, maximal clarity.
- Keep dependencies low and explicit.
- Prefer pure functions for generation/data paths.
- Every behavior change should include tests and docs updates.
