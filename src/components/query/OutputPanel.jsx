import React, { useState } from 'react'
import {
  Brain, Code2, Activity, ChevronDown, ChevronUp,
  CheckCircle2, Loader2, Clock, Lightbulb
} from 'lucide-react'
import { CodeBlock } from './CodeBlock'

function StatusPanel({ status }) {
  const config = {
    idle:       { icon: Clock,        color: 'text-slate-500',   bg: 'bg-slate-50',   ring: 'ring-slate-200',   label: 'Idle',       desc: 'Waiting for a query…' },
    processing: { icon: Loader2,      color: 'text-brand-600',   bg: 'bg-brand-50',   ring: 'ring-brand-200',   label: 'Processing', desc: 'Analyzing your documents…' },
    completed:  { icon: CheckCircle2, color: 'text-emerald-600', bg: 'bg-emerald-50', ring: 'ring-emerald-200', label: 'Completed',  desc: 'Results ready.' },
  }
  const { icon: Icon, color, bg, ring, label, desc } = config[status] || config.idle

  return (
    <div className={`flex items-center gap-3 px-4 py-3 rounded-xl bg-white shadow-sm ring-1 ${ring}`}>
      <div className={`w-8 h-8 rounded-lg ${bg} flex items-center justify-center`}>
        <Icon size={16} className={`${color} ${status === 'processing' ? 'animate-spin' : ''}`} />
      </div>
      <div>
        <p className={`text-sm font-semibold ${color}`}>{label}</p>
        <p className="text-[11px] text-slate-500 font-medium">{desc}</p>
      </div>
      {status === 'processing' && (
        <div className="ml-auto flex gap-1">
          {[0, 1, 2].map((i) => (
            <span key={i} className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
          ))}
        </div>
      )}
    </div>
  )
}

function Skeleton() {
  return (
    <div className="space-y-3">
      {[100, 90, 95, 60].map((w, i) => (
        <div key={i} className="h-3 rounded shimmer-bg" style={{ width: `${w}%`, animationDelay: `${i * 0.1}s` }} />
      ))}
    </div>
  )
}

function InsightsPanel({ insights, isLoading, collapsed, onToggle }) {
  return (
    <div className="glass-card shadow-sm overflow-hidden animate-slide-up bg-white">
      <button onClick={onToggle} className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-50 transition-colors">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-violet-50 border border-violet-100 flex items-center justify-center shadow-sm">
            <Brain size={16} className="text-violet-600" />
          </div>
          <div className="text-left">
            <p className="text-sm font-bold text-slate-800">Extracted Insights</p>
            <p className="text-[11px] text-slate-500 font-medium">AI-powered analysis of your documents</p>
          </div>
        </div>
        <div className="w-7 h-7 flex items-center justify-center rounded-full bg-slate-50 border border-slate-200 text-slate-500">
          {collapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
        </div>
      </button>
      {!collapsed && (
        <div className="px-5 pb-5 border-t border-slate-100 pt-4 animate-fade-in">
          {isLoading ? <Skeleton /> : insights ? (
            <div className="space-y-5 text-[13px] text-slate-700 leading-relaxed font-medium">
              {insights.summary && <p className="p-3 bg-slate-50 border border-slate-100 rounded-xl">{insights.summary}</p>}
              {insights.bullets?.length > 0 && (
                <ul className="space-y-2.5 px-1">
                  {insights.bullets.map((b, i) => (
                    <li key={i} className="flex gap-3 items-start">
                      <span className="mt-2 w-1.5 h-1.5 rounded-full bg-brand-500 shrink-0 shadow-sm" />
                      <span>{b}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center py-8 gap-3">
              <div className="w-12 h-12 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-center shadow-sm">
                <Lightbulb size={20} className="text-slate-400" />
              </div>
              <p className="text-sm text-slate-500 font-medium text-center">Submit a query above to see AI-generated insights</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function GeneratedCodePanel({ codeByTab, isLoading, collapsed, onToggle }) {
  const [codeCollapsed, setCodeCollapsed] = useState(false)
  return (
    <div className="glass-card shadow-sm overflow-hidden animate-slide-up bg-white" style={{ animationDelay: '0.1s' }}>
      <button onClick={onToggle} className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-50 transition-colors">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-brand-50 border border-brand-100 flex items-center justify-center shadow-sm">
            <Code2 size={16} className="text-brand-600" />
          </div>
          <div className="text-left">
            <p className="text-sm font-bold text-slate-800">Generated Code</p>
            <p className="text-[11px] text-slate-500 font-medium">Executable scripts for your analysis</p>
          </div>
        </div>
        <div className="w-7 h-7 flex items-center justify-center rounded-full bg-slate-50 border border-slate-200 text-slate-500">
          {collapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
        </div>
      </button>
      {!collapsed && (
        <div className="px-5 pb-5 border-t border-slate-100 pt-4 animate-fade-in">
          {isLoading ? <div className="h-40 shimmer-bg rounded-xl border border-slate-100" /> : codeByTab ? (
            <CodeBlock codeByTab={codeByTab} collapsed={codeCollapsed} onToggleCollapse={() => setCodeCollapsed((c) => !c)} />
          ) : (
            <div className="flex flex-col items-center py-8 gap-3">
              <div className="w-12 h-12 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-center shadow-sm">
                <Code2 size={20} className="text-slate-400" />
              </div>
              <p className="text-sm text-slate-500 font-medium text-center">Generated code will appear here after analysis</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export function OutputPanel({ output, status }) {
  const [insightsCollapsed, setInsightsCollapsed] = useState(false)
  const [codeCollapsed, setCodeCollapsed] = useState(false)
  const isLoading = status === 'processing'

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <div className="section-header px-1">
          <Activity size={13} className="text-brand-500" />
          <span className="text-slate-600">Processing Status</span>
        </div>
        <StatusPanel status={status} />
      </div>
      <InsightsPanel insights={output?.insights} isLoading={isLoading} collapsed={insightsCollapsed} onToggle={() => setInsightsCollapsed((c) => !c)} />
      <GeneratedCodePanel codeByTab={output?.code} isLoading={isLoading} collapsed={codeCollapsed} onToggle={() => setCodeCollapsed((c) => !c)} />
    </div>
  )
}
