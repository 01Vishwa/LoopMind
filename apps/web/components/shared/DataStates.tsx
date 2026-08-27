"use client";

import { RefreshCw } from "lucide-react";
import { STRINGS } from "@/lib/config/strings";
import { cn } from "@/lib/utils/cn";

/** Shimmer rows sized to a table body. Matches existing skeleton treatment. */
export function TableSkeleton({ rows = 4, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <tbody aria-busy="true">
      {Array.from({ length: rows }).map((_, r) => (
        <tr key={r} className="border-b border-vera-border-subtle">
          {Array.from({ length: cols }).map((_, c) => (
            <td key={c} className="px-4 py-3">
              <div
                className="h-3 rounded bg-vera-border-subtle shimmer"
                style={{ width: c === 0 ? "70%" : "45%" }}
              />
            </td>
          ))}
        </tr>
      ))}
    </tbody>
  );
}

/** Generic block skeleton for non-table regions. */
export function BlockSkeleton({ className, lines = 3 }: { className?: string; lines?: number }) {
  return (
    <div className={cn("space-y-2", className)} aria-busy="true">
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="h-4 rounded bg-vera-border-subtle shimmer"
          style={{ width: `${90 - i * 12}%` }}
        />
      ))}
    </div>
  );
}

export function ErrorState({
  error,
  onRetry,
  className,
}: {
  error?: Error;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center justify-center py-12 px-6 text-center", className)}>
      <p className="text-body text-vera-ink font-medium mb-1">{STRINGS.common.loadingError}</p>
      {error?.message && (
        <p className="text-label text-vera-muted mb-4 max-w-md break-words">{error.message}</p>
      )}
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-label font-medium text-vera-ink border border-vera-border rounded hover:bg-vera-border-subtle transition-colors"
          style={{ borderRadius: "6px" }}
        >
          <RefreshCw size={14} strokeWidth={1.5} />
          {STRINGS.common.retry}
        </button>
      )}
    </div>
  );
}
