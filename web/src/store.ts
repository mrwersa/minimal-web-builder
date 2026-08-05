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
}));