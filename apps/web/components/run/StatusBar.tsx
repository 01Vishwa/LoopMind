"use client";

import { useEffect, useRef, useState } from "react";
import { formatCost } from "@/lib/utils/formatCost";
import { cn } from "@/lib/utils/cn";
import type { RunPhase } from "@/lib/schemas/runSchemas";

const PHASE_LABELS: Record<RunPhase, string> = {
  connecting: "Connecting",
  analyzing: "Analyzing",
  planning: "Planning",
  coding: "Coding",
  executing: "Executing",
  verifying: "Verifying",
  routing: "Routing",
  debugging: "Debugging",
  finalizing: "Finalizing",
  complete: "Complete",
  failed: "Failed",
  cancelled: "Cancelled",
};

const PHASE_COLOR: Record<RunPhase, string> = {
  connecting: "text-vera-muted",
  analyzing: "text-vera-accent",
  planning: "text-vera-accent",
  coding: "text-vera-accent",
  executing: "text-vera-accent",
  verifying: "text-vera-accent",
  routing: "text-vera-accent",
  debugging: "text-vera-warning",
  finalizing: "text-vera-accent",
  complete: "text-vera-verified",
  failed: "text-vera-insufficient",
  cancelled: "text-vera-muted",
};

// Phase dot — collapsed to the three states called out in the spec:
// blue while active, green on completion, red on failure (grey for cancelled).
function phaseDotColor(phase: RunPhase): string {
  if (phase === "complete") return "bg-vera-verified";
  if (phase === "failed") return "bg-vera-insufficient";
  if (phase === "cancelled") return "bg-vera-muted";
  return "bg-vera-accent";
}

export interface StatusBarProps {
  phase: RunPhase;
  round: number;
  maxRounds?: number;
  elapsedMs: number;
  costUsd: number;
  costLimitUsd?: number;
  onCancel?: () => void;
  cancelConfirming?: boolean;
  onCancelConfirm?: () => void;
  onCancelDeny?: () => void;
  runId?: string;
}

export function StatusBar({
  phase,
  round,
  maxRounds = 10,
  elapsedMs,
  costUsd,
  costLimitUsd = 2.5,
  onCancel,
  cancelConfirming,
  onCancelConfirm,
  onCancelDeny,
}: StatusBarProps) {
  const isTerminal = phase === "complete" || phase === "failed" || phase === "cancelled";
  const elapsed = elapsedMs / 1000;
  const elapsedStr = elapsed < 60 ? `${elapsed.toFixed(1)}s` : `${Math.floor(elapsed / 60)}m ${Math.floor(elapsed % 60)}s`;

  // Per spec §11.2: the phase indicator announces via aria-live, debounced to
  // fire on phase change only — not on every render (elapsed/cost tick many
  // times per second and must not spam screen readers).
  const [announcedPhase, setAnnouncedPhase] = useState(phase);
  const lastPhase = useRef(phase);
  useEffect(() => {
    if (lastPhase.current !== phase) {
      lastPhase.current = phase;
      setAnnouncedPhase(phase);
    }
  }, [phase]);

  return (
    <div className="flex items-center gap-5 px-5 py-2 border-b border-vera-border bg-vera-surface text-label">
      {/* Debounced phase-only live region — see note above */}
      <span className="sr-only" role="status" aria-live="polite" aria-atomic="true">
        {PHASE_LABELS[announcedPhase]}
      </span>

      {/* Phase + round + cost + elapsed — one line, no progress bar.
          The Plan Timeline is the visual progress indicator; this is just labels. */}
      <div className="flex items-center gap-2 text-mono-ui text-vera-muted whitespace-nowrap">
        <span className={cn("w-1.5 h-1.5 rounded-full inline-block", phaseDotColor(phase), !isTerminal && "step-pulse")} aria-hidden />
        <span className={cn("font-medium uppercase tracking-wider", PHASE_COLOR[phase])} style={{ fontSize: "11px" }}>
          {PHASE_LABELS[phase]}
        </span>
        <span className="opacity-50">·</span>
        <span className="text-vera-ink">Round {Math.max(1, round)}{maxRounds > 0 ? `/${maxRounds}` : ""}</span>
        <span className="opacity-50">·</span>
        <span>{formatCost(costUsd)} / {formatCost(costLimitUsd)}</span>
        <span className="opacity-50">·</span>
        <span className="opacity-80">{elapsedStr}</span>
      </div>

      <div className="flex-1" />

      {/* Cancel */}
      {!isTerminal && onCancel && (
        <>
          {cancelConfirming ? (
            <div className="flex items-center gap-2">
              <span className="text-label text-vera-muted">Are you sure?</span>
              <button
                onClick={onCancelConfirm}
                className="text-label font-medium text-vera-insufficient hover:underline"
              >
                Yes
              </button>
              <span className="text-vera-muted">/</span>
              <button
                onClick={onCancelDeny}
                className="text-label font-medium text-vera-ink hover:underline"
              >
                No
              </button>
            </div>
          ) : (
            <button
              onClick={onCancel}
              className="text-[11px] font-medium text-vera-muted hover:text-vera-ink border border-vera-border rounded px-3 py-1.5 hover:bg-vera-border-subtle transition-colors"
            >
              Cancel run
            </button>
          )}
        </>
      )}
    </div>
  );
}
