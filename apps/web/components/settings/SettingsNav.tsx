"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils/cn";
import { SETTINGS_NAV } from "@/lib/config/navigation";
import { useAuth } from "@/lib/auth/AuthProvider";

interface SettingsNavProps {
  /** When true, renders a horizontal scrollable tab bar (tablet/mobile). */
  horizontal?: boolean;
}

export function SettingsNav({ horizontal = false }: SettingsNavProps) {
  const pathname = usePathname();
  const { can } = useAuth();
  const NAV_ITEMS = SETTINGS_NAV.filter((item) => can(item.requiredRole));

  if (horizontal) {
    return (
      <nav
        aria-label="Settings navigation"
        className="flex gap-0.5 overflow-x-auto border-b border-vera-border pb-0 shrink-0 px-4"
        style={{ scrollbarWidth: "none" }}
      >
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex items-center gap-2 px-3 py-2.5 text-sm whitespace-nowrap border-b-2 -mb-px transition-colors",
                active
                  ? "border-vera-accent text-vera-ink font-semibold"
                  : "border-transparent text-vera-muted hover:text-vera-ink font-medium"
              )}
            >
              <Icon size={14} strokeWidth={1.75} />
              {label}
            </Link>
          );
        })}
      </nav>
    );
  }

  return (
    <nav
      aria-label="Settings navigation"
      className="w-[200px] shrink-0 space-y-0.5 pt-1"
    >
      {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
        const active = pathname === href || pathname.startsWith(href + "/");
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex items-center gap-2.5 px-3 py-2 text-sm rounded-r-md border-l-2 transition-all",
              active
                ? "border-vera-accent text-vera-ink font-semibold bg-vera-accent-muted/30"
                : "border-transparent text-vera-muted hover:text-vera-ink font-medium hover:bg-vera-border-subtle"
            )}
          >
            <Icon size={14} strokeWidth={1.75} />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
