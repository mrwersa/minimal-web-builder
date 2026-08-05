from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.rendering import _PREVIEW_CSP

# Markers used to find (and strip) editor-injected markup from exported code.
CSP_META_MARKER_NAME = "mwb-preview-csp"
EDITOR_STYLE_ID = "mwb-editor-style"
EDITOR_SHIM_ID = "mwb-editor-shim"
TOOLBAR_ID = "mwb-toolbar"
SEL_CLASS = "mwb-sel"

_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "wysiwyg"

_EDITOR_STYLE = (
    f'<style id="{EDITOR_STYLE_ID}">'
    f".{SEL_CLASS}{{outline:2px solid #1976d2 !important;outline-offset:2px;}}"
    f"#{TOOLBAR_ID} button:hover{{background:#e3f2fd !important;}}"
    f'[contenteditable="true"]{{cursor:text;}}'
    "</style>"
)

_EDITOR_SHIM_JS = (
    """
(function(){
  function post(m){ try{ window.parent.postMessage(m, '*'); }catch(e){} }
  function ready(fn){ if(document.readyState==='loading'){ document.addEventListener('DOMContentLoaded',fn); } else { fn(); } }
  ready(function(){
    var TB = document.createElement('div');
    TB.id = '"""
    + TOOLBAR_ID
    + """';
    TB.style.cssText = 'position:fixed;top:10px;left:50%;transform:translateX(-50%);z-index:2147483647;display:none;gap:6px;align-items:center;background:#ffffff;border:1px solid #e3e8ee;border-radius:10px;box-shadow:0 4px 16px rgba(0,0,0,.18);padding:6px 8px;font:13px/1.4 system-ui,-apple-system,sans-serif;color:#222;max-width:90vw;flex-wrap:wrap;';
    function btn(t,fn){ var b=document.createElement('button'); b.textContent=t; b.style.cssText='border:1px solid #e3e8ee;background:#f7f9fb;border-radius:6px;padding:4px 8px;cursor:pointer;font:inherit;color:#222;'; b.addEventListener('click',fn); return b; }
    var sel=null;
    function clearSel(){ if(sel){ sel.classList.remove('"""
    + SEL_CLASS
    + """'); sel.removeAttribute('contenteditable'); sel=null; } }
    function selectEl(el){ clearSel(); sel=el; el.classList.add('"""
    + SEL_CLASS
    + """'); el.setAttribute('contenteditable','true'); el.focus(); TB.style.display='flex'; }
    document.addEventListener('click', function(e){
      if(e.target.closest('#"""
    + TOOLBAR_ID
    + """')) return;
      if(e.target.tagName==='A'){ e.preventDefault(); }
      if(sel && sel.contains(e.target)) return;
      e.preventDefault();
      if(e.target===document.body||e.target===document.documentElement){ clearSel(); TB.style.display='none'; return; }
      selectEl(e.target);
    }, true);
    function cmd(c,v){ try{ document.execCommand(c,false,v); }catch(e){} }
    TB.appendChild(btn('B',function(){cmd('bold');}));
    TB.appendChild(btn('I',function(){cmd('italic');}));
    var sw=document.createElement('input'); sw.type='color'; sw.title='Text color'; sw.value='#1976d2'; sw.style.cssText='width:28px;height:28px;border:1px solid #e3e8ee;border-radius:6px;cursor:pointer;background:#fff;';
    sw.addEventListener('change',function(){ cmd('foreColor', sw.value); });
    TB.appendChild(sw);
    TB.appendChild(btn('A+',function(){ if(sel){ var c=parseFloat(getComputedStyle(sel).fontSize)||16; sel.style.fontSize=(c+2)+'px'; } }));
    TB.appendChild(btn('A-',function(){ if(sel){ var c=parseFloat(getComputedStyle(sel).fontSize)||16; sel.style.fontSize=Math.max(8,c-2)+'px'; } }));
    TB.appendChild(btn('Delete',function(){ if(sel){ var p=sel.parentNode; if(p){ p.removeChild(sel); clearSel(); TB.style.display='none'; } } }));
    var apply=btn('Apply',function(){
      var clone=document.documentElement.cloneNode(true);
      function rm(id){ var e=clone.querySelector('#'+id); if(e)e.remove(); }
      rm('"""
    + TOOLBAR_ID
    + """'); rm('"""
    + EDITOR_SHIM_ID
    + """'); rm('"""
    + EDITOR_STYLE_ID
    + """');
      var csp=clone.querySelector('meta[name=\""""
    + CSP_META_MARKER_NAME
    + """\"]'); if(csp)csp.remove();
      clone.querySelectorAll('."""
    + SEL_CLASS
    + """').forEach(function(el){ el.classList.remove('"""
    + SEL_CLASS
    + """'); el.removeAttribute('contenteditable'); });
      post({type:'mwb:edits', nonce: Date.now(), html: '<!doctype html>\\n'+clone.outerHTML});
    });
    apply.style.cssText='border:1px solid #1976d2;background:#1976d2;color:#fff;border-radius:6px;padding:4px 10px;cursor:pointer;font:inherit;font-weight:600;';
    TB.appendChild(apply);
    document.body.appendChild(TB);
  });
})();
"""
)

_EDITOR_SHIM_SCRIPT = f'<script id="{EDITOR_SHIM_ID}">{_EDITOR_SHIM_JS}</script>'

_FULL_DOC_RE = re.compile(r"^\s*(<!doctype|<html)", re.IGNORECASE)
_HEAD_CLOSE_RE = re.compile(r"</head>", re.IGNORECASE)
_BODY_CLOSE_RE = re.compile(r"</body>", re.IGNORECASE)


def is_full_document(html_str: str) -> bool:
    """True when the markup already provides its own document shell."""
    return bool(_FULL_DOC_RE.match(html_str))


def build_editable_preview_document(generated_html: str, editing: bool = False) -> str:
    """Build a sandboxed preview document, optionally with the WYSIWYG shim.

    Returns the srcdoc *document* string (not an <iframe> element). The CSP meta
    and editor shim are marked so they can be stripped from exported markup.
    """
    csp_meta = (
        f'<meta name="{CSP_META_MARKER_NAME}" '
        f'http-equiv="Content-Security-Policy" content="{_PREVIEW_CSP}">'
    )
    if is_full_document(generated_html):
        head_inject = csp_meta
        if editing:
            head_inject += _EDITOR_STYLE + _EDITOR_SHIM_SCRIPT
        if _HEAD_CLOSE_RE.search(generated_html):
            return _HEAD_CLOSE_RE.sub(head_inject + "</head>", generated_html, count=1)
        if _BODY_CLOSE_RE.search(generated_html):
            return _BODY_CLOSE_RE.sub(head_inject + "</body>", generated_html, count=1)
        return generated_html + head_inject
    style = _EDITOR_STYLE if editing else ""
    script = _EDITOR_SHIM_SCRIPT if editing else ""
    return (
        "<!doctype html><html><head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"{csp_meta}{style}"
        '</head><body style="margin:0;padding:0;">'
        f"{generated_html}{script}"
        "</body></html>"
    )


_STRIP_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(rf'<style id="{EDITOR_STYLE_ID}">.*?</style>', re.DOTALL),
    re.compile(rf'<script id="{EDITOR_SHIM_ID}">.*?</script>', re.DOTALL),
    re.compile(rf'<meta\s+name="{CSP_META_MARKER_NAME}"[^>]*>', re.IGNORECASE),
    re.compile(r"\bmwb-sel\b"),
)


def strip_editor_injected_markup(html_str: str) -> str:
    """Remove editor-injected style/script/CSP/selection markup.

    A safety net for markup returned by the editor: the shim already cleans its
    serialization, but this guards against JS-side regressions so exported
    code stays clean and deterministic.
    """
    out = html_str
    for pat in _STRIP_PATTERNS:
        out = pat.sub("", out)
    return out


_component: Any = None


def register_component() -> Any:
    """Eagerly register the custom component with Streamlit's server.

    Safe to call at app startup; tests don't need to call it.
    """
    return _get_component()


def _get_component() -> Any:
    global _component
    if _component is None:
        import streamlit.components.v1 as components

        _component = components.declare_component("wysiwyg", path=str(_FRONTEND_DIR))
    return _component


def wysiwyg_preview(
    html: str,
    editing: bool = False,
    height: int = 800,
    key: str = "wysiwyg_preview",
) -> dict[str, Any]:
    """Render the editable preview via a custom Streamlit component.

    Returns the latest message posted by the editor (e.g. ``{"type": "mwb:edits", ...}``)
    or ``{"type": "mwb:none"}`` when nothing has been sent yet.
    """
    return _get_component()(
        html=html,
        editing=editing,
        height=height,
        key=key,
        default={"type": "mwb:none"},
    )


def consume_edit_message(state: dict[str, Any], message: dict[str, Any]) -> bool:
    """Apply an ``mwb:edits`` message to session state once (nonce-guarded).

    Returns True when the edit was applied, False when it was a stale duplicate.
    """
    if message.get("type") != "mwb:edits":
        return False
    nonce = int(message.get("nonce") or 0)
    if nonce and nonce == state.get("last_edit_nonce", 0):
        return False
    html = strip_editor_injected_markup(message.get("html", ""))
    if not html:
        return False
    state["last_app_code"] = html
    state["last_edit_nonce"] = nonce
    return True
