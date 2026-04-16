/**
 * api.js — LoopMind Backend Service Layer
 *
 * Wraps all FastAPI endpoints. The Vite dev proxy forwards /api/* → http://localhost:8000/api/*
 * so no hard-coded origin is needed here.
 *
 * NOTE: Agent runs use Server-Sent Events over POST /api/agent/run, not this module.
 * SSE streaming is handled by the useAgentStream hook which manages the EventSource
 * connection directly. The former runQuery() has been removed — it called /api/query
 * which does not exist in the backend router.
 */


const BASE = '/api'

/**
 * Uploads one or more File objects to the backend /api/upload endpoint.
 *
 * @param {File[]} files - Array of raw File objects to upload.
 * @param {(id: number, pct: number) => void} onProgress - Progress callback per file id.
 * @returns {Promise<{ accepted_files: object[], rejected_files: object[] }>}
 */
export async function uploadFiles(files, onProgress) {
  const formData = new FormData()
  files.forEach((file) => formData.append('files', file._raw, file.name))

  // Simulate incremental progress while the real upload is in-flight
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
    // Clear all intervals and drive progress to 100 (accepted) or leave at 0 (rejected)
    progressIntervals.forEach(({ id, interval }) => {
      clearInterval(interval)
      const rejected = data?.rejected_files?.some((f) => {
        // Match by original name — FormData keys use file.name
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
