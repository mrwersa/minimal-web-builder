import { ChevronRight, Layers3, SlidersHorizontal } from "lucide-react";
import { findNode, type EditorDocumentV1 } from "../../editor/document";
import { elementLabel, elementPath } from "../../editor/operations";
import { useStore } from "../../store";
import GrapeJSEditor from "../GrapeJSEditor";
import EditorInspector from "./EditorInspector";
import LayerTree from "./LayerTree";

export default function EditorWorkspace({ document }: { document: EditorDocumentV1 }) {
  const selectedNodeId = useStore((state) => state.selectedNodeId);
  const selectNode = useStore((state) => state.selectNode);
  const setDocumentWithHistory = useStore((state) => state.setDocumentWithHistory);
  const selectedNode = selectedNodeId ? findNode(document, selectedNodeId) : null;
  const path = selectedNodeId ? elementPath(document, selectedNodeId) : [];

  return (
    <div className="flex h-full min-w-0 bg-bg">
      <section className="flex min-w-0 flex-1 flex-col">
        <nav
          aria-label="Selected element path"
          className="flex h-9 shrink-0 items-center gap-1 overflow-x-auto border-b border-border2 bg-surface px-3"
        >
          {path.length === 0 ? (
            <span className="text-xs text-muted2">Select an element to inspect it</span>
          ) : (
            path.map((node, index) => (
              <span key={node.id} className="flex shrink-0 items-center gap-1">
                {index > 0 && <ChevronRight className="h-3 w-3 text-muted2" />}
                <button
                  onClick={() => selectNode(node.id)}
                  className="rounded px-1.5 py-0.5 text-xs text-muted hover:bg-accentSoft hover:text-accent"
                >
                  {elementLabel(node)}
                </button>
              </span>
            ))
          )}
        </nav>
        <div className="min-h-0 flex-1 bg-white">
          <GrapeJSEditor
            document={document}
            selectedNodeId={selectedNodeId}
            onSelect={selectNode}
            onUpdate={setDocumentWithHistory}
          />
        </div>
      </section>

      <aside className="flex w-72 shrink-0 flex-col border-l border-border2 bg-surface">
        <section className="flex max-h-[45%] min-h-32 flex-col border-b border-border2">
          <h2 className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-text2">
            <Layers3 className="h-3.5 w-3.5 text-muted2" /> Layers
          </h2>
          <div className="min-h-0 flex-1 overflow-y-auto">
            <LayerTree
              document={document}
              selectedNodeId={selectedNodeId}
              onSelect={selectNode}
              onChange={setDocumentWithHistory}
            />
          </div>
        </section>
        <section className="min-h-0 flex-1 overflow-y-auto">
          <h2 className="flex items-center gap-1.5 border-b border-border2 px-3 py-2 text-xs font-semibold text-text2">
            <SlidersHorizontal className="h-3.5 w-3.5 text-muted2" /> Inspector
          </h2>
          <EditorInspector
            document={document}
            node={selectedNode}
            onChange={setDocumentWithHistory}
          />
        </section>
      </aside>
    </div>
  );
}
