"use client";

import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { WorkspaceTable } from "@/components/workspace/WorkspaceTable";
import { NewWorkspaceModal } from "@/components/workspace/NewWorkspaceModal";
import { BlockSkeleton, ErrorState } from "@/components/shared/DataStates";
import { listWorkspaces, createWorkspace } from "@/lib/data/workspaces";
import { uploadWorkspaceFile } from "@/lib/data/workspaceFiles";
import { useResource } from "@/lib/data/useResource";
import type { Workspace } from "@/lib/schemas/runSchemas";

export default function WorkspacesPage() {
  const { data, status, error, retry } = useResource(listWorkspaces, []);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [modalOpen, setModalOpen] = useState(false);

  // Mirror fetched data into local state so optimistic creates can prepend.
  useEffect(() => {
    if (data) setWorkspaces(data);
  }, [data]);

  const handleCreated = async (name: string, description: string, files: File[]) => {
    const created = await createWorkspace(name, description);
    // Files staged in the modal can only be uploaded once the workspace exists.
    for (const file of files) {
      await uploadWorkspaceFile(created.id, file);
    }
    setWorkspaces((prev) => [
      files.length > 0 ? { ...created, fileCount: created.fileCount + files.length } : created,
      ...prev,
    ]);
  };

  return (
    <div className="px-6 py-6 max-w-[1440px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1
            className="text-display text-vera-ink"
            style={{ fontFamily: "'JetBrains Mono', monospace" }}
          >
            Workspaces
          </h1>
        </div>
        <button
          id="new-workspace-btn"
          onClick={() => setModalOpen(true)}
          className="inline-flex items-center gap-2 bg-vera-accent text-white font-medium px-4 py-2 rounded-md text-sm hover:bg-vera-accent-hover transition-colors"
        >
          <Plus size={16} strokeWidth={1.5} />
          New workspace
        </button>
      </div>

      {/* Table */}
      <div className="bg-vera-surface border border-vera-border rounded" style={{ borderRadius: "6px" }}>
        {status === "loading" ? (
          <BlockSkeleton className="p-4" lines={4} />
        ) : status === "error" ? (
          <ErrorState error={error} onRetry={retry} />
        ) : (
          <WorkspaceTable workspaces={workspaces} onNew={() => setModalOpen(true)} />
        )}
      </div>

      {/* Modal */}
      <NewWorkspaceModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onCreated={handleCreated}
      />
    </div>
  );
}
