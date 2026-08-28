-- seed.sql
-- Local dev seed: one demo tenant + one demo user with fixed UUIDs.
-- These are the same ids `vera dev seed` uses, so CLI commands can pass
--   --tenant 0000000d-0000-4000-8000-000000000001
--   --user   0000000d-0000-4000-8000-000000000002

insert into public.tenants (id, name, plan)
values ('0000000d-0000-4000-8000-000000000001', 'Dev Tenant', 'free')
on conflict (id) do nothing;

insert into public.users (id, tenant_id, email, full_name, role)
values (
    '0000000d-0000-4000-8000-000000000002',
    '0000000d-0000-4000-8000-000000000001',
    'dev@vera.local',
    'Dev User',
    'owner'
)
on conflict (id) do nothing;
