import Link from "next/link";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils/cn";

export interface EmptyStateProps {
  illustration: ReactNode;
  title: string;
  subtitle: string;
  ctaLabel?: string;
  ctaHref?: string;
  className?: string;
}

export function EmptyState({ illustration, title, subtitle, ctaLabel, ctaHref, className }: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center py-20 px-6 text-center ${className ?? ""}`}>
      <div className="mb-5 text-vera-accent" aria-hidden>
        {illustration}
      </div>
      <p className="text-body text-vera-ink font-medium mb-1">{title}</p>
      <p className={cn("text-label text-vera-muted max-w-xs", ctaLabel && ctaHref ? "mb-6" : "")}>{subtitle}</p>
      {ctaLabel && ctaHref && (
        <Link
          href={ctaHref}
          className="px-4 py-2 bg-vera-accent text-white text-label font-medium rounded hover:bg-vera-accent-hover transition-colors no-underline"
          style={{ borderRadius: "6px" }}
        >
          {ctaLabel}
        </Link>
      )}
    </div>
  );
}

// ── Simple line-art illustrations, VERA brand style (indigo accent, thin stroke) ──

export function NoRunsIllustration() {
  return (
    <svg width="96" height="96" viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="48" cy="48" r="44" stroke="currentColor" strokeOpacity="0.15" strokeWidth="1.5" />
      {/* Document */}
      <rect x="30" y="24" width="36" height="46" rx="3" stroke="currentColor" strokeWidth="1.5" />
      <path d="M38 36h20M38 44h20M38 52h12" stroke="currentColor" strokeOpacity="0.55" strokeWidth="1.5" strokeLinecap="round" />
      {/* Magnifying glass with a sparkle to suggest "ask a question" */}
      <circle cx="63" cy="60" r="9" stroke="currentColor" strokeWidth="1.75" fill="var(--vera-surface, #fff)" />
      <path d="M69.5 66.5 76 73" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
      <path d="M63 56v8M59 60h8" stroke="currentColor" strokeOpacity="0.6" strokeWidth="1.25" strokeLinecap="round" />
    </svg>
  );
}

export function NoSavedAnalysesIllustration() {
  return (
    <svg width="96" height="96" viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="48" cy="48" r="44" stroke="currentColor" strokeOpacity="0.15" strokeWidth="1.5" />
      {/* Bookmark */}
      <path
        d="M36 22h24a3 3 0 0 1 3 3v42l-15-9-15 9V25a3 3 0 0 1 3-3Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      {/* Recurring/schedule clock badge */}
      <circle cx="66" cy="62" r="11" stroke="currentColor" strokeWidth="1.75" fill="var(--vera-surface, #fff)" />
      <path d="M66 56v6l4 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
