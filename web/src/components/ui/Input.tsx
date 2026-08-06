import * as React from "react";
import { cn } from "../../lib/utils";

const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "flex h-9 w-full rounded-lg border border-border2 bg-surface px-3 py-1 text-sm text-text2 transition-colors placeholder:text-muted2 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accentSoft disabled:opacity-50",
        className
      )}
      {...props}
    />
  )
);
Input.displayName = "Input";
export { Input };