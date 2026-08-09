import type { EditorDocumentV1 } from "./document";

export type AdvancedSourceField = "headHtml" | "css" | "bodyScripts";

export function advancedSourceValue(
  document: EditorDocumentV1,
  field: AdvancedSourceField,
): string {
  return field === "bodyScripts"
    ? document.bodyScripts.join("\n\n")
    : document[field];
}

export function setAdvancedSource(
  document: EditorDocumentV1,
  field: AdvancedSourceField,
  value: string,
): EditorDocumentV1 {
  const normalized = value.trim();
  if (field === "bodyScripts") {
    return { ...document, bodyScripts: normalized ? [normalized] : [] };
  }
  return { ...document, [field]: normalized };
}
