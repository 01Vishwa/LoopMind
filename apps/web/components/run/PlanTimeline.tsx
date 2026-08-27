"use client";

import { useState, useCallback, useRef } from "react";
import { Check, ChevronDown, ChevronRight, RotateCcw, Circle, X, CheckCircle2, Clock, DollarSign } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import type { PlanStep, BacktrackEvent } from "@/lib/schemas/runSchemas";
import { CodePane } from "./CodePane";
import { formatCost } from "@/lib/utils/formatCost";

export interface TimelineLogEntry {
  round: number;
  verdict: "accepted" | "rejected";
  rationale?: string;
  costDelta: number;
  timeDeltaStr: string;
}

export interface PlanTimelineProps {
  steps: PlanStep[];
  activeIndex: number | null;
  backtracks: BacktrackEvent[];
  onStepClick: (index: number) => void;
  fileAnalysis?: { file: string; done: number; total: number } | null;
  currentPhase?: string;
  /** Previous vs. current source per step index, for the diff viewer. */
  historicalCode?: Record<number, { old: string, new: string }>;
  roundLogs?: TimelineLogEntry[];
}

type PlanTimelineView = "plan" | "round";

export function PlanTimeline({
  steps,
  activeIndex,
  backtracks,
  onStepClick,
  fileAnalysis,
  currentPhase,
  historicalCode,
  roundLogs = [],
}: PlanTimelineProps) {
  const [view, setView] = useState<PlanTimelineView>("plan");
  const [expandedBacktracks, setExpandedBacktracks] = useState<Set<number>>(new Set());
  const listRef = useRef<HTMLDivElement>(null);

  const toggleBacktrack = (fromIndex: number) => {
    setExpandedBacktracks((prev) => {
      const next = new Set(prev);
      if (next.has(fromIndex)) next.delete(fromIndex);
      else next.add(fromIndex);
      return next;
    });
  };

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent, index: number) => {
      const completedSteps = steps.filter((s) => s.status === "completed" || s.status === "active");
      const current = completedSteps.findIndex((s) => s.index === index);

      if (e.key === "ArrowDown" && current < completedSteps.length - 1) {
        e.preventDefault();
        const nextStep = completedSteps[current + 1];
        if (nextStep) onStepClick(nextStep.index);
      } else if (e.key === "ArrowUp" && current > 0) {
        e.preventDefault();
        const prevStep = completedSteps[current - 1];
        if (prevStep) onStepClick(prevStep.index);
      } else if (e.key === "Enter") {
        e.preventDefault();
        onStepClick(index);
      }
    },
    [steps, onStepClick]
  );

  const backtracksBeforeStep = (stepIndex: number) =>
    backtracks.filter((b) => b.toIndex === stepIndex - 1);

  const showAnalysis = fileAnalysis && currentPhase === "analyzing";

  return (
    <div
      role="region"
      aria-label="Plan timeline"
      className="h-full overflow-y-auto px-3 py-3"
    >
      <div className="mb-3 px-1" role="tablist" aria-label="Plan timeline view">
        <div className="inline-flex items-center gap-0.5 p-0.5 rounded bg-vera-border-subtle">
          {(["plan", "round"] as const).map((v) => (
            <button
              key={v}
              role="tab"
              aria-selected={view === v}
              onClick={() => setView(v)}
              className={cn(
                "px-2.5 py-1 text-[11px] font-medium rounded transition-colors capitalize",
                view === v
                  ? "bg-vera-surface text-vera-ink shadow-sm"
                  : "text-vera-muted hover:text-vera-ink"
              )}
            >
              {v === "plan" ? "Plan view" : "Round view"}
            </button>
          ))}
        </div>
      </div>

      {view === "round" ? (
        <RoundView logs={roundLogs} />
      ) : (
        <>
      {/* Pre-loop: File Analysis */}
      {(showAnalysis || fileAnalysis) && (
        <div className="mb-4">
          <div className="px-1 mb-2">
            <span className="text-label text-vera-muted font-medium" style={{ fontSize: "11px" }}>
              ─── File Analysis ───
            </span>
          </div>
          {fileAnalysis && (
            <div className="space-y-1 px-2">
              <FileAnalysisRow
                name={fileAnalysis.file}
                status={currentPhase === "analyzing" ? "analyzing" : "done"}
              />
            </div>
          )}
        </div>
      )}

      {/* Plan steps */}
      <div
        ref={listRef}
        role="listbox"
        aria-label="Plan steps"
        className="space-y-1"
      >
        {steps.map((step) => {
          const isActive = step.status === "active";
          const isCompleted = step.status === "completed";
          const isBacktracked = step.status === "backtracked";
          const isSelected = activeIndex === step.index;
          const backtrackForThisStep = backtracks.find((b) => b.fromIndex === step.index);

          return (
            <div key={step.index}>
              {/* Backtracked step */}
              {isBacktracked && (
                <BacktrackedStep
                  step={step}
                  backtrack={backtrackForThisStep}
                  expanded={expandedBacktracks.has(step.index)}
                  onToggle={() => toggleBacktrack(step.index)}
                  diffCode={historicalCode?.[step.index]}
                />
              )}

              {/* Backtrack connector — attached directly under the step it backtracked from */}
              {backtracksBeforeStep(step.index).map((bt) => (
                <BacktrackDividerInline key={bt.fromIndex} toIndex={bt.toIndex} />
              ))}

              {/* Active step */}
              {isActive && (
                <div
                  role="option"
                  aria-selected={isSelected}
                  className="flex items-start gap-3 px-3 py-2.5 rounded border-l-2 border-vera-accent bg-vera-accent-muted"
                  style={{ borderRadius: "0 4px 4px 0" }}
                >
                  <div className="w-5 h-5 rounded-full border-2 border-vera-accent flex items-center justify-center shrink-0 mt-0.5">
                    <span className="w-2 h-2 rounded-full bg-vera-accent step-pulse" aria-hidden />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-label text-vera-muted">Step {step.index + 1}</span>
                    </div>
                    <p className="text-label font-medium text-vera-ink mt-0.5 leading-relaxed line-clamp-2" title={step.text}>{step.text}</p>
                    
                    {/* Pre-execution Checklist */}
                    {step.criteria && step.criteria.length > 0 && (
                      <div className="mt-3 space-y-1.5 border-t border-vera-accent/20 pt-2">
                        <span className="text-[10px] font-medium text-vera-accent uppercase tracking-wider">Acceptance Criteria</span>
                        {step.criteria.map((crit, i) => (
                          <div key={i} className="flex items-start gap-1.5 text-label text-vera-muted">
                            <Circle size={10} strokeWidth={2} className="shrink-0 mt-1" aria-hidden />
                            <span className="font-normal">{crit}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Completed step */}
              {isCompleted && (
                <button
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => onStepClick(step.index)}
                  onKeyDown={(e) => handleKeyDown(e, step.index)}
                  tabIndex={0}
                  className={cn(
                    "w-full flex items-start gap-3 px-3 py-2.5 rounded border-l-2 text-left transition-colors",
                    isSelected
                      ? "border-vera-accent bg-vera-accent-muted"
                      : "border-vera-verified hover:bg-vera-border-subtle"
                  )}
                  style={{ borderRadius: "0 4px 4px 0" }}
                >
                  <div className="w-5 h-5 rounded-full bg-vera-verified flex items-center justify-center shrink-0 mt-0.5">
                    <Check size={11} strokeWidth={2.5} className="text-white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="text-label text-vera-muted">Step {step.index + 1}</span>
                    <p className="text-label text-vera-ink mt-0.5 leading-relaxed line-clamp-2" title={step.text}>{step.text}</p>
                    
                    {/* Met criteria checklist */}
                    {step.criteria && step.criteria.length > 0 && (
                      <div className="mt-2 space-y-1">
                        {step.criteria.map((crit, i) => (
                          <div key={i} className="flex items-start gap-1.5 text-label text-vera-verified">
                            <Check size={12} strokeWidth={2} className="shrink-0 mt-0.5" aria-hidden />
                            <span className="font-normal opacity-90">{crit}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </button>
              )}
            </div>
          );
        })}

        {/* Loading placeholder while planning */}
        {currentPhase && !["complete", "failed", "cancelled"].includes(currentPhase) && (
          <PlanningPlaceholder phase={currentPhase} />
        )}
      </div>
        </>
      )}
    </div>
  );
}

// ── Sub-components ──────────────────────────────────────────────

function RoundView({ logs }: { logs: TimelineLogEntry[] }) {
  if (logs.length === 0) {
    return <p className="text-label text-vera-muted px-1">No rounds completed yet.</p>;
  }

  return (
    <div className="relative px-1">
      {/* Timeline track */}
      <div className="absolute left-[15px] top-4 bottom-4 w-px bg-vera-border" />

      <div className="space-y-6">
        {logs.map((log) => {
          const isAccepted = log.verdict === "accepted";

          return (
            <div key={log.round} className="relative flex gap-4">
              {/* Node */}
              <div className={cn(
                "w-[30px] h-[30px] rounded-full flex items-center justify-center shrink-0 z-10 border-2 bg-vera-surface",
                isAccepted ? "border-vera-verified text-vera-verified" : "border-vera-insufficient text-vera-insufficient"
              )}>
                {isAccepted ? <CheckCircle2 size={14} strokeWidth={2.5} /> : <RotateCcw size={14} strokeWidth={2.5} />}
              </div>

              {/* Content */}
              <div className="flex-1 pt-1.5 pb-2">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-bold text-vera-ink">Round {log.round}</span>
                  <span className={cn(
                    "text-[10px] font-bold px-1.5 py-0.5 rounded",
                    isAccepted ? "text-vera-verified bg-vera-verified-muted" : "text-vera-insufficient bg-vera-insufficient-muted"
                  )}>
                    {isAccepted ? "Sufficient" : "Insufficient"}
                  </span>
                </div>

                {log.rationale && (
                  <p className="text-label text-vera-muted mb-3 leading-relaxed">
                    {log.rationale}
                  </p>
                )}

                <div className="flex items-center gap-4 text-[11px] font-medium text-vera-subtle">
                  <span className="flex items-center gap-1.5">
                    <DollarSign size={12} strokeWidth={2} className="text-vera-accent" />
                    {formatCost(log.costDelta)}
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Clock size={12} strokeWidth={2} className="text-vera-muted" />
                    {log.timeDeltaStr}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function BacktrackedStep({
  step,
  backtrack,
  expanded,
  onToggle,
  diffCode,
}: {
  step: PlanStep;
  backtrack?: BacktrackEvent;
  expanded: boolean;
  onToggle: () => void;
  diffCode?: { old: string, new: string };
}) {
  return (
    <div className="rounded border-l-2 border-vera-backtrack bg-vera-backtrack-muted" style={{ borderRadius: "0 4px 4px 0" }}>
      <button
        onClick={onToggle}
        aria-expanded={expanded}
        className="w-full flex items-center gap-2 px-3 py-2 text-left"
      >
        {expanded ? (
          <ChevronDown size={14} strokeWidth={2} className="text-vera-backtrack shrink-0" />
        ) : (
          <ChevronRight size={14} strokeWidth={2} className="text-vera-backtrack shrink-0" />
        )}
        <span className="text-label text-vera-muted line-through" style={{ opacity: 0.6 }}>
          Step {step.index + 1} — {step.text.slice(0, 40)}{step.text.length > 40 ? "…" : ""}
        </span>
        <span
          className="ml-auto text-label font-medium border border-vera-warning/30 px-1.5 py-0.5 shrink-0"
          style={{
            borderRadius: "2px",
            fontSize: "10px",
            backgroundColor: "var(--vera-warning-muted)",
            color: "var(--vera-warning)",
          }}
        >
          Backtracked
        </span>
      </button>

      {expanded && backtrack && (
        <div className="px-3 pb-4 space-y-3">
          {/* Failed Step Intent & Checklist */}
          <div>
            <p className="text-label text-vera-muted line-through mb-2" style={{ opacity: 0.6 }}>{step.text}</p>
            {step.criteria && step.criteria.length > 0 && (
              <div className="space-y-1">
                {step.criteria.map((crit, i) => {
                  // The verifier reports which criteria it rejected.
                  const failed = backtrack.failedCriteria?.includes(crit) ?? false;
                  return (
                    <div key={i} className={cn("flex items-start gap-1.5 text-label", failed ? "text-vera-insufficient" : "text-vera-verified")}>
                      {failed ? (
                        <X size={12} strokeWidth={2} className="shrink-0 mt-0.5" aria-hidden />
                      ) : (
                        <Check size={12} strokeWidth={2} className="shrink-0 mt-0.5" aria-hidden />
                      )}
                      <span className="font-normal opacity-90">{crit}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
          
          {/* Verifier Rationale */}
          <div className="flex items-start gap-2 p-2.5 rounded border border-vera-insufficient/20 bg-vera-insufficient-muted/50">
            <RotateCcw size={12} strokeWidth={2} className="text-vera-insufficient shrink-0 mt-0.5" />
            <div>
              <span className="text-[10px] font-bold text-vera-insufficient uppercase tracking-wider block mb-0.5">Verifier Rationale</span>
              <p className="text-label text-vera-ink leading-relaxed">
                {backtrack.rationale}
              </p>
            </div>
          </div>

          {/* Inline Code Diff Pane */}
          {diffCode && (
            <div className="h-64 mt-2">
              <CodePane
                code={diffCode.new}
                diffFrom={diffCode.old}
                diffMode={true}
                status="rejected"
                stepLabel={`Step ${step.index + 1} (Rejected)`}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function BacktrackDividerInline({ toIndex }: { toIndex: number }) {
  return (
    <div className="relative flex items-center gap-1.5 pl-11 pr-1 py-1 -mt-0.5 animate-slide-in-left">
      {/* Small vertical connector linking up to the step above */}
      <span className="absolute left-[22px] top-0 bottom-1/2 w-px bg-vera-backtrack/40" aria-hidden />
      <span className="absolute left-[22px] top-1/2 w-2 h-px bg-vera-backtrack/40" aria-hidden />
      <RotateCcw size={10} strokeWidth={1.5} className="text-vera-backtrack shrink-0" />
      <span className="text-label text-vera-backtrack whitespace-nowrap shrink-0">
        Backtracked to step {toIndex + 1}
      </span>
    </div>
  );
}

function FileAnalysisRow({ name, status }: { name: string; status: "pending" | "analyzing" | "done" }) {
  return (
    <div className="flex items-center gap-2 py-1">
      {status === "done" ? (
        <Check size={12} strokeWidth={2} className="text-vera-verified shrink-0" />
      ) : status === "analyzing" ? (
        <span className="w-2 h-2 rounded-full bg-vera-accent step-pulse shrink-0" aria-hidden />
      ) : (
        <span className="w-2 h-2 rounded-full bg-vera-border shrink-0" aria-hidden />
      )}
      <span className="text-label text-vera-muted truncate">{name}</span>
    </div>
  );
}

function PlanningPlaceholder({ phase }: { phase: string }) {
  const label =
    phase === "planning" ? "Planning…"
      : phase === "coding" ? "Coding…"
      : phase === "analyzing" ? "Analyzing…"
      : phase === "verifying" ? "Verifying…"
      : "Working…";

  return (
    <div className="flex items-center gap-3 px-3 py-2.5">
      <div className="w-5 h-5 rounded-full bg-vera-border-subtle shimmer shrink-0" />
      <div className="flex-1 space-y-1.5">
        <div className="h-3 rounded bg-vera-border-subtle shimmer w-16" />
        <div className="h-3 rounded bg-vera-border-subtle shimmer w-3/4" />
      </div>
    </div>
  );
}
