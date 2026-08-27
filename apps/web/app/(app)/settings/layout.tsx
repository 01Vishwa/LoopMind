"use client";

import { useEffect, useState } from "react";
import { SettingsNav } from "@/components/settings/SettingsNav";

/**
 * Picks a single layout tree for the given media query so `{children}` (and its
 * data fetches) mount exactly once, instead of once per responsive branch.
 */
function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);
  useEffect(() => {
    const mql = window.matchMedia(query);
    setMatches(mql.matches);
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, [query]);
  return matches;
}

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  const isDesktop = useMediaQuery("(min-width: 1024px)");

  return (
    <div className="px-6 py-8 max-w-[1440px] mx-auto">
      {/* Page heading */}
      <h1
        className="text-display text-vera-ink mb-8"
        style={{ fontFamily: "'JetBrains Mono', monospace" }}
      >
        Settings
      </h1>

      {/* One tree: sidebar beside content on ≥1024px, tab bar above it below. */}
      <div className={isDesktop ? "flex gap-10 items-start" : "flex flex-col gap-6"}>
        <SettingsNav horizontal={!isDesktop} />
        <div
          className={
            isDesktop
              ? "flex-1 min-w-0 max-w-[680px] space-y-6"
              : "max-w-[680px] space-y-6"
          }
        >
          {children}
        </div>
      </div>
    </div>
  );
}
