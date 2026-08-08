import { useEffect } from "react";
import {
  Sparkles, Sliders, Wand2, Layers, Save, Trash2, FolderOpen,
  MousePointerClick, ChevronDown, FolderKanban,
} from "lucide-react";
import { useStore } from "../store";
import { cn } from "../lib/utils";
import { Select } from "./ui/Select";
import { Switch } from "./ui/Switch";
import { Button } from "./ui/Button";
import { Input } from "./ui/Input";
import { Separator } from "./ui/Separator";
import ProjectPanel from "./ProjectPanel";

const COL_LABEL = "mb-1 block text-[11px] font-semibold uppercase tracking-wider text-muted2";

function CollapsibleSection({ icon, title, children, defaultOpen = true }: {
  icon: React.ReactNode; title: string; children: React.ReactNode; defaultOpen?: boolean;
}) {
  return (
    <details open={defaultOpen} className="group">
      <summary className="flex cursor-pointer list-none items-center gap-2 py-2 text-sm font-semibold text-text2">
        <span className="text-muted2">{icon}</span>
        {title}
        <ChevronDown className="ml-auto h-4 w-4 shrink-0 text-muted2 transition-transform group-open:rotate-180" />
      </summary>
      <div className="pb-3 pt-1">{children}</div>
      <Separator />
    </details>
  );
}

export default function Sidebar() {
  const s = useStore();
  const opts = s.options;

  useEffect(() => { if (s.code) s.refreshSections(); }, [s.code]); // eslint-disable-line
  useEffect(() => { s.refreshTemplates(); s.refreshDnas(); }, []); // eslint-disable-line

  if (!opts) {
    return (
      <aside className="flex h-full w-80 items-center justify-center border-r border-border2 bg-surface">
        <Spinner size="md" />
      </aside>
    );
  }

  const profileActive = s.profile !== opts.custom_profile_id;

  return (
    <aside className="flex h-full w-80 flex-col border-r border-border2 bg-surface">
      {/* Brand */}
      <div className="flex items-center gap-2 border-b border-border2 px-4 py-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accentSoft text-accent">
          <Sparkles className="h-4 w-4" />
        </div>
        <span className="text-sm font-bold">Minimal Web Builder</span>
      </div>

      <div className="flex-1 space-y-1 overflow-y-auto px-4 py-2">
        {/* Projects */}
        <CollapsibleSection icon={<FolderKanban className="h-4 w-4" />} title="Projects">
          <ProjectPanel />
        </CollapsibleSection>

        {/* Generation */}
        <CollapsibleSection icon={<Sliders className="h-4 w-4" />} title="Generation">
          <label className={COL_LABEL}>Profile</label>
          <Select
            value={s.profile}
            options={opts.profiles.map((p) => ({ value: p.id, label: p.label }))}
            onChange={(v) => s.set("profile", v)}
          />
          <p className="mt-1 text-xs text-muted2">
            {profileActive ? opts.profiles.find((p) => p.id === s.profile)?.description : "Set tone, complexity, and strict mode manually."}
          </p>

          <div className="mt-3 grid grid-cols-2 gap-3">
            <div>
              <label className={COL_LABEL}>Tone</label>
              <Select value={s.tone} options={opts.tones.map((t: any) => ({ value: t.key, label: t.label }))} onChange={(v) => s.set("tone", v)} disabled={profileActive} />
            </div>
            <div>
              <label className={COL_LABEL}>Complexity</label>
              <Select value={s.complexity} options={opts.complexities.map((c: any) => ({ value: c.key, label: c.label }))} onChange={(v) => s.set("complexity", v)} disabled={profileActive} />
            </div>
          </div>

          <div className="mt-3 flex items-center gap-2">
            <Switch checked={s.strictMinimal} onChange={(v) => s.set("strictMinimal", v)} disabled={profileActive} id="strict" />
            <label htmlFor="strict" className="text-sm text-text2 cursor-pointer">Strict minimal mode</label>
          </div>

          {/* Constraint-first */}
          <details className="mt-3 rounded-lg border border-border2 p-2">
            <summary className="cursor-pointer text-xs font-medium text-muted">Constraint-first generation</summary>
            <div className="mt-2 space-y-3">
              <div className="flex items-center gap-2">
                <Switch checked={s.constraintMode} onChange={(v) => s.set("constraintMode", v)} id="cm" />
                <label htmlFor="cm" className="text-sm">Generate from constraints</label>
              </div>
              {s.constraintMode && (
                <>
                  <div>
                    <label className={COL_LABEL}>Sections</label>
                    <div className="flex flex-wrap gap-1.5">
                      {opts.sections.map((sec: any) => {
                        const on = s.constraintSections.includes(sec.key);
                        return (
                          <button key={sec.key} onClick={() => s.set("constraintSections", on ? s.constraintSections.filter((x) => x !== sec.key) : [...s.constraintSections, sec.key])}
                            className={cn("rounded-full border px-2.5 py-1 text-xs transition-colors", on ? "border-accent bg-accentSoft text-accent" : "border-border2 text-muted2 hover:border-muted2")}>
                            {sec.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className={COL_LABEL}>Color limit</label>
                      <Select value={s.constraintColor} options={opts.color_limits.map((c: any) => ({ value: c.key, label: c.label }))} onChange={(v) => s.set("constraintColor", v)} />
                    </div>
                    <div>
                      <label className={COL_LABEL}>Density</label>
                      <Select value={s.constraintDensity} options={opts.complexities.map((c: any) => ({ value: c.key, label: c.label }))} onChange={(v) => s.set("constraintDensity", v)} />
                    </div>
                  </div>
                  <Button className="w-full" disabled={s.busy} onClick={() => s.runConstraints()}>Generate from constraints</Button>
                </>
              )}
            </div>
          </details>
        </CollapsibleSection>

        {/* Refine */}
        <CollapsibleSection icon={<Wand2 className="h-4 w-4" />} title="Refine">
          {!s.code ? (
            <p className="text-xs text-muted2">Generate a page first to refine it.</p>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Switch checked={s.editing} onChange={(v) => s.set("editing", v)} disabled={s.busy} id="wys" />
                <label htmlFor="wys" className="flex items-center gap-1.5 text-sm">
                  <MousePointerClick className="h-3.5 w-3.5 text-muted2" /> WYSIWYG editing
                </label>
              </div>
              <div>
                <label className={COL_LABEL}>Section</label>
                <Select
                  value={String(s.sectionIndex)}
                  options={s.sections.map((sec: any, i: number) => ({ value: String(i), label: `${i + 1}. <${sec.tag}>${sec.snippet ? " — " + sec.snippet : ""}` }))}
                  onChange={(v) => s.set("sectionIndex", Number(v))}
                />
              </div>
              <div>
                <label className={COL_LABEL}>Refine focus</label>
                <Select value={s.refineAspect} options={opts.refine_aspects.map((a: any) => ({ value: a.key, label: a.label }))} onChange={(v) => s.set("refineAspect", v)} />
              </div>
              <Button variant="secondary" className="w-full" disabled={s.busy || s.sections.length === 0} onClick={() => s.runRegenerate("")}>Regenerate section</Button>
            </div>
          )}
        </CollapsibleSection>

        {/* Layout DNA */}
        <CollapsibleSection icon={<Layers className="h-4 w-4" />} title="Layout DNA" defaultOpen={false}>
          {!s.code ? (
            <p className="text-xs text-muted2">Generate a page to inspect its layout DNA.</p>
          ) : (
            <div className="space-y-2">
              <Button variant="outline" className="w-full" onClick={() => s.doSaveDna()}>
                <Save className="h-3.5 w-3.5" /> Save current layout
              </Button>
              {s.dnas.length > 0 && (
                <div className="space-y-1.5">
                  {s.dnas.map((d) => (
                    <div key={d.name} className={cn("flex items-center justify-between rounded-lg border px-2.5 py-1.5 text-xs", s.layoutDnaGuidance === d.guidance ? "border-accent bg-accentSoft" : "border-border2")}>
                      <span className="truncate text-muted">{d.name}: {d.signature}</span>
                      <span className="flex shrink-0 gap-1">
                        <button onClick={() => s.set("layoutDnaGuidance", d.guidance)} className="rounded px-1.5 py-0.5 font-medium text-accent hover:bg-accentSoft">use</button>
                        <button onClick={() => s.set("layoutDnaGuidance", "")} className="rounded px-1.5 py-0.5 text-muted2 hover:bg-bg">clear</button>
                      </span>
                    </div>
                  ))}
                </div>
              )}
              {s.layoutDnaGuidance && <p className="text-xs text-muted2">Applies to the next generation.</p>}
            </div>
          )}
        </CollapsibleSection>

        {/* Templates */}
        <CollapsibleSection icon={<Save className="h-4 w-4" />} title="Templates" defaultOpen={false}>
          {!s.code ? (
            <p className="text-xs text-muted2">Generate a page to save it as a template.</p>
          ) : (
            <div className="space-y-2">
              <div className="flex gap-2">
                <Input value={s.templateName} onChange={(e) => s.set("templateName", e.target.value)} placeholder="template name" className="flex-1" />
                <Button variant="outline" onClick={() => s.doSaveTemplate()}>Save</Button>
              </div>
              {s.templates.length > 0 && (
                <div className="space-y-1.5">
                  {s.templates.map((t) => (
                    <div key={t} className="flex items-center justify-between rounded-lg border border-border2 px-2.5 py-1.5 text-xs">
                      <span className="truncate text-muted">{t}</span>
                      <span className="flex shrink-0 gap-1">
                        <button onClick={() => s.doLoadTemplate(t)} title={`Use ${t}`} className="rounded p-1 text-muted2 hover:bg-accentSoft hover:text-accent">
                          <FolderOpen className="h-3.5 w-3.5" />
                        </button>
                        <button onClick={() => s.doDeleteTemplate(t)} title={`Delete ${t}`} className="rounded p-1 text-muted2 hover:bg-red-50 hover:text-danger">
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </CollapsibleSection>
      </div>
    </aside>
  );
}

import { Spinner } from "./ui/Spinner";
