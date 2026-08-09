export const DOCUMENT_SCHEMA_VERSION = 1 as const;
export const NODE_ID_ATTRIBUTE = "data-mwb-id";
export type EditorBreakpoint = "tablet" | "mobile";
export type ResponsiveStyleMap = Record<
  string,
  Partial<Record<EditorBreakpoint, Record<string, string>>>
>;
export type DesignTokenMap = Record<string, string>;

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
  responsiveStyles?: ResponsiveStyleMap;
  designTokens?: DesignTokenMap;
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

function compileNode(
  node: DocumentNode,
  includeEditorIds: boolean,
  responsiveNodeIds: Set<string>,
): string {
  if (node.type === "text") return escapeText(node.value);
  if (node.type === "comment") return `<!--${node.value.replaceAll("-->", "--&gt;")}-->`;
  const values = { ...node.attributes };
  if (includeEditorIds) values[NODE_ID_ATTRIBUTE] = node.id;
  else if (responsiveNodeIds.has(node.id)) {
    values.class = Array.from(
      new Set([
        ...(values.class ?? "").split(/\s+/).filter(Boolean),
        `mwb-node-${node.id}`,
      ]),
    ).join(" ");
  }
  const opening = `<${node.tag}${serializeAttributes(values)}>`;
  if (VOID_ELEMENTS.has(node.tag)) return opening;
  return `${opening}${node.children
    .map((child) => compileNode(child, includeEditorIds, responsiveNodeIds))
    .join("")}</${node.tag}>`;
}

function extractDesignTokens(css: string): {
  css: string;
  designTokens: DesignTokenMap;
} {
  const designTokens: DesignTokenMap = {};
  const withoutTokens = css.replace(
    /:root\s*\{([^{}]*)\}/gi,
    (block, declarations: string) => {
      const remaining = declarations.replace(
        /--mwb-([a-z][a-z0-9-]{0,79})\s*:\s*([^;{}]+);?/gi,
        (_declaration, name: string, value: string) => {
          designTokens[name.toLowerCase()] = value.trim();
          return "";
        },
      );
      return remaining.trim() ? block.replace(declarations, remaining) : "";
    },
  );
  return { css: withoutTokens.trim(), designTokens };
}

export function parseEditorDocument(html: string): EditorDocumentV1 {
  const parser = new DOMParser();
  const parsed = parser.parseFromString(html, "text/html");
  const head = parsed.head.cloneNode(true) as HTMLHeadElement;
  const body = parsed.body.cloneNode(true) as HTMLBodyElement;
  const compiledCss = Array.from(parsed.querySelectorAll("style"))
    .map((style) => style.textContent ?? "")
    .filter(Boolean)
    .join("\n\n");
  const { css, designTokens } = extractDesignTokens(compiledCss);
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
    responsiveStyles: {},
    designTokens,
  };
}

export function compileCanvas(document: EditorDocumentV1): string {
  return document.body
    .map((node) => compileNode(node, true, new Set()))
    .join("");
}

function cssDeclarations(values: Record<string, string>): string {
  return Object.entries(values)
    .filter(([, value]) => value.trim())
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([property, value]) => `${property}: ${value.trim()};`)
    .join(" ");
}

export function compileDesignTokenCss(document: EditorDocumentV1): string {
  const declarations = Object.entries(document.designTokens ?? {})
    .filter(([, value]) => value.trim())
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([name, value]) => `--mwb-${name}: ${value.trim()};`);
  return declarations.length > 0 ? `:root { ${declarations.join(" ")} }` : "";
}

export function compileResponsiveCss(
  document: EditorDocumentV1,
  { includeEditorIds = true }: { includeEditorIds?: boolean } = {},
): string {
  const styles = document.responsiveStyles ?? {};
  const blocks: string[] = [];
  for (const [breakpoint, width] of [
    ["tablet", 1023],
    ["mobile", 639],
  ] as const) {
    const rules = Object.entries(styles)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([nodeId, byBreakpoint]) => {
        const declarations = cssDeclarations(byBreakpoint[breakpoint] ?? {});
        if (!declarations) return "";
        const selector = includeEditorIds
          ? `[${NODE_ID_ATTRIBUTE}="${nodeId}"]`
          : `.mwb-node-${nodeId}`;
        return `${selector} { ${declarations} }`;
      })
      .filter(Boolean);
    if (rules.length > 0) {
      blocks.push(`@media (max-width: ${width}px) {\n${rules.join("\n")}\n}`);
    }
  }
  return blocks.join("\n");
}

export function compileDocument(
  document: EditorDocumentV1,
  { includeEditorIds = true }: { includeEditorIds?: boolean } = {},
): string {
  const compiledCss = [
    compileDesignTokenCss(document),
    document.css.trim(),
    compileResponsiveCss(document, { includeEditorIds }),
  ]
    .filter(Boolean)
    .join("\n\n")
    .trim();
  const headItems = [
    document.headHtml,
    compiledCss ? `<style>\n${compiledCss}\n</style>` : "",
  ].filter(Boolean);
  const responsiveNodeIds = new Set(Object.keys(document.responsiveStyles ?? {}));
  const bodyItems = [
    document.body
      .map((node) => compileNode(node, includeEditorIds, responsiveNodeIds))
      .join(""),
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
  const body = parseNodes(parsed.body);
  const nodeIds = new Set<string>();
  const pending = [...body];
  while (pending.length > 0) {
    const node = pending.shift();
    if (node?.type !== "element") continue;
    nodeIds.add(node.id);
    pending.unshift(...node.children);
  }
  const responsiveStyles = Object.fromEntries(
    Object.entries(document.responsiveStyles ?? {}).filter(([nodeId]) =>
      nodeIds.has(nodeId),
    ),
  );
  return { ...document, body, css, responsiveStyles };
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
