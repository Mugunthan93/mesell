-- k8s/svc-customer/schema-role.sql
-- ===========================================================================
-- svc-customer — Sub-Plan E (customer extraction), INFRA deliverable I5.
--
-- Postgres SCHEMA + ROLE + GRANTS bootstrap for the customer service.
-- Authority: handoff_msE_infra.md §1 I5 + MASTER_PLAN §2.D (schema-per-service)
--            + §5.B (shared public.audit_events, GRANT INSERT to every service).
--
-- This is the infra-owned "step zero" bootstrap that runs against the shared
-- `meesell` database BEFORE svc-customer's own Alembic chain runs. The schema-split
-- migration a9f3b2c5e1d8 (backend PHASE A) moves the `seller_profile` table from
-- `public` INTO the `customer` schema (version_table_schema="customer", spec
-- _msE_backend.md:75) and DROPS the cross-schema FK seller_profile.user_id→users.id
-- (Risk #5). This script creates the schema, the role, and the grants the role
-- needs so that migration (and the running service) can operate.
--
-- ── HOW THIS RUNS ──────────────────────────────────────────────────────────
--   Applied once against the dev Postgres as a superuser (the `meesell` bootstrap
--   role) at deploy time:
--     kubectl exec postgres-0 -n dev -- psql -U meesell -d meesell -f - < schema-role.sql
--   It is IDEMPOTENT (IF NOT EXISTS / DO-block guards) — safe to re-run.
--   VERIFIED 2026-06-13: neither `customer` schema nor `customer_user` role exists
--   yet in dev, so this is a fresh create; the idempotent guards remain correct.
--
-- ── ORDERING vs the schema-split migration (CRITICAL) ────────────────────────
--   Run order at deploy: (1) THIS script — creates schema `customer` + role
--   `customer_user` + grants — THEN (2) the backend Alembic upgrade which does the
--   public→customer SET SCHEMA move. The schema must exist (this script) before the
--   migration moves the table into it. The migration runs as the superuser/migrator,
--   so it can SET SCHEMA; customer_user then owns DML on the moved table via the
--   ALTER DEFAULT PRIVILEGES below + the explicit ALL-TABLES grant (re-run this
--   script AFTER the migration too — idempotent — to pick up the moved table in the
--   ALL TABLES grant, or rely on the table being created/owned appropriately; the
--   defensive sequence-and-table grants cover both orderings).
--
-- ── ROLE PASSWORD ──────────────────────────────────────────────────────────
--   The customer_user password is NOT in this file (no secret in git — playbook §0).
--   It is set out-of-band from GCP Secret Manager at bootstrap, e.g.:
--     ALTER ROLE customer_user WITH PASSWORD :'customer_user_pw';   -- psql -v customer_user_pw=...
--   and the SAME value is composed into svc-customer's DATABASE_URL in the
--   customer-svc-secrets k8s Secret (deliverable I6). The placeholder ALTER below is
--   commented; run it with the SM-sourced value (NEW SM secret `dev-customer-db-password`,
--   founder to create — mirrors svc-export's `dev-export-db-password` and
--   svc-dashboard's `dev-dashboard-db-password`). Never a literal here.
--
-- ── CONNECTION / search_path ────────────────────────────────────────────────
--   svc-customer connects with role customer_user and DATABASE_URL carrying
--   `?options=-csearch_path%3Dcustomer,public` so its session sees `customer` first
--   (its owned `seller_profile` table) and `public` (for audit_events). See I6.
-- ===========================================================================

-- 1. Schema -----------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS customer;

-- 2. Role (LOGIN; NOSUPERUSER NOCREATEDB NOCREATEROLE — least privilege) ------
--    Created without a password here; password set out-of-band from Secret Manager.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'customer_user') THEN
    CREATE ROLE customer_user WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
  END IF;
END
$$;

-- Set the password from Secret Manager at bootstrap (run separately with -v):
-- ALTER ROLE customer_user WITH PASSWORD :'customer_user_pw';

-- 3. Schema ownership + usage -----------------------------------------------
--    customer_user owns its schema so its Alembic chain can DDL (the alembic_version
--    table with version_table_schema="customer", and any future customer tables)
--    without a separate migrator role. (Sub-Plan E keeps it simple — one role does
--    DDL + DML on its own schema. A dedicated customer_migrator role is a V2
--    hardening, infra plan §3.2.)
--    NOTE: the schema-split migration moves the EXISTING seller_profile table into
--    `customer`; making customer_user the schema owner lets it manage that table.
ALTER SCHEMA customer OWNER TO customer_user;
GRANT USAGE ON SCHEMA customer TO customer_user;

-- 4. DML on all tables in `customer` (current + future) ----------------------
--    Covers the seller_profile table once the schema-split migration lands it in
--    `customer`, plus any table the Alembic chain adds.
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA customer TO customer_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA customer
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO customer_user;
-- Sequences (UUID PKs use gen_random_uuid() so sequences are unlikely, but grant
-- defensively for any SERIAL/identity columns Alembic might add).
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA customer TO customer_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA customer
  GRANT USAGE, SELECT ON SEQUENCES TO customer_user;

-- 5. CROSS-SCHEMA AUDIT WRITE — R3 (handoff §1 I5 / §5; MASTER_PLAN §5.B) ------
--    *** THE BACKEND MERGE GATE DEPENDS ON THIS GRANT. ***
--    The 3 @audit_event PATCH routes (router.py:101 customer.profile_updated,
--    router.py:129 customer.active_categories.updated, router.py:158
--    customer.compliance_updated — SUB_PLAN_0E §0.4 routes 2/3/4) write an audit row
--    to public.audit_events via the shared core/audit.py API. The integration test
--    asserts an audit row lands on PATCH (spec_msE_backend.md:108 item (d)). So
--    customer_user MUST be able to:
--      - resolve the public schema (USAGE), and
--      - INSERT into public.audit_events.
--    audit_events has NO FK and is append-only (MASTER_PLAN §5.B) → INSERT only;
--    NO SELECT/UPDATE/DELETE granted (least privilege — a service cannot read or
--    tamper with another service's audit rows).
GRANT USAGE ON SCHEMA public TO customer_user;
GRANT INSERT ON public.audit_events TO customer_user;

-- ── NOTE: NO public.categories read-grant (E3-A / MASTER_PLAN §2.D) ──────────
--   customer's super_id validation (formerly SELECT DISTINCT super_id FROM
--   categories) is REPLACED by the E3-A HTTP shim (category_client →
--   category-svc/monolith GET /internal/super-categories) — SUB_PLAN_0E §3.
--   A cross-schema SQL read of `categories` is FORBIDDEN (§2.D). Therefore this
--   script DELIBERATELY does NOT grant customer_user any access to public.categories
--   or the category schema. The ONLY cross-schema grant is the audit INSERT above.

-- Done. Verify with:
--   \dn customer
--   \dp public.audit_events           -- expect customer_user=a (INSERT) in the ACL
--   SELECT has_table_privilege('customer_user','public.audit_events','INSERT');  -- t
--   SELECT has_schema_privilege('customer_user','customer','USAGE');             -- t
