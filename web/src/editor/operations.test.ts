import { describe, expect, it } from "vitest";
import {
  compileCanvas,
  compileDocument,
  compileResponsiveCss,
  parseEditorDocument,
  replaceCanvas,
} from "./document";
import {
  editableText,
  elementEntries,
  elementPath,
  moveElementBefore,
  setElementAttribute,
  setElementStyle,
  setElementText,
} from "./operations";

describe("structured document operations", () => {
  it("finds a stable hierarchy and updates properties immutably", () => {
    const document = parseEditorDocument(
      '<main><section><a href="/old">Read more</a></section></main>',
    );
    const entries = elementEntries(document);
    const link = entries.find(({ node }) => node.tag === "a")!.node;
    const path = elementPath(document, link.id);

    expect(path.map((node) => node.tag)).toEqual(["main", "section", "a"]);
    expect(editableText(link)).toBe("Read more");

    const attributed = setElementAttribute(document, link.id, "href", "/new");
    const updated = setElementText(attributed, link.id, "Explore");
    expect(compileCanvas(updated)).toContain('href="/new"');
    expect(compileCanvas(updated)).toContain(">Explore</a>");
    expect(compileCanvas(document)).toContain('href="/old"');
  });

  it("reorders elements without changing their stable IDs", () => {
    const document = parseEditorDocument("<main><p>First</p><p>Second</p></main>");
    const paragraphs = elementEntries(document).filter(({ node }) => node.tag === "p");
    const moved = moveElementBefore(document, paragraphs[1].node.id, paragraphs[0].node.id);

    expect(compileCanvas(moved).indexOf("Second")).toBeLessThan(
      compileCanvas(moved).indexOf("First"),
    );
    expect(compileCanvas(moved)).toContain(paragraphs[1].node.id);
  });

  it("does not allow an element to move inside its descendant", () => {
    const document = parseEditorDocument("<main><section><p>Text</p></section></main>");
    const [main, section] = elementEntries(document);

    expect(moveElementBefore(document, main.node.id, section.node.id)).toBe(document);
  });

  it("compiles base and responsive styles into portable HTML", () => {
    const document = parseEditorDocument("<main>Responsive</main>");
    const main = elementEntries(document)[0].node;
    const base = setElementStyle(document, main.id, "padding", "24px");
    const tablet = setElementStyle(base, main.id, "padding", "16px", "tablet");
    const mobile = setElementStyle(tablet, main.id, "display", "none", "mobile");

    expect(compileCanvas(base)).toContain('style="padding: 24px;"');
    expect(compileResponsiveCss(mobile)).toContain("max-width: 1023px");
    expect(compileResponsiveCss(mobile)).toContain("padding: 16px;");
    const portable = compileDocument(mobile, { includeEditorIds: false });
    expect(portable).toContain(`class="mwb-node-${main.id}"`);
    expect(portable).toContain("max-width: 639px");
    expect(portable).not.toContain("data-mwb-id");
  });

  it("removes responsive styles when their canvas element is removed", () => {
    const document = parseEditorDocument("<main>Keep</main><aside>Remove</aside>");
    const [, aside] = elementEntries(document);
    const styled = setElementStyle(document, aside.node.id, "display", "none", "mobile");

    const replaced = replaceCanvas(styled, "<main data-mwb-id=\"node-keep\">Keep</main>", "");

    expect(replaced.responsiveStyles).toEqual({});
  });
});
