# fix-data.md — data / lib / BFF layer fixes

Scope owned: `apps/web/lib/**`, `apps/web/app/api/**`, `apps/web/next.config.ts`.
`pnpm` is not on PATH in this environment; verified with `npx tsc --noEmit` inside
`apps/web` — **clean** except one pre-existing unrelated error
(`components/shared/ThemeToggle.tsx` imports `next-themes`, which is not installed —
that is review item A1.7, outside this scope).

---

## A4.1 — run-mode union standardised on `"precise" | "research"`

- `lib/config/modes.ts` — already canonical (`export type RunMode = "precise" | "research"`).
  Left as the single source of truth. **No change needed** — it already exports the type.
- `lib/data/session.ts` — `ProfileUpdate.defaultRunMode` was `"precise" | "deep"`,
  now `RunMode` (imported from `@/lib/config/modes`).
- `lib/schemas/runSchemas.ts` — already `z.enum(["precise", "research"])`. Untouched.
- No other `lib/**` usage of `"deep"` exists.

**Still emits `"deep"` — pages agent must fix** (`app/(app)/settings/profile/page.tsx`):
lines ~52–53 `useState<"precise" | "deep">("deep")`, line ~73 `defaultRunMode: runMode`,
line ~227 `(["precise", "deep"] as const)`. Switch the state type to
`RunMode` from `@/lib/config/modes`, use `"research"` instead of `"deep"`, and iterate
`MODES` (or `["precise","research"]`) for the radio options. `updateProfile` now
rejects `"deep"` at the type level.

## A3.10 — dead code deleted

- `lib/api/client.ts` — **deleted** (`git rm`). Grep confirmed zero imports in `apps/web`
  (only mentions were in `docs/` and `.review/`). Its `ApiError` class, `RunSummary` /
  `CreateRunRequest` types, and `getRun` were all unused; the Zod schema it referenced
  (`RunStateDTOSchema`) lives in `lib/schemas/runSchemas.ts` and is untouched.
  `lib/api/generated/.gitkeep` left in place.
- `lib/hooks/useRunStream.ts` — removed the unused `export const eventLog`.

## A3.1 + A3.2 — `useRunStream` rewritten (`lib/hooks/useRunStream.ts`)

- Now returns **real React state**: `const [status] = useState<StreamStatus>()` and
  `const [events] = useState<RunEvent[]>([])`. RAF batching preserved (events flushed
  into state in one `setEvents` per frame). Consumers re-render.
- `StreamStatus` union widened to
  `"connecting" | "streaming" | "reconnecting" | "complete" | "error"`.
  `onerror` now inspects `es.readyState`: `CLOSED` → `"error"` (dead),
  otherwise → `"reconnecting"` (EventSource is retrying). Terminal event → `"complete"`.
- Seq-gap re-hydration goes through `RunStateDTOSchema.safeParse` (mirrors the old
  `client.ts:getRun`), sets `lastSeqRef` from `parsed.data.lastSeq`, then calls
  `useRunStore.getState().hydrate(parsed.data)`. Parse failure is swallowed (no
  `as RunStateDTO` cast anywhere).
- Spurious first-event-after-reconnect gap fixed: a `resumingRef` flag is set on drop
  and the first event once reconnected is adopted (`lastSeq = seq`) instead of being
  compared. The gap check is now `seq > lastSeq + 1` (strictly missed events) and only
  runs when not resuming.
- `runStore` `applyEvent` / `hydrate` signatures unchanged — no store edits.

## A3.4 — `useResource` cancellation (`lib/data/useResource.ts`)

- New exported interface `FetcherContext { signal: AbortSignal }`.
- Fetcher signature is now `(ctx?: FetcherContext) => Promise<T>` (back-compatible —
  a zero-arg fetcher still assigns).
- Each effect run creates an `AbortController`, passes `{ signal }` to the fetcher, and
  calls `controller.abort()` in cleanup (alongside the existing `cancelled` flag).
- Aborted rejections are ignored (`if (cancelled || controller.signal.aborted) return`).
- Dep array fixed: `keepPreviousData` removed from `[...deps, nonce]` (it is a static
  option; it stays readable inside the effect closure).
- `lib/data/http.ts` `getJson` / `sendJson` gained an optional 3rd arg
  `options?: { signal?: AbortSignal }` threaded into `fetch`. `AbortError` is re-thrown
  (not wrapped as a transport `RequestError`).
- `lib/data/session.ts:getCurrentUser` now accepts `ctx?: { signal }` and forwards it,
  so `AuthProvider`'s `useResource(getCurrentUser)` cancels cleanly.

**Other `lib/data/*` fetchers were left zero-arg** (still valid). If a page wants
cancellation for a specific call, that module's function can take `ctx?` and pass
`{ signal: ctx?.signal }` as the 3rd arg to `getJson` — same pattern as `getCurrentUser`.

## A3.5 — runs list sorting (`lib/data/runs.ts` + `lib/data/types.ts`)

- `RunListFilters` gained `sort?: RunSortField` and `order?: SortOrder`.
- New exported types in `lib/data/types.ts`:
  `RunSortField = "createdAt" | "cost"`, `SortOrder = "asc" | "desc"`.
  (Matches the vocabulary `app/(app)/runs/page.tsx` already puts in the URL — its local
  `type SortField = "cost" | "createdAt"`. Pages agent may delete that local type and
  import `RunSortField` instead.)
- `listRuns` now forwards `sort` and `order` into the query string, so ordering is
  server-side and stable across "Load more".

## A3.8 — `AuthProvider.refresh()` double-fetch (`lib/auth/AuthProvider.tsx`)

- Removed the `sessionKey` state entirely. `useResource(getCurrentUser)` now takes no
  extra dep. `refresh()` calls **only** `retry()` (the nonce bump). Single refetch.

## A3.9 — helpers consolidated into `lib/utils/`

New files, matching `formatCost.ts` / `formatDuration.ts` style:

- `lib/utils/formatBytes.ts` → `export function formatBytes(bytes: number): string`
  (`"512 B"` / `"2.0 KB"` / `"5.0 MB"` / `"1.2 GB"`, guards non-finite/negative).
- `lib/utils/formatTokens.ts` → `export function formatTokens(n: number): string`
  (`"840"` / `"12.3K"` / `"2.5M"`).

`parseTabularOutput` — already the single impl in `lib/data/runDetail.ts` and already
exported. No move needed; left there per task instruction.

**Component copies the components agent must replace with the shared imports:**

| Helper | Inline copies to delete |
|---|---|
| `formatBytes` | `components/workspace/UploadDropzone.tsx:16`, `components/workspace/FileGrid.tsx:11`, `components/workspace/DescriptionDrawer.tsx:17`, `components/run/ObservationPane.tsx:8` |
| `formatBytes` (partial, inline expression) | `app/(app)/runs/[runId]/provenance/page.tsx:134` — `(f.sizeBytes / 1024).toFixed(1) KB` |
| `formatTokens` | `components/settings/UsageChart.tsx:24` (`fmtTokens`), `components/settings/CostBreakdown.tsx:1` (`fmtTokens`), `app/(app)/settings/usage/page.tsx:13` (`fmtTokens` — note: this one lacks the `M` rule, switching to the shared impl is a behaviour improvement) |
| `parseTabularOutput` | `components/run/ObservationPane.tsx` `DataframeRenderer` splits on `/\s{2,}/` itself — should call `parseTabularOutput` from `@/lib/data/runDetail` |

## A3.11 — safe clipboard helper

- `lib/utils/clipboard.ts` → `export async function copyText(text: string): Promise<boolean>`.
  Tries `navigator.clipboard.writeText`, falls back to a hidden `<textarea>` +
  `document.execCommand("copy")`, never rejects, returns whether it succeeded.

**Callers the components/pages agents should switch to `copyText`:**
`components/run/CodePane.tsx`, `app/(app)/runs/[runId]/provenance/page.tsx` (×3),
`app/(app)/runs/[runId]/report/page.tsx`, `components/workspace/DescriptionDrawer.tsx` (×2),
`components/settings/ProviderKeyCard.tsx`.

## A4.5 — noted only (not in scope)

`app/(app)/runs/[runId]/provenance/page.tsx:~545` `CopyableText` hard-codes
`text.slice(7, 15)` (assumes `"sha256:"` prefix). A bare hash renders mangled. Pages
agent: strip a known prefix explicitly or guard on `text.includes(":")`.

## A2.2 / A2.3 — one API surface + auth plumbing + real proxy

**Surface decision:** the BFF (`lib/data/*` → `/api/*` route handlers) is the single
request/response surface. The `/api/v1/:path*` rewrite in `next.config.ts` is **kept**,
now documented as existing **only** for the SSE run stream
(`lib/hooks/useRunStream.ts` → `/api/v1/runs/:id/events`), which also uses
`/api/v1/runs/:id` for its Zod re-hydration. Next route handlers are a poor fit for
long-lived streaming responses, so that one path stays a direct pass-through to FastAPI.

**Token holder — `lib/auth/token.ts` (new):**
```
getToken(): string | null
setToken(next: string | null): void
clearToken(): void
authHeader(): Record<string, string>   // { Authorization: `Bearer …` } or {}
```
Module-scoped variable only — no `localStorage` / cookie / persistence (keeps A5.1 GOOD).

**`lib/data/http.ts`:** every request now spreads `authHeader()` into its headers.
**`lib/data/workspaceFiles.ts`:** the XHR upload sets the same header via
`xhr.setRequestHeader`.

**`lib/auth/AuthProvider.tsx`:** exposes `setToken(token: string): void` and
`clearToken(): void` on the context (both write the in-memory holder then `retry()` the
session fetch). No login page, no refresh flow — just the plumbing, as scoped.
`AuthContextValue` gained those two fields.

**`app/api/_lib/respond.ts`:** `problem(status, title, detail?, traceId?)` — new 4th arg;
prefers a supplied upstream trace id, only synthesises `trace-<rand>` as a fallback.

**`app/api/_lib/proxy.ts` (new):**
- `proxy(request, { path, method?, jsonBody? }): Promise<Response | null>` — returns
  `null` when `process.env.API_URL` is unset; otherwise forwards to
  `${API_URL}${path}` (+ incoming query string), forwarding `Authorization` and
  `trace-id` / `x-trace-id` / `x-request-id` headers, streaming the body through
  (multipart-safe via `arrayBuffer`), and returning the upstream status / body /
  content-type verbatim with any upstream trace id surfaced as `x-trace-id`.
  Unreachable upstream → `problem(502, "Upstream unavailable", …)`.
- `proxyOr(request, path, stub, init?)` — proxy first, else run the offline `stub()`.
- `traceIdOf(res)` helper.

**All 30 `app/api/**/route.ts` handlers rewritten** to
`return proxyOr(request, "/v1/…", () => <current stub>)`. Upstream path mapping is
`/api/<rest>` → `/v1/<rest>` (path params `encodeURIComponent`-escaped). When `API_URL`
is unset every handler returns exactly the previous stub shape (empty payload / `404`
for `GET /api/workspaces/:id` / `501` for the not-yet-implemented mutations), so the UI
still works fully offline. `GET`/`PATCH /api/auth/me` proxy `/v1/auth/me` and fall back
to the blank-viewer / `501` stubs respectively.

> Assumption to confirm against `docs/VERA_BACKEND_PLAN.md` §9: the plan's file
> description endpoint is `/v1/files/{id}/description` whereas the BFF route is
> `/api/workspaces/:wsId/files/:fileId/description` and currently proxies
> `/v1/workspaces/:wsId/files/:fileId/description`. If the backend really is
> workspace-agnostic there, only the `path` string in
> `app/api/workspaces/[workspaceId]/files/[fileId]/description/route.ts` (and
> `.../describe/route.ts`) needs adjusting — the BFF URL the UI calls stays the same.

---

## Downstream contract (for the pages / components agents)

### New shared utilities — import these, delete local copies

| Symbol | Path | Signature |
|---|---|---|
| `formatBytes` | `@/lib/utils/formatBytes` | `(bytes: number) => string` |
| `formatTokens` | `@/lib/utils/formatTokens` | `(n: number) => string` |
| `copyText` | `@/lib/utils/clipboard` | `(text: string) => Promise<boolean>` (never throws) |
| `parseTabularOutput` | `@/lib/data/runDetail` | `(raw: string) => StepOutput` (already existed, still exported) |

### Run-mode type

`export type RunMode = "precise" | "research"` — canonical location
**`@/lib/config/modes`** (also `MODES`, `DEFAULT_MODE`, `MODE_ICONS`, `ModeDTO`).
`ProfileUpdate.defaultRunMode` (`@/lib/data/session`) is now `RunMode`.
`app/(app)/settings/profile/page.tsx` **must stop using `"deep"`**.

### `useResource` fetcher signature change (`@/lib/data/useResource`)

Old: `useResource<T>(fetcher: () => Promise<T>, deps?, options?)`
New: `useResource<T>(fetcher: (ctx?: FetcherContext) => Promise<T>, deps?, options?)`
where `FetcherContext = { signal: AbortSignal }`.
Zero-arg fetchers still compile. To honour cancellation, a data fn should accept
`ctx?: { signal?: AbortSignal }` and pass `{ signal: ctx?.signal }` as `getJson`'s 3rd arg
(see `getCurrentUser` for the pattern). `keepPreviousData` no longer forces a refetch
when toggled (it never should have).

### `useRunStream` (`@/lib/hooks/useRunStream`)

Returns `{ status, events }` as reactive state now.
`StreamStatus = "connecting" | "streaming" | "reconnecting" | "complete" | "error"`.
`eventLog` export **removed**. Consumers should treat `"reconnecting"` as "still live,
last state valid" and only `"error"` as dead.

### `AuthProvider` context (`@/lib/auth/AuthProvider`)

`useAuth()` now also returns `setToken(token: string): void` and `clearToken(): void`.
Token lives in memory only (`@/lib/auth/token`).

### `listRuns` filters (`@/lib/data/runs`)

`RunListFilters` now has `sort?: RunSortField` (`"createdAt" | "cost"`) and
`order?: SortOrder` (`"asc" | "desc"`), forwarded to the server. `app/(app)/runs/page.tsx`
should drop its local `SortField` type, import `RunSortField`, and remove the
client-side `page.items` re-sort (server now orders globally).

### `problem()` helper (`@/app/api/_lib/respond`)

Now `problem(status, title, detail?, traceId?)`. Route handlers that proxy get the
upstream trace id automatically via `proxy()`.
