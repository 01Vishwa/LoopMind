-- 0007_agent_defaults.sql

-- 1. Drop the provider_models_cache as it's no longer used server-side
drop table if exists public.provider_models_cache;

-- 2. Modify provider_connections
-- Drop columns that are no longer relevant to backend state
alter table public.provider_connections
    drop column if exists base_url,
    drop column if exists api_key_ref,
    drop column if exists status,
    drop column if exists last_validated_at,
    drop column if exists last_error;

-- 3. Create agent_defaults table
create table public.agent_defaults (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references public.tenants(id) on delete cascade,
    user_id uuid not null references public.users(id) on delete cascade,
    
    -- Run Limits
    max_rounds integer not null default 7 check (max_rounds >= 1 and max_rounds <= 20),
    max_cost_usd numeric(12,2) not null default 2.50 check (max_cost_usd >= 0.10 and max_cost_usd <= 50.0),
    max_debug_attempts integer not null default 3 check (max_debug_attempts >= 1 and max_debug_attempts <= 10),
    
    -- File Processing
    retriever_top_k integer not null default 12 check (retriever_top_k >= 1 and retriever_top_k <= 50),
    
    updated_at timestamptz not null default now(),
    
    unique (user_id)
);

create index idx_agent_defaults_user on public.agent_defaults(user_id);
create index idx_agent_defaults_tenant on public.agent_defaults(tenant_id);

-- 4. Create agent_model_assignments table
create table public.agent_model_assignments (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references public.tenants(id) on delete cascade,
    user_id uuid not null references public.users(id) on delete cascade,
    
    tier text not null check (tier in ('reasoning', 'utility', 'embedding')),
    provider_connection_id uuid references public.provider_connections(id) on delete set null,
    model_id text not null,
    
    updated_at timestamptz not null default now(),
    
    unique (user_id, tier)
);

create index idx_agent_model_assignments_user on public.agent_model_assignments(user_id);
create index idx_agent_model_assignments_tenant on public.agent_model_assignments(tenant_id);

-- Enable RLS
alter table public.agent_defaults enable row level security;
alter table public.agent_model_assignments enable row level security;

-- RLS policies for agent_defaults
create policy "Users can view their own agent defaults"
    on public.agent_defaults for select
    using (auth.uid() = user_id);

create policy "Users can insert their own agent defaults"
    on public.agent_defaults for insert
    with check (auth.uid() = user_id);

create policy "Users can update their own agent defaults"
    on public.agent_defaults for update
    using (auth.uid() = user_id);

create policy "Users can delete their own agent defaults"
    on public.agent_defaults for delete
    using (auth.uid() = user_id);

-- RLS policies for agent_model_assignments
create policy "Users can view their own agent model assignments"
    on public.agent_model_assignments for select
    using (auth.uid() = user_id);

create policy "Users can insert their own agent model assignments"
    on public.agent_model_assignments for insert
    with check (auth.uid() = user_id);

create policy "Users can update their own agent model assignments"
    on public.agent_model_assignments for update
    using (auth.uid() = user_id);

create policy "Users can delete their own agent model assignments"
    on public.agent_model_assignments for delete
    using (auth.uid() = user_id);
