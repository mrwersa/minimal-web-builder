import { cn } from "../../lib/utils";

export function Spinner({ className, size = "md" }: { className?: string; size?: "sm" | "md" | "lg" }) {
  const sizes: Record<string, string> = {
    sm: "h-4 w-4",
    md: "h-6 w-6",
    lg: "h-10 w-10",
  };
  return (
    <div
      className={cn(
        "animate-spin rounded-full border-2 border-accentSoft border-t-accent",
        sizes[size],
        className
      )}
    />
  );
}