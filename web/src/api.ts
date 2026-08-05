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
  const r = await fetch(`/api/sections?code=${encodeURIComponent(code)}`);
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

export async function fetchPreviewDoc(html: string, editing: boolean): Promise<string> {
  const r = await fetch(
    `/api/preview-doc?html=${encodeURIComponent(html)}&editing=${editing ? "true" : "false"}`
  );
  if (!r.ok) throw new Error(`preview-doc ${r.status}`);
  const j = await r.json();
  return j.doc;
}

export async function fetchTemplates(): Promise<string[]> {
  const r = await fetch("/api/templates");
  if (!r.ok) throw new Error(`templates ${r.status}`);
  const j = await r.json();
  return j.templates;
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