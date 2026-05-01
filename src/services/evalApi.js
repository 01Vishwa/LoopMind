/**
 * evalApi.js — Eval Dashboard API client
 *
 * All requests proxy through the Vite dev server to /api/eval/*
 * Auth interceptor: every call accepts an optional accessToken and
 * stamps it as Authorization: Bearer <token>.
 */

const BASE = '/api/eval'

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/**
 * @param {string|null|undefined} token
 * @returns {Record<string, string>}
 */
function authHeader(token) {
  return token ? { Authorization: `Bearer ${token}` } : {}
}

/**
 * @param {string}      path
 * @param {string|null} [accessToken=null]
 * @returns {Promise<unknown>}
 */
async function _get(path, accessToken = null) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { ...authHeader(accessToken) },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
    throw new Error(err.detail || `Request failed: ${res.status}`)
  }
  return res.json()
}

// ---------------------------------------------------------------------------
// Eval endpoints (eval dashboard is intentionally public — no auth guard)
// ---------------------------------------------------------------------------

/** System-level KPIs: total_runs, success_rate, avg_latency_ms, avg_retries */
export async function getOverview(accessToken = null) {
  return _get('/overview', accessToken)
}

/** Per-agent stats: avg_latency_ms, failure_rate, total_calls */
export async function getAgentPerformance(accessToken = null) {
  return _get('/agents', accessToken)
}

/** Debug loop stats: avg_debug_depth, error_type_distribution, retry_success_ratio */
export async function getDebugLoopStats(accessToken = null) {
  return _get('/debug-loop', accessToken)
}

/**
 * Paginated run list with metrics.
 *
 * @param {{ limit?: number, difficulty?: string, mode?: string }} [params={}]
 * @param {string|null} [accessToken=null]
 */
export async function listEvalRuns(params = {}, accessToken = null) {
  const qs = new URLSearchParams()
  if (params.limit)      qs.set('limit', params.limit)
  if (params.difficulty) qs.set('difficulty', params.difficulty)
  if (params.mode)       qs.set('mode', params.mode)
  const query = qs.toString() ? `?${qs}` : ''
  return _get(`/runs${query}`, accessToken)
}

/**
 * Step-by-step trace for one run.
 *
 * @param {string}      runId
 * @param {string|null} [accessToken=null]
 */
export async function getRunTrace(runId, accessToken = null) {
  return _get(`/runs/${runId}/trace`, accessToken)
}
