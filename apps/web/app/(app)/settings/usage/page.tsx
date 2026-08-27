"use client";

import { useState } from "react";
import { ChevronLeft } from "lucide-react";
import { SettingsCard } from "@/components/settings/SettingsCard";
import { UsageChart } from "@/components/settings/UsageChart";
import { CostBreakdown } from "@/components/settings/CostBreakdown";
import { BlockSkeleton, ErrorState } from "@/components/shared/DataStates";
import { useResource } from "@/lib/data/useResource";
import { listUsagePeriods, getUsageBreakdown } from "@/lib/data/usage";
import { cn } from "@/lib/utils/cn";

function fmtTokens(n: number) {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}K` : String(n);
}

function BudgetBar({ cost, budget }: { cost: number; budget: number }) {
  const pct = Math.min((cost / budget) * 100, 100);
  const colour = pct > 90 ? "bg-vera-insufficient" : pct > 70 ? "bg-vera-backtrack" : "bg-vera-accent";
  return (
    <div className="mt-1.5 h-1.5 rounded-full bg-vera-border overflow-hidden">
      <div className={cn("h-full rounded-full transition-all", colour)} style={{ width: `${pct}%` }} />
    </div>
  );
}
export default function UsagePage() {
  const {
    data: periods,
    status: periodsStatus,
    error: periodsError,
    retry: retryPeriods,
  } = useResource(listUsagePeriods, []);

  const [periodIdx, setPeriodIdx] = useState(0);
  const period = periods?.[Math.min(periodIdx, Math.max(periods.length - 1, 0))];
  const isCurrent = periodIdx === 0;

  // Breakdown is per-period, so it refetches whenever the selection changes.
  const { data: breakdown, status: breakdownStatus } = useResource(
    () => (period ? getUsageBreakdown(period.id) : Promise.resolve([])),
    [period?.id],
  );

  if (periodsStatus === "error") {
    return (
      <div className="space-y-6 animate-slide-up">
        <ErrorState error={periodsError} onRetry={retryPeriods} />
      </div>
    );
  }

  if (periodsStatus === "loading") {
    return (
      <div className="space-y-6 animate-slide-up">
        <div className="h-4 w-64 rounded bg-vera-border-subtle shimmer" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="bg-vera-surface border border-vera-border rounded-lg p-4">
              <div className="h-3 w-12 rounded bg-vera-border-subtle shimmer mb-2" />
              <div className="h-5 w-20 rounded bg-vera-border-subtle shimmer" />
            </div>
          ))}
        </div>
        <SettingsCard title="Cost by day">
          <BlockSkeleton lines={4} />
        </SettingsCard>
        <SettingsCard title="Cost breakdown">
          <BlockSkeleton lines={5} />
        </SettingsCard>
      </div>
    );
  }

  if (!period) {
    return (
      <div className="space-y-6 animate-slide-up">
        <SettingsCard title="Usage">
          <p className="text-sm text-vera-muted">
            No usage recorded yet. Figures appear here once you start a run.
          </p>
        </SettingsCard>
      </div>
    );
  }

  const stats = [
    { label: "Runs",   value: String(period.runs) },
    { label: "Tokens", value: fmtTokens(period.tokens) },
    { label: "Cost",   value: `$${period.cost.toFixed(2)}` },
  ];

  return (
    <div className="space-y-6 animate-slide-up">
      {/* Period header */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-vera-muted">
          {isCurrent ? `Current billing period (${period.label})` : `Viewing: ${period.label}`}
        </p>
        {!isCurrent && (
          <button
            onClick={() => setPeriodIdx(0)}
            className="flex items-center gap-1.5 text-xs text-vera-accent hover:underline"
          >
            <ChevronLeft size={12} strokeWidth={1.75} />
            Back to current
          </button>
        )}
      </div>

      {/* ── Stat cards ────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {stats.map(({ label, value }) => (
          <div key={label} className="bg-vera-surface border border-vera-border rounded-lg p-4">
            <p className="text-xs text-vera-muted mb-1">{label}</p>
            <p className="text-xl font-semibold text-vera-ink tabular-nums">{value}</p>
          </div>
        ))}
        {/* Budget card */}
        <div className="bg-vera-surface border border-vera-border rounded-lg p-4">
          <p className="text-xs text-vera-muted mb-1">Budget</p>
          <p className="text-xl font-semibold text-vera-ink tabular-nums">
            ${period.cost.toFixed(2)}<span className="text-sm font-normal text-vera-muted">/${period.budget}</span>
          </p>
          <BudgetBar cost={period.cost} budget={period.budget} />
          <p className="text-[10px] text-vera-muted mt-1">{Math.round((period.cost / period.budget) * 100)}% of budget used</p>
        </div>
      </div>

      {/* ── Chart ─────────────────────────────────────────── */}
      <SettingsCard title="Cost by day">
        <UsageChart data={period.data} height={180} />
      </SettingsCard>

      {/* ── Cost breakdown ────────────────────────────────── */}
      <SettingsCard title="Cost breakdown">
        {breakdownStatus === "loading" ? (
          <BlockSkeleton lines={5} />
        ) : breakdown && breakdown.length > 0 ? (
          <CostBreakdown sections={breakdown} />
        ) : (
          <p className="text-sm text-vera-muted">No spend recorded for this period.</p>
        )}
      </SettingsCard>

      {/* ── History ───────────────────────────────────────── */}
      <SettingsCard title="Billing history">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-vera-border">
              <th className="table-header pb-2 text-left">Period</th>
              <th className="table-header pb-2 text-right pr-4">Runs</th>
              <th className="table-header pb-2 text-right pr-4">Tokens</th>
              <th className="table-header pb-2 text-right">Cost</th>
            </tr>
          </thead>
          <tbody>
            {periods.map((p, idx) => (
              <tr
                key={p.id}
                className={cn(
                  "border-b border-vera-border-subtle last:border-0 transition-colors",
                  idx === periodIdx
                    ? "bg-vera-accent-muted/30"
                    : "hover:bg-vera-border-subtle"
                )}
              >
                <td className="py-2.5 text-vera-ink">
                  <button
                    type="button"
                    onClick={() => setPeriodIdx(idx)}
                    aria-pressed={idx === periodIdx}
                    className="flex items-center gap-2 text-left hover:text-vera-accent transition-colors rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-vera-accent"
                  >
                    {p.label}
                    {idx === 0 && (
                      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-vera-accent-muted text-vera-accent">
                        Current
                      </span>
                    )}
                  </button>
                </td>
                <td className="py-2.5 text-right text-vera-muted tabular-nums pr-4">{p.runs}</td>
                <td className="py-2.5 text-right text-vera-muted tabular-nums pr-4">{fmtTokens(p.tokens)}</td>
                <td className="py-2.5 text-right text-vera-ink font-medium tabular-nums">${p.cost.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </SettingsCard>
    </div>
  );
}
