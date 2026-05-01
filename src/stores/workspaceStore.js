/**
 * workspaceStore.js — Zustand store for active workspace state.
 *
 * Manages:
 *  - The list of user workspaces fetched from Supabase.
 *  - The currently active workspace (persisted to sessionStorage).
 *  - CRUD actions: fetch, create, select.
 *
 * The store is auth-aware: fetchWorkspaces() is a no-op when no
 * access token is provided, and createWorkspace() guards the same way.
 *
 * All Supabase interaction goes through the REST client injected via
 * the supabase singleton — no hard-coded URLs.
 */

import { create } from 'zustand'
import { supabase } from '../lib/supabaseClient'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const SESSION_KEY = 'agentloop_active_workspace'

function loadPersistedWorkspaceId() {
  try {
    return sessionStorage.getItem(SESSION_KEY) || null
  } catch {
    return null
  }
}

function persistWorkspaceId(id) {
  try {
    if (id) sessionStorage.setItem(SESSION_KEY, id)
    else sessionStorage.removeItem(SESSION_KEY)
  } catch {
    // sessionStorage not available (private browsing, etc.)
  }
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

/**
 * @typedef {import('../types/index').Workspace} Workspace
 */

export const useWorkspaceStore = create((set, get) => ({
  /** @type {Workspace[]} */
  workspaces: [],

  /** @type {Workspace|null} */
  activeWorkspace: null,

  loading: false,

  /** @type {string|null} */
  error: null,

  // ── Actions ──────────────────────────────────────────────────────────────

  /**
   * Fetches workspaces owned by the authenticated user.
   * Restores the previously active workspace from sessionStorage if valid.
   *
   * @param {string} userId - The authenticated user's UUID.
   */
  fetchWorkspaces: async (userId) => {
    if (!userId) return
    set({ loading: true, error: null })

    const { data, error } = await supabase
      .from('workspaces')
      .select('*')
      .eq('user_id', userId)
      .order('created_at', { ascending: true })

    if (error) {
      set({ loading: false, error: error.message })
      return
    }

    const workspaces = data ?? []
    const persistedId = loadPersistedWorkspaceId()
    const active =
      workspaces.find((w) => w.id === persistedId) ?? workspaces[0] ?? null

    set({ workspaces, activeWorkspace: active, loading: false })
  },

  /**
   * Creates a new workspace for the authenticated user, then adds it to
   * the store and activates it.
   *
   * @param {string} userId - The authenticated user's UUID.
   * @param {string} name   - Workspace display name.
   * @returns {Promise<Workspace|null>}
   */
  createWorkspace: async (userId, name) => {
    if (!userId || !name.trim()) return null
    set({ loading: true, error: null })

    const { data, error } = await supabase
      .from('workspaces')
      .insert({ user_id: userId, name: name.trim() })
      .select()
      .single()

    if (error) {
      set({ loading: false, error: error.message })
      return null
    }

    set((state) => ({
      workspaces: [...state.workspaces, data],
      activeWorkspace: data,
      loading: false,
    }))
    persistWorkspaceId(data.id)
    return data
  },

  /**
   * Sets the active workspace and persists the choice to sessionStorage.
   *
   * @param {Workspace} workspace
   */
  setActiveWorkspace: (workspace) => {
    persistWorkspaceId(workspace?.id ?? null)
    set({ activeWorkspace: workspace })
  },

  /**
   * Resets the store (call on sign-out).
   */
  reset: () => {
    persistWorkspaceId(null)
    set({ workspaces: [], activeWorkspace: null, loading: false, error: null })
  },
}))
