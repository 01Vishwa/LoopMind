-- ============================================================
-- DS-STAR Agent Runs — Complete Supabase Schema
-- Run the FULL contents of this file in the Supabase SQL editor.
-- It is safe to re-run on an existing database (idempotent).
-- ============================================================

-- ── 1. Create table if it doesn't exist ─────────────────────────────────────
create table if not exists agent_runs (
  id             text primary key,
  session_id     text,
  query          text not null,
  file_names     text[] not null default '{}',
  plan_steps     jsonb not null default '[]',
  final_code     text,
  rounds         int not null default 0,
  status         text not null default 'pending',
  -- status values: pending | running | completed | failed
  insights       jsonb,
  execution_logs jsonb not null default '[]',
  eval_metrics   jsonb,
  created_at     timestamptz not null default now(),
  completed_at   timestamptz
);

-- ── 2. Add missing columns if this is an upgrade ────────────────────────────
-- These are safe no-ops if columns already exist.
alter table agent_runs add column if not exists eval_metrics   jsonb;
alter table agent_runs add column if not exists session_id     text;
alter table agent_runs add column if not exists completed_at   timestamptz;

-- ── 3. Indexes ───────────────────────────────────────────────────────────────
create index if not exists agent_runs_created_at_idx
  on agent_runs (created_at desc);

create index if not exists agent_runs_status_idx
  on agent_runs (status);

create index if not exists agent_runs_session_id_idx
  on agent_runs (session_id);

-- ── 4. Optional: Row-Level Security ─────────────────────────────────────────
-- Uncomment the lines below if you use Supabase Auth and want
-- to restrict reads to the currently authenticated user.
--
alter table agent_runs enable row level security;
create policy "Allow all operations" on agent_runs for all using (true);
