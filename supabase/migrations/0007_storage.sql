-- supabase/migrations/0007_storage.sql

-- Private bucket — no public URLs
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'workspace-files',
    'workspace-files',
    false,
    209715200, -- 200 MB (covers parquet max)
    ARRAY[
        'text/csv',
        'application/json',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel',
        'application/x-parquet',
        'text/markdown',
        'text/plain',
        'application/pdf',
        'application/x-sqlite3',
        'application/zip',
        'application/octet-stream' -- fallback for uncommon MIME types
    ]
);

-- Helper: get the current user's tenant_id
CREATE OR REPLACE FUNCTION storage.user_tenant_id()
RETURNS uuid
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    SELECT tenant_id FROM public.profiles WHERE id = auth.uid()
$$;

-- READ: user can only read files in their tenant's folder
CREATE POLICY storage_read ON storage.objects FOR SELECT TO authenticated
USING (
    bucket_id = 'workspace-files' 
    AND (storage.foldername(name))[1] = storage.user_tenant_id()::text
);

-- INSERT: user can only upload to their tenant's folder
CREATE POLICY storage_insert ON storage.objects FOR INSERT TO authenticated
WITH CHECK (
    bucket_id = 'workspace-files' 
    AND (storage.foldername(name))[1] = storage.user_tenant_id()::text
);

-- DELETE: user can only delete from their tenant's folder
CREATE POLICY storage_delete ON storage.objects FOR DELETE TO authenticated
USING (
    bucket_id = 'workspace-files' 
    AND (storage.foldername(name))[1] = storage.user_tenant_id()::text
);
