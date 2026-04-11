/**
 * useFileUpload.js — Custom hook for file upload orchestration.
 *
 * Encapsulates all file state, upload flow, progress tracking,
 * and duplicate handling — extracted from App.jsx.
 */

import { useState, useCallback, useRef } from 'react'
import { toast } from '../components/shared/Toast'
import { uploadFiles, processFiles, clearBackendCache } from '../services/api'

let fileIdCounter = 0

/**
 * Generates a stable session ID for this browser tab.
 * Uses crypto.randomUUID when available (all modern browsers), falls back
 * to a random hex string for older environments.
 *
 * @returns {string} A UUID-like identifier string.
 */
const _generateSessionId = () =>
  typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2) + Math.random().toString(36).slice(2)

/**
 * Manages the full file lifecycle: adding, uploading, replacing duplicates, removing.
 *
 * Generates a stable session ID per component mount so uploaded files are
 * stored in an isolated cache bucket on the backend (Gap 1 fix).
 *
 * @returns {{ files, pendingDuplicates, sessionId, handleAddFiles, handleConfirmDuplicates, handleRemoveFile, handleClearAll }}
 */
export function useFileUpload() {
  const [files, setFiles] = useState([])
  const [pendingDuplicates, setPendingDuplicates] = useState([])

  // Stable session ID for this component mount — generated once, never changes.
  // Stored in a ref so it survives re-renders without triggering extra effects.
  const sessionIdRef = useRef(_generateSessionId())
  const sessionId = sessionIdRef.current

  // Update progress for a single file by id
  const applyProgress = useCallback((id, pct) => {
    setFiles((prev) =>
      prev.map((f) => (f.id === id ? { ...f, progress: pct < 0 ? 0 : pct } : f))
    )
  }, [])

  // Upload batch to backend then trigger /process for accepted files
  const startUploads = useCallback(
    async (entriesToUpload) => {
      let uploadResult
      try {
        uploadResult = await uploadFiles(entriesToUpload, applyProgress, sessionId)
      } catch (err) {
        toast(`Upload error: ${err.message}`, 'error')
        entriesToUpload.forEach((e) => applyProgress(e.id, 0))
        return
      }

      if (uploadResult.rejected_files?.length > 0) {
        uploadResult.rejected_files.forEach((r) =>
          toast(`Rejected "${r.filename}": ${r.reason}`, 'error')
        )
      }

      const acceptedNames = uploadResult.accepted_files.map((f) => f.filename)
      if (acceptedNames.length > 0) {
        try {
          await processFiles(acceptedNames, sessionId)
          toast(
            `${acceptedNames.length} file${acceptedNames.length > 1 ? 's' : ''} uploaded successfully`,
            'success'
          )
        } catch (err) {
          toast(`Processing error: ${err.message}`, 'error')
        }
      }
    },
    [applyProgress]
  )

  const handleAddFiles = useCallback(
    async (newFiles) => {
      const entries = newFiles.map((f) => ({
        id: ++fileIdCounter,
        name: f.name,
        size: f.size,
        progress: 0,
        _raw: f,
      }))

      const existingNames = files.map((f) => f.name)
      const unique = entries.filter((e) => !existingNames.includes(e.name))
      const duplicates = entries.filter((e) => existingNames.includes(e.name))

      if (unique.length > 0) {
        toast(`${unique.length} file${unique.length > 1 ? 's' : ''} added`, 'success')
        setFiles((prev) => [...prev, ...unique])
        startUploads(unique)
      }

      if (duplicates.length > 0) {
        setPendingDuplicates(duplicates)
      } else if (unique.length === 0) {
        toast('Files already uploaded', 'info')
      }
    },
    [files, startUploads]
  )

  const handleConfirmDuplicates = useCallback(() => {
    if (pendingDuplicates.length > 0) {
      toast(
        `${pendingDuplicates.length} file${pendingDuplicates.length > 1 ? 's' : ''} replaced`,
        'success'
      )
      setFiles((prev) => {
        const dupNames = pendingDuplicates.map((d) => d.name)
        return [...prev.filter((f) => !dupNames.includes(f.name)), ...pendingDuplicates]
      })
      startUploads(pendingDuplicates)
      setPendingDuplicates([])
    }
  }, [pendingDuplicates, startUploads])

  const handleRemoveFile = useCallback(
    (id) => {
      const file = files.find((f) => f.id === id)
      if (file) {
        toast(`Removed "${file.name}"`, 'error')
        setFiles((prev) => prev.filter((f) => f.id !== id))
      }
    },
    [files]
  )

  const handleClearAll = useCallback(async () => {
    if (files.length > 0) {
      toast('All files cleared', 'info')
      setFiles([])
      await clearBackendCache(sessionId)
    }
  }, [files, sessionId])

  return {
    files,
    pendingDuplicates,
    sessionId,           // expose so useAgentRun can pass it to the backend
    handleAddFiles,
    handleConfirmDuplicates,
    handleRemoveFile,
    handleClearAll,
  }
}
