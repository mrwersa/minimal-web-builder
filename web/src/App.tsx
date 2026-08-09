import { useEffect, useMemo, useRef, useState } from "react";
import { Toaster, toast } from "sonner";
import { Eye, Code2, AlertCircle, Info, Sparkles, ArrowRight, Undo2, Redo2, LogOut, Command as CommandIcon } from "lucide-react";
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
import AuthScreen from "./components/AuthScreen";
import { useAuthStore } from "./authStore";
import CommandPalette from "./components/CommandPalette";
import {
  isEditableTarget,
  keyboardShortcut,
  type BuilderCommand,
} from "./commands";

type Tab = "preview" | "code";

export default function App() {
  const restoreSession = useAuthStore((state) => state.restoreSession);
  const loading = useAuthStore((state) => state.loading);
  const user = useAuthStore((state) => state.user);

  useEffect(() => {
    void restoreSession();
  }, [restoreSession]);

  if (loading) {
    return (
      <main className="flex h-full items-center justify-center bg-bg" aria-label="Loading session">
        <Spinner />
      </main>
    );
  }
  if (!user) return <AuthScreen />;
  return <BuilderApp />;
}

function BuilderApp() {
  const loadOptions = useStore((s) => s.loadOptions);
  const restoreConversation = useStore((s) => s.restoreConversation);
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const authSubmitting = useAuthStore((state) => state.submitting);
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
  const editing = useStore((s) => s.editing);
  const setStore = useStore((s) => s.set);
  const [tab, setTab] = useState<Tab>("preview");
  const [prompt, setPrompt] = useState("");
  const [showChat, setShowChat] = useState(true);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const wasBusy = useRef(false);

  const commands = useMemo<BuilderCommand[]>(
    () => [
      {
        id: "open-command-palette",
        label: "Open command palette",
        description: "Search every builder command",
        shortcut: "mod+k",
        keywords: ["search", "actions"],
        run: () => setPaletteOpen(true),
      },
      {
        id: "show-preview",
        label: "Show preview",
        description: "Switch to the rendered page",
        shortcut: "mod+1",
        run: () => setTab("preview"),
      },
      {
        id: "show-code",
        label: "Show code",
        description: "Switch to portable HTML export",
        shortcut: "mod+2",
        disabled: !code,
        run: () => setTab("code"),
      },
      {
        id: "toggle-visual-editor",
        label: editing ? "Close visual editor" : "Open visual editor",
        description: "Toggle direct canvas editing",
        shortcut: "mod+.",
        disabled: !code || busy,
        keywords: ["wysiwyg", "canvas"],
        run: () => {
          setTab("preview");
          setStore("editing", !editing);
        },
      },
      {
        id: "toggle-chat",
        label: showChat ? "Hide chat" : "Show chat",
        description: "Toggle the AI conversation panel",
        shortcut: "mod+j",
        run: () => setShowChat((visible) => !visible),
      },
      {
        id: "undo",
        label: "Undo",
        description: "Revert the last document change",
        shortcut: "mod+z",
        disabled: undoStack.length === 0,
        run: undo,
      },
      {
        id: "redo",
        label: "Redo",
        description: "Restore the last reverted change",
        shortcut: "mod+shift+z",
        disabled: redoStack.length === 0,
        run: redo,
      },
    ],
    [busy, code, editing, redo, redoStack.length, setStore, showChat, undo, undoStack.length],
  );

  useEffect(() => { loadOptions(); }, [loadOptions]);
  useEffect(() => { void restoreConversation(); }, [restoreConversation]);
  useEffect(() => { if (safetyAlerts.length) toast.warning("Safety: " + safetyAlerts.join(", ")); }, [safetyAlerts]); // eslint-disable-line
  useEffect(() => { if (error) toast.error(error); }, [error]); // eslint-disable-line
  useEffect(() => {
    if (wasBusy.current && !busy && code && !error) {
      toast.success("Page updated");
      setTab("preview");
    }
    wasBusy.current = busy;
  }, [code, busy, error]);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const shortcut = keyboardShortcut(e);
      if (!shortcut || (isEditableTarget(e.target) && shortcut !== "mod+k")) return;
      const command = commands.find((candidate) => candidate.shortcut === shortcut);
      if (!command || command.disabled) return;
      e.preventDefault();
      command.run();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [commands]);

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
              aria-label="Open command palette"
              title="Commands (Ctrl+K)"
              onClick={() => setPaletteOpen(true)}
              className="rounded-lg p-1.5 text-muted2 transition-colors hover:bg-bg hover:text-text2"
            >
              <CommandIcon className="h-4 w-4" />
            </button>
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
            <span className="hidden max-w-48 truncate text-xs text-muted lg:inline">
              {user?.email}
            </span>
            <button
              aria-label="Sign out"
              className="rounded-lg p-1.5 text-muted2 transition-colors hover:bg-bg hover:text-text2 disabled:opacity-50"
              disabled={authSubmitting}
              onClick={() => void logout()}
              title="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </button>
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

        {paletteOpen && (
          <CommandPalette
            commands={commands.filter((command) => command.id !== "open-command-palette")}
            onClose={() => setPaletteOpen(false)}
          />
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
