"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { Copy, Download, GitCompare, Code, Check } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { copyText } from "@/lib/utils/clipboard";
import { catppuccinMochaTheme } from "@/styles/monaco-theme";

// Monaco is lazy-loaded
const MonacoEditor = dynamic(
  () => import("@monaco-editor/react").then((m) => m.default),
  { ssr: false }
);
const MonacoDiffEditor = dynamic(
  () => import("@monaco-editor/react").then((m) => m.DiffEditor),
  { ssr: false }
);

export type CodeStatus = "executing" | "accepted" | "rejected" | "neutral";

export interface CodePaneProps {
  code: string;
  language?: string;
  diffFrom?: string | null;
  streaming?: boolean;
  stepLabel?: string;
  diffMode?: boolean;
  onToggleDiff?: () => void;
  status?: CodeStatus;
  className?: string;
}

export function CodePane({
  code,
  language = "python",
  diffFrom,
  streaming,
  stepLabel,
  diffMode,
  onToggleDiff,
  status = "neutral",
  className,
}: CodePaneProps) {
  const [copied, setCopied] = useState(false);
  const [copyFailed, setCopyFailed] = useState(false);

  const handleCopy = async () => {
    const ok = await copyText(code);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } else {
      setCopyFailed(true);
      setTimeout(() => setCopyFailed(false), 2000);
    }
  };

  const handleDownload = () => {
    const blob = new Blob([code], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `vera_script.${language === "python" ? "py" : language}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleEditorMount = (editor: any, monacoInstance: any) => {
    try {
      monacoInstance.editor.defineTheme("catppuccin-mocha", catppuccinMochaTheme);
      monacoInstance.editor.setTheme("catppuccin-mocha");
    } catch {
      // Monaco theme already registered
    }
  };

  // Status Colors Mapping
  const borderColors = {
    neutral: "border-vera-code-border",
    accepted: "border-vera-verified shadow-[0_0_0_1px_var(--vera-verified)]",
    executing: "border-vera-accent shadow-[0_0_0_1px_var(--vera-accent)]",
    rejected: "border-vera-insufficient shadow-[0_0_0_1px_var(--vera-insufficient)]",
  };
  
  const headerColors = {
    neutral: "bg-[#181825] border-vera-code-border/50",
    accepted: "bg-vera-verified-muted border-vera-verified/30 text-vera-verified",
    executing: "bg-vera-accent-muted border-vera-accent/30 text-vera-accent",
    rejected: "bg-vera-insufficient-muted border-vera-insufficient/30 text-vera-insufficient",
  };

  return (
    <div
      role="region"
      aria-label="Code editor"
      className={cn(
        "flex flex-col h-full bg-vera-code-bg rounded overflow-hidden transition-all duration-300", 
        borderColors[status],
        status !== "neutral" && "border",
        className
      )}
    >
      {/* Header bar */}
      <div className={cn("flex items-center gap-2 px-4 py-2.5 border-b shrink-0", headerColors[status])}>
        <Code size={14} strokeWidth={1.5} className="opacity-80" />
        <span className="text-mono-ui font-medium opacity-90 flex-1">
          {stepLabel ?? "Script"} — Python
          {streaming && (
            <span className="ml-2 text-vera-accent text-xs animate-pulse">executing…</span>
          )}
          {status === "accepted" && <span className="ml-2 text-xs opacity-80">(Verified)</span>}
          {status === "rejected" && <span className="ml-2 text-xs opacity-80">(Rejected)</span>}
        </span>

        {/* Actions — icon+text ghost buttons, grouped right-aligned */}
        <div className="flex items-center gap-2">
          {diffFrom !== undefined && diffFrom !== null && onToggleDiff && (
            <button
              onClick={onToggleDiff}
              aria-pressed={diffMode}
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1 text-mono-ui rounded transition-colors",
                diffMode
                  ? "bg-vera-accent/20 text-vera-accent"
                  : "opacity-60 hover:opacity-100 hover:bg-white/10"
              )}
              style={{ borderRadius: "4px" }}
              title="Toggle diff mode (Ctrl+Shift+D)"
            >
              <GitCompare size={12} strokeWidth={1.5} />
              {diffMode ? "Full" : "Diff"}
            </button>
          )}

          <button
            onClick={handleCopy}
            aria-label="Copy code"
            className={cn(
              "flex items-center gap-1.5 px-2.5 py-1 text-mono-ui rounded transition-colors",
              copyFailed
                ? "text-vera-insufficient opacity-100"
                : "opacity-60 hover:opacity-100 hover:bg-white/10"
            )}
            style={{ borderRadius: "4px" }}
          >
            {copied ? <Check size={12} strokeWidth={2} /> : <Copy size={12} strokeWidth={1.5} />}
            {copyFailed ? "Copy failed" : copied ? "Copied" : "Copy"}
          </button>

          <button
            onClick={handleDownload}
            aria-label="Download script"
            className="flex items-center gap-1.5 px-2.5 py-1 text-mono-ui opacity-60 hover:opacity-100 hover:bg-white/10 rounded transition-colors"
            style={{ borderRadius: "4px" }}
          >
            <Download size={12} strokeWidth={1.5} />
            .py
          </button>
        </div>
      </div>

      {/* Editor or Diff */}
      <div className="flex-1 overflow-hidden relative">
        {code ? (
          diffMode && diffFrom ? (
            <MonacoDiffEditor
              original={diffFrom}
              modified={code}
              language={language}
              theme="catppuccin-mocha"
              options={{
                readOnly: true,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                fontSize: 13,
                lineHeight: 20,
                fontFamily: "'JetBrains Mono', 'Menlo', monospace",
                renderOverviewRuler: false,
                renderSideBySide: false, // Inline diff view as requested
                padding: { top: 12, bottom: 12 },
              }}
              onMount={handleEditorMount}
              loading={<CodeSkeleton />}
            />
          ) : (
            <MonacoEditor
              value={code}
              language={language}
              theme="catppuccin-mocha"
              options={{
                readOnly: true,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                fontSize: 13,
                lineHeight: 20,
                fontFamily: "'JetBrains Mono', 'Menlo', monospace",
                fontLigatures: true,
                wordWrap: "on",
                overviewRulerLanes: 0,
                hideCursorInOverviewRuler: true,
                renderLineHighlight: "line",
                padding: { top: 12, bottom: 12 },
                scrollbar: { verticalScrollbarSize: 6, horizontalScrollbarSize: 6 },
                lineNumbersMinChars: 3,
              }}
              onMount={handleEditorMount}
              loading={<CodeSkeleton />}
            />
          )
        ) : (
          <div className="flex items-center justify-center h-full">
            {streaming ? (
              <CodeSkeleton />
            ) : (
              <p className="text-label text-vera-code-fg/40">Awaiting code generation…</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function CodeSkeleton() {
  return (
    <div className="p-4 space-y-2">
      {[75, 55, 90, 40, 80, 60, 45, 70].map((w, i) => (
        <div key={i} className="flex gap-4">
          <div className="w-8 h-4 rounded bg-white/10 shimmer shrink-0" />
          <div className="h-4 rounded bg-white/10 shimmer" style={{ width: `${w}%` }} />
        </div>
      ))}
    </div>
  );
}
