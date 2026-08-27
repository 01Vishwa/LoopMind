"use client";

import { useEffect, useState } from "react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils/cn";

interface SaveButtonProps {
  isDirty: boolean;
  isSaving?: boolean;
  onSave: () => void | Promise<void>;
  label?: string;
}

export function SaveButton({
  isDirty,
  isSaving = false,
  onSave,
  label = "Save changes",
}: SaveButtonProps) {
  const [saved, setSaved] = useState(false);

  const handleClick = async () => {
    await onSave();
    setSaved(true);
  };

  useEffect(() => {
    if (!saved) return;
    const t = setTimeout(() => setSaved(false), 3000);
    return () => clearTimeout(t);
  }, [saved]);

  return (
    <div className="flex items-center gap-3 mt-6">
      <button
        onClick={handleClick}
        disabled={!isDirty || isSaving}
        className={cn(
          "px-4 py-2 rounded-md text-sm font-medium transition-all duration-150",
          isDirty && !isSaving
            ? "bg-vera-accent text-white hover:opacity-90 active:scale-[0.98] cursor-pointer"
            : "bg-vera-border text-vera-muted cursor-not-allowed opacity-70"
        )}
      >
        {isSaving ? "Saving…" : label}
      </button>

      {saved && (
        <span className="flex items-center gap-1.5 text-sm text-vera-verified animate-fade-in">
          <Check size={13} strokeWidth={2.5} />
          Changes saved
        </span>
      )}
    </div>
  );
}
