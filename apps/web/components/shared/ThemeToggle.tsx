"use client";

import { Moon, Sun } from "lucide-react";
import { ThemeProvider as NextThemesProvider, useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils/cn";

/**
 * Single source of truth for theme state. Wraps the app once (in
 * app/layout.tsx). `next-themes` owns the `<html>` class, the
 * `localStorage` read/write (key `vera-theme`) and the anti-flash
 * script, so the individual toggles below never touch storage or the
 * DOM directly.
 */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="dark"
      enableSystem={false}
      storageKey="vera-theme"
      disableTransitionOnChange
    >
      {children}
    </NextThemesProvider>
  );
}

/** Avoids a hydration mismatch: theme is only known on the client. */
function useIsLight(): { isLight: boolean; mounted: boolean; setLight: (v: boolean) => void } {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  return {
    mounted,
    isLight: resolvedTheme === "light",
    setLight: (v: boolean) => setTheme(v ? "light" : "dark"),
  };
}

// ---------------------------------------------------------------------------
// Expanded: segmented control — both "Light" and "Dark" visible, active highlighted
// ---------------------------------------------------------------------------
export function ThemeSegmentedControl({ className }: { className?: string }) {
  const { isLight, mounted, setLight } = useIsLight();

  return (
    <div
      className={cn(
        "flex items-center rounded-lg p-0.5",
        "bg-vera-border-subtle",
        className
      )}
    >
      {/* Light option */}
      <button
        onClick={() => setLight(true)}
        aria-pressed={mounted ? isLight : undefined}
        aria-label="Switch to light mode"
        className={cn(
          "flex flex-1 items-center justify-center gap-1.5",
          "py-1.5 rounded-md text-xs font-medium",
          "transition-all duration-150 ease-in-out",
          mounted && isLight
            ? "bg-vera-surface text-vera-ink shadow-sm"
            : "text-vera-muted hover:text-vera-ink"
        )}
      >
        <Sun size={12} strokeWidth={1.75} />
        Light
      </button>

      {/* Dark option */}
      <button
        onClick={() => setLight(false)}
        aria-pressed={mounted ? !isLight : undefined}
        aria-label="Switch to dark mode"
        className={cn(
          "flex flex-1 items-center justify-center gap-1.5",
          "py-1.5 rounded-md text-xs font-medium",
          "transition-all duration-150 ease-in-out",
          mounted && !isLight
            ? "bg-vera-surface text-vera-ink shadow-sm"
            : "text-vera-muted hover:text-vera-ink"
        )}
      >
        <Moon size={12} strokeWidth={1.75} />
        Dark
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Collapsed: icon-only toggle — shows the OPPOSITE icon (what you switch TO)
// matching macOS / VS Code convention
// ---------------------------------------------------------------------------
export function ThemeIconToggle({ className }: { className?: string }) {
  const { isLight, mounted, setLight } = useIsLight();

  // In dark mode → show Sun (click → go light); in light mode → show Moon (click → go dark)
  const Icon = isLight ? Moon : Sun;
  const label = isLight ? "Switch to dark mode" : "Switch to light mode";

  return (
    <button
      onClick={() => setLight(!isLight)}
      aria-label={label}
      title={label}
      className={cn(
        "flex items-center justify-center w-7 h-7 rounded-md shrink-0",
        "text-vera-muted hover:text-vera-ink hover:bg-vera-border-subtle",
        "transition-colors duration-100",
        className
      )}
    >
      {/* Render a stable icon until mounted to avoid hydration flicker */}
      <Icon size={16} strokeWidth={1.5} style={{ visibility: mounted ? "visible" : "hidden" }} />
    </button>
  );
}

// ---------------------------------------------------------------------------
// Legacy export kept for backward compatibility
// ---------------------------------------------------------------------------
export function ThemeToggle({ className, showLabel }: { className?: string; showLabel?: boolean }) {
  return showLabel
    ? <ThemeSegmentedControl className={className} />
    : <ThemeIconToggle className={className} />;
}
