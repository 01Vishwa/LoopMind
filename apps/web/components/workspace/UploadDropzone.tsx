"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, X, CheckCircle, AlertCircle, HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { FileTypeBadge } from "@/components/shared/FileTypeBadge";
import { toDropzoneAccept, formatSupportedFormats, kindFromFilename } from "@/lib/config/fileTypes";
import { uploadWorkspaceFile } from "@/lib/data/workspaceFiles";
import type { WorkspaceFile } from "@/lib/schemas/runSchemas";

const ACCEPTED_TYPES = toDropzoneAccept();

const extToKind = kindFromFilename;

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface FileEntry {
  file: File;
  progress: number; // 0–100
  status: "queued" | "uploading" | "done" | "error";
  error?: string;
}

const SUPPORTED_FORMATS = formatSupportedFormats();

export interface UploadDropzoneProps {
  /**
   * Target workspace. Omit when the workspace does not exist yet (the New
   * Workspace modal): files are then staged and reported via `onStaged` for the
   * caller to upload once it does.
   */
  workspaceId?: string;
  /** Receives the persisted records the server created for the upload. */
  onUploaded?: (files: WorkspaceFile[]) => void;
  /** Receives staged files when there is no `workspaceId` to upload into yet. */
  onStaged?: (files: File[]) => void;
  /** Compact single-line dropzone for workspaces that already have files. */
  compact?: boolean;
}

export function UploadDropzone({ workspaceId, onUploaded, onStaged, compact }: UploadDropzoneProps) {
  const [entries, setEntries] = useState<FileEntry[]>([]);

  const upload = useCallback(
    async (file: File, index: number) => {
      const patch = (entry: Partial<FileEntry>) =>
        setEntries((prev) => prev.map((e, i) => (i === index ? { ...e, ...entry } : e)));

      if (!workspaceId) {
        // Nothing to upload into yet — hold the file for the caller.
        patch({ progress: 0, status: "queued" });
        return;
      }

      try {
        const uploaded = await uploadWorkspaceFile(workspaceId, file, (progress) =>
          patch({ progress, status: "uploading" }),
        );
        patch({ progress: 100, status: "done" });
        onUploaded?.([uploaded]);
      } catch (err) {
        patch({
          status: "error",
          error: err instanceof Error ? err.message : String(err),
        });
      }
    },
    [workspaceId, onUploaded],
  );

  const onDrop = useCallback((accepted: File[]) => {
    setEntries((prev) => {
      const startIndex = prev.length;
      const newEntries: FileEntry[] = accepted.map((f) => ({
        file: f,
        progress: 0,
        status: "queued",
      }));
      accepted.forEach((f, i) => void upload(f, startIndex + i));
      return [...prev, ...newEntries];
    });
    if (!workspaceId) onStaged?.(accepted);
  }, [upload, workspaceId, onStaged]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    multiple: true,
  });

  const removeEntry = (index: number) => {
    setEntries((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-3">
      {compact ? (
        <div
          {...getRootProps()}
          className={cn(
            "flex items-center justify-center gap-2 border-2 border-dashed rounded px-4 h-12 cursor-pointer transition-colors",
            isDragActive
              ? "border-vera-accent bg-vera-accent-muted"
              : "border-vera-border hover:border-vera-accent hover:bg-vera-accent-muted/30"
          )}
          style={{ borderRadius: "6px" }}
          aria-label="File upload dropzone"
        >
          <input {...getInputProps()} />
          <Upload
            size={14}
            strokeWidth={1.5}
            className={cn("shrink-0", isDragActive ? "text-vera-accent" : "text-vera-muted")}
          />
          <span className="text-label text-vera-muted">
            {isDragActive ? "Drop files here" : "Drop files here or click to browse"}
          </span>
          <span
            className="text-vera-muted hover:text-vera-ink transition-colors shrink-0"
            title={`Supported formats: ${SUPPORTED_FORMATS}`}
          >
            <HelpCircle size={13} strokeWidth={1.5} />
          </span>
        </div>
      ) : (
        <div
          {...getRootProps()}
          className={cn(
            "border-2 border-dashed rounded px-6 py-8 text-center cursor-pointer transition-colors",
            isDragActive
              ? "border-vera-accent bg-vera-accent-muted"
              : "border-vera-border hover:border-vera-accent hover:bg-vera-accent-muted/30"
          )}
          style={{ borderRadius: "6px" }}
          aria-label="File upload dropzone"
        >
          <input {...getInputProps()} />
          <Upload
            size={24}
            strokeWidth={1.5}
            className={cn("mx-auto mb-3", isDragActive ? "text-vera-accent" : "text-vera-muted")}
          />
          <p className="text-body text-vera-ink">
            {isDragActive ? "Drop files here" : "Drop files here or click to browse"}
          </p>
          <p className="text-label text-vera-muted mt-1">{SUPPORTED_FORMATS}</p>
        </div>
      )}

      {entries.length > 0 && (
        <div className="space-y-2">
          {entries.map((entry, i) => (
            <div
              key={i}
              className="px-3 py-2 border border-vera-border rounded bg-vera-surface"
              style={{ borderRadius: "4px" }}
            >
              <div className="flex items-center gap-3">
                <FileTypeBadge kind={extToKind(entry.file.name)} />
                <span className="text-label text-vera-ink flex-1 truncate">{entry.file.name}</span>
                <span className="text-label text-vera-muted shrink-0">{formatBytes(entry.file.size)}</span>

                {/* Progress / status */}
                {entry.status === "uploading" && (
                  <div className="w-20 h-1.5 bg-vera-border rounded-full overflow-hidden shrink-0">
                    <div
                      className="h-full bg-vera-accent transition-all"
                      style={{ width: `${entry.progress}%` }}
                    />
                  </div>
                )}
                {entry.status === "done" && (
                  <CheckCircle size={14} strokeWidth={1.5} className="text-vera-verified shrink-0" aria-label="Uploaded" />
                )}
                {entry.status === "error" && (
                  <AlertCircle size={14} strokeWidth={1.5} className="text-vera-insufficient shrink-0" aria-hidden />
                )}

                <button
                  onClick={() => removeEntry(i)}
                  aria-label={`Remove ${entry.file.name}`}
                  className="text-vera-muted hover:text-vera-ink transition-colors shrink-0"
                >
                  <X size={14} strokeWidth={1.5} />
                </button>
              </div>

              {entry.status === "error" && (
                <p role="alert" className="text-label text-vera-insufficient mt-1.5">
                  {entry.error ?? "Upload failed. Please try again."}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
