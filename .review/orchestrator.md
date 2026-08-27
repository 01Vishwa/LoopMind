# VERA Code Review — Orchestrator / LLM / Sandbox / Retrieval / Evals / Tools

**Reviewer scope:** `apps/orchestrator/**`, `apps/worker/**`, `packages/llm/**`, `packages/sandbox/**`, `packages/retrieval/**`, `packages/evals/**`, `tools/**`
**Date:** 2026-08-27
**Branch:** `issue-fix`

## Headline finding

**Every file in scope is an empty 0-byte placeholder. There is no source code to review.**

The `apps/` + `packages/` monorepo described in `docs/VERA_BACKEND_PLAN.md` has been
*scaffolded* — the full directory tree and file names exist — but not a single
`.py`, `.sql`, `.json`, `.toml`, `Dockerfile`, or shell script in scope contains
any content. This was verified two ways:

```
find <scope> -type f -printf '%s\t%p\n'   # every entry reports size 0
git ls-files '*.py' | xargs wc -c          # 0 bytes across the board
```

The scaffolding is not even committed: `apps/orchestrator/**` etc. appear in
`git status` as staged "new file" entries on `issue-fix`, and
`git log -- apps/orchestrator/src/vera_orch/graph/build.py` returns nothing.

### Where the real implementation lives (out of scope)

The working VERA codebase is under `backend/` (and `src/` for the frontend),
using a different, older architecture (`backend/core/ds_star_orchestrator.py`,
`backend/core/coder/coder_agent.py`, `backend/core/executor/code_executor.py`,
`backend/core/llm_client.py`, `backend/middleware/auth.py`, Supabase service,
etc.). See commits `71bcece` ("implement DS-STAR agent framework") and
`2d3d2f8` ("implement secure code execution engine"). The plan doc represents a
target re-architecture into `apps/*` + `packages/*` that has been laid out as
empty files only. `apps/api/**` (also in `git status` as new) is likewise
0 bytes; only `backend/` carries logic.

## Assessment against the review checklist

Nothing can be assessed because no code exists in scope:

| Area | Status |
| --- | --- |
| 1. Correctness (graph edge wiring vs plan 7.1, state mutation, async, semaphore, retry/CB) | N/A — `graph/build.py`, `graph/state.py`, all `graph/nodes/*.py`, `policies/*.py`, `workflows/*.py` are empty |
| 2. Sandbox security (AST scanner bypass, Docker/gVisor limits, network isolation, fake leakage) | N/A — `guards/ast_scanner.py`, `guards/resource_limits.py`, `backends/{local_docker,gvisor_pool,fake}.py`, `client.py`, `capture.py`, `mounts.py`, `image/seccomp.json`, `image/Dockerfile` all empty |
| 3. LLM gateway (thin pass-through, provider headers/cost, structured-output fallback, key logging) | N/A — `packages/llm/src/vera_llm/{client,routing,structured,resilience,caching,cost,fakes}.py` all empty |
| 4. Consistency with plan (missing nodes, tier resolution, cost/token accounting) | N/A |
| 5. Stubs / NotImplemented that silently misbehave | The entire tree is effectively this, but as empty modules they raise `ImportError` / define nothing — they will fail loudly at import, not silently misbehave |
| 6. Code quality | N/A |

## Observations on the scaffold itself (design-doc level, not bugs)

These are comments on the *plan* and the *layout*, since that is all that exists:

1. **Plan vs. scaffold node naming is consistent.** The `graph/nodes/` directory
   matches plan §7.1 exactly: `analyze, retrieve, plan, code, execute, debug,
   verify, route, truncate, finalize`. Good — when implemented, the 10-node
   DS-STAR graph is already carved out correctly.

2. **`apps/orchestrator` introduces a `activities/` + `workflows/` split**
   (`activities/{llm,sandbox,persistence,embeddings}.py`,
   `workflows/{precise_run,research_run,ingest,scheduled_analysis}.py`). This is
   Temporal-style vocabulary, whereas plan §11 says "in-process for now;
   Temporal later" and §7 describes a plain LangGraph compile. The scaffold is
   already reaching for the durable-workflow design. Fine as direction, but the
   plan should be updated to match, or the scaffold trimmed, so the intended
   execution model is unambiguous before implementation starts.

3. **`packages/sandbox` has both `local_docker.py` and `gvisor_pool.py`
   backends.** Plan §8 / §17 only mention `local_docker | fake`
   (`VERA_SANDBOX_BACKEND`). gVisor is a good hardening target but is currently
   unplanned surface area — decide whether it is in v1 scope.

4. **`packages/llm` lives at `packages/llm/src/vera_llm/`** but the plan (§5,
   §16) places it at `packages/adapters/llm/src/vera_llm/`. Similar drift for
   sandbox (`packages/sandbox` vs `packages/adapters/sandbox`), retrieval, and
   keyvault. The `.importlinter` file (also empty) is meant to enforce layering;
   the flattened `packages/*` layout loses the `adapters/` boundary the plan
   relies on for its port/adapter architecture. Reconcile the layout with the
   import-linter contracts before writing code, or the contracts will be written
   against the wrong module paths.

5. **`packages/llm` has no `providers.py` or `validation.py`** (plan §5.2, §5.5)
   in the scaffold — provider config (`PROVIDER_CONFIGS`) and
   `validate_connection` have nowhere to go. `routing.py` and `caching.py` exist
   but are not in the plan's file list (§16: `client, providers, structured,
   resilience, validation, cost, fakes`). Adding a routing layer risks the
   "thin pass-through" principle from §5 / the closing note — worth a design
   note on what `routing.py` is allowed to do (tier→assignment resolution only,
   not model fallback/translation).

6. **`tools/vera-cli`** vs plan's `apps/cli/src/vera_cli` (§16) — another path
   drift.

## Recommendation

There is no code-review deliverable here. Next step is implementation, starting
from Build Order slice 1 (§18: "Domain + ports + fakes"). Before that:

- Reconcile the physical layout (`packages/llm` vs `packages/adapters/llm`,
  `tools/vera-cli` vs `apps/cli`, extra `gvisor_pool`/`routing`/`caching`/
  `activities`/`workflows` modules) with `docs/VERA_BACKEND_PLAN.md` §16, and
  populate `.importlinter` so the port/adapter boundaries are enforced from
  commit one.
- Decide the execution model (plain in-process LangGraph per §7/§11 vs the
  Temporal activities/workflows split the scaffold implies) and update the plan.
- Re-request this review once `apps/orchestrator`, `packages/llm`, and
  `packages/sandbox` have real implementations.
