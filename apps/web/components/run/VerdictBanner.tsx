"use client";

import { useEffect, useRef } from "react";
import { Check, X, RotateCcw, Plus } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import type { Verdict, BacktrackEvent } from "@/lib/schemas/runSchemas";

export interface VerdictBannerProps {
  verdict: Verdict | null;
  routerAction?: "add_step" | "backtrack";
  backtrackEvent?: BacktrackEvent | null;
  className?: string;
}

export function VerdictBanner({ verdict, routerAction, backtrackEvent, className }: VerdictBannerProps) {
  const bannerRef = useRef<HTMLDivElement>(null);
  const hasShaken = useRef(false);

  // Shake animation on FIRST insufficient verdict only.
  // Respects prefers-reduced-motion per spec §11.4 — reduced-motion users
  // get the instant state change with no shake.
  useEffect(() => {
    if (!verdict || verdict.sufficient || hasShaken.current) return;
    hasShaken.current = true;
    const el = bannerRef.current;
    if (!el) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    el.animate(
      [
        { transform: "translateX(0)" },
        { transform: "translateX(-2px)" },
        { transform: "translateX(2px)" },
        { transform: "translateX(-2px)" },
        { transform: "translateX(2px)" },
        { transform: "translateX(0)" },
      ],
      { duration: 250, easing: "ease-in-out" }
    );
  }, [verdict]);

  if (!verdict) return null;

  return (
    <div
      ref={bannerRef}
      role="status"
      aria-live="polite"
      aria-label={verdict.sufficient ? "Verification sufficient" : "Verification insufficient"}
      className={cn(
        "border-l-4 px-5 py-3 animate-slide-up",
        verdict.sufficient
          ? "border-vera-verified bg-vera-verified-muted"
          : "border-vera-insufficient bg-vera-insufficient-muted",
        className
      )}
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div
          className={cn(
            "w-5 h-5 rounded-full flex items-center justify-center shrink-0 mt-0.5",
            verdict.sufficient ? "bg-vera-verified" : "bg-vera-insufficient"
          )}
        >
          {verdict.sufficient ? (
            <Check size={12} strokeWidth={2.5} className="text-white" />
          ) : (
            <X size={12} strokeWidth={2.5} className="text-white" />
          )}
        </div>

        <div className="flex-1 min-w-0">
          {/* Verdict label + reason */}
          <div className="flex items-baseline gap-2">
            <span
              className={cn(
                "text-label font-medium",
                verdict.sufficient ? "text-vera-verified" : "text-vera-insufficient"
              )}
            >
              {verdict.sufficient ? "Sufficient" : "Insufficient"}
            </span>
            <span className="text-label text-vera-ink">— &ldquo;{verdict.reason}&rdquo;</span>
          </div>

          {/* Missing aspects */}
          {!verdict.sufficient && verdict.missingAspects.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              <span className="text-label text-vera-muted">Missing:</span>
              {verdict.missingAspects.map((aspect) => (
                <span
                  key={aspect}
                  className="px-2 py-0.5 text-label text-vera-insufficient bg-vera-insufficient/10 border border-vera-insufficient/20"
                  style={{ borderRadius: "2px" }}
                >
                  {aspect}
                </span>
              ))}
            </div>
          )}

          {/* Router decision badge */}
          {routerAction && (
            <div className="flex items-center gap-2 mt-2">
              <span className="text-label text-vera-muted">Router:</span>
              {routerAction === "backtrack" && backtrackEvent ? (
                <span
                  className="inline-flex items-center gap-1 px-2 py-0.5 text-label font-medium text-vera-backtrack bg-vera-backtrack-muted border border-vera-backtrack/30"
                  style={{ borderRadius: "2px" }}
                >
                  <RotateCcw size={10} strokeWidth={1.5} />
                  Backtrack to step {backtrackEvent.toIndex + 1}
                </span>
              ) : (
                <span
                  className="inline-flex items-center gap-1 px-2 py-0.5 text-label font-medium text-vera-accent bg-vera-accent-muted border border-vera-accent/30"
                  style={{ borderRadius: "2px" }}
                >
                  <Plus size={10} strokeWidth={1.5} />
                  Add step
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Screen reader live announcement text */}
      <span className="sr-only">
        {verdict.sufficient
          ? `Step verified: sufficient. ${verdict.reason}`
          : `Step verified: insufficient. ${verdict.reason}. Missing: ${verdict.missingAspects.join(", ")}`}
      </span>
    </div>
  );
}
