import type { EditorDocumentV1 } from "../../editor/document";
import {
  DESIGN_TOKEN_DEFINITIONS,
  setDesignToken,
  type DesignTokenGroup,
} from "../../editor/tokens";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "../ui/accordion";
import { CommitField } from "./EditorFields";

const GROUPS: readonly DesignTokenGroup[] = [
  "Color",
  "Typography",
  "Spacing",
  "Shape",
  "Layout",
];

/**
 * Document-wide tokens. Collapsed by default: they apply to the whole page, so
 * they should not crowd out the per-element controls that are edited far more
 * often. Previously this sat open above the inspector with its own scrollbar,
 * which clipped its own content.
 */
export default function DesignTokensPanel({
  document,
  onChange,
}: {
  document: EditorDocumentV1;
  onChange: (document: EditorDocumentV1) => void;
}) {
  return (
    <Accordion type="multiple" className="border-b">
      <AccordionItem value="tokens">
        <AccordionTrigger>Global design tokens</AccordionTrigger>
        <AccordionContent>
          <p className="text-xs leading-relaxed text-muted-foreground">
            Reusable values update every element that references them.
          </p>
          {GROUPS.map((group) => (
            <fieldset key={group} className="space-y-2">
              <legend className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                {group}
              </legend>
              {DESIGN_TOKEN_DEFINITIONS.filter((token) => token.group === group).map(
                (token) => (
                  <CommitField
                    key={token.name}
                    label={token.label}
                    value={document.designTokens?.[token.name] ?? ""}
                    placeholder={token.placeholder}
                    onCommit={(value) =>
                      onChange(setDesignToken(document, token.name, value))
                    }
                  />
                ),
              )}
            </fieldset>
          ))}
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
