/**
 * TracePanel.jsx
 * Displays step-by-step trace of a single run.
 */

import React from 'react'
import { Code2, Settings, AlertTriangle, FileCheck, CheckCircle2, XCircle, ArrowRightCircle } from 'lucide-react'

const AGENT_ICONS = {
  Analyzer: FileCheck,
  Planner: Settings,
  Coder: Code2,
  Executor: ArrowRightCircle,
  Debugger: AlertTriangle,
  Verifier: CheckCircle2,
  Router: Settings,
  Finalizer: FileCheck,
}

export function TracePanel({ traceData }) {
  if (!traceData) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-50 rounded-2xl border border-slate-100 border-dashed">
        <p className="text-slate-400 text-sm">Select a run from the list to view its execution trace.</p>
      </div>
    )
  }

  const { run, steps } = traceData

  return (
    <div className="flex flex-col h-full bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
      <div className="p-5 border-b border-slate-100 bg-slate-50/50">
        <h3 className="text-lg font-bold text-slate-800 mb-1">Execution Trace</h3>
        <p className="text-sm text-slate-500 font-mono">Run ID: {traceData.run_id.substring(0, 8)}...</p>
        {run?.query && (
          <div className="mt-4 p-3 bg-white border border-slate-200 rounded-lg text-sm text-slate-700 italic">
            "{run.query}"
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-5">
        {(!steps || steps.length === 0) ? (
          <p className="text-sm text-slate-400">No steps recorded for this run.</p>
        ) : (
          <div className="space-y-4">
            {steps.map((step, idx) => {
              const Icon = AGENT_ICONS[step.agent_name] || CheckCircle2
              const isError = step.error_type || !step.validation_passed
              
              return (
                <div key={step.id || idx} className="flex gap-4">
                  {/* Timeline column */}
                  <div className="flex flex-col items-center">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center shadow-sm shrink-0 ${
                      isError ? 'bg-rose-100 text-rose-600 border border-rose-200' : 'bg-violet-100 text-violet-600 border border-violet-200'
                    }`}>
                      <Icon size={14} />
                    </div>
                    {idx < steps.length - 1 && <div className="w-px h-full bg-slate-200 my-1"></div>}
                  </div>

                  {/* Content column */}
                  <div className="flex-1 pb-4">
                    <div className="bg-white border text-sm border-slate-100 shadow-sm rounded-xl p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="font-bold text-slate-800">{step.agent_name}</span>
                        <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 font-medium text-slate-500">
                          R{step.round_num}
                        </span>
                        <span className="text-xs py-0.5 font-mono text-slate-400 ml-auto">
                          {step.latency_ms > 0 ? `${step.latency_ms}ms` : ''}
                        </span>
                      </div>
                      
                      {step.error_type && (
                        <div className="mb-3 px-3 py-2 bg-rose-50 text-rose-700 border border-rose-100 rounded-lg text-xs font-mono break-all">
                          {step.error_type}
                        </div>
                      )}
                      
                      {step.input_summary && (
                        <div className="mb-2">
                          <span className="text-xs uppercase font-semibold text-slate-400 block mb-1">Input</span>
                          <p className="text-slate-600 text-sm line-clamp-3 leading-snug break-words">
                            {step.input_summary}
                          </p>
                        </div>
                      )}

                      {step.output_summary && (
                        <div>
                          <span className="text-xs uppercase font-semibold text-slate-400 block mb-1 mt-3">Output</span>
                          <p className="text-slate-600 text-sm line-clamp-3 leading-snug break-words">
                            {step.output_summary}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
