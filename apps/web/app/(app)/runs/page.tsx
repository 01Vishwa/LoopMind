"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { Plus, Search, RotateCcw, ArrowDown, ArrowUp, X } from "lucide-react";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { EmptyState, NoRunsIllustration } from "@/components/shared/EmptyState";
import { TableSkeleton, ErrorState } from "@/components/shared/DataStates";
import { cn } from "@/lib/utils/cn";
import { useResource } from "@/lib/data/useResource";
import { listRuns, countRuns, retryRun, RUN_STATUSES } from "@/lib/data/runs";
import { listWorkspaces } from "@/lib/data/workspaces";
import { formatRelativeTime, formatAbsoluteTime } from "@/lib/utils/formatRelativeTime";
import { formatCost } from "@/lib/utils/formatCost";
import { STRINGS } from "@/lib/config/strings";
import type { RunStatus } from "@/lib/data/types";

type SortField = "cost" | "createdAt";
type SortOrder = "asc" | "desc";

const PAGE_SIZE = 25;

/** How long the search box waits after the last keystroke before refetching. */
const SEARCH_DEBOUNCE_MS = 300;

export default function RunsListPage() {
  return (
    <Suspense fallback={null}>
      <RunsListContent />
    </Suspense>
  );
}

function RunsListContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Filter state
  const statusFilter = searchParams.get("status") || "all";
  const workspaceFilter = searchParams.get("workspace") || "all";
  const searchQuery = searchParams.get("q") || "";
  
  // Sort state
  const sortField = (searchParams.get("sort") as SortField) || "createdAt";
  const sortOrder = (searchParams.get("order") as SortOrder) || "desc";

  const updateParams = (updates: Record<string, string | null>) => {
    const params = new URLSearchParams(searchParams.toString());
    Object.entries(updates).forEach(([key, value]) => {
      if (value === null || value === "all" || value === "") {
        params.delete(key);
      } else {
        params.set(key, value);
      }
    });
    router.replace(`${pathname}?${params.toString()}`);
  };

  const [retryError, setRetryError] = useState<string | null>(null);

  // Search is debounced so a refetch fires once the user pauses, not per
  // keystroke. The input stays responsive by tracking its own value.
  const [searchInput, setSearchInput] = useState(searchQuery);
  useEffect(() => {
    setSearchInput(searchQuery);
    // Only re-sync when the query changes from outside this input (back/forward).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchQuery]);

  useEffect(() => {
    if (searchInput === searchQuery) return;
    const timer = setTimeout(() => updateParams({ q: searchInput }), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchInput]);

  const handleRetry = async (e: React.MouseEvent, runId: string) => {
    e.stopPropagation();
    e.preventDefault();
    try {
      const { runId: retried } = await retryRun(runId);
      setRetryError(null);
      router.push(`/runs/${retried}`);
    } catch (err) {
      setRetryError(err instanceof Error ? err.message : String(err));
    }
  };

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      updateParams({ order: sortOrder === "asc" ? "desc" : "asc" });
    } else {
      updateParams({ sort: field, order: "desc" }); // Default to desc when switching fields
    }
  };

  // Cursor-style pagination — resets whenever the filters change.
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
  }, [statusFilter, workspaceFilter, searchQuery]);

  // Filters AND ordering are sent to the data layer, not applied to a local
  // array — otherwise "Load more" re-sorts only the rows already fetched.
  const runsResource = useResource(
    () => {
      const filters = {
        status: statusFilter as RunStatus | "all",
        workspaceId: workspaceFilter,
        q: searchQuery,
        limit: visibleCount,
        sort: sortField,
        order: sortOrder,
      };
      return listRuns(filters);
    },
    [statusFilter, workspaceFilter, searchQuery, visibleCount, sortField, sortOrder],
  );

  // Workspace filter options come from the workspace list, not from run rows.
  const workspacesResource = useResource(listWorkspaces, []);
  const workspaces = workspacesResource.data ?? [];

  // Distinguishes "you have no runs" from "no runs match these filters".
  const totalResource = useResource(countRuns, []);

  const page = runsResource.data;
  // Server returns rows already ordered by the active sort/order params.
  const rows = page?.items ?? [];

  const hasActiveFilters = statusFilter !== "all" || workspaceFilter !== "all" || searchQuery !== "";
  const isTrueEmpty = totalResource.status === "success" && totalResource.data === 0;

  return (
    <div className="px-6 py-6 max-w-[1440px] mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-display text-vera-ink" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
            Runs
          </h1>
        </div>
        <Link
          href="/runs/new"
          className="inline-flex items-center gap-2 bg-vera-accent text-white font-medium px-4 py-2 rounded-md text-sm hover:bg-vera-accent-hover transition-colors no-underline"
        >
          <Plus size={16} strokeWidth={1.5} />
          New analysis
        </Link>
      </div>

      {isTrueEmpty ? (
        <div className="border border-dashed border-vera-border rounded" style={{ borderRadius: "6px" }}>
          <EmptyState
            illustration={<NoRunsIllustration />}
            title={STRINGS.runs.emptyTitle}
            subtitle={STRINGS.runs.emptySubtitle}
            ctaLabel={STRINGS.runs.emptyCta}
            ctaHref="/runs/new"
          />
        </div>
      ) : (
        <div className="space-y-4">
          {/* Filter Bar */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-[200px] max-w-[400px]">
              <Search size={14} strokeWidth={1.5} className="absolute left-3 top-1/2 -translate-y-1/2 text-vera-muted" />
              <input
                type="text"
                placeholder={STRINGS.runs.searchPlaceholder}
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                className="vera-input pl-8 py-1.5 text-sm w-full"
              />
            </div>

            <div className="flex items-center gap-3">
              <select
                value={statusFilter}
                onChange={(e) => updateParams({ status: e.target.value })}
                className="vera-input py-1.5 text-sm w-[160px]"
              >
                <option value="all">{STRINGS.runs.allStatuses}</option>
                {RUN_STATUSES.map(({ value, label }) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>

              <select
                value={workspaceFilter}
                onChange={(e) => updateParams({ workspace: e.target.value })}
                className="vera-input py-1.5 text-sm w-[200px]"
              >
                <option value="all">{STRINGS.runs.allWorkspaces}</option>
                {workspaces.map((ws) => (
                  <option key={ws.id} value={ws.id}>{ws.name}</option>
                ))}
              </select>
            </div>

            {hasActiveFilters && (
              <button
                onClick={() => updateParams({ status: "all", workspace: "all", q: "" })}
                className="text-label text-vera-muted hover:text-vera-ink transition-colors flex items-center gap-1 ml-auto"
              >
                <X size={14} strokeWidth={1.5} />
                {STRINGS.runs.clearFilters}
              </button>
            )}
          </div>

          {retryError && (
            <p className="text-label text-vera-insufficient">{retryError}</p>
          )}

          {/* Table */}
          <div className="bg-vera-surface border border-vera-border rounded overflow-hidden" style={{ borderRadius: "6px" }}>
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-vera-border bg-vera-surface">
                  <th className="table-header px-4 py-3">Query</th>
                  <th className="table-header px-4 py-3 w-[180px]">Workspace</th>
                  <th className="table-header px-4 py-3 w-[120px]">Status</th>

                  {/* Sortable Header: Cost */}
                  <th
                    className="table-header px-4 py-3 w-[100px] cursor-pointer hover:bg-vera-border-subtle/50 transition-colors select-none group"
                    onClick={() => toggleSort("cost")}
                  >
                    <div className="flex items-center gap-1">
                      <span className={cn(sortField === "cost" && "text-vera-ink font-bold")}>Cost</span>
                      {sortField === "cost" ? (
                        sortOrder === "asc" ? <ArrowUp size={12} className="text-vera-ink" /> : <ArrowDown size={12} className="text-vera-ink" />
                      ) : (
                        <ArrowDown size={12} className="opacity-0 group-hover:opacity-50" />
                      )}
                    </div>
                  </th>

                  {/* Sortable Header: Started */}
                  <th
                    className="table-header px-4 py-3 w-[120px] cursor-pointer hover:bg-vera-border-subtle/50 transition-colors select-none group"
                    onClick={() => toggleSort("createdAt")}
                  >
                    <div className="flex items-center gap-1">
                      <span className={cn(sortField === "createdAt" && "text-vera-ink font-bold")}>Started</span>
                      {sortField === "createdAt" ? (
                        sortOrder === "asc" ? <ArrowUp size={12} className="text-vera-ink" /> : <ArrowDown size={12} className="text-vera-ink" />
                      ) : (
                        <ArrowDown size={12} className="opacity-0 group-hover:opacity-50" />
                      )}
                    </div>
                  </th>

                  <th className="table-header px-4 py-3 w-[130px]">Run ID</th>
                  <th className="w-12 px-2">{/* Actions column */}</th>
                </tr>
              </thead>
              {runsResource.status === "loading" ? (
                <TableSkeleton rows={4} cols={7} />
              ) : runsResource.status === "error" ? (
                <tbody>
                  <tr>
                    <td colSpan={7}>
                      <ErrorState error={runsResource.error} onRetry={runsResource.retry} />
                    </td>
                  </tr>
                </tbody>
              ) : (
              <tbody>
                {rows.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-12 text-center">
                      <p className="text-label text-vera-muted mb-2">{STRINGS.runs.noMatchTitle}</p>
                      <button
                        onClick={() => updateParams({ status: "all", workspace: "all", q: "" })}
                        className="text-label text-vera-accent hover:underline font-medium"
                      >
                        {STRINGS.runs.clearFilters}
                      </button>
                    </td>
                  </tr>
                ) : (
                  rows.map((run) => (
                    <tr
                      key={run.runId}
                      className="border-b border-vera-border-subtle hover:bg-vera-border-subtle/50 transition-colors group"
                    >
                      <td className="px-4 py-3">
                        {/* The link carries the navigation, so the row is keyboard-operable. */}
                        <Link
                          href={`/runs/${run.runId}`}
                          className="block text-label text-vera-ink group-hover:text-vera-accent group-hover:underline transition-colors truncate max-w-[280px] no-underline rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-vera-accent"
                          title={run.query}
                        >
                          {run.query}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-label text-vera-muted">
                        {run.workspaceName}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={run.status} />
                      </td>
                      <td className="px-4 py-3 text-mono-ui text-vera-muted">
                        {formatCost(run.costUsd)}
                      </td>
                      <td className="px-4 py-3 text-label text-vera-muted" title={formatAbsoluteTime(run.createdAt)}>
                        {formatRelativeTime(run.createdAt)}
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-mono-ui text-vera-muted" style={{ fontSize: "11px" }}>
                          {run.runId}
                        </span>
                      </td>

                      {/* Actions Cell */}
                      <td className="px-2 py-3 text-right">
                        {(run.status === "failed" || run.status === "cancelled") && (
                          <button
                            onClick={(e) => handleRetry(e, run.runId)}
                            className="p-1.5 text-vera-muted hover:text-vera-ink hover:bg-vera-border rounded transition-all opacity-0 group-hover:opacity-100 focus:opacity-100"
                            title="Retry this run"
                          >
                            <RotateCcw size={14} strokeWidth={2} />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
              )}
            </table>
          </div>

          {/* Pagination footer — counts come from the response envelope */}
          {page && page.total > 0 && (
            <div className="flex flex-col items-center gap-3 pt-2">
              <p className="text-label text-vera-muted">
                Showing {page.showing} of {page.total} runs
              </p>
              {page.showing < page.total && (
                <button
                  onClick={() => setVisibleCount((v) => v + PAGE_SIZE)}
                  className="px-4 py-2 text-label font-medium text-vera-ink border border-vera-border rounded-md hover:bg-vera-border-subtle transition-colors"
                >
                  Load more
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
