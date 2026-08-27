import { cn } from "@/lib/utils/cn";
import { AlertCircle, RefreshCw } from "lucide-react";

export interface ErrorBannerProps {
  message: string;
  detail?: string;
  action?: { label: string; onClick: () => void };
  className?: string;
}

export function ErrorBanner({ message, detail, action, className }: ErrorBannerProps) {
  return (
    <div
      role="alert"
      className={cn(
        "flex items-start gap-3 px-4 py-3 rounded border border-vera-insufficient/30 bg-vera-insufficient-muted",
        className
      )}
    >
      <AlertCircle size={16} strokeWidth={1.5} className="text-vera-insufficient mt-0.5 shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-label font-medium text-vera-insufficient">{message}</p>
        {detail && <p className="text-label text-vera-insufficient/80 mt-0.5">{detail}</p>}
      </div>
      {action && (
        <button
          onClick={action.onClick}
          className="flex items-center gap-1 text-label text-vera-insufficient font-medium hover:underline shrink-0"
        >
          <RefreshCw size={12} strokeWidth={1.5} />
          {action.label}
        </button>
      )}
    </div>
  );
}
