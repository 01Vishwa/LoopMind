/**
 * useQuery.js — Custom hook for query submission and result state.
 *
 * Encapsulates query status, output, and history management
 * extracted from App.jsx.
 */

import { useState, useCallback } from 'react'
import { toast } from '../components/shared/Toast'
import { runQuery } from '../services/api'

/**
 * Manages query state: submission, status lifecycle, output, and history.
 *
 * @param {Array} files - The current file list (used to gate queries).
 * @returns {{ status, output, queryHistory, handleSubmit }}
 */
export function useQuery(files) {
  const [status, setStatus] = useState('idle') // idle | processing | completed
  const [output, setOutput] = useState(null)
  const [queryHistory, setQueryHistory] = useState([])

  const handleSubmit = useCallback(
    async (query) => {
      if (files.filter((f) => f.progress === 100).length === 0) {
        toast('Please upload at least one file first', 'error')
        return
      }

      setStatus('processing')
      setOutput(null)
      setQueryHistory((prev) => [{ query, ts: Date.now() }, ...prev].slice(0, 10))

      try {
        const result = await runQuery(query)
        setOutput(result)
        setStatus('completed')
        toast('Analysis complete!', 'success')
      } catch (err) {
        toast(`Query failed: ${err.message}`, 'error')
        setStatus('idle')
      }
    },
    [files]
  )

  return { status, output, queryHistory, handleSubmit }
}
