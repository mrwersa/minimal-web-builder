import { useEffect, useMemo, useRef, useState } from "react";
import { Command } from "lucide-react";
import { searchCommands, type BuilderCommand } from "../commands";
import { Input } from "./ui/input";

export default function CommandPalette({
  commands,
  onClose,
}: {
  commands: readonly BuilderCommand[];
  onClose: () => void;
}) {
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const dialogRef = useRef<HTMLElement>(null);
  const filtered = useMemo(() => searchCommands(commands, query), [commands, query]);

  useEffect(() => {
    const firstEnabled = filtered.findIndex((command) => !command.disabled);
    setActiveIndex(Math.max(0, firstEnabled));
  }, [filtered]);
  useEffect(() => {
    const previousFocus = document.activeElement as HTMLElement | null;
    return () => previousFocus?.focus();
  }, []);
  useEffect(() => {
    const trapFocus = (event: KeyboardEvent) => {
      if (event.key !== "Tab" || !dialogRef.current) return;
      const focusable = Array.from(
        dialogRef.current.querySelectorAll<HTMLElement>(
          'input, button:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      );
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener("keydown", trapFocus);
    return () => document.removeEventListener("keydown", trapFocus);
  }, []);

  const moveActive = (direction: -1 | 1) => {
    if (filtered.length === 0) return;
    let next = activeIndex;
    for (let attempts = 0; attempts < filtered.length; attempts += 1) {
      next = (next + direction + filtered.length) % filtered.length;
      if (!filtered[next].disabled) {
        setActiveIndex(next);
        return;
      }
    }
  };

  const execute = (command: BuilderCommand | undefined) => {
    if (!command || command.disabled) return;
    command.run();
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/35 px-4 pt-[15vh]"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        className="w-full max-w-lg overflow-hidden rounded-xl border border-border bg-surface shadow-2xl"
      >
        <div className="flex items-center gap-2 border-b border-border px-3">
          <Command className="h-4 w-4 shrink-0 text-muted-foreground" />
          <Input
            autoFocus
            role="combobox"
            aria-expanded="true"
            aria-autocomplete="list"
            aria-label="Search commands"
            aria-controls="builder-command-list"
            aria-activedescendant={filtered[activeIndex]?.id}
            value={query}
            placeholder="Type a command…"
            className="border-0 px-0 focus:ring-0"
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Escape") {
                event.preventDefault();
                onClose();
              } else if (event.key === "ArrowDown") {
                event.preventDefault();
                moveActive(1);
              } else if (event.key === "ArrowUp") {
                event.preventDefault();
                moveActive(-1);
              } else if (event.key === "Enter") {
                event.preventDefault();
                execute(filtered[activeIndex]);
              }
            }}
          />
          <kbd className="rounded border border-border bg-background px-1.5 py-0.5 text-[10px] text-muted-foreground">
            Esc
          </kbd>
        </div>
        <div id="builder-command-list" role="listbox" className="max-h-80 overflow-y-auto p-2">
          {filtered.length === 0 && (
            <p className="px-3 py-6 text-center text-xs text-muted-foreground">No commands found.</p>
          )}
          {filtered.map((command, index) => (
            <button
              key={command.id}
              id={command.id}
              role="option"
              aria-selected={index === activeIndex}
              disabled={command.disabled}
              onMouseEnter={() => setActiveIndex(index)}
              onClick={() => execute(command)}
              className={
                index === activeIndex
                  ? "flex w-full items-center gap-3 rounded-lg bg-primary/10 px-3 py-2 text-left text-primary"
                  : "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-foreground hover:bg-background disabled:opacity-40"
              }
            >
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-medium">{command.label}</span>
                <span className="block truncate text-[11px] text-muted-foreground">
                  {command.description}
                </span>
              </span>
              {command.shortcut && (
                <kbd className="shrink-0 rounded border border-border bg-surface px-1.5 py-0.5 text-[10px] text-muted-foreground">
                  {command.shortcut
                    .replace("mod", navigator.platform.includes("Mac") ? "⌘" : "Ctrl")
                    .replaceAll("+", " ")}
                </kbd>
              )}
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
