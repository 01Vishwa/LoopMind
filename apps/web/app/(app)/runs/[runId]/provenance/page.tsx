"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { Copy, Check, ChevronDown, ChevronUp } from "lucide-react";
import { Breadcrumbs } from "@/components/shared/Breadcrumbs";
import { BlockSkeleton, ErrorState } from "@/components/shared/DataStates";
import { useResource } from "@/lib/data/useResource";
import { getRunProvenance } from "@/lib/data/provenance";
import { copyText } from "@/lib/utils/clipboard";
import { cn } from "@/lib/utils/cn";

function CopyableText({ text, truncated }: { text: string; truncated?: boolean }) {
  const [state, setState] = useState<"idle" | "ok" | "fail">("idle");
  // Strip a "sha256:" prefix if present, then show the first 8 chars — a bare
  // hash is no longer mangled by a hard-coded slice offset.
  const bare = text.startsWith("sha256:") ? text.slice(7) : text;
  const display = truncated ? `${bare.slice(0, 8)}…${bare.slice(-4)}` : text;

  const handleCopy = async () => {
    const ok = await copyText(text);
    setState(ok ? "ok" : "fail");
    setTimeout(() => setState("idle"), 2000);
  };

  return (
    <span className="inline-flex items-center gap-1.5 group">
      <code className="text-mono-ui text-vera-ink bg-vera-border-subtle px-1.5 py-0.5 rounded">
        {display}
      </code>
      <button
        onClick={handleCopy}
        aria-label={state === "fail" ? "Copy failed" : "Copy"}
        className="text-vera-muted hover:text-vera-ink opacity-0 group-hover:opacity-100 transition"
      >
        {state === "ok" ? (
          <Check size={11} strokeWidth={1.5} className="text-vera-verified" />
        ) : state === "fail" ? (
          <span className="text-[10px] font-medium text-vera-insufficient">Failed</span>
        ) : (
          <Copy size={11} strokeWidth={1.5} />
        )}
      </button>
    </span>
  );
}

function ProvenanceCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-vera-surface border border-vera-border rounded" style={{ borderRadius: "6px" }}>
      <div className="px-5 py-3 border-b border-vera-border-subtle">
        <h2 className="text-label font-medium text-vera-muted uppercase tracking-wider" style={{ fontSize: "11px" }}>
          {title}
        </h2>
      </div>
      <div className="px-5 py-4">{children}</div>
    </div>
  );
}

export default function ProvenancePage() {
  const params = useParams();
  const runId = params.runId as string;
  const [expandedRounds, setExpandedRounds] = useState<Set<number>>(new Set());
  const [codeCopy, setCodeCopy] = useState<"idle" | "ok" | "fail">("idle");

  const { data: provenance, status, error, retry } = useResource(
    () => getRunProvenance(runId),
    [runId],
  );

  const toggleRound = (r: number) => {
    setExpandedRounds((prev) => {
      const next = new Set(prev);
      if (next.has(r)) next.delete(r); else next.add(r);
      return next;
    });
  };

  if (status === "error" || status === "loading" || !provenance) {
    return (
      <div className="px-6 py-6 max-w-[1440px] mx-auto">
        <Breadcrumbs
          segments={[
            { label: "Runs", href: "/runs" },
            { label: runId, href: `/runs/${runId}` },
            { label: "Provenance" },
          ]}
          className="mb-4"
        />
        <h1
          className="text-display text-vera-ink mb-6"
          style={{ fontFamily: "'JetBrains Mono', monospace" }}
        >
          Provenance
        </h1>
        <div className="max-w-[800px] space-y-4">
          {status === "error" ? (
            <ErrorState error={error} onRetry={retry} />
          ) : (
            <ProvenanceCard title="Query">
              <BlockSkeleton lines={4} />
            </ProvenanceCard>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="px-6 py-6 max-w-[1440px] mx-auto">
      <Breadcrumbs
        segments={[
          { label: "Runs", href: "/runs" },
          { label: runId, href: `/runs/${runId}` },
          { label: "Provenance" },
        ]}
        className="mb-4"
      />

      <h1
        className="text-display text-vera-ink mb-6"
        style={{ fontFamily: "'JetBrains Mono', monospace" }}
      >
        Provenance
      </h1>

      <div className="max-w-[800px] space-y-4">
        {/* Query */}
        <ProvenanceCard title="Query">
          <p className="text-body text-vera-ink">&ldquo;{provenance.query}&rdquo;</p>
        </ProvenanceCard>

        {/* Data snapshot */}
        <ProvenanceCard title="Data Snapshot">
          <table className="w-full text-left" aria-label="Files used">
            <thead>
              <tr className="border-b border-vera-border-subtle">
                <th className="table-header pb-2">File</th>
                <th className="table-header pb-2">Type</th>
                <th className="table-header pb-2">Size</th>
                <th className="table-header pb-2">sha256</th>
              </tr>
            </thead>
            <tbody>
              {provenance.files.map((f) => (
                <tr key={f.name} className="border-b border-vera-border-subtle last:border-0 hover:bg-vera-border-subtle/50 transition-colors">
                  <td className="py-2 text-label text-vera-ink font-medium">{f.name}</td>
                  <td className="py-2 text-label text-vera-muted">{f.kind}</td>
                  <td className={cn("py-2 text-label text-vera-muted", "tabular-nums")}>{(f.sizeBytes / 1024).toFixed(1)} KB</td>
                  <td className="py-2"><CopyableText text={f.sha256} truncated /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </ProvenanceCard>

        {/* Final script */}
        <ProvenanceCard title="Final Script">
          <div className="flex items-center justify-end mb-2">
            <button
              onClick={async () => {
                const ok = await copyText(provenance.finalScript);
                setCodeCopy(ok ? "ok" : "fail");
                setTimeout(() => setCodeCopy("idle"), 2000);
              }}
              className="flex items-center gap-1.5 text-label text-vera-muted hover:text-vera-ink"
            >
              {codeCopy === "ok" ? (
                <Check size={13} strokeWidth={1.5} className="text-vera-verified" />
              ) : (
                <Copy size={13} strokeWidth={1.5} />
              )}
              {codeCopy === "ok" ? "Copied!" : codeCopy === "fail" ? "Copy failed" : "Copy"}
            </button>
          </div>
          <pre
            className="text-code text-vera-code-fg bg-vera-code-bg rounded p-4 overflow-x-auto"
            style={{ fontSize: "12px", borderRadius: "6px" }}
          >
            {provenance.finalScript}
          </pre>
        </ProvenanceCard>

        {/* Answer */}
        <ProvenanceCard title="Answer">
          <pre
            className="text-code text-vera-code-fg bg-vera-code-bg rounded p-4 overflow-x-auto"
            style={{ fontSize: "12px", borderRadius: "6px" }}
          >
            {provenance.answer}
          </pre>
        </ProvenanceCard>

        {/* Trace */}
        <ProvenanceCard title="Trace">
          <div className="space-y-2">
            {provenance.rounds.map((round, i) => (
              <div key={i} className="border border-vera-border-subtle rounded" style={{ borderRadius: "4px" }}>
                <button
                  onClick={() => toggleRound(i)}
                  aria-expanded={expandedRounds.has(i)}
                  className="w-full flex items-center gap-3 px-3 py-2.5 text-left hover:bg-vera-border-subtle/50 transition-colors"
                >
                  {expandedRounds.has(i) ? <ChevronUp size={12} strokeWidth={1.5} className="text-vera-muted" /> : <ChevronDown size={12} strokeWidth={1.5} className="text-vera-muted" />}
                  <span className="text-label text-vera-muted">Round {round.round}</span>
                  <span className="text-label text-vera-ink font-medium flex-1">{round.step}</span>
                  <span className={cn(
                    "text-label font-medium px-2 py-0.5",
                    round.verdict === "sufficient" ? "text-vera-verified bg-vera-verified-muted" : "text-vera-insufficient bg-vera-insufficient-muted"
                  )} style={{ borderRadius: "2px" }}>
                    {round.verdict}
                  </span>
                </button>
                {expandedRounds.has(i) && (
                  <div className="px-4 pb-3 space-y-1 border-t border-vera-border-subtle">
                    <p className="text-label text-vera-muted mt-2">{round.reason}</p>
                    {round.action && (
                      <p className="text-label text-vera-accent">→ {round.action === "backtrack" ? "Backtracked" : "Added step"}</p>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </ProvenanceCard>

        {/* Models */}
        <ProvenanceCard title="Models">
          <table className="w-full text-left" aria-label="Agent invocations">
            <thead>
              <tr className="border-b border-vera-border-subtle">
                {["Agent", "Model", "Version", "Tokens in", "Tokens out", "Cost"].map((h) => (
                  <th key={h} className="table-header pb-2">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {provenance.models.map((m) => (
                <tr key={m.agent} className="border-b border-vera-border-subtle last:border-0 hover:bg-vera-border-subtle/50 transition-colors">
                  <td className="py-2 text-label text-vera-ink font-medium">{m.agent}</td>
                  <td className="py-2 text-mono-ui text-vera-muted">{m.model}</td>
                  <td className="py-2 text-mono-ui text-vera-muted">{m.promptVersion}</td>
                  <td className="py-2 text-mono-ui text-vera-muted">{m.tokensIn.toLocaleString()}</td>
                  <td className="py-2 text-mono-ui text-vera-muted">{m.tokensOut.toLocaleString()}</td>
                  <td className="py-2 text-mono-ui text-vera-muted">${m.costUsd.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ProvenanceCard>

        {/* Metadata */}
        <ProvenanceCard title="Metadata">
          <dl className="grid grid-cols-2 gap-x-8 gap-y-3 text-label">
            <div>
              <dt className="text-vera-muted">Run ID</dt>
              <dd className="text-vera-ink font-medium mt-0.5"><CopyableText text={provenance.metadata.runId} /></dd>
            </div>
            <div>
              <dt className="text-vera-muted">Trace ID</dt>
              <dd className="mt-0.5"><CopyableText text={provenance.metadata.traceId} truncated /></dd>
            </div>
            <div>
              <dt className="text-vera-muted">Started</dt>
              <dd className="text-vera-ink mt-0.5">{new Date(provenance.metadata.startedAt).toLocaleString()}</dd>
            </div>
            <div>
              <dt className="text-vera-muted">Finished</dt>
              <dd className="text-vera-ink mt-0.5">{new Date(provenance.metadata.finishedAt).toLocaleString()}</dd>
            </div>
            <div>
              <dt className="text-vera-muted">Total cost</dt>
              <dd className="text-vera-ink font-medium mt-0.5">${provenance.metadata.totalCostUsd.toFixed(2)}</dd>
            </div>
            <div>
              <dt className="text-vera-muted">Total tokens</dt>
              <dd className="text-vera-ink mt-0.5">{provenance.metadata.totalTokens.toLocaleString()}</dd>
            </div>
          </dl>
        </ProvenanceCard>
      </div>
    </div>
  );
}
