-- ============================================================
-- DS-STAR Agent Runs — Complete Supabase Schema
-- Run the FULL contents of this file in the Supabase SQL editor.
-- It is safe to re-run on an existing database (idempotent).
-- ============================================================

-- ── 0. Prerequisites: workspaces table must exist first ───────────────────────
-- Run create_workspaces.sql before this file if workspaces table is new.

-- ── 1. Create table if it doesn't exist ──────────────────────────────────────
create table if not exists agent_runs (
  id             text        primary key,
  session_id     text,
  user_id        uuid        references auth.users(id) on delete set null,
  workspace_id   uuid        references workspaces(id) on delete set null,
  query          text        not null,
  file_names     text[]      not null default '{}',
  plan_steps     jsonb       not null default '[]',
  final_code     text,
  rounds         int         not null default 0,
  status         text        not null default 'pending',
  -- status values: pending | running | completed | failed
  insights       jsonb,
  execution_logs jsonb       not null default '[]',
  eval_metrics   jsonb,
  parent_run_id  text        references agent_runs(id),
  created_at     timestamptz not null default now(),
  completed_at   timestamptz
);

-- ── 2. Add missing columns if this is an upgrade ──────────────────────────────
-- These are safe no-ops if columns already exist.
alter table agent_runs add column if not exists eval_metrics   jsonb;
alter table agent_runs add column if not exists session_id     text;
alter table agent_runs add column if not exists completed_at   timestamptz;
alter table agent_runs add column if not exists parent_run_id  text references agent_runs(id);
alter table agent_runs add column if not exists user_id        uuid references auth.users(id) on delete set null;
alter table agent_runs add column if not exists workspace_id   uuid references workspaces(id) on delete set null;

-- ── 3. Indexes ────────────────────────────────────────────────────────────────
create index if not exists agent_runs_created_at_idx
  on agent_runs (created_at desc);

create index if not exists agent_runs_status_idx
  on agent_runs (status);

create index if not exists agent_runs_session_id_idx
  on agent_runs (session_id);

create index if not exists agent_runs_user_id_idx
  on agent_runs (user_id);

create index if not exists agent_runs_workspace_id_idx
  on agent_runs (workspace_id);

create index if not exists agent_runs_parent_run_id_idx
  on agent_runs (parent_run_id);

-- ── 4. Row-Level Security ─────────────────────────────────────────────────────
alter table agent_runs enable row level security;

-- Drop the old open policy
drop policy if exists "Allow all operations" on agent_runs;
drop policy if exists "Users access own runs" on agent_runs;

-- Authenticated users can only read/write their own rows.
-- Rows with user_id IS NULL (legacy / anonymous) remain inaccessible
-- to logged-in users unless a separate policy is added for them.
create policy "Users access own runs"
  on agent_runs
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- Allow anonymous/service reads for rows where user_id is NULL
-- (backward-compatible for existing data without user_id).
drop policy if exists "Anonymous run access" on agent_runs;
create policy "Anonymous run access"
  on agent_runs
  for select
  using (user_id is null);
