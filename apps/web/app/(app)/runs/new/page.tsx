"use client";

import { Suspense, useState, useRef, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ChevronDown, ChevronUp, AlertTriangle } from "lucide-react";
import Link from "next/link";
import { Breadcrumbs } from "@/components/shared/Breadcrumbs";
import { ErrorState } from "@/components/shared/DataStates";
import { cn } from "@/lib/utils/cn";
import { useResource } from "@/lib/data/useResource";
import { listWorkspaces, listSuggestedQuestions, pickDefaultWorkspace } from "@/lib/data/workspaces";
import { createRun } from "@/lib/data/runs";
import { getModes, getResourceLimits } from "@/lib/data/config";
import { MODE_ICONS, DEFAULT_MODE, type RunMode } from "@/lib/config/modes";
import {
  DEFAULT_RESOURCE_LIMITS,
  estimatedCapUsd,
  typicalSpendUsd,
  isCostCeilingValid,
} from "@/lib/config/resourceLimits";
import { formatCost } from "@/lib/utils/formatCost";
import { STRINGS } from "@/lib/config/strings";

export default function NewRunPage() {
  return (
    <Suspense fallback={null}>
      <NewRunForm />
    </Suspense>
  );
}

function NewRunForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // ── Server-driven config & data ──────────────────────────────
  const {
    data: workspaces,
    status: workspacesStatus,
    error: workspacesError,
    retry: retryWorkspaces,
  } = useResource(listWorkspaces, []);
  const { data: modes, status: modesStatus, retry: retryModes } = useResource(getModes, []);
  const { data: fetchedLimits } = useResource(getResourceLimits, []);
  const limits = fetchedLimits ?? DEFAULT_RESOURCE_LIMITS;

  const [workspaceId, setWorkspaceId] = useState(searchParams.get("workspaceId") ?? "");
  const [query, setQuery] = useState("");
  const [selectedChip, setSelectedChip] = useState<string | null>(null);

  const [mode, setMode] = useState<RunMode>(DEFAULT_MODE);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [maxRounds, setMaxRounds] = useState(limits.rounds.default);
  const [maxCost, setMaxCost] = useState(limits.costCeilingUsd.default);
  const [limitsApplied, setLimitsApplied] = useState(false);

  // Adopt server defaults once the limits config resolves.
  useEffect(() => {
    if (fetchedLimits && !limitsApplied) {
      setMaxRounds(fetchedLimits.rounds.default);
      setMaxCost(fetchedLimits.costCeilingUsd.default);
      setLimitsApplied(true);
    }
  }, [fetchedLimits, limitsApplied]);

  // Auto-select the most recently used ready workspace once the list loads.
  useEffect(() => {
    if (!workspaceId && workspaces?.length) {
      const preferred = pickDefaultWorkspace(workspaces);
      if (preferred) setWorkspaceId(preferred.id);
    }
  }, [workspaces, workspaceId]);

  // Suggestions are regenerated per workspace.
  const { data: suggestions, status: suggestionsStatus } = useResource(
    () => (workspaceId ? listSuggestedQuestions(workspaceId) : Promise.resolve([])),
    [workspaceId],
  );

  const estimatedCap = estimatedCapUsd(maxRounds, limits);
  const maxCostError = !isCostCeilingValid(maxCost, limits);

  // Cost ceiling tracks the round slider until the user edits it directly.
  const [costTouched, setCostTouched] = useState(false);
  useEffect(() => {
    if (!costTouched) setMaxCost(Number(estimatedCap.toFixed(2)));
  }, [estimatedCap, costTouched]);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-grow textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 192)}px`; // max 8 lines ≈ 192px
  }, [query]);

  const handleChip = (q: string) => {
    setQuery(q);
    setSelectedChip(q);
    // Focus textarea after selection
    setTimeout(() => {
      textareaRef.current?.focus();
      // Move cursor to end
      textareaRef.current?.setSelectionRange(q.length, q.length);
    }, 0);
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setQuery(val);
    // If they manually edit away from the exact chip text, clear the selected chip state
    if (selectedChip && val !== selectedChip) {
      setSelectedChip(null);
    }
  };

  const resetToRecommended = () => {
    setMaxRounds(limits.rounds.default);
    setMaxCost(limits.costCeilingUsd.default);
    setCostTouched(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || maxCostError) return;
    setSubmitting(true);
    setError(null);
    try {
      const { runId } = await createRun({
        workspaceId,
        query: query.trim(),
        mode,
        maxRounds,
        maxCostUsd: maxCost,
      });
      router.push(`/runs/${runId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : STRINGS.common.loadingError);
    } finally {
      setSubmitting(false);
    }
  };

  const selectedWorkspace = (workspaces ?? []).find((w) => w.id === workspaceId);
  const isPartial = selectedWorkspace?.status === "partial";

  // The form is unusable without a workspace list, so surface that failure
  // instead of rendering empty selects.
  if (workspacesStatus === "error") {
    return (
      <div className="px-6 py-6 max-w-[1440px] mx-auto">
        <Breadcrumbs segments={[{ label: "Runs", href: "/runs" }, { label: "New analysis" }]} className="mb-4" />
        <ErrorState error={workspacesError} onRetry={retryWorkspaces} />
      </div>
    );
  }

  return (
    <div className="px-6 py-6 max-w-[1440px] mx-auto">
      <Breadcrumbs segments={[{ label: "Runs", href: "/runs" }, { label: "New analysis" }]} className="mb-4" />

      <div className="max-w-[640px] mx-auto">
        <h1
          className="text-display text-vera-ink mb-2"
          style={{ fontFamily: "'JetBrains Mono', monospace" }}
        >
          New analysis
        </h1>
        <p className="text-body text-vera-muted mb-8">
          Ask a question about your data. VERA will write, execute, and verify the answer.
        </p>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Workspace selector */}
          <div className="space-y-1.5">
            <label htmlFor="workspace-select" className="text-label font-medium text-vera-ink">
              Workspace
            </label>
            <select
              id="workspace-select"
              value={workspaceId}
              onChange={(e) => setWorkspaceId(e.target.value)}
              className="vera-input"
            >
              {(workspaces ?? []).map((ws) => (
                <option key={ws.id} value={ws.id}>
                  {ws.name} ({ws.status})
                </option>
              ))}
            </select>
          </div>

          {/* Partial Workspace Warning */}
          {isPartial && (
            <div className="flex items-start gap-2 p-3 bg-vera-warning-muted border border-vera-warning/30 rounded text-sm text-vera-warning font-medium">
              <AlertTriangle size={16} strokeWidth={2} className="shrink-0 mt-0.5" />
              <div>
                This workspace has files not yet fully described — results may be incomplete.{" "}
                <Link href={`/workspaces/${workspaceId}?action=resume`} className="underline hover:text-vera-ink transition-colors">
                  Resume setup
                </Link>
              </div>
            </div>
          )}

          {/* Query textarea */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-end mb-1">
              <label htmlFor="query-input" className="text-label font-medium text-vera-ink">
                Question
              </label>
            </div>
            
            <div className="relative">
              <textarea
                id="query-input"
                ref={textareaRef}
                value={query}
                onChange={handleTextareaChange}
                placeholder={STRINGS.newAnalysis.queryPlaceholder}
                rows={3}
                className="vera-input resize-none pb-8"
                style={{ minHeight: "100px" }}
              />
              {/* Live Cost/Time Estimate */}
              <div className="absolute bottom-2 right-3 text-[11px] font-medium text-vera-muted pointer-events-none">
                {query.length > 0 ? (
                  <span>
                    Estimated: {formatCost(typicalSpendUsd(maxRounds, limits))}–
                    {formatCost(estimatedCap)}
                  </span>
                ) : (
                  <span>{STRINGS.newAnalysis.emptyCharCount}</span>
                )}
              </div>
            </div>

            {!query && (
              <p className="text-label text-vera-muted mt-1.5">
                {STRINGS.newAnalysis.queryHelper}
              </p>
            )}

            {/* Example chips */}
            <div className="flex flex-wrap gap-2 mt-2">
              {suggestionsStatus === "loading"
                ? Array.from({ length: 4 }).map((_, i) => (
                    <span
                      key={i}
                      className="h-7 w-48 rounded-full bg-vera-border-subtle shimmer"
                      aria-hidden
                    />
                  ))
                : (suggestions ?? []).map(({ id, text: q }) => {
                const isSelected = selectedChip === q;
                return (
                  <button
                    key={id}
                    type="button"
                    onClick={() => handleChip(q)}
                    title={q}
                    className={cn(
                      "px-3 py-1.5 text-xs border rounded-full transition-all text-left",
                      isSelected
                        ? "border-vera-accent bg-vera-accent-glow text-vera-accent font-medium shadow-[0_0_0_1px_var(--vera-accent)]"
                        : "text-vera-muted border-vera-border hover:border-vera-accent/60 hover:text-vera-accent hover:bg-vera-accent-glow"
                    )}
                  >
                    {q.length > 50 ? q.slice(0, 47) + "…" : q}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Mode selector */}
          <div className="space-y-3">
            <p className="text-label font-medium text-vera-ink">Mode</p>
            {modesStatus === "error" && (
              <div className="flex items-center justify-between gap-3 p-3 bg-vera-warning-muted border border-vera-warning/30 rounded text-sm text-vera-warning font-medium">
                <span>Could not load run modes.</span>
                <button
                  type="button"
                  onClick={retryModes}
                  className="underline hover:text-vera-ink transition-colors"
                >
                  Retry
                </button>
              </div>
            )}
            <div className="grid grid-cols-2 gap-3">
              {(modes ?? []).map(({ value, label, description: desc }) => {
                const Icon = MODE_ICONS[value];
                return (
                <button
                  key={value}
                  type="button"
                  id={`mode-${value}`}
                  onClick={() => setMode(value)}
                  className={cn(
                    "flex flex-col items-start gap-2 p-4 text-left transition-all",
                    mode === value
                      ? "vera-card border-vera-accent bg-vera-accent-glow shadow-[0_0_0_1px_var(--vera-accent)]"
                      : "vera-card-hover text-vera-muted"
                  )}
                  aria-pressed={mode === value}
                >
                  <Icon
                    size={18}
                    strokeWidth={1.5}
                    className={mode === value ? "text-vera-accent" : "text-vera-muted"}
                  />
                  <div>
                    <p className={cn("text-label font-medium", mode === value ? "text-vera-accent" : "text-vera-ink")}>
                      {label}
                    </p>
                    <p className="text-label text-vera-muted mt-0.5">{desc}</p>
                  </div>
                </button>
                );
              })}
            </div>
            {/* Mode Comparison Persistent Row */}
            <div className="text-[11px] text-vera-muted font-medium bg-vera-paper border border-vera-border rounded p-2 text-center">
              {(modes ?? []).map((m, i) => (
                <span key={m.value}>
                  {i > 0 && <>&nbsp;·&nbsp; </>}
                  <span className="text-vera-ink">{m.label}:</span> {m.summary}
                </span>
              ))}
            </div>
          </div>

          {/* Advanced */}
          <div>
            <button
              type="button"
              onClick={() => setShowAdvanced((v) => !v)}
              className="flex items-center gap-1.5 text-label text-vera-muted hover:text-vera-ink transition-colors"
              aria-expanded={showAdvanced}
            >
              {showAdvanced ? <ChevronUp size={14} strokeWidth={1.5} /> : <ChevronDown size={14} strokeWidth={1.5} />}
              Advanced settings
            </button>

            {showAdvanced && (
              <div className="mt-4 vera-card p-5 bg-vera-paper space-y-6">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-medium text-vera-ink">Resource Limits</h4>
                  <button 
                    type="button"
                    onClick={resetToRecommended}
                    className="text-[11px] font-medium text-vera-accent hover:underline"
                  >
                    Reset to recommended
                  </button>
                </div>

                {/* Max rounds */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <label htmlFor="max-rounds" className="text-label font-medium text-vera-ink">
                      Max execution rounds
                    </label>
                    <span className="text-sm font-bold text-vera-accent">{maxRounds}</span>
                  </div>
                  <input
                    id="max-rounds"
                    type="range"
                    min={limits.rounds.min}
                    max={limits.rounds.max}
                    value={maxRounds}
                    onChange={(e) => setMaxRounds(Number(e.target.value))}
                    className="w-full accent-vera-accent cursor-pointer"
                  />
                  <div className="flex justify-between text-[10px] text-vera-muted mt-1">
                    <span>{limits.rounds.min}</span><span>{limits.rounds.max}</span>
                  </div>
                </div>

                {/* Max cost & live estimate readout */}
                <div className="pt-2 border-t border-vera-border-subtle">
                  <label htmlFor="max-cost" className="text-label font-medium text-vera-ink block mb-2">
                    {STRINGS.newAnalysis.costCeilingLabel}
                  </label>
                  <div className="flex gap-4 items-center">
                    <div className="relative w-32 shrink-0">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-label text-vera-muted">$</span>
                      <input
                        id="max-cost"
                        type="number"
                        min={limits.costCeilingUsd.min}
                        max={limits.costCeilingUsd.max}
                        step={limits.costCeilingUsd.step}
                        value={maxCost}
                        onChange={(e) => { setCostTouched(true); setMaxCost(Number(e.target.value)); }}
                        aria-invalid={maxCostError}
                        aria-describedby={maxCostError ? "max-cost-error" : undefined}
                        className={cn(
                          "vera-input pl-6 w-full",
                          maxCostError && "border-vera-insufficient focus:border-vera-insufficient"
                        )}
                      />
                    </div>
                    <div className="text-[11px] text-vera-subtle leading-tight">
                      At {maxRounds} rounds, estimated cap is <span className="text-vera-ink font-medium">{formatCost(estimatedCap)}</span>.
                      <br />(Rarely exceeds {formatCost(typicalSpendUsd(maxRounds, limits))} in practice).
                    </div>
                  </div>
                  {maxCostError && (
                    <p id="max-cost-error" className="text-[11px] text-vera-insufficient font-medium mt-1.5">
                      Cost ceiling must be between {formatCost(limits.costCeilingUsd.min)} and {formatCost(limits.costCeilingUsd.max)}.
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>

          {error && <p className="text-label text-vera-insufficient">{error}</p>}

          {/* Submit */}
          <button
            type="submit"
            disabled={!query.trim() || submitting || maxCostError}
            title={!query.trim() ? STRINGS.newAnalysis.submitDisabledTooltip : undefined}
            className={cn(
              "w-full justify-center py-3 text-sm font-medium rounded transition-all",
              !query.trim() || maxCostError
                ? "bg-vera-surface border border-vera-border text-vera-muted cursor-not-allowed opacity-50"
                : "vera-btn-primary"
            )}
          >
            {submitting ? STRINGS.newAnalysis.submitBusy : STRINGS.newAnalysis.submitIdle}
          </button>
        </form>
      </div>
    </div>
  );
}
