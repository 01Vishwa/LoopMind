-- supabase/migrations/0009_workspace_rls.sql

-- ── Workspaces ──
ALTER TABLE public.workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workspaces FORCE ROW LEVEL SECURITY;

CREATE POLICY workspaces_tenant_select ON public.workspaces FOR SELECT TO authenticated USING (tenant_id = public.current_tenant_id());
CREATE POLICY workspaces_tenant_insert ON public.workspaces FOR INSERT TO authenticated WITH CHECK (tenant_id = public.current_tenant_id());
CREATE POLICY workspaces_tenant_delete ON public.workspaces FOR DELETE TO authenticated USING (tenant_id = public.current_tenant_id());
CREATE POLICY workspaces_tenant_update ON public.workspaces FOR UPDATE TO authenticated USING (tenant_id = public.current_tenant_id()) WITH CHECK (tenant_id = public.current_tenant_id());

-- ── Files ──
ALTER TABLE public.files ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.files FORCE ROW LEVEL SECURITY;

CREATE POLICY files_tenant_select ON public.files FOR SELECT TO authenticated USING (tenant_id = public.current_tenant_id());
CREATE POLICY files_tenant_insert ON public.files FOR INSERT TO authenticated WITH CHECK (tenant_id = public.current_tenant_id());
CREATE POLICY files_tenant_delete ON public.files FOR DELETE TO authenticated USING (tenant_id = public.current_tenant_id());
CREATE POLICY files_tenant_update ON public.files FOR UPDATE TO authenticated USING (tenant_id = public.current_tenant_id()) WITH CHECK (tenant_id = public.current_tenant_id());

-- ── File Descriptions ──
ALTER TABLE public.file_descriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.file_descriptions FORCE ROW LEVEL SECURITY;

CREATE POLICY fd_tenant_select ON public.file_descriptions FOR SELECT TO authenticated USING (tenant_id = public.current_tenant_id());
CREATE POLICY fd_tenant_insert ON public.file_descriptions FOR INSERT TO authenticated WITH CHECK (tenant_id = public.current_tenant_id());
CREATE POLICY fd_tenant_delete ON public.file_descriptions FOR DELETE TO authenticated USING (tenant_id = public.current_tenant_id());
CREATE POLICY fd_tenant_update ON public.file_descriptions FOR UPDATE TO authenticated USING (tenant_id = public.current_tenant_id()) WITH CHECK (tenant_id = public.current_tenant_id());
