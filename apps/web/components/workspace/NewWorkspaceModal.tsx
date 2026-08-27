"use client";

import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { UploadDropzone } from "./UploadDropzone";
import { cn } from "@/lib/utils/cn";
import { STRINGS } from "@/lib/config/strings";

export interface NewWorkspaceModalProps {
  open: boolean;
  onClose: () => void;
  /**
   * Performs the create. Resolves once the workspace exists and any staged
   * files have been uploaded into it; rejects to keep the modal open with the
   * failure shown.
   */
  onCreated?: (name: string, description: string, files: File[]) => Promise<void> | void;
}

export function NewWorkspaceModal({ open, onClose, onCreated }: NewWorkspaceModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Files dropped before the workspace exists; uploaded once it does.
  const [stagedFiles, setStagedFiles] = useState<File[]>([]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) { setError("Name is required."); return; }
    setCreating(true);
    setError(null);
    try {
      await onCreated?.(name.trim(), description.trim(), stagedFiles);
      setName("");
      setDescription("");
      setStagedFiles([]);
      onClose();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not create workspace. Please try again.",
      );
    } finally {
      setCreating(false);
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={(next) => { if (!next) onClose(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-vera-ink/30 backdrop-blur-sm" />
        <Dialog.Content
          onOpenAutoFocus={(e) => {
            // Focus the name field rather than the close button.
            e.preventDefault();
            (e.currentTarget as HTMLElement)
              .querySelector<HTMLInputElement>("#ws-name")
              ?.focus();
          }}
          className="fixed left-1/2 top-1/2 z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 mx-4 bg-vera-surface border border-vera-border shadow-lg"
          style={{ borderRadius: "6px" }}
          aria-describedby={undefined}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-vera-border">
            <Dialog.Title className="text-heading text-vera-ink">
              New workspace
            </Dialog.Title>
            <Dialog.Close
              aria-label="Close"
              className="text-vera-muted hover:text-vera-ink transition-colors"
            >
              <X size={18} strokeWidth={1.5} />
            </Dialog.Close>
          </div>

          <form onSubmit={handleSubmit} className="px-6 py-5 space-y-5">
            {/* Name */}
            <div className="space-y-1.5">
              <label htmlFor="ws-name" className="text-label font-medium text-vera-ink">
                Name <span className="text-vera-insufficient">*</span>
              </label>
              <input
                id="ws-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={STRINGS.workspaceModal.namePlaceholder}
                required
                className={cn(
                  "w-full px-3 py-2 text-body text-vera-ink bg-vera-paper border border-vera-border rounded outline-none focus:border-vera-accent transition-colors",
                  error && !name.trim() ? "border-vera-insufficient" : ""
                )}
                style={{ borderRadius: "4px" }}
              />
            </div>

            {/* Description */}
            <div className="space-y-1.5">
              <label htmlFor="ws-desc" className="text-label font-medium text-vera-ink">
                Description <span className="text-vera-muted">(optional)</span>
              </label>
              <textarea
                id="ws-desc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder={STRINGS.workspaceModal.descriptionPlaceholder}
                rows={2}
                className="w-full px-3 py-2 text-body text-vera-ink bg-vera-paper border border-vera-border rounded outline-none focus:border-vera-accent transition-colors resize-none"
                style={{ borderRadius: "4px" }}
              />
            </div>

            {/* Upload */}
            <div className="space-y-1.5">
              <p className="text-label font-medium text-vera-ink">Files</p>
              <UploadDropzone onStaged={(files) => setStagedFiles((prev) => [...prev, ...files])} />
            </div>

            {error && (
              <p className="text-label text-vera-insufficient" role="alert">{error}</p>
            )}

            {/* Actions */}
            <div className="flex items-center justify-end gap-3 pt-1">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-label font-medium text-vera-muted hover:text-vera-ink border border-vera-border rounded hover:bg-vera-border-subtle transition-colors"
                style={{ borderRadius: "4px" }}
              >
                Cancel
              </button>
              <button
                id="create-workspace-btn"
                type="submit"
                disabled={creating}
                className="px-4 py-2 text-label font-medium text-white bg-vera-accent rounded hover:bg-vera-accent-hover disabled:opacity-60 transition-colors"
                style={{ borderRadius: "4px" }}
              >
                {creating ? "Creating…" : "Create workspace"}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
