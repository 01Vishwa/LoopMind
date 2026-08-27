"use client";

import { useState } from "react";
import { ArrowUpDown, Plus, ChevronUp, ChevronDown, ArrowRight, LayoutGrid } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils/cn";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { formatRelativeTime } from "@/lib/utils/formatRelativeTime";
import { WORKSPACE_STATUS_TOOLTIPS } from "@/lib/config/statusTooltips";
import type { Workspace } from "@/lib/schemas/runSchemas";

type SortKey = "name" | "fileCount" | "lastActivityAt" | "status";
type SortDir = "asc" | "desc";

export interface WorkspaceTableProps {
  workspaces: Workspace[];
  onNew: () => void;
}

export function WorkspaceTable({ workspaces, onNew }: WorkspaceTableProps) {
  const router = useRouter();
  const [sortKey, setSortKey] = useState<SortKey>("lastActivityAt");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(key); setSortDir("asc"); }
  };

  const sorted = [...workspaces].sort((a, b) => {
    let cmp = 0;
    if (sortKey === "name") cmp = a.name.localeCompare(b.name);
    else if (sortKey === "fileCount") cmp = a.fileCount - b.fileCount;
    else if (sortKey === "lastActivityAt") cmp = new Date(a.lastActivityAt).getTime() - new Date(b.lastActivityAt).getTime();
    else if (sortKey === "status") cmp = a.status.localeCompare(b.status);
    return sortDir === "asc" ? cmp : -cmp;
  });

  if (workspaces.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <div className="w-16 h-16 bg-vera-accent-muted rounded-2xl flex items-center justify-center mb-6 shadow-sm border border-vera-accent/20">
          <LayoutGrid size={32} className="text-vera-accent" strokeWidth={1.5} />
        </div>
        <h3 className="text-heading text-vera-ink mb-2">No workspaces yet</h3>
        <p className="text-body text-vera-muted mb-8 max-w-sm">
          Create your first workspace to upload datasets and start analyzing your data.
        </p>
        <button
          id="new-workspace-cta"
          onClick={onNew}
          className="vera-btn-primary"
        >
          <Plus size={16} strokeWidth={2} />
          Create your first workspace
        </button>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto vera-card">
      <table className="vera-table" aria-label="Workspaces">
        <thead>
          <tr>
            {(
              [
                { key: "name", label: "Name" },
                { key: "fileCount", label: "Files" },
                { key: "lastActivityAt", label: "Last Activity" },
                { key: "status", label: "Status" },
              ] as { key: SortKey; label: string }[]
            ).map(({ key, label }) => (
              <th
                key={key}
                aria-sort={sortKey === key ? (sortDir === "asc" ? "ascending" : "descending") : "none"}
                style={{ width: key === "status" ? "240px" : "auto" }}
              >
                <button
                  type="button"
                  onClick={() => handleSort(key)}
                  className="flex items-center gap-1.5"
                >
                  {label}
                  {sortKey === key ? (
                    sortDir === "asc" ? (
                      <ChevronUp size={12} strokeWidth={2} className="text-vera-ink" />
                    ) : (
                      <ChevronDown size={12} strokeWidth={2} className="text-vera-ink" />
                    )
                  ) : (
                    <ArrowUpDown size={12} strokeWidth={2} className="opacity-0 group-hover:opacity-40 transition-opacity" />
                  )}
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="group/tbody">
          {sorted.map((ws) => {
            const isPartial = ws.status === "partial";
            const tooltipText = WORKSPACE_STATUS_TOOLTIPS[ws.status];

            return (
              <tr
                key={ws.id}
                className="group/row relative"
              >
                <td className="px-4 py-3">
                  <Link
                    href={`/workspaces/${ws.id}`}
                    className="text-body text-vera-ink font-medium group-hover/row:text-vera-accent transition-colors no-underline before:absolute before:inset-0 before:content-[''] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vera-accent rounded-sm"
                  >
                    {ws.name}
                  </Link>
                  {ws.description && (
                    <p className="text-label text-vera-muted mt-0.5 truncate max-w-xs relative">{ws.description}</p>
                  )}
                </td>
                <td className={cn("px-4 py-3 text-label text-vera-muted font-medium", "tabular-nums")} aria-hidden>{ws.fileCount}</td>
                <td className="px-4 py-3 text-label text-vera-muted" aria-hidden>{formatRelativeTime(ws.lastActivityAt)}</td>
                <td className="px-4 py-3 relative z-10">
                  <div className="flex items-center justify-between min-w-[200px]">
                    <StatusBadge
                      status={ws.status}
                      tooltip={tooltipText}
                    />

                    {/* Resume setup deep-link CTA (visible on hover) */}
                    {isPartial && (
                      <button
                        onClick={() => router.push(`/workspaces/${ws.id}?action=resume`)}
                        className="opacity-0 group-hover/row:opacity-100 flex items-center gap-1 text-[11px] font-medium text-vera-accent hover:text-vera-accent-hover transition-all bg-vera-accent-glow px-2 py-1 rounded"
                      >
                        Resume setup
                        <ArrowRight size={10} strokeWidth={2} />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
