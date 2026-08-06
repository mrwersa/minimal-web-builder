import { useEffect, useState } from "react";
import { Toaster, toast } from "sonner";
import { Eye, Code2, Loader2, AlertCircle, Info } from "lucide-react";
import Preview from "./components/Preview";
import CodePanel from "./components/CodePanel";
import Sidebar from "./components/Sidebar";
import { useStore } from "./store";
import { cn } from "./lib/utils";

type Tab = "preview" | "code";

export default function App() {
  const loadOptions = useStore((s) => s.loadOptions);
  const code = useStore((s) => s.code);
  const busy = useStore((s) => s.busy);
  const error = useStore((s) => s.error);
  const notes = useStore((s) => s.notes);
  const safetyAlerts = useStore((s) => s.safetyAlerts);
  const runGenerate = useStore((s) => s.runGenerate);
  const runConstraints = useStore((s) => s.runConstraints);
  const constraintMode = useStore((s) => s.constraintMode);
  const [tab, setTab] = useState<Tab>("preview");
  const [prompt, setPrompt] = useState("");

  useEffect(() => {
    loadOptions();
  }, [loadOptions]);

  // Toast on state changes
  useEffect(() => {
    if (safetyAlerts.length > 0) toast.warning("Safety policy applied: " + safetyAlerts.join(", "));
  }, [safetyAlerts]); // eslint-disable-line

  useEffect(() => {
    if (error) toast.error(error);
  }, [error]); // eslint-disable-line

  useEffect(() => {
    if (code && !busy) {
      toast.success("Page generated successfully");
      setTab("preview");
    }
  }, [code, busy]); // eslint-disable-line

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
        <header className="flex items-center justify-between border-b border-border2 bg-surface px-4 py-2">
          <div className="flex items-center gap-1">
            {(["preview", "code"] as const).map((t) => {
              const Icon = t === "preview" ? Eye : Code2;
              const label = t.charAt(0).toUpperCase() + t.slice(1);
              return (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={cn(
                    "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                    tab === t
                      ? "bg-accentSoft text-accent"
                      : "text-muted hover:bg-bg hover:text-text2"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </button>
              );
            })}
          </div>
          <div className="flex items-center gap-2 text-xs">
            <StatusIndicator status={status} />
          </div>
        </header>

        {/* Inline alerts (safety/notes) */}
        {(safetyAlerts.length > 0 || notes.length > 0) && (
          <div className="flex flex-col gap-1 border-b border-border2 bg-surface px-4 py-2">
            {safetyAlerts.map((a, i) => (
              <AlertBanner key={`s${i}`} icon={<AlertCircle className="h-3.5 w-3.5" />} color="warning" text={a} />
            ))}
            {notes.slice(0, 3).map((n, i) => (
              <AlertBanner key={`n${i}`} icon={<Info className="h-3.5 w-3.5" />} color="muted" text={n} />
            ))}
          </div>
        )}

        {/* Content */}
        <div className="min-h-0 flex-1 overflow-hidden">
          {tab === "preview" ? (
            code ? (
              <Preview />
            ) : (
              <EmptyState onExample={(ex) => setPrompt(ex)} prompt={prompt} setPrompt={setPrompt} busy={busy} onSubmit={submit} constraintMode={constraintMode} onGenerateConstraints={runConstraints} />
            )
          ) : (
            <CodePanel />
          )}
        </div>

        {/* Chat input bar */}
        {code || tab === "preview" ? (
          <ChatInput
            value={prompt}
            onChange={setPrompt}
            onSubmit={submit}
            disabled={busy}
            placeholder={busy ? "Generating… please wait" : "Describe a website or refinement…"}
          />
        ) : null}

        <Toaster position="bottom-right" richColors closeButton />
      </main>
    </div>
  );
}

function StatusIndicator({ status }: { status: string }) {
  const cfg = {
    idle: { color: "text-muted2", dot: "bg-muted2", label: "Idle" },
    generating: { color: "text-accent", dot: "bg-accent animate-pulse", label: "Generating…" },
    ready: { color: "text-success", dot: "bg-success", label: "Ready" },
    error: { color: "text-danger", dot: "bg-danger", label: "Error" },
  } as const;
  const c = cfg[status as keyof typeof cfg] ?? cfg.idle;
  return (
    <div className={cn("flex items-center gap-1.5", c.color)}>
      <span className={cn("h-1.5 w-1.5 rounded-full", c.dot)} />
      {c.label}
    </div>
  );
}

function AlertBanner({ icon, color, text }: { icon: React.ReactNode; color: "warning" | "muted"; text: string }) {
  return (
    <div
      className={cn(
        "flex items-center gap-1.5 text-xs",
        color === "warning" ? "text-warning" : "text-muted"
      )}
    >
      {icon}
      <span className="truncate">{text}</span>
    </div>
  );
}

function ChatInput({
  value,
  onChange,
  onSubmit,
  disabled,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  placeholder: string;
}) {
  return (
    <div className="border-t border-border2 bg-surface px-4 py-3">
      <div className="flex items-end gap-2">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSubmit();
            }
          }}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className="max-h-40 min-h-[44px] flex-1 resize-none rounded-xl border border-border2 bg-bg px-4 py-3 text-sm text-text2 placeholder:text-muted2 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accentSoft disabled:opacity-50"
        />
        <button
          onClick={onSubmit}
          disabled={disabled || !value.trim()}
          className="flex h-[44px] items-center gap-2 rounded-xl bg-accent px-5 text-sm font-medium text-white transition-colors hover:bg-accentHover disabled:opacity-50"
        >
          {disabled ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          {disabled ? "…" : "Generate"}
        </button>
      </div>
    </div>
  );
}

function EmptyState({
  onExample,
  prompt,
  setPrompt,
  busy,
  onSubmit,
  constraintMode,
  onGenerateConstraints,
}: {
  onExample: (ex: string) => void;
  prompt: string;
  setPrompt: (v: string) => void;
  busy: boolean;
  onSubmit: () => void;
  constraintMode: boolean;
  onGenerateConstraints: () => void;
}) {
  const examples = [
    "A minimal landing page for a coffee shop called Fern — hero, three feature cards, footer",
    "A personal portfolio with an about section, project grid, and contact links",
    "A simple blog homepage with a featured post and recent posts list",
  ];
  return (
    <div className="flex h-full flex-col items-center justify-center gap-6 px-8 py-12 text-center">
      <div className="flex h-20 w-20 items-center justify-center rounded-3xl bg-accentSoft text-accent">
        <svg width="44" height="44" viewBox="0 0 120 120" fill="none">
          <circle cx="60" cy="60" r="56" fill="#E3F2FD" stroke="#90CAF9" strokeWidth="4" />
          <rect x="35" y="50" width="50" height="30" rx="6" fill="#fff" stroke="#90CAF9" strokeWidth="2" />
          <rect x="45" y="60" width="30" height="6" rx="3" fill="#BBDEFB" />
          <circle cx="60" cy="65" r="2.5" fill="#90CAF9" />
          <rect x="55" y="72" width="10" height="3" rx="1.5" fill="#E3F2FD" />
          <ellipse cx="60" cy="95" rx="18" ry="4" fill="#E3F2FD" />
        </svg>
      </div>
      <div className="space-y-1.5">
        <h2 className="text-xl font-semibold text-text2">Start your creative journey</h2>
        <p className="max-w-md text-sm text-muted">
          Describe your dream website and watch it come to life. Or pick a starting point:
        </p>
      </div>
      <div className="flex flex-col gap-2">
        {examples.map((ex, i) => (
          <button
            key={i}
            onClick={() => onExample(ex)}
            className="rounded-lg border border-border2 bg-surface px-4 py-2.5 text-left text-sm text-muted transition-colors hover:border-accent hover:text-accent"
          >
            {ex}
          </button>
        ))}
      </div>
      {/* Inline input for first generation */}
      <div className="flex w-full max-w-xl items-end gap-2">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSubmit();
            }
          }}
          placeholder="Describe the website you want to create…"
          rows={2}
          className="min-h-[52px] flex-1 resize-none rounded-xl border border-border2 bg-surface px-4 py-3 text-sm text-text2 placeholder:text-muted2 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accentSoft"
        />
        <button
          onClick={onSubmit}
          disabled={busy || !prompt.trim()}
          className="flex h-[52px] items-center gap-2 rounded-xl bg-accent px-5 text-sm font-medium text-white transition-colors hover:bg-accentHover disabled:opacity-50"
        >
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          Generate
        </button>
      </div>
      {constraintMode && (
        <button
          onClick={onGenerateConstraints}
          disabled={busy}
          className="text-sm text-accent hover:underline"
        >
          Or generate from your constraint selections →
        </button>
      )}
    </div>
  );
}