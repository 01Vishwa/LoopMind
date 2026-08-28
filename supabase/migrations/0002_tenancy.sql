-- 0002_tenancy.sql
-- Minimal tenancy — full Auth wiring is Phase 6. users.id is a plain uuid now;
-- Phase 6 aligns it with auth.users.id.

create table public.tenants (
    id          uuid primary key default gen_random_uuid(),
    name        text not null,
    plan        text not null default 'free',
    created_at  timestamptz not null default now()
);

create table public.users (
    id          uuid primary key default gen_random_uuid(),
    tenant_id   uuid not null references public.tenants(id) on delete cascade,
    email       text not null unique,
    full_name   text not null default '',
    role        text not null default 'analyst',      -- owner|admin|analyst|viewer
    created_at  timestamptz not null default now()
);
create index idx_users_tenant on public.users(tenant_id);
