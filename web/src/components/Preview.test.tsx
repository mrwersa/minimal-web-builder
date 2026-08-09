import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { compileDocument, parseEditorDocument } from "../editor/document";
import { useStore } from "../store";
import Preview, { buildPreviewDoc } from "./Preview";

describe("Preview", () => {
  beforeEach(() => {
    useStore.setState({ code: null, editorDocument: null, editing: false, busy: false });
  });

  it("renders the newest compiled document after an edit", () => {
    const first = parseEditorDocument("<main>Before</main>");
    const updated = parseEditorDocument("<main>After</main>");
    useStore.setState({ code: compileDocument(first), editorDocument: first });

    render(<Preview />);
    expect(screen.getByTitle("preview")).toHaveAttribute(
      "srcdoc",
      expect.stringContaining("Before"),
    );

    act(() => {
      useStore.setState({ code: compileDocument(updated), editorDocument: updated });
    });

    expect(screen.getByTitle("preview")).toHaveAttribute(
      "srcdoc",
      expect.stringContaining("After"),
    );
  });

  it("sandboxes the frame and never allows same-origin access", () => {
    useStore.setState({ code: "<main>Hi</main>" });
    render(<Preview />);

    const frame = screen.getByTitle("preview");
    expect(frame).toHaveAttribute("sandbox", "allow-scripts allow-forms");
    expect(frame.getAttribute("sandbox")).not.toContain("allow-same-origin");
  });
});

describe("buildPreviewDoc", () => {
  it("injects the CSP directly after an existing head tag", () => {
    const html = "<!doctype html><html><head><title>T</title></head><body>x</body></html>";

    const result = buildPreviewDoc(html);

    expect(result).toContain('http-equiv="Content-Security-Policy"');
    // The meta must precede the page's own head content so it applies to it.
    expect(result.indexOf("mwb-preview-csp")).toBeLessThan(result.indexOf("<title>"));
  });

  it("wraps a bare fragment in a full document", () => {
    const result = buildPreviewDoc("<main>fragment</main>");

    expect(result).toContain("<!doctype html>");
    expect(result).toContain("mwb-preview-csp");
    expect(result).toContain("<main>fragment</main>");
  });

  it("falls back to the closing head tag when there is no opening one", () => {
    const result = buildPreviewDoc("<html></head><body>x</body></html>");

    expect(result).toContain("mwb-preview-csp");
  });
});
