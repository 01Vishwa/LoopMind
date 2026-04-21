/**
 * evalApi.js — Eval Dashboard API client
 * All requests proxy through the Vite dev server to /api/eval/*
 */

const BASE = '/api/eval'

async function _get(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
    throw new Error(err.detail || `Request failed: ${res.status}`)
  }
  return res.json()
}

/** System-level KPIs: total_runs, success_rate, avg_latency_ms, avg_retries */
export async function getOverview() {
  return _get('/overview')
}

/** Per-agent stats: avg_latency_ms, failure_rate, total_calls */
export async function getAgentPerformance() {
  return _get('/agents')
}

/** Debug loop stats: avg_debug_depth, error_type_distribution, retry_success_ratio */
export async function getDebugLoopStats() {
  return _get('/debug-loop')
}

/**
 * Paginated run list with metrics.
 * @param {{ limit?: number, difficulty?: string, mode?: string }} params
 */
export async function listEvalRuns(params = {}) {
  const qs = new URLSearchParams()
  if (params.limit)     qs.set('limit', params.limit)
  if (params.difficulty) qs.set('difficulty', params.difficulty)
  if (params.mode)      qs.set('mode', params.mode)
  const query = qs.toString() ? `?${qs}` : ''
  return _get(`/runs${query}`)
}

/**
 * Step-by-step trace for one run.
 * @param {string} runId
 */
export async function getRunTrace(runId) {
  return _get(`/runs/${runId}/trace`)
}
