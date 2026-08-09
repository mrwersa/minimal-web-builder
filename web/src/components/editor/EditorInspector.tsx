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
import { tokenOptions } from "../../editor/tokens";
import { Select } from "../ui/Select";
import { CommitField, InspectorSection } from "./EditorFields";

interface EditorInspectorProps {
  document: EditorDocumentV1;
  node: ElementNode | null;
  breakpoint: "desktop" | EditorBreakpoint;
  onChange: (document: EditorDocumentV1) => void;
}

function TokenStyleField({
  document,
  label,
  value,
  placeholder,
  property,
  onCommit,
}: {
  document: EditorDocumentV1;
  label: string;
  value: string;
  placeholder: string;
  property: string;
  onCommit: (value: string) => void;
}) {
  const options = tokenOptions(document, property);
  return (
    <div className="space-y-1">
      <CommitField
        label={label}
        value={value}
        placeholder={placeholder}
        onCommit={onCommit}
      />
      {options.length > 0 && (
        <label className="block">
          <span className="sr-only">{label} token</span>
          <Select
            value={options.some((option) => option.value === value) ? value : ""}
            options={[{ value: "", label: `Use ${label.toLowerCase()} token…` }, ...options]}
            onChange={(next) => {
              if (next) onCommit(next);
            }}
            className="h-7 text-xs"
          />
        </label>
      )}
    </div>
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
        {([
          ["Padding", "padding", "16px 24px"],
          ["Margin", "margin", "0 auto"],
          ["Gap", "gap", "16px"],
          ["Width", "width", "100%"],
          ["Max width", "max-width", "1200px"],
          ["Border radius", "border-radius", "12px"],
        ] as const).map(([label, property, placeholder]) => (
          <TokenStyleField
            key={property}
            document={document}
            label={label}
            value={styleValue(property)}
            placeholder={placeholder}
            property={property}
            onCommit={(value) => commitStyle(property, value)}
          />
        ))}
      </InspectorSection>

      <InspectorSection title="Typography">
        {([
          ["Font size", "font-size", "16px"],
          ["Font family", "font-family", "Inter, sans-serif"],
          ["Line height", "line-height", "1.5"],
        ] as const).map(([label, property, placeholder]) => (
          <TokenStyleField
            key={property}
            document={document}
            label={label}
            value={styleValue(property)}
            placeholder={placeholder}
            property={property}
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
        <TokenStyleField
          document={document}
          label="Text color"
          value={styleValue("color")}
          placeholder="#111827"
          property="color"
          onCommit={(value) => commitStyle("color", value)}
        />
        <TokenStyleField
          document={document}
          label="Background"
          value={styleValue("background-color")}
          placeholder="#ffffff"
          property="background-color"
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
