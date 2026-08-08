export interface OptionsResponse {
  profiles: { id: string; label: string; description: string }[];
  custom_profile_id: string;
  tones: { key: string; label: string }[];
  complexities: { key: string; label: string }[];
  refine_aspects: { key: string; label: string }[];
  sections: { key: string; label: string }[];
  color_limits: { key: string; label: string }[];
  tokens: Record<string, string>;
}

export interface GenerateResponse {
  html: string;
  safety_alerts: string[];
  notes: string[];
  settings: { tone: string; complexity: string; strict_minimal: boolean; profile: string | null };
}

export interface SectionInfo {
  index: number;
  tag: string;
  snippet: string;
}

export interface ProjectSummary {
  id: string;
  name: string;
  page_count: number;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

export interface PageSnapshot {
  id: string;
  project_id: string;
  name: string;
  slug: string;
  version: number;
  current_revision_id: string;
  html: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectSnapshot extends ProjectSummary {
  pages: PageSnapshot[];
}

export interface RevisionSummary {
  id: string;
  page_id: string;
  sequence: number;
  source: string;
  parent_revision_id: string | null;
  created_at: string;
}

export class PageVersionConflictError extends Error {
  constructor(public currentVersion: number) {
    super(`A newer page version (${currentVersion}) is already saved`);
  }
}

export async function fetchOptions(): Promise<OptionsResponse> {
  const r = await fetch("/api/options");
  if (!r.ok) throw new Error(`options ${r.status}`);
  return r.json();
}

export async function generate(req: {
  prompt?: string;
  tone: string;
  complexity: string;
  strict_minimal: boolean;
  profile: string | null;
  current_code: string | null;
  layout_dna_guidance: string;
  constraints?: { sections: string[]; color_limit: string; density: string };
}): Promise<GenerateResponse> {
  const r = await fetch("/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    throw new Error(d.detail ?? `generate ${r.status}`);
  }
  return r.json();
}

export async function fetchSections(code: string): Promise<SectionInfo[]> {
  const r = await fetch("/api/sections", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });
  if (!r.ok) throw new Error(`sections ${r.status}`);
  const j = await r.json();
  return j.sections;
}

export async function regenerateSection(req: {
  code: string;
  section_index: number;
  instructions: string;
  tone: string;
  complexity: string;
  strict_minimal: boolean;
  profile: string | null;
  layout_dna_guidance: string;
  refine_aspect: string | null;
}): Promise<{ html: string; safety_alerts: string[]; notes: string[] }> {
  const r = await fetch("/api/generate-section", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    throw new Error(d.detail ?? `generate-section ${r.status}`);
  }
  return r.json();
}

export async function fetchTemplates(): Promise<string[]> {
  const r = await fetch("/api/templates");
  if (!r.ok) throw new Error(`templates ${r.status}`);
  const j = await r.json();
  return j.templates;
}

export async function fetchProjects(): Promise<ProjectSummary[]> {
  const r = await fetch("/api/projects");
  if (!r.ok) throw new Error(`projects ${r.status}`);
  const result = await r.json();
  return result.projects;
}

export async function createProject(name: string, html: string): Promise<ProjectSnapshot> {
  const r = await fetch("/api/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, html }),
  });
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    throw new Error(d.detail ?? `projects ${r.status}`);
  }
  return r.json();
}

export async function fetchProject(projectId: string): Promise<ProjectSnapshot> {
  const r = await fetch(`/api/projects/${encodeURIComponent(projectId)}`);
  if (!r.ok) throw new Error(`projects ${r.status}`);
  return r.json();
}

export async function savePage(
  pageId: string,
  html: string,
  expectedVersion: number,
  source = "autosave",
): Promise<PageSnapshot> {
  const r = await fetch(`/api/pages/${encodeURIComponent(pageId)}/document`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ html, expected_version: expectedVersion, source }),
  });
  if (r.status === 409) {
    const d = await r.json();
    throw new PageVersionConflictError(d.detail?.current_version ?? expectedVersion);
  }
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    throw new Error(d.detail ?? `pages ${r.status}`);
  }
  return r.json();
}

export async function fetchRevisions(pageId: string): Promise<RevisionSummary[]> {
  const r = await fetch(`/api/pages/${encodeURIComponent(pageId)}/revisions`);
  if (!r.ok) throw new Error(`revisions ${r.status}`);
  const result = await r.json();
  return result.revisions;
}

export async function restoreRevision(
  pageId: string,
  revisionId: string,
  expectedVersion: number,
): Promise<PageSnapshot> {
  const r = await fetch(
    `/api/pages/${encodeURIComponent(pageId)}/revisions/${encodeURIComponent(revisionId)}/restore`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expected_version: expectedVersion }),
    },
  );
  if (r.status === 409) {
    const d = await r.json();
    throw new PageVersionConflictError(d.detail?.current_version ?? expectedVersion);
  }
  if (!r.ok) throw new Error(`revisions ${r.status}`);
  return r.json();
}

export async function saveTemplate(name: string, html: string): Promise<void> {
  const r = await fetch("/api/templates", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, html }),
  });
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    throw new Error(d.detail ?? `templates ${r.status}`);
  }
}

export async function loadTemplate(name: string): Promise<string> {
  const r = await fetch(`/api/templates/${encodeURIComponent(name)}`);
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    throw new Error(d.detail ?? `templates ${r.status}`);
  }
  const result = await r.json();
  return result.html;
}

export async function deleteTemplate(name: string): Promise<void> {
  const r = await fetch(`/api/templates/${encodeURIComponent(name)}`, { method: "DELETE" });
  if (!r.ok) throw new Error(`templates ${r.status}`);
}

export interface DnaItem {
  name: string;
  signature: string;
  guidance: string;
}

export async function fetchDnas(): Promise<DnaItem[]> {
  const r = await fetch("/api/layout-dnas");
  if (!r.ok) throw new Error(`dnas ${r.status}`);
  const j = await r.json();
  return j.dnas;
}

export async function saveDna(html: string): Promise<void> {
  const r = await fetch("/api/layout-dnas", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ html }),
  });
  if (!r.ok) throw new Error(`dnas ${r.status}`);
}

export async function exportPage(
  html: string,
  mode: "single" | "split"
): Promise<{ mode: string; files: Record<string, string> }> {
  const r = await fetch("/api/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ html, mode }),
  });
  if (!r.ok) throw new Error(`export ${r.status}`);
  return r.json();
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  html: string | null;
  message: string;
  intent: string | null;
  validation_errors: string[];
  validation_notes: string[];
  error: string | null;
}

export async function chat(req: {
  message: string;
  thread_id: string;
  current_code: string | null;
  tone: string;
  complexity: string;
  strict_minimal: boolean;
  profile: string | null;
  layout_dna_guidance: string;
}): Promise<ChatResponse> {
  const r = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    throw new Error(d.detail ?? `chat ${r.status}`);
  }
  return r.json();
}
