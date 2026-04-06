-- DS-STAR agent_runs table
-- Run this in the Supabase SQL editor for your project.

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
  created_at     timestamptz not null default now(),
  completed_at   timestamptz
);

-- Index for chronological querying
create index if not exists agent_runs_created_at_idx
  on agent_runs (created_at desc);

-- Index for status filtering
create index if not exists agent_runs_status_idx
  on agent_runs (status);

-- Row-level security (optional — enable if using Supabase Auth)
-- alter table agent_runs enable row level security;
