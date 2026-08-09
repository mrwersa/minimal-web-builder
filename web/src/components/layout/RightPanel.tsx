import { MessageSquare, SlidersHorizontal } from "lucide-react";
import { findNode } from "../../editor/document";
import { useStore } from "../../store";
import ChatPanel from "../ChatPanel";
import DesignTokensPanel from "../editor/DesignTokensPanel";
import EditorInspector from "../editor/EditorInspector";
import ElementAiPanel from "../editor/ElementAiPanel";
import { ScrollArea } from "../ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";

export default function RightPanel() {
  const editorDocument = useStore((state) => state.editorDocument);
  const selectedNodeId = useStore((state) => state.selectedNodeId);
  const setDocumentWithHistory = useStore((state) => state.setDocumentWithHistory);
  const viewport = useStore((state) => state.viewport);
  const selectedNode =
    editorDocument && selectedNodeId ? findNode(editorDocument, selectedNodeId) : null;

  return (
    <aside className="flex w-80 shrink-0 flex-col border-l bg-surface">
      <Tabs defaultValue="inspector" className="flex min-h-0 flex-1 flex-col">
        <div className="border-b p-2">
          <TabsList className="w-full">
            <TabsTrigger value="inspector" className="flex-1">
              <SlidersHorizontal /> Inspector
            </TabsTrigger>
            <TabsTrigger value="chat" className="flex-1">
              <MessageSquare /> Chat
            </TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="inspector" className="min-h-0 flex-1">
          <ScrollArea className="h-full">
            {editorDocument ? (
              <>
                <DesignTokensPanel
                  document={editorDocument}
                  onChange={setDocumentWithHistory}
                />
                <ElementAiPanel node={selectedNode} />
                <EditorInspector
                  document={editorDocument}
                  node={selectedNode}
                  breakpoint={viewport}
                  onChange={setDocumentWithHistory}
                />
              </>
            ) : (
              <p className="p-4 text-xs text-muted-foreground">
                Generate a page to inspect and edit its elements.
              </p>
            )}
          </ScrollArea>
        </TabsContent>

        <TabsContent value="chat" className="min-h-0 flex-1">
          <ChatPanel />
        </TabsContent>
      </Tabs>
    </aside>
  );
}
