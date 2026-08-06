import { useEffect, useMemo, useRef } from "react";
import { MousePointerClick } from "lucide-react";
import { useStore } from "../store";
import { Spinner } from "./ui/Spinner";
import GrapeJSEditor from "./GrapeJSEditor";

const CSP = (
  "default-src 'none'; img-src data: blob:; style-src 'unsafe-inline'; " +
  "script-src 'unsafe-inline'; font-src data:; connect-src 'none'; " +
  "frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none';"
);
const CSP_META = `<meta name="mwb-preview-csp" http-equiv="Content-Security-Policy" content="${CSP}">`;

const EDITOR_STYLE = `<style id="mwb-editor-style">
.mwb-sel{outline:2px solid #2563eb !important;outline-offset:2px;}
#mwb-toolbar button:hover{background:#eff6ff !important;}
[contenteditable="true"]{cursor:text;}
</style>`;

const EDITOR_SHIM = `<script id="mwb-editor-shim">
(function(){
  function post(m){ try{ window.parent.postMessage(m, '*'); }catch(e){} }
  function ready(fn){ if(document.readyState==='loading'){ document.addEventListener('DOMContentLoaded',fn); } else { fn(); } }
  ready(function(){
    var TB = document.createElement('div');
    TB.id = 'mwb-toolbar';
    TB.style.cssText = 'position:fixed;top:10px;left:50%;transform:translateX(-50%);z-index:2147483647;display:none;gap:6px;align-items:center;background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;box-shadow:0 4px 16px rgba(0,0,0,.18);padding:6px 8px;font:13px/1.4 system-ui,sans-serif;color:#0f172a;max-width:90vw;flex-wrap:wrap;';
    function btn(t,fn){ var b=document.createElement('button'); b.textContent=t; b.style.cssText='border:1px solid #e2e8f0;background:#f8fafc;border-radius:6px;padding:4px 8px;cursor:pointer;font:inherit;color:#0f172a;'; b.addEventListener('click',fn); return b; }
    var sel=null;
    function clearSel(){ if(sel){ sel.classList.remove('mwb-sel'); sel.removeAttribute('contenteditable'); sel=null; } }
    function selectEl(el){ clearSel(); sel=el; el.classList.add('mwb-sel'); el.setAttribute('contenteditable','true'); el.focus(); TB.style.display='flex'; }
    document.addEventListener('click', function(e){
      if(e.target.closest('#mwb-toolbar')) return;
      if(e.target.tagName==='A'){ e.preventDefault(); }
      if(sel && sel.contains(e.target)) return;
      e.preventDefault();
      if(e.target===document.body||e.target===document.documentElement){ clearSel(); TB.style.display='none'; return; }
      selectEl(e.target);
    }, true);
    function cmd(c,v){ try{ document.execCommand(c,false,v); }catch(e){} }
    TB.appendChild(btn('B',function(){cmd('bold');}));
    TB.appendChild(btn('I',function(){cmd('italic');}));
    var sw=document.createElement('input'); sw.type='color'; sw.title='Text color'; sw.value='#2563eb'; sw.style.cssText='width:28px;height:28px;border:1px solid #e2e8f0;border-radius:6px;cursor:pointer;background:#fff;';
    sw.addEventListener('change',function(){ cmd('foreColor', sw.value); });
    TB.appendChild(sw);
    TB.appendChild(btn('A+',function(){ if(sel){ var c=parseFloat(getComputedStyle(sel).fontSize)||16; sel.style.fontSize=(c+2)+'px'; } }));
    TB.appendChild(btn('A-',function(){ if(sel){ var c=parseFloat(getComputedStyle(sel).fontSize)||16; sel.style.fontSize=Math.max(8,c-2)+'px'; } }));
    TB.appendChild(btn('Delete',function(){ if(sel){ var p=sel.parentNode; if(p){ p.removeChild(sel); clearSel(); TB.style.display='none'; } } }));
    var apply=btn('Apply',function(){
      var clone=document.documentElement.cloneNode(true);
      function rm(id){ var e=clone.querySelector('#'+id); if(e)e.remove(); }
      rm('mwb-toolbar'); rm('mwb-editor-shim'); rm('mwb-editor-style');
      var csp=clone.querySelector('meta[name="mwb-preview-csp"]'); if(csp)csp.remove();
      clone.querySelectorAll('.mwb-sel').forEach(function(el){ el.classList.remove('mwb-sel'); el.removeAttribute('contenteditable'); });
      post({type:'mwb:edits', nonce: Date.now(), html: '<!doctype html>\\n'+clone.outerHTML});
    });
    apply.style.cssText='border:1px solid #2563eb;background:#2563eb;color:#fff;border-radius:6px;padding:4px 10px;cursor:pointer;font:inherit;font-weight:600;';
    TB.appendChild(apply);
    document.body.appendChild(TB);
  });
})();
<\/script>`;

function buildPreviewDoc(html: string, editing: boolean): string {
  const inject = CSP_META + (editing ? EDITOR_STYLE + EDITOR_SHIM : "");
  const isFullDoc = /^\s*(<!doctype|<html)/i.test(html);

  if (!isFullDoc) {
    // Fragment — wrap in a minimal document
    return (
      "<!doctype html><html><head><meta charset='utf-8'>" + inject +
      "</head><body style='margin:0;padding:0;'>" + html +
      (editing ? "" : "") + "</body></html>"
    );
  }

  // Full document — insert CSP right after the first <head ...> tag
  const headOpenMatch = /<head[^>]*>/i.exec(html);
  if (headOpenMatch && headOpenMatch.index >= 0) {
    const pos = headOpenMatch.index + headOpenMatch[0].length;
    return html.slice(0, pos) + inject + html.slice(pos);
  }

  // No <head> tag at all — try </head> or </body> fallback
  if (/<\/head>/i.test(html)) return html.replace(/<\/head>/i, inject + "</head>");
  if (/<\/body>/i.test(html)) return html.replace(/<\/body>/i, inject + "</body>");
  return inject + html;
}

export default function Preview() {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const code = useStore((s) => s.code);
  const editing = useStore((s) => s.editing);
  const busy = useStore((s) => s.busy);
  const setCodeWithHistory = useStore((s) => s.setCodeWithHistory);

  const doc = useMemo(() => {
    if (!code) return "";
    return buildPreviewDoc(code, editing && !busy);
  }, [code, editing, busy]);

  useEffect(() => {
    const iframe = iframeRef.current;
    if (iframe && doc) iframe.srcdoc = doc;
  }, [doc]);

  // Apply edits posted from the editor shim
  useEffect(() => {
    function onMessage(e: MessageEvent) {
      const data = e.data;
      if (!data || typeof data.type !== "string" || data.type !== "mwb:edits") return;
      setCodeWithHistory(data.html as string);
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [setCodeWithHistory]);

  if (editing && code) {
    return (
      <div className="relative h-full w-full overflow-hidden bg-surface">
        <GrapeJSEditor html={code} onUpdate={(newHtml) => setCodeWithHistory(newHtml)} />

        {/* WYSIWYG editing indicator */}
        <div className="pointer-events-none absolute bottom-4 left-1/2 flex -translate-x-1/2 items-center gap-1.5 rounded-full bg-accent px-4 py-1.5 text-xs font-medium text-white shadow-lg animate-slide-up">
          <MousePointerClick className="h-3.5 w-3.5" />
          GrapeJS Editor — drag components, edit text, style with the right panel
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-full w-full overflow-hidden bg-surface">
      <iframe
        ref={iframeRef}
        title="preview"
        sandbox="allow-scripts allow-forms"
        referrerPolicy="no-referrer"
        className="h-full w-full border-0 bg-white"
      />

      {/* Loading overlay */}
      {busy && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/75 backdrop-blur-sm animate-fade-in">
          <div className="flex flex-col items-center gap-3">
            <Spinner size="lg" className="border-accentSoft border-t-accent" />
            <p className="text-sm font-medium text-accent">Generating your minimalist website…</p>
            <p className="text-xs text-muted2">This usually takes 5–15 seconds</p>
          </div>
        </div>
      )}
    </div>
  );
}