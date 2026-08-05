from __future__ import annotations

import html

from src.theme import COLORS

PREVIEW_LOADER_OVERLAY_HTML = """
<style>
.preview-loader-overlay {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: rgba(247,249,251,0.65);
    z-index: 10;
    backdrop-filter: blur(2.5px);
}
.preview-loader-spinner {
    width: 54px;
    height: 54px;
    margin-bottom: 18px;
    display: block;
}
.preview-loader-message {
    font-size: 1.13em;
    color: #1976d2 !important;
    font-weight: 500;
    letter-spacing: 0.01em;
    text-align: center;
    margin-top: 0;
    text-shadow: 0 1px 4px #fff, 0 0 2px #f7f9fb;
}
</style>
<div class="preview-loader-overlay">
    <svg class="preview-loader-spinner" viewBox="0 0 50 50">
        <circle cx="25" cy="25" r="20" fill="none" stroke="#1976d2" stroke-width="5" stroke-linecap="round" stroke-dasharray="31.4 31.4" stroke-dashoffset="0">
            <animateTransform attributeName="transform" type="rotate" from="0 25 25" to="360 25 25" dur="0.9s" repeatCount="indefinite"/>
        </circle>
        <circle cx="25" cy="25" r="12" fill="none" stroke="#90caf9" stroke-width="3" stroke-linecap="round" stroke-dasharray="18.8 18.8" stroke-dashoffset="0">
            <animateTransform attributeName="transform" type="rotate" from="360 25 25" to="0 25 25" dur="1.2s" repeatCount="indefinite"/>
        </circle>
    </svg>
    <div class="preview-loader-message">Generating your minimalist website...</div>
</div>
""".strip()

EMPTY_STATE_HTML = """
<div style="height:500px;display:flex;flex-direction:column;align-items:center;justify-content:center;">
    <svg width="120" height="120" viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="60" cy="60" r="56" fill="#E3F2FD" stroke="#90CAF9" stroke-width="4"/>
        <rect x="35" y="50" width="50" height="30" rx="6" fill="#fff" stroke="#90CAF9" stroke-width="2"/>
        <rect x="45" y="60" width="30" height="6" rx="3" fill="#BBDEFB"/>
        <circle cx="60" cy="65" r="2.5" fill="#90CAF9"/>
        <rect x="55" y="72" width="10" height="3" rx="1.5" fill="#E3F2FD"/>
        <ellipse cx="60" cy="95" rx="18" ry="4" fill="#E3F2FD"/>
    </svg>
    <div style="margin-top:18px;font-size:1.18em;color:#1976d2;font-weight:500;letter-spacing:0.01em;text-align:center;">
        <span style="font-size:1.5em;">Start your creative journey!</span><br/>
        <span style="color:#78909c;font-size:1em;">Describe your dream website below and watch it come to life.</span>
    </div>
</div>
""".strip()

NO_CODE_PLACEHOLDER = "<!-- No code generated yet -->"


_PREVIEW_CSP = (
    "default-src 'none'; img-src data: blob:; style-src 'unsafe-inline'; "
    "script-src 'unsafe-inline'; font-src data:; connect-src 'none'; "
    "frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none';"
)

# Sentinel meta tag used to strip the preview's injected CSP from export markup.
PREVIEW_CSP_META = (
    '<meta http-equiv="Content-Security-Policy" content="'
    "default-src 'none'; img-src data: blob:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
    "font-src data:; connect-src 'none'; frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none';"
    '">'
)


def build_preview_document(generated_html: str) -> str:
    """Wrap generated output in a sandboxed document with a restrictive CSP.

    The returned string is the srcdoc *document* (not an <iframe> element), so it
    can be assigned to an iframe's ``srcdoc`` property or used inside a custom
    component. Editors may inject an additional shim into this document.
    """
    return (
        "<!doctype html>"
        "<html><head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<meta http-equiv="Content-Security-Policy" content="{_PREVIEW_CSP}">'
        '</head><body style="margin:0;padding:0;">'
        f"{generated_html}"
        "</body></html>"
    )


def build_sandboxed_preview_html(generated_html: str) -> str:
    # Constrain generated output to a sandboxed iframe with a restrictive CSP.
    srcdoc_document = build_preview_document(generated_html)
    escaped_srcdoc = html.escape(srcdoc_document, quote=True)
    return (
        "<iframe "
        'sandbox="allow-scripts allow-forms" '
        'referrerpolicy="no-referrer" '
        f'srcdoc="{escaped_srcdoc}" '
        'style="width:100%;height:100%;border:0;background:#fff;"'
        "></iframe>"
    )


def preview_container_class(is_generating: bool) -> str:
    return "preview-container blur" if is_generating else "preview-container"


def _apply_colors(css: str) -> str:
    for key in sorted(COLORS, key=len, reverse=True):
        css = css.replace(f"${key}", COLORS[key])
    return css


_APP_STYLES_TEMPLATE = """
/* Complete hiding of default Streamlit elements */
#MainMenu, header, footer {display: none !important;}
.stDeployButton {display: none !important;}
[data-testid="stToolbar"] {display: none !important;}
.viewerBadge_container__1QSob {display: none !important;}

/* Base theme */
html, body, .stApp {
    margin: 0;
    padding: 0;
    background: $bg;
    color: $text;
}

[data-testid="stMainBlockContainer"] {
    padding: 2rem 2.5rem 7rem !important;
    max-width: 1280px;
    margin: 0 auto;
}

/* Tabs */
[data-testid="stTabs"] {
    background: $surface;
    border: 1px solid $border;
    border-radius: 12px 12px 0 0;
    border-bottom: 1.5px solid $border;
    padding: 0 12px;
}
[data-testid="stTab"] {
    font-size: 1.05em;
    font-weight: 500;
    color: $muted;
    padding: 10px 20px;
    border-radius: 8px 8px 0 0;
}
[data-testid="stTab"]:hover {
    color: $accent;
}
[data-testid="stTab"][aria-selected="true"] {
    color: $accent;
    box-shadow: inset 0 -2px 0 $accent;
}

/* Preview area */
.preview-container {
    width: 100%;
    border: 1px solid $border;
    border-radius: 12px;
    overflow: hidden;
    position: relative;
    background: $surface;
}

/* Chat input: Streamlit already pins it via stBottom, just restyle */
[data-testid="stChatInput"] {
    background: $bg !important;
    border-top: 1px solid $border;
    padding: 8px 0;
}
[data-testid="stChatInput"] textarea {
    background: $surface !important;
    border: 1.5px solid $border !important;
    border-radius: 24px !important;
    color: $text !important;
    caret-color: $accent !important;
    box-shadow: none !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: $accent !important;
    background: $surface !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: $muted !important;
    opacity: 1 !important;
}
[data-testid="stChatInput"] textarea:disabled {
    background: $bg !important;
    color: $disabled !important;
}
""".strip()


def build_app_styles() -> str:
    return "<style>" + _apply_colors(_APP_STYLES_TEMPLATE) + "</style>"
