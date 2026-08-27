# VERA `apps/web` — Frontend Fixes Applied

Date: 2026-08-27
Scope agreed with owner: **bugs + accessibility + design tokens only.**
Explicitly deferred: border-radius token migration (B1.3), large component splits (B3.1/B3.3/B3.5),
data/presentation type reshuffle (B3.4), server-component migration (A1.1), real login/refresh flow.

Executed by 4 parallel agents with partitioned file ownership, then a reconciliation pass.

## Verification

- `npx tsc --noEmit` — **clean (exit 0)**
- `npx next build` — **succeeds**, 14/14 pages generated
- 59 files changed under `apps/web` (+~1700 / −~1300), `lib/api/client.ts` deleted
- Environment note: `pnpm` is not on PATH; `next-themes@^0.4.6` installed via `npm --legacy-peer-deps`
  (React 19 / `@types/react` 18→19 peer set). Lockfile updated.

Per-agent detail: [`fix-design.md`](./fix-design.md) · [`fix-data.md`](./fix-data.md) ·
[`fix-components.md`](./fix-components.md) · [`fix-pages.md`](./fix-pages.md)

---

## Design system & theming (`tailwind.config.ts`, `globals.css`, `app/layout.tsx`, `ThemeToggle.tsx`, `monaco-theme.ts`, `package.json`)

| Item | Fix |
|------|-----|
| B1.1 | Colour tokens collapsed to one source of truth. `--vera-*` are now RGB-channel triples (`--vera-accent-rgb: 99 102 241`) with `rgb(var(--…-rgb))` aliases; Tailwind `vera.*` = `rgb(var(--vera-*-rgb) / <alpha-value>)` so **opacity / ring / divide / hover variants are theme-aware in dark mode**. Deleted the redundant `@layer utilities` colour re-declaration block. |
| B1.2 | `darkMode: ["selector", ":root:not(.light)"]` — matches the `.light` class the app actually toggles; `dark:` variants now live. |
| B1.4 | Accent unified to indigo `#6366F1` dark / `#4F46E5` light; hover is a same-hue step. Removed the blue-→-indigo mismatch. |
| B1.5 | Deleted `glow-pulse` keyframe/utility and the unreferenced `.sidebar-logo-mark` purple gradient. |
| A1.6 | Fonts loaded **only** via `next/font/google` (Inter → `--font-sans`, JetBrains Mono → `--font-mono`). Removed the manual `<link>` tags and the CSS `@import`. |
| A1.7 | Single theme source: `next-themes` `ThemeProvider` (attribute="class", default dark). Both toggle components rewritten on `useTheme()`; the three independent `useState`/`localStorage` reads and the inline anti-flash script are gone. |
| A4.4 | `@types/react` / `@types/react-dom` → `^19`. |
| — | `monaco-theme.ts` now exports typed dark+light themes + `defineVeraMonacoThemes()` / `veraMonacoThemeName()` helpers; `CodePane` imports them instead of an inlined object. |

## Data & transport (`lib/**`, `app/api/**`, `next.config.ts`)

| Item | Fix |
|------|-----|
| A3.1 | `useRunStream` returns real `useState` for `status`/`events` (RAF-batched) — **it re-renders now**. Store API unchanged. |
| A3.2 | Gap re-hydration uses `RunStateDTOSchema.safeParse` (no casts); spurious first-event-after-reconnect gap suppressed; new `"reconnecting"` status distinct from `"error"`. |
| A3.4 | `useResource` aborts in-flight fetches via `AbortController` (`{ signal }` passed to fetcher); `keepPreviousData` removed from the dep array. |
| A3.5 | `listRuns` forwards `sort`/`order` → server-side ordering, stable across "Load more". |
| A3.8 | `AuthProvider.refresh()` no longer double-fetches (dropped `sessionKey`, keeps `retry()`). |
| A3.9 | Single `formatBytes` / `formatTokens` in `lib/utils/`; `parseTabularOutput` is the one exported impl. |
| A3.10 | `lib/api/client.ts` deleted (zero importers); `eventLog` export removed. |
| A3.11 | New `lib/utils/clipboard.ts` `copyText(): Promise<boolean>` (clipboard API → textarea fallback, never throws). |
| A4.1 | Run-mode union standardized to `"precise" \| "research"`; `ProfileUpdate.defaultRunMode` retyped; profile page emits `"research"`. |
| A2.2 | One API surface: `lib/data/*` → `/api/*` BFF. `/api/v1/*` rewrite kept **only for SSE** (documented). |
| A2.3 | `lib/auth/token.ts` in-memory token holder; `http.ts` + XHR upload send `Authorization: Bearer`; `AuthProvider` exposes `setToken`/`clearToken`. New `app/api/_lib/proxy.ts`; all 30 route handlers now `proxyOr(request, "/v1/…", <existing stub>)` — proxy to `API_URL` when set (forwarding auth + trace), identical stub behaviour when unset. **No login page** (deferred). |

## Shared components (`components/**`)

| Item | Fix |
|------|-----|
| B2.2 | `NewWorkspaceModal`, `DescriptionDrawer` (was `role="complementary"`), `CitationPopover` rebuilt on `@radix-ui/react-dialog` → focus trap, initial focus, focus restoration, Escape, scroll lock. Public props unchanged. |
| B2.4 | `ObservationPane`: scroll container `aria-live="off"`; a visually-hidden `role="log" aria-live="polite"` receives only the appended delta while streaming. |
| B2.5 | `UploadDropzone`: visible `role="alert"` error text, undefined-guarded. |
| B2.6 | `DescriptionDrawer` tabs get `role="tablist/tab/tabpanel"` + roving tabindex. |
| B2.8 | `FileGrid` / `WorkspaceTable` sortable headers → nested `<button>` + `aria-sort`; `WorkspaceTable` rows use a real `<Link>` in the name cell (stretched-link), other cells `aria-hidden`. |
| B1.5 | `ProviderKeyCard` ✓/✗ → lucide `Check`/`X`; `DescriptionDrawer` ⚠ → `AlertTriangle`. |
| A5.4 | `ProviderKeyCard.handleTest` no longer fakes a green "Connected" — shows "Key saved (unverified)" + not-wired note. |
| B2.9 | `UsageChart` renders a "No usage data yet" state instead of an empty plot. |
| A3.11 | All `navigator.clipboard` calls → `copyText()` with visible failure feedback. |

## App pages (`app/(app)/**` + new boundaries)

| Item | Fix |
|------|-----|
| A1.2 | `settings/layout.tsx` and `runs/[runId]/page.tsx` render each subtree/pane **exactly once** via a `useMediaQuery` hook — no more double `useResource` fetches or double Monaco mount. |
| A3.3 | `isRunning` uses an explicit active-phase allow-list (`"connecting"`/unknown ⇒ not running); `MAX_POLLS` cap; step fetches guarded by `hasSteps`; `StatusBar` shows `Round N` (no `/0`) when `maxRounds` is 0. |
| A3.6 | `useElapsedTimer` resyncs to `run.status.elapsedMs` on every poll. |
| A3.7 | Snapshot + rollback + visible error on `saved-analyses` (`togglePause`/`handleDelete`/`handleReRun` — success only on resolve) and `runs` `handleRetry`. |
| A4.5 | `CopyableText` strips an optional `sha256:` prefix then shows 8 chars. |
| B2.1 | Clickable `<tr onClick>` replaced with a real `<Link>`/`<button>` in the primary cell on runs + usage-history tables; focus-visible styling. |
| B2.3 | Pane-resizer separators get `aria-valuenow` / `aria-valuemin` / `aria-valuemax` / `aria-controls`. |
| B2.9 | `workspaces/[workspaceId]` counts `"analyzing"` files correctly; `runs/new` gets error states for `listWorkspaces` / `getModes`. |
| B1.5 | Stray `⚠` glyphs removed; the hard-coded `"Estimated: ~$0.15–0.35 · ~20–40s"` string now derives from `resourceLimits`. |
| B3.2 | `report/page.tsx` uses `react-markdown` + `remark-gfm` with a `components` map; a `withCitations()` helper keeps `[SQ-n]` tokens as `CitationPopover` triggers. (**Bold renders now.**) |
| A1.3 | Added `app/error.tsx`, `app/not-found.tsx`, `app/(app)/loading.tsx`. |

---

## Follow-ups (not in this pass)

1. `pnpm install` to regenerate `pnpm-lock.yaml` (this pass used npm; see repo-hygiene H3 — pick one manager).
2. Real auth: login page, token persistence, 401 → redirect, refresh. Plumbing is in place (`lib/auth/token.ts`, `setToken`).
3. Wire `API_URL` and point the BFF at a running `apps/api` once the backend exists.
4. Deferred quality items from `frontend.md` §D: border-radius token migration, `runs/[runId]/page.tsx` &
   `PlanTimeline.tsx` splits, `StatusBadge` decomposition, `lib/schemas` coverage beyond `getRun`.
