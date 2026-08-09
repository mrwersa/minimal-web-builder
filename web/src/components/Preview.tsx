import { lazy, Suspense, useMemo } from "react";
import { useStore } from "../store";
import { Spinner } from "./ui/Spinner";

const EditorWorkspace = lazy(() => import("./editor/EditorWorkspace"));

const CSP = (
  "default-src 'none'; img-src data: blob:; style-src 'unsafe-inline'; " +
  "script-src 'unsafe-inline'; font-src data:; connect-src 'none'; " +
  "frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none';"
);
const CSP_META = `<meta name="mwb-preview-csp" http-equiv="Content-Security-Policy" content="${CSP}">`;

function buildPreviewDoc(html: string): string {
  const inject = CSP_META;
  const isFullDoc = /^\s*(<!doctype|<html)/i.test(html);

  if (!isFullDoc) {
    // Fragment — wrap in a minimal document
    return (
      "<!doctype html><html><head><meta charset='utf-8'>" + inject +
      "</head><body style='margin:0;padding:0;'>" + html + "</body></html>"
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
  const code = useStore((s) => s.code);
  const editorDocument = useStore((s) => s.editorDocument);
  const editing = useStore((s) => s.editing);
  const busy = useStore((s) => s.busy);

  const doc = useMemo(() => {
    if (!code) return "";
    return buildPreviewDoc(code);
  }, [code]);

  if (editing && editorDocument && !busy) {
    return (
      <div className="relative h-full w-full overflow-hidden bg-surface">
        <Suspense fallback={<div className="flex h-full items-center justify-center"><Spinner size="lg" /></div>}>
          <EditorWorkspace document={editorDocument} />
        </Suspense>
      </div>
    );
  }

  return (
    <div className="relative h-full w-full overflow-hidden bg-surface">
      <iframe
        title="preview"
        srcDoc={doc}
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
