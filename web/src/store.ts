import { create } from "zustand";
import * as api from "./api";

interface State {
  options: api.OptionsResponse | null;
  optionsLoading: boolean;
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
  sectionIndex: number;
  refineAspect: string;

  templates: string[];
  templateName: string;

  dnas: api.DnaItem[];

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
  doDeleteTemplate: (name: string) => Promise<void>;
  refreshDnas: () => Promise<void>;
  doSaveDna: () => Promise<void>;
  runChat: (message: string) => Promise<void>;
  clearChat: () => void;
  undo: () => void;
  redo: () => void;
  setCodeWithHistory: (code: string) => void;
}

export const useStore = create<State>((set, get) => ({
  options: null,
  optionsLoading: true,
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
  sectionIndex: 0,
  refineAspect: "general",

  templates: [],
  templateName: "",

  dnas: [],

  chatMessages: [],
  threadId: crypto.randomUUID(),

  undoStack: [],
  redoStack: [],

  set: (key, value) => set({ [key]: value } as Partial<State>),

  loadOptions: async () => {
    set({ optionsLoading: true, optionsError: null });
    try {
      const opts = await api.fetchOptions();
      set({ options: opts, optionsLoading: false });
    } catch (e) {
      set({ optionsLoading: false, optionsError: String(e instanceof Error ? e.message : e) });
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
      set({ code: res.html, notes: res.notes, safetyAlerts: res.safety_alerts, busy: false });
    } catch (e) {
      set({ busy: false, error: String(e instanceof Error ? e.message : e) });
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
      set({ code: res.html, notes: res.notes, safetyAlerts: res.safety_alerts, busy: false });
    } catch (e) {
      set({ busy: false, error: String(e instanceof Error ? e.message : e) });
    }
  },

  refreshSections: async () => {
    const s = get();
    if (!s.code) {
      set({ sections: [], sectionIndex: 0 });
      return;
    }
    try {
      const sections = await api.fetchSections(s.code);
      set({ sections, sectionIndex: Math.min(s.sectionIndex, Math.max(0, sections.length - 1)) });
    } catch {
      set({ sections: [] });
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
      set({ code: res.html, notes: res.notes, safetyAlerts: res.safety_alerts, busy: false });
    } catch (e) {
      set({ busy: false, error: String(e instanceof Error ? e.message : e) });
    }
  },

  refreshTemplates: async () => {
    try {
      set({ templates: await api.fetchTemplates() });
    } catch {
      /* ignore */
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
      set({ error: String(e instanceof Error ? e.message : e) });
    }
  },

  doDeleteTemplate: async (name) => {
    try {
      await api.deleteTemplate(name);
      await get().refreshTemplates();
    } catch (e) {
      set({ error: String(e instanceof Error ? e.message : e) });
    }
  },

  refreshDnas: async () => {
    try {
      set({ dnas: await api.fetchDnas() });
    } catch {
      /* ignore */
    }
  },

  doSaveDna: async () => {
    const s = get();
    if (!s.code) return;
    try {
      await api.saveDna(s.code);
      await get().refreshDnas();
    } catch (e) {
      set({ error: String(e instanceof Error ? e.message : e) });
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
      set({
        chatMessages: [...get().chatMessages, assistantMsg],
        code: res.html ?? get().code,
        busy: false,
        notes: res.validation_notes,
        safetyAlerts: res.validation_errors,
      });
      if (res.error) set({ error: res.error });
    } catch (e) {
      set({ busy: false, error: String(e instanceof Error ? e.message : e) });
    }
  },

  clearChat: () => set({ chatMessages: [], threadId: crypto.randomUUID() }),

  undo: () => {
    const { undoStack, code } = get();
    if (undoStack.length === 0) return;
    const prev = undoStack[undoStack.length - 1];
    const newUndo = undoStack.slice(0, -1);
    set({
      undoStack: newUndo,
      redoStack: code ? [code, ...get().redoStack] : get().redoStack,
      code: prev,
    });
  },

  redo: () => {
    const { redoStack, code } = get();
    if (redoStack.length === 0) return;
    const next = redoStack[0];
    const newRedo = redoStack.slice(1);
    set({
      redoStack: newRedo,
      undoStack: code ? [...get().undoStack, code] : get().undoStack,
      code: next,
    });
  },

  setCodeWithHistory: (newCode) => {
    const { code } = get();
    if (code && code !== newCode) {
      set({
        undoStack: [...get().undoStack.slice(-49), code],
        redoStack: [],
        code: newCode,
      });
    } else {
      set({ code: newCode });
    }
  },
}));