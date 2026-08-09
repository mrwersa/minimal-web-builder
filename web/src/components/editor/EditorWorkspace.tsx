import { useState } from "react";
import {
  ChevronRight,
  Layers3,
  Monitor,
  SlidersHorizontal,
  Smartphone,
  Tablet,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { findNode, type EditorDocumentV1 } from "../../editor/document";
import { elementLabel, elementPath } from "../../editor/operations";
import { useStore } from "../../store";
import GrapeJSEditor from "../GrapeJSEditor";
import DesignTokensPanel from "./DesignTokensPanel";
import EditorInspector from "./EditorInspector";
import LayerTree from "./LayerTree";

export default function EditorWorkspace({ document }: { document: EditorDocumentV1 }) {
  const selectedNodeId = useStore((state) => state.selectedNodeId);
  const selectNode = useStore((state) => state.selectNode);
  const setDocumentWithHistory = useStore((state) => state.setDocumentWithHistory);
  const selectedNode = selectedNodeId ? findNode(document, selectedNodeId) : null;
  const path = selectedNodeId ? elementPath(document, selectedNodeId) : [];
  const [viewport, setViewport] = useState<"desktop" | "tablet" | "mobile">(
    "desktop",
  );
  const [zoom, setZoom] = useState(1);
  const viewportWidth = viewport === "desktop" ? "100%" : viewport === "tablet" ? 768 : 390;

  return (
    <div className="flex h-full min-w-0 bg-bg">
      <section className="flex min-w-0 flex-1 flex-col">
        <div className="flex h-10 shrink-0 items-center justify-between border-b border-border2 bg-surface px-3">
          <div className="flex items-center gap-1" aria-label="Viewport presets">
            {([
              ["desktop", "Desktop", Monitor],
              ["tablet", "Tablet", Tablet],
              ["mobile", "Mobile", Smartphone],
            ] as const).map(([value, label, Icon]) => (
              <button
                key={value}
                aria-label={`${label} viewport`}
                aria-pressed={viewport === value}
                onClick={() => setViewport(value)}
                className={
                  viewport === value
                    ? "rounded bg-accentSoft p-1.5 text-accent"
                    : "rounded p-1.5 text-muted2 hover:bg-bg hover:text-text2"
                }
              >
                <Icon className="h-3.5 w-3.5" />
              </button>
            ))}
            <span className="ml-1 text-[11px] text-muted2">
              {viewport === "desktop" ? "Fluid" : `${viewportWidth}px`}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <button
              aria-label="Zoom out"
              onClick={() => setZoom((value) => Math.max(0.5, value - 0.25))}
              disabled={zoom <= 0.5}
              className="rounded p-1 text-muted2 hover:bg-bg disabled:opacity-30"
            >
              <ZoomOut className="h-3.5 w-3.5" />
            </button>
            <span className="w-10 text-center text-[11px] text-muted2">
              {Math.round(zoom * 100)}%
            </span>
            <button
              aria-label="Zoom in"
              onClick={() => setZoom((value) => Math.min(1.25, value + 0.25))}
              disabled={zoom >= 1.25}
              className="rounded p-1 text-muted2 hover:bg-bg disabled:opacity-30"
            >
              <ZoomIn className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
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
        <div className="flex min-h-0 flex-1 justify-center overflow-auto bg-slate-100 p-3">
          <div
            className="h-full shrink-0 overflow-hidden bg-white shadow-sm transition-[width,transform]"
            style={{
              width: viewportWidth,
              maxWidth: viewport === "desktop" ? "100%" : undefined,
              transform: `scale(${zoom})`,
              transformOrigin: "top center",
            }}
          >
            <GrapeJSEditor
              document={document}
              selectedNodeId={selectedNodeId}
              onSelect={selectNode}
              onUpdate={setDocumentWithHistory}
            />
          </div>
        </div>
      </section>

      <aside className="flex w-72 shrink-0 flex-col border-l border-border2 bg-surface">
        <DesignTokensPanel document={document} onChange={setDocumentWithHistory} />
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
            breakpoint={viewport}
            onChange={setDocumentWithHistory}
          />
        </section>
      </aside>
    </div>
  );
}
