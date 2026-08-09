import { useState } from "react";
import { ArrowRight, Sparkles } from "lucide-react";
import { useStore } from "../store";
import { Button } from "./ui/button";
import { Spinner } from "./ui/spinner";
import { Textarea } from "./ui/textarea";

const EXAMPLES = [
  "A minimal landing page for a coffee shop called Fern — hero, three feature cards, footer",
  "A personal portfolio with an about section, project grid, and contact links",
  "A simple blog homepage with a featured post and recent posts list",
];

/** First-run surface: the prompt is the primary action, examples are the ramp. */
export default function EmptyState() {
  const busy = useStore((state) => state.busy);
  const runGenerate = useStore((state) => state.runGenerate);
  const constraintMode = useStore((state) => state.constraintMode);
  const runConstraints = useStore((state) => state.runConstraints);
  const [prompt, setPrompt] = useState("");

  function submit() {
    const value = prompt.trim();
    if (!value || busy) return;
    setPrompt("");
    runGenerate(value);
  }

  return (
    <div className="canvas-backdrop flex min-h-0 flex-1 items-center justify-center overflow-y-auto p-6">
      <div className="flex w-full max-w-xl flex-col items-center gap-6 rounded-xl border bg-surface p-8 shadow-sm">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Sparkles className="h-6 w-6" />
        </div>
        <div className="space-y-1 text-center">
          <h2 className="text-lg font-semibold">Describe the site you want</h2>
          <p className="text-sm text-muted-foreground">
            Start from a sentence, then refine it visually or by chat.
          </p>
        </div>

        <div className="flex w-full items-end gap-2">
          <Textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                submit();
              }
            }}
            placeholder="Describe the website you want to create…"
            rows={2}
            className="flex-1"
          />
          <Button
            size="lg"
            onClick={submit}
            disabled={busy || !prompt.trim()}
          >
            {busy && <Spinner size="sm" />}
            Generate
          </Button>
        </div>

        <div className="flex w-full flex-col gap-1.5">
          {EXAMPLES.map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => setPrompt(example)}
              className="group flex items-center gap-2 rounded-md border px-3 py-2 text-left text-xs text-muted-foreground transition-colors hover:border-primary hover:text-primary"
            >
              <span className="flex-1">{example}</span>
              <ArrowRight className="h-3.5 w-3.5 shrink-0 opacity-0 transition-opacity group-hover:opacity-100" />
            </button>
          ))}
        </div>

        {constraintMode && (
          <Button variant="link" size="sm" disabled={busy} onClick={runConstraints}>
            Or generate from your constraint selections
          </Button>
        )}
      </div>
    </div>
  );
}
