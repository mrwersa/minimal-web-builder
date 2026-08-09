import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { BuilderCommand } from "../commands";
import CommandPalette from "./CommandPalette";

describe("CommandPalette", () => {
  it("filters, navigates, and executes commands from the keyboard", () => {
    const runPreview = vi.fn();
    const runCode = vi.fn();
    const onClose = vi.fn();
    const commands: BuilderCommand[] = [
      {
        id: "preview",
        label: "Show preview",
        description: "Render the page",
        run: runPreview,
      },
      {
        id: "code",
        label: "Show code",
        description: "Open HTML",
        run: runCode,
      },
    ];
    render(<CommandPalette commands={commands} onClose={onClose} />);

    const search = screen.getByLabelText("Search commands");
    fireEvent.change(search, { target: { value: "code" } });
    fireEvent.keyDown(search, { key: "Enter" });

    expect(runPreview).not.toHaveBeenCalled();
    expect(runCode).toHaveBeenCalledOnce();
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("closes with Escape without executing a command", () => {
    const onClose = vi.fn();
    render(
      <CommandPalette
        commands={[
          {
            id: "preview",
            label: "Show preview",
            description: "Render",
            run: vi.fn(),
          },
        ]}
        onClose={onClose}
      />,
    );

    fireEvent.keyDown(screen.getByLabelText("Search commands"), { key: "Escape" });
    expect(onClose).toHaveBeenCalledOnce();
  });
});
