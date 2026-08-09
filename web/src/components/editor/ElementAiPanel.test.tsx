import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { parseEditorDocument } from "../../editor/document";
import { useStore } from "../../store";
import ElementAiPanel from "./ElementAiPanel";

describe("ElementAiPanel", () => {
  it("runs an AI command against the selected stable node ID", () => {
    const document = parseEditorDocument("<h1>Selected</h1>");
    const node = document.body[0];
    if (node.type !== "element") throw new Error("expected heading element");
    const runChat = vi.fn().mockResolvedValue(undefined);
    useStore.setState({ busy: false, runChat });
    render(<ElementAiPanel node={node} />);

    fireEvent.change(screen.getByLabelText("Element AI instruction"), {
      target: { value: "Make it warmer" },
    });
    fireEvent.click(screen.getByLabelText("Apply AI edit to selected element"));

    expect(runChat).toHaveBeenCalledWith("Make it warmer", node.id);
  });
});
