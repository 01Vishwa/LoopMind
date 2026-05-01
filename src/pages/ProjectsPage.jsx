import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Briefcase, Loader2, ArrowRight, FolderKanban, LogOut, User } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useWorkspaceStore } from '../stores/workspaceStore'

export function ProjectsPage() {
  const { user, signOut, isAuthenticated, loading: authLoading } = useAuth()
  const { workspaces, loading: wsLoading, fetchWorkspaces, createWorkspace, setActiveWorkspace } = useWorkspaceStore()
  const navigate = useNavigate()

  const [isCreating, setIsCreating] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const [createLoading, setCreateLoading] = useState(false)

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate('/', { replace: true })
    }
  }, [authLoading, isAuthenticated, navigate])

  // Fetch projects on load
  useEffect(() => {
    if (user?.id) {
      fetchWorkspaces(user.id)
    }
  }, [user?.id, fetchWorkspaces])

  const handleSelectProject = (project) => {
    setActiveWorkspace(project)
    navigate(`/project/${project.id}`)
  }

  const handleCreateProject = async (e) => {
    e.preventDefault()
    if (!newProjectName.trim() || !user?.id) return
    setCreateLoading(true)
    try {
      const newWs = await createWorkspace(user.id, newProjectName)
      setNewProjectName('')
      setIsCreating(false)
      // Navigate straight to the newly created project
      handleSelectProject(newWs)
    } catch (err) {
      console.error('Failed to create project:', err)
    } finally {
      setCreateLoading(false)
    }
  }

  if (authLoading || (wsLoading && workspaces.length === 0)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#f8fafc]">
        <Loader2 size={32} className="animate-spin text-brand-500" />
      </div>
    )
  }

  return (
    <div className="min-h-screen font-sans bg-[#f8fafc] text-slate-800 relative">
      {/* Navbar */}
      <header className="relative z-20 border-b border-slate-200/80 bg-white/70 backdrop-blur-md">
        <div className="max-w-[1200px] mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-violet-600
                            flex items-center justify-center shadow-md">
              <FolderKanban size={18} className="text-white" />
            </div>
            <span className="font-bold text-slate-800 text-base tracking-tight">Agentloop Projects</span>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-slate-200
                            bg-white text-[12px] font-medium text-slate-700 shadow-sm">
              <User size={13} className="text-brand-500" />
              <span className="hidden sm:block max-w-[150px] truncate">{user?.email}</span>
            </div>
            <button
              onClick={() => { signOut(); navigate('/') }}
              className="btn-ghost px-3 text-[12px]"
              title="Sign out"
            >
              <LogOut size={15} />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-[1200px] mx-auto px-6 py-12 relative z-10">
        <div className="flex items-center justify-between mb-10">
          <div>
            <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Your Projects</h1>
            <p className="text-slate-500 mt-2">Select a project to continue or create a new isolated workspace.</p>
          </div>
          <button
            onClick={() => setIsCreating(true)}
            className="btn-primary"
            disabled={isCreating}
          >
            <Plus size={16} />
            New Project
          </button>
        </div>

        {isCreating && (
          <div className="mb-8 p-6 glass-card-elevated animate-slide-up border-brand-200 bg-brand-50/30">
            <h3 className="text-sm font-bold text-slate-800 mb-3">Create New Project</h3>
            <form onSubmit={handleCreateProject} className="flex gap-3">
              <input
                autoFocus
                type="text"
                placeholder="Project Name (e.g. Q1 Financial Analysis)"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                maxLength={60}
                className="flex-1 input-field"
                disabled={createLoading}
              />
              <button type="submit" disabled={!newProjectName.trim() || createLoading} className="btn-primary shrink-0">
                {createLoading ? <Loader2 size={16} className="animate-spin" /> : 'Create'}
              </button>
              <button type="button" onClick={() => setIsCreating(false)} className="btn-secondary shrink-0" disabled={createLoading}>
                Cancel
              </button>
            </form>
          </div>
        )}

        {workspaces.length === 0 && !wsLoading && !isCreating ? (
          <div className="text-center py-20 px-6 glass-card-elevated border-dashed border-2 border-slate-200">
            <Briefcase size={48} className="mx-auto text-slate-300 mb-4" />
            <h2 className="text-lg font-bold text-slate-700 mb-2">No projects yet</h2>
            <p className="text-slate-500 mb-6">Create your first project to start running agents and analyzing data.</p>
            <button onClick={() => setIsCreating(true)} className="btn-primary mx-auto">
              <Plus size={16} />
              Create Project
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {workspaces.map((ws) => (
              <div
                key={ws.id}
                onClick={() => handleSelectProject(ws)}
                className="group cursor-pointer glass-card-elevated p-6 transition-all duration-300 hover:shadow-xl hover:shadow-brand-500/10 hover:-translate-y-1 hover:border-brand-300"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center text-slate-500 group-hover:bg-brand-100 group-hover:text-brand-600 transition-colors">
                    <Briefcase size={20} />
                  </div>
                  <ArrowRight size={16} className="text-slate-300 opacity-0 group-hover:opacity-100 group-hover:text-brand-500 group-hover:translate-x-1 transition-all" />
                </div>
                <h3 className="text-lg font-bold text-slate-800 mb-1 truncate">{ws.name}</h3>
                <p className="text-xs text-slate-400">
                  Created {new Date(ws.created_at).toLocaleDateString()}
                </p>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
