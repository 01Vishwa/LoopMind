/**
 * AgentMetricsOverlay.jsx
 *
 * Developer/audit diagnostic panel that aggregates evaluation quality metrics
 * across DS-STAR agent runs. Surfaces the same convergence data used in the
 * paper's ablation studies (easy vs. hard task round distribution).
 *
 * Props:
 *  - metrics: RunMetrics summary dict from the "metrics" SSE event payload.
 *  - totalRunMs: number — wall-clock ms for the full run.
 *  - complexity: "easy" | "hard"
 *  - rounds: number — rounds completed.
 *  - isVisible: boolean — controlled by parent (e.g. a hotkey or dev toggle).
 */

import React, { useState } from 'react'
import {
  BarChart2, Zap, Clock, ChevronDown, ChevronUp,
  Activity, GitMerge, CheckCircle2, XCircle,
} from 'lucide-react'

// ─── helpers ─────────────────────────────────────────────────────────────────

function ms(val) {
  if (!val || val <= 0) return '—'
  if (val < 1000) return `${val}ms`
  return `${(val / 1000).toFixed(1)}s`
}

function pct(part, total) {
  if (!total || total <= 0) return '0%'
  return `${Math.round((part / total) * 100)}%`
}

// ─── Stage bar ────────────────────────────────────────────────────────────────
function StageBar({ label, value, total, color }) {
  const width = total > 0 ? Math.max(2, Math.round((value / total) * 100)) : 0
  return (
    <div className="flex items-center gap-3">
      <span className="text-[11px] text-slate-500 font-medium w-16 shrink-0">{label}</span>
      <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${width}%` }}
        />
      </div>
      <span className="text-[11px] font-mono text-slate-600 w-14 text-right shrink-0">
        {ms(value)} <span className="text-slate-400 text-[10px]">{pct(value, total)}</span>
      </span>
    </div>
  )
}

// ─── Round row ────────────────────────────────────────────────────────────────
function RoundRow({ round }) {
  return (
    <div className={`p-3 rounded-xl border text-[12px] ${
      round.is_sufficient
        ? 'bg-emerald-50 border-emerald-100'
        : 'bg-slate-50 border-slate-100'
    }`}>
      <div className="flex items-center justify-between mb-2">
        <span className="font-bold text-slate-700">Round {round.round_num}</span>
        <div className="flex items-center gap-2">
          {round.exec_success
            ? <CheckCircle2 size={12} className="text-emerald-500" />
            : <XCircle size={12} className="text-red-400" />}
          <span className={`text-[11px] font-semibold ${
            round.is_sufficient ? 'text-emerald-700' : 'text-slate-500'
          }`}>
            {round.is_sufficient ? 'Approved ✓' : `${Math.round(round.verifier_confidence * 100)}% conf`}
          </span>
          <span className="text-[11px] font-mono text-slate-400">{ms(round.total_ms)}</span>
        </div>
      </div>
      <div className="space-y-1">
        {round.round_num === 1 && round.planner_ms > 0 && (
          <StageBar label="Planner" value={round.planner_ms} total={round.total_ms} color="bg-blue-400" />
        )}
        <StageBar label="Coder" value={round.coder_ms} total={round.total_ms} color="bg-violet-400" />
        <StageBar label="Executor" value={round.executor_ms} total={round.total_ms} color="bg-amber-400" />
        <StageBar label="Verifier" value={round.verifier_ms} total={round.total_ms} color="bg-emerald-400" />
        {round.router_ms > 0 && (
          <StageBar label="Router" value={round.router_ms} total={round.total_ms} color="bg-rose-400" />
        )}
      </div>
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────
export function AgentMetricsOverlay({ metrics, totalRunMs, complexity, rounds, isVisible }) {
  const [collapsed, setCollapsed] = useState(false)
  const [roundsCollapsed, setRoundsCollapsed] = useState(true)

  if (!isVisible || !metrics) return null

  const perRound = metrics.per_round || []
  const routerFix = perRound.filter(r => r.router_ms > 0).length
  const failedRounds = perRound.filter(r => !r.is_sufficient).length

  return (
    <div className="glass-card-elevated overflow-hidden border-l-4 border-violet-400 animate-slide-up">
      {/* Header */}
      <button
        onClick={() => setCollapsed(c => !c)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-violet-50 border border-violet-100 flex items-center justify-center">
            <BarChart2 size={14} className="text-violet-600" />
          </div>
          <div className="text-left">
            <p className="text-[13px] font-bold text-slate-800">Evaluation Metrics</p>
            <p className="text-[11px] text-slate-500 font-medium">DS-STAR performance diagnostic</p>
          </div>
          {/* Complexity badge */}
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
            complexity === 'hard'
              ? 'bg-rose-50 text-rose-700 border-rose-200'
              : 'bg-sky-50 text-sky-700 border-sky-200'
          }`}>
            {complexity === 'hard' ? '⚡ Hard Task' : '✓ Easy Task'}
          </span>
        </div>
        <div className="w-6 h-6 flex items-center justify-center rounded-full bg-slate-50 border border-slate-200 text-slate-400">
          {collapsed ? <ChevronDown size={13} /> : <ChevronUp size={13} />}
        </div>
      </button>

      {!collapsed && (
        <div className="border-t border-slate-100 px-5 py-4 space-y-5 animate-fade-in">

          {/* KPI row */}
          <div className="grid grid-cols-4 gap-3">
            {[
              { icon: Clock, label: 'Total Time', value: ms(totalRunMs), color: 'text-violet-600' },
              { icon: Activity, label: 'Rounds Used', value: `${rounds}/${metrics.rounds_completed ?? rounds}`, color: 'text-blue-600' },
              { icon: GitMerge, label: 'Router Fixes', value: routerFix, color: 'text-amber-600' },
              { icon: CheckCircle2, label: 'Fail / Pass', value: `${failedRounds} / ${rounds - failedRounds}`, color: 'text-emerald-600' },
            ].map(({ icon: Icon, label, value, color }) => (
              <div key={label} className="flex flex-col items-center p-3 rounded-xl bg-slate-50 border border-slate-100 text-center gap-1">
                <Icon size={14} className={color} />
                <span className="text-[15px] font-bold text-slate-800">{value}</span>
                <span className="text-[10px] text-slate-500 font-medium">{label}</span>
              </div>
            ))}
          </div>

          {/* Per-round breakdown toggle */}
          <div>
            <button
              onClick={() => setRoundsCollapsed(c => !c)}
              className="w-full flex items-center justify-between px-3 py-2 rounded-xl
                         bg-slate-50 border border-slate-100 hover:border-slate-200 transition-colors"
            >
              <span className="text-[12px] font-semibold text-slate-700">
                <Zap size={11} className="inline mr-1 text-violet-500" />
                Per-Round Breakdown ({perRound.length} rounds)
              </span>
              {roundsCollapsed ? <ChevronDown size={12} /> : <ChevronUp size={12} />}
            </button>

            {!roundsCollapsed && perRound.length > 0 && (
              <div className="mt-3 space-y-2 animate-fade-in">
                {perRound.map(r => <RoundRow key={r.round_num} round={r} />)}
              </div>
            )}
          </div>

          <p className="text-[10px] text-slate-400 font-medium text-center">
            Paper benchmark — Easy tasks: ~3.0 rounds avg · Hard tasks: ~5.6 rounds avg (DABStep)
          </p>
        </div>
      )}
    </div>
  )
}
