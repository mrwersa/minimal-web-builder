from __future__ import annotations

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


def preview_container_class(is_generating: bool) -> str:
    return "preview-container blur" if is_generating else "preview-container"
