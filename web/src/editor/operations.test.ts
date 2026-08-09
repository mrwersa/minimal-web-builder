import { describe, expect, it } from "vitest";
import { compileCanvas, parseEditorDocument } from "./document";
import {
  editableText,
  elementEntries,
  elementPath,
  moveElementBefore,
  setElementAttribute,
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
});
