import { describe, expect, it } from "vitest";
import { buildDocument, parseDocument } from "./GrapeJSEditor";

describe("GrapeJS document round trip", () => {
  it("preserves metadata, attributes, scripts, and doctype", () => {
    const source = `<!doctype html>
      <html lang="en" data-theme="dark">
        <head><meta name="description" content="A site"><style>.old { color: red; }</style></head>
        <body class="landing"><main class="old">Hello</main><script>window.ready = true;</script></body>
      </html>`;

    const parts = parseDocument(source);
    const result = buildDocument(parts, '<main class="new">Updated</main>', ".new { color: blue; }");

    expect(result).toContain('<html lang="en" data-theme="dark">');
    expect(result).toContain('<meta name="description" content="A site">');
    expect(result).toContain('<body class="landing">');
    expect(result).toContain('<main class="new">Updated</main>');
    expect(result).toContain(".new { color: blue; }");
    expect(result).toContain("<script>window.ready = true;</script>");
    expect(result).not.toContain(".old { color: red; }");
  });

  it("wraps an HTML fragment in a complete document", () => {
    const parts = parseDocument("<section>Fragment</section>");
    const result = buildDocument(parts, parts.bodyHtml, parts.css);

    expect(result).toMatch(/^<!DOCTYPE html>/);
    expect(result).toContain("<body>\n<section>Fragment</section>\n</body>");
  });
});
