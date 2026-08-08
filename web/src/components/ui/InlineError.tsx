import { AlertCircle } from "lucide-react";

export function InlineError({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div role="alert" className="rounded-lg border border-danger/30 bg-red-50 p-2 text-xs">
      <div className="flex items-start gap-1.5 text-danger">
        <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        <span className="min-w-0 break-words">{message}</span>
      </div>
      <button
        onClick={onRetry}
        className="mt-1.5 font-medium text-danger underline-offset-2 hover:underline"
      >
        Try again
      </button>
    </div>
  );
}
