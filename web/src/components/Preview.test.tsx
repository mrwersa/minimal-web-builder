import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { compileDocument, parseEditorDocument } from "../editor/document";
import { useStore } from "../store";
import Preview from "./Preview";

vi.mock("./editor/EditorWorkspace", () => ({
  default: () => <div>Visual workspace</div>,
}));

describe("Preview", () => {
  beforeEach(() => {
    useStore.setState({
      code: null,
      editorDocument: null,
      editing: false,
      busy: false,
    });
  });

  it("loads the latest document when preview remounts after visual editing", async () => {
    const first = parseEditorDocument("<main>Before</main>");
    const updated = parseEditorDocument("<main>After</main>");
    useStore.setState({
      code: compileDocument(first),
      editorDocument: first,
      editing: true,
    });
    render(<Preview />);
    expect(await screen.findByText("Visual workspace")).toBeInTheDocument();

    act(() => {
      useStore.setState({
        code: compileDocument(updated),
        editorDocument: updated,
        editing: false,
      });
    });

    expect(screen.getByTitle("preview")).toHaveAttribute(
      "srcdoc",
      expect.stringContaining("After"),
    );
  });
});
