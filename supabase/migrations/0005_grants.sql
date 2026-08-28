-- 0005_grants.sql

grant usage on schema public to authenticated;
grant select, insert, update, delete on
    public.provider_connections, public.provider_models_cache to authenticated;
-- vault.decrypted_secrets is NOT granted to authenticated — server/service-role only.
