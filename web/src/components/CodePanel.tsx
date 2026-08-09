import { useEffect, useState } from "react";
import {
  Download,
  FileCode2,
  FileText,
  FileType2,
  SlidersHorizontal,
} from "lucide-react";
import { exportPage } from "../api";
import { compileDocument } from "../editor/document";
import { useStore } from "../store";
import { Button } from "./ui/button";
import AdvancedCodePanel from "./editor/AdvancedCodePanel";

export default function CodePanel() {
  const code = useStore((s) => s.code);
  const editorDocument = useStore((s) => s.editorDocument);
  const setDocumentWithHistory = useStore((s) => s.setDocumentWithHistory);
  const portableCode = editorDocument
    ? compileDocument(editorDocument, { includeEditorIds: false })
    : code;
  const [mode, setMode] = useState<"single" | "split">("single");
  const [view, setView] = useState<"output" | "advanced">("output");
  const [files, setFiles] = useState<Record<string, string> | null>(null);

  useEffect(() => setFiles(null), [portableCode, mode]);

  if (!code) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
        <FileCode2 className="h-10 w-10 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">No code generated yet.</p>
      </div>
    );
  }

  async function runExport() {
    if (!portableCode) return;
    const res = await exportPage(portableCode, mode);
    setFiles(res.files);
  }

  function download(name: string, content: string) {
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    URL.revokeObjectURL(url);
  }

  const fileIcons: Record<string, React.ReactNode> = {
    "index.html": <FileText className="h-3.5 w-3.5" />,
    "styles.css": <FileCode2 className="h-3.5 w-3.5" />,
    "app.js": <FileType2 className="h-3.5 w-3.5" />,
  };

  return (
    <div className="flex h-full flex-col overflow-hidden p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div
          className="flex rounded-lg border border-border p-0.5"
          aria-label="Code view"
        >
          {(["output", "advanced"] as const).map((value) => (
            <button
              key={value}
              onClick={() => setView(value)}
              className={
                view === value
                  ? "rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground"
                  : "rounded-md px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
              }
            >
              {value === "output" ? (
                <span className="flex items-center gap-1.5">
                  <FileCode2 className="h-3.5 w-3.5" /> Compiled output
                </span>
              ) : (
                <span className="flex items-center gap-1.5">
                  <SlidersHorizontal className="h-3.5 w-3.5" /> Advanced
                </span>
              )}
            </button>
          ))}
        </div>
        {view === "output" && (
          <div className="flex items-center gap-3">
            <div className="flex rounded-lg border border-border p-0.5">
              {(["single", "split"] as const).map((value) => (
                <button
                  key={value}
                  onClick={() => setMode(value)}
                  className={
                    mode === value
                      ? "rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground"
                      : "rounded-md px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
                  }
                >
                  {value === "single" ? "Single HTML" : "Split"}
                </button>
              ))}
            </div>
            <Button variant="outline" onClick={runExport} className="gap-1.5">
              <Download className="h-3.5 w-3.5" />
              Prepare export
            </Button>
          </div>
        )}
      </div>

      {view === "advanced" && editorDocument ? (
        <AdvancedCodePanel
          document={editorDocument}
          onChange={setDocumentWithHistory}
        />
      ) : (
        <>
          {files && (
            <div className="mb-3 flex flex-wrap gap-2">
              {Object.keys(files).map((name) => (
                <button
                  key={name}
                  onClick={() => download(name, files[name])}
                  className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs text-foreground transition-colors hover:border-primary hover:text-primary"
                >
                  {fileIcons[name] ?? <Download className="h-3.5 w-3.5" />}
                  {name}
                </button>
              ))}
            </div>
          )}

          <pre className="code flex-1 overflow-auto rounded-xl border border-border bg-surface p-4 text-foreground">
            {portableCode}
          </pre>
        </>
      )}
    </div>
  );
}
