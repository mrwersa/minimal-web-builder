import { useEffect, useRef, useCallback } from "react";
import grapesjs from "grapesjs";
import "grapesjs/dist/css/grapes.min.css";

interface GrapeJSEditorProps {
  html: string;
  onUpdate: (html: string) => void;
}

export default function GrapeJSEditor({ html, onUpdate }: GrapeJSEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const editorRef = useRef<any>(null);
  const onUpdateRef = useRef(onUpdate);
  onUpdateRef.current = onUpdate;

  const handleUpdate = useCallback(() => {
    const editor = editorRef.current;
    if (!editor) return;
    const fullHtml = editor.getHtml();
    const css = editor.getCss();
    const fullDoc = `<!DOCTYPE html>\n<html>\n<head>\n<meta charset="utf-8">\n<style>\n${css}\n</style>\n</head>\n<body>\n${fullHtml}\n</body>\n</html>`;
    onUpdateRef.current(fullDoc);
  }, []);

  useEffect(() => {
    if (!containerRef.current || editorRef.current) return;

    const editor = grapesjs.init({
      container: containerRef.current,
      height: "100%",
      storageManager: false,
      panels: { defaults: [] },
    });

    editorRef.current = editor;

    editor.on("component:update", handleUpdate);
    editor.on("style:update", handleUpdate);

    return () => {
      editor.off("component:update", handleUpdate);
      editor.off("style:update", handleUpdate);
      editor.destroy();
      editorRef.current = null;
    };
  }, [handleUpdate]);

  useEffect(() => {
    const editor = editorRef.current;
    if (!editor || !html) return;

    const currentHtml = editor.getHtml();
    if (currentHtml !== html) {
      editor.DomComponents.clear();
      editor.CssComposer.clear();
      editor.setComponents(html);
    }
  }, [html]);

  return (
    <div ref={containerRef} className="h-full w-full" />
  );
}
