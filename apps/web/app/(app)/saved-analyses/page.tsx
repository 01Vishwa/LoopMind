"use client";

import { useEffect, useState } from "react";
import { Play, RefreshCw, Pencil, Trash2, PauseCircle, PlayCircle, X } from "lucide-react";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { EmptyState, NoSavedAnalysesIllustration } from "@/components/shared/EmptyState";
import { BlockSkeleton, ErrorState } from "@/components/shared/DataStates";
import { cn } from "@/lib/utils/cn";
import { useResource } from "@/lib/data/useResource";
import {
  listSavedAnalyses,
  deleteSavedAnalysis,
  rerunSavedAnalysis,
  setSchedulePaused,
  scheduleLabel,
  nextRunLabel,
  countScheduled,
} from "@/lib/data/savedAnalyses";
import { formatRelativeTime, formatAbsoluteTime } from "@/lib/utils/formatRelativeTime";
import { STRINGS } from "@/lib/config/strings";
import type { SavedAnalysis } from "@/lib/data/types";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function SavedAnalysesPage() {
  const router = useRouter();
  const { data, status: loadStatus, error, retry } = useResource(listSavedAnalyses, []);
  const [analyses, setAnalyses] = useState<SavedAnalysis[]>([]);
  const [rerunning, setRerunning] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [errorPopoverId, setErrorPopoverId] = useState<string | null>(null);
  const [mutationError, setMutationError] = useState<string | null>(null);

  useEffect(() => {
    if (data) setAnalyses(data);
  }, [data]);

  const errMsg = (err: unknown) => (err instanceof Error ? err.message : String(err));

  const togglePause = async (id: string) => {
    const target = analyses.find((a) => a.id === id);
    if (!target) return;
    const previous = analyses;
    const paused = !target.schedule.paused;
    setAnalyses((prev) =>
      prev.map((a) => (a.id === id ? { ...a, schedule: { ...a.schedule, paused } } : a)),
    );
    try {
      await setSchedulePaused(id, paused);
      setMutationError(null);
    } catch (err) {
      setAnalyses(previous);
      setMutationError(errMsg(err));
    }
  };

  const handleDelete = async (id: string) => {
    const previous = analyses;
    setAnalyses((prev) => prev.filter((a) => a.id !== id));
    setDeleteConfirmId(null);
    try {
      await deleteSavedAnalysis(id);
      setMutationError(null);
    } catch (err) {
      setAnalyses(previous);
      setMutationError(errMsg(err));
    }
  };

  const handleReRun = async (id: string) => {
    const previous = analyses;
    setRerunning(id);
    try {
      await rerunSavedAnalysis(id);
      // Only reflect success once the call actually resolves.
      setAnalyses((prev) =>
        prev.map((a) =>
          a.id === id ? { ...a, status: "succeeded", lastRun: new Date().toISOString() } : a,
        ),
      );
      setMutationError(null);
    } catch (err) {
      setAnalyses(previous);
      setMutationError(errMsg(err));
    } finally {
      setRerunning(null);
    }
  };

  return (
    <div className="px-6 py-6 max-w-[1440px] mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-display text-vera-ink" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
            Saved Analyses
          </h1>
          {analyses.length > 0 && (
            <p className="text-label text-vera-muted mt-1">
              {analyses.length} saved · {countScheduled(analyses)} scheduled
            </p>
          )}
        </div>
      </div>

      {mutationError && (
        <p className="text-label text-vera-insufficient mb-3">{mutationError}</p>
      )}

      <div className="bg-vera-surface border border-vera-border rounded overflow-visible relative" style={{ borderRadius: "6px" }}>
        {loadStatus === "loading" ? (
          <BlockSkeleton className="p-4" lines={3} />
        ) : loadStatus === "error" ? (
          <ErrorState error={error} onRetry={retry} />
        ) : analyses.length === 0 ? (
          <EmptyState
            illustration={<NoSavedAnalysesIllustration />}
            title={STRINGS.savedAnalyses.emptyTitle}
            subtitle={STRINGS.savedAnalyses.emptySubtitle}
          />
        ) : (
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-vera-border bg-vera-surface">
                {["Name", "Workspace", "Last Run", "Schedule", "Status", ""].map((h) => (
                  <th key={h} className="table-header px-4 py-3">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {analyses.map((sa) => (
                <tr key={sa.id} className="border-b border-vera-border-subtle hover:bg-vera-border-subtle/50 transition-colors group">
                  <td className="px-4 py-3">
                    <div className="flex flex-col">
                      <Link href={`/runs/${sa.id}`} className="text-body text-vera-ink font-medium hover:text-vera-accent no-underline transition-colors w-fit">
                        {sa.name}
                      </Link>
                      <span className="text-label text-vera-muted truncate max-w-xs mt-0.5">{sa.query}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-label text-vera-muted">{sa.workspaceName}</td>
                  <td className="px-4 py-3 text-label text-vera-muted" title={formatAbsoluteTime(sa.lastRun)}>{formatRelativeTime(sa.lastRun)}</td>
                  
                  {/* Schedule Column */}
                  <td className="px-4 py-3 text-label">
                    <div className="flex items-center gap-2">
                      <div className="flex flex-col min-w-[80px]">
                        <span className={cn("font-medium", sa.schedule.paused ? "text-vera-muted" : "text-vera-ink")}>
                          {scheduleLabel(sa.schedule)}
                        </span>
                        {nextRunLabel(sa.schedule) && (
                          <span className={cn("text-[10px] text-vera-subtle mt-0.5", sa.schedule.paused && "line-through")}>
                            {nextRunLabel(sa.schedule)}
                          </span>
                        )}
                      </div>
                      
                      {sa.schedule.frequency !== "manual" && (
                        <button
                          onClick={() => togglePause(sa.id)}
                          className={cn(
                            "p-1.5 rounded transition-all ml-2",
                            sa.schedule.paused 
                              ? "text-vera-muted hover:text-vera-verified hover:bg-vera-verified-muted/50" 
                              : "text-vera-muted hover:text-vera-warning hover:bg-vera-warning-muted/50 opacity-0 group-hover:opacity-100"
                          )}
                          title={sa.schedule.paused ? "Resume schedule" : "Pause schedule"}
                        >
                          {sa.schedule.paused ? <PlayCircle size={14} strokeWidth={2} /> : <PauseCircle size={14} strokeWidth={2} />}
                        </button>
                      )}
                    </div>
                  </td>

                  {/* Status Column */}
                  <td className="px-4 py-3 relative">
                    {sa.status === "failed" ? (
                      <div className="relative inline-block">
                        <button
                          onClick={() => setErrorPopoverId(errorPopoverId === sa.id ? null : sa.id)}
                          aria-label="View error detail"
                          className="cursor-pointer"
                        >
                          <StatusBadge status={sa.status} />
                        </button>

                        {/* Error Popover */}
                        {errorPopoverId === sa.id && (
                          <div className="absolute top-full mt-2 left-0 w-64 bg-vera-surface border border-vera-insufficient/30 shadow-xl rounded-md p-3 z-50 animate-fade-in">
                            <div className="flex justify-between items-start mb-2">
                              <span className="text-[10px] font-bold text-vera-insufficient uppercase tracking-wider">Verifier Rationale</span>
                              <button onClick={() => setErrorPopoverId(null)} className="text-vera-muted hover:text-vera-ink">
                                <X size={12} strokeWidth={2} />
                              </button>
                            </div>
                            <p className="text-label text-vera-ink leading-relaxed">
                              {sa.errorReason || "Unknown failure."}
                            </p>
                            {sa.schedule.frequency !== "manual" && !sa.schedule.paused && (
                              <p className="text-[10px] text-vera-warning mt-2 font-medium">
                                Schedule will remain active and may continue to fail until paused or fixed.
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    ) : (
                      <StatusBadge status={sa.status} />
                    )}
                  </td>

                  {/* Actions Column */}
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      {/* Edit Button */}
                      <button
                        onClick={() => router.push(`/runs/new?workspaceId=${sa.workspaceId}&query=${encodeURIComponent(sa.query)}`)}
                        className="p-1.5 text-vera-muted hover:text-vera-ink hover:bg-vera-border-subtle rounded transition-all opacity-0 group-hover:opacity-100"
                        title="Edit analysis"
                      >
                        <Pencil size={14} strokeWidth={2} />
                      </button>

                      {/* Delete Action */}
                      <div className="relative">
                        <button
                          onClick={() => setDeleteConfirmId(sa.id)}
                          className="p-1.5 text-vera-muted hover:text-vera-insufficient hover:bg-vera-insufficient-muted/50 rounded transition-all opacity-0 group-hover:opacity-100"
                          title="Delete saved analysis"
                        >
                          <Trash2 size={14} strokeWidth={2} />
                        </button>
                        
                        {deleteConfirmId === sa.id && (
                          <div className="absolute right-0 top-full mt-2 bg-vera-surface border border-vera-border shadow-lg rounded p-2 z-50 flex items-center gap-2">
                            <span className="text-[11px] text-vera-muted whitespace-nowrap px-1">Delete?</span>
                            <button onClick={() => handleDelete(sa.id)} className="text-[11px] font-medium text-vera-insufficient hover:underline px-1">Yes</button>
                            <span className="text-vera-border">|</span>
                            <button onClick={() => setDeleteConfirmId(null)} className="text-[11px] font-medium text-vera-ink hover:underline px-1">No</button>
                          </div>
                        )}
                      </div>

                      {/* Re-run Button */}
                      <button
                        disabled={rerunning !== null}
                        onClick={() => handleReRun(sa.id)}
                        className={cn(
                          "flex items-center gap-1.5 px-3 py-1.5 text-label font-medium border rounded transition-all ml-2",
                          rerunning === sa.id
                            ? "border-vera-accent bg-vera-accent text-white" 
                            : "text-vera-muted border-vera-border hover:bg-vera-border-subtle hover:text-vera-ink",
                          rerunning !== null && rerunning !== sa.id && "opacity-50 cursor-not-allowed"
                        )}
                        style={{ borderRadius: "4px" }}
                      >
                        {rerunning === sa.id ? (
                          <>
                            <RefreshCw size={12} strokeWidth={2} className="animate-spin text-white/80" />
                            <span className="text-white">Running...</span>
                          </>
                        ) : (
                          <>
                            <Play size={12} strokeWidth={1.5} />
                            <span>Re-run</span>
                          </>
                        )}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
