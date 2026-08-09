import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { compileDocument, parseEditorDocument } from "../../editor/document";
import AdvancedCodePanel from "./AdvancedCodePanel";

describe("AdvancedCodePanel", () => {
  it("commits raw sources as structured, undoable document updates", () => {
    const document = parseEditorDocument("<main>Page</main>");
    let current = document;
    const onChange = vi.fn((next) => {
      current = next;
    });
    const view = render(<AdvancedCodePanel document={current} onChange={onChange} />);

    fireEvent.change(screen.getByLabelText("Custom CSS"), {
      target: { value: "main { color: rebeccapurple; }" },
    });
    fireEvent.blur(screen.getByLabelText("Custom CSS"));
    view.rerender(<AdvancedCodePanel document={current} onChange={onChange} />);
    fireEvent.change(screen.getByLabelText("Body script HTML"), {
      target: { value: "<script>window.advancedReady = true;</script>" },
    });
    fireEvent.blur(screen.getByLabelText("Body script HTML"));

    expect(compileDocument(current)).toContain("rebeccapurple");
    expect(compileDocument(current)).toContain("window.advancedReady = true");
    expect(onChange).toHaveBeenCalledTimes(2);
  });
});
