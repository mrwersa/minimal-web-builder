import { useEffect, useState } from "react";
import Preview from "./components/Preview";
import CodePanel from "./components/CodePanel";
import Sidebar from "./components/Sidebar";
import { useStore } from "./store";

type Tab = "preview" | "code";

export default function App() {
  const loadOptions = useStore((s) => s.loadOptions);
  const code = useStore((s) => s.code);
  const busy = useStore((s) => s.busy);
  const runGenerate = useStore((s) => s.runGenerate);
  const notes = useStore((s) => s.notes);
  const safetyAlerts = useStore((s) => s.safetyAlerts);
  const [tab, setTab] = useState<Tab>("preview");
  const [prompt, setPrompt] = useState("");

  useEffect(() => {
    loadOptions();
  }, [loadOptions]);

  function submit() {
    const p = prompt.trim();
    if (!p || busy) return;
    setPrompt("");
    setTab("preview");
    runGenerate(p);
  }

  return (
    <div className="flex h-full w-full">
      <Sidebar />
      <main className="flex min-w-0 flex-1 flex-col bg-bg">
        {/* top bar */}
        <header className="flex items-center justify-between border-b border-border2 bg-surface px-4 py-2.5">
          <div className="flex items-center gap-2">
            {(["preview", "code"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={
                  "rounded-lg px-3 py-1.5 text-sm font-medium capitalize " +
                  (tab === t ? "bg-accentSoft text-accent" : "text-muted hover:text-text2")
                }
              >
                {t}
              </button>
            ))}
          </div>
          <div className="text-xs text-muted">
            {code ? "Page ready" : "Describe a website to begin"}
          </div>
        </header>

        {/* notices */}
        {(safetyAlerts.length > 0 || notes.length > 0) && (
          <div className="space-y-1.5 border-b border-border2 bg-surface px-4 py-2">
            {safetyAlerts.map((a, i) => (
              <div key={`s${i}`} className="text-xs text-amber-700">⚠ {a}</div>
            ))}
            {notes.slice(0, 3).map((n, i) => (
              <div key={`n${i}`} className="text-xs text-muted">• {n}</div>
            ))}
          </div>
        )}

        {/* content */}
        <div className="min-h-0 flex-1">
          {tab === "preview" ? (
            code ? (
              <Preview />
            ) : (
              <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
                <div className="text-5xl">🧩</div>
                <div className="text-lg font-medium text-text2">Start your creative journey!</div>
                <div className="max-w-md text-sm text-muted">
                  Describe your dream website below and watch it come to life.
                </div>
              </div>
            )
          ) : (
            <CodePanel />
          )}
        </div>

        {/* chat input */}
        <div className="border-t border-border2 bg-surface px-4 py-3">
          <div className="flex items-end gap-2">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  submit();
                }
              }}
              placeholder={busy ? "Generating… please wait." : "Describe the website you want to create…"}
              disabled={busy}
              rows={1}
              className="max-h-40 min-h-[44px] flex-1 resize-none rounded-2xl border border-border2 bg-surface px-4 py-2.5 text-sm text-text2 placeholder:text-muted focus:border-accent focus:outline-none disabled:opacity-60"
            />
            <button
              onClick={submit}
              disabled={busy || !prompt.trim()}
              className="rounded-2xl bg-accent px-5 py-2.5 text-sm font-medium text-white hover:bg-accent/90 disabled:opacity-50"
            >
              {busy ? "…" : "Generate"}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}