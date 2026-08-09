import { GripVertical } from "lucide-react";
import type { EditorDocumentV1 } from "../../editor/document";
import {
  elementEntries,
  elementLabel,
  moveElementBefore,
} from "../../editor/operations";
import { cn } from "../../lib/utils";

interface LayerTreeProps {
  document: EditorDocumentV1;
  selectedNodeId: string | null;
  onSelect: (nodeId: string) => void;
  onChange: (document: EditorDocumentV1) => void;
}

export default function LayerTree({
  document,
  selectedNodeId,
  onSelect,
  onChange,
}: LayerTreeProps) {
  const entries = elementEntries(document);

  return (
    <div role="tree" aria-label="Page layers" className="space-y-0.5 p-2">
      {entries.length === 0 && (
        <p className="p-2 text-xs text-muted2">This page has no editable elements.</p>
      )}
      {entries.map(({ node, depth }) => (
        <button
          key={node.id}
          role="treeitem"
          aria-selected={selectedNodeId === node.id}
          draggable
          onDragStart={(event) => {
            event.dataTransfer.effectAllowed = "move";
            event.dataTransfer.setData("application/x-mwb-node", node.id);
          }}
          onDragOver={(event) => {
            event.preventDefault();
            event.dataTransfer.dropEffect = "move";
          }}
          onDrop={(event) => {
            event.preventDefault();
            const sourceId = event.dataTransfer.getData("application/x-mwb-node");
            if (!sourceId) return;
            const updated = moveElementBefore(document, sourceId, node.id);
            if (updated !== document) {
              onChange(updated);
              onSelect(sourceId);
            }
          }}
          onClick={() => onSelect(node.id)}
          className={cn(
            "flex w-full items-center gap-1 rounded px-1.5 py-1 text-left text-xs",
            selectedNodeId === node.id
              ? "bg-accentSoft text-accent"
              : "text-muted hover:bg-bg hover:text-text2",
          )}
          style={{ paddingLeft: `${depth * 12 + 6}px` }}
        >
          <GripVertical className="h-3 w-3 shrink-0 opacity-50" />
          <span className="truncate">{elementLabel(node)}</span>
        </button>
      ))}
    </div>
  );
}
