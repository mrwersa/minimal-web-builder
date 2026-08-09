import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { compileCanvas, findNode, parseEditorDocument } from "../../editor/document";
import EditorInspector from "./EditorInspector";

describe("EditorInspector", () => {
  it("commits text and link edits as structured document mutations", () => {
    const document = parseEditorDocument('<main><a href="/old">Read more</a></main>');
    const anchor = document.body[0];
    if (anchor.type !== "element") throw new Error("expected main element");
    const link = anchor.children[0];
    if (link.type !== "element") throw new Error("expected link element");
    let current = document;
    const onChange = vi.fn((next) => {
      current = next;
    });
    const view = render(
      <EditorInspector document={current} node={link} onChange={onChange} />,
    );

    fireEvent.change(screen.getByLabelText("Text content"), {
      target: { value: "Explore" },
    });
    fireEvent.blur(screen.getByLabelText("Text content"));
    expect(compileCanvas(current)).toContain(">Explore</a>");

    view.rerender(
      <EditorInspector
        document={current}
        node={findNode(current, link.id)}
        onChange={onChange}
      />,
    );
    fireEvent.change(screen.getByLabelText("Link URL"), {
      target: { value: "/new" },
    });
    fireEvent.blur(screen.getByLabelText("Link URL"));

    expect(compileCanvas(current)).toContain('href="/new"');
    expect(onChange).toHaveBeenCalledTimes(2);
  });
});
