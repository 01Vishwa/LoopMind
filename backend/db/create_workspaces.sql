-- ============================================================
-- Workspaces Table — Supabase SQL Migration
-- Run this file in the Supabase SQL editor.
-- It is safe to re-run on an existing database (idempotent).
-- ============================================================

-- ── 1. Create workspaces table ────────────────────────────────────────────────
create table if not exists workspaces (
  id          uuid        primary key default gen_random_uuid(),
  user_id     uuid        not null references auth.users(id) on delete cascade,
  name        text        not null check (char_length(name) > 0 and char_length(name) <= 120),
  created_at  timestamptz not null default now()
);

-- ── 2. Indexes ────────────────────────────────────────────────────────────────
create index if not exists workspaces_user_id_idx
  on workspaces (user_id);

create index if not exists workspaces_created_at_idx
  on workspaces (created_at);

-- ── 3. Row-Level Security — owner-only access ─────────────────────────────────
alter table workspaces enable row level security;

-- Drop any legacy open policies before creating the scoped one
drop policy if exists "Allow all operations on workspaces" on workspaces;
drop policy if exists "Users manage own workspaces" on workspaces;

create policy "Users manage own workspaces"
  on workspaces
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- ── 4. Comment ────────────────────────────────────────────────────────────────
comment on table workspaces is
  'User-owned project namespaces. All agent_runs and reports can be scoped to a workspace.';
comment on column workspaces.user_id is 'FK to auth.users — the workspace owner.';
comment on column workspaces.name    is 'Human-readable workspace label (1–120 chars).';
