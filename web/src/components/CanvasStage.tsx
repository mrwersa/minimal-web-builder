import { lazy, Suspense } from "react";
import { ChevronRight } from "lucide-react";
import { elementLabel, elementPath } from "../editor/operations";
import { useStore, VIEWPORT_WIDTHS } from "../store";
import EmptyState from "./EmptyState";
import Preview from "./Preview";
import { Spinner } from "./ui/spinner";

const GrapeJSEditor = lazy(() => import("./GrapeJSEditor"));

/** Breadcrumb of the selected element's ancestors, so selection stays legible. */
function SelectionPath() {
  const editorDocument = useStore((state) => state.editorDocument);
  const selectedNodeId = useStore((state) => state.selectedNodeId);
  const selectNode = useStore((state) => state.selectNode);
  const path =
    editorDocument && selectedNodeId ? elementPath(editorDocument, selectedNodeId) : [];

  return (
    <nav
      aria-label="Selected element path"
      className="flex h-8 shrink-0 items-center gap-1 overflow-x-auto border-t bg-surface px-3"
    >
      {path.length === 0 ? (
        <span className="text-xs text-muted-foreground">
          Select an element to inspect it
        </span>
      ) : (
        path.map((node, index) => (
          <span key={node.id} className="flex shrink-0 items-center gap-1">
            {index > 0 && <ChevronRight className="h-3 w-3 text-muted-foreground" />}
            <button
              type="button"
              onClick={() => selectNode(node.id)}
              className="rounded px-1.5 py-0.5 text-xs text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
            >
              {elementLabel(node)}
            </button>
          </span>
        ))
      )}
    </nav>
  );
}

export default function CanvasStage() {
  const code = useStore((state) => state.code);
  const busy = useStore((state) => state.busy);
  const editing = useStore((state) => state.editing);
  const editorDocument = useStore((state) => state.editorDocument);
  const selectedNodeId = useStore((state) => state.selectedNodeId);
  const selectNode = useStore((state) => state.selectNode);
  const setDocumentWithHistory = useStore((state) => state.setDocumentWithHistory);
  const viewport = useStore((state) => state.viewport);
  const zoom = useStore((state) => state.zoom);

  if (!code) return <EmptyState />;

  const width = VIEWPORT_WIDTHS[viewport];
  const isEditing = editing && editorDocument && !busy;

  return (
    <section className="flex min-h-0 min-w-0 flex-1 flex-col">
      <div className="canvas-backdrop relative flex min-h-0 flex-1 justify-center overflow-auto p-4">
        <div
          className="h-full shrink-0 overflow-hidden rounded-lg bg-white shadow-lg ring-1 ring-black/5 transition-[width]"
          style={{
            width: width ?? "100%",
            maxWidth: width === null ? "100%" : undefined,
            transform: zoom === 1 ? undefined : `scale(${zoom})`,
            transformOrigin: "top center",
          }}
        >
          {isEditing && editorDocument ? (
            <Suspense
              fallback={
                <div className="flex h-full items-center justify-center">
                  <Spinner />
                </div>
              }
            >
              <GrapeJSEditor
                document={editorDocument}
                selectedNodeId={selectedNodeId}
                onSelect={selectNode}
                onUpdate={setDocumentWithHistory}
              />
            </Suspense>
          ) : (
            <Preview />
          )}
        </div>

        {busy && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/70 backdrop-blur-sm">
            <div className="flex flex-col items-center gap-3 rounded-lg border bg-surface px-6 py-5 shadow-lg">
              <Spinner className="text-primary" />
              <p className="text-sm font-medium">Generating your page…</p>
              <p className="text-xs text-muted-foreground">
                This usually takes 5–15 seconds
              </p>
            </div>
          </div>
        )}
      </div>
      <SelectionPath />
    </section>
  );
}
