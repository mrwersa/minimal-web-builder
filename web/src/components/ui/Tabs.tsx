import * as React from "react";
import { cn } from "../../lib/utils";

type TabsProps = React.ComponentPropsWithoutRef<"div"> & {
  value: string;
  onValueChange: (v: string) => void;
  tabs: { value: string; label: string; icon?: React.ReactNode }[];
};

export function Tabs({ value, onValueChange, tabs, className, children }: TabsProps & { children: React.ReactNode }) {
  return (
    <div className={cn("flex h-full flex-col", className)}>
      <div className="flex items-center gap-1 border-b border-border2 px-2">
        {tabs.map((t) => (
          <button
            key={t.value}
            onClick={() => onValueChange(t.value)}
            className={cn(
              "flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-medium transition-colors",
              value === t.value
                ? "border-accent text-accent"
                : "border-transparent text-muted hover:text-text2"
            )}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>
      <div className="min-h-0 flex-1 overflow-hidden">{children}</div>
    </div>
  );
}