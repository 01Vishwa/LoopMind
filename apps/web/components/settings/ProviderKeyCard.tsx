"use client";

import { useState, useRef, useEffect } from "react";
import { Eye, EyeOff, Copy, Check, X, RefreshCw, Trash2, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { copyText } from "@/lib/utils/clipboard";

type ConnectionStatus = "saved" | "none";

interface ProviderKeyCardProps {
  name: string;
  description: string;
  /** Prefix shown in the masked key placeholder, e.g. "sk-or-v1-" */
  keyPrefix: string;
  docsUrl: string;
  /** SVG string or emoji to show as provider logo */
  icon: React.ReactNode;
  /** Accent colour for the provider badge */
  accentColor?: string;
}

const MASK_SUFFIX = "●●●●●●●●●●●●●●●●●●●●●●●●●●●●";

export function ProviderKeyCard({
  name,
  description,
  keyPrefix,
  docsUrl,
  icon,
  accentColor = "var(--vera-accent)",
}: ProviderKeyCardProps) {
  const [rawKey, setRawKey]         = useState("");
  const [savedKey, setSavedKey]     = useState("");
  const [showKey, setShowKey]       = useState(false);
  const [copied, setCopied]         = useState(false);
  const [testing, setTesting]       = useState(false);
  const [status, setStatus]         = useState<ConnectionStatus>("none");
  const [testNote, setTestNote]     = useState<string | null>(null);
  const [copyFailed, setCopyFailed] = useState(false);
  const [removing, setRemoving]     = useState(false);
  const [editing, setEditing]       = useState(false);
  const showTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Auto re-mask after 10 s
  useEffect(() => {
    if (showKey) {
      showTimerRef.current = setTimeout(() => setShowKey(false), 10000);
    }
    return () => { if (showTimerRef.current) clearTimeout(showTimerRef.current); };
  }, [showKey]);

  const maskedDisplay = savedKey
    ? `${keyPrefix}${MASK_SUFFIX}`
    : "";

  const displayValue = showKey ? (savedKey || rawKey) : maskedDisplay;

  const handleSave = async () => {
    if (!rawKey.trim()) return;
    setSavedKey(rawKey.trim());
    setStatus("saved");
    setTestNote(null);
    setEditing(false);
    setRawKey("");
  };

  const handleCopy = async () => {
    if (!savedKey) return;
    if (await copyText(savedKey)) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } else {
      setCopyFailed(true);
      setTimeout(() => setCopyFailed(false), 2000);
    }
  };

  // NOT YET WIRED: there is no backend endpoint to validate a provider key.
  // This deliberately does not fake a "Connected" success state — it only
  // acknowledges that the check is unavailable (review A5.4).
  const handleTest = async () => {
    setTesting(true);
    await new Promise((r) => setTimeout(r, 600));
    setTestNote("Connection testing isn’t available yet — the key is stored but unverified.");
    setTesting(false);
  };

  const handleRemove = () => {
    setSavedKey("");
    setStatus("none");
    setTestNote(null);
    setRemoving(false);
    setEditing(false);
  };

  const statusBadge: Record<ConnectionStatus, { label: string; icon: React.ReactNode; cls: string }> = {
    saved: { label: "Key saved (unverified)", icon: <Check size={12} strokeWidth={2} />, cls: "text-vera-muted" },
    none:  { label: "No key",                 icon: <X size={12} strokeWidth={2} />,     cls: "text-vera-muted" },
  };

  return (
    <div className="border border-vera-border rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-start justify-between px-5 py-4 border-b border-vera-border bg-vera-surface">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{icon}</span>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-vera-ink">{name}</h3>
              <a
                href={docsUrl}
                target="_blank"
                rel="noreferrer"
                className="text-vera-muted hover:text-vera-accent transition-colors"
                title={`${name} documentation`}
              >
                <ExternalLink size={12} strokeWidth={1.5} />
              </a>
            </div>
            <p className="text-xs text-vera-muted mt-0.5">{description}</p>
          </div>
        </div>

        {/* Status */}
        <span className={cn("flex items-center gap-1 text-xs font-medium", statusBadge[status].cls)}>
          {statusBadge[status].icon}
          {statusBadge[status].label}
        </span>
      </div>

      {/* Body */}
      <div className="px-5 py-4 space-y-3 bg-vera-surface">
        {/* Key input / display */}
        {!savedKey || editing ? (
          <div className="flex gap-2">
            <input
              type={showKey ? "text" : "password"}
              value={rawKey}
              onChange={(e) => setRawKey(e.target.value)}
              placeholder={`${keyPrefix}…`}
              className="vera-input font-mono text-xs flex-1"
              autoComplete="off"
              spellCheck={false}
            />
            <button
              onClick={handleSave}
              disabled={!rawKey.trim()}
              className={cn(
                "px-3 py-2 text-sm font-medium rounded-md transition-all",
                rawKey.trim()
                  ? "bg-vera-accent text-white hover:opacity-90"
                  : "bg-vera-border text-vera-muted cursor-not-allowed"
              )}
            >
              Save
            </button>
            {editing && (
              <button
                onClick={() => { setEditing(false); setRawKey(""); }}
                className="px-3 py-2 text-sm text-vera-muted border border-vera-border rounded-md hover:bg-vera-border-subtle"
              >
                Cancel
              </button>
            )}
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <code className="flex-1 px-3 py-2 text-xs font-mono bg-vera-border-subtle border border-vera-border rounded-md text-vera-ink truncate">
              {displayValue || maskedDisplay}
            </code>

            {/* Show / Hide */}
            <button
              onClick={() => setShowKey((v) => !v)}
              className="p-2 rounded-md text-vera-muted hover:text-vera-ink hover:bg-vera-border-subtle transition-colors"
              title={showKey ? "Hide key" : "Show key (10s)"}
            >
              {showKey ? <EyeOff size={14} strokeWidth={1.5} /> : <Eye size={14} strokeWidth={1.5} />}
            </button>

            {/* Copy */}
            <button
              onClick={handleCopy}
              className={cn(
                "p-2 rounded-md transition-colors",
                copyFailed
                  ? "text-vera-insufficient"
                  : "text-vera-muted hover:text-vera-ink hover:bg-vera-border-subtle"
              )}
              title={copyFailed ? "Copy failed" : "Copy to clipboard"}
              aria-label={copyFailed ? "Copy failed" : "Copy to clipboard"}
            >
              {copyFailed ? <X size={14} strokeWidth={2} /> : copied ? <Check size={14} strokeWidth={2} className="text-vera-verified" /> : <Copy size={14} strokeWidth={1.5} />}
            </button>
          </div>
        )}

        {testNote && (
          <p className="text-xs text-vera-muted" role="status">{testNote}</p>
        )}

        {/* Actions row */}
        {savedKey && !editing && (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {/* Test connection */}
              <button
                onClick={handleTest}
                disabled={testing}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border transition-all",
                  "border-vera-border text-vera-muted hover:text-vera-ink hover:bg-vera-border-subtle"
                )}
              >
                <RefreshCw size={12} strokeWidth={1.75} className={testing ? "animate-spin" : ""} />
                {testing ? "Testing…" : "Test connection"}
              </button>

              {/* Edit key */}
              <button
                onClick={() => { setEditing(true); setShowKey(false); }}
                className="px-3 py-1.5 text-xs font-medium rounded-md border border-vera-border text-vera-muted hover:text-vera-ink hover:bg-vera-border-subtle transition-all"
              >
                Replace key
              </button>
            </div>

            {/* Remove */}
            {!removing ? (
              <button
                onClick={() => setRemoving(true)}
                className="flex items-center gap-1 text-xs text-vera-muted hover:text-vera-insufficient transition-colors"
              >
                <Trash2 size={12} strokeWidth={1.5} />
                Remove
              </button>
            ) : (
              <div className="flex items-center gap-2 text-xs">
                <span className="text-vera-muted">Remove this key?</span>
                <button onClick={handleRemove} className="font-medium text-vera-insufficient hover:underline">
                  Remove
                </button>
                <span className="text-vera-border">|</span>
                <button onClick={() => setRemoving(false)} className="font-medium text-vera-ink hover:underline">
                  Cancel
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
