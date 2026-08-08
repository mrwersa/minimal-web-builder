import { create } from "zustand";
import * as api from "./api";
import { errorMessage } from "./lib/errors";

interface State {
  options: api.OptionsResponse | null;
  optionsError: string | null;

  profile: string;
  tone: string;
  complexity: string;
  strictMinimal: boolean;

  constraintMode: boolean;
  constraintSections: string[];
  constraintColor: string;
  constraintDensity: string;

  layoutDnaGuidance: string;

  editing: boolean;

  code: string | null;
  notes: string[];
  safetyAlerts: string[];
  busy: boolean;
  error: string | null;

  sections: api.SectionInfo[];
  sectionsError: string | null;
  sectionIndex: number;
  refineAspect: string;

  templates: string[];
  templatesError: string | null;
  templateName: string;

  dnas: api.DnaItem[];
  dnasError: string | null;

  projects: api.ProjectSummary[];
  projectsError: string | null;
  projectName: string;
  projectSearch: string;
  activeProjectId: string | null;
  activePageId: string | null;
  activePageVersion: number;
  revisions: api.RevisionSummary[];
  saveState: "idle" | "saving" | "saved" | "conflict";
  saveQueued: boolean;

  chatMessages: api.ChatMessage[];
  threadId: string;

  undoStack: string[];
  redoStack: string[];

  loadOptions: () => Promise<void>;
  set: <K extends keyof State>(key: K, value: State[K]) => void;
  runGenerate: (prompt: string) => Promise<void>;
  runConstraints: () => Promise<void>;
  refreshSections: () => Promise<void>;
  runRegenerate: (instructions: string) => Promise<void>;
  refreshTemplates: () => Promise<void>;
  doSaveTemplate: () => Promise<void>;
  doLoadTemplate: (name: string) => Promise<void>;
  doDeleteTemplate: (name: string) => Promise<void>;
  refreshDnas: () => Promise<void>;
  doSaveDna: () => Promise<void>;
  refreshProjects: () => Promise<void>;
  createCurrentProject: () => Promise<void>;
  openProject: (projectId: string) => Promise<void>;
  renameProject: (projectId: string, name: string) => Promise<void>;
  duplicateProject: (projectId: string) => Promise<void>;
  archiveProject: (projectId: string) => Promise<void>;
  saveActivePage: () => Promise<void>;
  refreshRevisions: () => Promise<void>;
  restoreRevision: (revisionId: string) => Promise<void>;
  runChat: (message: string) => Promise<void>;
  clearChat: () => void;
  undo: () => void;
  redo: () => void;
  setCodeWithHistory: (code: string) => void;
}

let autosaveTimer: ReturnType<typeof setTimeout> | null = null;
let projectRequestSequence = 0;

function scheduleAutosave(get: () => State, delay = 800) {
  if (!get().activePageId) return;
  if (autosaveTimer) clearTimeout(autosaveTimer);
  autosaveTimer = setTimeout(() => {
    autosaveTimer = null;
    void get().saveActivePage();
  }, delay);
}

function hasPendingProjectChanges(state: State, projectId: string): boolean {
  return state.activeProjectId === projectId && state.saveState !== "saved";
}

export const useStore = create<State>((set, get) => ({
  options: null,
  optionsError: null,

  profile: "custom",
  tone: "minimal",
  complexity: "balanced",
  strictMinimal: false,

  constraintMode: false,
  constraintSections: ["hero", "features", "footer"],
  constraintColor: "single-accent",
  constraintDensity: "balanced",

  layoutDnaGuidance: "",

  editing: false,

  code: null,
  notes: [],
  safetyAlerts: [],
  busy: false,
  error: null,

  sections: [],
  sectionsError: null,
  sectionIndex: 0,
  refineAspect: "general",

  templates: [],
  templatesError: null,
  templateName: "",

  dnas: [],
  dnasError: null,

  projects: [],
  projectsError: null,
  projectName: "",
  projectSearch: "",
  activeProjectId: null,
  activePageId: null,
  activePageVersion: 0,
  revisions: [],
  saveState: "idle",
  saveQueued: false,

  chatMessages: [],
  threadId: crypto.randomUUID(),

  undoStack: [],
  redoStack: [],

  set: (key, value) => set({ [key]: value } as Partial<State>),

  loadOptions: async () => {
    set({ optionsError: null });
    try {
      const opts = await api.fetchOptions();
      set({ options: opts });
    } catch (e) {
      set({ optionsError: errorMessage(e) });
    }
  },

  runGenerate: async (prompt) => {
    const s = get();
    set({ busy: true, error: null });
    try {
      const res = await api.generate({
        prompt,
        tone: s.tone,
        complexity: s.complexity,
        strict_minimal: s.strictMinimal,
        profile: s.profile,
        current_code: s.code,
        layout_dna_guidance: s.layoutDnaGuidance,
      });
      get().setCodeWithHistory(res.html);
      set({ notes: res.notes, safetyAlerts: res.safety_alerts, busy: false });
    } catch (e) {
      set({ busy: false, error: errorMessage(e) });
    }
  },

  runConstraints: async () => {
    const s = get();
    set({ busy: true, error: null });
    try {
      const res = await api.generate({
        tone: s.tone,
        complexity: s.complexity,
        strict_minimal: s.strictMinimal,
        profile: s.profile,
        current_code: s.code,
        layout_dna_guidance: s.layoutDnaGuidance,
        constraints: {
          sections: s.constraintSections,
          color_limit: s.constraintColor,
          density: s.constraintDensity,
        },
      });
      get().setCodeWithHistory(res.html);
      set({ notes: res.notes, safetyAlerts: res.safety_alerts, busy: false });
    } catch (e) {
      set({ busy: false, error: errorMessage(e) });
    }
  },

  refreshSections: async () => {
    const s = get();
    if (!s.code) {
      set({ sections: [], sectionsError: null, sectionIndex: 0 });
      return;
    }
    try {
      const sections = await api.fetchSections(s.code);
      set({
        sections,
        sectionsError: null,
        sectionIndex: Math.min(s.sectionIndex, Math.max(0, sections.length - 1)),
      });
    } catch (error) {
      set({ sections: [], sectionsError: errorMessage(error) });
    }
  },

  runRegenerate: async (instructions) => {
    const s = get();
    if (!s.code) return;
    set({ busy: true, error: null });
    try {
      const res = await api.regenerateSection({
        code: s.code,
        section_index: s.sectionIndex,
        instructions,
        tone: s.tone,
        complexity: s.complexity,
        strict_minimal: s.strictMinimal,
        profile: s.profile,
        layout_dna_guidance: s.layoutDnaGuidance,
        refine_aspect: s.refineAspect,
      });
      get().setCodeWithHistory(res.html);
      set({ notes: res.notes, safetyAlerts: res.safety_alerts, busy: false });
    } catch (e) {
      set({ busy: false, error: errorMessage(e) });
    }
  },

  refreshTemplates: async () => {
    try {
      set({ templates: await api.fetchTemplates(), templatesError: null });
    } catch (error) {
      set({ templatesError: errorMessage(error) });
    }
  },

  doSaveTemplate: async () => {
    const s = get();
    if (!s.code || !s.templateName.trim()) return;
    try {
      await api.saveTemplate(s.templateName.trim(), s.code);
      set({ templateName: "" });
      await get().refreshTemplates();
    } catch (e) {
      set({ error: errorMessage(e) });
    }
  },

  doLoadTemplate: async (name) => {
    try {
      const html = await api.loadTemplate(name);
      get().setCodeWithHistory(html);
      set({
        chatMessages: [],
        threadId: crypto.randomUUID(),
        notes: [],
        safetyAlerts: [],
        error: null,
      });
    } catch (e) {
      set({ error: errorMessage(e) });
    }
  },

  doDeleteTemplate: async (name) => {
    try {
      await api.deleteTemplate(name);
      await get().refreshTemplates();
    } catch (e) {
      set({ error: errorMessage(e) });
    }
  },

  refreshDnas: async () => {
    try {
      set({ dnas: await api.fetchDnas(), dnasError: null });
    } catch (error) {
      set({ dnasError: errorMessage(error) });
    }
  },

  doSaveDna: async () => {
    const s = get();
    if (!s.code) return;
    try {
      await api.saveDna(s.code);
      await get().refreshDnas();
    } catch (e) {
      set({ error: errorMessage(e) });
    }
  },

  refreshProjects: async () => {
    const requestSequence = ++projectRequestSequence;
    try {
      const projects = await api.fetchProjects(get().projectSearch);
      if (requestSequence === projectRequestSequence) {
        set({ projects, projectsError: null });
      }
    } catch (e) {
      if (requestSequence === projectRequestSequence) {
        set({ projectsError: errorMessage(e) });
      }
    }
  },

  createCurrentProject: async () => {
    const s = get();
    const name = s.projectName.trim();
    if (!name) return;
    try {
      const project = await api.createProject(name, s.code ?? "");
      const page = project.pages[0];
      set({
        projectName: "",
        activeProjectId: project.id,
        activePageId: page.id,
        activePageVersion: page.version,
        saveState: "saved",
        revisions: [],
        error: null,
      });
      await get().refreshProjects();
      await get().refreshRevisions();
    } catch (e) {
      set({ error: errorMessage(e) });
    }
  },

  openProject: async (projectId) => {
    const current = get();
    if (current.activePageId && current.saveState === "saving") {
      set({ error: "Wait for the current save to finish before switching projects" });
      return;
    }
    if (current.activePageId && current.saveState === "idle") {
      await get().saveActivePage();
      if (get().saveState !== "saved") return;
    }
    try {
      const project = await api.fetchProject(projectId);
      const page = project.pages[0];
      if (!page) throw new Error("Project has no pages");
      if (autosaveTimer) clearTimeout(autosaveTimer);
      autosaveTimer = null;
      set({
        activeProjectId: project.id,
        activePageId: page.id,
        activePageVersion: page.version,
        code: page.html,
        undoStack: [],
        redoStack: [],
        chatMessages: [],
        threadId: crypto.randomUUID(),
        notes: [],
        safetyAlerts: [],
        saveState: "saved",
        saveQueued: false,
        error: null,
      });
      await get().refreshRevisions();
    } catch (e) {
      set({ error: errorMessage(e) });
    }
  },

  renameProject: async (projectId, name) => {
    const cleanName = name.trim();
    if (!cleanName) return;
    try {
      await api.renameProject(projectId, cleanName);
      await get().refreshProjects();
      set({ error: null });
    } catch (e) {
      set({ error: errorMessage(e) });
    }
  },

  duplicateProject: async (projectId) => {
    if (hasPendingProjectChanges(get(), projectId)) {
      set({ error: "Save the active project before duplicating it" });
      return;
    }
    try {
      const project = await api.duplicateProject(projectId);
      await get().refreshProjects();
      await get().openProject(project.id);
    } catch (e) {
      set({ error: errorMessage(e) });
    }
  },

  archiveProject: async (projectId) => {
    if (hasPendingProjectChanges(get(), projectId)) {
      set({ error: "Save the active project before archiving it" });
      return;
    }
    try {
      await api.archiveProject(projectId);
      if (get().activeProjectId === projectId) {
        set({
          activeProjectId: null,
          activePageId: null,
          activePageVersion: 0,
          revisions: [],
          saveState: "idle",
        });
      }
      await get().refreshProjects();
      set({ error: null });
    } catch (e) {
      set({ error: errorMessage(e) });
    }
  },

  saveActivePage: async () => {
    const s = get();
    if (!s.activePageId || s.code === null) return;
    if (s.saveState === "saving") {
      set({ saveQueued: true });
      return;
    }
    const pageId = s.activePageId;
    const html = s.code;
    const expectedVersion = s.activePageVersion;
    set({ saveState: "saving", saveQueued: false });
    try {
      const page = await api.savePage(pageId, html, expectedVersion);
      if (get().activePageId !== pageId) return;
      const saveAgain = get().saveQueued || get().code !== html;
      set({
        activePageVersion: page.version,
        saveState: "saved",
        saveQueued: false,
        error: null,
      });
      await get().refreshProjects();
      await get().refreshRevisions();
      if (saveAgain) scheduleAutosave(get, 0);
    } catch (e) {
      if (get().activePageId !== pageId) return;
      if (e instanceof api.PageVersionConflictError) {
        set({ saveState: "conflict", saveQueued: false, error: e.message });
      } else {
        set({
          saveState: "idle",
          saveQueued: false,
          error: errorMessage(e),
        });
      }
    }
  },

  refreshRevisions: async () => {
    const pageId = get().activePageId;
    if (!pageId) {
      set({ revisions: [] });
      return;
    }
    try {
      set({ revisions: await api.fetchRevisions(pageId) });
    } catch (e) {
      set({ error: errorMessage(e) });
    }
  },

  restoreRevision: async (revisionId) => {
    const s = get();
    if (!s.activePageId) return;
    try {
      const page = await api.restoreRevision(
        s.activePageId,
        revisionId,
        s.activePageVersion,
      );
      const previous = get().code;
      set({
        code: page.html,
        activePageVersion: page.version,
        undoStack: previous ? [...get().undoStack.slice(-49), previous] : get().undoStack,
        redoStack: [],
        saveState: "saved",
        error: null,
      });
      await get().refreshRevisions();
    } catch (e) {
      if (e instanceof api.PageVersionConflictError) {
        set({ saveState: "conflict", error: e.message });
      } else {
        set({ error: errorMessage(e) });
      }
    }
  },

  runChat: async (message) => {
    const s = get();
    const userMsg: api.ChatMessage = { role: "user", content: message };
    set({
      chatMessages: [...s.chatMessages, userMsg],
      busy: true,
      error: null,
    });
    try {
      const res = await api.chat({
        message,
        thread_id: s.threadId,
        current_code: s.code,
        tone: s.tone,
        complexity: s.complexity,
        strict_minimal: s.strictMinimal,
        profile: s.profile,
        layout_dna_guidance: s.layoutDnaGuidance,
      });
      const assistantMsg: api.ChatMessage = { role: "assistant", content: res.message };
      if (res.html) get().setCodeWithHistory(res.html);
      set({
        chatMessages: [...get().chatMessages, assistantMsg],
        busy: false,
        notes: res.validation_notes,
        safetyAlerts: res.validation_errors,
      });
      if (res.error) set({ error: res.error });
    } catch (e) {
      set({ busy: false, error: errorMessage(e) });
    }
  },

  clearChat: () => set({ chatMessages: [], threadId: crypto.randomUUID() }),

  undo: () => {
    const { undoStack, code, activePageId, saveState } = get();
    if (undoStack.length === 0) return;
    const prev = undoStack[undoStack.length - 1];
    const newUndo = undoStack.slice(0, -1);
    set({
      undoStack: newUndo,
      redoStack: code ? [code, ...get().redoStack] : get().redoStack,
      code: prev,
      saveState: activePageId && saveState !== "conflict" ? "idle" : saveState,
    });
    scheduleAutosave(get);
  },

  redo: () => {
    const { redoStack, code, activePageId, saveState } = get();
    if (redoStack.length === 0) return;
    const next = redoStack[0];
    const newRedo = redoStack.slice(1);
    set({
      redoStack: newRedo,
      undoStack: code ? [...get().undoStack.slice(-49), code] : get().undoStack,
      code: next,
      saveState: activePageId && saveState !== "conflict" ? "idle" : saveState,
    });
    scheduleAutosave(get);
  },

  setCodeWithHistory: (newCode) => {
    const { code, activePageId, saveState } = get();
    if (code === newCode) return;
    const nextSaveState =
      activePageId && saveState !== "conflict" ? "idle" : saveState;
    if (code) {
      set({
        undoStack: [...get().undoStack.slice(-49), code],
        redoStack: [],
        code: newCode,
        saveState: nextSaveState,
      });
    } else {
      set({ code: newCode, saveState: nextSaveState });
    }
    scheduleAutosave(get);
  },
}));

export function resetWorkspace(): void {
  if (autosaveTimer) {
    clearTimeout(autosaveTimer);
    autosaveTimer = null;
  }
  projectRequestSequence += 1;
  useStore.setState({
    ...useStore.getInitialState(),
    threadId: crypto.randomUUID(),
  });
}
