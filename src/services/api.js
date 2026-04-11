/**
 * api.js — LoopMind Backend Service Layer
 *
 * Wraps all FastAPI endpoints. The Vite dev proxy forwards /api/* → http://localhost:8000/api/*
 * so no hard-coded origin is needed here.
 *
 * Gap 1 fix: All upload/process/clear calls now accept and forward a sessionId so
 * the backend can scope files to the correct session-scoped cache bucket.
 */

const BASE = '/api'

/**
 * Uploads one or more File objects to the backend /api/upload endpoint.
 *
 * @param {Array}    files       - Array of file entry objects (with _raw File and id).
 * @param {Function} onProgress  - Progress callback per file id.
 * @param {string}   [sessionId] - Session identifier for file cache scoping.
 * @returns {Promise<{ accepted_files: object[], rejected_files: object[] }>}
 */
export async function uploadFiles(files, onProgress, sessionId = '') {
  const formData = new FormData()
  files.forEach((file) => formData.append('files', file._raw, file.name))

  const progressIntervals = files.map((file) => {
    let pct = 0
    const interval = setInterval(() => {
      pct = Math.min(pct + 10, 90)
      onProgress(file.id, pct)
    }, 150)
    return { id: file.id, interval }
  })

  // Append session_id as a query param so the backend stores files in the
  // correct session bucket (two-level _FILE_CACHE fix for Gap 1).
  const url = sessionId
    ? `${BASE}/upload?session_id=${encodeURIComponent(sessionId)}`
    : `${BASE}/upload`

  let data
  try {
    const res = await fetch(url, { method: 'POST', body: formData })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ message: `HTTP ${res.status}` }))
      throw new Error(err.message || `Upload failed with status ${res.status}`)
    }
    data = await res.json()
  } finally {
    progressIntervals.forEach(({ id, interval }) => {
      clearInterval(interval)
      const rejected = data?.rejected_files?.some((f) => {
        const entry = files.find((f2) => f2.id === id)
        return entry && f.filename === entry.name
      })
      onProgress(id, rejected ? -1 : 100)
    })
  }

  return data
}

/**
 * Calls /api/process with the accepted filenames so the backend caches document context.
 *
 * @param {string[]} filenames  - List of filenames that were successfully uploaded.
 * @param {string}   [sessionId] - Session identifier for file cache scoping.
 * @returns {Promise<object>} Raw process response.
 */
export async function processFiles(filenames, sessionId = '') {
  const res = await fetch(`${BASE}/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ files: filenames, session_id: sessionId || undefined }),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: `HTTP ${res.status}` }))
    throw new Error(err.message || `Process failed with status ${res.status}`)
  }

  return res.json()
}

/**
 * Sends a DELETE request to /api/clear to wipe the backend's session-scoped
 * file cache and processing context, preventing memory leaks.
 *
 * @param {string} [sessionId] - Session to wipe. Only that session's data is removed.
 */
export async function clearBackendCache(sessionId = '') {
  try {
    const url = sessionId
      ? `${BASE}/clear?session_id=${encodeURIComponent(sessionId)}`
      : `${BASE}/clear`
    const res = await fetch(url, { method: 'DELETE' })
    if (!res.ok) {
      console.warn(`Cache wipe failed with status ${res.status}`)
    }
  } catch (err) {
    console.error('Network error wiping cache:', err)
  }
}
