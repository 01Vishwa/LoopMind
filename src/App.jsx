/**
 * App.jsx — Application root.
 *
 * Wraps the entire component tree with <AuthProvider> so that every
 * descendant can consume auth state via useAuth(). The provider must be
 * the outermost wrapper — placed here rather than in main.jsx so that
 * AuthModal can be rendered at the router level if needed.
 */

import React from 'react'
import { Routes, Route } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { LandingPage } from './pages/LandingPage'
import { ProjectsPage } from './pages/ProjectsPage'
import { HomePage } from './pages/HomePage'
import { ToastContainer } from './components/shared/Toast'
import { EvalDashboard } from './pages/EvalDashboard'
import { useFileUpload } from './hooks/useFileUpload'
import { useAgentRun } from './hooks/useAgentRun'
import './index.css'

/**
 * Inner app — lives inside AuthProvider so hooks can call useAuth().
 */
function AppInner() {
  const fileState = useFileUpload()
  const agentState = useAgentRun(fileState.files)

  return (
    <>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/project/:projectId" element={<HomePage fileState={fileState} agentState={agentState} />} />
        <Route path="/eval" element={<EvalDashboard />} />
      </Routes>
      <ToastContainer />
    </>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppInner />
    </AuthProvider>
  )
}
