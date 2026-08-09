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
      <EditorInspector
        document={current}
        node={link}
        breakpoint="desktop"
        onChange={onChange}
      />,
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
        breakpoint="desktop"
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

  it("writes responsive style overrides for the selected viewport", () => {
    const document = parseEditorDocument("<main>Responsive</main>");
    const node = document.body[0];
    if (node.type !== "element") throw new Error("expected main element");
    let current = document;
    const onChange = vi.fn((next) => {
      current = next;
    });
    render(
      <EditorInspector
        document={current}
        node={node}
        breakpoint="mobile"
        onChange={onChange}
      />,
    );

    fireEvent.change(screen.getByLabelText("Padding"), {
      target: { value: "12px" },
    });
    fireEvent.blur(screen.getByLabelText("Padding"));

    expect(current.responsiveStyles?.[node.id]?.mobile?.padding).toBe("12px");
    expect(compileCanvas(current)).not.toContain("padding: 12px");
  });
});
