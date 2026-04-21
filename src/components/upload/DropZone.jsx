import React, { useCallback, useRef, useState } from 'react'
import { UploadCloud } from 'lucide-react'

const ACCEPTED = '.csv,.txt,.xlsx,.xls,.pdf,.json,.md,.parquet'
const ACCEPTED_TYPES = ['csv', 'txt', 'xlsx', 'xls', 'pdf', 'json', 'md', 'parquet']
const SUPPORTED_LABEL = 'csv, txt, xlsx, pdf, json, md, parquet'

export function DropZone({ onFiles, onRejected }) {
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef(null)

  const processFiles = useCallback((rawFiles) => {
    const valid = []
    const invalid = []

    Array.from(rawFiles).forEach((f) => {
      const ext = f.name.split('.').pop()?.toLowerCase() ?? ''
      if (ACCEPTED_TYPES.includes(ext)) {
        valid.push(f)
      } else {
        invalid.push({ name: f.name, ext, reason: `Unsupported file type: .${ext || '(none)'}. Supported: ${SUPPORTED_LABEL}` })
      }
    })

    if (valid.length) onFiles(valid)
    if (invalid.length && onRejected) onRejected(invalid)
  }, [onFiles, onRejected])

  const onDragOver = useCallback((e) => { e.preventDefault(); setDragging(true) }, [])
  const onDragLeave = useCallback((e) => { if (!e.currentTarget.contains(e.relatedTarget)) setDragging(false) }, [])
  const onDrop = useCallback((e) => { e.preventDefault(); setDragging(false); processFiles(e.dataTransfer.files) }, [processFiles])
  const onInputChange = useCallback((e) => { if (e.target.files?.length) processFiles(e.target.files); e.target.value = '' }, [processFiles])

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      className={`
        relative flex flex-col items-center justify-center gap-4
        rounded-2xl border-2 border-dashed px-6 py-10
        cursor-pointer select-none transition-all duration-200
        ${dragging
          ? 'border-brand-400 bg-brand-50/80 scale-[1.01] shadow-md'
          : 'border-slate-200 bg-slate-50/50 hover:border-brand-300 hover:bg-slate-50'
        }
      `}
    >
      {dragging && (
        <div className="absolute inset-0 rounded-2xl bg-brand-50 animate-pulse-slow pointer-events-none" />
      )}
      <div className={`w-16 h-16 rounded-2xl flex items-center justify-center transition-all duration-200 ${dragging ? 'bg-brand-100 text-brand-600 scale-110 shadow-sm' : 'bg-white shadow-sm border border-slate-100 text-slate-400'}`}>
        <UploadCloud size={30} className={dragging ? 'text-brand-600' : 'text-slate-400'} />
      </div>
      <div className="text-center space-y-1.5 z-10 relative">
        <p className={`font-semibold text-sm transition-colors duration-200 ${dragging ? 'text-brand-700' : 'text-slate-700'}`}>
          {dragging ? 'Release to upload files' : 'Drag & Drop files here'}
        </p>
        <p className="text-xs text-slate-500">or click to browse your files</p>
        <div className="flex flex-wrap justify-center gap-1.5 pt-1">
          {ACCEPTED_TYPES.map((ext) => (
            <span key={ext} className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-200/60 text-slate-600 uppercase border border-slate-200/60 tracking-wide">
              {ext}
            </span>
          ))}
        </div>
      </div>
      <input ref={inputRef} type="file" multiple accept={ACCEPTED} onChange={onInputChange} className="hidden" />
    </div>
  )
}
