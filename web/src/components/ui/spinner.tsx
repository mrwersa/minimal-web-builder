import { cn } from "../../lib/utils";

export function Spinner({
  className,
  size = "default",
}: {
  className?: string;
  size?: "sm" | "default";
}) {
  return (
    <span
      role="status"
      aria-label="Loading"
      className={cn(
        "inline-block animate-spin rounded-full border-2 border-current border-t-transparent opacity-70",
        size === "sm" ? "h-3.5 w-3.5" : "h-5 w-5",
        className,
      )}
    />
  );
}
