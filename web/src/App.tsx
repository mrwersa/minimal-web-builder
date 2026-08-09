import { useEffect, useMemo, useRef, useState } from "react";
import { Toaster, toast } from "sonner";
import { AlertCircle, Info } from "lucide-react";
import { useAuthStore } from "./authStore";
import { useStore } from "./store";
import { ThemeProvider, useTheme } from "./theme";
import {
  isEditableTarget,
  keyboardShortcut,
  type BuilderCommand,
} from "./commands";
import AuthScreen from "./components/AuthScreen";
import CanvasStage from "./components/CanvasStage";
import CodePanel from "./components/CodePanel";
import CommandPalette from "./components/CommandPalette";
import LeftRail from "./components/layout/LeftRail";
import RightPanel from "./components/layout/RightPanel";
import TopBar from "./components/layout/TopBar";
import { Spinner } from "./components/ui/spinner";
import { TooltipProvider } from "./components/ui/tooltip";

type View = "canvas" | "code";

export default function App() {
  return (
    <ThemeProvider>
      <TooltipProvider delayDuration={400}>
        <Root />
      </TooltipProvider>
    </ThemeProvider>
  );
}

function Root() {
  const restoreSession = useAuthStore((state) => state.restoreSession);
  const loading = useAuthStore((state) => state.loading);
  const user = useAuthStore((state) => state.user);

  useEffect(() => {
    void restoreSession();
  }, [restoreSession]);

  if (loading) {
    return (
      <main
        className="flex h-full items-center justify-center bg-background"
        aria-label="Loading session"
      >
        <Spinner />
      </main>
    );
  }
  if (!user) return <AuthScreen />;
  return <BuilderApp />;
}

/** Non-blocking generation feedback, kept out of the canvas itself. */
function AlertStrip() {
  const notes = useStore((state) => state.notes);
  const safetyAlerts = useStore((state) => state.safetyAlerts);
  if (safetyAlerts.length === 0 && notes.length === 0) return null;

  return (
    <div className="flex shrink-0 flex-col gap-1 border-b bg-surface px-4 py-1.5">
      {safetyAlerts.map((alert, index) => (
        <div key={`s${index}`} className="flex items-center gap-1.5 text-xs text-warning">
          <AlertCircle className="h-3.5 w-3.5 shrink-0" />
          <span className="truncate">{alert}</span>
        </div>
      ))}
      {notes.slice(0, 3).map((note, index) => (
        <div
          key={`n${index}`}
          className="flex items-center gap-1.5 text-xs text-muted-foreground"
        >
          <Info className="h-3.5 w-3.5 shrink-0" />
          <span className="truncate">{note}</span>
        </div>
      ))}
    </div>
  );
}

function BuilderApp() {
  const loadOptions = useStore((state) => state.loadOptions);
  const restoreConversation = useStore((state) => state.restoreConversation);
  const code = useStore((state) => state.code);
  const busy = useStore((state) => state.busy);
  const error = useStore((state) => state.error);
  const safetyAlerts = useStore((state) => state.safetyAlerts);
  const undoStack = useStore((state) => state.undoStack);
  const redoStack = useStore((state) => state.redoStack);
  const undo = useStore((state) => state.undo);
  const redo = useStore((state) => state.redo);
  const editing = useStore((state) => state.editing);
  const setStore = useStore((state) => state.set);
  const { resolved, setPreference } = useTheme();
  const [view, setView] = useState<View>("canvas");
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
        run: () => setView("canvas"),
      },
      {
        id: "show-code",
        label: "Show code",
        description: "Switch to portable HTML export",
        shortcut: "mod+2",
        disabled: !code,
        run: () => setView("code"),
      },
      {
        id: "toggle-visual-editor",
        label: editing ? "Close visual editor" : "Open visual editor",
        description: "Toggle direct canvas editing",
        shortcut: "mod+.",
        disabled: !code || busy,
        keywords: ["wysiwyg", "canvas"],
        run: () => {
          setView("canvas");
          setStore("editing", !editing);
        },
      },
      {
        id: "toggle-theme",
        label: resolved === "dark" ? "Switch to light theme" : "Switch to dark theme",
        description: "Change the builder appearance",
        keywords: ["dark", "light", "appearance"],
        run: () => setPreference(resolved === "dark" ? "light" : "dark"),
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
    [
      busy,
      code,
      editing,
      redo,
      redoStack.length,
      resolved,
      setPreference,
      setStore,
      undo,
      undoStack.length,
    ],
  );

  useEffect(() => {
    loadOptions();
  }, [loadOptions]);
  useEffect(() => {
    void restoreConversation();
  }, [restoreConversation]);
  useEffect(() => {
    if (safetyAlerts.length) toast.warning("Safety: " + safetyAlerts.join(", "));
  }, [safetyAlerts]);
  useEffect(() => {
    if (error) toast.error(error);
  }, [error]);
  useEffect(() => {
    if (wasBusy.current && !busy && code && !error) {
      toast.success("Page updated");
      setView("canvas");
    }
    wasBusy.current = busy;
  }, [code, busy, error]);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      const shortcut = keyboardShortcut(event);
      if (!shortcut || (isEditableTarget(event.target) && shortcut !== "mod+k")) return;
      const command = commands.find((candidate) => candidate.shortcut === shortcut);
      if (!command || command.disabled) return;
      event.preventDefault();
      command.run();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [commands]);

  return (
    <div className="flex h-full w-full flex-col bg-background text-foreground">
      <TopBar
        view={view}
        onViewChange={setView}
        onOpenPalette={() => setPaletteOpen(true)}
      />
      <AlertStrip />

      <div className="flex min-h-0 flex-1">
        <LeftRail />
        {view === "canvas" ? (
          <CanvasStage />
        ) : (
          <section className="flex min-h-0 min-w-0 flex-1 flex-col">
            <CodePanel />
          </section>
        )}
        <RightPanel />
      </div>

      {paletteOpen && (
        <CommandPalette
          commands={commands.filter((command) => command.id !== "open-command-palette")}
          onClose={() => setPaletteOpen(false)}
        />
      )}

      <Toaster position="bottom-right" richColors closeButton theme={resolved} />
    </div>
  );
}
