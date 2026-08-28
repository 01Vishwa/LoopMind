-- 0006_profiles.sql
-- Wires public.profiles to auth.users so VERA has a single user record
-- to read from. Each new signup auto-creates a tenant + profile via trigger.

CREATE TABLE public.profiles (
    id          uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    tenant_id   uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    email       text NOT NULL,
    full_name   text NOT NULL DEFAULT '',
    avatar_url  text,
    timezone    text NOT NULL DEFAULT 'UTC',
    role        text NOT NULL DEFAULT 'analyst',
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_profiles_tenant ON public.profiles(tenant_id);

-- ── Auto-create profile on signup ────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    new_tenant_id uuid;
BEGIN
    -- Each new user gets their own tenant (single-tenant-per-user for now).
    INSERT INTO public.tenants (name)
    VALUES (NEW.email)
    RETURNING id INTO new_tenant_id;

    INSERT INTO public.profiles (id, tenant_id, email, full_name)
    VALUES (
        NEW.id,
        new_tenant_id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1))
    );

    RETURN NEW;
END;
$$;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ── updated_at auto-bump ─────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ── Row-level security ───────────────────────────────────────────────────────

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles FORCE ROW LEVEL SECURITY;

-- Users can only read their own profile.
CREATE POLICY profiles_self_read ON public.profiles
    FOR SELECT USING (id = auth.uid());

-- Update: only your own row, AND only via a trigger-enforced column allowlist.
-- RLS alone can't restrict which columns change on an UPDATE, so we add a
-- BEFORE UPDATE trigger that rejects changes to tenant_id and role unless
-- the request came from the service role (server-side, not the user's JWT).
CREATE POLICY profiles_self_update ON public.profiles
    FOR UPDATE USING (id = auth.uid())
    WITH CHECK (id = auth.uid());

CREATE OR REPLACE FUNCTION public.protect_profile_privileged_columns()
RETURNS trigger AS $$
BEGIN
    IF auth.role() = 'authenticated' THEN
        IF NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
           OR NEW.role IS DISTINCT FROM OLD.role THEN
            RAISE EXCEPTION 'tenant_id and role cannot be changed by the user';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER profiles_protect_privileged_columns
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION public.protect_profile_privileged_columns();
