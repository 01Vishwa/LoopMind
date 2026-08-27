# Frontend design-system fixes

Scope: `apps/web` colour tokens, dark-mode selector, accent hue, fonts, theme
provider, Monaco theme. Owned files only.

## Changes

### `apps/web/styles/globals.css`
- **B1.1** Removed the `@import url('https://fonts.googleapis.com/...')` font line.
- **B1.1** Rewrote the token system to a single source of truth. Every `--vera-*`
  token is now a space-separated RGB channel triple named `--vera-<name>-rgb`
  (e.g. `--vera-accent-rgb: 99 102 241;`). A block of `--vera-<name>` aliases
  wraps each triple back into `rgb(var(--vera-<name>-rgb))` so existing raw
  `var(--vera-*)` references in CSS and inline styles keep working. `.light` now
  only re-declares the `*-rgb` triples.
- **B1.1** Deleted the hand-written `@layer utilities` colour re-declaration block
  (`.bg-vera-*`, `.text-vera-*`, `.border-vera-*`) — Tailwind now generates these
  and they are theme-aware including opacity/ring/divide/hover variants.
- **B1.4** Accent reconciled to indigo everywhere: dark `--vera-accent` `#6366F1`
  with hover `#4F46E5` (a darker step of the same hue, was `#4F52D1`); light
  accent `#4F46E5` with hover `#4338CA` (was `#3730A3`). `--vera-accent-glow` is
  now `rgb(var(--vera-accent-rgb) / 0.15)` (derived, no separate hex).
- **B1.5** Deleted `@keyframes glow-pulse` and `.animate-glow-pulse`
  (grep: only self-references in this file). Deleted `.sidebar-logo-mark`
  purple-gradient rule (grep: referenced nowhere; `Sidebar.tsx` uses a flat
  `bg-vera-accent` box).
- **A1.6** All `font-family` declarations (`body`, `.text-*`, `.vera-input`,
  `.vera-btn-*`, `.vera-table th`) now reference `var(--font-sans)` /
  `var(--font-mono)` instead of literal `'Inter'` / `'JetBrains Mono'`.

### `apps/web/tailwind.config.ts`
- **B1.1** Every `vera.*` colour is now `rgb(var(--vera-<name>-rgb) / <alpha-value>)`
  via a small `channel()` helper. `accent-glow` kept as a fixed-alpha
  `rgb(var(--vera-accent-rgb) / 0.15)`.
- **B1.2** `darkMode` changed from `["class"]` (targeted `.dark`, which the app
  never sets) to `["selector", ":root:not(.light)"]` so `dark:` variants track
  the real theme (dark = default, `.light` opts out).
- **A1.6** `fontFamily.sans` / `.mono` now reference `var(--font-sans)` /
  `var(--font-mono)`.

### `apps/web/app/layout.tsx`
- **A1.6** Removed the manual Google Fonts `<link>`/`<preconnect>` tags. Load
  **Inter** (`--font-sans`) and **JetBrains Mono** (`--font-mono`) via
  `next/font/google`; both variable classes applied to `<html>`.
- **A1.7** Removed the inline `dangerouslySetInnerHTML` anti-flash script —
  `next-themes` injects its own. Wrapped `children` in `<ThemeProvider>`
  (from `components/shared/ThemeToggle`). `suppressHydrationWarning` kept on
  `<html>`. `<head>` element removed (was only holding the deleted tags).

### `apps/web/components/shared/ThemeToggle.tsx`
- **A1.7** New exported `ThemeProvider` = `next-themes` `ThemeProvider` with
  `attribute="class"`, `defaultTheme="dark"`, `enableSystem={false}`,
  `storageKey="vera-theme"` (stable key kept), `disableTransitionOnChange`.
- **A1.7** `ThemeSegmentedControl` and `ThemeIconToggle` rewritten to use a
  shared `useIsLight()` helper backed by `useTheme()` from `next-themes` — no
  more 3 independent `useState` + `localStorage` reads, so the two toggles can
  no longer hold opposite stale state. `mounted` guard prevents hydration
  mismatch on `aria-pressed` / icon.
- Public exports unchanged (`ThemeSegmentedControl`, `ThemeIconToggle`,
  `ThemeToggle`) so `Sidebar.tsx` is unaffected; `ThemeProvider` added.

### `apps/web/package.json`
- **A1.7** Added `next-themes` `^0.4.4` to dependencies.
- **A4.4** `@types/react` and `@types/react-dom` bumped `^18.3.x` → `^19`.

### `apps/web/styles/monaco-theme.ts`
- Now exports two complete, typed themes: `veraMonacoDark` (Catppuccin Mocha,
  `editor.background` aligned to `--vera-code-bg` `#11111B`) and `veraMonacoLight`
  (Catppuccin Latte). Added `MonacoTokenRule`, `MonacoEditorNamespace` types,
  theme-name constants (`VERA_MONACO_DARK` / `VERA_MONACO_LIGHT`), and helpers
  `defineVeraMonacoThemes(monaco)` / `veraMonacoThemeName(isLight)`.
- `catppuccinMochaTheme` retained as an alias of `veraMonacoDark` for
  backwards compatibility. `MonacoThemeData.base` widened to include `hc-light`.
- `CodePane.tsx` NOT edited (still inlines its own theme); this module is now
  ready for it to import.

### `apps/web/postcss.config.mjs`
- No change needed (already `tailwindcss` + `autoprefixer`).

## Verification

- `pnpm`/`npm` and `node_modules` for `apps/web` are **not installed** in this
  environment (`next-themes` absent), so `pnpm -C apps/web type-check` could not
  be run. Install deps then run it. Expected follow-ups: none anticipated beyond
  the new `next-themes` import resolving.
- Grep confirmed no app code references `glow-pulse`, `animate-glow-pulse`, or
  `sidebar-logo-mark`.
- Grep confirmed all raw `var(--vera-*)` usages in non-owned files
  (`CodePane`, `ObservationPane`, `PlanTimeline`, `ProviderKeyCard`, `EmptyState`,
  `app/(app)/layout.tsx`, `runs/new/page.tsx`) still resolve via the retained
  `--vera-*` colour aliases.
- No `dark:` variant is currently used anywhere in `apps/web`, so the
  `darkMode` selector change carries no regression risk for existing markup.

## Downstream contract (other agents / consumers must adapt)

1. **New CSS custom properties.** The canonical tokens are now
   `--vera-<name>-rgb` (space-separated `R G B` channels). The old
   `--vera-<name>` names still exist as **aliases** (`rgb(var(--vera-<name>-rgb))`),
   so raw `var(--vera-accent)` etc. keep working. If any agent adds new theme
   tokens, define the `-rgb` triple (in both `:root` and `.light`) **and** the
   alias, and add the Tailwind colour as
   `rgb(var(--vera-<name>-rgb) / <alpha-value>)`.
2. **Do not re-add `@layer utilities` colour classes** in `globals.css` — Tailwind
   owns `bg-/text-/border-/ring-/divide-vera-*` now. Removed classes behave
   identically plus gain opacity/hover/theme-awareness.
3. **`darkMode` is `selector` / `:root:not(.light)`.** `dark:` variants are now
   live and mean "not light mode". Anyone writing `dark:` utilities: base classes
   are the dark (default) look, `dark:` is redundant; use unprefixed for dark and
   (rare) a `.light`-scoped override or `[&:is(.light_*)]` for light-only tweaks.
   `.dark` class is NOT used.
4. **Accent hue is indigo** (`#6366F1` dark / `#4F46E5` light), not blue
   (`#2563EB`). `accent-hover` is same-hue darker. Any mockups/screenshots
   referencing blue `#2563EB` are stale.
5. **Fonts.** Inter → CSS var `--font-sans` (was `--font-inter`), JetBrains Mono
   → `--font-mono`, both via `next/font`. No `<link>` or `@import` for fonts.
   `--font-inter` no longer exists. Use `font-sans` / `font-mono` Tailwind
   classes or the `--font-*` vars; never hard-code `'Inter'` / `'JetBrains Mono'`.
6. **Theme state = `next-themes`.** Read/write theme via `useTheme()` from
   `next-themes` only. Do not read/write `localStorage['vera-theme']` directly
   and do not toggle `.light` on `<html>` manually. Storage key is still
   `vera-theme`; values `"dark"` / `"light"`. Provider is
   `ThemeProvider` exported from `@/components/shared/ThemeToggle`, mounted in
   `app/layout.tsx`. The inline anti-flash script is gone.
7. **`monaco-theme.ts` export shape changed.** `catppuccinMochaTheme` still
   exported (now an alias). New: `veraMonacoDark`, `veraMonacoLight`,
   `VERA_MONACO_DARK`, `VERA_MONACO_LIGHT`, `defineVeraMonacoThemes(monaco)`,
   `veraMonacoThemeName(isLight)`, and types `MonacoTokenRule` /
   `MonacoEditorNamespace`. Whoever wires `CodePane` to this module should call
   `defineVeraMonacoThemes` on mount and switch via `veraMonacoThemeName` on
   theme change (pair with `useTheme()`), replacing the inlined
   `defineTheme("catppuccin-mocha", …)`.
8. **`package.json`** gained `next-themes`; `@types/react*` are `^19`. Run a
   fresh install / lockfile update.
