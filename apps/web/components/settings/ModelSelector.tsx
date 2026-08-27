import { cn } from "@/lib/utils/cn";

export interface ModelOption {
  value: string;
  label: string;
  /** 1–4, relative cost indicator */
  cost: number;
  badge?: string;
}

interface ModelSelectorProps {
  id: string;
  label: string;
  description?: string;
  value: string;
  options: ModelOption[];
  onChange: (v: string) => void;
  disabled?: boolean;
  disabledReason?: React.ReactNode;
  className?: string;
}

function CostDots({ cost }: { cost: number }) {
  return (
    <span className="flex gap-0.5">
      {[1, 2, 3, 4].map((i) => (
        <span
          key={i}
          className={cn(
            "text-[10px]",
            i <= cost ? "text-vera-accent" : "text-vera-border"
          )}
        >
          ●
        </span>
      ))}
    </span>
  );
}

export function ModelSelector({
  id,
  label,
  description,
  value,
  options,
  onChange,
  disabled = false,
  disabledReason,
  className,
}: ModelSelectorProps) {
  return (
    <div className={cn("space-y-1.5", className)}>
      <label htmlFor={id} className="text-sm font-medium text-vera-ink block">
        {label}
      </label>
      {description && (
        <p className="text-xs text-vera-muted">{description}</p>
      )}

      {disabled && disabledReason ? (
        <div className="vera-input flex items-center gap-2 opacity-60 cursor-not-allowed">
          <span className="text-sm text-vera-muted">{disabledReason}</span>
        </div>
      ) : (
        <select
          id={id}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className="vera-input appearance-none cursor-pointer"
          style={{
            backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%238B8B9E' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E\")",
            backgroundRepeat: "no-repeat",
            backgroundPosition: "right 12px center",
            paddingRight: "2rem",
          }}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}{opt.badge ? ` (${opt.badge})` : ""}
            </option>
          ))}
        </select>
      )}

      {/* Cost legend for selected model */}
      {!disabled && (
        <div className="flex items-center gap-2">
          <CostDots cost={options.find((o) => o.value === value)?.cost ?? 2} />
          <span className="text-xs text-vera-muted">
            {options.find((o) => o.value === value)?.cost === 4
              ? "Highest quality"
              : options.find((o) => o.value === value)?.cost === 3
              ? "Recommended"
              : options.find((o) => o.value === value)?.cost === 2
              ? "Balanced"
              : "Fastest, cheapest"}
          </span>
        </div>
      )}
    </div>
  );
}
