import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import type { ElementNode } from "../../editor/document";
import { useStore } from "../../store";
import { Button } from "../ui/button";
import { Input } from "../ui/input";

export default function ElementAiPanel({ node }: { node: ElementNode | null }) {
  const [instruction, setInstruction] = useState("");
  const runChat = useStore((state) => state.runChat);
  const busy = useStore((state) => state.busy);

  useEffect(() => setInstruction(""), [node?.id]);
  if (!node) return null;

  const submit = () => {
    const message = instruction.trim();
    if (!message || busy) return;
    setInstruction("");
    void runChat(message, node.id);
  };

  return (
    <div className="border-b border-border p-3">
      <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-foreground">
        <Sparkles className="h-3.5 w-3.5 text-primary" /> AI edit this element
      </div>
      <p className="mb-2 text-[11px] leading-relaxed text-muted-foreground">
        The update is restricted to &lt;{node.tag}&gt; and its descendants.
      </p>
      <form
        className="flex gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <Input
          aria-label="Element AI instruction"
          value={instruction}
          placeholder="Make this heading warmer…"
          disabled={busy}
          onChange={(event) => setInstruction(event.target.value)}
        />
        <Button
          type="submit"
          size="sm"
          disabled={busy || !instruction.trim()}
          aria-label="Apply AI edit to selected element"
        >
          Apply
        </Button>
      </form>
    </div>
  );
}
