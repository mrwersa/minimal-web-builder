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


def build_sandboxed_preview_html(generated_html: str) -> str:
    # Constrain generated output to a sandboxed iframe with a restrictive CSP.
    srcdoc_document = (
        "<!doctype html>"
        "<html><head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" '
        "content=\"default-src 'none'; img-src data: blob:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
        "font-src data:; connect-src 'none'; frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none';\">"
        '</head><body style="margin:0;padding:0;">'
        f"{generated_html}"
        "</body></html>"
    )
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

/* Remove ALL padding and margins */
.block-container {
    padding: 0 !important;
    margin: 0 !important;
    max-width: 100% !important;
}

/* Fix gaps */
div[data-testid="stVerticalBlock"] {
    gap: 0 !important;
}

/* Remove padding from every element */
section.main, .element-container {
    padding: 0 !important;
    margin: 0 !important;
}

html, body, .stApp {
    margin: 0;
    padding: 0;
    height: 100vh;
    overflow-x: hidden;
    background: $bg;
}
.app-frame {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}
.main-scroll-area {
    flex: 1 1 auto;
    display: flex;
    flex-direction: column;
    align-items: stretch;
    justify-content: flex-start;
    padding: 0;
    margin: 0;
    overflow: hidden;
    position: relative;
    min-height: 0;
}
.sticky-tabs {
    position: sticky !important;
    top: 0 !important;
    z-index: 1002 !important;
    background: $bg !important;
}
.tab-content-scroll {
    flex: 1 1 auto;
    overflow-y: auto;
    min-height: 0;
    position: relative;
    padding-bottom: 24px;
}
.stChatInput {
    position: fixed !important;
    left: 0;
    right: 0;
    bottom: 0;
    width: 100vw;
    z-index: 2000;
    background: $bg !important;
    border-top: 1px solid #e9ecef;
    margin: 0 !important;
    padding: 0 20px;
}
.stChatInput > div {
    margin: 0 !important;
    padding: 0 !important;
    background: $bg !important;
    box-shadow: none !important;
    border-radius: 0 !important;
}
.stChatInput input, .stChatInput textarea {
    color: $text !important;
    caret-color: $accent !important;
    padding: 12px 16px !important;
    font-size: 1.08em !important;
    background: $surface !important;
    border: 1.5px solid $border !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    outline: none !important;
    transition: border-color 0.2s;
}
.stChatInput input:focus, .stChatInput textarea:focus {
    border: 1.5px solid $accent !important;
    outline: none !important;
    background: $surface !important;
}
.stChatInput input::placeholder, .stChatInput textarea::placeholder {
    color: $muted !important;
    opacity: 1 !important;
}
.stChatInput input:disabled, .stChatInput textarea:disabled {
    background: $bg !important;
    color: $disabled !important;
}
.preview-container {
    width: 100%;
    flex: 1 1 auto;
    min-height: 0;
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: stretch;
    justify-content: flex-start;
}
.status-indicator {
    position: absolute;
    left: 50%;
    bottom: 80px;
    transform: translateX(-50%);
    background: rgba(255,255,255,0.95);
    padding: 8px 16px;
    border-radius: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    font-size: 14px;
    z-index: 1001;
}
.stButton, .stDownloadButton {
    margin: 0 !important;
}
iframe {
    width: 100vw !important;
    max-width: 100% !important;
    height: 100% !important;
    min-height: 0 !important;
    border: none !important;
    display: block;
    overflow: auto !important;
}
.stTabs [data-baseweb="tab-list"] {
    background: $surface;
    border-radius: 10px 10px 0 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    border-bottom: 1.5px solid $border;
    padding-left: 12px;
}
.stTabs [data-baseweb="tab"] {
    font-size: 1.08em;
    font-weight: 500;
    color: $accent;
    padding: 12px 24px 10px 24px;
    margin-right: 2px;
    border-radius: 10px 10px 0 0;
    background: $bg;
    transition: background 0.2s, color 0.2s;
}
.stTabs [aria-selected="true"] {
    background: $accent !important;
    color: $surface !important;
    box-shadow: 0 2px 8px rgba(25,118,210,0.08);
}
.stTabs [data-baseweb="tab-panel"] {
    padding-top: 0 !important;
    margin-top: 0 !important;
}
""".strip()


def build_app_styles() -> str:
    return "<style>" + _apply_colors(_APP_STYLES_TEMPLATE) + "</style>"
