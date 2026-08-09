import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "./api";

vi.mock("./api", () => ({
  PageVersionConflictError: class PageVersionConflictError extends Error {
    constructor(public currentVersion: number) {
      super(`A newer page version (${currentVersion}) is already saved`);
    }
  },
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
  fetchProjects: vi.fn(),
  createProject: vi.fn(),
  fetchProject: vi.fn(),
  renameProject: vi.fn(),
  duplicateProject: vi.fn(),
  archiveProject: vi.fn(),
  savePage: vi.fn(),
  fetchRevisions: vi.fn(),
  restoreRevision: vi.fn(),
  createCheckpoint: vi.fn(),
  duplicateRevision: vi.fn(),
  fetchConversation: vi.fn(),
  saveConversationDocument: vi.fn(),
}));

import { useStore } from "./store";
import { compileDocument, parseEditorDocument } from "./editor/document";

const canonical = (html: string) => compileDocument(parseEditorDocument(html));

const generated = {
  html: "<html><body>new</body></html>",
  notes: [],
  safety_alerts: [],
  settings: { tone: "minimal", complexity: "balanced", strict_minimal: false, profile: null },
};

const page = {
  id: "page-1",
  project_id: "project-1",
  name: "Home",
  slug: "home",
  version: 1,
  current_revision_id: "revision-1",
  html: "<html>project</html>",
  document: null,
  created_at: "2026-08-08T00:00:00Z",
  updated_at: "2026-08-08T00:00:00Z",
};

const project = {
  id: "project-1",
  name: "Launch",
  page_count: 1,
  created_at: "2026-08-08T00:00:00Z",
  updated_at: "2026-08-08T00:00:00Z",
  archived_at: null,
  pages: [page],
};

describe("document revision workflows", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useStore.setState({
      code: null,
      editorDocument: null,
      busy: false,
      error: null,
      undoStack: [],
      redoStack: [],
      chatMessages: [],
      constraintSections: ["hero", "footer"],
      constraintColor: "single-accent",
      constraintDensity: "balanced",
      projects: [],
      projectsError: null,
      projectName: "",
      projectSearch: "",
      activeProjectId: null,
      activePageId: null,
      activePageVersion: 0,
      revisions: [],
      checkpointName: "",
      sectionsError: null,
      templatesError: null,
      dnasError: null,
      saveState: "idle",
      saveQueued: false,
    });
    vi.mocked(api.fetchProjects).mockResolvedValue([]);
    vi.mocked(api.fetchRevisions).mockResolvedValue([]);
    vi.mocked(api.fetchConversation).mockResolvedValue(null);
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
    expect(useStore.getState().code).toBe(canonical(generated.html));
  });

  it("records AI generations in undo history", async () => {
    useStore.setState({ code: "<html>old</html>" });
    vi.mocked(api.generate).mockResolvedValue(generated);

    await useStore.getState().runGenerate("improve the page");

    expect(useStore.getState().undoStack).toHaveLength(1);
    expect(compileDocument(useStore.getState().undoStack[0])).toBe(
      canonical("<html>old</html>"),
    );
    useStore.getState().undo();
    expect(useStore.getState().code).toBe(canonical("<html>old</html>"));
  });

  it("opens a template as a new conversation and a reversible revision", async () => {
    useStore.setState({
      code: "<html>old</html>",
      chatMessages: [{ role: "user", content: "old conversation" }],
    });
    vi.mocked(api.loadTemplate).mockResolvedValue("<html>template</html>");

    await useStore.getState().doLoadTemplate("landing");

    expect(api.loadTemplate).toHaveBeenCalledWith("landing");
    expect(useStore.getState().code).toBe(canonical("<html>template</html>"));
    expect(useStore.getState().chatMessages).toEqual([]);
    expect(useStore.getState().undoStack).toHaveLength(1);
  });

  it("restores a durable conversation checkpoint", async () => {
    vi.mocked(api.fetchConversation).mockResolvedValue({
      thread_id: useStore.getState().threadId,
      messages: [{ role: "assistant", content: "Welcome back" }],
      current_code: "<html>restored</html>",
      document: null,
    });

    await useStore.getState().restoreConversation();

    expect(useStore.getState().code).toBe(canonical("<html>restored</html>"));
    expect(useStore.getState().chatMessages).toEqual([
      { role: "assistant", content: "Welcome back" },
    ]);
    expect(useStore.getState().undoStack).toEqual([]);
  });

  it("creates a durable project from the current document", async () => {
    useStore.setState({ projectName: "Launch" });
    useStore.getState().setCodeWithHistory("<html>project</html>");
    vi.mocked(api.createProject).mockResolvedValue(project);

    await useStore.getState().createCurrentProject();

    expect(api.createProject).toHaveBeenCalledWith(
      "Launch",
      canonical("<html>project</html>"),
      expect.objectContaining({ schemaVersion: 1 }),
    );
    expect(useStore.getState().activeProjectId).toBe("project-1");
    expect(useStore.getState().activePageVersion).toBe(1);
    expect(useStore.getState().saveState).toBe("saved");
  });

  it("saves the active page with optimistic versioning", async () => {
    const editorDocument = parseEditorDocument("<html>v2</html>");
    useStore.setState({
      code: compileDocument(editorDocument),
      editorDocument,
      activeProjectId: "project-1",
      activePageId: "page-1",
      activePageVersion: 1,
    });
    vi.mocked(api.savePage).mockResolvedValue({
      ...page,
      html: "<html>v2</html>",
      version: 2,
      current_revision_id: "revision-2",
    });

    await useStore.getState().saveActivePage();

    expect(api.savePage).toHaveBeenCalledWith(
      "page-1",
      canonical("<html>v2</html>"),
      1,
      "autosave",
      editorDocument,
    );
    expect(useStore.getState().activePageVersion).toBe(2);
    expect(useStore.getState().saveState).toBe("saved");
  });

  it("surfaces an optimistic save conflict without overwriting", async () => {
    useStore.setState({
      code: "<html>stale</html>",
      activePageId: "page-1",
      activePageVersion: 1,
    });
    vi.mocked(api.savePage).mockRejectedValue(new api.PageVersionConflictError(2));

    await useStore.getState().saveActivePage();

    expect(useStore.getState().saveState).toBe("conflict");
    expect(useStore.getState().activePageVersion).toBe(1);
    expect(useStore.getState().error).toContain("version (2)");
  });

  it("marks active-project edits as pending autosave", () => {
    vi.useFakeTimers();
    useStore.setState({
      code: "<html>v1</html>",
      activePageId: "page-1",
      saveState: "saved",
    });

    useStore.getState().setCodeWithHistory("<html>v2</html>");

    expect(useStore.getState().saveState).toBe("idle");
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  it("persists standalone document edits to the durable conversation", async () => {
    vi.useFakeTimers();
    vi.mocked(api.saveConversationDocument).mockResolvedValue();
    useStore.setState({ code: "<html>old</html>", activePageId: null });

    useStore.getState().setCodeWithHistory("<html>edited</html>");
    await vi.advanceTimersByTimeAsync(800);

    expect(api.saveConversationDocument).toHaveBeenCalledWith(
      useStore.getState().threadId,
      canonical("<html>edited</html>"),
      expect.objectContaining({ schemaVersion: 1 }),
    );
    vi.useRealTimers();
  });

  it("ignores a late save response after the active project changes", async () => {
    let resolveSave!: (value: typeof page) => void;
    vi.mocked(api.savePage).mockReturnValue(new Promise((resolve) => {
      resolveSave = resolve;
    }));
    useStore.setState({
      code: "<html>old project</html>",
      activeProjectId: "project-1",
      activePageId: "page-1",
      activePageVersion: 1,
      saveState: "idle",
    });

    const saving = useStore.getState().saveActivePage();
    useStore.setState({ activeProjectId: "project-2", activePageId: "page-2", activePageVersion: 7 });
    resolveSave({ ...page, version: 2 });
    await saving;

    expect(useStore.getState().activePageId).toBe("page-2");
    expect(useStore.getState().activePageVersion).toBe(7);
  });

  it("renames and refreshes a project", async () => {
    vi.mocked(api.renameProject).mockResolvedValue({ ...project, name: "New name" });

    await useStore.getState().renameProject("project-1", "  New name  ");

    expect(api.renameProject).toHaveBeenCalledWith("project-1", "New name");
    expect(api.fetchProjects).toHaveBeenCalledWith("");
  });

  it("does not duplicate an active project with unsaved changes", async () => {
    useStore.setState({
      activeProjectId: "project-1",
      activePageId: "page-1",
      saveState: "idle",
    });

    await useStore.getState().duplicateProject("project-1");

    expect(api.duplicateProject).not.toHaveBeenCalled();
    expect(useStore.getState().error).toContain("Save the active project");
  });

  it("archives a saved active project and detaches the document", async () => {
    useStore.setState({
      activeProjectId: "project-1",
      activePageId: "page-1",
      activePageVersion: 2,
      saveState: "saved",
    });
    vi.mocked(api.archiveProject).mockResolvedValue({
      ...project,
      archived_at: "2026-08-08T01:00:00Z",
    });

    await useStore.getState().archiveProject("project-1");

    expect(api.archiveProject).toHaveBeenCalledWith("project-1");
    expect(useStore.getState().activeProjectId).toBeNull();
    expect(useStore.getState().activePageId).toBeNull();
  });

  it("duplicates a project from the selected historical revision", async () => {
    const historicalCopy = {
      ...project,
      id: "project-2",
      name: "Launch · v1",
      pages: [
        {
          ...page,
          id: "page-2",
          project_id: "project-2",
          html: "<html>historical</html>",
        },
      ],
    };
    useStore.setState({
      projects: [project],
      activeProjectId: "project-1",
      activePageId: "page-1",
      activePageVersion: 2,
      saveState: "saved",
    });
    vi.mocked(api.duplicateRevision).mockResolvedValue(historicalCopy);
    vi.mocked(api.fetchProject).mockResolvedValue(historicalCopy);

    await useStore.getState().duplicateRevision("revision-1", 1);

    expect(api.duplicateRevision).toHaveBeenCalledWith(
      "page-1",
      "revision-1",
      "Launch · v1",
    );
    expect(useStore.getState().activeProjectId).toBe("project-2");
    expect(useStore.getState().code).toBe(canonical("<html>historical</html>"));
  });

  it("surfaces and clears sidebar resource load errors", async () => {
    useStore.setState({ code: "<main>Page</main>" });
    vi.mocked(api.fetchSections).mockRejectedValueOnce(new Error("Sections unavailable"));
    vi.mocked(api.fetchTemplates).mockRejectedValueOnce(new Error("Templates unavailable"));
    vi.mocked(api.fetchDnas).mockRejectedValueOnce(new Error("DNA unavailable"));
    vi.mocked(api.fetchProjects).mockRejectedValueOnce(new Error("Projects unavailable"));

    await Promise.all([
      useStore.getState().refreshSections(),
      useStore.getState().refreshTemplates(),
      useStore.getState().refreshDnas(),
      useStore.getState().refreshProjects(),
    ]);

    expect(useStore.getState()).toMatchObject({
      sectionsError: "Sections unavailable",
      templatesError: "Templates unavailable",
      dnasError: "DNA unavailable",
      projectsError: "Projects unavailable",
    });

    vi.mocked(api.fetchSections).mockResolvedValue([]);
    vi.mocked(api.fetchTemplates).mockResolvedValue([]);
    vi.mocked(api.fetchDnas).mockResolvedValue([]);
    vi.mocked(api.fetchProjects).mockResolvedValue([]);
    await Promise.all([
      useStore.getState().refreshSections(),
      useStore.getState().refreshTemplates(),
      useStore.getState().refreshDnas(),
      useStore.getState().refreshProjects(),
    ]);

    expect(useStore.getState()).toMatchObject({
      sectionsError: null,
      templatesError: null,
      dnasError: null,
      projectsError: null,
    });
  });
});
