import { useEffect, useRef } from "react";
import { fetchPreviewDoc } from "../api";
import { useStore } from "../store";

export default function Preview() {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const code = useStore((s) => s.code);
  const editing = useStore((s) => s.editing);
  const busy = useStore((s) => s.busy);
  const set = useStore((s) => s.set);

  // Apply edits posted from the editor shim inside the sandboxed preview.
  useEffect(() => {
    function onMessage(e: MessageEvent) {
      const data = e.data;
      if (!data || typeof data.type !== "string" || data.type !== "mwb:edits") return;
      set("code", data.html as string);
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [set]);

  // Build the sandboxed preview document server-side and load it into the iframe.
  useEffect(() => {
    let cancelled = false;
    const html = code ?? "";
    if (!html) return;
    fetchPreviewDoc(html, editing && !busy)
      .then((doc) => {
        if (cancelled) return;
        const iframe = iframeRef.current;
        if (iframe) iframe.srcdoc = doc;
      })
      .catch(() => {
        /* ignore */
      });
    return () => {
      cancelled = true;
    };
  }, [code, editing, busy]);

  return (
    <div className="relative h-full w-full">
      <iframe
        ref={iframeRef}
        title="preview"
        sandbox="allow-scripts allow-forms"
        referrerPolicy="no-referrer"
        className="h-full w-full border-0 bg-white"
      />
      {busy && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/70 backdrop-blur-sm">
          <div className="flex flex-col items-center gap-3">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-accent border-t-transparent" />
            <div className="text-sm font-medium text-accent">Generating your minimalist website…</div>
          </div>
        </div>
      )}
      {editing && !busy && code && (
        <div className="pointer-events-none absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full bg-accent/90 px-3 py-1 text-xs font-medium text-white shadow">
          Editing mode — click an element, edit it, then press Apply
        </div>
      )}
    </div>
  );
}