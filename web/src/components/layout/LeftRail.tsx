import { FolderKanban, Layers3, SlidersHorizontal } from "lucide-react";
import { useStore } from "../../store";
import ProjectPanel from "../ProjectPanel";
import SetupPanel from "../SetupPanel";
import LayerTree from "../editor/LayerTree";
import { ScrollArea } from "../ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";

export default function LeftRail() {
  const editorDocument = useStore((state) => state.editorDocument);
  const selectedNodeId = useStore((state) => state.selectedNodeId);
  const selectNode = useStore((state) => state.selectNode);
  const setDocumentWithHistory = useStore((state) => state.setDocumentWithHistory);

  return (
    <aside className="flex w-72 shrink-0 flex-col border-r bg-surface">
      <Tabs defaultValue="layers" className="flex min-h-0 flex-1 flex-col">
        <div className="border-b p-2">
          <TabsList className="w-full">
            <TabsTrigger value="layers" className="flex-1">
              <Layers3 /> Layers
            </TabsTrigger>
            <TabsTrigger value="project" className="flex-1">
              <FolderKanban /> Project
            </TabsTrigger>
            <TabsTrigger value="setup" className="flex-1">
              <SlidersHorizontal /> Setup
            </TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="layers" className="min-h-0 flex-1">
          <ScrollArea className="h-full">
            {editorDocument ? (
              <LayerTree
                document={editorDocument}
                selectedNodeId={selectedNodeId}
                onSelect={selectNode}
                onChange={setDocumentWithHistory}
              />
            ) : (
              <p className="p-4 text-xs text-muted-foreground">
                Generate a page to browse its element tree.
              </p>
            )}
          </ScrollArea>
        </TabsContent>

        <TabsContent value="project" className="min-h-0 flex-1">
          <ScrollArea className="h-full">
            <div className="p-3">
              <ProjectPanel />
            </div>
          </ScrollArea>
        </TabsContent>

        <TabsContent value="setup" className="min-h-0 flex-1">
          <ScrollArea className="h-full">
            <SetupPanel />
          </ScrollArea>
        </TabsContent>
      </Tabs>
    </aside>
  );
}
