import React, { useState } from 'react'
import { Copy, Check, Terminal, ChevronDown, ChevronUp } from 'lucide-react'

const TABS = ['Python']

function highlightLine(line) {
  const SYNTAX_COLORS = {
    'import': 'text-purple-600 font-medium', 'from': 'text-purple-600 font-medium',
    'def': 'text-purple-600 font-medium', 'return': 'text-purple-600 font-medium',
    'for': 'text-purple-600 font-medium', 'in': 'text-purple-600 font-medium',
    'if': 'text-purple-600 font-medium', 'else': 'text-purple-600 font-medium',
    'True': 'text-orange-600', 'False': 'text-orange-600', 'None': 'text-orange-600',
    'SELECT': 'text-blue-600 font-semibold', 'FROM': 'text-blue-600 font-semibold',
    'WHERE': 'text-blue-600 font-semibold', 'AND': 'text-purple-600 font-medium',
    'COUNT': 'text-emerald-600', 'SUM': 'text-emerald-600',
  }
  const tokens = line.split(/(\s+|,|\.|(\(|\)|\[|\])|"|'|#.*)/g)
  return (
    <span>
      {tokens.map((token, i) => {
        if (token?.startsWith('#')) return <span key={i} className="text-slate-400 italic">{token}</span>
        if (token?.startsWith('"') || token?.startsWith("'")) return <span key={i} className="text-emerald-600">{token}</span>
        if (/^\d+(\.\d+)?$/.test(token)) return <span key={i} className="text-orange-600">{token}</span>
        if (SYNTAX_COLORS[token]) return <span key={i} className={SYNTAX_COLORS[token]}>{token}</span>
        return <span key={i}>{token}</span>
      })}
    </span>
  )
}

function CopyButton({ code }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code)
    } catch {
      const el = document.createElement('textarea')
      el.value = code
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button
      onClick={handleCopy}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all duration-200 shadow-sm
        ${copied ? 'bg-emerald-50 border-emerald-200 text-emerald-600' : 'bg-white border-slate-200 text-slate-500 hover:bg-slate-50 hover:text-slate-700'}`}
    >
      {copied ? <Check size={12} /> : <Copy size={12} />}
      {copied ? 'Copied!' : 'Copy'}
    </button>
  )
}

export function CodeBlock({ codeByTab, collapsed, onToggleCollapse }) {
  const [activeTab, setActiveTab] = useState('Python')
  const code = codeByTab[activeTab] || ''
  const lines = code.split('\n')

  return (
    <div className="code-block animate-slide-up">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-200 bg-[#f8fafc]">
        <div className="flex items-center gap-2">
          <Terminal size={14} className="text-slate-500" />
          <div className="flex gap-1">
            {TABS.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-3 py-1 rounded-md text-xs font-semibold transition-all duration-150 border
                  ${activeTab === tab ? 'bg-white border-slate-200 text-brand-600 shadow-sm' : 'bg-transparent border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-100'}`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <CopyButton code={code} />
          <button
            onClick={onToggleCollapse}
            className="w-7 h-7 flex items-center justify-center rounded-lg border border-slate-200 bg-white shadow-sm text-slate-500 hover:text-slate-700 transition-colors"
          >
            {collapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
          </button>
        </div>
      </div>
      {!collapsed && (
        <div className="overflow-x-auto bg-white">
          <table className="w-full text-[13px] font-mono leading-relaxed py-2 block">
            <tbody>
              {lines.map((line, i) => (
                <tr key={i} className="hover:bg-slate-50">
                  <td className="select-none text-right pr-4 pl-4 text-slate-300 w-12 border-r border-slate-100 py-0.5">{i + 1}</td>
                  <td className="pl-4 pr-6 text-slate-800 whitespace-pre py-0.5 min-w-max">{highlightLine(line)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
