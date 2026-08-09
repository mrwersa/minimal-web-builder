import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { parseEditorDocument } from "../../editor/document";
import { elementEntries } from "../../editor/operations";
import LayerTree from "./LayerTree";

describe("LayerTree", () => {
  it("moves keyboard focus and selection through the flattened element tree", () => {
    const document = parseEditorDocument("<main><h1>Title</h1><p>Body</p></main>");
    const entries = elementEntries(document);
    const onSelect = vi.fn();
    render(
      <LayerTree
        document={document}
        selectedNodeId={entries[0].node.id}
        onSelect={onSelect}
        onChange={vi.fn()}
      />,
    );

    const main = screen.getByRole("treeitem", { name: /main/ });
    main.focus();
    fireEvent.keyDown(main, { key: "ArrowDown" });

    expect(onSelect).toHaveBeenCalledWith(entries[1].node.id);
    expect(screen.getByRole("treeitem", { name: /h1/ })).toHaveFocus();
    fireEvent.keyDown(screen.getByRole("treeitem", { name: /h1/ }), { key: "End" });
    expect(onSelect).toHaveBeenLastCalledWith(entries[entries.length - 1].node.id);
    expect(screen.getByRole("treeitem", { name: /p · Body/ })).toHaveFocus();
  });
});
