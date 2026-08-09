import type {
  DocumentNode,
  EditorBreakpoint,
  EditorDocumentV1,
  ElementNode,
} from "./document";

export interface ElementEntry {
  node: ElementNode;
  parentId: string | null;
  depth: number;
  index: number;
}

function walk(
  nodes: DocumentNode[],
  parentId: string | null,
  depth: number,
  entries: ElementEntry[],
): void {
  nodes.forEach((node, index) => {
    if (node.type !== "element") return;
    entries.push({ node, parentId, depth, index });
    walk(node.children, node.id, depth + 1, entries);
  });
}

export function elementEntries(document: EditorDocumentV1): ElementEntry[] {
  const entries: ElementEntry[] = [];
  walk(document.body, null, 0, entries);
  return entries;
}

export function elementPath(
  document: EditorDocumentV1,
  nodeId: string,
): ElementNode[] {
  const visit = (nodes: DocumentNode[], path: ElementNode[]): ElementNode[] | null => {
    for (const node of nodes) {
      if (node.type !== "element") continue;
      const nextPath = [...path, node];
      if (node.id === nodeId) return nextPath;
      const match = visit(node.children, nextPath);
      if (match) return match;
    }
    return null;
  };
  return visit(document.body, []) ?? [];
}

function updateNodes(
  nodes: DocumentNode[],
  nodeId: string,
  update: (node: ElementNode) => ElementNode,
): DocumentNode[] {
  let changed = false;
  const next = nodes.map((node) => {
    if (node.type !== "element") return node;
    if (node.id === nodeId) {
      changed = true;
      return update(node);
    }
    const children = updateNodes(node.children, nodeId, update);
    if (children === node.children) return node;
    changed = true;
    return { ...node, children };
  });
  return changed ? next : nodes;
}

export function updateElement(
  document: EditorDocumentV1,
  nodeId: string,
  update: (node: ElementNode) => ElementNode,
): EditorDocumentV1 {
  const body = updateNodes(document.body, nodeId, update);
  return body === document.body ? document : { ...document, body };
}

export function setElementAttribute(
  document: EditorDocumentV1,
  nodeId: string,
  name: string,
  value: string,
): EditorDocumentV1 {
  return updateElement(document, nodeId, (node) => {
    const attributes = { ...node.attributes };
    if (value.trim()) attributes[name] = value.trim();
    else delete attributes[name];
    return { ...node, attributes };
  });
}

export function editableText(node: ElementNode): string | null {
  if (node.children.some((child) => child.type === "element")) return null;
  return node.children
    .filter((child) => child.type === "text")
    .map((child) => child.value)
    .join("");
}

export function setElementText(
  document: EditorDocumentV1,
  nodeId: string,
  value: string,
): EditorDocumentV1 {
  return updateElement(document, nodeId, (node) => ({
    ...node,
    children: value ? [{ type: "text", value }] : [],
  }));
}

function styleDeclaration(cssText: string): CSSStyleDeclaration {
  const element = globalThis.document.createElement("div");
  element.style.cssText = cssText;
  return element.style;
}

export function elementStyleValue(
  document: EditorDocumentV1,
  node: ElementNode,
  property: string,
  breakpoint: "desktop" | EditorBreakpoint = "desktop",
): string {
  if (breakpoint !== "desktop") {
    return document.responsiveStyles?.[node.id]?.[breakpoint]?.[property] ?? "";
  }
  return styleDeclaration(node.attributes.style ?? "").getPropertyValue(property);
}

export function setElementStyle(
  document: EditorDocumentV1,
  nodeId: string,
  property: string,
  value: string,
  breakpoint: "desktop" | EditorBreakpoint = "desktop",
): EditorDocumentV1 {
  if (breakpoint === "desktop") {
    return updateElement(document, nodeId, (node) => {
      const declaration = styleDeclaration(node.attributes.style ?? "");
      if (value.trim()) declaration.setProperty(property, value.trim());
      else declaration.removeProperty(property);
      const attributes = { ...node.attributes };
      if (declaration.cssText) attributes.style = declaration.cssText;
      else delete attributes.style;
      return { ...node, attributes };
    });
  }

  const responsiveStyles = structuredClone(document.responsiveStyles ?? {});
  const nodeStyles = (responsiveStyles[nodeId] ??= {});
  const breakpointStyles = (nodeStyles[breakpoint] ??= {});
  if (value.trim()) breakpointStyles[property] = value.trim();
  else delete breakpointStyles[property];
  if (Object.keys(breakpointStyles).length === 0) delete nodeStyles[breakpoint];
  if (Object.keys(nodeStyles).length === 0) delete responsiveStyles[nodeId];
  return { ...document, responsiveStyles };
}

function containsElement(node: ElementNode, nodeId: string): boolean {
  return node.children.some(
    (child) =>
      child.type === "element" &&
      (child.id === nodeId || containsElement(child, nodeId)),
  );
}

function detach(
  nodes: DocumentNode[],
  nodeId: string,
): { nodes: DocumentNode[]; detached: ElementNode | null } {
  let detached: ElementNode | null = null;
  const next: DocumentNode[] = [];
  for (const node of nodes) {
    if (node.type === "element" && node.id === nodeId) {
      detached = node;
      continue;
    }
    if (node.type === "element" && !detached) {
      const nested = detach(node.children, nodeId);
      if (nested.detached) {
        detached = nested.detached;
        next.push({ ...node, children: nested.nodes });
        continue;
      }
    }
    next.push(node);
  }
  return { nodes: detached ? next : nodes, detached };
}

function insertBefore(
  nodes: DocumentNode[],
  targetId: string,
  inserted: ElementNode,
): { nodes: DocumentNode[]; inserted: boolean } {
  const targetIndex = nodes.findIndex(
    (node) => node.type === "element" && node.id === targetId,
  );
  if (targetIndex >= 0) {
    return {
      nodes: [...nodes.slice(0, targetIndex), inserted, ...nodes.slice(targetIndex)],
      inserted: true,
    };
  }
  for (let index = 0; index < nodes.length; index += 1) {
    const node = nodes[index];
    if (node.type !== "element") continue;
    const nested = insertBefore(node.children, targetId, inserted);
    if (nested.inserted) {
      const next = [...nodes];
      next[index] = { ...node, children: nested.nodes };
      return { nodes: next, inserted: true };
    }
  }
  return { nodes, inserted: false };
}

export function moveElementBefore(
  document: EditorDocumentV1,
  nodeId: string,
  targetId: string,
): EditorDocumentV1 {
  if (nodeId === targetId) return document;
  const sourcePath = elementPath(document, nodeId);
  const source = sourcePath[sourcePath.length - 1];
  if (!source || containsElement(source, targetId)) return document;
  const detached = detach(document.body, nodeId);
  if (!detached.detached) return document;
  const inserted = insertBefore(detached.nodes, targetId, detached.detached);
  return inserted.inserted ? { ...document, body: inserted.nodes } : document;
}

export function elementLabel(node: ElementNode): string {
  const identity = node.attributes["aria-label"] || node.attributes.id;
  const text = editableText(node)?.trim().replace(/\s+/g, " ");
  const detail = identity || text?.slice(0, 28);
  return detail ? `${node.tag} · ${detail}` : node.tag;
}
