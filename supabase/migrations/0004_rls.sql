-- 0004_rls.sql

create or replace function public.current_tenant_id() returns uuid
language sql stable as $$
    select coalesce(
        nullif(current_setting('request.jwt.claims', true)::jsonb ->> 'tenant_id', ''),
        nullif(current_setting('app.tenant_id', true), '')
    )::uuid
$$;

alter table public.provider_connections enable row level security;
alter table public.provider_connections force row level security;
create policy prov_conn_tenant on public.provider_connections
    using (tenant_id = public.current_tenant_id())
    with check (tenant_id = public.current_tenant_id());

alter table public.provider_models_cache enable row level security;
alter table public.provider_models_cache force row level security;
create policy prov_models_tenant on public.provider_models_cache
    using (exists (
        select 1 from public.provider_connections pc
        where pc.id = provider_connection_id
          and pc.tenant_id = public.current_tenant_id()
    ));

alter table public.tenants enable row level security;   -- no policy: service-role only for now
alter table public.users   enable row level security;
