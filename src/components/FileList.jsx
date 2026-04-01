import React from 'react'
import { X, CheckCircle2, Loader2 } from 'lucide-react'
import { FileTypeIcon, FileTypeBadge, formatBytes } from './FileTypeUtils'

function ProgressBar({ value }) {
  return (
    <div className="mt-2 h-1 w-full bg-slate-100 rounded-full overflow-hidden">
      <div
        className="h-full bg-gradient-to-r from-brand-500 to-violet-500 rounded-full transition-all duration-300"
        style={{ width: `${value}%` }}
      />
    </div>
  )
}

function FileItem({ file, onRemove }) {
  const isUploading = file.progress < 100
  const isDone = file.progress === 100

  return (
    <div className="file-chip group animate-bounce-in">
      <FileTypeIcon filename={file.name} />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-slate-800 truncate">{file.name}</p>
          <FileTypeBadge filename={file.name} />
        </div>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-xs text-slate-500">{formatBytes(file.size)}</span>
          {isUploading && (
            <span className="text-xs text-brand-600 font-medium flex items-center gap-1">
              <Loader2 size={10} className="animate-spin" /> Uploading…
            </span>
          )}
          {isDone && (
            <span className="text-xs text-emerald-600 font-medium flex items-center gap-1">
              <CheckCircle2 size={10} /> Ready
            </span>
          )}
        </div>
        {isUploading && <ProgressBar value={file.progress} />}
      </div>

      <button
        onClick={() => onRemove(file.id)}
        className="shrink-0 w-7 h-7 rounded-lg flex items-center justify-center
                   text-slate-400 hover:text-rose-600 hover:bg-rose-50
                   opacity-0 group-hover:opacity-100 transition-all duration-150"
      >
        <X size={14} />
      </button>
    </div>
  )
}

export function FileList({ files, onRemove }) {
  if (!files.length) return null

  return (
    <div className="flex-1 min-h-0 flex flex-col animate-fade-in">
      <div className="section-header px-0.5 mb-2 shrink-0">
        <span>Uploaded files</span>
        <span className="ml-auto text-slate-500 normal-case font-medium tracking-normal text-xs">
          {files.length} file{files.length !== 1 ? 's' : ''}
        </span>
      </div>
      <div className="flex-1 overflow-y-auto pr-1 space-y-2 pb-2">
        {files.map(f => (
          <FileItem key={f.id} file={f} onRemove={onRemove} />
        ))}
      </div>
    </div>
  )
}
