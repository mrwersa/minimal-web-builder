import { describe, expect, it } from "vitest";
import {
  isEditableTarget,
  keyboardShortcut,
  searchCommands,
  type BuilderCommand,
} from "./commands";

const commands: BuilderCommand[] = [
  {
    id: "preview",
    label: "Show preview",
    description: "Render the page",
    keywords: ["canvas"],
    run: () => undefined,
  },
  {
    id: "code",
    label: "Show code",
    description: "Open portable HTML",
    run: () => undefined,
  },
];

describe("builder commands", () => {
  it("normalizes cross-platform modifier shortcuts", () => {
    expect(keyboardShortcut(new KeyboardEvent("keydown", { ctrlKey: true, key: "K" }))).toBe(
      "mod+k",
    );
    expect(
      keyboardShortcut(
        new KeyboardEvent("keydown", { metaKey: true, shiftKey: true, key: "z" }),
      ),
    ).toBe("mod+shift+z");
  });

  it("detects editable targets and searches command metadata", () => {
    const input = document.createElement("input");
    expect(isEditableTarget(input)).toBe(true);
    expect(isEditableTarget(document.createElement("div"))).toBe(false);
    expect(searchCommands(commands, "canvas").map(({ id }) => id)).toEqual(["preview"]);
    expect(searchCommands(commands, "portable html").map(({ id }) => id)).toEqual([
      "code",
    ]);
  });
});
