-- 0001_extensions.sql
create extension if not exists supabase_vault cascade;   -- Vault (pgsodium + vault schema)
create extension if not exists vector;
create extension if not exists pgcrypto;
