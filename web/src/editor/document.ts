export const DOCUMENT_SCHEMA_VERSION = 1 as const;
export const NODE_ID_ATTRIBUTE = "data-mwb-id";

export interface ElementNode {
  type: "element";
  id: string;
  tag: string;
  attributes: Record<string, string>;
  children: DocumentNode[];
}

export interface TextNode {
  type: "text";
  value: string;
}

export interface CommentNode {
  type: "comment";
  value: string;
}

export type DocumentNode = ElementNode | TextNode | CommentNode;

export interface EditorDocumentV1 {
  schemaVersion: typeof DOCUMENT_SCHEMA_VERSION;
  doctype: string;
  htmlAttributes: Record<string, string>;
  headHtml: string;
  bodyAttributes: Record<string, string>;
  body: DocumentNode[];
  css: string;
  bodyScripts: string[];
}

const VOID_ELEMENTS = new Set([
  "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
  "meta", "param", "source", "track", "wbr",
]);

function attributes(element: Element): Record<string, string> {
  return Object.fromEntries(
    Array.from(element.attributes)
      .filter(({ name }) => name !== NODE_ID_ATTRIBUTE)
      .map(({ name, value }) => [name, value]),
  );
}

function hash(value: string): string {
  let result = 0x811c9dc5;
  for (let index = 0; index < value.length; index += 1) {
    result ^= value.charCodeAt(index);
    result = Math.imul(result, 0x01000193);
  }
  return (result >>> 0).toString(36);
}

function validNodeId(value: string | null, usedIds: Set<string>): string | null {
  if (!value || !/^[a-zA-Z0-9_-]{1,80}$/.test(value) || usedIds.has(value)) return null;
  return value;
}

function uniqueNodeId(seed: string, usedIds: Set<string>): string {
  const base = `node-${hash(seed)}`;
  let candidate = base;
  let suffix = 2;
  while (usedIds.has(candidate)) {
    candidate = `${base}-${suffix}`;
    suffix += 1;
  }
  return candidate;
}

function parseNode(node: Node, path: string, usedIds: Set<string>): DocumentNode | null {
  if (node.nodeType === Node.TEXT_NODE) {
    return { type: "text", value: node.textContent ?? "" };
  }
  if (node.nodeType === Node.COMMENT_NODE) {
    return { type: "comment", value: node.textContent ?? "" };
  }
  if (node.nodeType !== Node.ELEMENT_NODE) return null;

  const element = node as Element;
  const tag = element.tagName.toLowerCase();
  const existingId = validNodeId(element.getAttribute(NODE_ID_ATTRIBUTE), usedIds);
  const id = existingId ?? uniqueNodeId(`${path}:${tag}`, usedIds);
  usedIds.add(id);
  const children = Array.from(element.childNodes)
    .map((child, index) => parseNode(child, `${path}.${index}`, usedIds))
    .filter((child): child is DocumentNode => child !== null);
  return { type: "element", id, tag, attributes: attributes(element), children };
}

function parseNodes(parent: ParentNode, usedIds = new Set<string>()): DocumentNode[] {
  return Array.from(parent.childNodes)
    .map((node, index) => parseNode(node, String(index), usedIds))
    .filter((node): node is DocumentNode => node !== null);
}

function escapeText(value: string): string {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

function escapeAttribute(value: string): string {
  return escapeText(value).replaceAll('"', "&quot;");
}

function serializeAttributes(values: Record<string, string>): string {
  return Object.entries(values)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([name, value]) => ` ${name}="${escapeAttribute(value)}"`)
    .join("");
}

function compileNode(node: DocumentNode, includeEditorIds: boolean): string {
  if (node.type === "text") return escapeText(node.value);
  if (node.type === "comment") return `<!--${node.value.replaceAll("-->", "--&gt;")}-->`;
  const values = includeEditorIds
    ? { ...node.attributes, [NODE_ID_ATTRIBUTE]: node.id }
    : node.attributes;
  const opening = `<${node.tag}${serializeAttributes(values)}>`;
  if (VOID_ELEMENTS.has(node.tag)) return opening;
  return `${opening}${node.children.map((child) => compileNode(child, includeEditorIds)).join("")}</${node.tag}>`;
}

export function parseEditorDocument(html: string): EditorDocumentV1 {
  const parser = new DOMParser();
  const parsed = parser.parseFromString(html, "text/html");
  const head = parsed.head.cloneNode(true) as HTMLHeadElement;
  const body = parsed.body.cloneNode(true) as HTMLBodyElement;
  const css = Array.from(parsed.querySelectorAll("style"))
    .map((style) => style.textContent ?? "")
    .filter(Boolean)
    .join("\n\n");
  const bodyScripts = Array.from(body.querySelectorAll("script")).map(
    (script) => script.outerHTML,
  );

  head.querySelectorAll("style").forEach((style) => style.remove());
  body.querySelectorAll("style, script").forEach((element) => element.remove());

  return {
    schemaVersion: DOCUMENT_SCHEMA_VERSION,
    doctype: html.match(/<!doctype[^>]*>/i)?.[0] ?? "<!DOCTYPE html>",
    htmlAttributes: attributes(parsed.documentElement),
    headHtml: head.innerHTML.trim(),
    bodyAttributes: attributes(parsed.body),
    body: parseNodes(body),
    css,
    bodyScripts,
  };
}

export function compileCanvas(document: EditorDocumentV1): string {
  return document.body.map((node) => compileNode(node, true)).join("");
}

export function compileDocument(
  document: EditorDocumentV1,
  { includeEditorIds = true }: { includeEditorIds?: boolean } = {},
): string {
  const headItems = [
    document.headHtml,
    document.css.trim() ? `<style>\n${document.css.trim()}\n</style>` : "",
  ].filter(Boolean);
  const bodyItems = [
    document.body.map((node) => compileNode(node, includeEditorIds)).join(""),
    ...document.bodyScripts,
  ].filter(Boolean);
  return [
    document.doctype,
    `<html${serializeAttributes(document.htmlAttributes)}>`,
    `<head>${headItems.join("\n")}</head>`,
    `<body${serializeAttributes(document.bodyAttributes)}>${bodyItems.join("\n")}</body></html>`,
  ].join("\n");
}

export function replaceCanvas(
  document: EditorDocumentV1,
  bodyHtml: string,
  css: string,
): EditorDocumentV1 {
  const parsed = new DOMParser().parseFromString(`<body>${bodyHtml}</body>`, "text/html");
  return { ...document, body: parseNodes(parsed.body), css };
}

export function findNode(
  document: EditorDocumentV1,
  nodeId: string,
): ElementNode | null {
  const pending = [...document.body];
  while (pending.length > 0) {
    const node = pending.shift();
    if (node?.type !== "element") continue;
    if (node.id === nodeId) return node;
    pending.unshift(...node.children);
  }
  return null;
}
