import { useCallback, useEffect, useRef } from "react";
import grapesjs, { type Editor } from "grapesjs";
import "grapesjs/dist/css/grapes.min.css";
import {
  compileCanvas,
  compileDocument,
  replaceCanvas,
  type EditorDocumentV1,
} from "../editor/document";

interface GrapeJSEditorProps {
  document: EditorDocumentV1;
  onUpdate: (document: EditorDocumentV1) => void;
}

export default function GrapeJSEditor({ document, onUpdate }: GrapeJSEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const editorRef = useRef<Editor | null>(null);
  const documentRef = useRef<EditorDocumentV1 | null>(null);
  const loadingRef = useRef(false);
  const updateTimerRef = useRef<number | null>(null);
  const lastEmittedRef = useRef("");
  const onUpdateRef = useRef(onUpdate);
  onUpdateRef.current = onUpdate;

  const emitUpdate = useCallback(() => {
    const editor = editorRef.current;
    const document = documentRef.current;
    if (!editor || !document || loadingRef.current) return;
    const nextDocument = replaceCanvas(document, editor.getHtml(), editor.getCss() ?? "");
    const nextHtml = compileDocument(nextDocument);
    if (nextHtml === lastEmittedRef.current) return;
    documentRef.current = nextDocument;
    lastEmittedRef.current = nextHtml;
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
    const html = compileDocument(document);
    if (!editor || html === lastEmittedRef.current) return;

    loadingRef.current = true;
    documentRef.current = document;
    editor.DomComponents.clear();
    editor.CssComposer.clear();
    editor.setComponents(compileCanvas(document));
    editor.setStyle(document.css);
    // GrapesJS normalizes markup while loading. Treat that normalized document as
    // the baseline so merely opening the editor does not create a revision.
    lastEmittedRef.current = compileDocument(
      replaceCanvas(document, editor.getHtml(), editor.getCss() ?? ""),
    );
    loadingRef.current = false;
  }, [document]);

  return <div ref={containerRef} className="h-full w-full" />;
}
