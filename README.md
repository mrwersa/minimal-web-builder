# Minimal Web Builder

A sleek, minimalist web application builder powered by Google Gemini AI. Create beautiful, responsive websites through natural language prompts with instant preview capabilities.

![Minimal Web Builder](https://img.shields.io/badge/Minimal%20Web%20Builder-v1.0-blue)
![Streamlit](https://img.shields.io/badge/Made%20with-Streamlit-FF4B4B)
![Gemini AI](https://img.shields.io/badge/Powered%20by-Gemini%20AI-green)

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
- Safety rails: empty inline scripts are stripped and generated JS is audited for complexity and unsafe calls
- Visible keyboard focus-state verification in generated templates
- Export options: single `index.html` or split `index.html` + `styles.css` + `app.js`
- Template memory: save the current page as a local template and reuse it to seed new generations
- Structured API logging with an opt-in local analytics file
- Instant preview and code view
- Input lock while generation is running
- Self-contained output (no external frontend dependencies)


## Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/mrwersa/minimal-web-builder.git
   cd minimal-web-builder
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root with your API key:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   ```
   Optional: set `ANALYTICS_FILE=data/events.jsonl` to append structured generation events (latency, output size, failures) as JSON lines to a local file.

4. Run the application:
   ```bash
   streamlit run app.py
   ```

5. Open your browser and navigate to:
   ```
   http://localhost:8501
   ```

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

## How It Works

1. The application uses the Streamlit framework for the user interface
2. When you enter a prompt, it's sent to Google's Gemini AI
3. Gemini generates complete HTML, CSS, and JavaScript code
4. Use the sidebar to pick a tone preset (editorial, product, portfolio, landing) or enable strict minimal mode before generating
5. While generating, the preview area is blurred and a loader overlay is shown
6. The code is rendered directly in the browser for immediate preview (full height)
7. You can view and download the source code

## Technologies

- **Streamlit** - Python web app framework
- **Google Generative AI** - Gemini model for code generation
- **Python** - Backend language
- **HTML/CSS/JS** - Output languages

## Requirements

- Python 3.7+
- streamlit>=1.30.0
- google-generativeai>=0.3.2
- python-dotenv

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
- Phase 4: Advanced minimal-builder ideas (constraint-first and refine mode)

## Contributing

Contributions are welcome through pull requests only. Start with [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

For private vulnerability reporting, see [SECURITY.md](SECURITY.md).

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

Created with ❤️ using [Claude Code](https://anthropic.com/claude)