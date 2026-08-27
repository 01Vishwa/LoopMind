"use client";

import { useState } from "react";
import { ChevronUp, ChevronDown, ArrowUpDown } from "lucide-react";
import { FileTypeBadge } from "@/components/shared/FileTypeBadge";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { cn } from "@/lib/utils/cn";
import { formatRelativeTime } from "@/lib/utils/formatRelativeTime";
import type { WorkspaceFile } from "@/lib/schemas/runSchemas";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

type SortKey = "name" | "kind" | "sizeBytes" | "status" | "uploadedAt";
type SortDir = "asc" | "desc";

export interface FileGridProps {
  files: WorkspaceFile[];
  onFileClick: (file: WorkspaceFile) => void;
}

export function FileGrid({ files, onFileClick }: FileGridProps) {
  const [sortKey, setSortKey] = useState<SortKey>("uploadedAt");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(key); setSortDir("asc"); }
  };

  const sorted = [...files].sort((a, b) => {
    let cmp = 0;
    if (sortKey === "name") cmp = a.name.localeCompare(b.name);
    else if (sortKey === "kind") cmp = a.kind.localeCompare(b.kind);
    else if (sortKey === "sizeBytes") cmp = a.sizeBytes - b.sizeBytes;
    else if (sortKey === "status") cmp = a.status.localeCompare(b.status);
    else if (sortKey === "uploadedAt") cmp = new Date(a.uploadedAt).getTime() - new Date(b.uploadedAt).getTime();
    return sortDir === "asc" ? cmp : -cmp;
  });

  const SortIcon = ({ col }: { col: SortKey }) =>
    sortKey === col ? (
      sortDir === "asc" ? <ChevronUp size={12} strokeWidth={1.5} /> : <ChevronDown size={12} strokeWidth={1.5} />
    ) : (
      <ArrowUpDown size={11} strokeWidth={1.5} className="opacity-40" />
    );

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left" aria-label="Files">
        <thead>
          <tr className="border-b border-vera-border">
            {(
              [
                { key: "name", label: "Filename" },
                { key: "kind", label: "Type" },
                { key: "sizeBytes", label: "Size" },
                { key: "status", label: "Description" },
                { key: "uploadedAt", label: "Uploaded" },
              ] as { key: SortKey; label: string }[]
            ).map(({ key, label }) => (
              <th
                key={key}
                className={cn("table-header px-4 py-3 select-none")}
                aria-sort={sortKey === key ? (sortDir === "asc" ? "ascending" : "descending") : "none"}
              >
                <button
                  type="button"
                  onClick={() => handleSort(key)}
                  className="flex items-center gap-1 hover:text-vera-ink transition-colors"
                >
                  {label}
                  <SortIcon col={key} />
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((file) => (
            <tr
              key={file.id}
              className="border-b border-vera-border-subtle hover:bg-vera-border-subtle/50 transition-colors cursor-pointer"
              onClick={() => onFileClick(file)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onFileClick(file);
                }
              }}
              aria-label={`View details for ${file.name}`}
            >
              <td className="px-4 py-3 text-body text-vera-ink font-medium">{file.name}</td>
              <td className="px-4 py-3">
                <FileTypeBadge kind={file.kind} />
              </td>
              <td className={cn("px-4 py-3 text-label text-vera-muted", "tabular-nums")}>{formatBytes(file.sizeBytes)}</td>
              <td className="px-4 py-3">
                <StatusBadge status={file.status} />
              </td>
              <td className="px-4 py-3 text-label text-vera-muted">{formatRelativeTime(file.uploadedAt)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {files.length === 0 && (
        <div className="py-16 text-center">
          <p className="text-body text-vera-muted">Drop files here to start.</p>
        </div>
      )}
    </div>
  );
}
