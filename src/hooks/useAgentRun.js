/**
 * useAgentRun.js — Custom hook for DS-STAR live agent state.
 *
 * Manages the full live state of an agent run: phase, plan steps,
 * execution logs, generated code, streaming events, artifacts, and
 * historical run replay.
 */

import { useState, useCallback, useRef } from 'react'
import { toast } from '../components/shared/Toast'
import { createCancellableStream } from '../services/agentApi'
import { DEFAULT_SETTINGS } from '../components/agent/AgentSettings'

// Always use the Vite dev proxy path — never hardcode the backend port.
// This avoids CORS issues and matches the agentApi.js convention.
const API_BASE = '/api'

/**
 * Provides live DS-STAR agent state and a submit handler.
 *
 * @param {Array} files - Current file list (used to gate submissions).
 * @returns {Object} Agent state and control functions.
 */
export function useAgentRun(files) {
  const [agentStatus, setAgentStatus] = useState('idle')
  const [phase, setPhase] = useState('idle')
  const [planSteps, setPlanSteps] = useState([])
  const [currentCode, setCurrentCode] = useState('')
  const [executionLogs, setExecutionLogs] = useState([])
  const [currentRound, setCurrentRound] = useState(0)
  const [maxRounds, setMaxRounds] = useState(10)
  const [output, setOutput] = useState(null)
  const [verifierFeedback, setVerifierFeedback] = useState(null)
  const [artifacts, setArtifacts] = useState([])
  const [historyRuns, setHistoryRuns] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [settings, setSettings] = useState({ ...DEFAULT_SETTINGS })
  const [activeRunId, setActiveRunId] = useState(null)   // run_id from backend
  // Evaluation metrics (from 'metrics' SSE event)
  const [runMetrics, setRunMetrics] = useState(null)
  const [totalRunMs, setTotalRunMs] = useState(0)
  const [complexity, setComplexity] = useState('easy')
  const [showMetrics, setShowMetrics] = useState(false)
  
  // Deep Research mode state
  const [isResearchMode, setIsResearchMode] = useState(false)
  const [subQuestions, setSubQuestions] = useState([])
  const [researchReport, setResearchReport] = useState(null)
  
  const abortRef = useRef(false)
  const stepTimeoutsRef = useRef([])
  // Holds the { abort } handle returned by createCancellableStream.
  // Calling streamRef.current?.abort() stops the fetch AND signals the server.
  const streamRef = useRef(null)

  const addLog = useCallback((text, type = 'info') => {
    setExecutionLogs((prev) => [...prev, { text, type, ts: Date.now() }])
  }, [])

  // ── SSE event dispatcher ────────────────────────────────────────────────
  const handleAgentEvent = useCallback((event) => {
    if (abortRef.current) return
    const { event: type, payload } = event

    switch (type) {
      case 'run_started':
        // Backend confirmed run created — store the run_id for later
        setActiveRunId(payload?.run_id || null)
        break

      case 'report_started':
        // DS-STAR+ deep research run started — use report_id as the active run identifier
        setActiveRunId(payload?.report_id || null)
        break

      case 'analyzing':
        setPhase('analyzing')
        setAgentStatus('analyzing')
        addLog('[Analyzer] ' + payload.message, 'info')
        break

      case 'analysis_complete':
        addLog('[Analyzer] Data description ready.', 'success')
        break

      case 'planning':
        setPhase('planning')
        setAgentStatus('planning')
        addLog('[Planner] ' + payload.message, 'info')
        break

      case 'plan_ready':
        setPlanSteps(payload.steps || [])
        addLog(`[Planner] Plan created — ${(payload.steps || []).length} steps.`, 'success')
        break

      case 'round_start':
        setCurrentRound(payload.round)
        setMaxRounds(payload.max_rounds)
        addLog(`━━━ Round ${payload.round}/${payload.max_rounds} ━━━`, 'info')
        break

      case 'coding':
        setPhase('coding')
        setAgentStatus('coding')
        addLog('[Coder] ' + payload.message, 'info')
        break

      case 'code_ready':
        setCurrentCode(payload.code || '')
        addLog(`[Coder] Code generated (${(payload.code || '').length} chars).`, 'success')
        break

      case 'executing':
        setPhase('executing')
        setAgentStatus('executing')
        addLog('[Executor] Running generated script…', 'info')
        break

      case 'execution_result':
        if (payload.success) {
          addLog('[Executor] ✓ Execution succeeded.', 'success')
        } else {
          addLog('[Executor] ✗ Execution failed.', 'error')
        }
        if (payload.stdout) addLog(payload.stdout.trim(), 'success')
        if (payload.stderr) addLog('[stderr] ' + payload.stderr.trim(), 'error')

        // Store execution timing on the active step (usually currentRound - 1)
        if (payload.executor_ms) {
          setPlanSteps((prev) => {
            const copy = [...prev]
            if (copy[payload.round - 1]) {
              copy[payload.round - 1].exec_ms = payload.executor_ms
            }
            return copy
          })
        }
        break

      // ── Artifact pipeline (fix #4) ──────────────────────────────────────
      case 'artifact':
        setArtifacts((prev) => [...prev, {
          name: payload.name,
          data: payload.data,
          mime_type: payload.mime_type,
          round: payload.round,
        }])
        addLog(`[Executor] 📎 Artifact captured: ${payload.name}`, 'success')
        break

      case 'verifying':
        setPhase('verifying')
        setAgentStatus('verifying')
        addLog('[Verifier] Evaluating plan sufficiency…', 'info')
        break

      case 'verification_result':
        setVerifierFeedback({
          isSufficient: payload.is_sufficient,
          reason: payload.reason,
          confidence: payload.confidence,
        })
        if (payload.is_sufficient) {
          addLog('[Verifier] ✓ Plan is sufficient!', 'success')
        } else {
          addLog(`[Verifier] ✗ Insufficient — ${payload.reason}`, 'warn')
        }
        // Store verifier timing
        if (payload.verifier_ms) {
          setPlanSteps((prev) => {
            const copy = [...prev]
            if (copy[payload.round - 1]) {
              copy[payload.round - 1].verifier_ms = payload.verifier_ms
            }
            return copy
          })
        }
        break

      case 'routing':
        setPhase('routing')
        setAgentStatus('routing')
        addLog('[Router] Deciding how to refine the plan…', 'info')
        break

      case 'plan_updated':
        setPlanSteps(payload.steps || [])
        addLog(`[Router] Plan updated (${payload.action}) — ${(payload.steps || []).length} steps.`, 'warn')
        break

      case 'debugging':
        setPhase('debugging')
        setAgentStatus('debugging')
        addLog(`[Debugger] ${payload.message}`, 'warn')
        break

      case 'debug_applied':
        addLog(`[Debugger] ✓ ${payload.message}`, 'success')
        break

      case 'finalizing':
        setPhase('finalizing')
        setAgentStatus('finalizing')
        addLog('[Finalizer] ' + payload.message, 'info')
        break

      case 'finalized':
        addLog('[Finalizer] ✓ ' + payload.message, 'success')
        break

      // ── Deep Research Events ──
      case 'research_started':
        setIsResearchMode(true)
        setPhase('analyzing')
        setAgentStatus('researching')
        addLog('[DeepResearch] ' + payload.message, 'info')
        break

      case 'retrieval_complete':
        addLog('[Retriever] ' + payload.message, 'info')
        break

      case 'generating_subquestions':
        setPhase('generating_subquestions')
        setAgentStatus('researching')
        addLog('[Decomposer] ' + payload.message, 'info')
        break

      case 'subquestions_ready':
        setSubQuestions((payload.sub_questions || []).map(q => ({
          question: q,
          status: 'pending'
        })))
        addLog(`[Decomposer] ✓ ${payload.message}`, 'success')
        break

      case 'running_subquestions':
        setPhase('running_subquestions')
        setAgentStatus('researching')
        addLog('[Parallel] ' + payload.message, 'info')
        break

      case 'subquestion_started':
        setSubQuestions(prev => prev.map((q, i) => i === payload.index ? { ...q, status: 'running' } : q))
        addLog(payload.message, 'info')
        break

      case 'subquestion_complete':
        setSubQuestions(prev => prev.map((q, i) => i === payload.index ? { ...q, status: payload.status } : q))
        addLog(payload.message, payload.status === 'completed' ? 'success' : 'warn')
        break

      case 'all_subquestions_complete':
        addLog('[Parallel] ✓ ' + payload.message, 'success')
        break

      case 'writing_report':
        setPhase('writing_report')
        setAgentStatus('researching')
        addLog('[ReportWriter] ' + payload.message, 'info')
        break

      case 'research_complete':
        setPhase('completed')
        setAgentStatus('completed')
        setResearchReport({
          title: payload.title,
          executive_summary: payload.executive_summary,
          report_body: payload.report_body,
          key_findings: payload.key_findings || [],
          caveats: payload.caveats || [],
          total_ms: payload.total_ms || 0
        })
        addLog('[DeepResearch] ✓ ' + payload.message, 'success')
        toast('Deep Research complete!', 'success')
        setTimeout(() => fetchHistory(), 1500)
        break

      case 'retrying':
        addLog(
          `[⟳] ${payload.agent} — attempt ${payload.attempt} retrying…`,
          'warn',
        )
        break

      case 'completed':
        setPhase('completed')
        setAgentStatus('completed')
        setOutput({
          insights: payload.insights,
          code: payload.code,
          plan_steps: payload.plan_steps,
          rounds: payload.rounds,
          execution_logs: payload.execution_logs,
        })
        
        if (payload.plan_steps) {
          const isVerified = payload.insights?.bullets?.some(b => b.includes('✓ Approved'));
          setPlanSteps(payload.plan_steps);
          
          if (isVerified) {
            payload.plan_steps.forEach((step, index) => {
              const tid = setTimeout(() => {
                if (abortRef.current) return;
                setPlanSteps((prev) => {
                  const updated = [...prev];
                  if (updated[index]) {
                    updated[index] = { ...updated[index], status: 'done' };
                  }
                  return updated;
                });
              }, (index + 1) * 300);
              stepTimeoutsRef.current.push(tid);
            });
          }
        }
        
        addLog(`[DS-STAR] ✓ Completed in ${payload.rounds} round(s).`, 'success')
        toast('DS-STAR analysis complete!', 'success')
        // Auto-refresh history so the new run appears immediately
        setTimeout(() => fetchHistory(), 1500)
        break

      // ── Evaluation metrics (new) ────────────────────────────────────────
      case 'metrics':
        setRunMetrics(payload.metrics || null)
        setTotalRunMs(payload.total_run_ms || 0)
        setComplexity(payload.complexity || 'easy')
        setShowMetrics(true)
        addLog(
          `[Metrics] Task complexity: ${payload.complexity || 'easy'} · Total: ${Math.round((payload.total_run_ms || 0) / 1000)}s`,
          'info',
        )
        break

      case 'warning':
        addLog('[⚠] ' + payload.message, 'warn')
        break

      case 'error':
        setPhase('error')
        setAgentStatus('failed')
        addLog('[✗] ' + payload.message, 'error')
        toast(`Agent error: ${payload.message}`, 'error')
        // Refresh history so failed run shows with correct badge
        setTimeout(() => fetchHistory(), 1500)
        break

      case 'stream_end':
        if (agentStatus !== 'completed') {
          setAgentStatus((s) => (s === 'failed' ? s : 'completed'))
        }
        break

      default:
        break
    }
  }, [addLog, agentStatus])

  // ── Submit handler ──────────────────────────────────────────────────────
  const handleSubmit = useCallback(
    async (query, sessionId = '') => {
      const uploadedFiles = files.filter((f) => f.progress === 100)
      if (uploadedFiles.length === 0) {
        toast('Please upload at least one file first', 'error')
        return
      }

      stepTimeoutsRef.current.forEach(clearTimeout)
      stepTimeoutsRef.current = []

      abortRef.current = false
      setAgentStatus('analyzing')
      setPhase('analyzing')
      setPlanSteps([])
      setCurrentCode('')
      setExecutionLogs([])
      setArtifacts([])
      setCurrentRound(0)
      setOutput(null)
      setVerifierFeedback(null)
      setActiveRunId(null)  // clear previous run_id
      setIsResearchMode(false)
      setSubQuestions([])
      setResearchReport(null)

      addLog(`[DS-STAR] Starting run for query: "${query}"`, 'info')

      // Cancel any in-flight stream before starting a new one
      streamRef.current?.abort()

      const { promise, abort } = createCancellableStream(
        query,
        handleAgentEvent,
        sessionId,
        settings,
      )
      streamRef.current = { abort }

      try {
        await promise
      } catch (err) {
        if (err?.name === 'AbortError') return   // user cancelled — not an error
        setAgentStatus('failed')
        setPhase('error')
        addLog('[✗] Stream error: ' + err.message, 'error')
        toast(`Agent failed: ${err.message}`, 'error')
      }
    },
    // 'settings' and 'sessionId' MUST be in deps to avoid stale closures.
    [files, settings, handleAgentEvent, addLog],
  )

  // ── Reset handler ───────────────────────────────────────────────────────
  const handleReset = useCallback(() => {
    stepTimeoutsRef.current.forEach(clearTimeout)
    stepTimeoutsRef.current = []

    // Abort the in-flight SSE stream — this signals AbortController.abort(),
    // which closes the fetch AND triggers the server's is_disconnected() check.
    streamRef.current?.abort()
    streamRef.current = null

    abortRef.current = true
    setAgentStatus('idle')
    setPhase('idle')
    setPlanSteps([])
    setCurrentCode('')
    setExecutionLogs([])
    setArtifacts([])
    setCurrentRound(0)
    setOutput(null)
    setVerifierFeedback(null)
    setRunMetrics(null)
    setTotalRunMs(0)
    setComplexity('easy')
    setShowMetrics(false)
    setIsResearchMode(false)
    setSubQuestions([])
    setResearchReport(null)
  }, [])

  // ── History: fetch run list (fix #6) ────────────────────────────────────
  const fetchHistory = useCallback(async (limit = 20) => {
    setHistoryLoading(true)
    try {
      const res = await fetch(`${API_BASE}/agent/runs?limit=${limit}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setHistoryRuns(data)
    } catch (err) {
      toast('Could not load history: ' + err.message, 'error')
    } finally {
      setHistoryLoading(false)
    }
  }, [])

  // ── History: restore a past run (fix #6) ────────────────────────────────
  const loadRun = useCallback(async (runId) => {
    try {
      const res = await fetch(`${API_BASE}/agent/runs/${runId}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const run = await res.json()

      abortRef.current = true      // halt any live stream
      setAgentStatus('completed')
      setPhase('completed')
      setPlanSteps(run.plan_steps || [])
      setCurrentCode(run.final_code || '')
      setExecutionLogs(
        (run.execution_logs || []).map((t) => ({ text: t, type: 'info', ts: 0 })),
      )
      setCurrentRound(run.rounds || 0)
      setArtifacts([])             // artifacts not stored in Supabase yet
      setOutput({
        insights: run.insights || {},
        code: { Python: run.final_code || '' },
        plan_steps: run.plan_steps || [],
        rounds: run.rounds || 0,
        execution_logs: run.execution_logs || [],
      })
      setVerifierFeedback(null)
      setIsResearchMode(false)
      setSubQuestions([])
      setResearchReport(null)
      toast(`Loaded run: "${(run.query || '').slice(0, 50)}…"`, 'success')
    } catch (err) {
      toast('Could not load run: ' + err.message, 'error')
    }
  }, [])

  return {
    agentStatus,
    phase,
    planSteps,
    currentCode,
    executionLogs,
    currentRound,
    maxRounds,
    output,
    verifierFeedback,
    artifacts,
    historyRuns,
    historyLoading,
    activeRunId,
    settings,
    setSettings,
    handleSubmit,
    handleReset,
    fetchHistory,
    loadRun,
    // Evaluation metrics
    runMetrics,
    totalRunMs,
    complexity,
    showMetrics,
    // Deep Research state
    isResearchMode,
    subQuestions,
    researchReport,
  }
}
