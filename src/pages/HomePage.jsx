import React from 'react'
import { Cpu, Zap, GitBranch } from 'lucide-react'
import { FileUploadPanel } from '../components/upload/FileUploadPanel'
import { QueryInput } from '../components/query/QueryInput'
import { OutputPanel } from '../components/query/OutputPanel'
import { ConfirmDialog } from '../components/shared/ConfirmDialog'
import { useFileUpload } from '../hooks/useFileUpload'
import { useQuery } from '../hooks/useQuery'

export function HomePage() {
  const {
    files,
    pendingDuplicates,
    handleAddFiles,
    handleConfirmDuplicates,
    handleRemoveFile,
    handleClearAll,
  } = useFileUpload()

  const { status, output, queryHistory, handleSubmit } = useQuery(files)

  return (
    <div className="min-h-screen font-sans bg-[#f8fafc] text-slate-800">
      {/* Background grid */}
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

      {/* ── Navbar ── */}
      <header className="relative z-20 border-b border-slate-200/80 bg-white/70 backdrop-blur-md">
        <div className="max-w-[1600px] mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-violet-600 flex items-center justify-center shadow-md">
              <Cpu size={18} className="text-white" />
            </div>
            <div>
              <span className="font-bold text-slate-800 text-base tracking-tight">DocMind</span>
              <span className="ml-2 text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-brand-50 text-brand-600 uppercase tracking-wider" />
            </div>
          </div>

          <div className="hidden md:flex items-center gap-2 text-xs text-slate-500 font-medium">
            <Zap size={12} className="text-brand-500" />
            Intelligent Document Processing Platform
          </div>

          <div className="flex items-center gap-2">
            <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="btn-ghost px-3">
              <GitBranch size={16} />
            </a>
          </div>
        </div>
      </header>

      {/* ── Main Layout ── */}
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
          <div className="glass-card-elevated p-5 shrink-0">
            <QueryInput
              onSubmit={handleSubmit}
              isProcessing={status === 'processing'}
              fileCount={files.filter((f) => f.progress === 100).length}
            />
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

          <div className="flex-1">
            <OutputPanel output={output} status={status} />
          </div>
        </section>
      </main>

      <ConfirmDialog
        isOpen={pendingDuplicates.length > 0}
        duplicates={pendingDuplicates}
        onConfirm={handleConfirmDuplicates}
        onCancel={() => {}}
      />
    </div>
  )
}
