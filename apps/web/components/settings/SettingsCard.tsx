import { cn } from "@/lib/utils/cn";

interface SettingsCardProps {
  title?: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
}

export function SettingsCard({ title, description, children, className }: SettingsCardProps) {
  return (
    <div className={cn("bg-vera-surface border border-vera-border rounded-lg p-6", className)}>
      {title && (
        <div className="mb-5">
          <h2 className="text-[15px] font-semibold text-vera-ink leading-tight">{title}</h2>
          {description && (
            <p className="text-sm text-vera-muted mt-1">{description}</p>
          )}
        </div>
      )}
      {children}
    </div>
  );
}

/** A horizontal rule used to separate cards within a section. */
export function SettingsDivider() {
  return <div className="border-t border-vera-border my-6" />;
}
