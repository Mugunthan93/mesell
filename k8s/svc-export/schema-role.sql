-- k8s/svc-export/schema-role.sql
-- ===========================================================================
-- svc-export — Sub-Plan A (export extraction), INFRA deliverable I5.
--
-- Postgres SCHEMA + ROLE + GRANTS bootstrap for the export service.
-- Authority: handoff_msA_infra.md §1 I5 + MASTER_PLAN §2.D (schema-per-service)
--            + §5.B (shared public.audit_events, GRANT INSERT to every service).
--
-- This is the infra-owned "step zero" bootstrap that runs against the shared
-- `meesell` database BEFORE svc-export's own Alembic chain runs (Alembic creates
-- the `exports` table inside the `export` schema; this script creates the schema,
-- the role, and the grants the role needs).
--
-- ── HOW THIS RUNS ──────────────────────────────────────────────────────────
--   Applied once against the dev Postgres as a superuser (the `meesell` bootstrap
--   role), e.g. at deploy time:
--     kubectl exec postgres-0 -n dev -- psql -U meesell -d meesell -f - < schema-role.sql
--   It is IDEMPOTENT (IF NOT EXISTS / DO-block guards) — safe to re-run.
--
-- ── ROLE PASSWORD ──────────────────────────────────────────────────────────
--   The export_user password is NOT in this file (no secret in git — playbook §0).
--   It is set out-of-band from GCP Secret Manager at bootstrap, e.g.:
--     ALTER ROLE export_user WITH PASSWORD :'export_user_pw';   -- psql -v export_user_pw=...
--   and the SAME value is composed into svc-export's DATABASE_URL in the
--   svc-export-secrets k8s Secret (deliverable I7). The placeholder ALTER below is
--   commented; run it with the SM-sourced value, never a literal here.
--
-- ── CONNECTION / search_path ────────────────────────────────────────────────
--   svc-export connects with role export_user and DATABASE_URL carrying
--   `?options=-csearch_path%3Dexport,public` so its session sees `export` first
--   (its owned tables) and `public` (for audit_events). See I7.
-- ===========================================================================

-- 1. Schema -----------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS export;

-- 2. Role (LOGIN; NOSUPERUSER NOCREATEDB NOCREATEROLE — least privilege) ------
--    Created without a password here; password set out-of-band from Secret Manager.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'export_user') THEN
    CREATE ROLE export_user WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
  END IF;
END
$$;

-- Set the password from Secret Manager at bootstrap (run separately with -v):
-- ALTER ROLE export_user WITH PASSWORD :'export_user_pw';

-- 3. Schema ownership + usage -----------------------------------------------
--    export_user owns its schema so its Alembic chain can DDL (CREATE TABLE
--    exports, version_table_schema=export) without a separate migrator role.
--    (Sub-Plan A keeps it simple — one role does DDL + DML on its own schema.
--     A dedicated export_migrator role is a V2 hardening, infra plan §3.2.)
ALTER SCHEMA export OWNER TO export_user;
GRANT USAGE ON SCHEMA export TO export_user;

-- 4. DML on all tables in `export` (current + future) ------------------------
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA export TO export_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA export
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO export_user;
-- Sequences (UUID PKs use gen_random_uuid() so sequences are unlikely, but grant
-- defensively for any SERIAL/identity columns Alembic might add).
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA export TO export_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA export
  GRANT USAGE, SELECT ON SEQUENCES TO export_user;

-- 5. CROSS-SCHEMA AUDIT WRITE — R3 (handoff §1 I5 / §5; MASTER_PLAN §5.B) ------
--    *** THE BACKEND MERGE GATE DEPENDS ON THIS GRANT. ***
--    The integration test asserts an `export.initiated` / `export.completed` /
--    `export.failed` audit row lands in public.audit_events. svc-export writes
--    there via the shared core/audit.py API, so export_user MUST be able to:
--      - resolve the public schema (USAGE), and
--      - INSERT into public.audit_events.
--    audit_events has NO FK and is append-only (MASTER_PLAN §5.B) → INSERT only;
--    NO SELECT/UPDATE/DELETE granted (least privilege — a service cannot read or
--    tamper with another service's audit rows).
GRANT USAGE ON SCHEMA public TO export_user;
GRANT INSERT ON public.audit_events TO export_user;

-- Done. Verify with:
--   \dn export
--   \dp public.audit_events           -- expect export_user=a (INSERT) in the ACL
--   SELECT has_table_privilege('export_user','public.audit_events','INSERT');  -- t
