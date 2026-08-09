import { describe, expect, it } from "vitest";
import {
  compileCanvas,
  compileDocument,
  findNode,
  parseEditorDocument,
  replaceCanvas,
} from "../editor/document";

describe("GrapeJS document round trip", () => {
  it("preserves metadata, attributes, scripts, and doctype", () => {
    const source = `<!doctype html>
      <html lang="en" data-theme="dark">
        <head><meta name="description" content="A site"><style>.old { color: red; }</style></head>
        <body class="landing"><main class="old">Hello</main><script>window.ready = true;</script></body>
      </html>`;

    const document = parseEditorDocument(source);
    const updated = replaceCanvas(
      document,
      '<main data-mwb-id="hero" class="new">Updated</main>',
      ".new { color: blue; }",
    );
    const result = compileDocument(updated);

    expect(result).toContain('<html data-theme="dark" lang="en">');
    expect(result).toContain('<meta name="description" content="A site">');
    expect(result).toContain('<body class="landing">');
    expect(result).toContain('data-mwb-id="hero"');
    expect(result).toContain('class="new"');
    expect(result).toContain(".new { color: blue; }");
    expect(result).toContain("<script>window.ready = true;</script>");
    expect(result).not.toContain(".old { color: red; }");
  });

  it("wraps an HTML fragment in a complete document", () => {
    const document = parseEditorDocument("<section>Fragment</section>");
    const result = compileDocument(document);

    expect(result).toMatch(/^<!DOCTYPE html>/);
    expect(result).toContain("<body><section data-mwb-id=");
    expect(result).toContain(">Fragment</section></body>");
  });

  it("produces stable node IDs and deterministic output", () => {
    const first = parseEditorDocument("<main><h1>Hello</h1><p>World</p></main>");
    const second = parseEditorDocument(compileDocument(first));

    expect(compileDocument(second)).toBe(compileDocument(first));
    expect(compileCanvas(first)).toBe(compileCanvas(second));
    const root = first.body[0];
    expect(root.type).toBe("element");
    if (root.type === "element") expect(findNode(second, root.id)?.tag).toBe("main");
  });

  it("deduplicates invalid or repeated imported node IDs", () => {
    const document = parseEditorDocument(
      '<main data-mwb-id="same"><p data-mwb-id="same">One</p><p data-mwb-id="bad id">Two</p></main>',
    );
    const ids = compileCanvas(document).match(/data-mwb-id="[^"]+"/g) ?? [];

    expect(new Set(ids).size).toBe(3);
  });

  it("can compile a clean export without editor identifiers", () => {
    const document = parseEditorDocument('<main data-mwb-id="hero">Hello</main>');

    expect(compileDocument(document, { includeEditorIds: false })).not.toContain(
      "data-mwb-id",
    );
  });
});
