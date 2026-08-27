"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowDown, Download } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import type { ArtifactRef } from "@/lib/schemas/runSchemas";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// Detect pandas/polars-style dataframe output
function isDataframeLike(text: string): boolean {
  return (text.includes("   ") && (text.includes("\n") && /\d+\s+\w/.test(text))) ||
    (text.includes("│") && text.includes("─"));
}

export interface ObservationPaneProps {
  output: string;
  artifacts?: ArtifactRef[];
  streaming?: boolean;
  stepLabel?: string;
  className?: string;
}

export function ObservationPane({
  output,
  artifacts = [],
  streaming,
  stepLabel,
  className,
}: ObservationPaneProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [showScrollBtn, setShowScrollBtn] = useState(false);

  // B2.4: only the newly-appended chunk is announced, not the whole buffer.
  const prevOutputRef = useRef("");
  const [liveDelta, setLiveDelta] = useState("");

  // Auto-scroll when new output arrives
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [output, autoScroll]);

  useEffect(() => {
    const prev = prevOutputRef.current;
    if (streaming && output.length > prev.length && output.startsWith(prev)) {
      setLiveDelta(output.slice(prev.length));
    } else if (!streaming) {
      setLiveDelta("");
    }
    prevOutputRef.current = output;
  }, [output, streaming]);

  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const isAtBottom = el.scrollHeight - el.scrollTop <= el.clientHeight + 40;
    setShowScrollBtn(!isAtBottom);
    if (isAtBottom) setAutoScroll(true);
    else setAutoScroll(false);
  };

  const scrollToBottom = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      setAutoScroll(true);
      setShowScrollBtn(false);
    }
  };

  const lines = output.split("\n");

  return (
    <div
      role="region"
      aria-label="Execution output"
      className={cn("flex flex-col h-full bg-vera-code-bg", className)}
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-white/10 bg-vera-code-bg shrink-0">
        <span className="text-mono-ui text-vera-code-fg/80 flex-1">
          {streaming ? "Executing…" : output ? `Output — ${stepLabel ?? "Step"}` : "Awaiting execution"}
        </span>
        {streaming && (
          <span className="w-1.5 h-1.5 rounded-full bg-vera-accent step-pulse" aria-hidden />
        )}
      </div>

      {/* Screen-reader log: announces only newly-appended lines while streaming */}
      <div className="sr-only" role="log" aria-live="polite" aria-atomic="false">
        {streaming ? liveDelta : ""}
      </div>

      {/* Terminal output */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-auto relative"
        aria-live="off"
      >
        {output ? (
          <div className="p-4">
            {isDataframeLike(output) ? (
              <DataframeRenderer text={output} />
            ) : (
              <pre
                className="text-code whitespace-pre-wrap break-words"
                style={{
                  fontSize: "13px",
                  lineHeight: "20px",
                  fontFamily: "'JetBrains Mono', 'Menlo', monospace",
                  color: "var(--vera-code-fg)",
                }}
              >
                {lines.map((line, i) => (
                  <TerminalLine key={i} line={line} />
                ))}
              </pre>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            {streaming ? (
              <OutputSkeleton />
            ) : (
              <p className="text-label text-vera-code-fg/40">
                {stepLabel ? "The script completed but produced no output." : "Awaiting execution"}
              </p>
            )}
          </div>
        )}

        {/* Stick-to-bottom button */}
        {showScrollBtn && (
          <button
            onClick={scrollToBottom}
            aria-label="Scroll to latest output"
            className="absolute bottom-4 right-4 flex items-center gap-1.5 px-3 py-1.5 bg-vera-accent text-white text-label rounded shadow-lg hover:bg-vera-accent-hover transition-colors"
            style={{ borderRadius: "4px" }}
          >
            <ArrowDown size={12} strokeWidth={1.5} />
            Latest
          </button>
        )}
      </div>

      {/* Artifact pills */}
      {artifacts.length > 0 && (
        <div className="flex flex-wrap gap-2 px-4 py-3 border-t border-white/10 bg-vera-code-bg">
          {artifacts.map((art) => (
            <a
              key={art.url}
              href={art.url}
              download={art.name}
              className="flex items-center gap-1.5 px-2.5 py-1 text-mono-ui text-vera-code-fg/70 border border-white/10 rounded hover:border-vera-accent hover:text-vera-accent transition-colors no-underline"
              style={{ borderRadius: "4px" }}
            >
              <Download size={11} strokeWidth={1.5} />
              {art.name}
              {art.sizeBytes && (
                <span className="text-vera-code-fg/40">{formatBytes(art.sizeBytes)}</span>
              )}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Terminal line — color stderr differently ────────────────────
function TerminalLine({ line }: { line: string }) {
  const isStderr =
    line.toLowerCase().startsWith("error") ||
    line.toLowerCase().startsWith("traceback") ||
    line.toLowerCase().startsWith("warning") ||
    line.startsWith("  File ");

  return (
    <span
      className={cn("block", isStderr ? "text-vera-insufficient" : "")}
      style={!isStderr ? { color: "var(--vera-code-fg)" } : undefined}
    >
      {line || " "}
    </span>
  );
}

// ── Simple dataframe renderer ────────────────────────────────
function DataframeRenderer({ text }: { text: string }) {
  // Try to parse a pandas-like repr into a table
  const lines = text.split("\n").filter(Boolean);

  const [headerLine, ...bodyLines] = lines;
  if (!headerLine) return null;
  const headerCells = headerLine.split(/\s{2,}/).map((cell) => cell.trim());

  return (
    <div className="overflow-x-auto" style={{ overflowX: "auto" }}>
      <table className="text-code border-collapse" style={{ fontSize: "12px", color: "var(--vera-code-fg)" }}>
        <thead>
          <tr className="border-b border-white/20 font-medium">
            {headerCells.map((cell, j) => (
              <th
                key={j}
                className="px-3 py-0.5 text-left whitespace-nowrap"
                style={{ whiteSpace: "nowrap", minWidth: "120px" }}
              >
                {cell}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {bodyLines.map((line, i) => (
            <tr key={i}>
              {line.split(/\s{2,}/).map((cell, j) => (
                <td key={j} className="px-3 py-0.5 text-left whitespace-nowrap" style={{ minWidth: "120px" }}>
                  {cell.trim()}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function OutputSkeleton() {
  return (
    <div className="p-4 space-y-2 w-full">
      {[90, 70, 85].map((w, i) => (
        <div key={i} className="h-4 rounded bg-white/10 shimmer" style={{ width: `${w}%` }} />
      ))}
    </div>
  );
}
