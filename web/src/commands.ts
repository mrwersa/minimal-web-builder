export interface BuilderCommand {
  id: string;
  label: string;
  description: string;
  shortcut?: string;
  keywords?: string[];
  disabled?: boolean;
  run: () => void;
}

export function keyboardShortcut(event: KeyboardEvent): string | null {
  if (!event.metaKey && !event.ctrlKey) return null;
  const parts = ["mod"];
  if (event.shiftKey) parts.push("shift");
  if (event.altKey) parts.push("alt");
  parts.push(event.key.toLowerCase());
  return parts.join("+");
}

export function isEditableTarget(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLElement &&
    (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))
  );
}

export function searchCommands(
  commands: readonly BuilderCommand[],
  query: string,
): BuilderCommand[] {
  const terms = query.toLowerCase().trim().split(/\s+/).filter(Boolean);
  if (terms.length === 0) return [...commands];
  return commands.filter((command) => {
    const haystack = [
      command.label,
      command.description,
      ...(command.keywords ?? []),
    ]
      .join(" ")
      .toLowerCase();
    return terms.every((term) => haystack.includes(term));
  });
}
