-- ============================================================
-- DS-STAR Evaluation + Observability Schema
-- Run the FULL contents of this file in the Supabase SQL editor.
-- It is safe to re-run on an existing database (idempotent).
-- ============================================================

-- ── 1. eval_steps — one row per agent step per run ───────────────────────────
--    Captures every deterministic boundary inside the orchestrator loop.
create table if not exists eval_steps (
  id                text        primary key,          -- uuid4 step_id
  run_id            text        not null,             -- FK → agent_runs.id
  step_seq          int         not null,             -- ordering within the run (0-based)
  round_num         int         not null default 1,   -- orchestrator round this step belongs to
  agent_name        text        not null,             -- Analyzer|Planner|Coder|Executor|Debugger|Verifier|Router|Finalizer
  input_summary     text,                             -- truncated input (≤ 512 chars)
  output_summary    text,                             -- truncated output (≤ 512 chars)
  latency_ms        int         not null default 0,
  retry_count       int         not null default 0,
  error_type        text,                             -- NULL = success
  validation_passed boolean     not null default true,
  timestamp_iso     text        not null,
  created_at        timestamptz not null default now()
);

-- Indexes for common query patterns
create index if not exists eval_steps_run_id_idx  on eval_steps (run_id);
create index if not exists eval_steps_agent_idx   on eval_steps (agent_name);
create index if not exists eval_steps_error_idx   on eval_steps (error_type) where error_type is not null;

-- ── 2. eval_metrics — one row per completed run (materialized) ───────────────
create table if not exists eval_metrics (
  run_id              text        primary key,        -- FK → agent_runs.id
  -- Correctness
  success_rate        float       not null default 0, -- 1.0 = verified, 0.0 = max rounds hit
  exec_success_rate   float       not null default 0, -- fraction of rounds where execution succeeded
  validation_pass_rate float      not null default 0, -- step-level schema validation pass rate
  -- Efficiency
  total_retries       int         not null default 0,
  avg_debug_depth     float       not null default 0, -- avg debug loop depth per failed exec
  plan_step_count     int         not null default 0, -- steps in initial plan
  final_step_count    int         not null default 0, -- steps in final plan (deviation indicator)
  -- Per-agent latency breakdowns (ms)
  analyzer_ms         int         not null default 0,
  planner_ms          int         not null default 0,
  coder_ms            int         not null default 0,
  executor_ms         int         not null default 0,
  debugger_ms         int         not null default 0,
  verifier_ms         int         not null default 0,
  router_ms           int         not null default 0,
  finalizer_ms        int         not null default 0,
  -- Classification
  difficulty          text        not null default 'easy',  -- easy | hard
  mode                text        not null default 'live',  -- live | batch
  query_length        int         not null default 0,
  created_at          timestamptz not null default now()
);

create index if not exists eval_metrics_difficulty_idx on eval_metrics (difficulty);
create index if not exists eval_metrics_mode_idx       on eval_metrics (mode);
create index if not exists eval_metrics_created_idx    on eval_metrics (created_at desc);

-- ── 3. RLS — allow all operations (same policy as agent_runs) ────────────────
alter table eval_steps   enable row level security;
alter table eval_metrics enable row level security;

drop policy if exists "Allow all on eval_steps" on eval_steps;
create policy "Allow all on eval_steps"
  on eval_steps for all using (true);

drop policy if exists "Allow all on eval_metrics" on eval_metrics;
create policy "Allow all on eval_metrics"
  on eval_metrics for all using (true);
