import { describe, expect, it } from "vitest";
import { compileDocument, parseEditorDocument } from "./document";
import { advancedSourceValue, setAdvancedSource } from "./advanced";

describe("advanced editor sources", () => {
  it("updates head HTML, custom CSS, and body scripts without touching page nodes", () => {
    const document = parseEditorDocument("<main>Keep</main>");
    const withHead = setAdvancedSource(
      document,
      "headHtml",
      '<meta name="description" content="Advanced">',
    );
    const withCss = setAdvancedSource(withHead, "css", ".hero { color: tomato; }");
    const withScript = setAdvancedSource(
      withCss,
      "bodyScripts",
      "<script>window.ready = true;</script>",
    );

    const compiled = compileDocument(withScript);
    expect(compiled).toContain('<meta name="description" content="Advanced">');
    expect(compiled).toContain(".hero { color: tomato; }");
    expect(compiled).toContain("window.ready = true");
    expect(compiled).toContain(">Keep</main>");
    expect(advancedSourceValue(withScript, "bodyScripts")).toContain("<script>");
  });

  it("removes an advanced source when its editor is cleared", () => {
    const document = parseEditorDocument("<main>Keep</main><script>old()</script>");
    expect(setAdvancedSource(document, "bodyScripts", "").bodyScripts).toEqual([]);
  });
});
