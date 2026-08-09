# Minimal Web Builder

A sleek, minimalist web application builder powered by AI (Gemini / OpenRouter). Create beautiful, responsive websites through natural language prompts with instant preview, WYSIWYG editing, and one-click export.

![Minimal Web Builder](https://img.shields.io/badge/Minimal%20Web%20Builder-v2.0-blue)
![React](https://img.shields.io/badge/React-18-61DAFB)
![FastAPI](https://img.shields.io/badge/FastAPI-0.41-009688)
![LangGraph](https://img.shields.io/badge/LangGraph-1.2-1C3C3C)

## Features

- Minimal, distraction-free interface
- Responsive web app generation
- Prompt-driven chat workflow
- Gemini-powered HTML/CSS/JS generation
- Tone presets (minimal, editorial, product, portfolio, landing)
- Generation profiles (Minimal, Startup Landing, Portfolio) that bundle tone, complexity, and guidance
- Output complexity control (compact / balanced / detailed)
- Optional strict minimal mode for flat, monochrome designs
- Accessibility guardrails in generation + static audit of generated HTML
- Iterative refinement: prior instructions are preserved so follow-up prompts build on the original request
- Section-level regeneration: pick any top-level section (hero, cards, footer) and regenerate just that block
- Refine mode: focus a section update on spacing, typography, layout, or color only
- Constraint-first generation: pick sections, a color limit, and density; the model fills in the details
- Layout DNA: inspect the grammar of the current page, save good layouts, and reuse their rhythm in future generations
- Safety rails: empty inline scripts are stripped and generated JS is audited for complexity and unsafe calls
- Visible keyboard focus-state verification in generated templates
- Export options: single `index.html` or split `index.html` + `styles.css` + `app.js`
- Private template memory: save the current page to your account and open it later as a reversible new starting point
- Structured API logging with an opt-in local analytics file
- Instant preview and code view
- WYSIWYG editing: select and edit elements on the visual canvas with debounced synchronization and undo/redo
- Input lock while generation is running
- Self-contained output (no external frontend dependencies)
- Durable projects with automatic SQLite development storage or PostgreSQL via `DATABASE_URL`
- Immutable page revisions, debounced autosave, optimistic conflict detection, and restore
- Email/password accounts with Argon2id hashing, opaque server-side sessions, and owner-isolated projects
- Owner-isolated reusable templates and Layout DNA stored in the application database
- Durable conversation checkpoints and generation-job history shared by every generation path
- Named revision checkpoints, restore, and one-click project branching from any revision
- Database-backed generation/authentication rate limits, idempotency keys, and owner-scoped audit events
- A document-native visual workspace with stable selection, breadcrumbs, draggable layers, and a focused property inspector
- Desktop, tablet, and mobile canvas presets with zoom and direct responsive controls for spacing, typography, color, layout, visibility, and links
- Global color, typography, spacing, radius, and container tokens that can be reused across element styles
- Element-scoped AI editing that uses stable node IDs and applies only the generated target subtree
- Keyboard-navigable layers, document shortcuts, and a searchable accessible command palette
- Explicit, undoable advanced editors for head markup, custom CSS, and sandboxed body scripts


## Setup

1. Install Python deps and the frontend:
   ```bash
   pip install -r requirements.txt
   cd web && npm install
   ```
2. Create a `.env` with an API key (see below).
   The default `DATABASE_URL` uses `./data/minimal-web-builder.db`; set a
   `postgresql+psycopg://...` URL for a production PostgreSQL database.
3. Apply database migrations before starting a production/PostgreSQL deployment,
   or when upgrading an existing SQLite database:
   ```bash
   alembic upgrade head
   ```
   A new local SQLite database creates its schema automatically; migrations remain
   the canonical upgrade and production schema history. The first account created
   after this ownership migration claims projects created by the pre-auth version.
4. Run both processes:
   ```bash
   # terminal 1: API
   uvicorn server.main:app --port 8000 --reload
   # terminal 2: frontend
   cd web && npm run dev
   ```
5. Open http://localhost:5173 (the Vite dev server proxies `/api` to :8000),
   create an account, and start a project. Set `SESSION_COOKIE_SECURE=true` in
   HTTPS production deployments; customize `SESSION_HOURS` and `CORS_ORIGINS`
   when the frontend and API use different origins. The authentication and
   generation limits can be tuned with `AUTH_RATE_LIMIT_PER_MINUTE` and
   `GENERATION_RATE_LIMIT_PER_MINUTE`.

For a single-process production build, run `cd web && npm run build` then
`uvicorn server.main:app --port 8000` and open http://localhost:8000/.

## Usage

1. Once the app is running, create an account or sign in to your private workspace.
2. Open the sidebar to pick a generation **Profile** (Minimal, Startup Landing, Portfolio) or keep **Custom** to set tone, complexity, and strict minimal mode individually. Profile selection disables the manual controls and applies the profile's settings to the next generation.
3. Type a description of the website you want to create, for example:
   - "Create a landing page for a coffee shop with a hero section, menu, and contact form"
   - "Build a personal portfolio website with projects section and about me"
   - "Design a minimal blog homepage with featured posts"
4. Press enter. While your site is being generated, the preview area will blur and a modern animated loader will appear above it. The chat input is disabled until generation is complete.
5. Preview your website in the main area (full height up to the chat input)
6. Use the "View Code" tab to see the HTML/CSS/JS
7. In the Code tab, pick an export format: **Single HTML** downloads one self-contained `index.html`, or **Split** downloads `index.html`, `styles.css`, and `app.js` (inline styles and scripts are extracted into the separate files)
8. In the sidebar you can **save the current page as a template**, then use the folder button beside a saved template to open it as a fresh conversation
9. In **Projects**, create, search, rename, duplicate, or archive durable projects. Later edits autosave as immutable revisions; add named checkpoints, restore an earlier result, or branch a new project from any revision in Version history.

To refine a single section after generation, open the sidebar, pick a section from the "Regenerate section" dropdown, choose a **Refine focus** (General, Spacing, Typography, Layout, or Color), and press **Regenerate section**. The selected block is regenerated in place while the rest of the page stays untouched.

To edit the generated page directly, turn on **WYSIWYG editing** in the sidebar (Refine section). Select elements in the canvas or Layers tree, then use the Inspector for content, spacing, typography, color, layout, visibility, and links. Desktop, tablet, and mobile presets apply breakpoint-specific values without regenerating the page, and zoom keeps narrow canvases comfortable to edit. Preview, Code, export, and undo/redo all use the updated structured document while preserving page metadata, styles, attributes, and scripts. Editing pauses while generation is running.

## How It Works

1. The React frontend sends your prompt to the FastAPI backend.
2. A LangGraph conversational agent classifies your intent (generate / refine / answer), calls the AI model, and validates the output through safety + accessibility guardrails.
3. The generated HTML is rendered in a sandboxed preview iframe.
4. Turn on WYSIWYG editing to click and edit elements directly.
5. Describe refinements in the chat bar — the agent applies them to the current page.
6. Export your page as a single HTML file or split into HTML/CSS/JS.
7. When a project is active, document changes autosave with an expected version so stale browser sessions cannot silently overwrite newer work.
8. Conversation state, standalone edits, and generation outcomes are checkpointed in the database, so a browser or server restart restores the active thread.
9. Mutating requests carry idempotency keys, sensitive generation/authentication routes are rate-limited, and mutation outcomes are written to owner-scoped audit history.

## Technologies

- **React 18 + Vite + TypeScript** — single-page frontend
- **Tailwind CSS** — styling, themed from the shared design tokens
- **Zustand** — lightweight state
- **FastAPI** — backend serving the existing `src/*` generation, safety, and export logic
- **LangGraph** — conversational agent with memory, guardrails, and resilience
- **Python** — backend language
- **uvicorn** — ASGI server
- **Google Generative AI / OpenRouter** — Gemini model for code generation
- **HTML/CSS/JS** — output languages

## Requirements

- Python 3.12+
- Node.js 24+
- See `requirements.txt` and `web/package.json`

## Verification

```bash
# Backend
coverage run -m pytest -q
coverage report --include="src/*,server/*" --fail-under=70

# Frontend unit, type, and build gates
cd web
npm run typecheck
npm test
npm run build

# Critical browser workflow (install Chromium once first)
npx playwright install chromium
npm run test:e2e
```

## Repository Protection

This repository uses PR-only governance on the main branch:

- Direct pushes to main are blocked
- At least 1 approving review is required
- CODEOWNERS review is required
- Stale approvals are dismissed after new commits
- Last push must be approved by someone else
- Conversation resolution is required before merge
- Linear history is required
- Force pushes and branch deletions are blocked
- CI runs backend validation, lint/format, frontend type/test/build, and Chromium browser-smoke gates

See:

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [.github/CODEOWNERS](.github/CODEOWNERS)
- [.github/PULL_REQUEST_TEMPLATE/default.md](.github/PULL_REQUEST_TEMPLATE/default.md)
- [.github/workflows/ci.yml](.github/workflows/ci.yml)

## Product Roadmap

The detailed roadmap is in [ROADMAP.md](ROADMAP.md).

Current priorities:

- Phase 0: complete — product truth, reversible document changes, editor reliability, and full-stack CI
- Phase 1: complete — private projects, reusable assets, durable conversations/jobs, revision branching, and request hardening
- Phase 2: complete — a durable versioned document model with stable canvas node IDs and deterministic HTML compilation, plus responsive controls, global design tokens, element-scoped AI, a command palette, and advanced code escape hatches
- Phase 3: next — cancellable, measurable, patch-based AI generation
- Phase 4: multi-page publishing, assets, forms, domains, and rollback
- Phase 5: collaboration and scale after the core single-user workflow has traction

## Contributing

Contributions are welcome through pull requests only. Start with [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

For private vulnerability reporting, see [SECURITY.md](SECURITY.md).

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

Created with ❤️ using [Claude Code](https://anthropic.com/claude)
