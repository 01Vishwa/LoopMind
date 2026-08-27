# VERA — Complete UI Design & Implementation Prompt

### A production-grade brief for building the entire frontend

**Companion to:** `VERA_PRODUCT_STRUCTURE.md`, `VERA_IMPLEMENTATION_PLAN.md`
**Stack:** Next.js 15, React 19, TypeScript 5.6, Tailwind v4, shadcn/ui, Zustand, TanStack Query
**Status:** v1.0 — Ready to build

---

## Table of Contents

1. [Product Identity & Design Philosophy](#1-product-identity--design-philosophy)
2. [Design System — Token Specification](#2-design-system--token-specification)
3. [Application Shell & Navigation](#3-application-shell--navigation)
4. [Screen-by-Screen Specification](#4-screen-by-screen-specification)
5. [The Run View — The Core Experience](#5-the-run-view--the-core-experience)
6. [Component Library — Domain Components](#6-component-library--domain-components)
7. [Real-Time Data Architecture](#7-real-time-data-architecture)
8. [State Management](#8-state-management)
9. [API Integration & Type Safety](#9-api-integration--type-safety)
10. [Interaction Design & Micro-Interactions](#10-interaction-design--micro-interactions)
11. [Accessibility Requirements](#11-accessibility-requirements)
12. [Responsive Behaviour](#12-responsive-behaviour)
13. [Performance Budget](#13-performance-budget)
14. [Error, Empty & Loading States](#14-error-empty--loading-states)
15. [Testing Strategy](#15-testing-strategy)
16. [File Structure & Code Standards](#16-file-structure--code-standards)
17. [Build Order](#17-build-order)
18. [Anti-Patterns to Reject](#18-anti-patterns-to-reject)

---

## 1. Product Identity & Design Philosophy

### 1.1 What VERA is

VERA is a **verifiable data analysis platform**. An analyst uploads heterogeneous data files (CSV, XLSX, JSON, PDF, Markdown, SQLite), asks a natural-language question, and VERA's multi-agent system produces an answer by writing, executing, verifying, and self-correcting code — iteratively. The answer ships with the exact script, intermediate observations, verifier reasoning, and data hashes, so every number is reproducible.

### 1.2 Who uses it

Primary: **data analysts and operations leads** who currently wait days for ad-hoc pulls, or export to spreadsheets and get the answer wrong. They are technically literate but not developers. They care about speed, correctness, and being able to explain how a number was derived.

Secondary: **data platform engineers** who need to audit the agent's reasoning trail — what did it try, where did it fail, why did it backtrack.

### 1.3 The emotional thesis

The product's differentiator is not that it writes code — every copilot does that. The differentiator is **visible self-correction**. The user watches the agent plan, execute, judge its own work, catch a mistake, backtrack, and try a different approach. That moment — seeing it fail and fix itself in the open — is what builds trust. Every design decision should make that moment legible, not hide it.

**Three words:** Transparent. Grounded. Precise.

- **Transparent** — the process is always visible. No spinners that hide what's happening.
- **Grounded** — every claim traces to an execution. Citations are links, not decorations.
- **Precise** — the interface is typographically tight, information-dense, and never padded for the sake of looking friendly.

### 1.4 What VERA is NOT

It is not a chatbot. There is no chat bubble UI, no avatar, no "thinking…" animation. It is a structured analytical workbench. Think Bloomberg Terminal's information density married to Linear's clarity of purpose. The machine is a machine; the interface makes the machine's work legible, not anthropomorphized.

### 1.5 The visual signature

The single memorable element: **the Plan Timeline** — a vertical stepper in the left panel where completed steps stack, superseded (backtracked) steps appear struck-through and collapsed under a "backtracked" marker with the router's rationale, and the current step pulses subtly. This is the product's visual identity; it must be instantly recognizable and unlike anything in a standard dashboard template.

---

## 2. Design System — Token Specification

### 2.1 Colour palette

The palette is derived from the concept of a **lab notebook** — ink on matte paper, with precisely one accent for what deserves attention.

| Token | Hex | Role |
| --- | --- | --- |
| `--vera-ink` | `#1A1A2E` | Primary text, headings, nav |
| `--vera-paper` | `#FAFAF8` | Page background |
| `--vera-surface` | `#FFFFFF` | Cards, panels, drawers |
| `--vera-muted` | `#8B8B9E` | Secondary text, timestamps, labels |
| `--vera-border` | `#E5E5EA` | Dividers, card borders |
| `--vera-border-subtle` | `#F0F0F2` | Inner dividers, nested borders |
| `--vera-accent` | `#2563EB` | Links, active step, CTAs — one accent only |
| `--vera-accent-muted` | `#DBEAFE` | Accent background washes |
| `--vera-verified` | `#059669` | Sufficient verdicts, success |
| `--vera-verified-muted` | `#D1FAE5` | Verified background |
| `--vera-insufficient` | `#DC2626` | Insufficient verdicts, errors |
| `--vera-insufficient-muted` | `#FEE2E2` | Insufficient background |
| `--vera-backtrack` | `#D97706` | Backtrack markers, warnings |
| `--vera-backtrack-muted` | `#FEF3C7` | Backtrack background |
| `--vera-code-bg` | `#1E1E2E` | Code pane background (Catppuccin Mocha base) |
| `--vera-code-fg` | `#CDD6F4` | Code text |

**Dark mode:** invert `ink` and `paper`; `surface` becomes `#1E1E2E`; accent, verified, insufficient, backtrack hues rotate to their lighter counterparts for contrast. Dark mode is not optional — analysts staring at code output at 11 PM will switch.

### 2.2 Typography

| Role | Family | Weight | Size | Tracking |
| --- | --- | --- | --- | --- |
| **Display** | `JetBrains Mono` | 700 | 28 / 32px | −0.02em |
| **Heading** | `Inter` | 600 | 20 / 24px | −0.01em |
| **Body** | `Inter` | 400 | 14 / 20px | 0 |
| **Small / Label** | `Inter` | 500 | 12 / 16px | 0.02em |
| **Code / Output** | `JetBrains Mono` | 400 | 13 / 20px | 0 |
| **Monospace UI** | `JetBrains Mono` | 500 | 12 / 16px | 0.01em |

**Why JetBrains Mono for display:** the product *is* code execution. Using a monospace face at the display level signals that immediately, and it's distinctive — most analytical tools use a neutral sans. Inter for everything readable; JetBrains Mono for everything the machine produced.

### 2.3 Spacing & layout

- Base unit: `4px`. Every margin, padding, gap is a multiple.
- Max content width: `1440px`, centred.
- Panel-based layout (not card-grid). Panels fill height; content scrolls inside them.
- Border radius: `6px` on cards, `4px` on inputs, `2px` on inline badges. Never `rounded-full` except on avatars.
- Shadows: almost never. A single `shadow-sm` on floating popovers only. Depth is communicated through borders and background shifts, not elevation — this keeps the lab-notebook flatness.

### 2.4 Iconography

Lucide React, 16px default, 20px in navigation. Stroke width 1.5. Never filled icons. Never emoji.

### 2.5 Status Color Tokens

To ensure absolute consistency across all screens (Workspaces, Runs, Saved Analyses, Run Detail), status indicators must strictly map to these tokens:

- **`status-success` (green):** Ready, Succeeded. Uses `--vera-verified` text on `--vera-verified-muted` background.
- **`status-warning` (amber):** Partial, Pending, Backtracked, Failed-but-retryable. Uses `--vera-warning` text on `--vera-warning-muted` background.
- **`status-info` (blue):** Running, Ingesting, Executing, Analyzing. Uses `--vera-accent` text on `--vera-accent-muted` background. Must always be styled as a pill badge (dot + label pattern), never just a colored dot or plain text.
- **`status-error` (red):** Failed, Error, Insufficient. Uses `--vera-insufficient` text on `--vera-insufficient-muted` background.
- **`status-neutral` (gray):** Cancelled, Paused, Archived. Uses `--vera-muted` text on `--vera-border-strong` background.

### 2.6 Theming Rules & 'Console' Surfaces

The app shell (sidebar, tables, forms) uses the active theme (light or dark mode) as controlled by the user.

**The "Console" Exception:**
All code, log, and terminal surfaces — specifically the Run Detail code panel, execution output pane, and the File Inspector's Analyzer Script blocks — **always render in dark theme**, regardless of the app-wide mode.
These are distinct "console" surfaces representing the machine's inner workings. They use `--vera-code-bg` (Catppuccin Mocha base) and `--vera-code-fg` with a consistent border radius and monospace font, ensuring no jarring light/dark seams occur mid-screen.

### 2.7 Primary CTA Consistency

There is exactly one styling for primary calls to action: **Solid Indigo** (`bg-vera-accent text-white`, consistent padding, `rounded` 6px radius).
This applies to "New workspace", "New analysis", and "Start analysis". 
- Do not use washed-out lavender variants for primary actions. 
- The only acceptable variant of a primary CTA is the destructive-primary variant (e.g., "Cancel run" in solid red).

### 2.8 Table Row Interaction Patterns

Interaction patterns for tables must immediately signal their primary use case:

1. **Navigation Tables (e.g., Workspaces, Runs):** 
   - Primary use case: Navigate to detail view.
   - Pattern: Full-row clickability. The entire `<tr>` gets a hover tint (`hover:bg-vera-border-subtle/50`) and `cursor-pointer`. The primary identifier cell (e.g., Run ID) is styled as a link (`--vera-accent`) to reinforce navigability.
2. **Action Tables (e.g., Saved Analyses):** 
   - Primary use case: Take one of several actions on a specific item (Run, Edit, Pause, Delete).
   - Pattern: Explicit per-row buttons. The row itself does not navigate on click and retains a default cursor. Actions are discoverable via an explicit action column or visible icon buttons on hover.

---

## 3. Application Shell & Navigation

### 3.1 Layout anatomy

```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar (56px collapsed / 240px expanded)                  │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Logo (VERA monogram, JetBrains Mono, 20px)             ││
│  │                                                         ││
│  │ ── Workspaces                                          ││
│  │ ── Runs                                                ││
│  │ ── Saved Analyses                                      ││
│  │                                                         ││
│  │ ── ── ── ── ── ── (spacer)                             ││
│  │                                                         ││
│  │ ── Settings                                            ││
│  │ ── user@co.com                                         ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  Main content (fills remainder)                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

- Sidebar collapses to icon-only (56px) on `<1024px` or via toggle. State persists in `localStorage`.
- Active route gets a `--vera-accent-muted` background wash on the nav item and a 2px left border in `--vera-accent`.
- The sidebar is **not** a feature showcase. Three primary destinations, a settings link, and the user — that's the budget. No badges, no notification dots, no marketing banners.

### 3.2 Breadcrumb bar

Below the top edge of the main content, a breadcrumb trail in small text: `Workspaces / Payments Q3 / Runs / run-a1b2`.
- Every segment except the final (current) page must be styled as a clickable link with a consistent hover state (e.g., `--vera-muted` transitioning to `--vera-ink` on hover).
- The final (current) segment is plain text (`--vera-ink`) and non-clickable.
- Do not mix clickable and non-clickable historical segments.

### 3.3 Theme Toggle

The moon/sun icon in the top right controls the **app shell's light/dark mode only**.
- It does not affect Console surfaces (code/logs), which remain dark by design per §2.6.
- The toggle must include a tooltip ("Switch to dark mode" / "Switch to light mode") to make its function unambiguous.

---

## 4. Screen-by-Screen Specification

### 4.1 Workspace List (`/workspaces`)

**Purpose:** show the user's workspaces and let them create a new one.

**Layout:** a clean table, not a card grid. Columns: Name, Files (count), Last Activity (relative time), Status (ingesting / ready / partial). Sortable by any column.

**Empty state:** centred message: "No workspaces yet. Create one to start analysing your data." with a single primary button "New workspace." No illustration, no onboarding carousel.

**New workspace flow:** a modal (not a separate page): name (required), optional description, then a dropzone for files *or* a field for an S3 prefix (later phase). On create, navigates to the workspace detail page with the upload dropzone active.

### 4.2 Workspace Detail (`/workspaces/[workspaceId]`)

**Purpose:** manage files and trigger analysis. Two vertical sections.

**Section A — File Grid**

A table with columns: Filename, Type (icon + label: CSV, XLSX, JSON…), Size, Description Status (a three-state badge: `pending` / `analyzing` / `ready`), Uploaded (relative time). Clicking a row opens the Description Drawer.

Above the table: an `UploadDropzone` — a dashed-border region that accepts drag-and-drop or click-to-browse. Accepted types: `.csv, .json, .xlsx, .xls, .md, .txt, .pdf, .sqlite, .zip, .parquet`. During upload, a progress bar per file appears inline. After upload, the row appears with status `pending`.

An "Ingest all" button triggers the Analyzer across every un-described file. As files are analyzed, their status badge live-updates from `pending` → `analyzing` → `ready` via polling or SSE.

**Section B — Description Drawer**

A slide-over panel (right, 480px) triggered by clicking a file row. Contents:

- File name, type badge, size, content hash (truncated, copyable).
- **Schema table:** columns → Column Name, Type, Sample Values (3). For XLSX, a tab selector for each sheet.
- **Analyzer Script:** a read-only code block showing the exact Python script the Analyzer wrote to profile this file. This is a trust signal — the user sees what ran.
- **Raw Description Output:** collapsible section with the raw `d_i` stdout, truncated with "Show full" toggle.

### 4.3 New Run (`/runs/new`)

**Purpose:** compose a query and start a run.

**Layout:** a focused, centred single-column form (max 640px).

- **Workspace selector** — dropdown of the user's workspaces (only those with status `ready` or `partial`).
- **Query input** — a tall textarea (min 3 lines, auto-grows to 8) with placeholder: `Ask a question about your data…`. Below it, 3–4 example queries as clickable chips pulled from `fixtures/manifest.yaml` — clicking one fills the textarea.
- **Mode selector** — two cards side by side: "Precise answer" (icon: target) and "Deep research" (icon: microscope). Precise is default. Deep research shows a tooltip: "Decomposes your question into sub-questions, solves each, and produces a cited report. Takes longer."
- **Budget overrides** (collapsed by default, expandable via "Advanced"): max rounds (slider, 1–10, default 10), max cost (input, default $2.50).
- **Run button** — `"Start analysis"`. On click → POST `/v1/runs`, receive `run_id`, navigate to `/runs/[runId]`.

No "are you sure" modal. The run starts. Analysts do not want friction; they want answers.

### 4.4 Run View (`/runs/[runId]`) — See §5 (its own section; it's the product)

### 4.5 Report View (`/runs/[runId]/report`)

**Purpose:** display the DS-STAR+ cited research report.

**Layout:** centred prose column (max 720px), rendered from the markdown the Report Writer produced. Two critical features:

**Citations:** every `[SQ-n]` in the text renders as a superscript link. On click/tap, a `CitationPopover` opens showing:
- The sub-question text.
- The code that answered it (collapsible code block).
- The execution output (truncated, expandable).
- Status badge: resolved / unresolved.

The popover is a floating panel (Radix Popover), anchored to the citation, dismissable on outside click or Escape.

**Report actions bar** (sticky top): "Copy as Markdown", "Export PDF" (later), "View provenance".

### 4.6 Provenance View (`/runs/[runId]/provenance`)

**Purpose:** the audit trail — everything needed to reproduce the answer.

**Layout:** a vertical card stack, each card one section:

| Card | Contents |
| --- | --- |
| Query | The original natural-language question, verbatim |
| Data snapshot | File list: name, type, `content_sha256` (copyable), size |
| Final script | Full Python code in a code block with copy button |
| Answer | The final output, formatted |
| Trace | Rounds summary: for each round, plan step + verdict (sufficient/insufficient) + router action. Collapsed by default, expandable per-round. |
| Models | For each agent invocation: agent name, model used, prompt version, tokens in/out, cost |
| Metadata | Run ID, started/finished timestamps, total cost, total tokens, trace ID (link to Langfuse if configured) |

### 4.7 Saved Analyses (`/saved-analyses`)

**Purpose:** pinned runs that can be re-executed on updated data.

**Layout:** table: Name, Workspace, Last Run, Schedule (manual / daily / weekly), Status. Clicking → detail view showing last run's result + a "Re-run now" button.

### 4.8 Settings (`/settings`)

**Purpose:** account-level config.

Tabs: Profile (name, email, avatar), API Keys (display masked, rotate), Usage (current billing period: runs, tokens, cost — bar chart by day). Keep it minimal; this is not where the product lives.

---

## 5. The Run View — The Core Experience

This is the product. If this screen is wrong, nothing else matters.

### 5.1 Three-pane layout

```
┌──────────────────────────────────────────────────────────────────┐
│  Breadcrumb: Workspaces / Payments Q3 / Runs / run-a1b2         │
│  Status bar: ● Round 4 of 10 · 12.3s · $0.34 · Verifying…      │
├────────────┬─────────────────────────────┬───────────────────────┤
│            │                             │                       │
│  Plan      │  Code                       │  Output               │
│  Timeline  │  Pane                       │  Pane                 │
│            │                             │                       │
│  (280px)   │  (flex: 1)                  │  (flex: 1)            │
│            │                             │                       │
│  scrolls   │  scrolls                    │  scrolls              │
│  indep.    │  indep.                     │  indep.               │
│            │                             │                       │
├────────────┴─────────────────────────────┴───────────────────────┤
│  Footer: Verifier verdict (when available)                      │
└──────────────────────────────────────────────────────────────────┘
```

Panes are **resizable** via drag handles (a thin divider line with a grip indicator on hover). Minimum width: 200px per pane. The layout state persists in `localStorage`. On mobile (< 768px), the panes stack vertically with tab switching (Plan / Code / Output).

### 5.2 Status bar

A horizontal strip above the panes. Contents, left to right:

- **Phase indicator** — the current node name as a label: `Analyzing`, `Planning`, `Coding`, `Executing`, `Verifying`, `Routing`, `Debugging`, `Finalizing`, `Complete`, `Failed`. Colour-coded: neutral for in-progress, `--vera-verified` for complete, `--vera-insufficient` for failed.
- **Round counter** — `Round 4 of 10`
- **Elapsed time** — `12.3s`, ticking live
- **Cost** — `$0.34`, incremented on each LLM call event
- **Cancel button** — a secondary button, `"Cancel run"`, with confirmation (inline "Are you sure? Yes / No" replacing the button, not a modal)

### 5.3 Plan Timeline (left pane) — the signature component

A vertical stepper where each step is a node. Three visual states:

**Active step:**
- Left border: 2px solid `--vera-accent`
- Background: `--vera-accent-muted`
- A subtle pulse animation on the step number indicator (CSS `@keyframes pulse` on opacity, 2s, respects `prefers-reduced-motion`)
- Step text in `--vera-ink` weight 500

**Completed step:**
- Left border: 2px solid `--vera-verified`
- Step number in a small circle with `--vera-verified` background, white check icon
- Step text in `--vera-ink` weight 400
- Clickable — clicking a completed step scrolls the Code Pane and Output Pane to show that step's code and observation

**Backtracked (superseded) step:**
- The entire block is visually demoted: ~~struck-through text~~ in `--vera-muted`
- Collapsed into a single line by default: `Step 3 — [backtracked]`
- A small `--vera-backtrack` coloured badge: `Backtracked`
- On expand (click or arrow), shows:
  - The original step text
  - The router's rationale: *"Step 3 produced incorrect merchant filtering. Truncating plan to step 2 and replanning."*
  - A faint connector line to the new step that replaced it
- The entire backtracked block has a `--vera-backtrack-muted` background wash

**The backtrack moment** is the key UX event. When the Router fires `BACKTRACK(l)`:
1. Steps l through k fade to `--vera-muted`, then collapse into the backtracked state (CSS transition 300ms)
2. A thin horizontal divider appears with label `↩ Backtracked to step l-1` in `--vera-backtrack`
3. The new step appears below with the `Active` state
4. The user's eye is guided: old steps dim, the correction marker appears, the new step highlights. This is visible self-correction.

Below the last step, while the run is active, an `Analyzing…` / `Planning…` / `Coding…` skeleton placeholder with a shimmer animation shows what the system is currently doing.

**Interaction:** clicking any completed step is the primary navigation within the run view. It updates the Code Pane and Output Pane to reflect that step's state, while the Plan Timeline scroll position stays where the user clicked.

### 5.4 Code Pane (centre pane)

- **Editor:** Monaco Editor (read-only), with the Catppuccin Mocha theme matching `--vera-code-bg / --vera-code-fg`.
- **Header bar:** `Step 3 — Python` label, a toggle: `Full script` / `Diff from previous step`. Diff mode shows the incremental changes as a unified diff with green additions and red deletions — this demonstrates the incremental coding approach.
- **Copy button** and **Download .py button** in the header.
- **Line numbers** always visible. If the script refers to a specific data file (from the descriptions), that filename is a hoverable link that opens the Description Drawer.
- During the `Coding` phase, the code streams in line-by-line (via SSE `code.generated` events). The editor auto-scrolls to the bottom.
- After a backtrack, the code pane shows the **rolled-back** script (the one at step `l-1`), visually confirming to the user that flawed code was discarded, not patched.

### 5.5 Output Pane (right pane)

- **Execution output:** rendered as a terminal — dark background (`--vera-code-bg`), monospace text, with stdout in `--vera-code-fg` and stderr in `--vera-insufficient`.
- **During execution:** stdout streams in live via SSE `exec.stdout` events. Auto-scroll is on by default with a "stick to bottom" toggle (a small down-arrow button that appears when the user scrolls up).
- **After execution:** the full truncated observation. If the output contains a dataframe repr, render it as a formatted table (auto-detect `│` and `─` characters or pandas-style spacing). If the output contains a chart path, render the chart inline (PNG via the artifacts endpoint).
- **Header bar:** label changes per phase — `Output — Step 3` (after execution), `Executing…` (during), `Awaiting execution` (before).
- **Artifact pills:** if the execution produced downloadable artifacts (charts, exported files), they appear as small pills below the output: `📊 revenue_by_region.png` / `📄 cleaned_data.csv`, each clickable for download.

### 5.6 Verdict Footer

A bottom strip that appears after the Verifier runs. Two states:

**Sufficient:**
```
✓ Sufficient — "The plan correctly computes merchant-level chargeback rates 
by joining payments.csv with merchant_data.json and filters for Q3."
```
Green left border, `--vera-verified` icon, verdict text in `--vera-ink`. Appears with a gentle slide-up animation.

**Insufficient:**
```
✗ Insufficient — "The current script filters by year but does not constrain 
to March (days 60–90). Revenue calculation is missing the fee adjustment step."

Missing: fee deduction, date range constraint

Router: Add step → planning step 5
```
Red left border, `--vera-insufficient` icon. Below: the `missing_aspects` as tags, and the router's decision as a small inline badge (`Add step` in `--vera-accent` or `Backtrack to step 2` in `--vera-backtrack`). This footer is critical — it is where the user sees the *reasoning*, not just the outcome.

### 5.7 Run completion states

**Success:** the status bar turns `--vera-verified`. The Output Pane shows the final answer prominently at the top, followed by the execution output. A sticky bar at the bottom of the page: `"View provenance"` button + `"Ask another question"` button.

**Failed (budget exhausted):** the status bar turns `--vera-insufficient`. A banner: `"This run reached the maximum of 10 rounds without a sufficient answer. The best result so far is shown below."` The output still shows, marked `confidence: low`.

**Cancelled:** status bar shows `Cancelled`. Output shows whatever was available at cancellation.

### 5.8 Run view — Analysis phase (before the loop)

Before the core loop starts, the Analyzer profiles files. The Plan Timeline shows a distinct pre-loop section:

```
─── File Analysis ───
  ✓ payments.csv       2.1 KB  [ready]
  ● merchant_data.json 6.8 KB  [analyzing…]
    fees.json          1.2 KB  [pending]
─── Planning ───
  (step 1 will appear here)
```

Progress updates per file via SSE `analyze.progress` events. This section collapses automatically when the core loop begins.

---

## 6. Component Library — Domain Components

These are VERA-specific components beyond the base shadcn primitives.

### 6.1 `<PlanTimeline steps={PlanStep[]} activeIndex={number} />`

The signature component. Props:
- `steps` — array of plan steps with status, text, round, superseded flag
- `activeIndex` — currently executing step
- `backtracks` — array of `{ fromIndex, toIndex, rationale }`
- `onStepClick(index)` — navigation callback

Renders the vertical stepper described in §5.3. Must handle rapid state transitions gracefully (multiple SSE events in quick succession).

### 6.2 `<CodePane code={string} language={"python"} diffFrom={string | null} />`

Monaco wrapper with:
- Read-only mode
- Diff toggle (unified diff when `diffFrom` is provided)
- Line-by-line streaming support (accepts a `streaming` prop + `onChunk` handler that appends)
- Catppuccin Mocha theme
- Header with copy/download

### 6.3 `<ObservationPane output={string} artifacts={ArtifactRef[]} streaming={boolean} />`

Terminal-style output renderer with:
- ANSI colour support
- Auto-detect and render dataframe tables (from pandas/polars repr)
- Inline chart rendering from artifact refs
- Auto-scroll with stick-to-bottom toggle
- Stderr highlighting

### 6.4 `<VerdictBanner verdict={Verdict} routerDecision={RouterDecision | null} />`

The footer component from §5.6. Animate in with `framer-motion` `AnimatePresence` (slide up + fade, 200ms).

### 6.5 `<FileTypeBadge kind={FileKind} />`

Small inline badge with an icon and label. Icons: CSV → table icon, XLSX → grid icon, JSON → braces icon, PDF → file-text icon, MD → hash icon, TXT → align-left icon, SQLite → database icon, ZIP → archive icon. Background: `--vera-border-subtle`. Text: `--vera-muted`. Size: 12px label.

### 6.6 `<StatusBadge status={"pending"|"analyzing"|"ready"|"sufficient"|"insufficient"|"backtracked"} />`

Small pill badge with colour-coded background and text:
- pending: grey
- analyzing: accent with shimmer
- ready: verified green
- sufficient: verified green
- insufficient: red
- backtracked: amber

### 6.7 `<CostMeter spent={number} limit={number} />`

A small horizontal bar in the status bar. Fill colour transitions from `--vera-accent` to `--vera-backtrack` at 70% to `--vera-insufficient` at 90%. Shows `$0.34 / $2.50` as text.

### 6.8 `<CitationPopover index={number} subQuestion={SubQuestion} />`

Floating panel triggered by `[SQ-n]` clicks in the report. Contains: sub-question text, collapsible code block, truncated observation, status badge. Dismissable on Escape or outside click. Built on Radix Popover.

### 6.9 `<DescriptionDrawer file={FileRef} description={FileDescription} />`

Right slide-over (480px). Schema table, analyzer script, raw output. Built on Radix Sheet.

### 6.10 `<UploadDropzone workspaceId={string} onUploaded={fn} />`

Drag-and-drop zone using `react-dropzone`. Accepted types validated client-side; shows per-file progress bars; calls presigned-upload endpoint. On completion, fires `onUploaded` with new file refs.

---

## 7. Real-Time Data Architecture

### 7.1 SSE event stream

The run view subscribes to `GET /v1/runs/{runId}/events` (SSE). The event types, as defined in `core.models.events`:

```typescript
type RunEvent =
  | { type: "run.started";     runId: string; mode: "precise" | "research" }
  | { type: "analyze.progress"; done: number; total: number; file: string }
  | { type: "plan.step";        index: number; text: string; round: number }
  | { type: "code.generated";   sha: string; diff: string; fullSource: string }
  | { type: "exec.stdout";      chunk: string }
  | { type: "exec.finished";    exitCode: number; durationMs: number; artifacts: ArtifactRef[] }
  | { type: "verify.verdict";   sufficient: boolean; reason: string; missingAspects: string[] }
  | { type: "route.decision";   action: "add_step" | "backtrack"; backtrackIndex?: number; rationale: string }
  | { type: "plan.truncated";   toIndex: number }
  | { type: "debug.attempt";    attempt: number; maxAttempts: number }
  | { type: "budget.warning";   spentUsd: number; limitUsd: number }
  | { type: "run.finished";     status: "succeeded" | "failed" | "cancelled"; answer?: string }
  | { type: "run.failed";       error: { code: string; message: string } };
```

Every event carries a `seq` (monotonic integer) and `runId`. The stream sends `id: <seq>` and `retry: 3000`.

### 7.2 `useRunStream` hook

```typescript
function useRunStream(runId: string): {
  status: "connecting" | "streaming" | "complete" | "error";
  events: RunEvent[];         // full ordered log
  latestByType: Map<RunEvent["type"], RunEvent>;
}
```

Implementation:
1. Opens `EventSource` to `/v1/runs/{runId}/events`.
2. On reconnect, sends `Last-Event-ID: <lastSeq>` — the server replays from `run_events WHERE seq > $lastSeq`.
3. **Seq-gap detection:** if incoming `seq` is not `lastSeq + 1`, trigger a full re-fetch of the run state via REST (`GET /v1/runs/{runId}`) and reconcile — this handles the case where a reconnect missed events that were already garbage-collected.
4. On `run.finished` or `run.failed`, close the stream.
5. Dispatches each event to the Zustand store (§8).

### 7.3 Optimistic state

The SSE stream is the source of truth for a live run. REST polling is the fallback for stale tabs. On initial page load for a run that's already in progress, the page fetches the full `RunState` via REST, hydrates the store, then opens the SSE stream from the last known `seq`. No double-rendering; no flash of empty state.

---

## 8. State Management

### 8.1 Zustand stores

Two stores; no more.

**`useRunStore`** — scoped to a single run view instance:

```typescript
interface RunStore {
  // Derived from SSE events
  phase: RunPhase;
  round: number;
  elapsed: number;
  cost: number;
  planSteps: PlanStep[];
  backtracks: BacktrackEvent[];
  currentCode: string;
  codeDiffFromPrevious: string | null;
  observations: Map<number, Observation>;  // keyed by step index
  verdicts: Verdict[];
  answer: string | null;
  artifacts: ArtifactRef[];

  // UI state
  selectedStepIndex: number | null;
  codeDiffMode: boolean;
  outputAutoScroll: boolean;

  // Actions
  applyEvent(event: RunEvent): void;
  selectStep(index: number): void;
  toggleDiffMode(): void;
  hydrate(runState: RunStateDTO): void;
}
```

**`useWorkspaceStore`** — file list, descriptions, ingest status. Simpler; TanStack Query handles most of this via server state.

### 8.2 What TanStack Query owns vs Zustand

- **TanStack Query:** workspace lists, file lists, run history list, description detail, provenance data — all REST-fetched, cacheable, stale-while-revalidate.
- **Zustand:** the live run view's rapidly-updating state that arrives via SSE. This data changes multiple times per second during execution; React Query is not designed for that update frequency.

Clear boundary: TanStack Query for "load once, maybe refresh" data; Zustand for "60 events per second" data.

---

## 9. API Integration & Type Safety

### 9.1 Generated client

`tools/codegen/openapi_to_ts.sh` generates TypeScript types and a fetch-based client from `docs/api/openapi.yaml` into `apps/web/lib/api/generated/`. The generated code:

- Exports one function per endpoint: `createRun(body: CreateRunRequest): Promise<RunResponse>`
- All request/response types are exported
- No runtime dependencies beyond `fetch`

### 9.2 Zod validation at the boundary

Every API response is validated with Zod before entering the application. The Zod schemas mirror the generated types and catch backend contract drift at runtime:

```typescript
// apps/web/lib/api/client.ts
export async function getRunState(runId: string): Promise<RunState> {
  const res = await fetch(`/api/v1/runs/${runId}`);
  if (!res.ok) throw new ApiError(await res.json());
  const data = await res.json();
  return RunStateSchema.parse(data);  // Zod parse — throws on shape mismatch
}
```

### 9.3 Error contract

All API errors arrive as RFC 9457 `application/problem+json`:

```typescript
interface ProblemDetail {
  type: string;        // stable URI, e.g. "urn:vera:error:run-budget-exhausted"
  title: string;       // human-readable
  status: number;
  detail?: string;
  traceId: string;     // for support escalation
}
```

The error handler renders these via a `<ProblemToast>` component: title, detail, and a "Copy trace ID" button. Never display raw stack traces to the user.

---

## 10. Interaction Design & Micro-Interactions

### 10.1 The backtrack animation (the moment that matters)

When a `route.decision` event with `action: "backtrack"` arrives:

1. **T+0ms:** the superseded steps (from `backtrackIndex` to current) begin a 250ms opacity fade from 1.0 → 0.4.
2. **T+250ms:** the steps collapse vertically (height transition 200ms ease-out) into the backtracked state — one-line summary with `--vera-backtrack` badge.
3. **T+300ms:** the horizontal divider `↩ Backtracked to step N` slides in from the left (150ms).
4. **T+500ms:** the Code Pane smoothly transitions to the rolled-back script (crossfade 200ms).
5. **T+600ms:** the new planning step begins appearing (from the next `plan.step` event).

All timings respect `prefers-reduced-motion: reduce` — skip to final state instantly.

### 10.2 Verdict slide-in

The Verdict Footer (`<VerdictBanner>`) uses `framer-motion`'s `AnimatePresence` for enter/exit. Entry: slide up 24px + fade in, 200ms spring. Exit: fade out 150ms. Insufficient verdicts shake subtly (2px horizontal, 100ms, once) to draw attention — but only on the first insufficient verdict per run (not every round).

### 10.3 Step click → pane sync

Clicking a completed step in the Plan Timeline:
1. The step receives the active-selected style (accent background wash).
2. The Code Pane smoothly scrolls/transitions to that step's code snapshot.
3. The Output Pane shows that step's observation.
4. The Verdict Footer updates to that round's verdict (or hides if the step hasn't been verified).

This interaction is instant — no loading state, because all step data is already in the Zustand store (arrived via SSE or initial hydration).

### 10.4 Keyboard navigation

| Key | Action |
| --- | --- |
| `↑` / `↓` | Navigate between plan steps (when Plan Timeline is focused) |
| `Enter` | Select the focused step (syncs Code + Output panes) |
| `Escape` | Deselect step (return to latest/live) |
| `Cmd/Ctrl + C` (with code pane focused) | Copy visible code |
| `Cmd/Ctrl + Shift + D` | Toggle diff mode in Code Pane |

### 10.5 What NOT to animate

- Do NOT animate individual lines of code appearing. Streaming code arrives fast; a per-line animation would create jank. The Monaco editor handles its own rendering; just append.
- Do NOT add a typing animation to stdout. It streams. Display it immediately.
- Do NOT animate the cost counter incrementing. Just update the number.
- Do NOT add a progress ring or spinner to the status bar. The Plan Timeline itself *is* the progress indicator — adding a spinner alongside it is redundant and noisy.

---

## 11. Accessibility Requirements

WCAG 2.2 AA minimum. These are non-negotiable, not aspirational.

### 11.1 Keyboard

- Every interactive element is focusable and operable via keyboard.
- Plan Timeline steps are an `aria-listbox` with `aria-selected` on the active step. Arrow keys navigate.
- The three panes are landmarks: `role="region"` with `aria-label="Plan timeline"`, `aria-label="Code editor"`, `aria-label="Execution output"`.
- Resizable pane dividers are `role="separator"` with `aria-orientation="vertical"` and operable via arrow keys (8px per press).
- Skip links to each pane at the top of the run view, visible on focus.

### 11.2 Screen readers

- Verdict announcements use `aria-live="polite"`: when a verdict arrives, the assistive text reads "Step 3 verified: sufficient" or "Step 3 verified: insufficient, reason: …".
- Backtrack events announce: "Steps 3 through 5 have been backtracked. Replanning from step 2."
- The status bar phase indicator has `aria-live="polite"` with debounce (announce on phase change, not every event).

### 11.3 Colour

- No information conveyed by colour alone. Sufficient/insufficient verdicts have icon (checkmark/X) + text label in addition to green/red colour.
- Backtracked steps have strikethrough text + "Backtracked" label, not just amber colour.
- All text passes 4.5:1 contrast against its background. `--vera-muted` on `--vera-paper` is 4.7:1 (verified).

### 11.4 Motion

- All transitions respect `prefers-reduced-motion: reduce`. Reduced-motion users get instant state changes with no animation.
- The pulse animation on the active step is `opacity` only (no layout shift), and is suppressed under `prefers-reduced-motion`.

---

## 12. Responsive Behaviour

### 12.1 Breakpoints

| Name | Width | Layout change |
| --- | --- | --- |
| `desktop` | ≥ 1280px | Three-pane side-by-side; sidebar expanded |
| `laptop` | 1024–1279px | Three-pane; sidebar collapsed to icon-only |
| `tablet` | 768–1023px | Two-pane (Plan + tabbed Code/Output); sidebar collapsed |
| `mobile` | < 768px | Single pane with tab bar (Plan / Code / Output); no sidebar, bottom nav |

### 12.2 Mobile run view

On mobile, the three panes become three tabs at the top of the viewport. The currently active phase determines which tab auto-selects: Planning → Plan tab, Coding → Code tab, Executing → Output tab. The user can manually switch at any time and auto-switch is suppressed after manual interaction.

The Plan Timeline on mobile drops the left-border treatment and uses a compact card layout instead — each step is a tappable card showing step number, first line of text, and status icon.

### 12.3 What does NOT adapt

- The Code Pane always uses Monaco on all viewports ≥ 768px. On mobile, it falls back to a syntax-highlighted `<pre>` block (Monaco's mobile performance is poor).
- The Verdict Footer is always full-width and anchored to the bottom of the visible pane.
- Tables (file list, provenance trace) become horizontally scrollable on narrow viewports, never reorganised into cards (cards obscure the columnar relationships that make tabular data useful).

---

## 13. Performance Budget

| Metric | Target | Enforcement |
| --- | --- | --- |
| LCP | < 1.5s | Lighthouse CI, fail on regression |
| FID / INP | < 100ms | Lighthouse CI |
| CLS | < 0.05 | Lighthouse CI |
| JS bundle (initial route) | < 150 KB gzipped | `next/bundle-analyzer`, budgeted per route |
| SSE event → UI update | < 50ms | Manual profiling; if exceeded, the run view feels laggy |
| Time to interactive on run view | < 2s (hydration + SSE open) | Playwright timing assertion |

### 13.1 Critical path optimisation

- **Monaco lazy load:** the editor is heavy (~2 MB). Load it only on the run view route via `next/dynamic` with `ssr: false` and a skeleton placeholder during load.
- **Route-based code splitting:** each top-level route is its own chunk. Workspace list never loads Monaco or the SSE hook.
- **SSE event batching:** `useRunStream` batches events into 16ms frames using `requestAnimationFrame` before dispatching to the store, preventing React re-renders per individual event during rapid stdout streaming.
- **Virtual scrolling for output:** if the observation exceeds 500 lines, switch to a virtualised list (`@tanstack/virtual`) to prevent DOM node explosion.
- **Image/chart lazy loading:** artifact PNGs load only when the Output Pane is scrolled to their position, using `loading="lazy"`.

---

## 14. Error, Empty & Loading States

### 14.1 Principle

Errors explain what happened and what to do. Empty states invite action. Loading states show structure, not spinners. Never apologise, never be vague, never say "something went wrong."

### 14.2 Error states

| Context | Message | Action |
| --- | --- | --- |
| SSE connection lost | "Connection interrupted. Reconnecting…" (inline banner, auto-retry) | Auto-retry with back-off; show "Reconnecting in 5s…" countdown |
| Run creation failed | "Could not start the analysis: {detail}" | "Try again" button |
| File upload failed | "{filename} failed: {detail}" (per-file inline) | "Retry" link per file |
| Budget exhausted | "This run reached its cost limit ($2.50). Showing the best result so far." | "View partial result" + "Increase budget and retry" |
| Provider unavailable | "The AI provider is temporarily unavailable. Retrying automatically." | Auto-retry; after 3 failures: "Still unavailable. Try again in a few minutes." |

### 14.3 Empty states

| Context | Message | CTA |
| --- | --- | --- |
| No workspaces | "No workspaces yet." | "New workspace" button |
| Workspace with no files | "Drop files here to start." | Dropzone is the CTA |
| No runs | "No analyses yet. Upload data and ask a question." | "New analysis" button |
| Empty observation (code produced no output) | "The script completed but produced no output." | (none) |

### 14.4 Loading states

- **Page load:** RSC streams the shell immediately; loading content areas show `Skeleton` components (shadcn Skeleton, matching the exact layout of the loaded state).
- **Run view initial load:** the three-pane layout renders immediately with skeletons in each pane. The Plan Timeline shows a single shimmer block. Code Pane shows a code-block-shaped skeleton. Output Pane shows three lines of shimmer text.
- **Never:** a full-page spinner. Never a centred "Loading…" text. Never a blank white page.

---

## 15. Testing Strategy

### 15.1 Unit tests (Vitest + Testing Library)

- Every domain component has a test file: `PlanTimeline.test.tsx`, `VerdictBanner.test.tsx`, etc.
- Tests render the component with fixture data and assert on structure, text content, and ARIA attributes.
- SSE behaviour is tested by mocking `EventSource` and dispatching events programmatically.
- Store logic tested independently: create a store instance, call `applyEvent` with a sequence, assert on the resulting state.

### 15.2 E2E tests (Playwright)

Critical path test, one flow:

```
1. Navigate to workspace list
2. Create workspace
3. Upload 2 fixture files (CSV + JSON)
4. Trigger ingest → wait for descriptions to appear
5. Navigate to New Run → compose query → start
6. Assert: Plan Timeline shows steps appearing
7. Assert: Code Pane shows code
8. Assert: Output Pane shows execution result
9. If a backtrack event occurs: assert superseded steps are visually demoted
10. Assert: run completes → answer is displayed
11. Navigate to provenance → verify script and data hashes are present
```

Run against the real API with `FakeLLM` + `FakeSandbox` so the flow is deterministic and free.

### 15.3 Visual regression (Playwright screenshots)

Capture screenshots of:
- Empty workspace
- Workspace with files at various description statuses
- Run view mid-execution (mocked at step 3)
- Run view after a backtrack (mocked with superseded steps)
- Verdict: sufficient vs insufficient
- Report with citation popovers
- Dark mode variants of all above

Compare against committed baselines. Flag regressions in CI.

---

## 16. File Structure & Code Standards

### 16.1 Structure

```
apps/web/
├── app/                      # Next.js App Router pages
│   ├── layout.tsx            # root layout: fonts, providers, sidebar
│   ├── page.tsx              # redirect to /workspaces
│   ├── workspaces/           # pages for workspace CRUD
│   └── runs/                 # pages for run view, report, provenance
├── components/
│   ├── ui/                   # shadcn components — DO NOT MODIFY inline
│   ├── run/                  # run-view-specific components
│   ├── workspace/            # workspace-specific components
│   ├── report/               # report-view components
│   └── shared/               # truly shared (ErrorBanner, Skeleton, Breadcrumbs)
├── lib/
│   ├── api/
│   │   ├── generated/        # ← codegen output. DO NOT EDIT.
│   │   └── client.ts         # wrapper with Zod validation + error handling
│   ├── hooks/                # custom hooks
│   ├── stores/               # Zustand stores
│   ├── schemas/              # Zod schemas mirroring generated types
│   └── utils/                # formatDuration, formatCost, truncate — pure functions
├── styles/
│   ├── globals.css           # CSS variables, font imports, Tailwind base
│   └── monaco-theme.ts       # Catppuccin Mocha definition for Monaco
├── e2e/                      # Playwright tests
├── public/
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

### 16.2 Code standards

- `strict: true`, `noUncheckedIndexedAccess: true` in tsconfig. No `any`. Use `unknown` + narrowing.
- ESLint + Prettier, enforced in pre-commit.
- Every component: named export, not default (except page.tsx per Next.js convention).
- Every component file contains one component and its types. No multi-component files.
- Props interfaces are named `{Component}Props` and exported.
- No inline styles. Tailwind utilities only, composed with `cn()` (clsx + tailwind-merge).
- `"use client"` only on components that actually use hooks, event handlers, or browser APIs. RSC by default.
- No `useEffect` for data fetching — use TanStack Query or RSC `fetch`.
- No `useEffect` for derived state — use `useMemo` or compute in the render.
- `useEffect` is permitted for: SSE subscription setup, keyboard shortcuts, Monaco lifecycle. Comment the reason.

### 16.3 Naming

| Thing | Convention | Example |
| --- | --- | --- |
| Component file | PascalCase | `PlanTimeline.tsx` |
| Hook file | camelCase with `use` prefix | `useRunStream.ts` |
| Store file | camelCase with `Store` suffix | `runStore.ts` |
| Utility file | camelCase | `formatDuration.ts` |
| Test file | mirrors source with `.test` | `PlanTimeline.test.tsx` |
| CSS variable | `--vera-*` kebab-case | `--vera-accent-muted` |
| Tailwind custom class | never; use utilities directly | — |

---

## 17. Build Order

Ship vertical slices. Each row is demoable and unblocks the next.

| # | Slice | What ships | What it proves |
| --- | --- | --- | --- |
| 1 | **Shell + design tokens** | Root layout, sidebar, routing, CSS variables, typography, dark mode toggle, empty states | The app loads, navigates, and looks intentional |
| 2 | **Workspace CRUD** | Workspace list, create modal, file grid (static), upload dropzone, file type badges | Files land in the system |
| 3 | **Description drawer** | Description drawer with schema table, analyzer script block, raw output | The user can inspect what the Analyzer found |
| 4 | **Run view skeleton** | Three-pane layout with resizable dividers, status bar, static Plan Timeline with fixture data | The signature layout exists |
| 5 | **SSE integration** | `useRunStream` hook, Zustand store, Plan Timeline receiving live events, step click → pane sync | The run view is live |
| 6 | **Code pane** | Monaco integration, diff toggle, streaming code, backtrack-aware rollback display | The code is readable and the diff shows incremental building |
| 7 | **Output pane** | Terminal renderer, streaming stdout, dataframe table detection, artifact pills | Execution results are visible |
| 8 | **Verdict + router** | Verdict footer (sufficient/insufficient), backtrack animation, router badge, missing aspects | ★ The trust moment — visible self-correction |
| 9 | **Report view** | Markdown renderer, citation popovers, sub-question detail | DS-STAR+ research output is usable |
| 10 | **Provenance** | Provenance card stack, copy/export, trace detail | Auditability is real |
| 11 | **Polish** | Mobile responsive, keyboard navigation, accessibility audit, visual regression baselines, dark mode completion | Production-grade |

**Slice 8 is the product.** If the backtrack animation — steps dimming, correction marker appearing, new plan sliding in — does not feel trustworthy and transparent, invest time here before moving to slices 9–11. The user's willingness to rely on VERA's answers depends entirely on this moment.

---

## 18. Anti-Patterns to Reject

| Pattern | Why it's rejected |
| --- | --- |
| Chat bubble UI | VERA is not a chatbot. It's a structured workbench. Chat bubbles hide the process. |
| "Thinking…" / "AI is working…" spinners | The Plan Timeline *is* the progress. Adding a spinner beside it is redundant and reduces the perceived transparency. |
| Full-page loading screens | The shell and layout render immediately via RSC. Content areas use skeletons. |
| Toast notifications for run events | Events stream into the run view in real time. Toasts would duplicate what the user is already watching, and they stack up and obscure the view. |
| Animations on every state change | Animate the backtrack. Animate the verdict entry. Animate nothing else in the run view — rapid stdout and code streaming must feel instant, not theatrical. |
| Anthropomorphic language | "I'm thinking about your data…" — no. The system is executing step 3. Say that. |
| Cards for tabular data | File lists, provenance traces, and run history are tables. Cards hide column alignment and make scanning harder. |
| Separate pages for every detail | Descriptions are a drawer, not a page. Verdicts are a footer, not a page. Sub-question details are a popover, not a page. Navigation kills flow during a live run. |
| `any` types | Use `unknown` + narrowing. Type safety is the only thing standing between the SSE stream and a runtime crash. |
| Storing SSE-derived state in TanStack Query | Query is for request-response data. SSE events arrive 60/s during execution. Store them in Zustand and dispatch via `requestAnimationFrame` batching. |
| Optimistic UI for run actions | Do not show a "Step 4" before the server confirms it. The SSE stream is the source of truth; rendering ahead of it creates flicker when the server disagrees. |

---

### Closing note

The run view is the product. The backtrack moment is the thesis. Everything else — workspaces, settings, provenance — exists to support those two.

Build slice 4 (static run view layout), then slice 5 (SSE integration), then slice 8 (backtrack animation). Wire them with fixture data and `FakeLLM` events before touching real prompts. If the animation of a backtrack — steps dimming, the correction marker sliding in, the Code Pane rolling back to the good script — does not make you think "oh, it caught that," then iterate on the animation, not on more features.

The interface is not a wrapper around an API. It is the argument that VERA's answers are trustworthy. Make the machine's self-correction *visible*, and trust follows.