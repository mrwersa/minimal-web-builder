import type { EditorDocumentV1 } from "./editor/document";

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

export interface User {
  id: string;
  email: string;
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
  current_revision_id: string | null;
  html: string;
  document: EditorDocumentV1 | null;
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
  name: string | null;
  parent_revision_id: string | null;
  created_at: string;
}

export class PageVersionConflictError extends Error {
  constructor(public currentVersion: number) {
    super(`A newer page version (${currentVersion}) is already saved`);
  }
}

async function readPageResponse(
  response: Response,
  expectedVersion: number,
  fallback: string,
): Promise<PageSnapshot> {
  if (response.status === 409) {
    const payload = await response.json();
    throw new PageVersionConflictError(
      payload.detail?.current_version ?? expectedVersion,
    );
  }
  return readJson(response, fallback);
}

const JSON_HEADERS = { "Content-Type": "application/json" };

function jsonRequest(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { ...JSON_HEADERS, "Idempotency-Key": crypto.randomUUID() },
    body: JSON.stringify(body),
  };
}

async function readJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = payload.detail;
    const message =
      typeof detail === "string"
        ? detail
        : typeof detail?.message === "string"
          ? detail.message
          : fallback;
    throw new Error(message);
  }
  return response.json();
}

async function requestJson<T>(
  url: string,
  init?: RequestInit,
  fallback = `request ${url}`,
): Promise<T> {
  return readJson<T>(await fetch(url, init), fallback);
}

export async function fetchCurrentUser(): Promise<User> {
  return requestJson("/api/auth/me", undefined, "Unable to restore your session");
}

export async function register(email: string, password: string): Promise<User> {
  return requestJson(
    "/api/auth/register",
    jsonRequest("POST", { email, password }),
    "Unable to create account",
  );
}

export async function login(email: string, password: string): Promise<User> {
  return requestJson(
    "/api/auth/login",
    jsonRequest("POST", { email, password }),
    "Unable to sign in",
  );
}

export async function logout(): Promise<void> {
  const response = await fetch("/api/auth/logout", { method: "POST" });
  if (!response.ok) throw new Error("Unable to sign out");
}

export async function fetchOptions(): Promise<OptionsResponse> {
  return requestJson("/api/options", undefined, "Unable to load options");
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
  thread_id: string;
}): Promise<GenerateResponse> {
  return requestJson(
    "/api/generate",
    jsonRequest("POST", req),
    "Generation failed",
  );
}

export async function fetchSections(code: string): Promise<SectionInfo[]> {
  const result = await requestJson<{ sections: SectionInfo[] }>(
    "/api/sections",
    jsonRequest("POST", { code }),
    "Unable to inspect sections",
  );
  return result.sections;
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
  thread_id: string;
}): Promise<{ html: string; safety_alerts: string[]; notes: string[] }> {
  return requestJson(
    "/api/generate-section",
    jsonRequest("POST", req),
    "Section regeneration failed",
  );
}

export async function fetchTemplates(): Promise<string[]> {
  const result = await requestJson<{ templates: string[] }>(
    "/api/templates",
    undefined,
    "Unable to load templates",
  );
  return result.templates;
}

export async function fetchProjects(search = ""): Promise<ProjectSummary[]> {
  const query = search.trim() ? `?search=${encodeURIComponent(search.trim())}` : "";
  const result = await requestJson<{ projects: ProjectSummary[] }>(
    `/api/projects${query}`,
    undefined,
    "Unable to load projects",
  );
  return result.projects;
}

export async function createProject(
  name: string,
  html: string,
  document?: EditorDocumentV1 | null,
): Promise<ProjectSnapshot> {
  return requestJson(
    "/api/projects",
    jsonRequest("POST", { name, html, document }),
    "Unable to create project",
  );
}

export async function fetchProject(projectId: string): Promise<ProjectSnapshot> {
  return requestJson(
    `/api/projects/${encodeURIComponent(projectId)}`,
    undefined,
    "Unable to open project",
  );
}

export async function renameProject(
  projectId: string,
  name: string,
): Promise<ProjectSnapshot> {
  return requestJson(
    `/api/projects/${encodeURIComponent(projectId)}`,
    jsonRequest("PATCH", { name }),
    "Unable to rename project",
  );
}

export async function duplicateProject(
  projectId: string,
  name?: string,
): Promise<ProjectSnapshot> {
  return requestJson(
    `/api/projects/${encodeURIComponent(projectId)}/duplicate`,
    jsonRequest("POST", { name }),
    "Unable to duplicate project",
  );
}

export async function archiveProject(projectId: string): Promise<ProjectSnapshot> {
  return requestJson(
    `/api/projects/${encodeURIComponent(projectId)}`,
    { method: "DELETE" },
    "Unable to archive project",
  );
}

export async function savePage(
  pageId: string,
  html: string,
  expectedVersion: number,
  source = "autosave",
  document?: EditorDocumentV1 | null,
): Promise<PageSnapshot> {
  const r = await fetch(
    `/api/pages/${encodeURIComponent(pageId)}/document`,
    jsonRequest("PUT", { html, document, expected_version: expectedVersion, source }),
  );
  return readPageResponse(r, expectedVersion, "Unable to save page");
}

export async function fetchRevisions(pageId: string): Promise<RevisionSummary[]> {
  const result = await requestJson<{ revisions: RevisionSummary[] }>(
    `/api/pages/${encodeURIComponent(pageId)}/revisions`,
    undefined,
    "Unable to load version history",
  );
  return result.revisions;
}

export async function restoreRevision(
  pageId: string,
  revisionId: string,
  expectedVersion: number,
): Promise<PageSnapshot> {
  const r = await fetch(
    `/api/pages/${encodeURIComponent(pageId)}/revisions/${encodeURIComponent(revisionId)}/restore`,
    jsonRequest("POST", { expected_version: expectedVersion }),
  );
  return readPageResponse(r, expectedVersion, "Unable to restore revision");
}

export async function createCheckpoint(
  pageId: string,
  name: string,
  expectedVersion: number,
): Promise<PageSnapshot> {
  const response = await fetch(
    `/api/pages/${encodeURIComponent(pageId)}/checkpoints`,
    jsonRequest("POST", { name, expected_version: expectedVersion }),
  );
  return readPageResponse(response, expectedVersion, "Unable to create checkpoint");
}

export async function duplicateRevision(
  pageId: string,
  revisionId: string,
  name: string,
): Promise<ProjectSnapshot> {
  return requestJson(
    `/api/pages/${encodeURIComponent(pageId)}/revisions/${encodeURIComponent(revisionId)}/duplicate`,
    jsonRequest("POST", { name }),
    "Unable to duplicate revision",
  );
}

export async function saveTemplate(name: string, html: string): Promise<void> {
  await requestJson(
    "/api/templates",
    jsonRequest("POST", { name, html }),
    "Unable to save template",
  );
}

export async function loadTemplate(name: string): Promise<string> {
  const result = await requestJson<{ html: string }>(
    `/api/templates/${encodeURIComponent(name)}`,
    undefined,
    "Unable to load template",
  );
  return result.html;
}

export async function deleteTemplate(name: string): Promise<void> {
  await requestJson(
    `/api/templates/${encodeURIComponent(name)}`,
    { method: "DELETE" },
    "Unable to delete template",
  );
}

export interface DnaItem {
  name: string;
  signature: string;
  guidance: string;
}

export async function fetchDnas(): Promise<DnaItem[]> {
  const result = await requestJson<{ dnas: DnaItem[] }>(
    "/api/layout-dnas",
    undefined,
    "Unable to load layout DNA",
  );
  return result.dnas;
}

export async function saveDna(html: string): Promise<void> {
  await requestJson(
    "/api/layout-dnas",
    jsonRequest("POST", { html }),
    "Unable to save layout DNA",
  );
}

export async function exportPage(
  html: string,
  mode: "single" | "split"
): Promise<{ mode: string; files: Record<string, string> }> {
  return requestJson(
    "/api/export",
    jsonRequest("POST", { html, mode }),
    "Unable to export page",
  );
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

export interface ConversationSnapshot {
  thread_id: string;
  messages: ChatMessage[];
  current_code: string | null;
  document: EditorDocumentV1 | null;
}

export async function fetchConversation(
  threadId: string,
): Promise<ConversationSnapshot | null> {
  const response = await fetch(`/api/conversations/${encodeURIComponent(threadId)}`);
  if (response.status === 404) return null;
  return readJson(response, "Unable to restore conversation");
}

export async function saveConversationDocument(
  threadId: string,
  code: string,
  document?: EditorDocumentV1 | null,
): Promise<void> {
  await requestJson(
    `/api/conversations/${encodeURIComponent(threadId)}/document`,
    jsonRequest("PUT", { code, document }),
    "Unable to save draft",
  );
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
  target_node_id?: string;
}): Promise<ChatResponse> {
  return requestJson(
    "/api/chat",
    jsonRequest("POST", req),
    "Chat request failed",
  );
}
