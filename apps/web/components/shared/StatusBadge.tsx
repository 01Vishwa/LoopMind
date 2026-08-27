import { cn } from "@/lib/utils/cn";
import { Check, CircleDashed, Circle, XCircle, Ban, Undo2, HelpCircle, type LucideIcon } from "lucide-react";

export type BadgeStatus =
  | "pending"
  | "analyzing"
  | "ready"
  | "sufficient"
  | "insufficient"
  | "backtracked"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled"
  | "ingesting"
  | "partial"
  | "archived";

export interface StatusBadgeProps {
  status: BadgeStatus;
  tooltip?: string;
  progress?: number; // 0 to 100
  eta?: string;
  className?: string;
}

interface StatusConfig {
  label: string;
  bg: string;
  text: string;
  icon?: LucideIcon;
  dot?: boolean; // animated pulse dot instead of a static icon
}

// One visual contract for every status badge in the app — see G4.
const STATUS_CONFIG: Record<BadgeStatus, StatusConfig> = {
  ready: { label: "Ready", bg: "bg-vera-verified-muted", text: "text-vera-verified", icon: Check },
  succeeded: { label: "Succeeded", bg: "bg-vera-verified-muted", text: "text-vera-verified", icon: Check },
  sufficient: { label: "Sufficient", bg: "bg-vera-verified-muted", text: "text-vera-verified", icon: Check },

  partial: { label: "Partial", bg: "bg-vera-backtrack-muted", text: "text-vera-backtrack", icon: CircleDashed },
  backtracked: { label: "Backtracked", bg: "bg-vera-backtrack-muted", text: "text-vera-backtrack", icon: Undo2 },

  ingesting: { label: "Ingesting", bg: "bg-vera-accent-muted", text: "text-vera-accent", dot: true },
  analyzing: { label: "Analyzing", bg: "bg-vera-accent-muted", text: "text-vera-accent", dot: true },
  running: { label: "Running", bg: "bg-vera-accent-muted", text: "text-vera-accent", dot: true },

  pending: { label: "Pending", bg: "bg-vera-border", text: "text-vera-muted", icon: Circle },
  cancelled: { label: "Cancelled", bg: "bg-vera-border", text: "text-vera-muted", icon: Ban },
  archived: { label: "Archived", bg: "bg-vera-border", text: "text-vera-muted", icon: Ban },

  failed: { label: "Failed", bg: "bg-vera-insufficient-muted", text: "text-vera-insufficient", icon: XCircle },
  insufficient: { label: "Insufficient", bg: "bg-vera-insufficient-muted", text: "text-vera-insufficient", icon: XCircle },
};

export function StatusBadge({ status, tooltip, progress, eta, className }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status];
  if (!config) return null;

  const Icon = config.icon;
  const isIngesting = status === "ingesting" || status === "running" || status === "analyzing";
  const hasProgress = isIngesting && typeof progress === "number";

  return (
    <div className={cn("inline-flex flex-col gap-1", className)}>
      <span
        className={cn(
          "px-2 py-0.5 rounded text-xs font-medium inline-flex items-center gap-1",
          config.bg,
          config.text
        )}
      >
        {config.dot && (
          <span className="w-1.5 h-1.5 rounded-full bg-current status-badge-pulse inline-block shrink-0" aria-hidden />
        )}
        {Icon && <Icon size={12} strokeWidth={2} className="shrink-0" aria-hidden />}
        {config.label}
        {tooltip && (
          <span
            title={tooltip}
            aria-label={tooltip}
            className="inline-flex items-center opacity-70 shrink-0 cursor-help"
          >
            <HelpCircle size={12} strokeWidth={2} />
          </span>
        )}
      </span>

      {/* Progress indicator for ingesting/running/analyzing */}
      {isIngesting && (hasProgress || eta) && (
        <div className="flex flex-col gap-1 w-full min-w-[100px]">
          {hasProgress && (
            <div className="h-1 w-full bg-vera-border rounded-full overflow-hidden">
              <div
                className="h-full bg-vera-accent transition-all duration-300 ease-out"
                style={{ width: `${Math.min(Math.max(progress, 0), 100)}%` }}
              />
            </div>
          )}
          {(hasProgress || eta) && (
            <div className="flex items-center justify-between gap-2 text-[10px] text-vera-muted font-medium">
              {hasProgress && <span>{Math.round(progress)}%</span>}
              {eta && <span>{eta}</span>}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
