import { useCallback, useEffect, useRef } from "react";
import grapesjs, { type Component, type Editor } from "grapesjs";
import "grapesjs/dist/css/grapes.min.css";
import {
  compileCanvas,
  compileDesignTokenCss,
  compileDocument,
  compileResponsiveCss,
  replaceCanvas,
  type EditorDocumentV1,
} from "../editor/document";

interface GrapeJSEditorProps {
  document: EditorDocumentV1;
  selectedNodeId: string | null;
  onSelect: (nodeId: string) => void;
  onUpdate: (document: EditorDocumentV1) => void;
}

function componentNodeId(component: Component | null | undefined): string | null {
  const value = component?.getAttributes()?.["data-mwb-id"];
  return typeof value === "string" ? value : null;
}

function findComponent(component: Component, nodeId: string): Component | null {
  if (componentNodeId(component) === nodeId) return component;
  for (const child of component.components().models) {
    const match = findComponent(child, nodeId);
    if (match) return match;
  }
  return null;
}

function syncManagedStyles(editor: Editor, document: EditorDocumentV1): void {
  const canvasDocument = editor.Canvas.getDocument();
  if (!canvasDocument) return;
  for (const [name, css] of [
    ["tokens", compileDesignTokenCss(document)],
    ["responsive", compileResponsiveCss(document)],
  ]) {
    let style = canvasDocument.querySelector<HTMLStyleElement>(
      `style[data-mwb-${name}]`,
    );
    if (!style) {
      style = canvasDocument.createElement("style");
      style.setAttribute(`data-mwb-${name}`, "true");
      canvasDocument.head.append(style);
    }
    style.textContent = css;
  }
}

export default function GrapeJSEditor({
  document,
  selectedNodeId,
  onSelect,
  onUpdate,
}: GrapeJSEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const editorRef = useRef<Editor | null>(null);
  const documentRef = useRef<EditorDocumentV1 | null>(null);
  const loadingRef = useRef(false);
  const updateTimerRef = useRef<number | null>(null);
  const lastEmittedRef = useRef("");
  const onUpdateRef = useRef(onUpdate);
  onUpdateRef.current = onUpdate;
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

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
    const handleSelection = (component: Component) => {
      const nodeId = componentNodeId(component);
      if (nodeId) onSelectRef.current(nodeId);
    };
    editor.on("component:selected", handleSelection);
    const handleFrameLoad = () => {
      if (documentRef.current) syncManagedStyles(editor, documentRef.current);
    };
    editor.on("canvas:frame:load", handleFrameLoad);

    return () => {
      if (updateTimerRef.current !== null) window.clearTimeout(updateTimerRef.current);
      editor.off("update", scheduleUpdate);
      editor.off("component:selected", handleSelection);
      editor.off("canvas:frame:load", handleFrameLoad);
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
    editor.setStyle(document.css);
    // Load shared CSS before components so GrapesJS can register inline styles
    // without the subsequent stylesheet reset discarding them.
    editor.setComponents(compileCanvas(document));
    syncManagedStyles(editor, document);
    // GrapesJS normalizes markup while loading. Treat that normalized document as
    // the baseline so merely opening the editor does not create a revision.
    lastEmittedRef.current = compileDocument(
      replaceCanvas(document, editor.getHtml(), editor.getCss() ?? ""),
    );
    loadingRef.current = false;
  }, [document]);

  useEffect(() => {
    const editor = editorRef.current;
    const wrapper = editor?.getWrapper();
    if (!editor || !wrapper || !selectedNodeId) return;
    if (componentNodeId(editor.getSelected()) === selectedNodeId) return;
    const component = findComponent(wrapper, selectedNodeId);
    if (component) editor.select(component);
  }, [selectedNodeId, document]);

  return <div ref={containerRef} className="h-full w-full" />;
}
