import { useCallback, useEffect, useRef } from "react";
import grapesjs, { type Editor } from "grapesjs";
import "grapesjs/dist/css/grapes.min.css";

interface GrapeJSEditorProps {
  html: string;
  onUpdate: (html: string) => void;
}

export interface DocumentParts {
  doctype: string;
  htmlAttributes: string;
  headHtml: string;
  bodyAttributes: string;
  bodyHtml: string;
  bodyScripts: string[];
  css: string;
}

function serializeAttributes(element: Element): string {
  return Array.from(element.attributes)
    .map(({ name, value }) => ` ${name}="${value.replaceAll("&", "&amp;").replaceAll('"', "&quot;")}"`)
    .join("");
}

/** Split a complete document into canvas-editable and preserved parts. */
export function parseDocument(html: string): DocumentParts {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, "text/html");
  const head = doc.head.cloneNode(true) as HTMLHeadElement;
  const body = doc.body.cloneNode(true) as HTMLBodyElement;
  const css = Array.from(doc.querySelectorAll("style"))
    .map((style) => style.textContent ?? "")
    .filter(Boolean)
    .join("\n\n");
  const bodyScripts = Array.from(body.querySelectorAll("script")).map((script) => script.outerHTML);

  head.querySelectorAll("style").forEach((style) => style.remove());
  body.querySelectorAll("style, script").forEach((element) => element.remove());

  return {
    doctype: html.match(/<!doctype[^>]*>/i)?.[0] ?? "<!DOCTYPE html>",
    htmlAttributes: serializeAttributes(doc.documentElement),
    headHtml: head.innerHTML.trim(),
    bodyAttributes: serializeAttributes(doc.body),
    bodyHtml: body.innerHTML.trim(),
    bodyScripts,
    css,
  };
}

/** Rebuild the complete export document without dropping metadata or scripts. */
export function buildDocument(parts: DocumentParts, bodyHtml: string, css: string): string {
  const headItems = [parts.headHtml, css.trim() ? `<style>\n${css.trim()}\n</style>` : ""].filter(Boolean);
  const bodyItems = [bodyHtml.trim(), ...parts.bodyScripts].filter(Boolean);
  return [
    parts.doctype,
    `<html${parts.htmlAttributes}>`,
    "<head>",
    headItems.join("\n"),
    "</head>",
    `<body${parts.bodyAttributes}>`,
    bodyItems.join("\n"),
    "</body>",
    "</html>",
  ].join("\n");
}

export default function GrapeJSEditor({ html, onUpdate }: GrapeJSEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const editorRef = useRef<Editor | null>(null);
  const documentPartsRef = useRef<DocumentParts | null>(null);
  const loadingRef = useRef(false);
  const updateTimerRef = useRef<number | null>(null);
  const lastEmittedRef = useRef("");
  const onUpdateRef = useRef(onUpdate);
  onUpdateRef.current = onUpdate;

  const emitUpdate = useCallback(() => {
    const editor = editorRef.current;
    const parts = documentPartsRef.current;
    if (!editor || !parts || loadingRef.current) return;
    const nextDocument = buildDocument(parts, editor.getHtml(), editor.getCss() ?? "");
    if (nextDocument === lastEmittedRef.current) return;
    lastEmittedRef.current = nextDocument;
    onUpdateRef.current(nextDocument);
  }, []);

  const scheduleUpdate = useCallback(() => {
    if (loadingRef.current) return;
    if (updateTimerRef.current !== null) window.clearTimeout(updateTimerRef.current);
    updateTimerRef.current = window.setTimeout(emitUpdate, 500);
  }, [emitUpdate]);

  useEffect(() => {
    if (!containerRef.current || editorRef.current) return;

    const editor = grapesjs.init({
      container: containerRef.current,
      height: "100%",
      storageManager: false,
      panels: { defaults: [] },
    });

    editorRef.current = editor;
    editor.on("update", scheduleUpdate);

    return () => {
      if (updateTimerRef.current !== null) window.clearTimeout(updateTimerRef.current);
      editor.off("update", scheduleUpdate);
      editor.destroy();
      editorRef.current = null;
    };
  }, [scheduleUpdate]);

  useEffect(() => {
    const editor = editorRef.current;
    if (!editor || !html || html === lastEmittedRef.current) return;

    const parts = parseDocument(html);
    loadingRef.current = true;
    documentPartsRef.current = parts;
    editor.DomComponents.clear();
    editor.CssComposer.clear();
    editor.setComponents(parts.bodyHtml);
    editor.setStyle(parts.css);
    // GrapesJS normalizes markup while loading. Treat that normalized document as
    // the baseline so merely opening the editor does not create a revision.
    lastEmittedRef.current = buildDocument(parts, editor.getHtml(), editor.getCss() ?? "");
    loadingRef.current = false;
  }, [html]);

  return <div ref={containerRef} className="h-full w-full" />;
}
