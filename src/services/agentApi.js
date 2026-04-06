/**
 * agentApi.js — DS-STAR Agent SSE Client
 *
 * Opens a Server-Sent Events stream to /api/agent/run and dispatches
 * each parsed AgentEvent to the provided callback.
 */

const BASE = '/api'

/**
 * Runs the DS-STAR agent and streams events in real time.
 *
 * @param {string} query - The user's natural language query.
 * @param {function} onEvent - Callback invoked for every AgentEvent received.
 * @param {string} [sessionId] - Optional session identifier.
 * @returns {Promise<void>} Resolves when the stream ends.
 */
export async function runAgentStream(query, onEvent, sessionId = '', settings = {}) {
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
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: `HTTP ${res.status}` }))
    throw new Error(err.message || `Agent run failed with status ${res.status}`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

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
        // Ignore non-JSON lines
      }
    }
  }
}
