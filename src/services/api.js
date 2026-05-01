/**
 * api.js — Agentloop Backend Service Layer
 *
 * Wraps all FastAPI endpoints. The Vite dev proxy forwards
 * /api/* → http://localhost:8000/api/* so no hard-coded origin is needed.
 *
 * Auth interceptor: every exported function optionally accepts an
 * `accessToken` string. When provided it is stamped into the
 * Authorization: Bearer <token> header so the FastAPI auth middleware
 * can verify the Supabase JWT and inject the authenticated user_id.
 *
 * Gap 1 fix: all upload/process/clear calls accept and forward a sessionId
 * so the backend can scope files to the correct session-scoped cache bucket.
 */

const BASE = '/api'

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/**
 * Builds an Authorization header object when an access token is available.
 *
 * @param {string|null|undefined} accessToken
 * @returns {Record<string, string>}
 */
function authHeader(accessToken) {
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {}
}

/**
 * Thin GET/DELETE helper with auth support.
 *
 * @param {string}            url
 * @param {string|null}       accessToken
 * @param {'GET'|'DELETE'}    [method='GET']
 * @returns {Promise<Response>}
 */
async function _request(url, accessToken, method = 'GET') {
  return fetch(url, {
    method,
    headers: { ...authHeader(accessToken) },
  })
}

// ---------------------------------------------------------------------------
// Upload
// ---------------------------------------------------------------------------

/**
 * Uploads one or more File objects to /api/upload.
 *
 * @param {import('../types/index').FileEntry[]} files       - Array of file entry objects.
 * @param {(id: number, pct: number) => void}   onProgress  - Progress callback per file id.
 * @param {string}  [sessionId='']              - Session identifier for file cache scoping.
 * @param {string|null} [accessToken=null]      - JWT for Authorization header.
 * @returns {Promise<{ accepted_files: object[], rejected_files: object[] }>}
 */
export async function uploadFiles(files, onProgress, sessionId = '', accessToken = null) {
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

  const url = sessionId
    ? `${BASE}/upload?session_id=${encodeURIComponent(sessionId)}`
    : `${BASE}/upload`

  let data
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { ...authHeader(accessToken) },
      body: formData,
    })
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

// ---------------------------------------------------------------------------
// Process
// ---------------------------------------------------------------------------

/**
 * Calls /api/process with accepted filenames so the backend caches context.
 *
 * @param {string[]}    filenames         - Filenames successfully uploaded.
 * @param {string}      [sessionId='']    - Session identifier.
 * @param {string|null} [accessToken=null] - JWT for Authorization header.
 * @returns {Promise<object>}
 */
export async function processFiles(filenames, sessionId = '', accessToken = null) {
  const res = await fetch(`${BASE}/process`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeader(accessToken),
    },
    body: JSON.stringify({ files: filenames, session_id: sessionId || undefined }),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: `HTTP ${res.status}` }))
    throw new Error(err.message || `Process failed with status ${res.status}`)
  }

  return res.json()
}

// ---------------------------------------------------------------------------
// Clear cache
// ---------------------------------------------------------------------------

/**
 * Sends DELETE /api/clear to wipe the backend session-scoped file cache.
 *
 * @param {string}      [sessionId='']    - Session to wipe.
 * @param {string|null} [accessToken=null] - JWT for Authorization header.
 */
export async function clearBackendCache(sessionId = '', accessToken = null) {
  try {
    const url = sessionId
      ? `${BASE}/clear?session_id=${encodeURIComponent(sessionId)}`
      : `${BASE}/clear`
    const res = await _request(url, accessToken, 'DELETE')
    if (!res.ok) {
      console.warn(`Cache wipe failed with status ${res.status}`)
    }
  } catch (err) {
    console.error('Network error wiping cache:', err)
  }
}
