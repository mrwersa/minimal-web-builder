import { useEffect } from "react";
import { FolderOpen, Save, Trash2 } from "lucide-react";
import { useStore } from "../store";
import { cn } from "../lib/utils";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "./ui/accordion";
import { Button } from "./ui/button";
import { Field, InlineError } from "./ui/field";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Select } from "./ui/select";
import { Spinner } from "./ui/spinner";
import { Switch } from "./ui/switch";

/** Generation setup: profile, constraints, section refinement, saved assets. */
export default function SetupPanel() {
  const s = useStore();
  const opts = s.options;

  useEffect(() => {
    if (s.code) s.refreshSections();
  }, [s.code]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    s.refreshTemplates();
    s.refreshDnas();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (!opts) {
    return (
      <div className="flex h-full items-center justify-center p-4">
        {s.optionsError ? (
          <InlineError message={s.optionsError} onRetry={() => s.loadOptions()} />
        ) : (
          <Spinner />
        )}
      </div>
    );
  }

  const profileActive = s.profile !== opts.custom_profile_id;

  return (
    <Accordion
      type="multiple"
      defaultValue={["generation", "refine"]}
      className="w-full"
    >
      <AccordionItem value="generation">
        <AccordionTrigger>Generation</AccordionTrigger>
        <AccordionContent>
          <Field label="Profile">
            <Select
              aria-label="Profile"
              value={s.profile}
              options={opts.profiles.map((p) => ({ value: p.id, label: p.label }))}
              onChange={(v) => s.set("profile", v)}
            />
          </Field>
          <p className="text-xs text-muted-foreground">
            {profileActive
              ? opts.profiles.find((p) => p.id === s.profile)?.description
              : "Set tone, complexity, and strict mode manually."}
          </p>

          <div className="grid grid-cols-2 gap-2">
            <Field label="Tone">
              <Select
                aria-label="Tone"
                value={s.tone}
                options={opts.tones.map((t) => ({ value: t.key, label: t.label }))}
                onChange={(v) => s.set("tone", v)}
                disabled={profileActive}
              />
            </Field>
            <Field label="Complexity">
              <Select
                aria-label="Complexity"
                value={s.complexity}
                options={opts.complexities.map((c) => ({
                  value: c.key,
                  label: c.label,
                }))}
                onChange={(v) => s.set("complexity", v)}
                disabled={profileActive}
              />
            </Field>
          </div>

          <div className="flex items-center justify-between gap-2">
            <Label htmlFor="strict-minimal" className="cursor-pointer">
              Strict minimal mode
            </Label>
            <Switch
              id="strict-minimal"
              checked={s.strictMinimal}
              onCheckedChange={(v) => s.set("strictMinimal", v)}
              disabled={profileActive}
            />
          </div>

          <div className="flex items-center justify-between gap-2">
            <Label htmlFor="constraint-mode" className="cursor-pointer">
              Generate from constraints
            </Label>
            <Switch
              id="constraint-mode"
              checked={s.constraintMode}
              onCheckedChange={(v) => s.set("constraintMode", v)}
            />
          </div>

          {s.constraintMode && (
            <div className="space-y-3 rounded-md border bg-muted/40 p-2.5">
              <Field label="Sections">
                <div className="flex flex-wrap gap-1.5">
                  {opts.sections.map((sec) => {
                    const on = s.constraintSections.includes(sec.key);
                    return (
                      <button
                        key={sec.key}
                        type="button"
                        aria-pressed={on}
                        onClick={() =>
                          s.set(
                            "constraintSections",
                            on
                              ? s.constraintSections.filter((x) => x !== sec.key)
                              : [...s.constraintSections, sec.key],
                          )
                        }
                        className={cn(
                          "rounded-full border px-2.5 py-1 text-xs transition-colors",
                          on
                            ? "border-primary bg-primary/10 text-primary"
                            : "border-border text-muted-foreground hover:border-muted-foreground",
                        )}
                      >
                        {sec.label}
                      </button>
                    );
                  })}
                </div>
              </Field>
              <div className="grid grid-cols-2 gap-2">
                <Field label="Color limit">
                  <Select
                    aria-label="Color limit"
                    value={s.constraintColor}
                    options={opts.color_limits.map((c) => ({
                      value: c.key,
                      label: c.label,
                    }))}
                    onChange={(v) => s.set("constraintColor", v)}
                  />
                </Field>
                <Field label="Density">
                  <Select
                    aria-label="Density"
                    value={s.constraintDensity}
                    options={opts.complexities.map((c) => ({
                      value: c.key,
                      label: c.label,
                    }))}
                    onChange={(v) => s.set("constraintDensity", v)}
                  />
                </Field>
              </div>
              <Button
                size="sm"
                className="w-full"
                disabled={s.busy}
                onClick={() => s.runConstraints()}
              >
                Generate from constraints
              </Button>
            </div>
          )}
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="refine">
        <AccordionTrigger>Refine section</AccordionTrigger>
        <AccordionContent>
          {!s.code ? (
            <p className="text-xs text-muted-foreground">
              Generate a page first to refine it.
            </p>
          ) : (
            <>
              <InlineError
                message={s.sectionsError}
                onRetry={() => s.refreshSections()}
              />
              <Field label="Section">
                <Select
                  aria-label="Section"
                  value={String(s.sectionIndex)}
                  options={s.sections.map((sec, i) => ({
                    value: String(i),
                    label: `${i + 1}. <${sec.tag}>${sec.snippet ? " — " + sec.snippet : ""}`,
                  }))}
                  onChange={(v) => s.set("sectionIndex", Number(v))}
                />
              </Field>
              <Field label="Refine focus">
                <Select
                  aria-label="Refine focus"
                  value={s.refineAspect}
                  options={opts.refine_aspects.map((a) => ({
                    value: a.key,
                    label: a.label,
                  }))}
                  onChange={(v) => s.set("refineAspect", v)}
                />
              </Field>
              <Button
                size="sm"
                variant="secondary"
                className="w-full"
                disabled={s.busy || s.sections.length === 0}
                onClick={() => s.runRegenerate("")}
              >
                Regenerate section
              </Button>
            </>
          )}
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="dna">
        <AccordionTrigger>Layout DNA</AccordionTrigger>
        <AccordionContent>
          {!s.code ? (
            <p className="text-xs text-muted-foreground">
              Generate a page to inspect its layout DNA.
            </p>
          ) : (
            <>
              <InlineError message={s.dnasError} onRetry={() => s.refreshDnas()} />
              <Button
                size="sm"
                variant="outline"
                className="w-full"
                onClick={() => s.doSaveDna()}
              >
                <Save /> Save current layout
              </Button>
              {s.dnas.map((d) => (
                <div
                  key={d.name}
                  className={cn(
                    "flex items-center justify-between gap-2 rounded-md border px-2.5 py-1.5 text-xs",
                    s.layoutDnaGuidance === d.guidance && "border-primary bg-primary/5",
                  )}
                >
                  <span className="truncate text-muted-foreground">
                    {d.name}: {d.signature}
                  </span>
                  <span className="flex shrink-0 gap-1">
                    <button
                      type="button"
                      onClick={() => s.set("layoutDnaGuidance", d.guidance)}
                      className="rounded px-1.5 py-0.5 font-medium text-primary hover:bg-primary/10"
                    >
                      use
                    </button>
                    <button
                      type="button"
                      onClick={() => s.set("layoutDnaGuidance", "")}
                      className="rounded px-1.5 py-0.5 text-muted-foreground hover:bg-muted"
                    >
                      clear
                    </button>
                  </span>
                </div>
              ))}
              {s.layoutDnaGuidance && (
                <p className="text-xs text-muted-foreground">
                  Applies to the next generation.
                </p>
              )}
            </>
          )}
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="templates">
        <AccordionTrigger>Templates</AccordionTrigger>
        <AccordionContent>
          {!s.code ? (
            <p className="text-xs text-muted-foreground">
              Generate a page to save it as a template.
            </p>
          ) : (
            <>
              <InlineError
                message={s.templatesError}
                onRetry={() => s.refreshTemplates()}
              />
              <div className="flex gap-2">
                <Input
                  aria-label="Template name"
                  value={s.templateName}
                  onChange={(e) => s.set("templateName", e.target.value)}
                  placeholder="template name"
                />
                <Button size="sm" variant="outline" onClick={() => s.doSaveTemplate()}>
                  Save
                </Button>
              </div>
              {s.templates.map((t) => (
                <div
                  key={t}
                  className="flex items-center justify-between gap-2 rounded-md border px-2.5 py-1.5 text-xs"
                >
                  <span className="truncate text-muted-foreground">{t}</span>
                  <span className="flex shrink-0 gap-1">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      title={`Use ${t}`}
                      aria-label={`Use ${t}`}
                      onClick={() => s.doLoadTemplate(t)}
                    >
                      <FolderOpen />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      title={`Delete ${t}`}
                      aria-label={`Delete ${t}`}
                      onClick={() => s.doDeleteTemplate(t)}
                    >
                      <Trash2 />
                    </Button>
                  </span>
                </div>
              ))}
            </>
          )}
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
