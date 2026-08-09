import { useRef } from "react";
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
  const itemRefs = useRef(new Map<string, HTMLButtonElement>());

  const focusEntry = (index: number) => {
    const entry = entries[index];
    if (!entry) return;
    onSelect(entry.node.id);
    itemRefs.current.get(entry.node.id)?.focus();
  };

  return (
    <div role="tree" aria-label="Page layers" className="space-y-0.5 p-2">
      {entries.length === 0 && (
        <p className="p-2 text-xs text-muted-foreground">This page has no editable elements.</p>
      )}
      {entries.map(({ node, depth }) => (
        <button
          key={node.id}
          role="treeitem"
          aria-selected={selectedNodeId === node.id}
          aria-level={depth + 1}
          tabIndex={
            selectedNodeId === node.id || (!selectedNodeId && node.id === entries[0]?.node.id)
              ? 0
              : -1
          }
          ref={(element) => {
            if (element) itemRefs.current.set(node.id, element);
            else itemRefs.current.delete(node.id);
          }}
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
          onKeyDown={(event) => {
            const index = entries.findIndex((entry) => entry.node.id === node.id);
            if (event.key === "ArrowDown") {
              event.preventDefault();
              focusEntry(Math.min(index + 1, entries.length - 1));
            } else if (event.key === "ArrowUp") {
              event.preventDefault();
              focusEntry(Math.max(index - 1, 0));
            } else if (event.key === "Home") {
              event.preventDefault();
              focusEntry(0);
            } else if (event.key === "End") {
              event.preventDefault();
              focusEntry(entries.length - 1);
            } else if (
              event.key === "ArrowRight" &&
              entries[index + 1]?.depth > entries[index].depth
            ) {
              event.preventDefault();
              focusEntry(index + 1);
            } else if (event.key === "ArrowLeft" && entries[index].parentId) {
              event.preventDefault();
              focusEntry(
                entries.findIndex(
                  (entry) => entry.node.id === entries[index].parentId,
                ),
              );
            }
          }}
          className={cn(
            "flex w-full items-center gap-1 rounded px-1.5 py-1 text-left text-xs",
            selectedNodeId === node.id
              ? "bg-primary/10 text-primary"
              : "text-muted-foreground hover:bg-background hover:text-foreground",
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
