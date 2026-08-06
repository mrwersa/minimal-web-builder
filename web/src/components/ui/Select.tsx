import { cn } from "../../lib/utils";

export function Select({
  value,
  options,
  onChange,
  disabled,
  className,
}: {
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
  disabled?: boolean;
  className?: string;
}) {
  return (
    <select
      className={cn(
        "flex h-9 w-full cursor-pointer rounded-lg border border-border2 bg-surface px-3 text-sm text-text2 transition-colors hover:border-muted2 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accentSoft disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      value={value}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value)}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}