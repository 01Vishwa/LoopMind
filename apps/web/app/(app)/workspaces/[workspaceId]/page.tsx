"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Plus, RefreshCw } from "lucide-react";
import { FileGrid } from "@/components/workspace/FileGrid";
import { DescriptionDrawer } from "@/components/workspace/DescriptionDrawer";
import { UploadDropzone } from "@/components/workspace/UploadDropzone";
import { Breadcrumbs } from "@/components/shared/Breadcrumbs";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { BlockSkeleton, ErrorState } from "@/components/shared/DataStates";
import Link from "next/link";
import { useResource } from "@/lib/data/useResource";
import { getWorkspace } from "@/lib/data/workspaces";
import { listWorkspaceFiles, ingestWorkspaceFiles } from "@/lib/data/workspaceFiles";
import type { WorkspaceFile } from "@/lib/schemas/runSchemas";

export default function WorkspaceDetailPage() {
  const params = useParams();
  const workspaceId = params.workspaceId as string;

  const {
    data: workspace,
    status: workspaceStatus,
    error: workspaceError,
    retry: retryWorkspace,
  } = useResource(() => getWorkspace(workspaceId), [workspaceId]);

  const {
    data: fetchedFiles,
    status: filesStatus,
    error: filesError,
    retry: retryFiles,
  } = useResource(() => listWorkspaceFiles(workspaceId), [workspaceId]);

  // Local copy so uploads and ingestion can update the grid optimistically;
  // it is re-seeded whenever the server list arrives.
  const [files, setFiles] = useState<WorkspaceFile[]>([]);
  useEffect(() => {
    if (fetchedFiles) setFiles(fetchedFiles);
  }, [fetchedFiles]);

  const [selectedFile, setSelectedFile] = useState<WorkspaceFile | null>(null);
  const [ingesting, setIngesting] = useState(false);

  const handleIngestAll = useCallback(async () => {
    setIngesting(true);
    try {
      // The server owns the status transitions; adopt whatever it reports.
      setFiles(await ingestWorkspaceFiles(workspaceId));
    } finally {
      setIngesting(false);
    }
  }, [workspaceId]);

  const readyCount = files.filter((f) => f.status === "ready").length;
  const pendingCount = files.filter((f) => f.status === "pending").length;
  const analyzingCount = files.filter((f) => f.status === "analyzing").length;
  const workspaceName = workspace?.name ?? "";

  const loading = workspaceStatus === "loading" || filesStatus === "loading";
  const error = workspaceError ?? filesError;
  const retry = useCallback(() => {
    retryWorkspace();
    retryFiles();
  }, [retryWorkspace, retryFiles]);

  if (error) {
    return (
      <div className="px-6 py-6 max-w-[1440px] mx-auto">
        <Breadcrumbs
          segments={[{ label: "Workspaces", href: "/workspaces" }]}
          className="mb-4"
        />
        <ErrorState error={error} onRetry={retry} />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="px-6 py-6 max-w-[1440px] mx-auto">
        <Breadcrumbs
          segments={[{ label: "Workspaces", href: "/workspaces" }]}
          className="mb-4"
        />
        <BlockSkeleton className="max-w-sm mb-6" lines={2} />
        <div className="bg-vera-surface border border-vera-border rounded p-6" style={{ borderRadius: "6px" }}>
          <BlockSkeleton lines={4} />
        </div>
      </div>
    );
  }

  return (
    <div className="px-6 py-6 max-w-[1440px] mx-auto">
      {/* Breadcrumbs */}
      <Breadcrumbs
        segments={[
          { label: "Workspaces", href: "/workspaces" },
          { label: workspaceName },
        ]}
        className="mb-4"
      />

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1
              className="text-display text-vera-ink"
              style={{ fontFamily: "'JetBrains Mono', monospace" }}
            >
              {workspaceName}
            </h1>
            {workspace && <StatusBadge status={workspace.status} />}
          </div>
          <p className="text-body text-vera-muted mt-1">
            {files.length} file{files.length !== 1 ? "s" : ""} · {readyCount} described
            {analyzingCount > 0 && ` · ${analyzingCount} analyzing`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleIngestAll}
            disabled={ingesting || analyzingCount > 0 || pendingCount === 0}
            title={
              !ingesting && analyzingCount === 0 && pendingCount === 0
                ? "All files already analyzed."
                : undefined
            }
            className="flex items-center gap-2 px-4 py-2 text-label font-medium text-vera-ink border border-vera-border rounded hover:bg-vera-border-subtle disabled:opacity-50 transition-colors"
            style={{ borderRadius: "6px" }}
          >
            <RefreshCw
              size={14}
              strokeWidth={1.5}
              className={ingesting || analyzingCount > 0 ? "animate-spin" : ""}
            />
            {ingesting || analyzingCount > 0
              ? "Analyzing…"
              : `Analyze pending${pendingCount > 0 ? ` (${pendingCount})` : ""}`}
          </button>
          <Link
            href={`/runs/new?workspaceId=${workspaceId}`}
            className="inline-flex items-center gap-2 bg-vera-accent text-white font-medium px-4 py-2 rounded-md text-sm hover:bg-vera-accent-hover transition-colors no-underline"
          >
            <Plus size={16} strokeWidth={1.5} />
            New analysis
          </Link>
        </div>
      </div>

      {/* Upload zone */}
      <div className="mb-6">
        <UploadDropzone
          workspaceId={workspaceId}
          compact={files.length > 0}
          onUploaded={(uploadedFiles) => {
            // The server assigns id, kind, and uploadedAt — adopt its records.
            setFiles((prev) => [...prev, ...uploadedFiles]);
          }}
        />
      </div>

      {/* File grid */}
      <div className="bg-vera-surface border border-vera-border rounded" style={{ borderRadius: "6px" }}>
        <FileGrid files={files} onFileClick={setSelectedFile} />
      </div>

      {/* Description drawer */}
      <DescriptionDrawer
        workspaceId={workspaceId}
        file={selectedFile}
        onClose={() => setSelectedFile(null)}
      />
    </div>
  );
}
