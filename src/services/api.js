/**
 * api.js — Semantica Backend Service Layer
 *
 * Wraps all FastAPI endpoints. The Vite dev proxy forwards /api/* → http://localhost:8000/api/*
 * so no hard-coded origin is needed here.
 */

const BASE = '/api'

/**
 * Uploads one or more File objects to the backend /api/upload endpoint.
 *
 * @param {Array} files - Array of file entry objects (with _raw File and id).
 * @param {(id: number, pct: number) => void} onProgress - Progress callback per file id.
 * @returns {Promise<{ accepted_files: object[], rejected_files: object[] }>}
 */
export async function uploadFiles(files, onProgress) {
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

  let data
  try {
    const res = await fetch(`${BASE}/upload`, { method: 'POST', body: formData })
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
 * @param {string[]} filenames - List of filenames that were successfully uploaded.
 * @returns {Promise<object>} Raw process response.
 */
export async function processFiles(filenames) {
  const res = await fetch(`${BASE}/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ files: filenames }),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: `HTTP ${res.status}` }))
    throw new Error(err.message || `Process failed with status ${res.status}`)
  }

  return res.json()
}

/**
 * Sends a natural language query to /api/query.
 *
 * @param {string} query - The user's query string.
 * @returns {Promise<{ insights: { summary: string, bullets: string[] }, code: object }>}
 */
export async function runQuery(query) {
  const res = await fetch(`${BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: `HTTP ${res.status}` }))
    throw new Error(err.message || `Query failed with status ${res.status}`)
  }

  return res.json()
}

/**
 * Sends a DELETE request to /api/clear to wipe the backend's in-memory byte cache
 * and processing contexts preventing memory leaks.
 */
export async function clearBackendCache() {
  try {
    const res = await fetch(`${BASE}/clear`, { method: 'DELETE' })
    if (!res.ok) {
      console.warn(`Cache wipe failed with status ${res.status}`)
    }
  } catch (err) {
    console.error("Network error wiping cache:", err)
  }
}
