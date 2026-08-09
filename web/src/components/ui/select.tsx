import * as React from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "../../lib/utils";

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps
  extends Omit<React.ComponentProps<"select">, "onChange" | "value"> {
  value: string;
  options: SelectOption[];
  onChange: (value: string) => void;
}

/**
 * A styled native `<select>`.
 *
 * The rest of the app uses Radix primitives, but the inspector alone renders a
 * dozen of these in a narrow column: the native control keeps keyboard and
 * mobile behaviour for free, needs no portal, and stays operable by
 * `selectOption` in tests.
 */
const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, value, options, onChange, ...props }, ref) => (
    <div className="relative">
      <select
        ref={ref}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className={cn(
          "flex h-9 w-full appearance-none rounded-md border border-input bg-surface px-3 py-1 pr-8 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
          className,
        )}
        {...props}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
    </div>
  ),
);
Select.displayName = "Select";

export { Select };
