/**
 * agentApi.js — DS-STAR Agent SSE Client
 *
 * Opens a streaming POST to /api/agent/run and dispatches each parsed
 * AgentEvent to the provided callback.
 *
 * Gap fixes applied:
 * - AbortController support: callers can cancel a run mid-stream.
 * - Stream hang protection: a configurable idle timeout aborts the stream
 *   if no data arrives for more than `idleTimeoutMs` milliseconds.
 * - Returns the AbortController so callers can cancel on unmount.
 */

const BASE = '/api'

/**
 * Runs the DS-STAR agent and streams events in real time.
 *
 * @param {string}   query          - The user's natural language query.
 * @param {function} onEvent        - Callback invoked for every AgentEvent.
 * @param {string}   [sessionId]    - Optional session identifier.
 * @param {object}   [settings]     - Per-run agent settings.
 * @param {AbortSignal} [signal]    - Optional AbortSignal for cancellation.
 * @param {number}   [idleTimeoutMs] - Max ms to wait for next chunk (default 60s).
 * @returns {Promise<void>}          Resolves when the stream ends or is aborted.
 */
export async function runAgentStream(
  query,
  onEvent,
  sessionId = '',
  settings = {},
  signal = null,
  idleTimeoutMs = 60_000,
) {
  const body = {
    query,
    session_id: sessionId,
    max_rounds:   settings.maxRounds   ?? undefined,
    model:        settings.model       ?? undefined,
    coder_model:  settings.coderModel  ?? undefined,
    temperature:  settings.temperature ?? undefined,
  }

  const res = await fetch(`${BASE}/agent/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,   // allows AbortController.abort() to cancel the fetch
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

      // SSE lines are separated by double newlines
      const lines = buffer.split('\n\n')
      buffer = lines.pop() // keep any incomplete chunk

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
          // Ignore non-JSON lines (keep-alive lines, etc.)
        }
      }
    }
  } finally {
    clearTimeout(idleTimer)
  }
}

/**
 * Creates a cancellable agent stream wrapper.
 *
 * Returns both the stream promise and an `abort()` function so callers
 * (e.g. React useEffect cleanup) can stop the stream on unmount.
 *
 * @param {string}   query       - Natural language query.
 * @param {function} onEvent     - Event callback.
 * @param {string}   [sessionId] - Session ID.
 * @param {object}   [settings]  - Agent settings.
 * @returns {{ promise: Promise<void>, abort: function }}
 */
export function createCancellableStream(query, onEvent, sessionId = '', settings = {}) {
  const controller = new AbortController()

  const promise = runAgentStream(
    query,
    onEvent,
    sessionId,
    settings,
    controller.signal,
  ).catch(err => {
    // Suppress abort errors — these are expected on user cancellation
    if (err.name === 'AbortError') return
    throw err
  })

  return {
    promise,
    abort: () => controller.abort(),
  }
}
