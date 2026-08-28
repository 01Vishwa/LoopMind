"use client";

import { useState, useRef, useEffect } from "react";
import { Eye, EyeOff, Copy, Check, X, RefreshCw, Trash2, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { copyText } from "@/lib/utils/clipboard";
import { isValidKeyFormat, maskKey, ProviderKind } from "@/lib/providers/keyFormat";
import { keyStore, modelsCache } from "@/lib/providers/keyStore";

type ConnectionStatus = "connected" | "invalid_key" | "unreachable" | "none";

interface ProviderKeyCardProps {
  id: ProviderKind;
  connectionId?: string; // If already connected, this is the DB row ID
  name: string;
  description: string;
  keyPrefix: string;
  docsUrl: string;
  icon: React.ReactNode;
  accentColor?: string;
  modelCount?: number;
  onConnected: () => void;
  onRemoved: () => void;
}

export function ProviderKeyCard({
  id,
  connectionId,
  name,
  description,
  keyPrefix,
  docsUrl,
  icon,
  accentColor = "var(--vera-accent)",
  modelCount,
  onConnected,
  onRemoved,
}: ProviderKeyCardProps) {
  const [rawKey, setRawKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [copied, setCopied] = useState(false);
  const [testing, setTesting] = useState(false);
  
  const [status, setStatus] = useState<ConnectionStatus>(connectionId ? "connected" : "none");
  const [copyFailed, setCopyFailed] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [editing, setEditing] = useState(false);
  
  const [formatError, setFormatError] = useState(false);

  const showTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setStatus(connectionId ? "connected" : "none");
  }, [connectionId]);

  // Auto re-mask after 10 s
  useEffect(() => {
    if (showKey) {
      showTimerRef.current = setTimeout(() => setShowKey(false), 10000);
    }
    return () => { if (showTimerRef.current) clearTimeout(showTimerRef.current); };
  }, [showKey]);

  const handleKeyChange = (val: string) => {
    setRawKey(val);
    if (val.trim()) {
      setFormatError(!isValidKeyFormat(id, val));
    } else {
      setFormatError(false);
    }
  };

  const handleSave = async () => {
    if (!rawKey.trim() || formatError) return;
    setTesting(true);
    
    try {
      // 1. Test key
      const testRes = await fetch("/api/providers/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind: id, api_key: rawKey.trim() })
      });
      const testData = await testRes.json();
      
      if (testData.status === "invalid_key") {
        setStatus("invalid_key");
        return;
      }
      if (testData.status === "provider_unreachable") {
        setStatus("unreachable");
        return;
      }
      if (testData.status === "invalid_format") {
        setFormatError(true);
        return;
      }
      
      // 2. Fetch models
      const modelsRes = await fetch("/api/providers/models", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind: id, api_key: rawKey.trim() })
      });
      const modelsData = await modelsRes.json();
      
      // 3. Register connection
      const regRes = await fetch("/api/providers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind: id, display_name: name })
      });
      
      if (!regRes.ok) {
        if (regRes.status === 409) {
          alert("You have reached the maximum number of connected providers.");
          return;
        }
        throw new Error("Failed to register");
      }
      
      const connData = await regRes.json();
      
      // 4. Save to keystore & cache
      await keyStore.save(connData.id, rawKey.trim());
      await modelsCache.save(connData.id, modelsData.models || []);
      
      setStatus("connected");
      setEditing(false);
      setRawKey("");
      onConnected();
      
    } catch (e) {
      console.error(e);
      setStatus("unreachable");
    } finally {
      setTesting(false);
    }
  };

  const handleCopy = async () => {
    if (!connectionId) return;
    const key = await keyStore.get(connectionId);
    if (!key) return;
    if (await copyText(key)) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } else {
      setCopyFailed(true);
      setTimeout(() => setCopyFailed(false), 2000);
    }
  };

  const handleRemove = async () => {
    if (!connectionId) return;
    
    await fetch(`/api/providers/${connectionId}`, { method: "DELETE" });
    await keyStore.delete(connectionId);
    await modelsCache.delete(connectionId);
    
    setStatus("none");
    setRemoving(false);
    setEditing(false);
    onRemoved();
  };

  const statusBadge = {
    connected: { label: `✓ Connected · ${modelCount || '?'} models`, icon: null, cls: "text-vera-ink" },
    invalid_key: { label: "✗ Invalid API key", icon: null, cls: "text-red-500" },
    unreachable: { label: `Couldn't reach ${name} right now.`, icon: null, cls: "text-amber-500" },
    none:  { label: "× No key", icon: null, cls: "text-vera-muted" },
  };
  
  // Real mask using the new function. Note: we need rawKey to show real key if editing.
  // Actually, we don't have the saved key in memory (it's in IDB). To show it, we would need to fetch it.
  // But requirement says: "never pre-filled with the real key, only the mask is ever displayed".
  // "masked format matches the uniform style sk-or-v1-x●●●●●●"
  // Wait, if it's connected and not editing, we just display the mask.
  const [displayKey, setDisplayKey] = useState("");
  useEffect(() => {
    if (connectionId && !editing) {
      if (showKey) {
        keyStore.get(connectionId).then(k => setDisplayKey(k || ""));
      } else {
        keyStore.get(connectionId).then(k => setDisplayKey(k ? maskKey(k) : ""));
      }
    }
  }, [connectionId, editing, showKey]);

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
          {statusBadge[status].label}
        </span>
      </div>

      {/* Body */}
      <div className="px-5 py-4 space-y-3 bg-vera-surface">
        {/* Key input / display */}
        {!connectionId || editing ? (
          <div className="flex flex-col gap-2">
            <div className="flex gap-2">
              <input
                type={showKey ? "text" : "password"}
                value={rawKey}
                onChange={(e) => handleKeyChange(e.target.value)}
                placeholder={`${keyPrefix}…`}
                className="vera-input font-mono text-xs flex-1"
                autoComplete="off"
                spellCheck={false}
              />
              <button
                onClick={handleSave}
                disabled={!rawKey.trim() || formatError || testing}
                className={cn(
                  "px-3 py-2 text-sm font-medium rounded-md transition-all",
                  rawKey.trim() && !formatError
                    ? "bg-vera-accent text-white hover:opacity-90"
                    : "bg-vera-border text-vera-muted cursor-not-allowed"
                )}
              >
                {testing ? "Testing…" : "Save"}
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
            {formatError && (
              <p className="text-xs text-red-500">Doesn't look like a valid {name} key</p>
            )}
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <code className="flex-1 px-3 py-2 text-xs font-mono bg-vera-border-subtle border border-vera-border rounded-md text-vera-ink truncate">
              {displayKey || "●●●●●●●●●●●●●●●"}
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

        {/* Actions row */}
        {connectionId && !editing && (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button
                onClick={() => { setEditing(true); setShowKey(false); setFormatError(false); }}
                className="px-3 py-1.5 text-xs font-medium rounded-md border border-vera-border text-vera-muted hover:text-vera-ink hover:bg-vera-border-subtle transition-all"
              >
                Change key
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
                <span className="text-vera-muted">Remove this key? Model assignments using {name} will need to be reconfigured.</span>
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
