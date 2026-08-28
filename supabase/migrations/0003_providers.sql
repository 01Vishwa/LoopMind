-- 0003_providers.sql

create table public.provider_connections (
    id                 uuid primary key default gen_random_uuid(),
    tenant_id          uuid not null references public.tenants(id) on delete cascade,
    user_id            uuid not null references public.users(id) on delete cascade,
    kind               text not null check (kind in ('openrouter','nvidia_nim')),
    display_name       text not null,
    base_url           text not null,
    api_key_ref        text not null,                 -- Vault secret name; NEVER the key
    status             text not null default 'validating'
                       check (status in ('connected','validating','failed','revoked')),
    last_validated_at  timestamptz,
    last_error         text,
    created_at         timestamptz not null default now(),
    unique (user_id, display_name)
);
create index idx_prov_conn_user on public.provider_connections(user_id);
create index idx_prov_conn_tenant on public.provider_connections(tenant_id);

create table public.provider_models_cache (
    provider_connection_id     uuid not null references public.provider_connections(id) on delete cascade,
    model_id                   text not null,
    display_name               text not null,
    context_window             integer not null default 0,
    input_price_per_m          numeric(12,6),
    output_price_per_m         numeric(12,6),
    supports_json_mode         boolean not null default false,
    supports_function_calling  boolean not null default false,
    supports_vision            boolean not null default false,
    cached_at                  timestamptz not null default now(),
    primary key (provider_connection_id, model_id)
);
