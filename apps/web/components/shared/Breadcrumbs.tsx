"use client";

import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils/cn";

export interface BreadcrumbSegment {
  label: string;
  href?: string;
}

export interface BreadcrumbsProps {
  segments: BreadcrumbSegment[];
  className?: string;
}

export function Breadcrumbs({ segments, className }: BreadcrumbsProps) {
  return (
    <nav
      aria-label="Breadcrumb"
      className={cn("flex items-center gap-1 text-label text-vera-muted", className)}
    >
      {segments.map((seg, i) => {
        const isLast = i === segments.length - 1;
        return (
          <span key={i} className="flex items-center gap-1">
            {i > 0 && (
              <ChevronRight size={12} strokeWidth={1.5} className="text-vera-border" aria-hidden />
            )}
            {seg.href && !isLast ? (
              <Link
                href={seg.href}
                className="hover:text-vera-ink transition-colors no-underline"
              >
                {seg.label}
              </Link>
            ) : (
              <span className={isLast ? "text-vera-ink font-medium" : ""}>{seg.label}</span>
            )}
          </span>
        );
      })}
    </nav>
  );
}
