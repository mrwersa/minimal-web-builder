import { useMemo } from "react";
import { useStore } from "../store";

const CSP =
  "default-src 'none'; img-src data: blob:; style-src 'unsafe-inline'; " +
  "script-src 'unsafe-inline'; font-src data:; connect-src 'none'; " +
  "frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none';";
const CSP_META = `<meta name="mwb-preview-csp" http-equiv="Content-Security-Policy" content="${CSP}">`;

export function buildPreviewDoc(html: string): string {
  const inject = CSP_META;
  const isFullDoc = /^\s*(<!doctype|<html)/i.test(html);

  if (!isFullDoc) {
    return (
      "<!doctype html><html><head><meta charset='utf-8'>" +
      inject +
      "</head><body style='margin:0;padding:0;'>" +
      html +
      "</body></html>"
    );
  }

  const headOpenMatch = /<head[^>]*>/i.exec(html);
  if (headOpenMatch && headOpenMatch.index >= 0) {
    const pos = headOpenMatch.index + headOpenMatch[0].length;
    return html.slice(0, pos) + inject + html.slice(pos);
  }

  if (/<\/head>/i.test(html)) return html.replace(/<\/head>/i, inject + "</head>");
  if (/<\/body>/i.test(html)) return html.replace(/<\/body>/i, inject + "</body>");
  return inject + html;
}

/** The sandboxed render of the current page. */
export default function Preview() {
  const code = useStore((state) => state.code);
  const doc = useMemo(() => (code ? buildPreviewDoc(code) : ""), [code]);

  return (
    <iframe
      title="preview"
      srcDoc={doc}
      sandbox="allow-scripts allow-forms"
      referrerPolicy="no-referrer"
      className="h-full w-full border-0 bg-white"
    />
  );
}
