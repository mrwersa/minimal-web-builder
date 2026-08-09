import { useEffect, useState } from "react";
import type {
  EditorBreakpoint,
  EditorDocumentV1,
  ElementNode,
} from "../../editor/document";
import {
  editableText,
  elementStyleValue,
  setElementAttribute,
  setElementStyle,
  setElementText,
} from "../../editor/operations";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";

interface EditorInspectorProps {
  document: EditorDocumentV1;
  node: ElementNode | null;
  breakpoint: "desktop" | EditorBreakpoint;
  onChange: (document: EditorDocumentV1) => void;
}

function InspectorSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <details open className="rounded-lg border border-border2 p-2">
      <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-wide text-muted2">
        {title}
      </summary>
      <div className="mt-2 space-y-2">{children}</div>
    </details>
  );
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
  breakpoint,
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
  const styleValue = (property: string) =>
    elementStyleValue(document, node, property, breakpoint);
  const commitStyle = (property: string, value: string) =>
    onChange(setElementStyle(document, node.id, property, value, breakpoint));

  return (
    <div className="space-y-3 p-3" aria-label="Property inspector">
      <div>
        <div className="flex items-center justify-between gap-2">
          <div className="text-xs font-semibold text-text2">&lt;{node.tag}&gt;</div>
          <span className="rounded bg-bg px-1.5 py-0.5 text-[10px] capitalize text-muted2">
            {breakpoint}
          </span>
        </div>
        <div className="mt-0.5 truncate font-mono text-[10px] text-muted2">{node.id}</div>
      </div>

      <InspectorSection title="Content & attributes">
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
          <CommitField
            label="Link URL"
            value={node.attributes.href ?? ""}
            placeholder="https://example.com"
            onCommit={(value) => commitAttribute("href", value)}
          />
        )}
        {node.tag === "a" && (
          <CommitField
            label="Link target"
            value={node.attributes.target ?? ""}
            placeholder="_blank"
            onCommit={(value) => commitAttribute("target", value)}
          />
        )}
        {node.tag === "img" && (
          <CommitField
            label="Alternative text"
            value={node.attributes.alt ?? ""}
            onCommit={(value) => commitAttribute("alt", value)}
          />
        )}
      </InspectorSection>

      <InspectorSection title="Spacing & size">
        {[
          ["Padding", "padding", "16px 24px"],
          ["Margin", "margin", "0 auto"],
          ["Gap", "gap", "16px"],
          ["Width", "width", "100%"],
          ["Max width", "max-width", "1200px"],
        ].map(([label, property, placeholder]) => (
          <CommitField
            key={property}
            label={label}
            value={styleValue(property)}
            placeholder={placeholder}
            onCommit={(value) => commitStyle(property, value)}
          />
        ))}
      </InspectorSection>

      <InspectorSection title="Typography">
        {[
          ["Font size", "font-size", "16px"],
          ["Font family", "font-family", "Inter, sans-serif"],
          ["Line height", "line-height", "1.5"],
        ].map(([label, property, placeholder]) => (
          <CommitField
            key={property}
            label={label}
            value={styleValue(property)}
            placeholder={placeholder}
            onCommit={(value) => commitStyle(property, value)}
          />
        ))}
        <label className="block space-y-1 text-[11px] font-medium text-muted2">
          <span>Font weight</span>
          <Select
            value={styleValue("font-weight")}
            options={[
              { value: "", label: "Inherit" },
              { value: "400", label: "Regular" },
              { value: "500", label: "Medium" },
              { value: "600", label: "Semibold" },
              { value: "700", label: "Bold" },
            ]}
            onChange={(value) => commitStyle("font-weight", value)}
          />
        </label>
        <label className="block space-y-1 text-[11px] font-medium text-muted2">
          <span>Text align</span>
          <Select
            value={styleValue("text-align")}
            options={[
              { value: "", label: "Inherit" },
              { value: "left", label: "Left" },
              { value: "center", label: "Center" },
              { value: "right", label: "Right" },
            ]}
            onChange={(value) => commitStyle("text-align", value)}
          />
        </label>
      </InspectorSection>

      <InspectorSection title="Color">
        <CommitField
          label="Text color"
          value={styleValue("color")}
          placeholder="#111827"
          onCommit={(value) => commitStyle("color", value)}
        />
        <CommitField
          label="Background"
          value={styleValue("background-color")}
          placeholder="#ffffff"
          onCommit={(value) => commitStyle("background-color", value)}
        />
      </InspectorSection>

      <InspectorSection title="Layout & visibility">
        <label className="block space-y-1 text-[11px] font-medium text-muted2">
          <span>Display</span>
          <Select
            value={styleValue("display")}
            options={[
              { value: "", label: "Default" },
              { value: "block", label: "Block" },
              { value: "flex", label: "Flex" },
              { value: "grid", label: "Grid" },
              { value: "inline-flex", label: "Inline flex" },
              { value: "none", label: "Hidden" },
            ]}
            onChange={(value) => commitStyle("display", value)}
          />
        </label>
        <label className="block space-y-1 text-[11px] font-medium text-muted2">
          <span>Direction</span>
          <Select
            value={styleValue("flex-direction")}
            options={[
              { value: "", label: "Default" },
              { value: "row", label: "Row" },
              { value: "column", label: "Column" },
              { value: "row-reverse", label: "Row reversed" },
            ]}
            onChange={(value) => commitStyle("flex-direction", value)}
          />
        </label>
        <CommitField
          label="Grid columns"
          value={styleValue("grid-template-columns")}
          placeholder="repeat(3, 1fr)"
          onCommit={(value) => commitStyle("grid-template-columns", value)}
        />
      </InspectorSection>
    </div>
  );
}
