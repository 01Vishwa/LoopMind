# Frontend component fixes — apps/web/components/**

Scope owned: `apps/web/components/**` (excluding `shared/ThemeToggle.tsx`).
`pnpm`/`tsc --noEmit` run: only two **pre-existing** errors remain, both outside my scope
(`app/(app)/runs/page.tsx` sort union, `ThemeToggle.tsx` missing `next-themes`). No new
type errors introduced by these changes.

## Shared utils created (contracts matched; another agent later overwrote with richer versions — compatible)
- `lib/utils/clipboard.ts` → `copyText(text): Promise<boolean>`
- `lib/utils/formatBytes.ts` → `formatBytes(n): string`
- `lib/utils/formatTokens.ts` → `formatTokens(n): string`

## B2.2 — Dialog/drawer focus management via Radix
- **NewWorkspaceModal.tsx**: rebuilt on `@radix-ui/react-dialog`
  (Root/Portal/Overlay/Content/Title/Close). Focus trap, initial focus (forced to the
  `#ws-name` field via `onOpenAutoFocus`), focus restoration, Escape, scroll lock now
  free. Props unchanged (`open`, `onClose`, `onCreated`). `onOpenChange` calls `onClose`
  on any dismiss. Submit behaviour identical. Error `<p>` now `role="alert"`.
- **DescriptionDrawer.tsx**: converted from `role="complementary"` + hand-rolled backdrop
  to Radix Dialog with Content styled as a right-side sheet (`fixed right-0 top-0 bottom-0
  max-w-[500px]`). Escape/focus-trap/restoration free. `role="complementary"` dropped.
  Diff/tabs/schema UI preserved. Props unchanged.
- **CitationPopover.tsx**: it is neither anchored to a citation nor centered (fixed
  `right-4 top-1/4`, has a backdrop, `anchorRect` prop was never used) — converted to
  Radix **Dialog** (keeps the modal-with-backdrop behaviour and existing Escape).
  Removed hand-rolled `aria-modal` + keydown listener. `anchorRect` prop kept in the
  interface for backward compat (still unused, as before).

## B2.4 — ObservationPane live region
Scroll container is now `aria-live="off"`. Added a visually-hidden
`<div className="sr-only" role="log" aria-live="polite">` that receives only the newly
appended delta (`output.slice(prevOutput.length)`) while `streaming`. Delta cleared when
streaming stops.

## B2.5 — UploadDropzone error affordance
Removed `<AlertCircle aria-label={entry.error}><title>`. Row wrapper restructured: icon
is now `aria-hidden`; a visible `<p role="alert">` renders under the row with
`entry.error ?? "Upload failed. Please try again."` (guards undefined). `done` state icon
got `aria-label="Uploaded"`.

## B2.6 — Tab semantics + icon-only buttons
- DescriptionDrawer sheet tabs: `role="tablist"` / `role="tab"` / `aria-selected` /
  `aria-controls` / roving `tabIndex`; the schema panel is now `role="tabpanel"` with
  `aria-labelledby` (only when sheets exist), mirroring `PlanTimeline.tsx`.
- Scanned components for icon-only buttons missing labels — the flagged ones
  (Breadcrumbs, Sidebar, StatusBar, VerdictBanner, CodePane) already had labels; no
  additional gaps found. UsageChart/FileGrid/WorkspaceTable new sort controls carry text
  labels.

## B2.8 — Sortable headers + row keyboard access
- **FileGrid.tsx**: `<th onClick>` → `<th aria-sort>` containing a real nested
  `<button onClick={handleSort}>`. Rows: added `role="button"`, Space key (with
  `preventDefault`) alongside the existing Enter handler.
- **WorkspaceTable.tsx**: header `<th>` keeps `aria-sort`, `onClick` moved to a nested
  `<button>`. Clickable rows: **removed `<tr onClick>`**; the name cell is now a real
  Next `<Link>` using the stretched-link pattern (`before:absolute before:inset-0`) so
  the whole row is a single keyboard-focusable link. Non-primary cells marked
  `aria-hidden`. The "Resume setup" CTA cell is `relative z-10` so it stays clickable
  above the overlay; its `stopPropagation` hack removed (no longer needed).

## B1.5 — Emoji → lucide icons
- **ProviderKeyCard.tsx**: `✓`/`✗` text glyphs → `Check` / `X` lucide icons.
- **DescriptionDrawer.tsx**: `⚠` in "Script error — regenerating" → `<AlertTriangle>`.

## A5.4 — ProviderKeyCard.handleTest honesty
`ConnectionStatus` union changed from `"connected" | "invalid" | "none"` to
`"saved" | "none"` (internal type, not exported). `handleTest` no longer fakes a green
"Connected" state from a client-side prefix check — it sets a muted `testNote`:
"Connection testing isn't available yet — the key is stored but unverified." Header badge
shows "Key saved (unverified)" / "No key" in muted colour with an icon. Clear
NOT-YET-WIRED comment added.

## B2.9 — UsageChart empty state
`data.length === 0` now renders a bordered-dashed "No usage data yet" panel (icon +
copy) instead of an empty plot area driven by `Math.max(...[], 0.01)`. Also switched the
local `fmtTokens` to the shared `formatTokens`.

## A3.11 — Clipboard guards
`navigator.clipboard.writeText` replaced with `copyText()` from `lib/utils/clipboard.ts`
in **CodePane.tsx**, **DescriptionDrawer.tsx** (×2), **ProviderKeyCard.tsx**. Failure is
surfaced inline:
- CodePane: copy button shows "Copy failed" in the insufficient colour for 2 s.
- ProviderKeyCard: copy button swaps to an `X` icon + "Copy failed" title/label.
- DescriptionDrawer: copy only flips to the "Copied" check on success.

## CodePane theme
Inlined `defineTheme` object replaced with an import of `catppuccinMochaTheme` from
`@/styles/monaco-theme` (`@/styles/*` alias verified in tsconfig). Theme name string
`"catppuccin-mocha"` and all runtime behaviour unchanged.

---

## Prop-contract changes the pages agent must know
**None.** All public component props are backward-compatible:
- `NewWorkspaceModal` — same props; it no longer early-returns `null` when
  `open === false` (Radix handles mount), but renders nothing visible — safe to keep
  mounted.
- `DescriptionDrawer`, `CitationPopover`, `UploadDropzone`, `FileGrid`, `WorkspaceTable`,
  `ObservationPane`, `CodePane`, `UsageChart`, `ProviderKeyCard` — public prop
  interfaces unchanged. `CitationPopover.anchorRect` remains in the type (still unused).
- `ProviderKeyCard`'s internal `ConnectionStatus` type changed but it was never exported.

## Notes / follow-ups not in scope
- `ObservationPane`, `FileGrid` still carry local `formatBytes` copies (A3.9) — left as-is
  since only DescriptionDrawer was in the emoji/util task; trivial follow-up to switch
  them to `lib/utils/formatBytes`.
- `CostBreakdown.tsx` still has its own `fmtTokens` (A3.9) — out of the B2.9 "UsageChart
  only" scope.
