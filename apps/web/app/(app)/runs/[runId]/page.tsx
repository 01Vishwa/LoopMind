"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Archive, AlertTriangle } from "lucide-react";
import { Breadcrumbs } from "@/components/shared/Breadcrumbs";
import { StatusBar } from "@/components/run/StatusBar";
import { PlanTimeline } from "@/components/run/PlanTimeline";
import { CodePane } from "@/components/run/CodePane";
import { ObservationPane } from "@/components/run/ObservationPane";
import { VerdictBanner } from "@/components/run/VerdictBanner";
import { cn } from "@/lib/utils/cn";
import { BlockSkeleton, ErrorState } from "@/components/shared/DataStates";
import { useResource } from "@/lib/data/useResource";
import { getRunDetail, getStepCode, getStepOutput } from "@/lib/data/runDetail";
import type { RunPhase } from "@/lib/schemas/runSchemas";

/** How often an in-flight run re-fetches its state. */
const RUN_POLL_INTERVAL_MS = 3000;

/**
 * Hard cap on poll iterations (~10 min). Protects against a backend that never
 * reports a terminal phase — the page stops polling rather than hammering it
 * forever.
 */
const MAX_POLLS = 200;

/**
 * Phases that mean "work is actively happening". `connecting` and any unknown
 * value are treated as NOT running, so a stub that never advances past
 * `connecting` does not trigger an unbounded poll loop.
 */
const RUNNING_PHASES = new Set<RunPhase>([
  "analyzing",
  "planning",
  "coding",
  "executing",
  "verifying",
  "routing",
  "debugging",
  "finalizing",
]);

// ── Media query hook ────────────────────────────────────────────
function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);
  useEffect(() => {
    const mql = window.matchMedia(query);
    setMatches(mql.matches);
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, [query]);
  return matches;
}

// ── Live elapsed timer hook ─────────────────────────────────────
function useElapsedTimer(serverElapsedMs: number, running: boolean) {
  const [elapsed, setElapsed] = useState(serverElapsedMs);

  // Resync to the server figure on every poll so local ticking cannot drift.
  useEffect(() => {
    setElapsed(serverElapsedMs);
  }, [serverElapsedMs]);

  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => setElapsed((e) => e + 100), 100);
    return () => clearInterval(id);
  }, [running]);

  return elapsed;
}

// ── Resizable pane hook ─────────────────────────────────────────
const LEFT_MIN = 200;
const LEFT_MAX = 400;
const CODE_MIN = 300;
const CODE_MAX = 800;

function usePaneSizes() {
  const [leftWidth, setLeftWidth] = useState(280);
  const [codeWidth, setCodeWidth] = useState(480);
  const draggingLeft = useRef(false);
  const draggingRight = useRef(false);
  const startX = useRef(0);
  const startWidth = useRef(0);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const storedLeft = localStorage.getItem("vera-pane-left");
    if (storedLeft) setLeftWidth(Number(storedLeft));
    const storedCode = localStorage.getItem("vera-pane-code");
    if (storedCode) setCodeWidth(Number(storedCode));
  }, []);

  const onMouseMoveLeft = useCallback((e: MouseEvent) => {
    if (draggingLeft.current) {
      const delta = e.clientX - startX.current;
      const next = Math.max(LEFT_MIN, Math.min(LEFT_MAX, startWidth.current + delta));
      setLeftWidth(next);
      localStorage.setItem("vera-pane-left", String(next));
    }
    if (draggingRight.current) {
      const delta = e.clientX - startX.current;
      const next = Math.max(CODE_MIN, Math.min(CODE_MAX, startWidth.current + delta));
      setCodeWidth(next);
      localStorage.setItem("vera-pane-code", String(next));
    }
  }, []);

  const onMouseUp = useCallback(() => {
    draggingLeft.current = false;
    draggingRight.current = false;
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  }, []);

  useEffect(() => {
    window.addEventListener("mousemove", onMouseMoveLeft);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMoveLeft);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [onMouseMoveLeft, onMouseUp]);

  const startDragLeft = (e: React.MouseEvent) => {
    draggingLeft.current = true;
    startX.current = e.clientX;
    startWidth.current = leftWidth;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  };

  const startDragRight = (e: React.MouseEvent) => {
    draggingRight.current = true;
    startX.current = e.clientX;
    startWidth.current = codeWidth;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  };

  // Keyboard resize per spec §11.1: divider is a role="separator", arrow keys
  // resize it by 8px per press.
  const onKeyDownLeft = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      const next = Math.max(LEFT_MIN, Math.min(LEFT_MAX, leftWidth - 8));
      setLeftWidth(next);
      localStorage.setItem("vera-pane-left", String(next));
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      const next = Math.max(LEFT_MIN, Math.min(LEFT_MAX, leftWidth + 8));
      setLeftWidth(next);
      localStorage.setItem("vera-pane-left", String(next));
    }
  };

  const onKeyDownRight = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      const next = Math.max(CODE_MIN, Math.min(CODE_MAX, codeWidth - 8));
      setCodeWidth(next);
      localStorage.setItem("vera-pane-code", String(next));
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      const next = Math.max(CODE_MIN, Math.min(CODE_MAX, codeWidth + 8));
      setCodeWidth(next);
      localStorage.setItem("vera-pane-code", String(next));
    }
  };

  return { leftWidth, codeWidth, startDragLeft, startDragRight, onKeyDownLeft, onKeyDownRight, containerRef };
}

// ── Main page ────────────────────────────────────────────────────
export default function RunViewPage() {
  const params = useParams();
  const runId = params.runId as string;

  const isDesktop = useMediaQuery("(min-width: 768px)");

  // Bumped by the poll below to re-run the fetch while the run is in flight.
  const [pollTick, setPollTick] = useState(0);
  const [pollCount, setPollCount] = useState(0);
  const { data: run, status: loadStatus, error, retry } = useResource(
    () => getRunDetail(runId),
    [runId, pollTick],
    // Polling must not flash a skeleton over live content, and a dropped poll
    // must not blank the page.
    { keepPreviousData: true },
  );

  const [selectedStep, setSelectedStep] = useState<number | null>(null);
  const [diffMode, setDiffMode] = useState(false);
  const [cancelConfirming, setCancelConfirming] = useState(false);
  const [showVerdict, setShowVerdict] = useState(true);
  const [activeTab, setActiveTab] = useState<"plan" | "code" | "output">("plan");

  const {
    leftWidth,
    codeWidth,
    startDragLeft,
    startDragRight,
    onKeyDownLeft,
    onKeyDownRight,
    containerRef,
  } = usePaneSizes();

  const isRunning = run ? RUNNING_PHASES.has(run.status.phase) : false;
  const elapsedMs = useElapsedTimer(run?.status.elapsedMs ?? 0, isRunning);

  // Poll while the run is in flight. Stops on a terminal/unknown phase, and
  // hard-stops after MAX_POLLS so a never-advancing backend cannot loop forever.
  useEffect(() => {
    if (!isRunning || pollCount >= MAX_POLLS) return;
    const interval = setInterval(() => {
      setPollTick((t) => t + 1);
      setPollCount((c) => c + 1);
    }, RUN_POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [isRunning, pollCount]);

  // Code for whichever step is selected, else the active step.
  const activeStepIndex =
    selectedStep ?? run?.steps.find((s) => s.status === "active")?.index ?? 0;
  const runLoaded = run !== undefined;
  const hasSteps = (run?.steps.length ?? 0) > 0;

  const { data: stepCode } = useResource(
    () => (runLoaded && hasSteps ? getStepCode(runId, activeStepIndex) : Promise.resolve(null)),
    [runId, activeStepIndex, runLoaded, hasSteps],
    { keepPreviousData: true },
  );

  const { data: stepOutput } = useResource(
    () => (runLoaded && hasSteps ? getStepOutput(runId, activeStepIndex) : Promise.resolve(null)),
    [runId, activeStepIndex, runLoaded, hasSteps],
    { keepPreviousData: true },
  );

  const stepLabel = `Step ${activeStepIndex + 1}`;
  const verdict = showVerdict ? (run?.verdict ?? null) : null;
  const verification = run?.verification ?? null;
  const isPreExecutionValidationFailure =
    verification?.status === "rejected" && verification.preExecution;

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "D") {
        e.preventDefault();
        setDiffMode((v) => !v);
      }
      if (e.key === "Escape") setSelectedStep(null);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  if (loadStatus === "loading") {
    return <BlockSkeleton className="p-6" lines={6} />;
  }
  // A failed poll keeps the last good state on screen; only a load with nothing
  // to show falls back to the error state.
  if (!run) {
    return <ErrorState error={error} onRetry={retry} />;
  }

  // Each pane is built once and placed into whichever layout the viewport picks.
  const planPane = (
    <PlanTimeline
      steps={run.steps}
      activeIndex={selectedStep}
      backtracks={run.backtracks}
      onStepClick={(idx) => setSelectedStep(idx === selectedStep ? null : idx)}
      currentPhase={run.status.phase}
      historicalCode={
        stepCode?.previousSource
          ? { [activeStepIndex]: { old: stepCode.previousSource, new: stepCode.source } }
          : undefined
      }
      roundLogs={run.roundLogs}
    />
  );

  const codePane = (
    <CodePane
      code={stepCode?.source ?? ""}
      stepLabel={stepLabel}
      diffFrom={stepCode?.previousSource}
      diffMode={diffMode}
      onToggleDiff={() => setDiffMode((v) => !v)}
      status="executing"
    />
  );

  const preExecutionBanner = isPreExecutionValidationFailure ? (
    <div className="flex items-start gap-2.5 px-4 py-3 border-l-4 border-vera-backtrack bg-vera-backtrack-muted shrink-0 animate-fade-in">
      <AlertTriangle className="text-vera-backtrack mt-0.5 shrink-0" size={16} aria-hidden />
      <div className="text-label leading-relaxed">
        <p className="text-vera-ink font-medium">{verification?.headline}</p>
        <p className="text-vera-muted">{verification?.detail}</p>
      </div>
    </div>
  ) : null;

  const observationPane = (
    <>
      {preExecutionBanner}
      <ObservationPane
        output={stepOutput?.raw ?? ""}
        stepLabel={stepLabel}
        streaming={
          !isPreExecutionValidationFailure &&
          run.status.phase === "executing" &&
          selectedStep === null
        }
      />
    </>
  );

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Breadcrumbs + header */}
      <div className="px-5 pt-3 pb-0 shrink-0">
        <Breadcrumbs
          segments={[
            { label: "Workspaces", href: "/workspaces" },
            { label: run.workspaceName, href: `/workspaces/${run.workspaceId}` },
            { label: "Runs", href: "/runs" },
            { label: run.runId },
          ]}
        />
      </div>

      {/* Status bar */}
      <StatusBar
        phase={run.status.phase}
        round={run.status.round}
        maxRounds={run.status.maxRounds}
        elapsedMs={elapsedMs}
        costUsd={run.status.costUsd}
        costLimitUsd={run.status.costLimitUsd}
        cancelConfirming={cancelConfirming}
        onCancel={() => setCancelConfirming(true)}
        onCancelConfirm={() => setCancelConfirming(false)}
        onCancelDeny={() => setCancelConfirming(false)}
      />

      {/* Mobile tabs */}
      {!isDesktop && (
        <div className="flex border-b border-vera-border bg-vera-surface shrink-0">
          {(["plan", "code", "output"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                "flex-1 py-2 text-label font-medium capitalize transition-colors",
                activeTab === tab
                  ? "text-vera-accent border-b-2 border-vera-accent"
                  : "text-vera-muted hover:text-vera-ink",
              )}
            >
              {tab}
            </button>
          ))}
        </div>
      )}

      {/* Pane layout — desktop three-pane, mobile single-pane tabs. Only one
          set of panes is mounted at a time. */}
      <div ref={containerRef} className="flex flex-1 overflow-hidden">
        {isDesktop ? (
          <>
            <div
              id="run-plan-pane"
              className="border-r border-vera-border bg-vera-surface flex flex-col overflow-hidden"
              style={{ width: leftWidth, minWidth: LEFT_MIN, maxWidth: LEFT_MAX, flexShrink: 0 }}
              aria-label="Plan timeline"
            >
              {planPane}
            </div>

            <div
              className="w-1 bg-vera-border hover:bg-vera-accent cursor-col-resize shrink-0 transition-colors"
              onMouseDown={startDragLeft}
              onKeyDown={onKeyDownLeft}
              role="separator"
              aria-orientation="vertical"
              aria-label="Resize plan pane"
              aria-controls="run-plan-pane"
              aria-valuenow={leftWidth}
              aria-valuemin={LEFT_MIN}
              aria-valuemax={LEFT_MAX}
              tabIndex={0}
            />

            <div
              id="run-code-pane"
              className="flex flex-col overflow-hidden border-r border-vera-border"
              style={{ width: codeWidth, minWidth: CODE_MIN, maxWidth: CODE_MAX, flexShrink: 0 }}
            >
              {codePane}
            </div>

            <div
              className="w-1 bg-vera-border hover:bg-vera-accent cursor-col-resize shrink-0 transition-colors"
              onMouseDown={startDragRight}
              onKeyDown={onKeyDownRight}
              role="separator"
              aria-orientation="vertical"
              aria-label="Resize code pane"
              aria-controls="run-code-pane"
              aria-valuenow={codeWidth}
              aria-valuemin={CODE_MIN}
              aria-valuemax={CODE_MAX}
              tabIndex={0}
            />

            <div className="flex-1 flex flex-col overflow-hidden">{observationPane}</div>
          </>
        ) : (
          <>
            <div
              className={cn(
                "flex-1 flex-col overflow-hidden",
                activeTab === "plan" ? "flex" : "hidden",
              )}
            >
              {planPane}
            </div>
            <div
              className={cn(
                "flex-1 flex-col overflow-hidden",
                activeTab === "code" ? "flex" : "hidden",
              )}
            >
              {codePane}
            </div>
            <div
              className={cn(
                "flex-1 flex-col overflow-hidden",
                activeTab === "output" ? "flex" : "hidden",
              )}
            >
              {observationPane}
            </div>
          </>
        )}
      </div>

      {/* Verdict footer (if post-execution failure) */}
      {!isPreExecutionValidationFailure && (
        <VerdictBanner
          verdict={verdict}
          routerAction="backtrack"
          backtrackEvent={run.backtracks[0]}
        />
      )}

      {/* Completion actions (shown when run is done) */}
      {run.status.phase === "complete" && (
        <div className="flex items-center gap-3 px-5 py-3 border-t border-vera-border bg-vera-surface shrink-0">
          <Link
            href={`/runs/${runId}/provenance`}
            className="px-4 py-2 text-label font-medium text-vera-ink border border-vera-border rounded hover:bg-vera-border-subtle transition-colors no-underline"
            style={{ borderRadius: "6px" }}
          >
            <span className="flex items-center gap-2">
              <Archive size={14} strokeWidth={1.5} />
              View provenance
            </span>
          </Link>
          <Link
            href="/runs/new"
            className="px-4 py-2 text-label font-medium text-white bg-vera-accent rounded hover:bg-vera-accent-hover transition-colors no-underline"
            style={{ borderRadius: "6px" }}
          >
            Ask another question
          </Link>
        </div>
      )}
    </div>
  );
}
