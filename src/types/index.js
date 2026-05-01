/**
 * index.js — Shared JSDoc typedefs for the Agentloop frontend.
 *
 * These are documentation-only; no runtime code is exported.
 * Import in JSDoc @param / @returns annotations for IDE autocomplete.
 *
 * @module types
 */

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

/**
 * @typedef {Object} AuthUser
 * @property {string} id
 * @property {string} email
 * @property {string|null} [avatar_url]
 * @property {Record<string, unknown>} [user_metadata]
 */

/**
 * @typedef {Object} AuthSession
 * @property {string}   access_token
 * @property {string}   refresh_token
 * @property {number}   expires_at        - Unix timestamp (seconds)
 * @property {AuthUser} user
 */

// ---------------------------------------------------------------------------
// Workspace
// ---------------------------------------------------------------------------

/**
 * @typedef {Object} Workspace
 * @property {string} id           - UUID
 * @property {string} user_id      - FK → auth.users.id
 * @property {string} name
 * @property {string} created_at   - ISO 8601
 */

// ---------------------------------------------------------------------------
// Agent run
// ---------------------------------------------------------------------------

/**
 * @typedef {'pending'|'running'|'completed'|'failed'} RunStatus
 */

/**
 * @typedef {Object} AgentRun
 * @property {string}      id
 * @property {string|null} session_id
 * @property {string|null} user_id
 * @property {string|null} workspace_id
 * @property {string}      query
 * @property {string[]}    file_names
 * @property {Object[]}    plan_steps
 * @property {string|null} final_code
 * @property {number}      rounds
 * @property {RunStatus}   status
 * @property {Object|null} insights
 * @property {string[]}    execution_logs
 * @property {Object|null} eval_metrics
 * @property {string}      created_at
 * @property {string|null} completed_at
 */

/**
 * @typedef {Object} PlanStep
 * @property {number} index
 * @property {string} description
 * @property {string} status   - 'pending' | 'active' | 'done' | 'error'
 */

// ---------------------------------------------------------------------------
// File upload
// ---------------------------------------------------------------------------

/**
 * @typedef {Object} FileEntry
 * @property {number}  id
 * @property {string}  name
 * @property {number}  size
 * @property {number}  progress  - 0–100, or -1 for rejected
 * @property {File}    _raw
 */
