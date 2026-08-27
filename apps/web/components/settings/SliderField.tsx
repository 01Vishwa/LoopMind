"use client";

import { cn } from "@/lib/utils/cn";

interface SliderFieldProps {
  id: string;
  label: string;
  min: number;
  max: number;
  step?: number;
  value: number;
  onChange: (v: number) => void;
  helpText?: string;
  className?: string;
}

export function SliderField({
  id,
  label,
  min,
  max,
  step = 1,
  value,
  onChange,
  helpText,
  className,
}: SliderFieldProps) {
  const pct = ((value - min) / (max - min)) * 100;

  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex items-center justify-between">
        <label htmlFor={id} className="text-sm font-medium text-vera-ink">
          {label}
        </label>
        <span className="text-sm font-semibold text-vera-ink tabular-nums w-8 text-right">
          {value}
        </span>
      </div>

      <div className="relative flex items-center gap-2">
        <span className="text-xs text-vera-muted tabular-nums w-6 text-right">{min}</span>
        <div className="relative flex-1 h-5 flex items-center">
          {/* Track background */}
          <div className="absolute w-full h-1.5 rounded-full bg-vera-border" />
          {/* Fill */}
          <div
            className="absolute h-1.5 rounded-full bg-vera-accent transition-all"
            style={{ width: `${pct}%` }}
          />
          {/* Native range — invisible but interactive */}
          <input
            id={id}
            type="range"
            min={min}
            max={max}
            step={step}
            value={value}
            onChange={(e) => onChange(Number(e.target.value))}
            className="absolute w-full opacity-0 cursor-pointer h-5"
          />
          {/* Thumb */}
          <div
            className="absolute w-4 h-4 rounded-full bg-vera-accent border-2 border-white shadow-sm pointer-events-none transition-all"
            style={{ left: `calc(${pct}% - 8px)` }}
          />
        </div>
        <span className="text-xs text-vera-muted tabular-nums w-6">{max}</span>
      </div>

      {helpText && (
        <p className="text-xs text-vera-muted leading-relaxed">{helpText}</p>
      )}
    </div>
  );
}
