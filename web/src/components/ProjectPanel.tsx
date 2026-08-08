import { useEffect, useState } from "react";
import {
  Archive,
  Cloud,
  Copy,
  FolderKanban,
  Pencil,
  RotateCcw,
  Search,
  X,
} from "lucide-react";
import { useStore } from "../store";
import { cn } from "../lib/utils";
import { Button } from "./ui/Button";
import { Input } from "./ui/Input";
import { InlineError } from "./ui/InlineError";

export default function ProjectPanel() {
  const s = useStore();
  const [renameId, setRenameId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [archiveId, setArchiveId] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => void s.refreshProjects(), 250);
    return () => clearTimeout(timer);
  }, [s.projectSearch]); // eslint-disable-line react-hooks/exhaustive-deps

  const beginRename = (projectId: string, name: string) => {
    setArchiveId(null);
    setRenameId(projectId);
    setRenameValue(name);
  };

  const finishRename = async () => {
    if (!renameId || !renameValue.trim() || busyId) return;
    setBusyId(renameId);
    await s.renameProject(renameId, renameValue);
    setBusyId(null);
    setRenameId(null);
  };

  const runAction = async (projectId: string, action: () => Promise<void>) => {
    if (busyId) return;
    setBusyId(projectId);
    try {
      await action();
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-2">
      {s.projectsError && (
        <InlineError message={s.projectsError} onRetry={() => s.refreshProjects()} />
      )}
      <div className="flex gap-2">
        <Input
          value={s.projectName}
          onChange={(event) => s.set("projectName", event.target.value)}
          placeholder="New project name"
          className="flex-1"
          maxLength={120}
        />
        <Button
          variant="outline"
          onClick={() => void runAction("create", s.createCurrentProject)}
          disabled={!s.projectName.trim() || busyId !== null}
        >
          Create
        </Button>
      </div>

      <div className="relative">
        <Search className="pointer-events-none absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted2" />
        <Input
          value={s.projectSearch}
          onChange={(event) => s.set("projectSearch", event.target.value)}
          placeholder="Search projects"
          className="pl-8"
          maxLength={120}
        />
      </div>

      {s.activeProjectId && (
        <div className="flex items-center justify-between rounded-lg bg-bg px-2.5 py-2 text-xs">
          <span className="flex items-center gap-1.5 text-muted">
            <Cloud className="h-3.5 w-3.5" />
            {s.saveState === "saving"
              ? "Saving…"
              : s.saveState === "conflict"
                ? "Save conflict"
                : s.saveState === "idle"
                  ? `Unsaved · v${s.activePageVersion}`
                  : `Saved · v${s.activePageVersion}`}
          </span>
          <button
            onClick={() => s.saveActivePage()}
            className="font-medium text-accent hover:underline"
          >
            Save now
          </button>
        </div>
      )}

      <div className="space-y-1">
        {s.projects.map((project) => (
          <div key={project.id} className="rounded-lg border border-border2 p-1.5">
            {renameId === project.id ? (
              <div className="flex gap-1.5">
                <Input
                  value={renameValue}
                  onChange={(event) => setRenameValue(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") void finishRename();
                    if (event.key === "Escape") setRenameId(null);
                  }}
                  autoFocus
                  aria-label={`Rename ${project.name}`}
                  maxLength={120}
                />
                <Button
                  variant="outline"
                  onClick={() => void finishRename()}
                  disabled={busyId !== null}
                >
                  Save
                </Button>
                <button
                  onClick={() => setRenameId(null)}
                  className="rounded p-1.5 text-muted2 hover:bg-bg hover:text-text"
                  aria-label="Cancel rename"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            ) : archiveId === project.id ? (
              <div className="flex items-center justify-between gap-2 px-1 py-0.5 text-xs">
                <span className="text-muted">Archive this project?</span>
                <div className="flex gap-1.5">
                  <button
                    onClick={() => setArchiveId(null)}
                    className="text-muted2 hover:text-text"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => {
                      setArchiveId(null);
                      void runAction(project.id, () => s.archiveProject(project.id));
                    }}
                    disabled={busyId !== null}
                    className="font-medium text-red-500 hover:underline"
                  >
                    Archive
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-1">
                <button
                  onClick={() => s.openProject(project.id)}
                  className={cn(
                    "min-w-0 flex-1 rounded px-1.5 py-1 text-left text-xs",
                    s.activeProjectId === project.id
                      ? "bg-accentSoft text-accent"
                      : "text-muted hover:bg-bg",
                  )}
                >
                  <span className="flex items-center gap-1.5 truncate font-medium">
                    <FolderKanban className="h-3.5 w-3.5 shrink-0" />
                    {project.name}
                  </span>
                </button>
                <ProjectAction
                  label={`Rename ${project.name}`}
                  onClick={() => beginRename(project.id, project.name)}
                  disabled={busyId !== null}
                >
                  <Pencil className="h-3.5 w-3.5" />
                </ProjectAction>
                <ProjectAction
                  label={`Duplicate ${project.name}`}
                  onClick={() =>
                    void runAction(project.id, () => s.duplicateProject(project.id))
                  }
                  disabled={busyId !== null}
                >
                  <Copy className="h-3.5 w-3.5" />
                </ProjectAction>
                <ProjectAction
                  label={`Archive ${project.name}`}
                  onClick={() => {
                    setRenameId(null);
                    setArchiveId(project.id);
                  }}
                  disabled={busyId !== null}
                >
                  <Archive className="h-3.5 w-3.5" />
                </ProjectAction>
              </div>
            )}
          </div>
        ))}
        {s.projects.length === 0 && (
          <p className="px-1 py-2 text-xs text-muted2">
            {s.projectSearch ? "No projects match this search." : "No projects yet."}
          </p>
        )}
      </div>

      {s.revisions.length > 1 && (
        <details className="rounded-lg border border-border2 p-2">
          <summary className="cursor-pointer text-xs font-medium text-muted">
            Version history
          </summary>
          <div className="mt-2 space-y-1">
            {s.revisions.slice(0, 8).map((revision) => (
              <div
                key={revision.id}
                className="flex items-center justify-between rounded px-1.5 py-1 text-xs text-muted2"
              >
                <span>
                  v{revision.sequence} · {revision.source}
                </span>
                <button
                  onClick={() => s.restoreRevision(revision.id)}
                  disabled={revision.sequence === s.activePageVersion}
                  aria-label={`Restore version ${revision.sequence}`}
                  className="rounded p-1 hover:bg-accentSoft hover:text-accent disabled:opacity-30"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

function ProjectAction({
  label,
  onClick,
  children,
  disabled = false,
}: {
  label: string;
  onClick: () => void;
  children: React.ReactNode;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      aria-label={label}
      title={label}
      disabled={disabled}
      className="rounded p-1.5 text-muted2 hover:bg-bg hover:text-text disabled:opacity-40"
    >
      {children}
    </button>
  );
}
