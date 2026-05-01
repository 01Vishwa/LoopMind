/**
 * agentApi.js — DS-STAR Agent SSE Client
 *
 * Opens a streaming POST to /api/agent/run and dispatches each parsed
 * AgentEvent to the provided callback.
 *
 * Auth interceptor: `runAgentStream` accepts an optional `accessToken`
 * which is stamped into the Authorization: Bearer header so the FastAPI
 * auth middleware can verify the Supabase JWT.
 *
 * Gap fixes:
 * - AbortController support: callers can cancel a run mid-stream.
 * - Stream hang protection: configurable idle timeout aborts the stream
 *   if no data arrives for more than `idleTimeoutMs` milliseconds.
 * - Returns the AbortController so callers can cancel on unmount.
 */

const BASE = '/api'

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/**
 * Builds an Authorization header when a token is present.
 *
 * @param {string|null|undefined} token
 * @returns {Record<string, string>}
 */
function authHeader(token) {
  return token ? { Authorization: `Bearer ${token}` } : {}
}

// ---------------------------------------------------------------------------
// runAgentStream
// ---------------------------------------------------------------------------

/**
 * Runs the DS-STAR agent and streams SSE events in real time.
 *
 * @param {string}      query           - User's natural language query.
 * @param {Function}    onEvent         - Callback invoked for every AgentEvent.
 * @param {string}      [sessionId='']  - Optional session identifier.
 * @param {object}      [settings={}]   - Per-run agent settings.
 * @param {AbortSignal} [signal=null]   - Optional AbortSignal for cancellation.
 * @param {number}      [idleTimeoutMs=60000] - Max ms to wait between chunks.
 * @param {string|null} [accessToken=null]    - JWT for Authorization header.
 * @returns {Promise<void>}  Resolves when the stream ends or is aborted.
 */
export async function runAgentStream(
  query,
  onEvent,
  sessionId = '',
  settings = {},
  signal = null,
  idleTimeoutMs = 60_000,
  accessToken = null,
  workspaceId = null,
) {
  const body = {
    query,
    session_id: sessionId,
    max_rounds:  settings.maxRounds   ?? undefined,
    model:       settings.model       ?? undefined,
    coder_model: settings.coderModel  ?? undefined,
    temperature: settings.temperature ?? undefined,
    workspace_id: workspaceId         ?? undefined,
  }

  const res = await fetch(`${BASE}/agent/run`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeader(accessToken),
    },
    body: JSON.stringify(body),
    signal,   // AbortController.abort() cancels the fetch
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: `HTTP ${res.status}` }))
    throw new Error(err.message || `Agent run failed with status ${res.status}`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  // Idle timeout: abort if no data arrives for idleTimeoutMs
  let idleTimer = null
  const resetIdleTimer = () => {
    clearTimeout(idleTimer)
    idleTimer = setTimeout(() => {
      reader.cancel('SSE idle timeout exceeded')
    }, idleTimeoutMs)
  }

  try {
    resetIdleTimer()

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      resetIdleTimer()
      buffer += decoder.decode(value, { stream: true })

      // SSE events are separated by double newlines
      const lines = buffer.split('\n\n')
      buffer = lines.pop() // keep any incomplete trailing chunk

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed.startsWith('data:')) continue

        const jsonStr = trimmed.slice(5).trim()
        if (!jsonStr) continue

        try {
          const event = JSON.parse(jsonStr)
          onEvent(event)
          if (event.event === 'stream_end') return
        } catch {
          // Ignore keep-alive or non-JSON lines
        }
      }
    }
  } finally {
    clearTimeout(idleTimer)
  }
}

// ---------------------------------------------------------------------------
// createCancellableStream
// ---------------------------------------------------------------------------

/**
 * Cancellable wrapper around runAgentStream.
 *
 * @param {string}      query          - Natural language query.
 * @param {Function}    onEvent        - Event callback.
 * @param {string}      [sessionId=''] - Session ID.
 * @param {object}      [settings={}]  - Agent settings.
 * @param {string|null} [accessToken=null] - JWT access token.
 * @param {string|null} [workspaceId=null] - Workspace ID.
 * @returns {{ promise: Promise<void>, abort: Function }}
 */
export function createCancellableStream(
  query,
  onEvent,
  sessionId = '',
  settings = {},
  accessToken = null,
  workspaceId = null,
) {
  const controller = new AbortController()

  const promise = runAgentStream(
    query,
    onEvent,
    sessionId,
    settings,
    controller.signal,
    60_000,
    accessToken,
    workspaceId,
  ).catch((err) => {
    // Suppress abort errors — expected on user cancellation
    if (err.name === 'AbortError') return
    throw err
  })

  return {
    promise,
    abort: () => controller.abort(),
  }
}
