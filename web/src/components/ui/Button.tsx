import * as React from "react";
import { cn } from "../../lib/utils";

const Button = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: "default" | "outline" | "ghost" | "secondary";
    size?: "sm" | "md" | "lg" | "icon";
  }
>(({ className, variant = "default", size = "md", ...props }, ref) => {
  const variants: Record<string, string> = {
    default: "bg-accent text-white hover:bg-accentHover shadow-sm",
    outline: "border border-border2 bg-surface hover:bg-bg text-text2",
    ghost: "hover:bg-bg text-muted hover:text-text2",
    secondary: "bg-accentSoft text-accent hover:bg-accent hover:text-white",
  };
  const sizes: Record<string, string> = {
    sm: "h-8 px-3 text-xs",
    md: "h-9 px-4 text-sm",
    lg: "h-11 px-6 text-base",
    icon: "h-9 w-9",
  };
  return (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accentSoft disabled:pointer-events-none disabled:opacity-50",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    />
  );
});
Button.displayName = "Button";
export { Button };