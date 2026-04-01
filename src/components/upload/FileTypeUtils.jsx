/* eslint-disable react-refresh/only-export-components */
import React from 'react'
import {
  FileText, FileSpreadsheet, Code2, FileJson,
  File, FileCog
} from 'lucide-react'

const FILE_CONFIG = {
  csv:  { icon: FileSpreadsheet, color: 'text-emerald-700', bg: 'bg-emerald-50 border border-emerald-100', label: 'CSV'  },
  xlsx: { icon: FileSpreadsheet, color: 'text-emerald-700', bg: 'bg-emerald-50 border border-emerald-100', label: 'XLSX' },
  xls:  { icon: FileSpreadsheet, color: 'text-emerald-700', bg: 'bg-emerald-50 border border-emerald-100', label: 'XLS'  },
  pdf:  { icon: FileText,        color: 'text-rose-600',    bg: 'bg-rose-50 border border-rose-100',       label: 'PDF'  },
  txt:  { icon: FileText,        color: 'text-sky-700',     bg: 'bg-sky-50 border border-sky-100',         label: 'TXT'  },
  json: { icon: FileJson,        color: 'text-amber-700',   bg: 'bg-amber-50 border border-amber-100',     label: 'JSON' },
  md:   { icon: FileCog,         color: 'text-violet-700',  bg: 'bg-violet-50 border border-violet-100',   label: 'MD'   },
  js:   { icon: Code2,           color: 'text-yellow-700',  bg: 'bg-yellow-50 border border-yellow-100',   label: 'JS'   },
}

export function getFileConfig(filename) {
  const ext = filename.split('.').pop()?.toLowerCase() || ''
  return FILE_CONFIG[ext] || { icon: File, color: 'text-slate-600', bg: 'bg-slate-50 border border-slate-200', label: ext.toUpperCase() || 'FILE' }
}

export function formatBytes(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

export function FileTypeIcon({ filename, size = 18 }) {
  const cfg = getFileConfig(filename)
  const Icon = cfg.icon
  return (
    <div className={`shrink-0 w-9 h-9 rounded-lg ${cfg.bg} flex items-center justify-center shadow-sm`}>
      <Icon size={size} className={cfg.color} />
    </div>
  )
}

export function FileTypeBadge({ filename }) {
  const cfg = getFileConfig(filename)
  return (
    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${cfg.bg} ${cfg.color} shadow-sm border-none`}>
      {cfg.label}
    </span>
  )
}
