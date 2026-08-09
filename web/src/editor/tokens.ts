import type { EditorDocumentV1 } from "./document";

export type DesignTokenGroup = "Color" | "Typography" | "Spacing" | "Shape" | "Layout";

export interface DesignTokenDefinition {
  name: string;
  label: string;
  group: DesignTokenGroup;
  placeholder: string;
  properties: readonly string[];
}

export const DESIGN_TOKEN_DEFINITIONS: readonly DesignTokenDefinition[] = [
  {
    name: "color-primary",
    label: "Primary color",
    group: "Color",
    placeholder: "#2563eb",
    properties: ["color", "background-color"],
  },
  {
    name: "color-secondary",
    label: "Secondary color",
    group: "Color",
    placeholder: "#64748b",
    properties: ["color", "background-color"],
  },
  {
    name: "color-background",
    label: "Background color",
    group: "Color",
    placeholder: "#ffffff",
    properties: ["color", "background-color"],
  },
  {
    name: "color-text",
    label: "Text color",
    group: "Color",
    placeholder: "#0f172a",
    properties: ["color", "background-color"],
  },
  {
    name: "font-heading",
    label: "Heading font",
    group: "Typography",
    placeholder: "Inter, sans-serif",
    properties: ["font-family"],
  },
  {
    name: "font-body",
    label: "Body font",
    group: "Typography",
    placeholder: "Inter, sans-serif",
    properties: ["font-family"],
  },
  {
    name: "font-size-base",
    label: "Base font size",
    group: "Typography",
    placeholder: "16px",
    properties: ["font-size"],
  },
  {
    name: "line-height-body",
    label: "Body line height",
    group: "Typography",
    placeholder: "1.5",
    properties: ["line-height"],
  },
  {
    name: "space-sm",
    label: "Small space",
    group: "Spacing",
    placeholder: "8px",
    properties: ["padding", "margin", "gap"],
  },
  {
    name: "space-md",
    label: "Medium space",
    group: "Spacing",
    placeholder: "16px",
    properties: ["padding", "margin", "gap"],
  },
  {
    name: "space-lg",
    label: "Large space",
    group: "Spacing",
    placeholder: "32px",
    properties: ["padding", "margin", "gap"],
  },
  {
    name: "radius",
    label: "Corner radius",
    group: "Shape",
    placeholder: "12px",
    properties: ["border-radius"],
  },
  {
    name: "container-width",
    label: "Container width",
    group: "Layout",
    placeholder: "1200px",
    properties: ["width", "max-width"],
  },
];

export function designTokenReference(name: string): string {
  return `var(--mwb-${name})`;
}

export function setDesignToken(
  document: EditorDocumentV1,
  name: string,
  value: string,
): EditorDocumentV1 {
  const designTokens = { ...(document.designTokens ?? {}) };
  if (value.trim()) designTokens[name] = value.trim();
  else delete designTokens[name];
  return { ...document, designTokens };
}

export function tokenOptions(
  document: EditorDocumentV1,
  property: string,
): { value: string; label: string }[] {
  return DESIGN_TOKEN_DEFINITIONS.filter(
    ({ name, properties }) =>
      properties.includes(property) && document.designTokens?.[name],
  ).map(({ name, label }) => ({ value: designTokenReference(name), label }));
}
