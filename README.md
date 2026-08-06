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
- Template memory: save the current page as a local template and reuse it to seed new generations
- Structured API logging with an opt-in local analytics file
- Instant preview and code view
- WYSIWYG editing: click any element in the preview to edit its text and style it inline, then Apply to sync changes back into the page
- Input lock while generation is running
- Self-contained output (no external frontend dependencies)


## Setup

1. Install Python deps and the frontend:
   ```bash
   pip install -r requirements.txt
   cd web && npm install
   ```
2. Create a `.env` with an API key (see below).
3. Run both processes:
   ```bash
   # terminal 1: API
   uvicorn server.main:app --port 8000 --reload
   # terminal 2: frontend
   cd web && npm run dev
   ```
4. Open http://localhost:5173 (the Vite dev server proxies `/api` to :8000).

For a single-process production build, run `cd web && npm run build` then
`uvicorn server.main:app --port 8000` and open http://localhost:8000/.

## Usage

1. Once the app is running, you'll see a clean interface with a chat input at the bottom.
2. Open the sidebar to pick a generation **Profile** (Minimal, Startup Landing, Portfolio) or keep **Custom** to set tone, complexity, and strict minimal mode individually. Profile selection disables the manual controls and applies the profile's settings to the next generation.
3. Type a description of the website you want to create, for example:
   - "Create a landing page for a coffee shop with a hero section, menu, and contact form"
   - "Build a personal portfolio website with projects section and about me"
   - "Design a minimal blog homepage with featured posts"
4. Press enter. While your site is being generated, the preview area will blur and a modern animated loader will appear above it. The chat input is disabled until generation is complete.
5. Preview your website in the main area (full height up to the chat input)
6. Use the "View Code" tab to see the HTML/CSS/JS
7. In the Code tab, pick an export format: **Single HTML** downloads one self-contained `index.html`, or **Split** downloads `index.html`, `styles.css`, and `app.js` (inline styles and scripts are extracted into the separate files)
8. In the Code tab you can also **save the current page as a template**, then later start a new conversation from any saved template

To refine a single section after generation, open the sidebar, pick a section from the "Regenerate section" dropdown, choose a **Refine focus** (General, Spacing, Typography, Layout, or Color), and press **Regenerate section**. The selected block is regenerated in place while the rest of the page stays untouched.

To edit the generated page directly, turn on **WYSIWYG editing** in the sidebar (Refine section). Click any element in the preview to select it, type to edit its text, and use the floating toolbar to bold/italicize text, change its color, resize it, or delete it. Press **Apply** to sync the edits into the page (the Preview, Code, and export all update). Editing is paused while a generation is running.

## How It Works

1. The React frontend sends your prompt to the FastAPI backend.
2. A LangGraph conversational agent classifies your intent (generate / refine / answer), calls the AI model, and validates the output through safety + accessibility guardrails.
3. The generated HTML is rendered in a sandboxed preview iframe.
4. Turn on WYSIWYG editing to click and edit elements directly.
5. Describe refinements in the chat bar — the agent applies them to the current page.
6. Export your page as a single HTML file or split into HTML/CSS/JS.

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
- Node.js 18+
- See `requirements.txt` and `web/package.json`

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
- CI status checks `ci / validate` (context: `validate`) and `ci / lint` (context: `lint`) are required

See:

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [.github/CODEOWNERS](.github/CODEOWNERS)
- [.github/PULL_REQUEST_TEMPLATE/default.md](.github/PULL_REQUEST_TEMPLATE/default.md)
- [.github/workflows/ci.yml](.github/workflows/ci.yml)

## Product Roadmap

The detailed roadmap is in [ROADMAP.md](ROADMAP.md).

Highlights:

- Phase 1: Refactor into modules, add tests, stabilize generation lifecycle ✅ complete
- Phase 2: UX/design system and generation controls while staying minimal ✅ complete
- Phase 3: Export modes, profiles, and product-grade reliability ✅ complete
- Phase 4: Advanced minimal-builder ideas — constraint-first generation, refine mode, safety rails, and layout DNA ✅ complete
- Phase 5: WYSIWYG editing (in-app direct manipulation of the generated page) 🔄 in progress

## Contributing

Contributions are welcome through pull requests only. Start with [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

For private vulnerability reporting, see [SECURITY.md](SECURITY.md).

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

Created with ❤️ using [Claude Code](https://anthropic.com/claude)