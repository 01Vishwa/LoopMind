import React, { useRef, useState, useEffect } from 'react'
import { Send, Sparkles, Paperclip } from 'lucide-react'

export function QueryInput({ onSubmit, isProcessing, fileCount }) {
  const [query, setQuery] = useState('')
  const textareaRef = useRef(null)

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 220)}px`
  }, [query])

  const handleSubmit = () => {
    const trimmed = query.trim()
    if (!trimmed || isProcessing) return
    onSubmit(trimmed)
    setQuery('')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleSubmit()
  }

  const hasContent = query.trim().length > 0
  const tokenCount = Math.ceil(query.trim().split(/\s+/).filter(Boolean).length * 1.3) || 0

  return (
    <div className="space-y-3 flex-shrink-0">
      <div className="section-header">
        <Sparkles size={13} className="text-brand-500" />
        <span className="text-slate-600">Natural Language Query</span>
      </div>

      <div className={`
        relative rounded-2xl transition-all duration-200 bg-white
        ${isProcessing
          ? 'border-brand-300 shadow-[0_0_15px_rgba(59,78,248,0.1)] ring-4 ring-brand-50'
          : 'border border-slate-200 shadow-sm focus-within:ring-4 focus-within:ring-brand-50 focus-within:border-brand-400'
        }
      `}>
        {/* Animated border glow while processing */}
        {isProcessing && (
          <div className="absolute inset-0 rounded-2xl border-2 border-brand-400/20 animate-pulse-slow pointer-events-none" />
        )}

        <textarea
          ref={textareaRef}
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isProcessing}
          rows={3}
          placeholder="Ask questions about your uploaded documents… (Ctrl+Enter to run)"
          className="
            w-full resize-none bg-transparent px-5 pt-4 pb-14
            text-sm font-medium text-slate-800 placeholder-slate-400
            focus:outline-none disabled:opacity-60
            leading-relaxed
          "
        />

        {/* Bottom toolbar */}
        <div className="absolute bottom-3 left-4 right-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            {fileCount > 0 && (
              <span className="flex items-center gap-1.5 text-[11px] text-slate-600 font-medium bg-slate-100 px-2.5 py-1 rounded-lg border border-slate-200">
                <Paperclip size={12} className="text-slate-500" />
                {fileCount} file{fileCount !== 1 ? 's' : ''}
              </span>
            )}
            {hasContent && (
              <span className="text-[11px] text-brand-600 font-bold bg-brand-50 border border-brand-100 px-2 py-1 rounded-lg">
                ~{tokenCount} Tokens
              </span>
            )}
            <span className="text-[11px] text-slate-400 font-medium hidden sm:block ml-1">Ctrl + Enter to run</span>
          </div>

          <button
            onClick={handleSubmit}
            disabled={!hasContent || isProcessing}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold shadow-sm
              transition-all duration-200 border
              ${hasContent && !isProcessing
                ? 'bg-brand-600 border-brand-500 text-white hover:bg-brand-700 hover:shadow-md hover:-translate-y-0.5 active:translate-y-0'
                : 'bg-slate-50 border-slate-200 text-slate-400 cursor-not-allowed hidden sm:flex'
              }
            `}
          >
            {isProcessing ? (
              <>
                <span className="w-3.5 h-3.5 rounded-full border-2 border-brand-200 border-t-white animate-spin" />
                Processing
              </>
            ) : (
              <>
                <Send size={14} className={hasContent && !isProcessing ? 'text-brand-100' : 'text-slate-400'} />
                Analyse
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
