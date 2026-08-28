"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import { PanelLeftClose, PanelLeftOpen, Zap, LogOut } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { ThemeSegmentedControl, ThemeIconToggle } from "@/components/shared/ThemeToggle";
import { PRIMARY_NAV, SETTINGS_NAV_ITEM } from "@/lib/config/navigation";
import { useAuth } from "@/lib/auth/AuthProvider";
import { initialsOf } from "@/lib/data/session";

export function Sidebar() {
  const pathname = usePathname();
  const { user, can, signOut } = useAuth();
  const navItems = PRIMARY_NAV.filter((item) => can(item.requiredRole));
  const [expanded, setExpanded] = useState(true);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const stored = localStorage.getItem("vera-sidebar-expanded");
    if (stored !== null) {
      setExpanded(stored === "true");
    } else {
      // No explicit user preference yet — collapse to icon-only under 1024px per spec §3.1.
      setExpanded(window.innerWidth >= 1024);
    }
  }, []);

  const toggle = () => {
    const next = !expanded;
    setExpanded(next);
    localStorage.setItem("vera-sidebar-expanded", String(next));
  };

  const isActive = (href: string) => pathname.startsWith(href);

  return (
    <nav
      aria-label="Primary navigation"
      className={cn(
        "flex flex-col h-full shrink-0",
        "border-r border-vera-border",
        "transition-all duration-200 ease-in-out",
        "bg-vera-surface relative",
        expanded ? "w-56" : "w-14"
      )}
    >
      {/* Logo */}
      <div
        className={cn(
          "flex items-center h-12 px-3 border-b border-vera-border shrink-0",
          !expanded && "justify-center"
        )}
      >
        <Link href="/workspaces" className="flex items-center gap-2.5 no-underline group">
          {/* Logo mark */}
          <div className="w-7 h-7 rounded-lg bg-vera-accent flex items-center justify-center shrink-0 shadow-lg shadow-vera-accent/20 group-hover:shadow-vera-accent/40 transition-shadow">
            <Zap size={14} strokeWidth={2} className="text-white" />
          </div>
          {expanded && (
            <div className="flex flex-col leading-none">
              <span
                className="text-sm font-bold tracking-tight text-vera-ink"
                style={{ fontFamily: "'JetBrains Mono', monospace", letterSpacing: "-0.03em" }}
              >
                VERA
              </span>
              <span className="text-[10px] text-vera-muted font-normal mt-px" style={{ letterSpacing: "0.08em" }}>
                ANALYTICS
              </span>
            </div>
          )}
        </Link>
      </div>

      {/* Navigation group — primary items + divider + Settings, all styled identically */}
      <div className="py-3 px-1.5 space-y-0.5 overflow-y-auto shrink-0">
        {navItems.map(({ href, label, icon: Icon, shortcut }) => {
          const active = isActive(href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              title={!expanded ? (shortcut ? `${label} (${shortcut})` : label) : undefined}
              className={cn(
                "flex items-center gap-3 px-2.5 py-2 rounded-md text-sm font-medium no-underline",
                "transition-all duration-100 group relative",
                active
                  ? "bg-vera-accent-muted text-vera-accent"
                  : "text-vera-muted hover:text-vera-ink hover:bg-vera-border-subtle",
                !expanded && "justify-center px-0"
              )}
            >
              {/* Active indicator bar */}
              {active && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-vera-accent rounded-r-full" />
              )}
              <Icon
                size={16}
                strokeWidth={1.75}
                className={cn(
                  "shrink-0 transition-transform duration-100",
                  active && "text-vera-accent",
                  "group-hover:scale-105"
                )}
              />
              {expanded && (
                <span className="truncate">{label}</span>
              )}
            </Link>
          );
        })}

        {/* Divider */}
        <div className="border-t border-vera-border-subtle my-1.5" />

        {/* Settings — same NavItem treatment as the primary group above */}
        {(() => {
          const { href, label, icon: Icon } = SETTINGS_NAV_ITEM;
          const active = isActive(href);
          return (
            <Link
              href={href}
              aria-current={active ? "page" : undefined}
              title={!expanded ? label : undefined}
              className={cn(
                "flex items-center gap-3 px-2.5 py-2 rounded-md text-sm font-medium no-underline",
                "transition-all duration-100 group relative",
                active
                  ? "bg-vera-accent-muted text-vera-accent"
                  : "text-vera-muted hover:text-vera-ink hover:bg-vera-border-subtle",
                !expanded && "justify-center px-0"
              )}
            >
              {active && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-vera-accent rounded-r-full" />
              )}
              <Icon
                size={16}
                strokeWidth={1.75}
                className={cn(
                  "shrink-0 transition-transform duration-100",
                  active && "text-vera-accent",
                  "group-hover:scale-105"
                )}
              />
              {expanded && <span className="truncate">{label}</span>}
            </Link>
          );
        })()}
      </div>

      {/* Spacer — fills remaining space so the user block + chrome controls stay pinned to the bottom */}
      <div className="flex-1" />

      {/* User block — bottom-pinned, above the chrome controls row */}
      <div className="px-1.5 pb-1.5 pt-1.5 border-t border-vera-border-subtle shrink-0">
        {/* Avatar + name/email → navigates to settings */}
        <Link
          href="/settings"
          title={!expanded && user ? `${user.name} · ${user.email}` : undefined}
          className={cn(
            "flex items-center gap-2.5 px-1.5 py-2 rounded-md no-underline",
            "hover:bg-vera-border-subtle transition-colors duration-100",
            !expanded && "justify-center px-0"
          )}
        >
          <div className="w-8 h-8 rounded-full bg-vera-accent-muted border border-vera-accent/30 flex items-center justify-center shrink-0 overflow-hidden">
            {user?.avatarUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={user.avatarUrl} alt="" className="w-full h-full object-cover" />
            ) : (
              <span className="text-[11px] font-semibold text-vera-accent">
                {user ? initialsOf(user.name) : ""}
              </span>
            )}
          </div>
          {expanded && (
            <div className="flex flex-col leading-tight min-w-0">
              {user ? (
                <>
                  <span className="text-xs font-medium text-vera-ink truncate">{user.name}</span>
                  <span className="text-vera-muted truncate" style={{ fontSize: "11px" }}>
                    {user.email}
                  </span>
                </>
              ) : (
                <>
                  <span className="h-3 w-20 rounded bg-vera-border-subtle shimmer" />
                  <span className="h-2.5 w-28 rounded bg-vera-border-subtle shimmer mt-1" />
                </>
              )}
            </div>
          )}
        </Link>

        {/* Sign out */}
        <button
          onClick={() => signOut()}
          title="Sign out"
          aria-label="Sign out"
          className={cn(
            "flex items-center gap-2.5 px-1.5 py-1.5 rounded-md w-full text-left",
            "text-vera-muted hover:text-vera-insufficient hover:bg-vera-border-subtle",
            "transition-colors duration-100 text-xs font-medium",
            !expanded && "justify-center px-0"
          )}
        >
          <LogOut size={14} strokeWidth={1.75} className="shrink-0" />
          {expanded && <span>Sign out</span>}
        </button>
      </div>

      {/* Chrome controls — two separate rows so theme and collapse are never confused */}
      <div className="border-t border-vera-border-subtle shrink-0">
        {/* Row 1: theme toggle */}
        {expanded ? (
          /* Expanded: full segmented control */
          <div className="px-2 pt-2 pb-1">
            <ThemeSegmentedControl className="w-full" />
          </div>
        ) : (
          /* Collapsed: icon-only, centred */
          <div className="flex justify-center pt-2 pb-1">
            <ThemeIconToggle />
          </div>
        )}

        {/* Row 2: collapse / expand */}
        {expanded ? (
          <div className="px-2 pb-2">
            <button
              onClick={toggle}
              aria-label="Collapse sidebar"
              title="Collapse sidebar"
              className={cn(
                "flex items-center gap-2 w-full px-2 py-1.5 rounded-md text-xs font-medium",
                "text-vera-muted hover:text-vera-ink hover:bg-vera-border-subtle",
                "transition-colors duration-100"
              )}
            >
              <PanelLeftClose size={14} strokeWidth={1.5} />
              <span>Collapse</span>
            </button>
          </div>
        ) : (
          <div className="flex justify-center pb-2">
            <button
              onClick={toggle}
              aria-label="Expand sidebar"
              title="Expand sidebar"
              className={cn(
                "flex items-center justify-center w-7 h-7 rounded-md shrink-0",
                "text-vera-muted hover:text-vera-ink hover:bg-vera-border-subtle",
                "transition-colors duration-100"
              )}
            >
              <PanelLeftOpen size={20} strokeWidth={1.5} />
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}
