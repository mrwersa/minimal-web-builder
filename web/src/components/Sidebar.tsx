import { useEffect } from "react";
import { useStore } from "../store";

const labelCls = "block text-xs font-semibold uppercase tracking-wide text-muted mb-1";

function Select<T extends string>({
  value,
  options,
  onChange,
  disabled,
}: {
  value: string;
  options: { key: T; label: string }[] | { id: string; label: string }[];
  onChange: (v: string) => void;
  disabled?: boolean;
}) {
  return (
    <select
      className="w-full rounded-lg border border-border2 bg-surface px-2.5 py-2 text-sm text-text2 focus:border-accent focus:outline-none disabled:opacity-50"
      value={value}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value)}
    >
      {(options as { key?: string; id?: string; label: string }[]).map((o) => {
        const v = o.key ?? o.id ?? "";
        return (
          <option key={v} value={v}>
            {o.label}
          </option>
        );
      })}
    </select>
  );
}

export default function Sidebar() {
  const s = useStore();
  const opts = s.options;

  useEffect(() => {
    if (s.code) s.refreshSections();
  }, [s.code]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    s.refreshTemplates();
    s.refreshDnas();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (!opts) return <div className="p-4 text-sm text-muted">Loading…</div>;

  const profileActive = s.profile !== opts.custom_profile_id;

  return (
    <aside className="flex h-full w-80 flex-col border-r border-border2 bg-surface">
      <div className="flex-1 overflow-y-auto p-4">
        <h1 className="mb-4 flex items-center gap-2 text-lg font-semibold text-text2">
          <span>🧩</span> Minimal Web Builder
        </h1>

        {/* Generation */}
        <section className="mb-5">
          <h2 className="mb-2 text-sm font-semibold text-text2">Generation</h2>
          <div className={labelCls}>Profile</div>
          <Select
            value={s.profile}
            options={opts.profiles.map((p) => ({ key: p.id, label: p.label }))}
            onChange={(v) => s.set("profile", v)}
          />
          <div className="mt-1 text-xs text-muted">
            {profileActive
              ? opts.profiles.find((p) => p.id === s.profile)?.description
              : "Set tone, complexity, and strict minimal mode manually."}
          </div>

          <div className="mt-3 grid grid-cols-2 gap-3">
            <div>
              <div className={labelCls}>Tone</div>
              <Select
                value={s.tone}
                options={opts.tones}
                onChange={(v) => s.set("tone", v)}
                disabled={profileActive}
              />
            </div>
            <div>
              <div className={labelCls}>Complexity</div>
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
              className="h-4 w-4 accent-accent"
            />
            Strict minimal mode
          </label>

          {/* Constraint-first */}
          <details className="mt-3 rounded-lg border border-border2 p-2">
            <summary className="cursor-pointer text-sm font-medium text-text2">
              Constraint-first generation
            </summary>
            <div className="mt-3 space-y-3">
              <label className="flex items-center gap-2 text-sm text-text2">
                <input
                  type="checkbox"
                  checked={s.constraintMode}
                  onChange={(e) => s.set("constraintMode", e.target.checked)}
                  className="h-4 w-4 accent-accent"
                />
                Generate from constraints
              </label>
              {s.constraintMode && (
                <>
                  <div>
                    <div className={labelCls}>Sections</div>
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
                            className={
                              "rounded-full border px-2.5 py-1 text-xs " +
                              (on
                                ? "border-accent bg-accentSoft text-accent"
                                : "border-border2 bg-surface text-muted")
                            }
                          >
                            {sec.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <div className={labelCls}>Color limit</div>
                      <Select
                        value={s.constraintColor}
                        options={opts.color_limits}
                        onChange={(v) => s.set("constraintColor", v)}
                      />
                    </div>
                    <div>
                      <div className={labelCls}>Density</div>
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
                    className="w-full rounded-lg bg-accent px-3 py-2 text-sm font-medium text-white hover:bg-accent/90 disabled:opacity-50"
                  >
                    Generate from constraints
                  </button>
                </>
              )}
            </div>
          </details>
        </section>

        {/* Refine */}
        <section className="mb-5">
          <h2 className="mb-2 text-sm font-semibold text-text2">Refine</h2>
          {!s.code ? (
            <p className="text-xs text-muted">Generate a page first, then refine it.</p>
          ) : (
            <>
              <label className="flex items-center gap-2 text-sm text-text2">
                <input
                  type="checkbox"
                  checked={s.editing}
                  disabled={s.busy}
                  onChange={(e) => s.set("editing", e.target.checked)}
                  className="h-4 w-4 accent-accent"
                />
                WYSIWYG editing
              </label>

              <div className="mt-3">
                <div className={labelCls}>Section</div>
                <Select
                  value={String(s.sectionIndex)}
                  options={s.sections.map((sec, i) => ({
                    key: String(i),
                    label: `${i + 1}. <${sec.tag}>${sec.snippet ? " — " + sec.snippet : ""}`,
                  }))}
                  onChange={(v) => s.set("sectionIndex", Number(v))}
                />
              </div>
              <div className="mt-3">
                <div className={labelCls}>Refine focus</div>
                <Select
                  value={s.refineAspect}
                  options={opts.refine_aspects}
                  onChange={(v) => s.set("refineAspect", v)}
                />
              </div>
              <button
                disabled={s.busy || s.sections.length === 0}
                onClick={() => s.runRegenerate("")}
                className="mt-3 w-full rounded-lg border border-accent bg-accentSoft px-3 py-2 text-sm font-medium text-accent hover:bg-accent hover:text-white disabled:opacity-50"
              >
                Regenerate section
              </button>
            </>
          )}
        </section>

        {/* Layout DNA */}
        <section className="mb-5">
          <h2 className="mb-2 text-sm font-semibold text-text2">Layout DNA</h2>
          {!s.code ? (
            <p className="text-xs text-muted">Generate a page to inspect its layout DNA.</p>
          ) : (
            <>
              <button
                onClick={() => s.doSaveDna()}
                className="w-full rounded-lg border border-border2 px-3 py-2 text-sm hover:bg-bg"
              >
                Save current layout as DNA
              </button>
              {s.dnas.length > 0 && (
                <div className="mt-3">
                  <div className={labelCls}>Saved layouts</div>
                  <div className="space-y-1.5">
                    {s.dnas.map((d) => (
                      <div
                        key={d.name}
                        className={
                          "flex items-center justify-between rounded-lg border px-2.5 py-1.5 text-xs " +
                          (s.layoutDnaGuidance === d.guidance
                            ? "border-accent bg-accentSoft"
                            : "border-border2")
                        }
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
                            className="rounded px-1.5 py-0.5 text-muted hover:bg-bg"
                          >
                            clear
                          </button>
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {s.layoutDnaGuidance && (
                <p className="mt-2 text-xs text-muted">Layout guidance applies to the next generation.</p>
              )}
            </>
          )}
        </section>

        {/* Templates */}
        <section className="mb-5">
          <h2 className="mb-2 text-sm font-semibold text-text2">Templates</h2>
          {!s.code ? (
            <p className="text-xs text-muted">Generate a page to save it as a template.</p>
          ) : (
            <>
              <div className="flex gap-2">
                <input
                  value={s.templateName}
                  onChange={(e) => s.set("templateName", e.target.value)}
                  placeholder="template name"
                  className="flex-1 rounded-lg border border-border2 bg-surface px-2.5 py-2 text-sm focus:border-accent focus:outline-none"
                />
                <button
                  onClick={() => s.doSaveTemplate()}
                  className="rounded-lg border border-border2 px-3 py-2 text-sm hover:bg-bg"
                >
                  Save
                </button>
              </div>
              {s.templates.length > 0 && (
                <div className="mt-3 space-y-1.5">
                  {s.templates.map((t) => (
                    <div key={t} className="flex items-center justify-between rounded-lg border border-border2 px-2.5 py-1.5 text-xs">
                      <span className="truncate">{t}</span>
                      <button
                        onClick={() => s.doDeleteTemplate(t)}
                        className="shrink-0 rounded px-1.5 py-0.5 text-muted hover:bg-bg hover:text-red-500"
                      >
                        delete
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </section>
      </div>

      {s.error && (
        <div className="border-t border-red-200 bg-red-50 p-3 text-xs text-red-700">{s.error}</div>
      )}
    </aside>
  );
}