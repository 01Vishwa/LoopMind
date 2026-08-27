# VERA — Cross-Cutting Security Review

Date: 2026-08-27
Reviewer: automated security-focused code review
Scope: whole repo (BYOK vault, multi-tenant isolation, auth/RBAC, sandbox, secrets hygiene, supply chain, SSRF, upload validation)

---

## 0. Executive context — READ FIRST

The repo is mid-migration and this materially changes what "the code" is:

- **Committed `HEAD` (`a94ec95`)** contains a *legacy* single-service implementation under `backend/`
  (FastAPI + Supabase, NVIDIA-NIM-only, **no BYOK, no key vault, no Postgres RLS**).
- **The working tree / index on branch `issue-fix`** deletes `backend/` wholesale (`git status`:
  `R backend/tests/__init__.py -> .importlinter`, plus ~200 staged `A` files) and replaces it with a
  new **monorepo scaffold** (`apps/api`, `apps/orchestrator`, `apps/worker`, `packages/*`).
- **Every Python file in the new scaffold is empty (0 bytes).** `apps/api/src/vera_api/dependencies/{auth,db,tenancy}.py`,
  `settings.py`, all routers, all `packages/*` (`vera_llm`, `vera_db`, `vera_core`, …), all `db/schema/*.sql`,
  all `db/policies/*.sql`, all `config/*.yaml`, all Dockerfiles, all `pyproject.toml`, root `.env.example`,
  root `package.json`, `.pre-commit-config.yaml`, `Makefile` — **all 0 bytes**.
- The only substantive code on `issue-fix` is the **Next.js frontend** (`apps/web`), whose `app/api/*`
  BFF routes are explicitly stubs (`app/api/_lib/respond.ts`: "Every handler here is a **stub**").
- There is **no `packages/keyvault` / `vera_keyvault` package at all** — not even an empty scaffold file.
  The design doc (section 6) is the only place BYOK vault logic exists.

**Consequence:** almost none of the target attack surface is currently implemented. The findings below are
split into:

- **Part A — Design-doc defects** (`docs/VERA_BACKEND_PLAN.md`): these are the spec the empty files will be
  filled from. Several code snippets in the plan are directly exploitable if typed in as written. This is
  where the actionable security value is.
- **Part B — Legacy `backend/` at `HEAD`** (real, reviewable code, but staged for deletion on this branch).
- **Part C — Frontend (`apps/web`)** — real code, shipped.
- **Part D — Repo hygiene / supply chain** — applies regardless.

---

## PART A — Design-doc defects (docs/VERA_BACKEND_PLAN.md)

These become real vulnerabilities the moment the corresponding empty file is implemented from the snippet.

### A1. SQL injection into RLS context via `SET LOCAL` — **Critical**

`docs/VERA_BACKEND_PLAN.md:1397-1400`:

```python
async def set_tenant(db: AsyncSession, principal: Principal):
    await db.execute(text(f"SET LOCAL app.tenant_id = '{principal.tenant_id}'"))
```

- **Vuln:** f-string interpolation of `principal.tenant_id` into raw SQL. `SET LOCAL` does not accept
  bind parameters in the normal `$1` position, which is exactly why developers reach for string
  formatting here and get it wrong.
- **Exploit:** if `tenant_id` is ever attacker-influenced (JWT with `alg:none` / weak secret — see A2 — or
  a future code path that derives it from a header/body), a value like
  `00000000-0000-0000-0000-000000000000'; SET app.tenant_id = 'victim-uuid` or a stacked statement
  disables/rewrites the RLS predicate for the rest of the transaction, giving full cross-tenant read/write.
  Even without SQLi, a malformed value silently makes `current_setting('app.tenant_id', true)` return NULL,
  and every RLS policy in the plan (`USING (tenant_id = current_setting('app.tenant_id', true)::uuid)`)
  then evaluates `tenant_id = NULL` → NULL → row hidden (fails closed for reads) BUT
  `key_vault` policy (line 915-916) has only `USING`, no `WITH CHECK`, so writes are not symmetric.
- **Fix:**
  1. Validate `principal.tenant_id` is a real `uuid.UUID` object (Pydantic `UUID` type) before use.
  2. Use `SET LOCAL` via `set_config('app.tenant_id', :val, true)` which **does** accept a bind param:
     `await db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": str(tid)})`.
  3. Add `FORCE ROW LEVEL SECURITY` + both `USING` and `WITH CHECK` to every policy (the plan omits
     `WITH CHECK` on `key_vault`).
  4. Ensure the app DB role is **not** the table owner and not `BYPASSRLS`/superuser (Neon default
     role often owns the schema → RLS silently not enforced).

### A2. JWT: algorithm not pinned safely, no `verify_exp`/`aud`, weak default secret — **Critical**

`docs/VERA_BACKEND_PLAN.md:1381-1384` and `:1566`:

```python
async def auth(authorization: str = Header(...)) -> Principal:
    token = authorization.removeprefix("Bearer ").strip()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    return Principal(**payload)
```
```bash
VERA_JWT_SECRET=change-me-in-production
```

- **Vulns:**
  - **Weak committed default secret** `change-me-in-production`. If `settings.py` falls back to it (the
    `.env.example` implies it will), anyone can forge a token:
    `{"sub": <any-user>, "tenant_id": <any-tenant>, "role": "owner", "exp": <far future>}` → full account
    takeover of every tenant. Combined with A1 this is trivial total compromise.
  - **No explicit `options={"require": ["exp"], "verify_exp": True}`** and **no `audience=`/`issuer=`**.
    PyJWT verifies `exp` only *if present*; a token minted without `exp` never expires. No `aud`/`iss`
    binding means a token from any other system signed with the same secret is accepted.
  - **`Principal(**payload)`** — mass assignment. Every JWT claim flows straight into the Principal.
    If any claim name later collides with an internal field, or if `role` validation is loose, privilege
    escalation follows. `role` should be parsed against the `Role` enum and rejected if unknown.
  - **`Header(...)` required** but no handling for missing/malformed `Authorization` → 500 instead of 401
    (info leak / DoS surface).
- **Fix:** load secret with **no default** and fail startup if unset and not dev; enforce
  `jwt.decode(token, key, algorithms=["HS256"], options={"require":["exp","sub"], "verify_exp":True},
  audience="vera-api", issuer=settings.jwt_issuer)`; validate `role` against enum; catch decode errors →
  401. If prod uses OIDC/asymmetric (plan 9.1 says "OIDC provider (prod)"), pin `algorithms=["RS256"]`
  or `["ES256"]` **only** and never accept HS256 alongside asymmetric (classic RS256→HS256 confusion:
  attacker signs with the public key as HMAC secret).

### A3. `require_role` is not wired as a dependency and is bypassable — **High**

`docs/VERA_BACKEND_PLAN.md:1386-1391`:

```python
async def require_role(*allowed: Role):
    def checker(principal: Principal = Depends(auth)):
        ...
    return checker
```

- `require_role` is `async def` but returns `checker` synchronously used as `Depends(require_role(...))` —
  FastAPI would treat the coroutine as the dependency. As written it does not enforce anything.
- The RBAC matrix (plan 12) is a table with **no enforcement mechanism specified per route**. History
  shows this class of app ships routers with `Depends(auth)` only and forgets per-verb role checks →
  viewers can mutate. Every mutating route needs an explicit `Depends(require_role(OWNER, ADMIN, ANALYST))`.
- **IDOR:** plan router snippets (e.g. SSE `:1304`) fetch by `run_id` + `tenant_id` (good), but
  `provider`/`workspace`/`file` GET-by-id endpoints in 9.2 are not shown filtering by `tenant_id`/`user_id`.
  `GET /v1/files/{id}` and `GET /v1/files/{id}/description` in particular are tenant-scoped only via RLS —
  if RLS is misconfigured (A1) these become cross-tenant reads. Defense in depth: filter in the repo query
  too, never rely on RLS alone.
- **Fix:** make `require_role` a plain sync factory returning a dependency; add a route test matrix
  (schemathesis + per-role fixtures) asserting 403 for every disallowed (role,endpoint) pair.

### A4. Key Vault: per-tenant key derivation salted with `tenant_id`, no AAD, no rotation history — **High**

`docs/VERA_BACKEND_PLAN.md:877-899, 919-925`:

- `HKDF(master, salt=tenant_id)` — `tenant_id` is a **non-secret, low-entropy, publicly-knowable UUID**
  used as the HKDF salt. That is acceptable for domain separation but the doc frames it as a security
  boundary ("a compromised tenant's keys cannot decrypt another tenant's vault"). It is **not** — whoever
  has `VERA_VAULT_MASTER_KEY` can derive every tenant key. The only real protection is master-key secrecy.
  Document it honestly and put the master key in a KMS/HSM, not an env var (`.env.example:1567`
  `VERA_VAULT_MASTER_KEY=base64-...` → ends up in shell history, CI logs, container inspect).
- **No associated data / binding.** Fernet token for `provider:<connX>:api_key` can be copied into
  another row (`provider:<connY>:api_key`) and still decrypts. Bind the `ref` (and tenant) as AAD — use
  AES-GCM with AAD instead of Fernet, or store an HMAC(ref) alongside and verify.
- **Raw asyncpg string SQL** in `store`/`retrieve` (`"... WHERE tenant_id = $1 AND ref = $2"`) — this
  path bypasses the SQLAlchemy session that sets `app.tenant_id`, so **RLS on `key_vault` is not applied**
  to the vault's own queries. If the `ref` is ever attacker-controlled (it is derived from
  `provider_connection_id` which is a user-supplied path param on `POST /v1/providers/{id}/...`), and the
  connection lookup that maps id→tenant is flawed, you get cross-tenant key retrieval. Enforce tenant in
  the query **and** run it through the RLS-scoped connection.
- **"Key rotation: old ciphertext is not preserved"** — fine, but there is no re-encryption story for
  `VERA_VAULT_MASTER_KEY` rotation (all tenants' keys become undecryptable). Add a key-version column.
- **Fix:** AES-256-GCM with `aad = tenant_id || ref`; master key from KMS; `key_version smallint`;
  vault queries go through the RLS session.

### A5. SSRF — user-supplied provider `base_url` (NIM) and `webhook_url` — **High**

- `ProviderConnection.base_url: HttpUrl` (plan 3.1 `:151`) is **user-supplied** for NVIDIA NIM
  ("User-provided (e.g., https://nim.corp.internal/...)", plan 2.3). The gateway then does
  `url = f"{conn.base_url}/chat/completions"` (`:733`) and `await self.http.*` with the **decrypted API
  key in the Authorization header** (`:844`). Nothing in the plan validates `base_url` against:
  - private/link-local ranges (`169.254.169.254` cloud metadata, `127.0.0.0/8`, `10/8`, `172.16/12`,
    `192.168/16`, `::1`, `fd00::/8`),
  - non-http(s) schemes, credentials in URL, redirects to internal hosts,
  - DNS-rebinding (resolve once, pin the IP for the request).
- **Exploit:** attacker adds a "NIM" connection with `base_url=http://169.254.169.254/latest/meta-data/iam/security-credentials/`
  → validation flow (`:847` `GET {base_url}/models`) and every subsequent agent call SSRFs into the VPC,
  and VERA will forward the attacker's own bearer token there (harmless) but more importantly returns the
  response body to the attacker → cloud credential theft, internal port scan, hitting internal admin APIs.
- Same for `notification_preferences.webhook_url` (DDL `:648`) used by
  `POST /v1/settings/notifications/test-webhook` (plan 9.2) and background webhook dispatch (plan 18 slice 12).
- **Fix:** allowlist. For OpenRouter, ignore user `base_url` entirely (hardcode). For NIM, require the
  user to pre-register the endpoint host, resolve DNS and reject non-public IPs at request time (not just
  validation time), disable redirects, set tight timeouts, block non-443. For webhooks, same egress
  filter + require https + sign the payload (HMAC) + cap response read.

### A6. Sandbox — AST deny-list is bypassable by design; no container hardening guarantees — **High**

`docs/VERA_BACKEND_PLAN.md:1117-1131`:

```python
DENIED_MODULES = {"socket","requests","urllib",...,"os","sys",...,"pickle","importlib","code","compile","exec","eval",...}
DENIED_ATTRIBUTES = {"os.system","os.popen",...,"__import__","globals","locals","breakpoint"}
```

- **An AST name/attribute deny-list is not a security boundary.** Trivial bypasses:
  `__builtins__['ev'+'al']`, `getattr(__import__('o'+'s'),'system')`, `().__class__.__base__.__subclasses__()`
  to reach `Popen`, `breakpoint()` via `sys.breakpointhook`, reading `/proc`, `ctypes` via
  `importlib` alternatives, encoded source, `exec(compile(...))` reconstructed from string ops. The plan
  even lists `compile`/`exec`/`eval` as "modules" which shows the model is confused (they're builtins).
- The **real** boundary is the container config (`:1094-1101`): `network_disabled=True`, `read_only=True`,
  `user="nonroot"`, `pids_limit`, `mem_limit`, `tmpfs noexec`, `cpu_quota`. Those are good — but:
  - **no `--cap-drop=ALL`, no `--security-opt=no-new-privileges`, no seccomp/apparmor profile,
    no user-namespace remap** mentioned. Without `cap-drop ALL` + `no-new-privileges` a container-root
    (or setuid) process has a much larger kernel attack surface.
  - **mounts are `mode: "ro"` but `m.host_path` is interpolated directly** (`:1091`). If `DataMount.host_path`
    is ever derived from the file `uri` (`.vera/objects/<sha>`) without canonicalization, a crafted `uri`
    could mount arbitrary host paths (`/`, `/var/run/docker.sock`) read-only into the sandbox → host fs read.
  - **`workdir` bind is `ro` but `/tmp` tmpfs has `noexec` only, not `nosuid`/`nodev`**.
  - Docker socket access by the API/orchestrator to spawn containers = the orchestrator is effectively
    root on the host. A sandbox escape → orchestrator → host. Use gVisor/Kata or a rootless/remote
    builder, or Firecracker.
  - `_stream_with_timeout` then `container.wait()` — if `wait` hangs (docker daemon issue) there's no
    hard kill deadline shown; `container.remove(force=True)` is only reached on the happy path.
- **Fix:** treat AST scan as *lint only* (defense in depth, never rely on it). Harden the runtime:
  `cap_drop=["ALL"]`, `security_opt=["no-new-privileges:true","seccomp=<profile>"]`, userns-remap or
  rootless, gVisor runtime, `nosuid,nodev,noexec` on all tmpfs, no host bind mounts (copy data in or use
  a named volume populated out-of-band), hard wall-clock kill via `asyncio.wait_for` around the whole
  execution with `finally: container.remove(force=True)`.

### A7. Structured-output fallback mutates and echoes caller messages; prompt-injection of schema — **Low/Med**

`docs/VERA_BACKEND_PLAN.md:797-809`: the non-JSON-mode fallback does
`kwargs["messages"][-1]["content"] += schema_instruction` (mutates caller's list) and on failure appends
the raw `ValidationError` (`f"JSON validation failed: {e}"`) back into the model context — `e` can contain
attacker-controlled data from the file being analyzed, enabling second-order prompt injection into the
coder/planner. Low direct impact but relevant given sandboxed code execution downstream. Deep-copy
messages; sanitize error text.

### A8. `asyncio.create_task(self.orchestrator.execute(run))` — no isolation, no backpressure — **Med**

`docs/VERA_BACKEND_PLAN.md:1360`. Runs execute in-process in the API event loop. A malicious/expensive run
(or many) starves the API, and an unhandled exception in the task is swallowed. Budget caps
(`max_cost_usd`, `max_wall_clock_s`) are in the state model but enforcement is "later (Temporal)".
DoS + cost-exhaustion (BYOK: the *user's* money, but also VERA's provider-side rate limits / a shared
OpenRouter referer). Move to a real queue/worker with concurrency limits before shipping runs.

### A9. `.env.example` (plan `:1556-1580`) ships real-looking secret slots with weak placeholders

`VERA_JWT_SECRET=change-me-in-production` (A2) and `VERA_VAULT_MASTER_KEY=base64-encoded-32-byte-key`.
Startup must refuse these exact values outside dev.

---

## PART B — Legacy `backend/` at HEAD (staged for deletion on `issue-fix`)

Real code, currently committed at `a94ec95`. If the migration is abandoned/reverted, these apply.
This service is **NVIDIA-NIM-only, server-holds-the-key — not BYOK — and has no Postgres RLS**
(uses Supabase; tenancy relies on `user_id` filters in `supabase_service.py`).

### B1. Path traversal in file upload — **High**

`backend/api/controllers/upload_controller.py:77-88, 192-206`:

```python
def _resolve_file_path(workspace_id: str, filename: str) -> str:
    return os.path.join(base_dir, workspace_id, filename)
...
file_path = _resolve_file_path(workspace_id, file.filename)   # file.filename straight from client
os.makedirs(os.path.dirname(file_path), exist_ok=True)
# ... open(file_path, "wb")
```

- The comment claims "sanitised by save_upload_file" but this path is used directly. `file.filename` is
  fully client-controlled. `os.path.join(base, wsid, "../../../etc/cron.d/x")` escapes `base_dir`; an
  absolute `filename` (`/etc/...`) makes `os.path.join` discard the prefix entirely.
- `workspace_id` is also unvalidated and concatenated → `workspace_id="../other-tenant"` writes into
  another workspace dir.
- **Exploit:** arbitrary file write on the API host (RCE via cron/`.bashrc`/writable app code), or
  cross-workspace file pl+ description poisoning.
- **Fix:** `name = werkzeug.utils.secure_filename(file.filename)` (or `os.path.basename` + allowlist
  charset), validate `workspace_id` is a UUID owned by the caller, then
  `final = os.path.realpath(os.path.join(base, wsid, name)); assert final.startswith(os.path.realpath(base)+os.sep)`.

### B2. Sandbox defaults to subprocess, not Docker; `DOCKER_SANDBOX_ENABLED=false` by default — **High**

`backend/core/config.py` (`DOCKER_SANDBOX_ENABLED` default `"false"`), `backend/.env.example`
(`DOCKER_SANDBOX_ENABLED=false`), `backend/core/executor/code_executor.py`.

- Out of the box, LLM-generated Python runs as a **subprocess on the API host** with only:
  a sanitised env, `RLIMIT_CPU`/`RLIMIT_AS` (Unix only — **no-op on the Windows dev host this repo targets**,
  per `git config` / platform), output caps, and `os.killpg` on timeout.
- **No filesystem isolation, no network isolation** in subprocess mode. Generated code can read the API
  source, read `backend/.env` (`SUPABASE_JWT_SECRET`, `SUPABASE_SERVICE_ROLE_KEY`, `NVIDIA_API_KEY`),
  open sockets, exfiltrate. `SUPABASE_SERVICE_ROLE_KEY` = full DB bypass of all RLS.
- The code comment says "FAIL-CLOSED: raises RuntimeError when Docker is enabled but unavailable — no
  subprocess fallback in production" — but that only triggers when `DOCKER_SANDBOX_ENABLED=true`, which
  is not the default and not enforced.
- **Fix:** default to Docker; refuse to start if sandbox backend is `subprocess` and
  `ENV != "dev"`; on Windows there is effectively no sandbox — block run execution.

### B3. AST/import validation — same deny-list weakness as A6. `backend/core/validation.py` +
`_run_popen_capped` path allowlist is bypassable (checks `args`, not what the script does at runtime).

### B4. `backend/middleware/auth.py` — mostly OK, two issues — **Med**

- Accepts **both ES256 (JWKS) and HS256** based on the token's own `alg` header (`_decode_supabase_jwt`).
  If `SUPABASE_JWT_SECRET` is set (it's "REQUIRED" per `.env.example`), an attacker who learns the
  project's JWT secret (or if it's weak) can forge HS256 tokens even on projects that use asymmetric keys.
  Supabase JWT secret is a shared symmetric secret → treat HS256 acceptance as legacy-only and gate it
  behind an explicit `ALLOW_HS256=true` (the docstring mentions this but the code does not implement the gate).
- `get_optional_user` swallows all `HTTPException` and returns `None` — fine for truly optional routes,
  but make sure no mutating route uses it.
- Positive: `audience="authenticated"` enforced, `verify_aud=True`, `ExpiredSignatureError` handled,
  disallowed algs rejected, JWKS fetched async with timeout. Reasonable.

### B5. `RRequestLoggerMiddleware` decodes the Bearer token **without verifying signature**
(`backend/middleware/request_logger.py:34-46`) to extract `user_id` for logs. Low risk (logging only,
claims not trusted for authz) but an attacker can forge log lines / poison analytics with arbitrary
`user_id`. Note it and ensure that value never feeds a security decision.

### B6. CORS — `backend/main.py:171` reads `ALLOWED_ORIGINS` from env, refuses to start if unset
(`.env.example`: "Server refuses to start if not set"). Good. Verify `allow_credentials` is not `True`
together with a wildcard (couldn't confirm full `add_middleware` args — check `allow_methods`/`allow_headers`
are not blanket `["*"]` with credentials).

---

## PART C — Frontend (apps/web) — shipped code

### C1. No auth on the BFF; `/api/auth/me` returns a hardcoded empty `viewer` — **N/A yet / by design**

`apps/web/app/api/auth/me/route.ts` returns `{id:"",name:"",email:"",role:"viewer",...}` unconditionally;
`apps/web/app/api/_lib/respond.ts` documents every handler as a stub. `next.config.ts` `rewrites()` proxies
`/api/v1/*` → `${API_URL}/v1/*` with **no auth header injection and no cookie→bearer exchange** — the BFF
does not forward credentials at all. This is pre-auth scaffold, not a live vuln, but flag: when wired,
the browser must never hold the provider keys or the raw JWT in `localStorage`; use httpOnly cookies and
exchange server-side in the route handlers / rewrite.

### C2. `next.config.ts` — `API_URL` from env into `rewrites` destination; `images.remotePatterns`
allows `http://localhost`. Dev-only; ensure prod build pins https and a fixed internal host (no
user-influence over `API_URL`). Not currently exploitable.

### C3. File-type validation is client-side only (`apps/web/lib/config/fileTypes.ts`,
`components/workspace/UploadDropzone.tsx`) — react-dropzone `accept` is a UX hint, trivially bypassed.
`kindFromFilename` trusts the extension. **No size check anywhere in the web layer.** The server (once it
exists) must do magic-byte sniffing, size caps (`max_file_size_bytes`), decompression-bomb limits for
`zip`/`xlsx`/`parquet`, and filename sanitization (see B1). `sqlite`/`zip` uploads are a notable RCE/DoS
surface for the analyzer.

### C4. `apps/web/lib/data/workspaceFiles.ts` / `http.ts` — uses `encodeURIComponent` on path segments
(good), no obvious client-side injection. `respond.ts` `traceId: Math.random()` — non-crypto, fine for a
trace id, don't use that pattern for anything security-sensitive.

---

## PART D — Repo hygiene & supply chain

### D1. No secrets committed — **OK**
`git log --all -p` grep for key/secret/token/password patterns across all 25 commits and all history:
only match is `backend/tests/test_auth_middleware.py:118` `_make_token(secret="wrong-secret")` — a test
fixture, not a real secret. `backend/.env.example` and root `.env.example` use `<placeholder>` values.
No `.env`, `*.pem`, `id_rsa`, service-account JSON, or real API keys in `git ls-files`.

### D2. `.gitignore` — **adequate.** Covers `.env`, `.env.local`, `apps/*/.env*`, `.venv`, `*.sqlite3`,
`*.db`, `node_modules`, `.next`. Gaps: does not ignore `.review/` (this file — intentional?),
`*.pem`/`*.key`/`credentials.json`/`.aws`/`secrets.*`, `.turbo` is covered. Recommend adding a
belt-and-braces `*.key`, `*.pem`, `*_rsa`, `.env.*` (currently only specific suffixes).

### D3. Supply chain — **only `apps/web/package.json` is populated; all `pyproject.toml` are 0 bytes.**
- `apps/web/package.json` uses **caret ranges** (`^`) for every dependency and **has a committed
  `package-lock.json`** (325 KB) — so installs are reproducible in CI if `npm ci` is used. Acceptable.
- `next: 15.0.3`, `react: 19.0.0` pinned exact (good). `@monaco-editor/react`, `framer-motion`,
  `react-markdown` + `remark-gfm` — `react-markdown` renders model/agent output; ensure `rehype-raw` is
  NOT added and no `dangerouslySetInnerHTML` around report markdown (XSS via LLM output). Quick check:
  `CitationPopover.tsx` / `report/page.tsx` should be reviewed when report rendering is wired.
- No `pyproject.toml` content → cannot assess Python pins. When populated: pin exact + hashes
  (`uv.lock`/`pip-compile --generate-hashes`), watch `cryptography`, `pyjwt` (pin >=2.10 to avoid
  CVE-2024-53861 aud bypass and older `alg` issues), `langgraph`, `httpx`, docker SDK.
- `.pre-commit-config.yaml` is empty → no automated secret-scanning (`detect-secrets`/`gitleaks`),
  no `bandit`, no `ruff`. Add them.

### D4. `.importlinter` present (renamed from a test `__init__.py`) — check it actually defines contracts;
architecture-as-lint is good for keeping the vault/adapter boundaries enforced. Could not read (may be
0/near-0 bytes).

### D5. Dockerfiles all 0 bytes — when written: non-root `USER`, no build secrets in layers,
pinned base image digests, `--chmod` on copies, drop the docker socket from the API image (see A6).

---

## Severity ranking (actionable)

| # | Severity | Where | Issue |
|---|----------|-------|-------|
| A2 | **Critical** | plan → `apps/api/.../auth.py` (empty) + `.env.example` | Weak default JWT secret `change-me-in-production` + no `exp`/`aud` enforcement + `Principal(**payload)` mass-assign → cross-tenant account takeover |
| A1 | **Critical** | plan → `apps/api/.../tenancy.py` (empty) | f-string `SET LOCAL app.tenant_id = '{tenant_id}'` → SQLi / RLS disable; missing `WITH CHECK` on `key_vault` policy |
| B1 | **High** | `backend/api/controllers/upload_controller.py:77-88` (committed) | Path traversal via `file.filename` / `workspace_id` → arbitrary file write / RCE |
| B2 | **High** | `backend/core/config.py`, `code_executor.py` (committed) | Sandbox defaults to host subprocess; no fs/net isolation; no-op rlimits on Windows; `.env` with `SUPABASE_SERVICE_ROLE_KEY` readable by generated code |
| A6 | **High** | plan → `packages/sandbox` (does not exist) | AST deny-list is not a boundary; container config missing `cap-drop ALL` / `no-new-privileges` / seccomp / userns; host bind-mount interpolation; orchestrator holds docker socket = host root |
| A5 | **High** | plan → LLM gateway / notifications (empty) | SSRF via user-supplied NIM `base_url` and `webhook_url`; no private-IP/metadata filtering; forwards decrypted key |
| A4 | **High** | plan section 6 → `vera_keyvault` (does not exist) | Master key in env not KMS; no AAD binding ciphertext↔ref; raw asyncpg queries bypass RLS session; no master-key rotation/versioning |
| A3 | **High** | plan section 12 → routers (empty) | `require_role` non-functional as written; no per-route RBAC enforcement specified; IDOR on `GET /v1/files/{id}` relies on RLS alone |
| B4 | **Med** | `backend/middleware/auth.py` (committed) | HS256 accepted alongside ES256 with no gate; shared Supabase JWT secret forgeable |
| A8 | **Med** | plan `:1360` | `asyncio.create_task` run execution in API process; no queue/backpressure; budget caps unenforced → DoS + cost exhaustion |
| C3 | **Med** | `apps/web` upload + server (empty) | File validation client-side only; no size cap; zip/xlsx/sqlite decompression-bomb & RCE surface for analyzer |
| B5 | **Low** | `backend/middleware/request_logger.py:34` | Unverified JWT decode for logging → forgeable `user_id` in logs |
| A7 | **Low** | plan `:797-809` | Structured-output fallback mutates caller messages & echoes attacker-influenced `ValidationError` into model context |
| D2/D3 | **Low** | `.gitignore`, `.pre-commit-config.yaml` (empty), `pyproject.toml` (empty) | Add `*.key`/`*.pem` ignores; add gitleaks/bandit/ruff pre-commit; pin Python deps with hashes, `pyjwt>=2.10` |

## Positives

- No real secrets in git history (D1).
- `.gitignore` covers env files and local DBs (D2).
- `apps/web` has a committed lockfile; `next`/`react` pinned exact (D3).
- Legacy `backend/middleware/auth.py` enforces `aud`, `exp`, rejects unknown algs, async JWKS with timeout (B4 positive).
- Legacy CORS fails closed if `ALLOWED_ORIGINS` unset (B6).
- Plan's *intent* is sound: per-tenant RLS with `FORCE`, `SecretStr`, "never log / never return keys",
  one-container-per-exec, `network_disabled`, `read_only`, non-root, pids/mem/cpu limits. The gaps are in
  the sample code, not the goals.

## Top recommendations (order)

1. Before any backend code is written from the plan, fix the plan snippets A1 and A2 (they are copy-paste
   sources) and add a "security requirements" section: no default secrets, `set_config()` bind param,
   AES-GCM+AAD vault, KMS master key, SSRF allowlist, container `cap-drop ALL`+seccomp+gVisor, per-route RBAC.
2. If the legacy `backend/` stays alive at all: patch B1 (path traversal) and B2 (force Docker sandbox / block on Windows) now.
3. Populate `.pre-commit-config.yaml` with `gitleaks`, `bandit`, `ruff`; add CI dependency-audit (`pip-audit`, `npm audit`).
4. Add the RBAC route-matrix test and an RLS integration test (two tenants, assert zero cross-tenant rows) as merge gates for slice 8/9.
