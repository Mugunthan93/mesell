-- k8s/svc-category/schema-role.sql
-- ===========================================================================
-- svc-category — Sub-Plan F (category extraction, MS-4), INFRA deliverable I5.
--
-- Postgres SCHEMA + ROLE + GRANTS bootstrap for the category service.
-- Authority: handoff_msF_infra.md §4 (schema + role + the TWO grants)
--            + SUB_PLAN_0F §F3.c (cross-schema audit INSERT, F3.c)
--            + MASTER_PLAN §2.D (schema-per-service) + §5.B (shared
--              public.audit_events, GRANT INSERT to every service).
--
-- This is the infra-owned "step zero" bootstrap that runs against the shared
-- `meesell` database BEFORE svc-category's own Alembic chain runs. The schema-move
-- migration c4f1e7a9d302 (database-builder, db branch — verified at
-- origin/feature/microservices-category/db) moves the 4 GLOBAL category tables
-- (categories, templates, field_enum_values, field_aliases) from `public` INTO the
-- `category` schema via ALTER TABLE ... SET SCHEMA (version_table_schema="category").
-- This script creates the schema, the role, and the grants the role + that migration
-- need.
--
-- ── HOW THIS RUNS (playbook Section 5 — PostgreSQL; applied via kubectl exec) ──
--   Applied once against the dev Postgres as a superuser (the `meesell` bootstrap
--   role) at the founder-gated cutover deploy time:
--     kubectl exec postgres-0 -n dev -- psql -U meesell -d meesell -f - < schema-role.sql
--   It is IDEMPOTENT (IF NOT EXISTS / DO-block guards) — safe to re-run.
--   *** NOT applied by this lane — Sub-Plan F is dev-namespace manifest work; the
--   actual apply happens at the founder-gated cutover (offline-authored here). ***
--
-- ── ORDERING vs the schema-move migration (CRITICAL) ────────────────────────
--   Run order at deploy: (1) THIS script — creates schema `category` + role
--   `category_user` + grants — THEN (2) the backend Alembic upgrade c4f1e7a9d302
--   which does the 4× public→category SET SCHEMA moves. The schema must exist (this
--   script) before the migration moves the tables into it (the migration also emits
--   a belt-and-suspenders CREATE SCHEMA IF NOT EXISTS category, so either order is
--   safe). The migration runs as the superuser/migrator, so it can SET SCHEMA;
--   category_user then owns DML/DDL on the moved tables via the ALL-TABLES grant +
--   ALTER DEFAULT PRIVILEGES below. RE-RUN this script AFTER the migration too
--   (idempotent) to pick up the 4 moved tables in the ALL TABLES grant — or rely on
--   schema-ownership making category_user the implicit owner; the defensive
--   all-tables + default-privileges grants cover both orderings.
--
-- ── ROLE PASSWORD ──────────────────────────────────────────────────────────
--   The category_user password is NOT in this file (no secret in git — playbook
--   §0/§10). It is set out-of-band from GCP Secret Manager at bootstrap, e.g.:
--     ALTER ROLE category_user WITH PASSWORD :'category_user_pw';   -- psql -v category_user_pw=...
--   and the SAME value is composed into svc-category's DATABASE_URL in the
--   svc-category-secrets k8s Secret (deliverable I7). The placeholder ALTER below is
--   commented; run it with the SM-sourced value (NEW SM secret `dev-category-db-password`,
--   founder to create — mirrors svc-export's `dev-export-db-password`, svc-image's
--   `dev-image-db-password`, svc-pricing's `dev-pricing-db-password`,
--   svc-customer's `dev-customer-db-password`). Never a literal here.
--
-- ── CONNECTION / search_path ────────────────────────────────────────────────
--   svc-category connects with role category_user and DATABASE_URL carrying
--   `?options=-csearch_path%3Dcategory,public` so its session sees `category` first
--   (its owned categories/templates/field_enum_values/field_aliases tables) and
--   `public` (for audit_events). See I7.
--
-- ╔═══════════════════════════════════════════════════════════════════════════╗
-- ║ TABLES ARE READ-ONLY AT RUNTIME — but the role still needs DDL ownership.  ║
-- ║                                                                           ║
-- ║ The 4 category tables are READ-ONLY after seed (categories, templates,    ║
-- ║ field_enum_values, field_aliases) — the running service only SELECTs them.║
-- ║ HOWEVER category_user must OWN the `category` schema so that:              ║
-- ║   • the schema-move migration's alembic_version table                     ║
-- ║     (version_table_schema="category") can be created/written, AND          ║
-- ║   • any future Alembic DDL on the category schema runs without a separate  ║
-- ║     migrator role (Sub-Plan F keeps it simple — one role does DDL on its   ║
-- ║     own schema; a dedicated category_migrator is V2 hardening).            ║
-- ║ So the role gets full DML (incl. the read-only-at-runtime SELECT) + schema ║
-- ║ ownership. The "read-only" property is a runtime/app contract, not a       ║
-- ║ revoked-write DB grant (revoking write would break the Alembic chain).     ║
-- ╚═══════════════════════════════════════════════════════════════════════════╝
-- ===========================================================================

-- 1. Schema -----------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS category;

-- 2. Role (LOGIN; NOSUPERUSER NOCREATEDB NOCREATEROLE — least privilege) ------
--    Created without a password here; password set out-of-band from Secret Manager.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'category_user') THEN
    CREATE ROLE category_user WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
  END IF;
END
$$;

-- Set the password from Secret Manager at bootstrap (run separately with -v):
-- ALTER ROLE category_user WITH PASSWORD :'category_user_pw';

-- 3. Schema ownership + usage -----------------------------------------------
--    category_user owns its schema so the schema-move migration's alembic_version
--    table (version_table_schema="category") and any future DDL run without a
--    separate migrator role. The 4 moved tables (categories, templates,
--    field_enum_values, field_aliases) become category-schema objects; schema
--    ownership lets category_user manage them.
ALTER SCHEMA category OWNER TO category_user;
GRANT USAGE ON SCHEMA category TO category_user;

-- 4. DML on all tables in `category` (current + future) ----------------------
--    Covers the 4 read-only-at-runtime tables once the schema-move migration lands
--    them in `category`, plus any table the Alembic chain adds. SELECT is the
--    runtime privilege actually exercised (read-heavy, cache-fronted); INSERT/UPDATE/
--    DELETE are needed for the seed + migration path, not the running service.
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA category TO category_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA category
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO category_user;
-- Sequences (UUID PKs use gen_random_uuid() so sequences are unlikely, but grant
-- defensively for any SERIAL/identity columns Alembic might add).
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA category TO category_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA category
  GRANT USAGE, SELECT ON SEQUENCES TO category_user;

-- 5. CROSS-SCHEMA AUDIT WRITE — handoff §4 / §F3.c; MASTER_PLAN §5.B -----------
--    *** THE BACKEND MERGE GATE DEPENDS ON THIS GRANT. ***
--    category-svc's vendored cost_tracker.py writes every AI call's committed cost
--    to public.audit_events (the SHARED AI cost ledger — cost_tracker.py:55
--    `from app.shared.models.audit_event import AuditEvent`, the documented
--    direct-ORM-write exception, cost_tracker.py:250 "Drops on failure with
--    WARNING."). The smart_picker Gemini calls land their cost here. WITHOUT this
--    grant the budget brake's cost-ledger write silently drops (cost_tracker
--    drops-on-failure) — the ₹500 cap STILL enforces via the Valkey ai:cost:* keys
--    but the AUDIT TRAIL breaks (SUB_PLAN_0F §F3.c). So category_user MUST be able to:
--      - resolve the public schema (USAGE), and
--      - INSERT into public.audit_events.
--    audit_events has NO FK and is append-only (MASTER_PLAN §5.B) → INSERT only;
--    NO SELECT/UPDATE/DELETE granted (least privilege — a service cannot read or
--    tamper with another service's audit rows). Mirrors the export_user / pricing_user
--    / customer_user audit-INSERT grants (§5.B pattern).
GRANT USAGE ON SCHEMA public TO category_user;
GRANT INSERT ON public.audit_events TO category_user;

-- ── NOTE: NO cross-schema read-grant on other services' tables ──────────────
--   category is a CALLEE (it exposes /internal/* shims that OTHER services call); it
--   makes ZERO outbound DB reads into other schemas. So this script grants NO access
--   to public.products / public.catalogs / any other schema beyond the audit INSERT.
--   (The cross-schema FKs public.catalogs.category_id → category.categories.id and
--   public.products.category_id → category.categories.id remain valid after the move
--   — PostgreSQL supports cross-schema FKs in the same DB — but they do NOT require a
--   grant TO category_user; they are FKs FROM the public-schema tables, owned by the
--   catalog/monolith role.)

-- Done. Verify with:
--   \dn category
--   \dp public.audit_events           -- expect category_user=a (INSERT) in the ACL
--   SELECT has_table_privilege('category_user','public.audit_events','INSERT'); -- t
--   SELECT has_table_privilege('category_user','public.audit_events','SELECT'); -- f
--   SELECT has_schema_privilege('category_user','category','USAGE');            -- t
--   SELECT has_schema_privilege('category_user','public','USAGE');              -- t
-- ===========================================================================
