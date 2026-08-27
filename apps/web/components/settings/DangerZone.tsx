"use client";

import { useState } from "react";
import { cn } from "@/lib/utils/cn";

interface DangerZoneProps {
  title?: string;
  description: string;
  buttonLabel: string;
  confirmLabel?: string;
  onConfirm: () => void;
}

export function DangerZone({
  title = "Danger zone",
  description,
  buttonLabel,
  confirmLabel = "Yes, proceed",
  onConfirm,
}: DangerZoneProps) {
  const [confirming, setConfirming] = useState(false);

  return (
    <div className="mt-8 pt-6 border-t border-vera-border">
      <h3 className="text-xs font-semibold uppercase tracking-widest text-vera-insufficient mb-1">
        {title}
      </h3>
      <p className="text-sm text-vera-muted mb-4 max-w-[480px]">{description}</p>

      {!confirming ? (
        <button
          onClick={() => setConfirming(true)}
          className={cn(
            "px-4 py-2 text-sm font-medium rounded-md border transition-all duration-150",
            "border-vera-insufficient text-vera-insufficient",
            "hover:bg-vera-insufficient hover:text-white"
          )}
        >
          {buttonLabel}
        </button>
      ) : (
        <div className="flex items-center gap-3 text-sm">
          <span className="text-vera-muted">Are you sure? This cannot be undone.</span>
          <button
            onClick={() => { onConfirm(); setConfirming(false); }}
            className="font-medium text-vera-insufficient hover:underline"
          >
            {confirmLabel}
          </button>
          <span className="text-vera-border select-none">|</span>
          <button
            onClick={() => setConfirming(false)}
            className="font-medium text-vera-ink hover:underline"
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}
