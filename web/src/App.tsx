import { useEffect, useState } from "react";
import { Toaster, toast } from "sonner";
import { Eye, Code2, AlertCircle, Info, Sparkles, ArrowRight, Undo2, Redo2 } from "lucide-react";
import Preview from "./components/Preview";
import CodePanel from "./components/CodePanel";
import Sidebar from "./components/Sidebar";
import ChatPanel from "./components/ChatPanel";
import { useStore } from "./store";
import { cn } from "./lib/utils";
import { Button } from "./components/ui/Button";
import { Textarea } from "./components/ui/Textarea";
import { Spinner } from "./components/ui/Spinner";
import { Badge } from "./components/ui/Badge";

type Tab = "preview" | "code";

export default function App() {
  const loadOptions = useStore((s) => s.loadOptions);
  const code = useStore((s) => s.code);
  const busy = useStore((s) => s.busy);
  const error = useStore((s) => s.error);
  const notes = useStore((s) => s.notes);
  const safetyAlerts = useStore((s) => s.safetyAlerts);
  const runGenerate = useStore((s) => s.runGenerate);
  const constraintMode = useStore((s) => s.constraintMode);
  const runConstraints = useStore((s) => s.runConstraints);
  const undoStack = useStore((s) => s.undoStack);
  const redoStack = useStore((s) => s.redoStack);
  const undo = useStore((s) => s.undo);
  const redo = useStore((s) => s.redo);
  const [tab, setTab] = useState<Tab>("preview");
  const [prompt, setPrompt] = useState("");
  const [showChat, setShowChat] = useState(true);

  useEffect(() => { loadOptions(); }, [loadOptions]);
  useEffect(() => { if (safetyAlerts.length) toast.warning("Safety: " + safetyAlerts.join(", ")); }, [safetyAlerts]); // eslint-disable-line
  useEffect(() => { if (error) toast.error(error); }, [error]); // eslint-disable-line
  useEffect(() => { if (code && !busy) { toast.success("Page generated"); setTab("preview"); } }, [code, busy]); // eslint-disable-line

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "z") {
        e.preventDefault();
        if (e.shiftKey) {
          redo();
        } else {
          undo();
        }
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [undo, redo]);

  function submit() {
    const p = prompt.trim();
    if (!p || busy) return;
    setPrompt("");
    runGenerate(p);
  }

  const status = busy ? "generating" : error ? "error" : code ? "ready" : "idle";

  return (
    <div className="flex h-full w-full bg-bg text-text2">
      <Sidebar />

      <main className="flex min-w-0 flex-1 flex-col">
        {/* Toolbar */}
        <header className="flex shrink-0 items-center justify-between border-b border-border2 bg-surface px-4 py-2">
          <div className="flex items-center gap-1">
            <ToolbarTab icon={<Eye className="h-4 w-4" />} label="Preview" active={tab === "preview"} onClick={() => setTab("preview")} />
            <ToolbarTab icon={<Code2 className="h-4 w-4" />} label="Code" active={tab === "code"} onClick={() => setTab("code")} />
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={undo}
              disabled={undoStack.length === 0}
              className={cn(
                "rounded-lg p-1.5 transition-colors",
                undoStack.length === 0 ? "text-muted2/40" : "text-muted2 hover:bg-bg hover:text-text2"
              )}
              title="Undo (Ctrl+Z)"
            >
              <Undo2 className="h-4 w-4" />
            </button>
            <button
              onClick={redo}
              disabled={redoStack.length === 0}
              className={cn(
                "rounded-lg p-1.5 transition-colors",
                redoStack.length === 0 ? "text-muted2/40" : "text-muted2 hover:bg-bg hover:text-text2"
              )}
              title="Redo (Ctrl+Shift+Z)"
            >
              <Redo2 className="h-4 w-4" />
            </button>
            <StatusIndicator status={status} />
            <button
              onClick={() => setShowChat(!showChat)}
              className={cn(
                "rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors",
                showChat ? "bg-accentSoft text-accent" : "text-muted2 hover:bg-bg"
              )}
            >
              Chat
            </button>
          </div>
        </header>

        {/* Inline alerts */}
        {(safetyAlerts.length > 0 || notes.length > 0) && (
          <div className="flex flex-col gap-1 border-b border-border2 bg-surface px-4 py-1.5">
            {safetyAlerts.map((a, i) => (
              <div key={`s${i}`} className="flex items-center gap-1.5 text-xs text-warning">
                <AlertCircle className="h-3.5 w-3.5 shrink-0" /> <span className="truncate">{a}</span>
              </div>
            ))}
            {notes.slice(0, 3).map((n, i) => (
              <div key={`n${i}`} className="flex items-center gap-1.5 text-xs text-muted">
                <Info className="h-3.5 w-3.5 shrink-0" /> <span className="truncate">{n}</span>
              </div>
            ))}
          </div>
        )}

        {/* Content */}
        <div className="min-h-0 flex-1 overflow-hidden">
          {tab === "preview" ? (
            code ? <Preview /> : <EmptyState prompt={prompt} setPrompt={setPrompt} busy={busy} onSubmit={submit} constraintMode={constraintMode} onConstraints={runConstraints} />
          ) : (
            <CodePanel />
          )}
        </div>

        {/* Chat panel */}
        {showChat && (
          <div className="h-72 shrink-0 border-t border-border2">
            <ChatPanel />
          </div>
        )}

        <Toaster position="bottom-right" richColors closeButton />
      </main>
    </div>
  );
}

function ToolbarTab({ icon, label, active, onClick }: { icon: React.ReactNode; label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
        active ? "bg-accentSoft text-accent" : "text-muted hover:bg-bg hover:text-text2"
      )}
    >
      {icon}
      {label}
    </button>
  );
}

function StatusIndicator({ status }: { status: string }) {
  const cfg: Record<string, { color: string; dot: string; label: string }> = {
    idle: { color: "text-muted2", dot: "bg-muted2", label: "Idle" },
    generating: { color: "text-accent", dot: "bg-accent animate-pulse", label: "Generating" },
    ready: { color: "text-success", dot: "bg-success", label: "Ready" },
    error: { color: "text-danger", dot: "bg-danger", label: "Error" },
  };
  const c = cfg[status] ?? cfg.idle;
  return (
    <div className="flex items-center gap-2">
      <Badge variant={status === "ready" ? "success" : status === "error" ? "danger" : status === "generating" ? "default" : "muted"}>
        <span className={cn("h-1.5 w-1.5 rounded-full", c.dot)} />
        {c.label}
      </Badge>
    </div>
  );
}

function EmptyState({
  prompt, setPrompt, busy, onSubmit, constraintMode, onConstraints,
}: {
  prompt: string; setPrompt: (v: string) => void; busy: boolean; onSubmit: () => void; constraintMode: boolean; onConstraints: () => void;
}) {
  const examples = [
    "A minimal landing page for a coffee shop called Fern — hero, three feature cards, footer",
    "A personal portfolio with an about section, project grid, and contact links",
    "A simple blog homepage with a featured post and recent posts list",
  ];
  return (
    <div className="flex h-full flex-col items-center justify-center gap-6 overflow-y-auto px-8 py-12 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-accentSoft text-accent">
        <Sparkles className="h-8 w-8" />
      </div>
      <div className="space-y-1">
        <h2 className="text-xl font-semibold">Start your creative journey</h2>
        <p className="max-w-md text-sm text-muted">Describe your dream website and watch it come to life. Or pick a starting point:</p>
      </div>
      <div className="flex flex-col gap-2">
        {examples.map((ex, i) => (
          <button
            key={i}
            onClick={() => setPrompt(ex)}
            className="group flex items-center gap-2 rounded-lg border border-border2 bg-surface px-4 py-2.5 text-left text-sm text-muted transition-all hover:border-accent hover:text-accent hover:shadow-sm"
          >
            <span className="flex-1">{ex}</span>
            <ArrowRight className="h-3.5 w-3.5 shrink-0 opacity-0 transition-opacity group-hover:opacity-100" />
          </button>
        ))}
      </div>
      <div className="flex w-full max-w-xl items-end gap-2">
        <Textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onSubmit(); } }}
          placeholder="Describe the website you want to create…"
          rows={2}
          className="min-h-[52px] flex-1"
        />
        <Button size="lg" onClick={onSubmit} disabled={busy || !prompt.trim()} className="h-[52px]">
          {busy ? <Spinner size="sm" className="border-white/30 border-t-white" /> : null}
          Generate
        </Button>
      </div>
      {constraintMode && (
        <button onClick={onConstraints} disabled={busy} className="text-sm text-accent hover:underline">
          Or generate from your constraint selections →
        </button>
      )}
    </div>
  );
}