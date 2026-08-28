-- supabase/migrations/0008_workspaces_files.sql

-- ═══════════════════════════════════════════
-- WORKSPACES
-- ═══════════════════════════════════════════
CREATE TABLE public.workspaces (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    created_by uuid NOT NULL REFERENCES public.profiles(id),
    name text NOT NULL,
    description text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT workspaces_name_length CHECK (char_length(name) BETWEEN 1 AND 100)
);

CREATE INDEX idx_workspaces_tenant ON workspaces(tenant_id);

-- ═══════════════════════════════════════════
-- FILES
-- ═══════════════════════════════════════════
CREATE TABLE public.files (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id uuid NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
    tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    filename text NOT NULL,
    kind text NOT NULL, -- csv|json|xlsx|parquet|markdown|txt|pdf|sqlite|zip
    size_bytes bigint NOT NULL,
    content_sha256 text NOT NULL,
    storage_path text NOT NULL, -- full path in Supabase Storage
    uploaded_by uuid NOT NULL REFERENCES public.profiles(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT files_name_length CHECK (char_length(filename) BETWEEN 1 AND 255),
    CONSTRAINT files_size_positive CHECK (size_bytes > 0),
    CONSTRAINT files_kind_valid CHECK (kind IN (
        'csv','json','xlsx','parquet','markdown','txt','pdf','sqlite','zip'
    ))
);

CREATE INDEX idx_files_workspace ON files(workspace_id);
CREATE INDEX idx_files_tenant ON files(tenant_id);
CREATE UNIQUE INDEX idx_files_dedup ON files(workspace_id, content_sha256);

-- ═══════════════════════════════════════════
-- FILE DESCRIPTIONS (from the Analyzer)
-- ═══════════════════════════════════════════
CREATE TABLE public.file_descriptions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id uuid NOT NULL UNIQUE REFERENCES public.files(id) ON DELETE CASCADE,
    tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    summary_text text NOT NULL,
    schema_fields jsonb, -- [{name, dtype, samples, warning}]
    row_count integer,
    sheet_names jsonb, -- for xlsx: ["Sheet1", "Sheet2"]
    sample_rows jsonb, -- first 3-5 rows as dicts
    analyzer_script text, -- the Python code the Analyzer wrote
    analyzer_model text NOT NULL, -- e.g., "anthropic/claude-sonnet-5"
    prompt_version text NOT NULL, -- e.g., "analyzer/v3"
    embedding halfvec(3072), -- for retrieval
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_fd_file ON file_descriptions(file_id);
CREATE INDEX idx_fd_tenant ON file_descriptions(tenant_id);
CREATE INDEX idx_fd_embedding ON file_descriptions USING hnsw (embedding halfvec_cosine_ops) WITH (m = 16, ef_construction = 64);
