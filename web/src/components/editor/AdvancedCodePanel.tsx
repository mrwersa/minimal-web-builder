import { AlertTriangle } from "lucide-react";
import type { EditorDocumentV1 } from "../../editor/document";
import {
  advancedSourceValue,
  setAdvancedSource,
  type AdvancedSourceField,
} from "../../editor/advanced";
import { CommitTextarea } from "./EditorFields";

const FIELDS: ReadonlyArray<{
  field: AdvancedSourceField;
  label: string;
  placeholder: string;
  help: string;
}> = [
  {
    field: "headHtml",
    label: "Head HTML",
    placeholder: '<meta name="description" content="\u2026">',
    help: "Metadata, preload links, and other markup inserted inside <head>.",
  },
  {
    field: "css",
    label: "Custom CSS",
    placeholder: ".hero { min-height: 70vh; }",
    help: "Global CSS loaded after design tokens and before responsive overrides.",
  },
  {
    field: "bodyScripts",
    label: "Body script HTML",
    placeholder: "<script>\n  // Your JavaScript\n</script>",
    help: "One or more complete <script> tags inserted at the end of <body>.",
  },
];

export default function AdvancedCodePanel({
  document,
  onChange,
}: {
  document: EditorDocumentV1;
  onChange: (document: EditorDocumentV1) => void;
}) {
  return (
    <div className="min-h-0 flex-1 overflow-y-auto rounded-xl border border-border bg-surface p-4">
      <div className="mb-4 flex gap-2 rounded-lg border border-warning/30 bg-warning/10 p-3 text-xs text-warning">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
        <p>
          Advanced code bypasses visual controls. Invalid markup or scripts can break the
          page; every commit remains undoable, and preview execution stays sandboxed.
        </p>
      </div>
      <div className="space-y-4">
        {FIELDS.map(({ field, label, placeholder, help }) => (
          <div key={field} className="space-y-1">
            <CommitTextarea
              label={label}
              value={advancedSourceValue(document, field)}
              placeholder={placeholder}
              onCommit={(value) => onChange(setAdvancedSource(document, field, value))}
            />
            <p className="text-[11px] text-muted-foreground">{help}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
