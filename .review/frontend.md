# VERA `apps/web` — Frontend Code Review

Scope: `apps/web/**` (app/, components/, lib/, styles/, config). `.next/` ignored.
Every `.ts`/`.tsx` file in scope was read. Reference docs skimmed: `docs/UI.md`,
`docs/VERA_BACKEND_PLAN.md` §9, `docs/superpowers/specs/2026-08-22-vera-web-shell-design.md`.

Legend: **BUG** = wrong today · **INCOMPLETE** = expected scaffold gap · **QUALITY** = works but below bar.

---

## 0. Executive summary (top 10 by severity)

| # | Severity | Area | One-liner |
|---|----------|------|-----------|
| 1 | BUG | Design system | `vera-*` colour tokens defined **twice** and diverge; opacity/hover/ring utilities render the light palette in dark mode. |
| 2 | BUG | Data layer | `useRunStream` returns refs, not state → the SSE hook never triggers a re-render; it is non-functional as written. |
| 3 | INCOMPLETE | Architecture | Two disconnected API layers (`/api/*` Next stubs vs `/api/v1/*` rewrite to FastAPI) and **no auth-token plumbing** anywhere; backend expects JWT bearer. |
| 4 | BUG | Rendering | Settings layout and Run-detail page render their subtree **twice** (`hidden lg:flex` + `lg:hidden`) → double data fetches, two Monaco instances mount on every viewport. |
| 5 | BUG (a11y) | Tables | Row-as-link with `onClick`+`cursor-pointer` and no keyboard handler on Runs / Workspaces / Usage history / Saved Analyses (WCAG 2.1.1). |
| 6 | BUG (a11y) | Dialogs | `NewWorkspaceModal`, `DescriptionDrawer`, `CitationPopover`: `role="dialog"`/`aria-modal` with no focus trap, no initial focus, no focus restoration, inconsistent Esc — despite Radix Dialog being a dependency. |
| 7 | BUG | Report page | Hand-rolled markdown renderer while `react-markdown`+`remark-gfm` are installed; the bold transform is a literal no-op so **bold never renders**; lists only match `1./2./3.`. |
| 8 | BUG | Types | Run-mode vocabulary is inconsistent: `"research"` (modes/run schema) vs `"deep"` (`ProfileUpdate.defaultRunMode`, profile page). Profile save sends a value the rest of the app/back end doesn't accept. |
| 9 | BUG | Mutations | Optimistic mutations with no error handling/rollback in Saved Analyses (`handleReRun` marks "succeeded" regardless of result) and Runs `handleRetry` (unhandled rejection; endpoint is 501). Team page does it right — inconsistent. |
| 10 | QUALITY | Build/perf | `@types/react` 18 pinned against React 19 (type-check breakage); fonts loaded 3× (`next/font` + `<link>` + CSS `@import`); JetBrains Mono not via `next/font` → CLS on every heading. |

---

## A. Correctness / Architecture

### A1. Next.js App Router correctness

**A1.1 — QUALITY — Server vs client components.** Almost every page is `"use client"`,
including pure redirect shells that are already server components (`app/page.tsx`,
`app/(app)/settings/page.tsx`, the file redirect page — these three are correctly
server). But list pages (`workspaces/page.tsx`, `runs/page.tsx`, settings/*) could
fetch on the server; instead everything is client `useResource` + spinner. Acceptable
for a scaffold, but the "when the REST API lands, only the fetcher changes" comment in
`useResource.ts` bakes in client-only fetching.

**A1.2 — BUG — Duplicate subtree rendering in responsive layouts.**
- `app/(app)/settings/layout.tsx:266-281`: the `<div className="hidden lg:flex">` and
  `<div className="... lg:hidden">` **both** render `{children}`. Every settings page
  mounts twice; every `useResource` in `agent-defaults`, `usage`, `team`, `profile`
  fires twice. `SettingsNav` also mounts twice.
- `app/(app)/runs/[runId]/page.tsx:359-495`: `PlanTimeline`, `CodePane`, and
  `ObservationPane` are each rendered once in a `hidden md:flex` wrapper and again in a
  `md:hidden` wrapper. Two `<MonacoEditor>` (lazy) instances load on all viewports;
  CSS only hides one. Heavy perf + double-mount state bugs.
  Fix: render one instance, move it with CSS order / a single conditional, or gate on a
  `useMediaQuery`.

**A1.3 — INCOMPLETE — No route-level error/loading/not-found boundaries.** There is no
`error.tsx`, `loading.tsx`, or `not-found.tsx` anywhere under `app/`. A throw in any
page bubbles to the framework default. `useResource` covers data errors but not render
errors, bad params, or 404 runs.

**A1.4 — Next 15 async params: OK.** Server routes correctly type
`params: Promise<{...}>` and `await` them (`app/api/**`, file redirect page). Client
pages use `useParams()` with `params.runId as string` — acceptable but unsafe cast
(see A4).

**A1.5 — QUALITY — `export const dynamic` from a non-route module.**
`app/api/_lib/respond.ts:13` exports `dynamic = "force-dynamic"`; this only has an
effect in a `route.ts`/`page.tsx`. Each route re-declares it anyway, so harmless, but
misleading.

**A1.6 — QUALITY — Manual `<link>` font tags in the root `<head>`.**
`app/layout.tsx:27-33` hand-injects Google Fonts `<link>` **and** `next/font/google`
loads Inter **and** `styles/globals.css:6` `@import`s the same fonts. Three loaders,
duplicate network cost. JetBrains Mono (used by every `.text-display` heading and all
mono UI) is loaded only via `<link>`/`@import`, never `next/font`, so it is
render-blocking-then-swap → CLS. The spec explicitly says "Inter + JetBrains Mono via
`next/font/google`".

**A1.7 — QUALITY — Inline theme script.** `app/layout.tsx:34-50`
`dangerouslySetInnerHTML` with a static anti-flash script is a fine pattern (no user
input). But it reads `localStorage` key `vera-theme` while `ThemeToggle.tsx` also
writes `vera-theme` and `layout` toggles `.light` — three independent
`useState(false)` + `useEffect(localStorage)` reads (`ThemeSegmentedControl`,
`ThemeIconToggle`, the script). No shared context/event, so the two toggle components
can hold stale opposite state. `next-themes` is a dependency (per spec) and unused.

### A2. The `app/api/**` BFF routes

**A2.1 — INCOMPLETE — They do not proxy at all.** Every handler under `app/api/**`
returns a hard-coded empty payload or `501`. `app/api/_lib/respond.ts` acknowledges
this ("Every handler here is a **stub**… The real implementations proxy `apps/api`").
So there is currently **no** BFF: no upstream fetch, no header forwarding, no
`API_URL` usage in the route layer (only `next.config.ts` rewrites use it).

**A2.2 — BUG/INCOMPLETE — Two parallel, inconsistent API surfaces.**
- `lib/data/*` (the layer the UI actually uses) calls `/api/workspaces`, `/api/runs`,
  `/api/auth/me`, … → hits the Next **stub** handlers.
- `lib/api/client.ts` (dead — imported nowhere) and `lib/hooks/useRunStream.ts` call
  `/api/v1/...` → `next.config.ts:9-14` rewrites `/api/v1/:path*` →
  `${API_URL}/v1/:path*`, bypassing Next entirely and hitting FastAPI directly.
- `docs/VERA_BACKEND_PLAN.md` §9 lists the real endpoints as `/v1/...`. The frontend
  BFF path prefix (`/api/...` without `v1`) and the rewrite (`/api/v1/...`) disagree
  with each other and partially with the plan (e.g. plan: `GET /v1/files/{id}/description`;
  frontend: `/api/workspaces/:wsId/files/:fileId/description`).
  Decide on one surface.

**A2.3 — INCOMPLETE — No auth anywhere.** `AuthProvider` has no notion of a token.
`lib/data/http.ts` sends no `Authorization` header. The `/api/v1/*` rewrite forwards
nothing. `docs/VERA_BACKEND_PLAN.md:1150` shows `POST /v1/auth/login → JWT` (bearer,
not cookie). There is no login page, no token store, no 401 handling, no refresh flow.
`/api/auth/me` stub returns `200` with a blank user (`role: "viewer"`) so the app
always renders as a logged-in nobody; a real `401` is only mentioned in a TODO
comment.

**A2.4 — QUALITY — RFC 9457 shape is close but synthetic.** `respond.ts:problem()`
always emits `type: "about:blank"` and a locally-generated `traceId`
(`trace-<random>`), never the upstream trace id. `lib/data/http.ts` reads
`problem.detail ?? problem.title` correctly and `ApiError`/`RequestError` carry the
`problem` object — the client side is fine; the server side is a placeholder.

**A2.5 — INCOMPLETE — Upload/ingest contracts diverge from the plan.**
- `lib/data/workspaceFiles.ts:uploadWorkspaceFile` does a multipart `POST` to
  `/api/workspaces/:id/files`; the plan (`:1173-1174`) is a two-step presigned-URL +
  confirm flow.
- `ingestWorkspaceFiles` expects the full updated file list synchronously; the plan
  (`:1180-1181`) returns `202` + a separate `/ingest/status` poll endpoint.
  A BFF could bridge these, but the client types assume the simpler shape.

### A3. Data layer (`lib/data/**`, `lib/hooks/useRunStream`, `lib/stores/runStore`)

**A3.1 — BUG — `useRunStream` never re-renders.** `lib/hooks/useRunStream.ts:108-111`
returns `{ status: statusRef.current, events: eventsRef.current }` — both **refs**
mutated inside an effect. React is never told to re-render, so a consumer sees
`"connecting"` / `[]` forever. `flush()` pushes into `eventsRef.current` and calls the
store's `applyEvent` (Zustand subscribers do re-render), so the store path works but
the hook's own return value is dead. Needs `useState`/`useSyncExternalStore`.

**A3.2 — BUG — `useRunStream` re-hydration is unsafe and racy.**
- Lines 61-66: on a seq gap it does `fetch('/api/v1/runs/:id').then(r=>r.json())` and
  `useRunStore.getState().hydrate(data as RunStateDTO)` — **no Zod parse** (contrast
  `lib/api/client.ts:getRun` which does `RunStateDTOSchema.parse`), errors swallowed.
- The gap check `seq !== lastSeqRef.current + 1` also fires on the very first event
  after a reconnect where `lastSeqRef` is stale, causing spurious full re-fetches.
- `onerror` sets status `"error"` but EventSource auto-reconnects; the UI has no way to
  distinguish "reconnecting" from "dead".

**A3.3 — BUG — Run-detail page polls a stub forever.** `app/(app)/runs/[runId]/page.tsx:255`
`isRunning = run ? !["complete","failed","cancelled"].includes(run.status.phase) : false`.
The stub `app/api/runs/[runId]/route.ts` returns `phase: "connecting"`, so `isRunning`
is permanently true → `setInterval(…, 3000)` never clears, plus the step-code and
step-output resources refetch on every tick. `StatusBar` then shows `Round 1/0`
(`maxRounds: 0`) and `$0.00 / $0.00`. Also `stepIndex` 0 is fetched even when there
are no steps.

**A3.4 — QUALITY — `useResource` has no request cancellation.** `lib/data/useResource.ts`
uses only a `cancelled` boolean; the in-flight `fetch` is never `AbortController`-
aborted, so slow responses still complete and are discarded. Ordering across dep
changes is handled (each effect owns its flag), but overlapping identical fetches are
wasted. `keepPreviousData` is in the dep array (`:75`) alongside `[...deps, nonce]`,
and `exhaustive-deps` is disabled — the `fetcher` closure is not a dep, so stale-
closure bugs are possible at any call site that closes over changing values without
listing them (many do; most currently list the right deps by luck).

**A3.5 — BUG — Runs list sorts one server page while paginating.**
`app/(app)/runs/page.tsx:1511-1521` sorts `page.items` client-side; `1477-1483`
writes `sort`/`order` to the URL; but `lib/data/runs.ts:listRuns` never sends a sort
param. With "Load more" (`:1729`) increasing `limit`, the visible order is
"server order of first N rows, then re-sorted locally" — wrong global ordering and it
silently changes as you page.

**A3.6 — QUALITY — `useElapsedTimer` drifts.** `app/(app)/runs/[runId]/page.tsx:118-133`
seeds `elapsed` from `startMs` once at mount and ticks +100ms locally; it never
resyncs to the server's `run.status.elapsedMs` when a poll returns, so it drifts.

**A3.7 — BUG — Optimistic mutations without rollback / error handling.**
- `app/(app)/saved-analyses/page.tsx:54-63` `handleReRun`: sets status to
  `"succeeded"` and `lastRun = now` **unconditionally** after `await rerunSavedAnalysis`
  (which returns `void`); a failed rerun still shows green. No try/catch.
- Same file `togglePause` (`:38-46`), `handleDelete` (`:48-52`): optimistic, no
  try/catch, no revert — a rejected request leaves the UI lying.
- `app/(app)/runs/page.tsx:1471-1475` `handleRetry`: `await retryRun(runId)` then
  `router.push` — `retryRun` hits a `501` endpoint, so this throws an unhandled
  rejection and nothing happens visibly.
- Contrast `app/(app)/settings/team/page.tsx:1009-1031` which snapshots `previous`
  and rolls back correctly. The pattern should be uniform.

**A3.8 — QUALITY — `AuthProvider.refresh()` double-fetches.**
`lib/auth/AuthProvider.tsx:26-29` calls both `setSessionKey(k+1)` (which is a
`useResource` dep → refetch) **and** `retry()` (bumps the nonce → another refetch).

**A3.9 — QUALITY — Duplicated helpers.** `formatBytes` is re-implemented in
`DescriptionDrawer.tsx`, `FileGrid.tsx`, `ObservationPane.tsx`, `UploadDropzone.tsx`
(and `provenance/page.tsx` inlines `(x/1024).toFixed(1) KB`). `fmtTokens` exists in
`usage/page.tsx`, `UsageChart.tsx`, `CostBreakdown.tsx` with three slightly different
rules. Whitespace-table parsing is in both `lib/data/runDetail.ts:parseTabularOutput`
and `components/run/ObservationPane.tsx:DataframeRenderer`. `lib/utils/` is the home
for these.

**A3.10 — QUALITY — `lib/api/client.ts` is entirely dead code** (imported nowhere)
and duplicates domain types with a *different* shape from `lib/data/*`
(`RunSummary`, `CreateRunRequest`, its own `ApiError`, `cancelRun` hitting a
non-existent `/api/v1/runs/:id/cancel`). Same for the exported `eventLog` const in
`useRunStream.ts`. Delete or wire up.

**A3.11 — QUALITY — Clipboard writes are unguarded.** `navigator.clipboard.writeText`
is called with no try/catch and no fallback in `CodePane`, `ObservationPane` (n/a),
`provenance/page.tsx` (×3), `report/page.tsx`, `DescriptionDrawer` (×2),
`ProviderKeyCard`. Throws on insecure origins / denied permission → unhandled
rejection, no user feedback.

### A4. Type safety

**A4.1 — BUG — Run-mode union is inconsistent across the app.**
- `lib/config/modes.ts`: `RunMode = "precise" | "research"`.
- `lib/schemas/runSchemas.ts`: `z.enum(["precise", "research"])`.
- `lib/data/session.ts:ProfileUpdate.defaultRunMode`: `"precise" | "deep"`.
- `app/(app)/settings/profile/page.tsx:745`: `runMode` state is `"precise" | "deep"`,
  UI label "Deep research", saved via `updateProfile`.
  A saved profile emits `"deep"`, which no consumer of `RunMode` accepts.

**A4.2 — QUALITY — Unsafe casts instead of validation.**
- `lib/api/client.ts`: `handleResponse(res, (d) => d as Workspace[])` etc. — Zod is
  used for exactly one call (`getRun`). `lib/data/*` never validates a response
  (`getJson<T>` just casts). For a "type safety + schema validation with Zod" goal,
  the `lib/schemas` coverage is ~5% of the surface.
- `useRunStream.ts:64` `data as RunStateDTO`; `runStore.ts:227` `dto.phase as RunPhase`
  (unchecked `string` → union).
- `app/(app)/runs/[runId]/page.tsx:235` `params.runId as string` (and same in every
  client detail page) — `useParams` returns `string | string[] | undefined`.
- `CodePane.tsx:63` `handleEditorMount(editor: any, monacoInstance: any)` (eslint-
  disabled). Acceptable given Monaco, but `styles/monaco-theme.ts` already types this
  and is unused (the theme object is re-inlined in `CodePane`).

**A4.3 — QUALITY — Heuristic string parsing typed as structured data.**
`parseTabularOutput` / `DataframeRenderer` split stdout on `/\s{2,}/` and present it
as a table; any value containing a double space corrupts columns. Flagged in comments
as intentional, but there is no fallback signal to the user when parsing is wrong.

**A4.4 — QUALITY — `@types/react`/`@types/react-dom` are v18, `react` is v19.**
`package.json`. `tsc --noEmit` will surface JSX/ref type errors (e.g. React 19 changed
`ref` as a prop, `useRef` overloads). Bump to `@types/react@^19`.

**A4.5 — QUALITY — `CopyableText` assumes a 7-char prefix.**
`app/(app)/runs/[runId]/provenance/page.tsx:545` `text.slice(7, 15)` hard-codes
`"sha256:".length`; a bare hash renders mangled.

### A5. Auth / token handling / XSS

**A5.1 — GOOD — No token in `localStorage`.** Nothing stores a bearer/JWT in web
storage; there is no XSS token-exfiltration surface. API keys in `ProviderKeyCard` live
only in component state (and the save is a stub).

**A5.2 — INCOMPLETE — No auth model at all** (see A2.3). `can()` in `AuthProvider.tsx:32`
returns `!requiredRole` when `user` is undefined, so during the session fetch,
role-gated nav items fl/ hidden→shown. No logout. No route protection —
`app/(app)/layout.tsx` renders children regardless of auth state.

**A5.3 — GOOD — No `dangerouslySetInnerHTML` with dynamic content.** The only use is
the static theme script. The report "markdown renderer" builds React nodes (no
`innerHTML`), so it is XSS-safe (just broken — see B).

**A5.4 — QUALITY — `ProviderKeyCard.handleTest`** simulates validation client-side by
comparing the key against `keyPrefix` (`:1324`) and `handleSave` just moves the raw key
into state. Obvious placeholder, but it *looks* like a working "Test connection",
which could mislead during demos.

---

## B. Frontend UI engineering quality

### B1. Design system adherence

**B1.1 — BUG — The colour token system is defined twice and the two definitions
disagree.**
- `tailwind.config.ts:17-45` hard-codes hex values for `vera.*` (the **light**
  palette: `accent: "#2563EB"`, `accent-muted: "#DBEAFE"`, …). This is what generates
  `bg-vera-*`, `text-vera-*`, `border-vera-*`, **and every derived utility**:
  `bg-vera-accent-muted/30`, `border-vera-accent/20`, `ring-vera-accent`,
  `divide-vera-border`, `shadow-[0_0_0_1px_var(--vera-accent)]` (this last one is fine,
  it uses the var).
- `styles/globals.css:191-232` then **redefines a hand-picked subset** of those exact
  class names inside `@layer utilities` to point at `var(--vera-*)`, which *is*
  theme-aware (`:root` dark, `.light` light).
- Result: the ~40 classes re-declared in `globals.css` are theme-correct; **everything
  else** — notably all `/<opacity>` variants, `accent-hover`, `warning*` when used with
  opacity, `ring-*`, `accent-*` utilities — resolves to the **static light hex** in
  dark mode. Dark mode is the default. So e.g. `bg-vera-accent-muted/30` (used in
  `saved-analyses`, `usage`, `runs`) paints pale-blue `#DBEAFE` at 30% on a near-black
  surface.
  Fix: delete the hex block, define `vera.*` in the config as
  `"var(--vera-accent) / <alpha-value>"` (Tailwind v3 alpha syntax) or via a plugin,
  and drop the `globals.css` re-declarations.

**B1.2 — BUG — `darkMode: ["class"]` targets `.dark`; the app toggles `.light`.**
`tailwind.config.ts:4` vs `styles/globals.css:59` / `ThemeToggle.tsx:1866`. Any
`dark:` variant a future contributor writes is silently dead. Should be
`darkMode: ["selector", ':root:not(.light)']` or invert the class.

**B1.3 — QUALITY — Border-radius tokens exist and are ignored.** `tailwind.config.ts`
defines `borderRadius.card/input/badge` (6/4/2px). Not one component uses
`rounded-card`; instead there are **hundreds** of inline `style={{ borderRadius: "6px" }}`
(and `"4px"`, `"2px"`) *alongside* a `rounded` class. Enormous noise, guarantees
drift.

**B1.4 — QUALITY — Accent hue is internally inconsistent.**
Dark `--vera-accent: #6366F1` (indigo) but `--vera-accent-hover: #4F52D1`; light
`#4F46E5` → `#3730A3`. `tailwind.config.ts` says `accent: #2563EB` (blue),
`accent-hover: #3730A3` (indigo) — a blue button hovers to indigo. `.sidebar-logo-mark`
(`globals.css:440`) is an indigo→`#A855F7` purple gradient that **no component
references** (Sidebar uses a flat `bg-vera-accent` box). Pick one accent story.

**B1.5 — QUALITY — "AI aesthetic" red flags.**
- Purple gradient logo treatment (dead CSS, but it's in the design intent).
- `animate-glow-pulse` / `glow-pulse` keyframe (box-shadow pulsing in the accent
  colour) defined in `globals.css:260-263`; the "grounded, precise, lab-notebook"
  identity in `docs/UI.md §1.3` argues against ambient glow.
- Literal emoji sprinkled into UI copy next to real icons: `⚠` in
  `runs/new/page.tsx:1162` (right after an `<AlertTriangle>`), `DescriptionDrawer.tsx:248`,
  `saved-analyses/page.tsx:171`; `✓`/`✗` glyphs in `ProviderKeyCard.tsx:1336-1338`
  instead of lucide icons used everywhere else; `🔀`/`⚡` provider icons in
  `app/api/settings/providers/route.ts`.
- `runs/new/page.tsx:1192` hard-codes a fake `"Estimated: ~$0.15–0.35 · ~20–40s"`
  string not derived from `resourceLimits` config (which has all the numbers).

### B2. Accessibility (WCAG 2.1 AA)

**B2.1 — BUG — Clickable table rows are not keyboard-operable.**
`runs/page.tsx:1672` (`<tr onClick>` no `tabIndex`/`onKeyDown`),
`WorkspaceTable.tsx:873`, `usage/page.tsx:1391` (billing history rows),
`saved-analyses` name cell is a `<Link>` (ok) but the row hover/affordance implies
whole-row click. `FileGrid.tsx:389-396` **does** add `tabIndex={0}` + Enter handler —
so the correct pattern exists in the codebase and just isn't applied consistently.
Also: a `<tr tabIndex=0 onKeyDown=Enter>` is still a WCAG/ARIA smell — prefer a real
`<a>`/`<button>` in the primary cell with the rest of the row as `aria-hidden`
decoration, or `role="row"` + `role="gridcell"` semantics.

**B2.2 — BUG — Modals/drawers have no focus management.**
- `NewWorkspaceModal.tsx:470`: `role="dialog" aria-modal` — no focus trap, focus is
  not moved into the dialog on open, not restored to the trigger on close, **no Escape
  handler at all**. Background page remains scrollable/tabbable.
- `DescriptionDrawer.tsx:104`: `role="complementary"` (should be `dialog` for a modal
  slide-over with a backdrop), no focus trap, no Escape, no focus restoration.
- `CitationPopover.tsx:957`: has Escape (`:943-949`) but no trap, no initial focus,
  `aria-modal` on a non-trapping element.
- Radix `@radix-ui/react-dialog` is already a dependency and solves all of this.

**B2.3 — BUG — Pane resizers missing required ARIA.**
`app/(app)/runs/[runId]/page.tsx:403-411, 432-440`: `role="separator"` + `tabIndex={0}`
+ arrow-key handlers, but no `aria-valuenow` / `aria-valuemin` / `aria-valuemax` /
`aria-controls`. A focusable separator that resizes must expose its value. Also
`aria-orientation="vertical"` on a horizontally-dragged divider is arguably inverted
(separator orientation = the line's orientation, which is vertical here — that part is
ok, but pair it with the value attrs).

**B2.4 — BUG — `ObservationPane` live region floods screen readers.**
`components/run/ObservationPane.tsx:337-343`: `aria-live={streaming ? "polite" : "off"}`
wraps the **entire** scroll container holding all accumulated stdout. Every `exec.stdout`
chunk re-announces the whole buffer. Announce only appended deltas, or use a visually-
hidden log region that receives just the new lines.

**B2.5 — QUALITY — `UploadDropzone` error affordance.**
`components/workspace/UploadDropzone.tsx:746-755`: `<AlertCircle aria-label={entry.error}>`
with a child `<title>` — lucide icon components don't reliably render a `<title>`
child, and `entry.error` may be `undefined` (→ `aria-label="undefined"` string in some
browsers). Put the error text in visible copy under the row, and use `role="alert"`.

**B2.6 — QUALITY — Icon-only buttons: mostly good.** `Breadcrumbs`, `Sidebar`,
`StatusBar`, `VerdictBanner`, `CodePane`, most drawers add `aria-label`/`title`.
Exceptions: `DescriptionDrawer.tsx:256` "Diff" button (icon+text, ok), the sheet-tab
buttons `:166` have no `role="tab"`/`aria-selected` (contrast `PlanTimeline.tsx:571`
which does it right). `provenance/page.tsx:552` copy button `aria-label="Copy"` is
generic (which hash?).

**B2.7 — GOOD.** Skip link (`app/(app)/layout.tsx:71-76`), `:focus-visible` ring
(`globals.css:125-129`), `prefers-reduced-motion` block (`:430-437`), debounced
phase-only `aria-live` in `StatusBar` (`:1026-1029`), reduced-motion-aware shake in
`VerdictBanner` (`:1103-1120`), `aria-sort` in `WorkspaceTable`. These are done
thoughtfully.

**B2.8 — QUALITY — `FileGrid` sortable headers** (`:375-385`) are `<th onClick>` with
no `role="button"`, `tabIndex`, `aria-sort`, or keyboard handler. `runs/page.tsx`
sortable headers (`:1613-1640`) same. `WorkspaceTable` has `aria-sort` but still
`<th onClick>` only. None are keyboard-sortable.

**B2.9 — QUALITY — Empty/error/loading coverage is broad but uneven.**
- Good: `useResource` + `DataStates` gives most screens all three states.
- Gaps: `UsageChart` with `data = []` → `Math.max(...[], 0.01)` renders an empty
  plot area with no "no data" message (`components/settings/UsageChart.tsx:1754`).
  `runs/new/page.tsx` never shows an error state for `listWorkspaces`/`getModes`
  failures — it just renders empty selects. `saved-analyses` `handleReRun` shows no
  spinner-then-error, only optimistic success.
- `app/(app)/workspaces/[workspaceId]/page.tsx:1556` filters files by
  `f.status === "pending"` but `DescriptionStatus` is `"pending" | "analyzing" | "ready"`
  — files mid-`"analyzing"` are counted as neither pending nor ready in the header
  ("N files · M described"), and the "Analyze pending" button won't reflect them.

### B3. Component architecture

**B3.1 — QUALITY — `app/(app)/runs/[runId]/page.tsx` is a 530-line client component**
with three custom hooks defined inline (`useElapsedTimer`, `usePaneSizes`), global
`window` keydown listeners, `document.body.style` mutation during drag, localStorage
I/O, and the full three-pane layout duplicated for mobile. Split: `<RunLayout>`,
`useResizablePanes` (own file), `<RunPanes>` data/presentation boundary.

**B3.2 — QUALITY — `report/page.tsx` reinvents markdown.** `renderMarkdown` /
`renderWithCitations` (`:827-895`) is a bespoke line-parser while `react-markdown` +
`remark-gfm` are installed and unused. It only handles `#`, `##`, `1./2./3.` lists,
and paragraphs. **`line.replace(/\*\*(.*?)\*\*/g, "**$1**")` (`:885`) replaces bold
markup with itself — a no-op — so `**bold**` renders as literal asterisks.** Nested
lists, tables, links, code spans, blockquotes all unsupported. Use `react-markdown`
with a custom `text`/link renderer for `[SQ-n]`.

**B3.3 — QUALITY — `PlanTimeline.tsx` (935 lines) mixes 6 sub-components, a keyboard
nav model, a diff viewer (embeds `CodePane`), and two view modes in one file.**
`BacktrackedStep`, `RoundView`, `BacktrackDividerInline`, `FileAnalysisRow`,
`PlanningPlaceholder` should be separate files; the `handleKeyDown` roving-tabindex
logic (`:537-556`) belongs in a `useListboxNavigation` hook.

**B3.4 — QUALITY — Data/presentation coupling.** Presentational components import from
the data layer and define API-shaped types:
- `components/settings/ModelSelector.tsx` exports `ModelOption` which `lib/data/providers.ts`
  then imports (`:258`) — the dependency arrow points the wrong way (data → component).
- `components/report/CitationPopover.tsx` exports `SubQuestion`, imported by
  `lib/data/report.ts`.
- `components/run/PlanTimeline.tsx` exports `TimelineLogEntry`, imported by
  `lib/data/runDetail.ts`.
  Domain types should live in `lib/` (or `lib/schemas`) and flow outward.

**B3.5 — QUALITY — `StatusBadge` is a 12-status switchboard** (`:1782-1800`) that also
renders a progress bar + ETA. It conflates "run status", "file description status",
"verdict", and "workspace status" enums into one `BadgeStatus` union — a change to any
one domain touches this shared file. Consider a base `<Badge tone=…>` + per-domain
thin wrappers.

**B3.6 — QUALITY — Local mirror-state pattern is copy-pasted 4×** with subtle
differences: `workspaces/page.tsx`, `workspaces/[workspaceId]/page.tsx`,
`saved-analyses/page.tsx`, `settings/team/page.tsx` each do
`const [x, setX] = useState([])` + `useEffect(() => { if (data) setX(data) }, [data])`
so they can mutate optimistically. Extract a `useMirroredResource` /
`useOptimisticList` hook so rollback semantics are uniform (see A3.7).

**B3.7 — QUALITY — Responsive.** Mostly sound (grid/flex, `max-w`, `overflow-x-auto`
wrappers on tables). Concerns: the run-view three-pane duplication (A1.2); fixed pixel
pane widths persisted to localStorage with no viewport clamp on read
(`usePaneSizes:145-150` reads a stored `480` even on a 375px screen — though mobile
uses the tab layout, so low impact); `DescriptionDrawer` is `max-w-[500px]` and
`w-full` — on a 320px phone the schema table (`min-w` cells) will force horizontal
body scroll inside the drawer (it has `overflow-y-auto` but the table wrapper is
`overflow-x-auto`, so ok — verify).

---

## C. Positive notes

- `lib/data/http.ts` error normalisation (transport vs HTTP vs malformed-JSON) is clean
  and consistent.
- `useResource` `keepPreviousData` for polling is the right instinct.
- Accessibility fundamentals (skip link, focus-visible, reduced-motion, debounced live
  regions) show real care — see B2.7.
- `lib/config/*` centralisation (strings, modes, file types, roles, resource limits) is
  good separation; `fileTypes.ts` deriving both the dropzone `accept` map and the
  human list from one array is exactly right.
- Route-handler stubs return correctly-shaped empty payloads so the UI degrades to
  empty states instead of crashing — a deliberate, sensible scaffold choice.
- `formatCost` / `formatRelativeTime` / `formatDuration` are properly centralised with
  "never hand-roll at the call site" comments (mostly honoured).

---

## D. Suggested fix priority

1. Collapse the colour-token system to one source of truth (B1.1, B1.2). Highest
   visual impact, touches every screen.
2. Remove the duplicate-subtree rendering (A1.2) — perf + correctness.
3. Decide the API/auth architecture: one surface, token plumbing, real proxy (A2).
4. Make `useRunStream` actually work or delete it + `runStore` + `lib/api/client.ts`
   until SSE is wired (A3.1, A3.2, A3.10).
5. Keyboard access for row-links, focus traps for dialogs (B2.1, B2.2) — use Radix.
6. Unify optimistic-mutation error handling (A3.7, B3.6).
7. Replace the report markdown renderer with `react-markdown` (B3.2).
8. Reconcile the run-mode union (A4.1); bump `@types/react` to 19 (A4.4); fonts via
   `next/font` only (A1.6).
