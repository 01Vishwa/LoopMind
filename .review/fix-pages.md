# Frontend page fixes — `apps/web/app/**`

Scope owned: `app/(app)/**`, `app/page.tsx`, and new `app/error.tsx`, `app/not-found.tsx`,
`app/(app)/loading.tsx`. No edits to `layout.tsx` (root), `app/api/**`, `components/**`,
`lib/**`, or config/styles.

Type-check: ran `npx tsc --noEmit` (pnpm not on PATH). Result: **only one pre-existing
error, in a non-owned file** — `components/shared/ThemeToggle.tsx` (`next-themes` module
missing, review item A1.7). No errors in any owned/changed file.

---

## A1.2 — Duplicate subtree rendering

### `app/(app)/settings/layout.tsx`
Replaced the `hidden lg:flex` + `lg:hidden` twin trees (which mounted every settings page
and its `useResource` calls twice) with a single tree. Added a local `useMediaQuery`
hook (`(min-width: 1024px)`) that picks the layout class set and the `SettingsNav
horizontal` flag. `{children}` and `<SettingsNav>` now render exactly once.

### `app/(app)/runs/[runId]/page.tsx`
Added a local `useMediaQuery("(min-width: 768px)")`. Each pane (`PlanTimeline`,
`CodePane`, `ObservationPane` + pre-execution banner) is now built **once** into a
`const` and placed into either the desktop 3-pane layout or the mobile tab layout via a
JS conditional — no more CSS-hidden second copy, so only one lazy Monaco instance mounts.
Mobile tab bar is now gated on `!isDesktop` instead of `md:hidden`.

## A3.3 — Infinite polling against the stub (`runs/[runId]/page.tsx`)
- `isRunning` is now `RUNNING_PHASES.has(run.status.phase)` — an explicit allow-list of
  active phases. `"connecting"` and any unknown phase are treated as **not running**, so
  the stub that returns `"connecting"` forever no longer keeps the interval alive.
- Added `MAX_POLLS = 200` (~10 min) hard cap: `pollCount` state increments per tick and
  the poll effect bails once the cap is hit.
- Step-code / step-output fetches are now guarded by `hasSteps` (`run.steps.length > 0`)
  in addition to `runLoaded`, so step 0 is not fetched when there are no steps.
- **StatusBar `maxRounds: 0` → `—`**: NOT done here. `StatusBar` lives in
  `components/run/StatusBar.tsx` (not in my ownership) and it hard-codes
  `Round {Math.max(1, round)}/{maxRounds}`. The consumer passes `run.status.maxRounds`
  through unchanged. **Follow-up for the components owner**: in `StatusBar`, render `—`
  (or hide the round segment) when `maxRounds` is `0`/falsy.

## A3.6 — `useElapsedTimer` drift (`runs/[runId]/page.tsx`)
Hook signature changed to `useElapsedTimer(serverElapsedMs, running)`. Added
`useEffect(() => setElapsed(serverElapsedMs), [serverElapsedMs])` so every poll (which
replaces the `run` object, hence `run.status.elapsedMs`) resyncs the local counter.
Local +100ms ticking unchanged.

## A3.7 — Optimistic mutation rollback

### `app/(app)/saved-analyses/page.tsx`
Added `mutationError` state + an `errMsg` helper. `togglePause`, `handleDelete`, and
`handleReRun` now snapshot `previous = analyses`, wrap the call in try/catch, revert to
`previous` and set `mutationError` on rejection. `handleReRun` **only** applies the
`status: "succeeded"` / `lastRun` patch inside the try after the call resolves (was
unconditional). `rerunning` cleared in `finally`. Error shown as a red line above the
table. Mirrors the `settings/team/page.tsx` pattern.

### `app/(app)/runs/page.tsx`
`handleRetry` wrapped in try/catch (`e.preventDefault()` added). On success clears error
and navigates; on failure sets `retryError`, shown as a red line above the table. No more
unhandled rejection from the 501 endpoint.

## A3.5 — Runs list server-side sort (`app/(app)/runs/page.tsx`)
Removed the client-side `useMemo` sort of `page.items` (and the now-unused `useMemo`
import). The `listRuns` call now passes `sort: sortField` and `order: sortOrder`, and
both are in the `useResource` dep array, so ordering is server-driven and stable across
"Load more". Rows render straight from `page.items` (`rows`).
**Dependency**: relies on the data agent adding `sort`/`order` forwarding in
`lib/data/runs.ts` `listRuns` (+ the `RunListFilters` type). The params are passed via a
non-literal object so tsc does not flag the extra properties today; they are simply
ignored until the data layer forwards them.

## A4.1 — Run-mode union (`app/(app)/settings/profile/page.tsx`)
`runMode` / `savedRm` state retyped from `"precise" | "deep"` to `RunMode`
(`"precise" | "research"`), default value `"research"`. Radio option list changed to
`["precise", "research"]`. Visible label still "Deep research". `session.ts`
`ProfileUpdate.defaultRunMode` was already `RunMode` (updated by another agent), so
`updateProfile({ defaultRunMode: runMode })` is now type-correct end to end.

## A4.5 — `CopyableText` prefix (`runs/[runId]/provenance/page.tsx`)
Replaced `text.slice(7, 15)` with: strip a literal `"sha256:"` prefix only when present
(`text.startsWith("sha256:") ? text.slice(7) : text`), then `bare.slice(0, 8)` + `…` +
last 4. A bare hash is no longer mangled.

## B2.1 — Keyboard-operable table rows

### `app/(app)/runs/page.tsx`
Removed `<tr onClick>` / `handleRowClick` / `cursor-pointer`. The Query cell is now a
real `<Link href={/runs/:id}>` (block, truncating, with `focus-visible` outline) that
carries navigation. Retry button unchanged (still `stopPropagation` + `preventDefault`).

### `app/(app)/settings/usage/page.tsx` (billing history)
Removed `<tr onClick>` / `cursor-pointer`. The Period cell is now a `<button
aria-pressed>` with `focus-visible` outline that calls `setPeriodIdx`. Row keeps only the
selected-row background + hover.

## B2.3 — Pane resizer ARIA (`runs/[runId]/page.tsx`)
Both `role="separator"` handles now expose `aria-controls` (`run-plan-pane` /
`run-code-pane`, ids added to the pane divs), `aria-valuenow` (current px width),
`aria-valuemin`, `aria-valuemax` (200–400 / 300–800, extracted to `LEFT_MIN/MAX`,
`CODE_MIN/MAX` constants also used by the drag + keyboard clamps). `aria-orientation`
retained.

## B2.9 — Status filter + new-run error states

### `app/(app)/workspaces/[workspaceId]/page.tsx`
Added `analyzingCount` (`f.status === "analyzing"`). Header now appends `· N analyzing`.
"Analyze pending" button is disabled while `analyzingCount > 0`, shows the spinner +
"Analyzing…" during either local ingest or a server-side analyzing state, and the "all
analyzed" tooltip only shows when nothing is pending *or* analyzing.

### `app/(app)/runs/new/page.tsx`
`listWorkspaces` failure → full `ErrorState` (with retry) in place of the form.
`getModes` failure → inline warning banner with a Retry button above the mode grid.

## B1.5 — AI-aesthetic red flags (`runs/new/page.tsx`, `saved-analyses/page.tsx`)
- Removed the stray `⚠` glyph next to `<AlertTriangle>` in `runs/new` (partial-workspace
  warning) and in `runs/[runId]/page.tsx` kept the single `⚠` that is `aria-hidden` in
  the pre-execution banner (that one is the only visual marker there; lucide swap is out
  of scope for this pass — flagged if you want it changed).
- Removed the `⚠` prefix from the schedule-failure note in `saved-analyses`.
- `runs/new`: replaced the hard-coded `"Estimated: ~$0.15–0.35 · ~20–40s"` with
  `{formatCost(typicalSpendUsd(maxRounds, limits))}–{formatCost(estimatedCap)}` derived
  from `lib/config/resourceLimits`. Dropped the fabricated time range (no config source).

## B3.2 — Report markdown (`runs/[runId]/report/page.tsx`)
Deleted the hand-rolled `renderMarkdown` / `renderWithCitations` (bold was a literal
no-op). Now renders with `react-markdown` + `remark-gfm`. A `components` map keeps the
existing visual style (display/heading fonts, `text-body`, list, code, table, blockquote
treatments). Citation support: a `withCitations()` helper walks rendered children and
splits `[SQ-n]` tokens out of text nodes into `<button>` triggers wired to
`toggleCitation`; it is applied to every text-bearing renderer (`p`, `li`, `td`, headings,
`strong`, `em`) so citations nested in formatting still work. `CitationPopover` and the
sub-questions index are unchanged.

## A1.3 — Route boundaries (new files)
- `app/error.tsx` — client component, logs the error, `reset()` button, JetBrains-Mono
  heading + `vera-*` tokens, matches `ErrorState` styling.
- `app/not-found.tsx` — server component, "404 / Page not found", link back to
  `/workspaces`.
- `app/(app)/loading.tsx` — `<BlockSkeleton>` fallback for app-shell route transitions.

## A3.11 — Guarded clipboard
All `navigator.clipboard.writeText` calls under `app/**` replaced with `copyText()` from
`lib/utils/clipboard.ts` (already present), each surfacing failure in the UI:
- `report/page.tsx` — "Copy as Markdown" → "Copied!" / "Copy failed".
- `provenance/page.tsx` — `CopyableText` (icon → "Failed" text + `aria-label="Copy
  failed"`) and the Final Script "Copy" button ("Copy failed").
`grep` confirms no remaining `navigator.clipboard` usage in `app/`.

---

## Not done / follow-ups for other owners
- **StatusBar `maxRounds: 0`** — needs a change in `components/run/StatusBar.tsx` (see
  A3.3 above).
- **`listRuns` sort/order forwarding** — needs `lib/data/runs.ts` + `RunListFilters`
  (`lib/data/types.ts`) from the data agent (see A3.5).
- **`next-themes` missing** — pre-existing tsc error in `components/shared/ThemeToggle.tsx`
  (A1.7), untouched.
- Lucide-icon swap for the remaining `aria-hidden` `⚠` in the run-detail pre-execution
  banner was left as-is (purely decorative, screen-reader-hidden).
