import { useEffect, useState } from "react";
import type { EditorDocumentV1, ElementNode } from "../../editor/document";
import {
  editableText,
  setElementAttribute,
  setElementText,
} from "../../editor/operations";
import { Input } from "../ui/Input";

interface EditorInspectorProps {
  document: EditorDocumentV1;
  node: ElementNode | null;
  onChange: (document: EditorDocumentV1) => void;
}

function CommitField({
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
  const [draft, setDraft] = useState(value);
  useEffect(() => setDraft(value), [value]);

  const commit = () => {
    if (draft !== value) onCommit(draft);
  };

  return (
    <label className="block space-y-1 text-[11px] font-medium text-muted2">
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
            setDraft(value);
            event.currentTarget.blur();
          }
        }}
      />
    </label>
  );
}

export default function EditorInspector({
  document,
  node,
  onChange,
}: EditorInspectorProps) {
  if (!node) {
    return (
      <div className="p-3 text-xs text-muted2">
        Select an element on the canvas or in Layers to edit its properties.
      </div>
    );
  }

  const text = editableText(node);
  const commitAttribute = (name: string, value: string) =>
    onChange(setElementAttribute(document, node.id, name, value));

  return (
    <div className="space-y-3 p-3" aria-label="Property inspector">
      <div>
        <div className="text-xs font-semibold text-text2">&lt;{node.tag}&gt;</div>
        <div className="mt-0.5 truncate font-mono text-[10px] text-muted2">{node.id}</div>
      </div>

      {text !== null && (
        <CommitField
          label="Text content"
          value={text}
          onCommit={(value) => onChange(setElementText(document, node.id, value))}
        />
      )}
      <CommitField
        label="CSS classes"
        value={node.attributes.class ?? ""}
        placeholder="hero centered"
        onCommit={(value) => commitAttribute("class", value)}
      />
      <CommitField
        label="Element ID"
        value={node.attributes.id ?? ""}
        placeholder="section-name"
        onCommit={(value) => commitAttribute("id", value)}
      />
      <CommitField
        label="Accessible label"
        value={node.attributes["aria-label"] ?? ""}
        onCommit={(value) => commitAttribute("aria-label", value)}
      />
      {node.tag === "a" && (
        <>
          <CommitField
            label="Link URL"
            value={node.attributes.href ?? ""}
            placeholder="https://example.com"
            onCommit={(value) => commitAttribute("href", value)}
          />
          <CommitField
            label="Link target"
            value={node.attributes.target ?? ""}
            placeholder="_blank"
            onCommit={(value) => commitAttribute("target", value)}
          />
        </>
      )}
      {node.tag === "img" && (
        <CommitField
          label="Alternative text"
          value={node.attributes.alt ?? ""}
          onCommit={(value) => commitAttribute("alt", value)}
        />
      )}
    </div>
  );
}
