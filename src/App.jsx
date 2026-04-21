import React from 'react'
import { HomePage } from './pages/HomePage'
import { ToastContainer } from './components/shared/Toast'
import { EvalDashboard } from './pages/EvalDashboard'
import { Routes, Route } from 'react-router-dom'
import { useFileUpload } from './hooks/useFileUpload'
import { useAgentRun } from './hooks/useAgentRun'
import './index.css'

export default function App() {
  const fileState = useFileUpload()
  const agentState = useAgentRun(fileState.files, fileState.sessionId)

  return (
    <>
      <Routes>
        <Route path="/" element={<HomePage fileState={fileState} agentState={agentState} />} />
        <Route path="/eval" element={<EvalDashboard />} />
      </Routes>
      <ToastContainer />
    </>
  )
}
