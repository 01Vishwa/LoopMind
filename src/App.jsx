import React, { useState, useCallback } from 'react'
import { Cpu, Zap, GitBranch, ChevronRight } from 'lucide-react'
import { FileUploadPanel } from './components/FileUploadPanel'
import { QueryInput } from './components/QueryInput'
import { OutputPanel } from './components/OutputPanel'
import { ToastContainer, toast } from './components/Toast'
import { ConfirmDialog } from './components/ConfirmDialog'
import './index.css'

let fileIdCounter = 0

function simulateUpload(file) {
  return new Promise((resolve) => {
    const steps = [15, 35, 55, 75, 90, 100]
    let i = 0
    const interval = setInterval(() => {
      file._onProgress(steps[i])
      i++
      if (i >= steps.length) {
        clearInterval(interval)
        resolve()
      }
    }, 120)
  })
}

export default function App() {
  const [files, setFiles] = useState([])
  const [status, setStatus] = useState('idle') // idle | processing | completed
  const [output, setOutput] = useState(null)
  const [queryHistory, setQueryHistory] = useState([])
  const [pendingDuplicates, setPendingDuplicates] = useState([])

  // ── File handling ───────────────────────────────────────────────────────────
  const startUploads = async (entriesToUpload) => {
    for (const entry of entriesToUpload) {
      entry._onProgress = (pct) => {
        setFiles(prev => prev.map(f => f.id === entry.id ? { ...f, progress: pct } : f))
      }
      await simulateUpload(entry)
    }
  }

  const handleAddFiles = useCallback(async (newFiles) => {
    const entries = newFiles.map(f => ({
      id: ++fileIdCounter,
      name: f.name,
      size: f.size,
      progress: 0,
      _raw: f,
      _onProgress: null,
    }))

    const existingNames = files.map(f => f.name)
    const unique = entries.filter(e => !existingNames.includes(e.name))
    const duplicates = entries.filter(e => existingNames.includes(e.name))

    if (unique.length > 0) {
      toast(`${unique.length} file${unique.length > 1 ? 's' : ''} added`, 'success')
      setFiles(prev => [...prev, ...unique])
      startUploads(unique)
    }

    if (duplicates.length > 0) {
      setPendingDuplicates(duplicates)
    } else if (unique.length === 0) {
      toast('Files already uploaded', 'info')
    }
  }, [files])

  const handleConfirmDuplicates = useCallback(() => {
    if (pendingDuplicates.length > 0) {
      toast(`${pendingDuplicates.length} file${pendingDuplicates.length > 1 ? 's' : ''} replaced`, 'success')
      
      setFiles(prev => {
        const dupNames = pendingDuplicates.map(d => d.name)
        const withoutOld = prev.filter(f => !dupNames.includes(f.name))
        return [...withoutOld, ...pendingDuplicates]
      })

      startUploads(pendingDuplicates)
      setPendingDuplicates([])
    }
  }, [pendingDuplicates])

  const handleRemoveFile = useCallback((id) => {
    const file = files.find(f => f.id === id)
    if (file) {
      toast(`Removed "${file.name}"`, 'error')
      setFiles(prev => prev.filter(f => f.id !== id))
    }
  }, [files])

  const handleClearAll = useCallback(() => {
    if (files.length > 0) {
      toast('All files cleared', 'info')
      setFiles([])
    }
  }, [files])

  // ── Query handling ──────────────────────────────────────────────────────────
  const handleSubmit = useCallback(async (query) => {
    if (files.filter(f => f.progress === 100).length === 0) {
      toast('Please upload at least one file first', 'error')
      return
    }

    setStatus('processing')
    setOutput(null)
    setQueryHistory(prev => [{ query, ts: Date.now() }, ...prev].slice(0, 10))

    // Simulate 2.5s processing time
    await new Promise(r => setTimeout(r, 2500))

    const inputTokens = Math.ceil(query.trim().split(/\s+/).filter(Boolean).length * 1.3) || 0
    const outputText = `Based on your request: "${query}", we have processed the ${files.length} attached document(s).\n\nThe key patterns matched your parameters successfully. No major anomalies were detected during the analysis phase.`
    const outputTokens = Math.ceil(outputText.split(/\s+/).filter(Boolean).length * 1.3)
    
    const result = {
      insights: {
        summary: outputText,
        bullets: [
          `Input Query Tokens: ~${inputTokens}`,
          `Generated Output Tokens: ~${outputTokens}`,
          `Total Tokens Processed: ~${inputTokens + outputTokens}`
        ]
      },
      code: {
        Python: `# Analysis script for query:\n# ${query}\n\nimport pandas as pd\n\nprint("Tokens processed: ${inputTokens + outputTokens}")\nprint("Analysis complete.")`
      }
    }

    setOutput(result)
    setStatus('completed')
    toast('Analysis complete!', 'success')
  }, [files])

  return (
    <div className={`min-h-screen font-sans bg-[#f8fafc] text-slate-800`}>
      {/* Background grid (Light mode style) */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          backgroundImage: `
            radial-gradient(ellipse 80% 50% at 20% 10%, rgba(59,78,248,0.04) 0%, transparent 60%),
            radial-gradient(ellipse 60% 40% at 80% 70%, rgba(139,92,246,0.03) 0%, transparent 60%),
            linear-gradient(rgba(0,0,0,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,0,0,0.03) 1px, transparent 1px)
          `,
          backgroundSize: '100% 100%, 100% 100%, 48px 48px, 48px 48px',
        }}
      />

      {/* ── Navbar ─────────────────────────────────────────────────────────── */}
      <header className="relative z-20 border-b border-slate-200/80 bg-white/70 backdrop-blur-md">
        <div className="max-w-[1600px] mx-auto px-6 py-3 flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-violet-600 flex items-center justify-center shadow-md">
              <Cpu size={18} className="text-white" />
            </div>
            <div>
              <span className="font-bold text-slate-800 text-base tracking-tight">DocMind</span>
              <span className="ml-2 text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-brand-50 text-brand-600 uppercase tracking-wider">
              </span>
            </div>
          </div>

          {/* Center tag */}
          <div className="hidden md:flex items-center gap-2 text-xs text-slate-500 font-medium">
            <Zap size={12} className="text-brand-500" />
            Intelligent Document Processing Platform
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="btn-ghost px-3"
            >
              <GitBranch size={16} />
            </a>
          </div>
        </div>
      </header>

      {/* ── Main Layout ────────────────────────────────────────────────────── */}
      <main className="relative z-10 max-w-[1600px] mx-auto px-6 py-6 h-[calc(100vh-61px)] flex gap-6">

        {/* LEFT — File Upload Panel (32%) */}
        <aside className="w-[32%] shrink-0 flex flex-col min-h-0">
          <div className="glass-card-elevated h-full flex flex-col min-h-0 p-5">
            <FileUploadPanel
              files={files}
              onAddFiles={handleAddFiles}
              onRemoveFile={handleRemoveFile}
              onClearAll={handleClearAll}
            />
          </div>
        </aside>

        {/* RIGHT — Query + Output (68%) */}
        <section className="flex-1 flex flex-col gap-5 overflow-y-auto">
          {/* Query header */}
          <div className="glass-card-elevated p-5 shrink-0">
            <QueryInput
              onSubmit={handleSubmit}
              isProcessing={status === 'processing'}
              fileCount={files.filter(f => f.progress === 100).length}
            />

            {/* Query history chips */}
            {queryHistory.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2 items-center">
                <span className="text-[11px] text-slate-500 font-medium">Recent:</span>
                {queryHistory.slice(0, 4).map((h, i) => (
                  <button
                    key={i}
                    className="text-[11px] px-2.5 py-1 rounded-lg bg-slate-100/80 text-slate-600 hover:text-slate-800
                               hover:bg-slate-200 transition-all duration-150 truncate max-w-[200px]"
                    title={h.query}
                  >
                    {h.query.length > 40 ? h.query.slice(0, 40) + '…' : h.query}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Output */}
          <div className="flex-1">
            <OutputPanel output={output} status={status} />
          </div>
        </section>
      </main>

      <ConfirmDialog
        isOpen={pendingDuplicates.length > 0}
        duplicates={pendingDuplicates}
        onConfirm={handleConfirmDuplicates}
        onCancel={() => setPendingDuplicates([])}
      />

      {/* Toast notifications */}
      <ToastContainer />
    </div>
  )
}
