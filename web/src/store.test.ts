import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "./api";

vi.mock("./api", () => ({
  fetchOptions: vi.fn(),
  generate: vi.fn(),
  fetchSections: vi.fn(),
  regenerateSection: vi.fn(),
  fetchTemplates: vi.fn(),
  saveTemplate: vi.fn(),
  loadTemplate: vi.fn(),
  deleteTemplate: vi.fn(),
  fetchDnas: vi.fn(),
  saveDna: vi.fn(),
  chat: vi.fn(),
}));

import { useStore } from "./store";

const generated = {
  html: "<html><body>new</body></html>",
  notes: [],
  safety_alerts: [],
  settings: { tone: "minimal", complexity: "balanced", strict_minimal: false, profile: null },
};

describe("document revision workflows", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useStore.setState({
      code: null,
      busy: false,
      error: null,
      undoStack: [],
      redoStack: [],
      chatMessages: [],
      constraintSections: ["hero", "footer"],
      constraintColor: "single-accent",
      constraintDensity: "balanced",
    });
  });

  it("generates from constraints without a prompt", async () => {
    vi.mocked(api.generate).mockResolvedValue(generated);

    await useStore.getState().runConstraints();

    expect(api.generate).toHaveBeenCalledWith(expect.objectContaining({
      constraints: {
        sections: ["hero", "footer"],
        color_limit: "single-accent",
        density: "balanced",
      },
    }));
    expect(useStore.getState().code).toBe(generated.html);
  });

  it("records AI generations in undo history", async () => {
    useStore.setState({ code: "<html>old</html>" });
    vi.mocked(api.generate).mockResolvedValue(generated);

    await useStore.getState().runGenerate("improve the page");

    expect(useStore.getState().undoStack).toEqual(["<html>old</html>"]);
    useStore.getState().undo();
    expect(useStore.getState().code).toBe("<html>old</html>");
  });

  it("opens a template as a new conversation and a reversible revision", async () => {
    useStore.setState({
      code: "<html>old</html>",
      chatMessages: [{ role: "user", content: "old conversation" }],
    });
    vi.mocked(api.loadTemplate).mockResolvedValue("<html>template</html>");

    await useStore.getState().doLoadTemplate("landing");

    expect(api.loadTemplate).toHaveBeenCalledWith("landing");
    expect(useStore.getState().code).toBe("<html>template</html>");
    expect(useStore.getState().chatMessages).toEqual([]);
    expect(useStore.getState().undoStack).toEqual(["<html>old</html>"]);
  });
});
