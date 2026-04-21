import React from 'react'
import { Cpu, Zap, GitBranch, BarChart2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { FileUploadPanel } from '../components/upload/FileUploadPanel'
import { QueryInput } from '../components/query/QueryInput'
import { AgentProgressPanel } from '../components/agent/AgentProgressPanel'
import { HistoryPanel } from '../components/agent/HistoryPanel'
import { AgentSettings } from '../components/agent/AgentSettings'
import { ConfirmDialog } from '../components/shared/ConfirmDialog'

export function HomePage({ fileState, agentState }) {
  const {
    files,
    pendingDuplicates,
    sessionId,
    handleAddFiles,
    handleConfirmDuplicates,
    handleRemoveFile,
    handleClearAll,
  } = fileState

  const {
    agentStatus,
    phase,
    planSteps,
    currentCode,
    executionLogs,
    currentRound,
    maxRounds,
    output: agentOutput,
    verifierFeedback,
    artifacts,
    historyRuns,
    historyLoading,
    settings,
    setSettings,
    handleSubmit,
    handleReset,
    fetchHistory,
    loadRun,
    runMetrics,
    totalRunMs,
    complexity,
    showMetrics,
  } = agentState

  const isProcessing = !['idle', 'completed', 'failed'].includes(agentStatus)

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
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-violet-600
                            flex items-center justify-center shadow-md">
              <Cpu size={18} className="text-white" />
            </div>
            <div>
              <span className="font-bold text-slate-800 text-base tracking-tight">LoopMind</span>
              <span className="ml-2 text-[10px] font-semibold px-1.5 py-0.5 rounded-full
                               bg-brand-50 text-brand-600 uppercase tracking-wider">
                DS-STAR
              </span>
            </div>
          </div>

          <div className="hidden md:flex items-center gap-2 text-xs text-slate-500 font-medium">
            <Zap size={12} className="text-brand-500" />
            DS-STAR · Plan → Code → Execute → Verify
          </div>

          <div className="flex items-center gap-3">
            <Link to="/eval" className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-slate-200 text-[12px] font-semibold bg-white text-slate-700 shadow-sm hover:bg-slate-50 transition-colors">
              <BarChart2 size={13} className="text-violet-600" />
            </Link>

            <AgentSettings
              settings={settings}
              onChange={setSettings}
              disabled={isProcessing}
              placement="header"
            />

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

      {/* ── Main Layout ── */}
      <main className="relative z-10 max-w-[1600px] mx-auto px-6 py-6
                       h-[calc(100vh-61px)] flex gap-6">

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

          {/* Query input */}
          <div className="glass-card-elevated p-5 shrink-0">
            <QueryInput
              onSubmit={(query) => handleSubmit(query, sessionId)}
              isProcessing={isProcessing}
              fileCount={files.filter((f) => f.progress === 100).length}
              placeholder="Ask DS-STAR anything about your data…"
            />
          </div>

          {/* Output area */}
          <div className="flex-1 space-y-4">
            {/* History drawer */}
            <HistoryPanel
              historyRuns={historyRuns}
              historyLoading={historyLoading}
              fetchHistory={fetchHistory}
              loadRun={loadRun}
            />
            <AgentProgressPanel
              phase={phase}
              agentStatus={agentStatus}
              planSteps={planSteps}
              currentCode={currentCode}
              executionLogs={executionLogs}
              currentRound={currentRound}
              maxRounds={maxRounds}
              output={agentOutput}
              verifierFeedback={verifierFeedback}
              artifacts={artifacts}
              onReset={handleReset}
              runMetrics={runMetrics}
              totalRunMs={totalRunMs}
              complexity={complexity}
              showMetrics={showMetrics}
            />
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
