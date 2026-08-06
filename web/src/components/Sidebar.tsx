import { useEffect } from "react";
import {
  Sparkles,
  Sliders,
  Wand2,
  Layers,
  Save,
  Trash2,
  MousePointerClick,
  ChevronDown,
} from "lucide-react";
import { useStore } from "../store";
import { cn } from "../lib/utils";

const COL_LABEL = "mb-1 block text-[11px] font-semibold uppercase tracking-wider text-muted2";

function Select({
  value,
  options,
  onChange,
  disabled,
}: {
  value: string;
  options: { key?: string; label: string }[];
  onChange: (v: string) => void;
  disabled?: boolean;
}) {
  return (
    <select
      className="w-full cursor-pointer rounded-lg border border-border2 bg-surface px-3 py-2 text-sm text-text2 transition-colors hover:border-muted2 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accentSoft disabled:cursor-not-allowed disabled:opacity-50"
      value={value}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value)}
    >
      {options.map((o) => {
        const v = o.key ?? o.label;
        return (
          <option key={v} value={v}>
            {o.label}
          </option>
        );
      })}
    </select>
  );
}

function CollapsibleSection({
  icon,
  title,
  children,
  defaultOpen = true,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  return (
    <details open={defaultOpen} className="group border-b border-border2 pb-1">
      <summary className="flex cursor-pointer list-none items-center gap-2 py-2 text-sm font-semibold text-text2">
        <span className="text-muted2">{icon}</span>
        {title}
        <ChevronDown className="ml-auto h-4 w-4 shrink-0 text-muted2 transition-transform group-open:rotate-180" />
      </summary>
      <div className="pb-3 pt-1">{children}</div>
    </details>
  );
}

export default function Sidebar() {
  const s = useStore();
  const opts = s.options;

  useEffect(() => {
    if (s.code) s.refreshSections();
  }, [s.code]); // eslint-disable-line

  useEffect(() => {
    s.refreshTemplates();
    s.refreshDnas();
  }, []); // eslint-disable-line

  if (!opts) {
    return (
      <div className="flex h-full w-80 items-center justify-center border-r border-border2 bg-surface">
        <div className="animate-pulse text-sm text-muted">Loading…</div>
      </div>
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
        <span className="text-sm font-bold text-text2">Minimal Web Builder</span>
      </div>

      <div className="flex-1 overflow-y-auto px-4">
        {/* Generation */}
        <CollapsibleSection icon={<Sliders className="h-4 w-4" />} title="Generation">
          <label className={COL_LABEL}>Profile</label>
          <Select
            value={s.profile}
            options={opts.profiles.map((p) => ({ key: p.id, label: p.label }))}
            onChange={(v) => s.set("profile", v)}
          />
          <p className="mt-1 text-xs text-muted2">
            {profileActive
              ? opts.profiles.find((p) => p.id === s.profile)?.description
              : "Set tone, complexity, and strict mode manually."}
          </p>

          <div className="mt-3 grid grid-cols-2 gap-3">
            <div>
              <label className={COL_LABEL}>Tone</label>
              <Select
                value={s.tone}
                options={opts.tones}
                onChange={(v) => s.set("tone", v)}
                disabled={profileActive}
              />
            </div>
            <div>
              <label className={COL_LABEL}>Complexity</label>
              <Select
                value={s.complexity}
                options={opts.complexities}
                onChange={(v) => s.set("complexity", v)}
                disabled={profileActive}
              />
            </div>
          </div>

          <label className="mt-3 flex items-center gap-2 text-sm text-text2">
            <input
              type="checkbox"
              checked={s.strictMinimal}
              disabled={profileActive}
              onChange={(e) => s.set("strictMinimal", e.target.checked)}
              className="h-4 w-4 rounded accent-accent"
            />
            Strict minimal mode
          </label>

          {/* Constraint-first */}
          <details className="mt-3 rounded-lg border border-border2 p-2">
            <summary className="cursor-pointer text-xs font-medium text-muted">
              Constraint-first generation
            </summary>
            <div className="mt-2 space-y-3">
              <label className="flex items-center gap-2 text-sm text-text2">
                <input
                  type="checkbox"
                  checked={s.constraintMode}
                  onChange={(e) => s.set("constraintMode", e.target.checked)}
                  className="h-4 w-4 rounded accent-accent"
                />
                Generate from constraints
              </label>
              {s.constraintMode && (
                <>
                  <div>
                    <label className={COL_LABEL}>Sections</label>
                    <div className="flex flex-wrap gap-1.5">
                      {opts.sections.map((sec) => {
                        const on = s.constraintSections.includes(sec.key);
                        return (
                          <button
                            key={sec.key}
                            onClick={() =>
                              s.set(
                                "constraintSections",
                                on
                                  ? s.constraintSections.filter((x) => x !== sec.key)
                                  : [...s.constraintSections, sec.key]
                              )
                            }
                            className={cn(
                              "rounded-full border px-2.5 py-1 text-xs transition-colors",
                              on
                                ? "border-accent bg-accentSoft text-accent"
                                : "border-border2 bg-surface text-muted2 hover:border-muted2"
                            )}
                          >
                            {sec.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className={COL_LABEL}>Color limit</label>
                      <Select
                        value={s.constraintColor}
                        options={opts.color_limits}
                        onChange={(v) => s.set("constraintColor", v)}
                      />
                    </div>
                    <div>
                      <label className={COL_LABEL}>Density</label>
                      <Select
                        value={s.constraintDensity}
                        options={opts.complexities}
                        onChange={(v) => s.set("constraintDensity", v)}
                      />
                    </div>
                  </div>
                  <button
                    disabled={s.busy}
                    onClick={() => s.runConstraints()}
                    className="w-full rounded-lg bg-accent px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-accentHover disabled:opacity-50"
                  >
                    Generate from constraints
                  </button>
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
              <label className="flex items-center gap-2 text-sm text-text2">
                <input
                  type="checkbox"
                  checked={s.editing}
                  disabled={s.busy}
                  onChange={(e) => s.set("editing", e.target.checked)}
                  className="h-4 w-4 rounded accent-accent"
                />
                <MousePointerClick className="h-3.5 w-3.5 text-muted2" />
                WYSIWYG editing
              </label>
              <div>
                <label className={COL_LABEL}>Section</label>
                <Select
                  value={String(s.sectionIndex)}
                  options={s.sections.map((sec, i) => ({
                    key: String(i),
                    label: `${i + 1}. <${sec.tag}>${sec.snippet ? " — " + sec.snippet : ""}`,
                  }))}
                  onChange={(v) => s.set("sectionIndex", Number(v))}
                />
              </div>
              <div>
                <label className={COL_LABEL}>Refine focus</label>
                <Select
                  value={s.refineAspect}
                  options={opts.refine_aspects}
                  onChange={(v) => s.set("refineAspect", v)}
                />
              </div>
              <button
                disabled={s.busy || s.sections.length === 0}
                onClick={() => s.runRegenerate("")}
                className="w-full rounded-lg border border-accent bg-accentSoft px-3 py-2 text-sm font-medium text-accent transition-colors hover:bg-accent hover:text-white disabled:opacity-50"
              >
                Regenerate section
              </button>
            </div>
          )}
        </CollapsibleSection>

        {/* Layout DNA */}
        <CollapsibleSection icon={<Layers className="h-4 w-4" />} title="Layout DNA" defaultOpen={false}>
          {!s.code ? (
            <p className="text-xs text-muted2">Generate a page to inspect its layout DNA.</p>
          ) : (
            <div className="space-y-2">
              <button
                onClick={() => s.doSaveDna()}
                className="flex w-full items-center gap-2 rounded-lg border border-border2 px-3 py-2 text-sm text-text2 transition-colors hover:bg-bg"
              >
                <Save className="h-3.5 w-3.5 text-muted2" />
                Save current layout
              </button>
              {s.dnas.length > 0 && (
                <div className="space-y-1.5">
                  {s.dnas.map((d) => (
                    <div
                      key={d.name}
                      className={cn(
                        "flex items-center justify-between rounded-lg border px-2.5 py-1.5 text-xs",
                        s.layoutDnaGuidance === d.guidance
                          ? "border-accent bg-accentSoft"
                          : "border-border2"
                      )}
                    >
                      <span className="truncate text-muted">
                        {d.name}: {d.signature}
                      </span>
                      <span className="flex shrink-0 gap-1">
                        <button
                          onClick={() => s.set("layoutDnaGuidance", d.guidance)}
                          className="rounded px-1.5 py-0.5 font-medium text-accent hover:bg-accentSoft"
                        >
                          use
                        </button>
                        <button
                          onClick={() => s.set("layoutDnaGuidance", "")}
                          className="rounded px-1.5 py-0.5 text-muted2 hover:bg-bg"
                        >
                          clear
                        </button>
                      </span>
                    </div>
                  ))}
                </div>
              )}
              {s.layoutDnaGuidance && (
                <p className="text-xs text-muted2">Applies to the next generation.</p>
              )}
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
                <input
                  value={s.templateName}
                  onChange={(e) => s.set("templateName", e.target.value)}
                  placeholder="template name"
                  className="flex-1 rounded-lg border border-border2 bg-surface px-2.5 py-2 text-sm focus:border-accent focus:outline-none"
                />
                <button
                  onClick={() => s.doSaveTemplate()}
                  className="rounded-lg border border-border2 px-3 py-2 text-sm transition-colors hover:bg-bg"
                >
                  Save
                </button>
              </div>
              {s.templates.length > 0 && (
                <div className="space-y-1.5">
                  {s.templates.map((t) => (
                    <div key={t} className="flex items-center justify-between rounded-lg border border-border2 px-2.5 py-1.5 text-xs">
                      <span className="truncate text-muted">{t}</span>
                      <button
                        onClick={() => s.doDeleteTemplate(t)}
                        className="shrink-0 rounded p-1 text-muted2 transition-colors hover:bg-dangerSoft hover:text-danger"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
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