import { cn } from "@/lib/utils/cn";
import type { FileKind } from "@/lib/schemas/runSchemas";
import type { LucideIcon } from "lucide-react";
import {
  Table2,
  Grid3X3,
  Braces,
  FileText,
  Hash,
  AlignLeft,
  Database,
  Archive,
  File,
} from "lucide-react";

export interface FileTypeBadgeProps {
  kind: FileKind;
  className?: string;
}

const FILE_TYPE_CONFIG: Record<FileKind, { label: string; Icon: LucideIcon }> = {
  csv: { label: "CSV", Icon: Table2 },
  xlsx: { label: "XLSX", Icon: Grid3X3 },
  xls: { label: "XLS", Icon: Grid3X3 },
  json: { label: "JSON", Icon: Braces },
  pdf: { label: "PDF", Icon: FileText },
  md: { label: "MD", Icon: Hash },
  txt: { label: "TXT", Icon: AlignLeft },
  sqlite: { label: "SQLite", Icon: Database },
  zip: { label: "ZIP", Icon: Archive },
  parquet: { label: "Parquet", Icon: Table2 },
  unknown: { label: "File", Icon: File },
};

export function FileTypeBadge({ kind, className }: FileTypeBadgeProps) {
  const config = FILE_TYPE_CONFIG[kind] ?? FILE_TYPE_CONFIG.unknown;
  const { label, Icon } = config;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-vera-muted bg-vera-border-subtle",
        className
      )}
      style={{ borderRadius: "2px" }}
    >
      <Icon size={11} strokeWidth={1.5} />
      <span className="text-mono-ui" style={{ fontSize: "11px", lineHeight: "14px" }}>
        {label}
      </span>
    </span>
  );
}
