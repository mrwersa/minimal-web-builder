import { useEffect, useRef, useState } from "react";
import { Send, Trash2, MessageSquare } from "lucide-react";
import { useStore } from "../store";
import { cn } from "../lib/utils";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { Spinner } from "./ui/spinner";

export default function ChatPanel() {
  const chatMessages = useStore((s) => s.chatMessages);
  const busy = useStore((s) => s.busy);
  const runChat = useStore((s) => s.runChat);
  const clearChat = useStore((s) => s.clearChat);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [chatMessages, busy]);

  function submit() {
    const msg = input.trim();
    if (!msg || busy) return;
    setInput("");
    runChat(msg);
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex shrink-0 items-center justify-between border-b border-border px-4 py-2">
        <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
          <MessageSquare className="h-4 w-4 text-muted-foreground" />
          Chat
        </div>
        {chatMessages.length > 0 && (
          <button
            onClick={clearChat}
            className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-background hover:text-destructive"
          >
            <Trash2 className="h-3 w-3" />
            Clear
          </button>
        )}
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {chatMessages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
            <MessageSquare className="h-8 w-8 text-muted-foreground/40" />
            <p className="max-w-xs text-xs text-muted-foreground">
              Start a conversation. Describe what you want, ask questions, or request changes.
            </p>
          </div>
        )}
        {chatMessages.map((msg, i) => (
          <div
            key={i}
            className={cn(
              "rounded-lg px-3 py-2 text-sm",
              msg.role === "user"
                ? "ml-8 bg-primary text-primary-foreground"
                : "mr-8 bg-background text-foreground"
            )}
          >
            <p className="whitespace-pre-wrap break-words">{msg.content}</p>
          </div>
        ))}
        {busy && (
          <div className="mr-8 flex items-center gap-2 rounded-lg bg-background px-3 py-2">
            <Spinner size="sm" />
            <span className="text-xs text-muted-foreground">Thinking…</span>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="shrink-0 border-t border-border px-4 py-3">
        <div className="flex items-end gap-2">
          <Textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            placeholder={busy ? "Generating…" : "Describe a change or ask a question…"}
            disabled={busy}
            rows={1}
            className="max-h-32 min-h-[40px] flex-1"
          />
          <Button
            onClick={submit}
            disabled={busy || !input.trim()}
            className="h-[40px] px-3"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
