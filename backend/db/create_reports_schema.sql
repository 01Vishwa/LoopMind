-- ============================================================
-- DS-STAR+ Reports Schema — Supabase SQL Migration
-- Run the FULL contents of this file in the Supabase SQL editor.
-- It is safe to re-run on an existing database (idempotent).
-- ============================================================

-- ── 0. Prerequisites ─────────────────────────────────────────────────────────
-- Run create_workspaces.sql and create_agent_runs.sql before this file.

-- ── 1. Extend agent_runs with parent_run_id ───────────────────────────────────
-- Already added in create_agent_runs.sql — no-op here if already present.
alter table agent_runs add column if not exists parent_run_id text references agent_runs(id);

create index if not exists agent_runs_parent_run_id_idx
  on agent_runs (parent_run_id);

-- ── 2. Create reports table ───────────────────────────────────────────────────
create table if not exists reports (
  id                text        primary key,
  query             text        not null,
  status            text        not null default 'running',
  -- status values: running | completed | failed
  user_id           uuid        references auth.users(id) on delete set null,
  workspace_id      uuid        references workspaces(id) on delete set null,
  title             text,
  executive_summary text,
  report_body       text,
  key_findings      jsonb       not null default '[]',
  caveats           jsonb       not null default '[]',
  sub_questions     jsonb       not null default '[]',   -- ordered List[str]
  sub_run_ids       jsonb       not null default '[]',   -- ordered List[run_id]
  session_id        text,
  file_names        text[]      not null default '{}',
  total_ms          int,
  created_at        timestamptz not null default now(),
  completed_at      timestamptz
);

-- Idempotent upgrade columns
alter table reports add column if not exists title             text;
alter table reports add column if not exists executive_summary text;
alter table reports add column if not exists report_body       text;
alter table reports add column if not exists key_findings      jsonb;
alter table reports add column if not exists caveats           jsonb;
alter table reports add column if not exists sub_questions     jsonb;
alter table reports add column if not exists sub_run_ids       jsonb;
alter table reports add column if not exists session_id        text;
alter table reports add column if not exists file_names        text[];
alter table reports add column if not exists total_ms          int;
alter table reports add column if not exists completed_at      timestamptz;
alter table reports add column if not exists user_id           uuid references auth.users(id) on delete set null;
alter table reports add column if not exists workspace_id      uuid references workspaces(id) on delete set null;

-- ── 3. Create sub_questions table ─────────────────────────────────────────────
create table if not exists sub_questions (
  id              text        primary key,
  report_id       text        not null references reports(id) on delete cascade,
  question        text        not null,
  question_index  int         not null,
  status          text        not null default 'pending',
  -- status values: pending | running | completed | failed | max_rounds_reached
  result_run_id   text        references agent_runs(id),
  created_at      timestamptz not null default now(),
  completed_at    timestamptz
);

alter table sub_questions add column if not exists question_index  int;
alter table sub_questions add column if not exists completed_at    timestamptz;

-- ── 4. Indexes ────────────────────────────────────────────────────────────────
create index if not exists reports_created_at_idx
  on reports (created_at desc);

create index if not exists reports_status_idx
  on reports (status);

create index if not exists reports_session_id_idx
  on reports (session_id);

create index if not exists reports_user_id_idx
  on reports (user_id);

create index if not exists reports_workspace_id_idx
  on reports (workspace_id);

create index if not exists sub_questions_report_id_idx
  on sub_questions (report_id);

create index if not exists sub_questions_result_run_id_idx
  on sub_questions (result_run_id);

-- ── 5. Row-Level Security ─────────────────────────────────────────────────────

-- reports
alter table reports enable row level security;

drop policy if exists "Allow all operations on reports" on reports;
drop policy if exists "Users access own reports" on reports;
drop policy if exists "Anonymous report access" on reports;

create policy "Users access own reports"
  on reports
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "Anonymous report access"
  on reports
  for select
  using (user_id is null);

-- sub_questions
alter table sub_questions enable row level security;

drop policy if exists "Allow all operations on sub_questions" on sub_questions;
drop policy if exists "Users access own sub_questions" on sub_questions;

create policy "Users access own sub_questions"
  on sub_questions
  for all
  using (
    exists (
      select 1 from reports r
      where r.id = sub_questions.report_id
        and auth.uid() = r.user_id
    )
  );
