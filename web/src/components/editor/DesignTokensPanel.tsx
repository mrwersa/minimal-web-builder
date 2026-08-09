import type { EditorDocumentV1 } from "../../editor/document";
import {
  DESIGN_TOKEN_DEFINITIONS,
  setDesignToken,
  type DesignTokenGroup,
} from "../../editor/tokens";
import { CommitField } from "./EditorFields";

const GROUPS: readonly DesignTokenGroup[] = [
  "Color",
  "Typography",
  "Spacing",
  "Shape",
  "Layout",
];

export default function DesignTokensPanel({
  document,
  onChange,
}: {
  document: EditorDocumentV1;
  onChange: (document: EditorDocumentV1) => void;
}) {
  return (
    <details className="border-b border-border2" open>
      <summary className="cursor-pointer px-3 py-2 text-xs font-semibold text-text2">
        Global design tokens
      </summary>
      <div className="max-h-52 space-y-3 overflow-y-auto px-3 pb-3">
        <p className="text-[11px] leading-relaxed text-muted2">
          Reusable values update every element that references them.
        </p>
        {GROUPS.map((group) => (
          <fieldset key={group} className="space-y-2">
            <legend className="text-[10px] font-semibold uppercase tracking-wide text-muted2">
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
      </div>
    </details>
  );
}
