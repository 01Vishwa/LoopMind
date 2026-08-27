# VERA Web — Slice 1: Shell + Design Tokens

**Status:** Approved
**Companion doc:** `docs/UI.md` (full UI spec — this covers only Build Order §17 Slice 1)

## Purpose

Stand up `apps/web` as a running Next.js app with the application shell (sidebar, routing, breadcrumbs), the VERA design token system, typography, and dark mode. This is the foundation slice: no API calls, no SSE, no live data. It proves the app loads, navigates, and looks intentional per `docs/UI.md` §17 row 1.

Later slices (workspace CRUD, run view, SSE integration, etc.) build on top of this shell and are out of scope here.

## Stack

- Next.js 15 (App Router), React 19, TypeScript 5.6 — `strict: true`, `noUncheckedIndexedAccess: true`, no `any`
- Tailwind v4
- shadcn/ui primitives (Button, Skeleton, Sheet, Separator — only what the shell needs)
- Fonts: Inter (400/500/600) + JetBrains Mono (400/500/700) via `next/font/google`
- Dark mode via `next-themes`, persisted to `localStorage`
- pnpm, inside the existing `pnpm-workspace.yaml` / `turbo.json` monorepo

## File structure

```
apps/web/
├── app/
│   ├── layout.tsx              # fonts, ThemeProvider, sidebar shell
│   ├── page.tsx                # redirect → /workspaces
│   ├── workspaces/page.tsx     # empty state
│   ├── runs/page.tsx           # empty state
│   ├── saved-analyses/page.tsx # empty state
│   └── settings/page.tsx       # minimal placeholder
├── components/
│   ├── shared/Sidebar.tsx
│   ├── shared/Breadcrumbs.tsx
│   ├── shared/EmptyState.tsx
│   └── ui/                     # shadcn primitives, not modified inline
├── lib/utils/cn.ts
├── styles/globals.css          # --vera-* tokens, light + dark
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

## Design tokens

All `--vera-*` custom properties from `docs/UI.md` §2.1 defined on `:root` (light) and swapped under a dark-mode selector per the doc's dark-mode rules (ink/paper invert, surface → `#1E1E2E`, accent/verified/insufficient/backtrack rotate to lighter counterparts). Typography scale, spacing (4px base unit), border radius (6/4/2px), and "shadows almost never" rules from §2.2–2.3 apply globally via Tailwind config + CSS variables.

## Components

**Sidebar** (`components/shared/Sidebar.tsx`)
- 240px expanded / 56px icon-only collapsed; collapses automatically under 1024px or via manual toggle; toggle state persisted to `localStorage`.
- Items: Workspaces, Runs, Saved Analyses, spacer, Settings, user email (from session — for this slice, a static placeholder value since auth isn't wired up yet).
- Active route: `--vera-accent-muted` background wash + 2px left border in `--vera-accent`.
- No badges, notification dots, or banners (per §3.1).

**Breadcrumbs** (`components/shared/Breadcrumbs.tsx`) — generic trail component in `--vera-muted` small text, segments clickable. For this slice it will just render single-segment trails (e.g. "Workspaces") since nested routes don't exist yet.

**EmptyState** (`components/shared/EmptyState.tsx`) — reusable: centered message + optional single CTA button, no illustration. Used by all four placeholder pages per §14.3's copy:
- `/workspaces`: "No workspaces yet. Create one to start analysing your data." + "New workspace" button (disabled/no-op in this slice — workspace creation ships in a later slice)
- `/runs`: "No analyses yet. Upload data and ask a question." + "New analysis" button (disabled/no-op)
- `/saved-analyses`: placeholder empty state, no CTA
- `/settings`: minimal static content (no empty state needed — it's a real, if sparse, page)

## Testing

No unit tests for this slice — it's pure layout and static empty-state content, which the project's own testing strategy (`docs/UI.md` §15) doesn't call for until domain components with real logic appear in later slices. Verification is manual: run the dev server, check nav routing, sidebar collapse/expand + persistence, dark-mode toggle + persistence, and the three responsive breakpoints from §12.1 (desktop/laptop/tablet/mobile) in a browser.

## Out of scope

File grid, upload dropzone, run view (three-pane layout, Plan Timeline, Code Pane, Output Pane), SSE (`useRunStream`), Zustand stores, TanStack Query, Monaco editor, API client / Zod schemas, report/provenance views. These are Slices 2–11 in `docs/UI.md` §17.
