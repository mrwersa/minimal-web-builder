# Product Roadmap

This roadmap keeps the project a minimal web builder while raising quality, reliability, and extensibility.

Legend: ✅ done · 🔄 in progress · ⬜ not started

## North Star

Build the most reliable minimal web builder for self-contained, beautiful, responsive pages generated from natural language.

## Current State (v1)

- Modular architecture: `app.py` orchestrates UI; `src/` holds config, generation, rendering, state, validation, safety, and theme.
- Gemini prompt-to-HTML generation with sandboxed in-app preview.
- Session state lifecycle, input validation, output safety policy, and deterministic tests.
- Generation controls (tone presets + strict minimal mode) shipped as Phase 2 groundwork.
- ~95% coverage on core non-UI modules; CI gates on lint + syntax + tests.

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

## Phase 2: Usability + Design System (in progress)

Goals:
- Improve design quality without losing minimalism.
- Increase user trust and control.

Work items:
- ✅ Introduce a small design token layer:
  - ✅ Typography scale, spacing scale, neutral + accent palette.
  - ✅ Shared UI constants for Streamlit theme consistency.
  - ⬜ Consume tokens in the app CSS/Streamlit theme (follow-up).
- 🔄 Better generation controls:
  - ✅ Tone presets (minimal, editorial, product, portfolio, landing).
  - ✅ Optional strict minimal mode (fewer decorations).
  - ⬜ Output size and complexity sliders.
- ⬜ Prompt iteration UX:
  - ⬜ Keep instruction history with concise diffs.
  - ⬜ Regenerate section-level variants (hero, cards, footer).
- ⬜ Accessibility checks:
  - ⬜ Contrast guardrails in generation prompt.
  - ⬜ Keyboard navigation checks in generated templates.

Exit criteria:
- ✅ Reduced failed-generation rate (baseline established).
- ⬜ Faster time-to-usable-result for first prompt.
- ⬜ Documented visual system and generation presets.

## Phase 3: Productization (4-8 weeks)

Goals:
- Make the tool production-usable for repeated workflows.
- Keep architecture minimal but extensible.

Work items:
- Project export modes:
  - Single HTML export (current default).
  - Optional split export (index.html, styles.css, app.js).
- Configurable generation profiles:
  - profiles/minimal.json (strict default).
  - profiles/startup-landing.json, profiles/portfolio.json.
- Template memory:
  - Save successful outputs as reusable local templates.
  - Let users seed new generations from a prior build.
- Observability:
  - Structured logs around API latency and failures.
  - Lightweight analytics hooks (local-only, opt-in).

Exit criteria:
- Repeatable workflow for build -> revise -> export.
- Strong reliability for long editing sessions.

## Phase 4: Advanced Minimal Builder Ideas

Potential additions that preserve minimalism:
- Constraint-first generation:
  - Users specify only constraints (sections, color limits, density), model fills details.
- Layout DNA:
  - Extract reusable layout grammar from accepted generations.
- Refine mode:
  - "Improve only spacing" or "Improve typography only" updates without major rewrites.
- Safety rails:
  - Validate generated JS complexity and forbid unnecessary scripts.

## Engineering Principles

- Minimal surface area, maximal clarity.
- Keep dependencies low and explicit.
- Prefer pure functions for generation/data paths.
- Every behavior change should include tests and docs updates.
