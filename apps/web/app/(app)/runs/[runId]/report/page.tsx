"use client";

import { Children, useState, type ReactNode } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Copy, ExternalLink } from "lucide-react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { Breadcrumbs } from "@/components/shared/Breadcrumbs";
import { CitationPopover } from "@/components/report/CitationPopover";
import { BlockSkeleton, ErrorState } from "@/components/shared/DataStates";
import { useResource } from "@/lib/data/useResource";
import { getRunReport } from "@/lib/data/report";
import { copyText } from "@/lib/utils/clipboard";

export default function ReportPage() {
  const params = useParams();
  const runId = params.runId as string;
  const [activeCitation, setActiveCitation] = useState<number | null>(null);
  const [copyState, setCopyState] = useState<"idle" | "ok" | "fail">("idle");

  const { data: report, status, error, retry } = useResource(
    () => getRunReport(runId),
    [runId],
  );

  const markdown = report?.markdown ?? "";
  const subQuestions = report?.subQuestions ?? [];

  const handleCopy = async () => {
    const ok = await copyText(markdown);
    setCopyState(ok ? "ok" : "fail");
    setTimeout(() => setCopyState("idle"), 2000);
  };

  const toggleCitation = (idx: number) =>
    setActiveCitation((cur) => (cur === idx ? null : idx));

  // Walk rendered children and turn any `[SQ-n]` token inside a text node into
  // an interactive citation trigger. Elements (bold, links, …) pass through so
  // citations nested in formatting still work.
  const withCitations = (children: ReactNode): ReactNode =>
    Children.map(children, (child) => {
      if (typeof child !== "string") return child;
      const parts = child.split(/(\[SQ-\d+\])/g);
      if (parts.length === 1) return child;
      return parts.map((part, i) => {
        const m = part.match(/^\[SQ-(\d+)\]$/);
        if (!m) return part;
        const idx = Number(m[1]);
        return (
          <button
            key={i}
            onClick={() => toggleCitation(idx)}
            className="text-vera-accent align-super text-xs font-medium hover:underline"
            aria-label={`Citation ${idx}: view sub-question`}
          >
            [{idx}]
          </button>
        );
      });
    });

  const components: Components = {
    h1: ({ children }) => (
      <h1
        className="text-display text-vera-ink mb-6"
        style={{ fontFamily: "'JetBrains Mono', monospace" }}
      >
        {withCitations(children)}
      </h1>
    ),
    h2: ({ children }) => (
      <h2 className="text-heading text-vera-ink mt-8 mb-3">{withCitations(children)}</h2>
    ),
    h3: ({ children }) => (
      <h3
        className="text-label font-medium text-vera-muted uppercase tracking-wider mt-6 mb-2"
        style={{ fontSize: "11px" }}
      >
        {withCitations(children)}
      </h3>
    ),
    p: ({ children }) => (
      <p className="text-body text-vera-ink mb-4 leading-relaxed">{withCitations(children)}</p>
    ),
    ul: ({ children }) => (
      <ul className="list-disc pl-6 space-y-1 text-body text-vera-ink my-3">{children}</ul>
    ),
    ol: ({ children }) => (
      <ol className="list-decimal pl-6 space-y-1 text-body text-vera-ink my-3">{children}</ol>
    ),
    li: ({ children }) => <li>{withCitations(children)}</li>,
    strong: ({ children }) => (
      <strong className="font-semibold text-vera-ink">{withCitations(children)}</strong>
    ),
    em: ({ children }) => <em className="italic">{withCitations(children)}</em>,
    a: ({ href, children }) => (
      <a
        href={href}
        target="_blank"
        rel="noreferrer"
        className="text-vera-accent hover:underline"
      >
        {children}
      </a>
    ),
    blockquote: ({ children }) => (
      <blockquote className="border-l-2 border-vera-border pl-4 text-vera-muted my-4">
        {children}
      </blockquote>
    ),
    code: ({ className, children }) => {
      const isBlock = /language-/.test(className ?? "");
      return isBlock ? (
        <code className={className}>{children}</code>
      ) : (
        <code className="text-mono-ui bg-vera-border-subtle px-1 py-0.5 rounded">{children}</code>
      );
    },
    pre: ({ children }) => (
      <pre
        className="text-code text-vera-code-fg bg-vera-code-bg rounded p-4 overflow-x-auto my-4"
        style={{ fontSize: "12px", borderRadius: "6px" }}
      >
        {children}
      </pre>
    ),
    table: ({ children }) => (
      <div className="overflow-x-auto my-4">
        <table className="w-full text-left text-label border-collapse">{children}</table>
      </div>
    ),
    th: ({ children }) => (
      <th className="table-header px-3 py-2 border-b border-vera-border">{children}</th>
    ),
    td: ({ children }) => (
      <td className="px-3 py-2 border-b border-vera-border-subtle text-vera-ink">
        {withCitations(children)}
      </td>
    ),
    hr: () => <hr className="my-6 border-vera-border" />,
  };

  const activeSQ = subQuestions.find((sq) => sq.index === activeCitation);

  return (
    <div className="px-6 py-6 max-w-[1440px] mx-auto">
      <Breadcrumbs
        segments={[
          { label: "Runs", href: "/runs" },
          { label: runId, href: `/runs/${runId}` },
          { label: "Report" },
        ]}
        className="mb-4"
      />

      {/* Sticky actions bar */}
      <div className="sticky top-0 z-10 flex items-center gap-3 py-3 bg-vera-paper border-b border-vera-border mb-8">
        <h1
          className="text-heading text-vera-ink flex-1"
          style={{ fontFamily: "'JetBrains Mono', monospace" }}
        >
          Research Report
        </h1>
        <button
          onClick={handleCopy}
          className="flex items-center gap-2 px-3 py-1.5 text-label font-medium text-vera-muted border border-vera-border rounded hover:bg-vera-border-subtle transition-colors"
          style={{ borderRadius: "4px" }}
        >
          <Copy size={13} strokeWidth={1.5} />
          {copyState === "ok" ? "Copied!" : copyState === "fail" ? "Copy failed" : "Copy as Markdown"}
        </button>
        <Link
          href={`/runs/${runId}/provenance`}
          className="flex items-center gap-2 px-3 py-1.5 text-label font-medium text-vera-muted border border-vera-border rounded hover:bg-vera-border-subtle transition-colors no-underline"
          style={{ borderRadius: "4px" }}
        >
          <ExternalLink size={13} strokeWidth={1.5} />
          View provenance
        </Link>
      </div>

      {/* Prose content */}
      <div className="max-w-[720px] mx-auto">
        {status === "loading" && <BlockSkeleton lines={6} />}
        {status === "error" && <ErrorState error={error} onRetry={retry} />}
        {status === "success" && markdown === "" && (
          <p className="text-body text-vera-muted">
            This run has not produced a report yet.
          </p>
        )}
        {status === "success" && markdown !== "" && (
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
            {markdown}
          </ReactMarkdown>
        )}

        {/* Citations index */}
        {subQuestions.length > 0 && (
          <div className="mt-12 pt-6 border-t border-vera-border">
            <h3
              className="text-label font-medium text-vera-muted uppercase tracking-wider mb-4"
              style={{ fontSize: "11px" }}
            >
              Sub-questions
            </h3>
            {subQuestions.map((sq) => (
              <div key={sq.index} className="flex items-start gap-3 mb-3">
                <button
                  onClick={() => toggleCitation(sq.index)}
                  className="text-mono-ui text-vera-accent font-medium mt-0.5 shrink-0 hover:underline"
                >
                  [{sq.index}]
                </button>
                <p className="text-label text-vera-muted">{sq.text}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Citation popover */}
      {activeSQ && (
        <CitationPopover
          subQuestion={activeSQ}
          onClose={() => setActiveCitation(null)}
        />
      )}
    </div>
  );
}
