-- k8s/svc-dashboard/audit-grant.sql
-- ===========================================================================
-- svc-dashboard — Sub-Plan B (dashboard extraction), INFRA deliverable I5.
--
-- Postgres ROLE + AUDIT-WRITE GRANT for the dashboard service.
-- Authority: handoff_msB_infra.md §1 I5 + MASTER_PLAN §5.B (shared
--            public.audit_events, GRANT INSERT to every service)
--            + SUB_PLAN_0B §0.8 (dashboard owns ZERO tables).
--
-- *** KEY DIFFERENCE vs k8s/svc-export/schema-role.sql (MS-A I5) ***
--   svc-export OWNS the `export` schema (CREATE SCHEMA export, ALTER OWNER,
--   GRANT SELECT/INSERT/UPDATE/DELETE on its tables). svc-dashboard owns
--   ZERO tables (§0.8 — it queries ~nothing; DATABASE_URL exists only so the
--   vendored middleware chain + Depends(get_db) signature have a session).
--   THEREFORE this file:
--     - has NO `CREATE SCHEMA dashboard`   (no owned schema)
--     - has NO schema OWNER / table DML grants  (no owned tables)
--     - grants ONLY the cross-schema audit INSERT (the SAME R3 grant svc-export
--       gets) — for the INERT audit_mw import path.
--   It is the cheapest database bootstrap of any extraction.
--
-- ── WHY THE AUDIT GRANT IS STILL NEEDED (audit_mw writes NOTHING on GET) ─────
--   dashboard's GET /api/v1/products is read-only with a NONE audit posture
--   (§0.7 / §13.B — audit_mw RUNS but writes no row on this route). So at
--   RUNTIME, svc-dashboard never INSERTs into public.audit_events.
--   The grant exists for IMPORT-SAFETY: the vendored audit_mw / core/audit.py
--   import-chain wires the audit-write API (it expects the INSERT capability to
--   be present). The backend merge gate asserts `dashboard_user` HAS
--   `INSERT ON public.audit_events` so the vendored middleware import is safe.
--   (handoff §5 acceptance item: "I5 confirmed.")
--
-- ── HOW THIS RUNS ──────────────────────────────────────────────────────────
--   Applied once against the dev Postgres as the `meesell` bootstrap superuser,
--   e.g. at deploy time:
--     kubectl exec postgres-0 -n dev -- psql -U meesell -d meesell -f - < audit-grant.sql
--   It is IDEMPOTENT (DO-block role guard; GRANTs are idempotent) — safe to re-run.
--
-- ── ROLE PASSWORD ──────────────────────────────────────────────────────────
--   The dashboard_user password is NOT in this file (no secret in git — playbook
--   §0). It is set out-of-band from GCP Secret Manager at bootstrap:
--     ALTER ROLE dashboard_user WITH PASSWORD :'dashboard_user_pw';  -- psql -v ...
--   and the SAME value is composed into svc-dashboard's DATABASE_URL in the
--   svc-dashboard-secrets k8s Secret (deliverable I7). The placeholder ALTER
--   below is commented; run it with the SM-sourced value, never a literal here.
--
-- ── CONNECTION / search_path ────────────────────────────────────────────────
--   svc-dashboard connects with role dashboard_user. UNLIKE svc-export there is
--   NO owned schema to pin first — dashboard's session needs only `public`
--   (for the inert audit path + any shared-table reads the get_db wiring touches).
--   So the DATABASE_URL carries NO custom search_path override (default `public`
--   is correct). See I7 (svc-dashboard-secrets.yaml.example).
-- ===========================================================================

-- 1. Role (LOGIN; NOSUPERUSER NOCREATEDB NOCREATEROLE — least privilege) ------
--    Created without a password here; password set out-of-band from Secret Manager.
--    NO schema is created or owned by this role (dashboard owns zero tables, §0.8).
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'dashboard_user') THEN
    CREATE ROLE dashboard_user WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
  END IF;
END
$$;

-- Set the password from Secret Manager at bootstrap (run separately with -v):
-- ALTER ROLE dashboard_user WITH PASSWORD :'dashboard_user_pw';

-- 2. CROSS-SCHEMA AUDIT WRITE — R3 (handoff §1 I5 / §5; MASTER_PLAN §5.B) ------
--    *** THE BACKEND MERGE GATE DEPENDS ON THIS GRANT. ***
--    The vendored audit_mw / core/audit.py import-chain wires the audit-write API;
--    even though dashboard's read-only GET writes NO row at runtime (NONE audit
--    posture, §0.7), the role MUST be able to:
--      - resolve the public schema (USAGE), and
--      - INSERT into public.audit_events.
--    audit_events has NO FK and is append-only (MASTER_PLAN §5.B) → INSERT only;
--    NO SELECT/UPDATE/DELETE granted (least privilege — a service cannot read or
--    tamper with another service's audit rows).
GRANT USAGE ON SCHEMA public TO dashboard_user;
GRANT INSERT ON public.audit_events TO dashboard_user;

-- NOTE: NO `GRANT ... ON ALL TABLES IN SCHEMA <owned>` and NO ALTER DEFAULT
-- PRIVILEGES block here (contrast svc-export §3/§4) — dashboard owns no schema
-- and no tables. If the get_db-wired shared-read path ever needs SELECT on a
-- specific public table, add a tightly-scoped `GRANT SELECT ON public.<table>`
-- here (NOT a blanket schema grant). As of V1 the 2 outbound shims do their own
-- DB access on the CALLEE side (catalog/customer), so dashboard reads ~nothing
-- directly (§0.5 / §0.8).

-- Done. Verify with:
--   \du dashboard_user                 -- expect NOSUPERUSER, no schema owned
--   \dp public.audit_events            -- expect dashboard_user=a (INSERT) in the ACL
--   SELECT has_table_privilege('dashboard_user','public.audit_events','INSERT');  -- t
--   SELECT has_table_privilege('dashboard_user','public.audit_events','SELECT');  -- f
