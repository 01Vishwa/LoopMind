"use client";

import { useState } from "react";
import { BarChart3 } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { formatTokens } from "@/lib/utils/formatTokens";

export interface UsageDataPoint {
  day: string;
  runs: number;
  tokens: number;
  cost: number;
}

interface Tooltip {
  x: number;
  y: number;
  data: UsageDataPoint;
}

interface UsageChartProps {
  data: UsageDataPoint[];
  height?: number;
}

export function UsageChart({ data, height = 180 }: UsageChartProps) {
  const [tooltip, setTooltip] = useState<Tooltip | null>(null);

  if (data.length === 0) {
    return (
      <div
        className="flex flex-col items-center justify-center gap-2 text-center rounded-md border border-dashed border-vera-border"
        style={{ height: height + 20 }}
      >
        <BarChart3 size={20} strokeWidth={1.5} className="text-vera-muted" />
        <p className="text-sm font-medium text-vera-ink">No usage data yet</p>
        <p className="text-xs text-vera-muted">Run an analysis to start tracking spend here.</p>
      </div>
    );
  }

  const maxCost = Math.max(...data.map((d) => d.cost), 0.01);
  const chartTop = Math.ceil(maxCost * 10) / 10;
  const TICKS = 4;

  return (
    <div className="relative select-none">
      <div className="flex gap-3">
        {/* Y-axis */}
        <div
          className="flex flex-col justify-between shrink-0 text-right"
          style={{ height, paddingBottom: "20px" }}
        >
          {Array.from({ length: TICKS + 1 }, (_, i) => TICKS - i).map((tick) => (
            <span key={tick} className="text-[10px] font-mono text-vera-muted">
              ${((chartTop / TICKS) * tick).toFixed(2)}
            </span>
          ))}
        </div>

        {/* Chart area */}
        <div className="relative flex-1" style={{ height }}>
          {/* Gridlines */}
          <div className="absolute inset-0 flex flex-col justify-between pb-5 pointer-events-none">
            {Array.from({ length: TICKS + 1 }).map((_, i) => (
              <div key={i} className="border-t border-vera-border-subtle" />
            ))}
          </div>

          {/* Bars */}
          <div className="absolute inset-x-0 bottom-5 top-0 flex items-end gap-1.5 px-1">
            {data.map((d, idx) => {
              const barH = Math.max((d.cost / chartTop) * 100, 2);
              return (
                <div
                  key={d.day}
                  className="flex-1 flex flex-col items-center gap-1 h-full justify-end"
                  onMouseEnter={(e) => {
                    const rect = e.currentTarget.getBoundingClientRect();
                    const parent = e.currentTarget.closest(".relative")?.getBoundingClientRect();
                    setTooltip({
                      x: rect.left - (parent?.left ?? 0) + rect.width / 2,
                      y: rect.top - (parent?.top ?? 0),
                      data: d,
                    });
                  }}
                  onMouseLeave={() => setTooltip(null)}
                >
                  <div
                    className="w-full bg-vera-accent hover:bg-vera-accent-hover transition-colors cursor-default"
                    style={{
                      height: `${barH}%`,
                      borderRadius: "3px 3px 0 0",
                    }}
                  />
                  <span className="text-[10px] font-mono text-vera-muted shrink-0 pb-0.5">
                    {d.day.slice(-2)}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Floating tooltip */}
          {tooltip && (
            <div
              className={cn(
                "absolute z-10 pointer-events-none",
                "bg-vera-surface border border-vera-border rounded-md px-3 py-2 shadow-lg",
                "text-xs whitespace-nowrap -translate-x-1/2 -translate-y-full -mt-2"
              )}
              style={{ left: tooltip.x, top: tooltip.y }}
            >
              <p className="font-semibold text-vera-ink mb-1">{tooltip.data.day}</p>
              <p className="text-vera-muted">
                ${tooltip.data.cost.toFixed(2)} · {tooltip.data.runs} runs · {formatTokens(tooltip.data.tokens)} tokens
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
