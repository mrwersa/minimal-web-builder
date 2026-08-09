import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { compileDocument, parseEditorDocument } from "../editor/document";
import { useStore } from "../store";
import CanvasStage from "./CanvasStage";

vi.mock("./GrapeJSEditor", () => ({
  default: () => <div>Visual canvas</div>,
}));

const document = parseEditorDocument("<main><h1>Fern</h1></main>");

describe("CanvasStage", () => {
  beforeEach(() => {
    useStore.setState({
      code: null,
      editorDocument: null,
      editing: false,
      busy: false,
      viewport: "desktop",
      zoom: 1,
      selectedNodeId: null,
    });
  });

  it("prompts for a description before anything is generated", () => {
    render(<CanvasStage />);

    expect(
      screen.getByPlaceholderText("Describe the website you want to create…"),
    ).toBeInTheDocument();
  });

  it("shows the sandboxed preview when not editing", () => {
    useStore.setState({ code: compileDocument(document), editorDocument: document });

    render(<CanvasStage />);

    expect(screen.getByTitle("preview")).toBeInTheDocument();
  });

  it("swaps in the visual canvas while editing", async () => {
    useStore.setState({
      code: compileDocument(document),
      editorDocument: document,
      editing: true,
    });

    render(<CanvasStage />);

    expect(await screen.findByText("Visual canvas")).toBeInTheDocument();
  });

  it("keeps the preview while generating, even with editing on", () => {
    useStore.setState({
      code: compileDocument(document),
      editorDocument: document,
      editing: true,
      busy: true,
    });

    render(<CanvasStage />);

    // Editing is suspended during generation so the canvas cannot fight the
    // incoming document.
    expect(screen.getByTitle("preview")).toBeInTheDocument();
    expect(screen.queryByText("Visual canvas")).not.toBeInTheDocument();
  });

  it("constrains the frame to the selected viewport width", () => {
    useStore.setState({
      code: compileDocument(document),
      editorDocument: document,
      viewport: "mobile",
    });

    const { container } = render(<CanvasStage />);

    const frame = container.querySelector("[style*='width']") as HTMLElement;
    expect(frame.style.width).toBe("390px");
  });
});
