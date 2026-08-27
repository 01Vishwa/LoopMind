# VERA Codebase Review — Consolidated Findings

Date: 2026-08-27
Branch reviewed: `issue-fix`
Reviewers: 4 parallel review passes (backend/core, orchestrator/LLM/sandbox, frontend, security)

Detailed reports:
- [`backend.md`](./backend.md) — apps/api, packages/core, packages/db, observability, root config
- [`orchestrator.md`](./orchestrator.md) — apps/orchestrator, apps/worker, packages/{llm,sandbox,retrieval,evals}, tools
- [`frontend.md`](./frontend.md) — apps/web
- [`security.md`](./security.md) — cross-cutting security + legacy backend/

---

## The headline

**This branch is a regression, not a feature branch.** Commit `71bcece` (and follow-ups) delete the
entire previously-working `backend/` implementation (DS-STAR orchestrator, 9 agents, 7 parsers,
DB SQL, 11 test files) and stage a new `apps/` + `packages/` monorepo in which **every Python file,
every SQL file, every Dockerfile, every `pyproject.toml`, `ruff.toml`, `mypy.ini`, `Makefile`,
`.importlinter`, `.pre-commit-config.yaml`, `config/*.yaml`, `docs/api/openapi.yaml`, `.env.example`,
and `README.md` is 0 bytes.**

Commit messages such as *"feat: implement multi-file workspace upload system…"* and
*"feat: implement secure code execution engine with sandboxed subprocess…"* correspond to empty
files. Git history on this branch is not trustworthy.

The **only real code** in the changeset is `apps/web` (~5k lines of TypeScript), plus lock files
(`pnpm-lock.yaml`, `apps/web/package-lock.json`, `uv.lock`) and `docs/`.

### Recommended immediate action

1. **Do not merge `issue-fix`.** In its current state it destroys the working backend and ships nothing.
2. Decide explicitly: is the plan (`docs/VERA_BACKEND_PLAN.md`) a rewrite that should happen on a
   long-lived branch while `main` keeps the legacy backend, or is the legacy backend truly dead?
3. If rewriting: keep the legacy `backend/` on `main` until `apps/api` reaches Build-Order slice 9,
   and land the rewrite in vertical slices (see plan §18), each with tests, not as one empty scaffold.
4. Regardless of direction, fix the **legacy backend security bugs below** if any deployment still runs it.

---

## Repo hygiene (blocks all backend work)

| # | Issue | Impact |
|---|---|---|
| H1 | Root `pyproject.toml` empty, but `uv.lock` committed against no manifest | Nothing installable/lintable/testable |
| H2 | `README.md` 0 bytes | No project entry point |
| H3 | Dueling package managers: `pnpm-lock.yaml` + `pnpm-workspace.yaml` at root vs `apps/web/package-lock.json` | Non-deterministic installs; CI vs local drift. Pick pnpm, delete the npm lockfile |
| H4 | `.importlinter`, `.pre-commit-config.yaml`, `ruff.toml`, `mypy.ini`, `Makefile` all empty | No import-layering contract, no lint/format/secret-scan hooks |
| H5 | `.importlinter` was created by `git mv backend/tests/__init__.py .importlinter` | Rename artifact — verify intent |
| H6 | All `tests/**` and `apps/*/tests/**` are `.gitkeep` only | Zero backend test coverage; plan §18 gates can't be verified |
| H7 | `.gitignore` missing `*.key` / `*.pem` | Key material not protected from accidental commit |
| H8 | Layout diverges from plan §16: `packages/llm` vs `packages/adapters/llm`; `tools/vera-cli` vs `apps/cli`; no `keyvault`/`storage`/`events` adapter packages | Reconcile before implementing |
| H9 | `apps/orchestrator` adds Temporal-style `activities/` + `workflows/` dirs; plan §7/§11 says in-process LangGraph ("Temporal later") | Execution model undecided |

---

## Security — CRITICAL (design doc; will be real once typed in)

| ID | Issue | Fix |
|----|-------|-----|
| A2 | `.env.example` ships `VERA_JWT_SECRET=change-me-in-production`; plan's `auth()` does `jwt.decode` with no `exp`/`aud` check then `Principal(**payload)` mass-assigns `role` | Require secret from env with no default; enforce `exp`/`aud`/`iss`; construct `Principal` field-by-field; map `InvalidTokenError`→401 (no `UnauthorizedError` exists in the taxonomy today) |
| A1 | `dependencies/tenancy.py` planned as `text(f"SET LOCAL app.tenant_id = '{principal.tenant_id}'")` — SQL injection / RLS bypass | `await db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": str(tenant_id)})`; validate UUID; ensure the app DB role is not table owner and lacks `BYPASSRLS` |
| — | `key_vault` RLS policy has `USING` but no `WITH CHECK` | Add `WITH CHECK` |

## Security — CRITICAL (real, committed in legacy `backend/` at HEAD)

| ID | Issue | Fix |
|----|-------|-----|
| B1 | `backend/api/controllers/upload_controller.py:77-88` — `os.path.join(base, workspace_id, file.filename)` with unsanitized client filename → path traversal / arbitrary file write → RCE | Generate server-side name; `secure_filename`; resolve and assert path stays under the workspace dir |
| B2 | `DOCKER_SANDBOX_ENABLED` defaults false → LLM-generated code runs as a **host subprocess** with no fs/net isolation; rlimits are no-ops on Windows dev hosts; that code can read `backend/.env` including `SUPABASE_SERVICE_ROLE_KEY` (full RLS bypass) | Fail closed when Docker unavailable; never run model code un-isolated; move secrets out of readable cwd |
| B4 | Legacy `auth.py` accepts HS256 alongside ES256 with no gate — token forgeable with the shared Supabase JWT secret | Pin to the asymmetric alg only; reject HS* |

## Security — HIGH (design)

- **A5 SSRF:** user-supplied NIM `base_url` and notification `webhook_url` never validated against
  private / link-local / `169.254.169.254` ranges; gateway forwards the decrypted key → cloud-credential theft.
- **A6 Sandbox:** AST deny-list is trivially bypassable (`getattr`, `__import__`, dunder traversal, string
  obfuscation) and must not be treated as a boundary; planned container config omits `cap-drop ALL`,
  `no-new-privileges`, seccomp, userns; `mount.host_path` interpolated; orchestrator holding the docker
  socket == host root. gVisor/microVM is the real boundary.
- **A4 Key vault:** master key in env not KMS; Fernet token has no AAD binding ciphertext ↔ ref ↔ tenant;
  planned raw asyncpg queries bypass the RLS-scoped session; no master-key rotation/versioning.
- **A3 RBAC:** `require_role` as written is `async def` returning a sync closure — non-functional as a
  FastAPI dependency; no per-route enforcement specified; `GET /v1/files/{id}` leans on RLS alone (IDOR if RLS misconfigured).
- **A8 DoS/cost:** `asyncio.create_task(orchestrator.execute(run))` runs in the API process; budget caps unenforced.

## Security — MEDIUM / LOW

- C3 upload validation client-side only, no size cap → zip/xlsx/sqlite decompression bombs + analyzer RCE surface.
- B5 request logger decodes JWT unverified → forgeable `user_id` in logs.
- A7 structured-output fallback mutates the caller's `messages` list and echoes attacker-influenced parse errors back into model context.
- D2/D3 empty `.pre-commit-config.yaml` (no gitleaks/bandit), empty `pyproject.toml` (deps unpinned, no hashes; pin `pyjwt>=2.10`).

### Security positives
No real secrets in git history. `.gitignore` covers `.env*`, `.venv`, local DBs. `apps/web` has a
committed lockfile with `next`/`react` pinned exact. Legacy `backend/middleware/auth.py` does enforce
`aud`/`exp`, rejects unknown algs, uses async JWKS with timeout; legacy CORS fails closed when
`ALLOWED_ORIGINS` is unset. The plan's stated intent (FORCE RLS, `SecretStr`, never log/return keys,
one-container-per-exec, `network_disabled`) is sound — the defects are in the sample code.

---

## Backend plan-level risks (to fix before/while implementing)

1. `BudgetExhaustedError` has `status = 200` — a `200 application/problem+json` document is invalid.
   Budget exhaustion is a terminal run state, not an HTTP error.
2. RFC 9457 problem docs lack `instance` and a field-error extension schema.
3. UUIDv7 requirement (§9.4) contradicted by `gen_random_uuid()` defaults throughout the DDL.
4. `Idempotency-Key` promised on all POSTs (§9.4) with no table or middleware.
5. SSE design (§10): no `request.is_disconnected()` loop check, no heartbeat frames, terminal-state
   check misses `CANCELLED`, and `event.payload.model_dump_json()` is called on a value the schema
   declares as a plain `jsonb` dict.
6. `.importlinter` empty → hexagonal port/adapter boundaries unenforced (this was Build-Order slice 1's whole point).
7. `observability/redaction.py` — the control that keeps API keys out of logs — is unimplemented.
8. `packages/llm` scaffold missing `providers.py` (`PROVIDER_CONFIGS`) and `validation.py`
   (`validate_connection`) from §5.2 / §5.5. Extra `routing.py` / `caching.py` not in the plan risk
   violating the §5 "thin pass-through" principle — bound their scope with a design note.
9. HS256 (dev) vs "OIDC in prod" (RS256/JWKS) unreconciled in the auth dependency.

---

## Frontend (`apps/web`) — real bugs

| # | File | Bug |
|---|------|-----|
| F1 | `tailwind.config.ts:17-45` + `styles/globals.css:191-232` | Colour tokens defined twice and diverge. Config hard-codes the *light* hex palette for all `vera-*` utilities; globals.css only re-maps ~40 of them to `var(--vera-*)`. Every utility outside that subset (all `/<opacity>` variants, `ring-*`, `accent-hover`) renders static light hex in dark mode — which is the default theme. Pervasive. |
| F2 | `lib/hooks/useRunStream.ts:108-111` | Returns `statusRef.current` / `eventsRef.current` (refs mutated in an effect) → never re-renders; consumers see `"connecting"` / `[]` forever. Also re-hydrates via raw `fetch` with `as RunStateDTO` and no Zod parse. (Currently unused — run page polls the stub instead, so `StatusBar` shows `Round 1/0` indefinitely.) |
| F3 | `lib/data/*` vs `lib/api/client.ts` | Two disconnected API layers, neither wired. `lib/data/*` → Next `/api/*` **stubs** (return empty / 501); dead `lib/api/client.ts` + `useRunStream` → `/api/v1/*` rewrite. **Nothing attaches an auth token anywhere**; no login; `/api/auth/me` always returns a blank `viewer`. |
| F4 | `settings/layout.tsx:266-281`; `runs/[runId]/page.tsx:359-495` | Renders `{children}` in both `hidden lg:flex` and `lg:hidden` branches → every settings page mounts twice (double `useResource`). Run page renders the three panes twice → two lazy Monaco instances on all viewports. |
| F5 | `runs/page.tsx:1672`, `WorkspaceTable.tsx:873`, `usage/page.tsx:1391` | `<tr onClick>` with no `tabIndex` / `onKeyDown` — not keyboard-operable (WCAG 2.1.1). `FileGrid` does it correctly; pattern just isn't applied consistently. |
| F6 | `NewWorkspaceModal`, `DescriptionDrawer`, `CitationPopover` | Dialogs/drawers: no focus trap, no initial/restore focus, no Escape (modal has none at all). `DescriptionDrawer` uses `role="complementary"` for a modal slide-over. `@radix-ui/react-dialog` is already a dependency. |
| F7 | `report/page.tsx:827-895` | Bespoke markdown line-parser while `react-markdown` + `remark-gfm` are installed and unused. `line.replace(/\*\*(.*?)\*\*/g, "**$1**")` (:885) is a no-op → **bold never renders**; lists only match literal `1./2./3.`. |
| F8 | `modes.ts` / `runSchemas.ts` vs `profile/page.tsx:745` | Run-mode union is `"precise" \| "research"` in most places but `"precise" \| "deep"` in `ProfileUpdate.defaultRunMode`. Saving a profile emits `"deep"`, which no `RunMode` consumer accepts. |
| F9 | `saved-analyses/page.tsx:54-63`, `runs/page.tsx:1471` | Optimistic mutations with no rollback: rerun marked `"succeeded"` unconditionally; `togglePause` / `handleDelete` swallow failures; `handleRetry` throws unhandled. `settings/team/page.tsx` does snapshot+rollback correctly — inconsistent. |
| F10 | `package.json` | `@types/react` v18 against React 19 (type-check breakage). Fonts loaded 3× (`next/font` + `<link>` + CSS `@import`); JetBrains Mono never via `next/font` → CLS on every `.text-display` heading. `borderRadius` tokens defined then ignored for hundreds of inline `style={{ borderRadius: "6px" }}`. |

Smaller: `useResource` has no `AbortController`; runs list sorts one server page client-side while
paginating; `ObservationPane` `aria-live` wraps the entire stdout buffer; pane resizers missing
`aria-valuenow/min/max`; `lib/api/client.ts` + `eventLog` dead code; data-layer types exported *from*
presentational components; unguarded `navigator.clipboard` writes; `formatBytes`/`fmtTokens` duplicated 4×.

### Frontend positives
`lib/data/http.ts` error normalisation, `lib/config/*` centralisation, skip link, focus-visible,
reduced-motion handling, debounced `aria-live` in `StatusBar` & `VerdictBanner`, and stubs shaped so
the UI degrades to empty states rather than crashing.
