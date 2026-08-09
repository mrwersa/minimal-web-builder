import { useEffect, useState, type ReactNode } from "react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "../ui/accordion";
import { Input } from "../ui/input";
import { Textarea } from "../ui/textarea";

function useCommittedDraft(value: string, onCommit: (value: string) => void) {
  const [draft, setDraft] = useState(value);
  useEffect(() => setDraft(value), [value]);
  return {
    draft,
    setDraft,
    commit: () => {
      if (draft !== value) onCommit(draft);
    },
    reset: () => setDraft(value),
  };
}

export function InspectorSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <Accordion type="multiple" defaultValue={["section"]} className="-mx-3 border-t">
      <AccordionItem value="section" className="border-b-0">
        <AccordionTrigger>{title}</AccordionTrigger>
        <AccordionContent>{children}</AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}

export function CommitField({
  label,
  value,
  placeholder,
  onCommit,
}: {
  label: string;
  value: string;
  placeholder?: string;
  onCommit: (value: string) => void;
}) {
  const { draft, setDraft, commit, reset } = useCommittedDraft(value, onCommit);

  return (
    <label className="block space-y-1 text-[11px] font-medium text-muted-foreground">
      <span>{label}</span>
      <Input
        aria-label={label}
        value={draft}
        placeholder={placeholder}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={commit}
        onKeyDown={(event) => {
          if (event.key === "Enter") event.currentTarget.blur();
          if (event.key === "Escape") {
            reset();
            event.currentTarget.blur();
          }
        }}
      />
    </label>
  );
}

export function CommitTextarea({
  label,
  value,
  placeholder,
  rows = 7,
  onCommit,
}: {
  label: string;
  value: string;
  placeholder?: string;
  rows?: number;
  onCommit: (value: string) => void;
}) {
  const { draft, setDraft, commit, reset } = useCommittedDraft(value, onCommit);

  return (
    <label className="block space-y-1 text-xs font-medium text-muted-foreground">
      <span>{label}</span>
      <Textarea
        aria-label={label}
        value={draft}
        placeholder={placeholder}
        rows={rows}
        spellCheck={false}
        className="resize-y font-mono text-xs leading-relaxed"
        onChange={(event) => setDraft(event.target.value)}
        onBlur={commit}
        onKeyDown={(event) => {
          if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
            event.currentTarget.blur();
          }
          if (event.key === "Escape") {
            reset();
            event.currentTarget.blur();
          }
        }}
      />
    </label>
  );
}
