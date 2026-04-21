/**
 * RunList.jsx
 * Filterable run list.
 */

import React, { useState } from 'react'
import { Search, Filter, CheckCircle2, XCircle } from 'lucide-react'

export function RunList({ runs = [], onSelectRun, selectedRunId }) {
  const [diffFilter, setDiffFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')

  const filteredRuns = runs.filter(run => {
    if (diffFilter !== 'all' && run.difficulty !== diffFilter) return false
    if (statusFilter !== 'all') {
      const isSuccess = run.success_rate >= 1.0
      if (statusFilter === 'success' && !isSuccess) return false
      if (statusFilter === 'failed' && isSuccess) return false
    }
    return true
  })

  return (
    <div className="flex flex-col h-full bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
      {/* Header and Filters */}
      <div className="p-4 border-b border-slate-100 bg-slate-50/50">
        <h3 className="text-sm font-bold text-slate-800 mb-3">Evaluation Runs</h3>
        <div className="flex gap-2">
          <select 
            className="text-xs border-slate-200 rounded-lg px-2 py-1.5 bg-white shadow-sm flex-1"
            value={diffFilter}
            onChange={e => setDiffFilter(e.target.value)}
          >
            <option value="all">All Difficulties</option>
            <option value="easy">Easy Tasks</option>
            <option value="hard">Hard Tasks</option>
          </select>
          <select 
            className="text-xs border-slate-200 rounded-lg px-2 py-1.5 bg-white shadow-sm flex-1"
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
          >
            <option value="all">All Statuses</option>
            <option value="success">Successful</option>
            <option value="failed">Failed</option>
          </select>
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {filteredRuns.length === 0 ? (
          <div className="p-6 text-center text-sm text-slate-400">No runs found matching filters.</div>
        ) : (
          <div className="divide-y divide-slate-100">
            {filteredRuns.map(run => {
              const isSelected = selectedRunId === run.run_id
              const isSuccess = run.success_rate >= 1.0
              const queryStr = run.agent_runs?.query || 'Unknown query'
              
              return (
                <button
                  key={run.run_id}
                  onClick={() => onSelectRun(run.run_id)}
                  className={`w-full text-left p-4 hover:bg-slate-50 transition-colors flex flex-col gap-2 ${
                    isSelected ? 'bg-violet-50/50 hover:bg-violet-50 border-l-2 border-violet-500 pl-[14px]' : 'pl-4'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <p className="text-sm text-slate-700 font-medium line-clamp-2 pr-4">{queryStr}</p>
                    {isSuccess ? 
                      <CheckCircle2 size={16} className="text-emerald-500 shrink-0 mt-0.5" /> : 
                      <XCircle size={16} className="text-rose-500 shrink-0 mt-0.5" />
                    }
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    <span className={`px-2 py-0.5 rounded-full font-medium ${
                      run.difficulty === 'hard' ? 'bg-rose-50 text-rose-700' : 'bg-sky-50 text-sky-700'
                    }`}>
                      {run.difficulty === 'hard' ? 'Hard' : 'Easy'}
                    </span>
                    <span className="text-slate-400">&bull;</span>
                    <span className="text-slate-500">{new Date(run.created_at).toLocaleDateString()}</span>
                    <span className="text-slate-400">&bull;</span>
                    <span className="text-slate-500">{run.agent_runs?.rounds || '?'} rounds</span>
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
