"use client";

import { useEffect } from "react";
import { RefreshCw } from "lucide-react";

/**
 * Route-level error boundary. Catches render/runtime errors thrown by any page
 * and offers a reset without a full reload.
 */
export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-6 text-center">
      <p
        className="text-heading text-vera-ink font-medium mb-1"
        style={{ fontFamily: "'JetBrains Mono', monospace" }}
      >
        Something broke
      </p>
      <p className="text-label text-vera-muted mb-6 max-w-md break-words">
        {error.message || "An unexpected error occurred while rendering this page."}
      </p>
      <button
        onClick={reset}
        className="inline-flex items-center gap-1.5 px-4 py-2 text-label font-medium text-vera-ink border border-vera-border rounded hover:bg-vera-border-subtle transition-colors"
        style={{ borderRadius: "6px" }}
      >
        <RefreshCw size={14} strokeWidth={1.5} />
        Try again
      </button>
    </div>
  );
}
