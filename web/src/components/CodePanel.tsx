import { useState } from "react";
import { exportPage } from "../api";
import { useStore } from "../store";

export default function CodePanel() {
  const code = useStore((s) => s.code);
  const [mode, setMode] = useState<"single" | "split">("single");
  const [files, setFiles] = useState<Record<string, string> | null>(null);

  if (!code) {
    return <div className="p-6 text-sm text-muted">No code generated yet.</div>;
  }

  async function runExport() {
    if (!code) return;
    const res = await exportPage(code, mode);
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

  return (
    <div className="flex h-full flex-col overflow-y-auto p-4">
      <div className="mb-4 flex items-center gap-3">
        <div className="flex rounded-lg border border-border2 p-0.5">
          {(["single", "split"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={
                "rounded-md px-3 py-1.5 text-sm " +
                (mode === m ? "bg-accent text-white" : "text-muted hover:text-text2")
              }
            >
              {m === "single" ? "Single HTML" : "Split"}
            </button>
          ))}
        </div>
        <button
          onClick={runExport}
          className="rounded-lg bg-accentSoft px-3 py-1.5 text-sm font-medium text-accent hover:bg-accent hover:text-white"
        >
          Prepare export
        </button>
      </div>

      {files && (
        <div className="mb-4 flex flex-wrap gap-2">
          {Object.keys(files).map((name) => (
            <button
              key={name}
              onClick={() => download(name, files[name])}
              className="rounded-lg border border-border2 px-3 py-1.5 text-xs hover:bg-bg"
            >
              ⬇ {name}
            </button>
          ))}
        </div>
      )}

      <pre className="code rounded-lg border border-border2 bg-surface p-4 text-text2">
        {code}
      </pre>
    </div>
  );
}