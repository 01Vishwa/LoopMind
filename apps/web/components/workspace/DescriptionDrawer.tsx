"use client";

import { useState, useEffect, useCallback, useId } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X, Copy, Check, ChevronDown, ChevronUp, RefreshCw, AlertTriangle, FileCode2, GitCompare } from "lucide-react";
import { FileTypeBadge } from "@/components/shared/FileTypeBadge";
import { cn } from "@/lib/utils/cn";
import { truncateHash } from "@/lib/utils/truncate";
import { copyText } from "@/lib/utils/clipboard";
import { formatBytes } from "@/lib/utils/formatBytes";
import { useResource } from "@/lib/data/useResource";
import {
  getFileDescription,
  reanalyzeFile,
  type FileDescription,
  type SchemaColumn,
} from "@/lib/data/fileDescriptions";
import type { WorkspaceFile } from "@/lib/schemas/runSchemas";

export interface DescriptionDrawerProps {
  workspaceId: string;
  file: WorkspaceFile | null;
  onClose: () => void;
}

export function DescriptionDrawer({ workspaceId, file, onClose }: DescriptionDrawerProps) {
  const [copied, setCopied] = useState(false);
  const [scriptCopied, setScriptCopied] = useState(false);
  const tabIdBase = useId();

  // Raw output starts expanded while the file is still pending analysis.
  const [rawExpanded, setRawExpanded] = useState(false);
  const [activeSheet, setActiveSheet] = useState(0);

  const { data: fetched, status } = useResource(
    () =>
      file
        ? getFileDescription(workspaceId, file.id)
        : Promise.resolve(null as FileDescription | null),
    [workspaceId, file?.id],
  );

  // Local copy so "Re-analyze" can swap in the refreshed description.
  const [description, setDescription] = useState<FileDescription | null>(null);
  const [reanalyzing, setReanalyzing] = useState(false);
  useEffect(() => {
    setDescription(fetched ?? null);
    setActiveSheet(0);
  }, [fetched]);

  useEffect(() => {
    if (file) setRawExpanded(file.status === "pending");
  }, [file]);

  const handleReanalyze = useCallback(async () => {
    if (!file) return;
    setReanalyzing(true);
    try {
      setDescription(await reanalyzeFile(workspaceId, file.id));
    } catch {
      // Keep the description already on screen rather than blanking the drawer.
    } finally {
      setReanalyzing(false);
    }
  }, [workspaceId, file]);

  const copyHash = async () => {
    if (file?.contentSha256 && (await copyText(file.contentSha256))) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const copyScript = async () => {
    if (await copyText(description?.analyzerScript ?? "")) {
      setScriptCopied(true);
      setTimeout(() => setScriptCopied(false), 2000);
    }
  };

  if (!file) return null;

  // "validating" is the in-flight state; afterwards the server reports whether
  // the analyzer script actually ran.
  const scriptStatus: "validating" | "verified" | "error" =
    status === "loading" || reanalyzing ? "validating" : description?.scriptStatus ?? "error";

  // The analyzer flags suspect columns; the table never infers them itself.
  const hasTypeMismatch = (col: SchemaColumn) => Boolean(col.warning);

  const sheets = description?.sheets;

  return (
    <Dialog.Root open onOpenChange={(next) => { if (!next) onClose(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-vera-ink/20 backdrop-blur-[1px]" />
        <Dialog.Content
          aria-describedby={undefined}
          className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-[500px] bg-vera-surface border-l border-vera-border flex flex-col shadow-2xl overflow-hidden focus:outline-none"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-vera-border shrink-0 bg-vera-surface">
            <div className="flex items-center gap-3 min-w-0">
              <FileTypeBadge kind={file.kind} />
              <Dialog.Title className="text-body font-medium text-vera-ink truncate">{file.name}</Dialog.Title>
            </div>
            <Dialog.Close
              aria-label="Close drawer"
              className="p-1.5 text-vera-muted hover:text-vera-ink hover:bg-vera-border-subtle rounded transition-colors shrink-0 ml-2"
            >
              <X size={18} strokeWidth={1.5} />
            </Dialog.Close>
          </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto bg-vera-paper pb-8">
          {/* File meta */}
          <div className="px-5 py-4 border-b border-vera-border-subtle bg-vera-surface">
            <div className="flex items-center gap-6 text-label text-vera-muted">
              <span>{formatBytes(file.sizeBytes)}</span>
            </div>
            {file.contentSha256 && (
              <div className="flex items-center gap-2 mt-2">
                <span className="text-label text-vera-muted">sha256:</span>
                <code className="text-mono-ui text-vera-ink bg-vera-paper border border-vera-border px-2 py-0.5 rounded">
                  {truncateHash(file.contentSha256)}
                </code>
                <button
                  onClick={copyHash}
                  aria-label="Copy hash"
                  className="text-vera-muted hover:text-vera-ink transition-colors"
                >
                  {copied ? (
                    <Check size={12} strokeWidth={2} className="text-vera-verified" />
                  ) : (
                    <Copy size={12} strokeWidth={1.5} />
                  )}
                </button>
              </div>
            )}
            <button
              onClick={handleReanalyze}
              disabled={reanalyzing}
              aria-label="Re-analyze file"
              title="Run the Data File Analyzer again on this file."
              className="flex items-center gap-1.5 mt-3 px-2.5 py-1.5 text-label font-medium text-vera-subtle border border-vera-border hover:text-vera-ink hover:bg-vera-border-subtle rounded transition-colors"
            >
              <RefreshCw size={13} strokeWidth={1.5} className={reanalyzing ? "animate-spin" : ""} />
              Re-analyze
            </button>
          </div>

          {/* Sheet tabs (XLSX only) */}
          {sheets && (
            <div
              className="px-5 pt-4 bg-vera-surface border-b border-vera-border-subtle flex gap-2 overflow-x-auto"
              role="tablist"
              aria-label="Workbook sheets"
            >
              {sheets.map((sheet, i) => (
                <button
                  key={sheet}
                  role="tab"
                  id={`${tabIdBase}-tab-${i}`}
                  aria-selected={activeSheet === i}
                  aria-controls={`${tabIdBase}-panel-${i}`}
                  tabIndex={activeSheet === i ? 0 : -1}
                  onClick={() => setActiveSheet(i)}
                  className={cn(
                    "px-3 py-2 text-sm transition-colors border-b-2 font-medium whitespace-nowrap",
                    activeSheet === i
                      ? "border-vera-accent text-vera-accent"
                      : "border-transparent text-vera-muted hover:text-vera-ink hover:border-vera-border-strong"
                  )}
                >
                  {sheet}
                </button>
              ))}
            </div>
          )}

          {/* Schema table */}
          <div
            className="px-5 py-5 bg-vera-surface"
            {...(sheets
              ? {
                  role: "tabpanel",
                  id: `${tabIdBase}-panel-${activeSheet}`,
                  "aria-labelledby": `${tabIdBase}-tab-${activeSheet}`,
                }
              : {})}
          >
            <h3 className="text-label font-medium text-vera-subtle mb-3 uppercase tracking-wider" style={{ fontSize: "11px" }}>
              Schema Definition
            </h3>
            <div className="vera-card overflow-hidden">
              <table className="vera-table w-full text-left" aria-label="File schema">
                <thead className="bg-vera-paper">
                  <tr>
                    <th className="py-2.5 px-3">Column</th>
                    <th className="py-2.5 px-3">Type</th>
                    <th className="py-2.5 px-3">Samples</th>
                  </tr>
                </thead>
                <tbody>
                  {(description?.schema ?? []).map((col) => {
                    const mismatch = hasTypeMismatch(col);
                    return (
                      <tr key={col.name} className="group/col border-b border-vera-border-subtle last:border-0 hover:bg-vera-border-subtle/50">
                        <td className="py-2.5 px-3 text-mono-ui font-medium text-vera-ink whitespace-nowrap">{col.name}</td>
                        <td className="py-2.5 px-3">
                          <div className="flex items-center gap-1.5">
                            <span className={cn("text-label", mismatch ? "text-vera-warning font-medium" : "text-vera-muted")}>
                              {col.type}
                            </span>
                            {mismatch && (
                              <span className="inline-flex cursor-help" title={col.warning}>
                                <AlertTriangle
                                  size={12}
                                  strokeWidth={2}
                                  className="text-vera-warning"
                                  aria-label="Type mismatch warning"
                                />
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-2.5 px-3 text-label text-vera-muted truncate max-w-[200px]" title={col.samples.join(", ")}>
                          {col.samples.join(", ")}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Analyzer script */}
          <div className="px-5 py-5 border-t border-vera-border-subtle bg-vera-surface">
            <div className="flex items-center gap-2 mb-3">
              <h3 className="text-label font-medium text-vera-subtle uppercase tracking-wider" style={{ fontSize: "11px" }}>
                Analyzer Script
              </h3>

              {scriptStatus === "verified" && (
                <span className="flex items-center gap-1.5 text-[11px] font-medium text-vera-verified animate-fade-in">
                  <span className="text-vera-border" aria-hidden>·</span>
                  <span className="w-1.5 h-1.5 rounded-full bg-vera-verified inline-block" aria-hidden />
                  Executed successfully
                </span>
              )}

              {scriptStatus === "error" && (
                <div className="ml-auto flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-vera-insufficient-muted text-vera-insufficient border border-vera-insufficient/20 text-[11px] font-medium animate-fade-in">
                  <AlertTriangle size={11} strokeWidth={2} aria-hidden />
                  Script error — regenerating
                </div>
              )}
            </div>

            <div className="relative group rounded bg-vera-code-bg border border-vera-code-border overflow-hidden shadow-sm">
              {/* Action Row */}
              <div className="flex items-center justify-end gap-1 p-1 border-b border-vera-code-border/50 bg-[#181825]">
                <button className="flex items-center gap-1 px-2 py-1 text-[11px] font-medium text-vera-muted hover:text-vera-code-fg hover:bg-white/5 rounded transition-colors">
                  <GitCompare size={12} strokeWidth={1.5} />
                  Diff
                </button>
                <button
                  onClick={copyScript}
                  className="flex items-center gap-1 px-2 py-1 text-[11px] font-medium text-vera-muted hover:text-vera-code-fg hover:bg-white/5 rounded transition-colors"
                >
                  {scriptCopied ? <Check size={12} strokeWidth={2} className="text-vera-verified" /> : <Copy size={12} strokeWidth={1.5} />}
                  {scriptCopied ? "Copied" : "Copy"}
                </button>
                <div className="flex items-center gap-1 px-2 py-1 text-[11px] font-mono text-vera-accent ml-2 border-l border-vera-code-border/50 pl-3">
                  <FileCode2 size={12} strokeWidth={1.5} />
                  .py
                </div>
              </div>

              {/* Code */}
              <div className="relative p-4 overflow-x-auto">
                <pre className={cn("text-code text-vera-code-fg transition-opacity duration-300", scriptStatus === "error" && "opacity-30 blur-[1px]")} style={{ fontSize: "12px" }}>
                  {description?.analyzerScript ?? ""}
                </pre>
              </div>
            </div>
          </div>

          {/* Raw output */}
          <div className="px-5 py-5 border-t border-vera-border-subtle bg-vera-surface">
            <button
              onClick={() => setRawExpanded((v) => !v)}
              className="flex items-center gap-2 text-label font-medium text-vera-muted hover:text-vera-ink transition-colors mb-2 w-full text-left"
              aria-expanded={rawExpanded}
            >
              {rawExpanded ? <ChevronUp size={14} strokeWidth={2} className="text-vera-ink" /> : <ChevronDown size={14} strokeWidth={2} />}
              Raw Description Output
            </button>
            {rawExpanded && (
              <div className="relative rounded bg-vera-code-bg border border-vera-code-border mt-3 overflow-hidden shadow-sm animate-slide-up">
                <div className="flex items-center px-3 py-1.5 border-b border-vera-code-border/50 bg-[#181825] text-[10px] font-mono text-vera-muted uppercase tracking-wider">
                  stdout
                </div>
                <div className="p-4 overflow-x-auto">
                  <pre className="text-code text-vera-code-fg opacity-90" style={{ fontSize: "12px" }}>
                    {description?.rawOutput ?? ""}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
