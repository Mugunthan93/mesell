-- k8s/svc-catalog/schema-role.sql
-- ===========================================================================
-- svc-catalog — Sub-Plan H (catalog extraction, MS-5), INFRA deliverable I5.
--
-- THE SPINE. Postgres SCHEMA + ROLE + GRANTS bootstrap for the catalog service.
-- Authority: handoff_msH_infra.md §4 (schema + role + the audit grant covering
--            TWO writers + the cross-schema FK note Risk #5)
--            + SUB_PLAN_0H_catalog_extraction.md (DB-tables-owned: 3 spine tables;
--              §H3.c cost_tracker audit write; the 4 write-route audit_mw rows)
--            + MASTER_PLAN §2.D (schema-per-service) + §5.B (shared
--              public.audit_events, GRANT INSERT to every service).
--
-- This is the infra-owned "step zero" bootstrap that runs against the shared
-- `meesell` database BEFORE svc-catalog's own Alembic chain runs. The schema-move
-- migration a8f3b2e9c1d5 (database-builder, db branch — verified at
-- origin/feature/microservices-catalog/db) moves the 3 TENANT-SCOPED catalog
-- tables (catalogs, products, product_drafts) from `public` INTO the `catalog`
-- schema via ALTER TABLE ... SET SCHEMA (version_table_schema="catalog", env.py).
-- This script creates the schema, the role, and the grants the role + that
-- migration need.
--
-- ── HOW THIS RUNS (playbook Section 5 — PostgreSQL; applied via kubectl exec) ──
--   Applied once against the dev Postgres as a superuser (the `meesell` bootstrap
--   role) at the founder-gated cutover deploy time:
--     kubectl exec postgres-0 -n dev -- psql -U meesell -d meesell -f - < schema-role.sql
--   It is IDEMPOTENT (IF NOT EXISTS / DO-block guards) — safe to re-run.
--   *** NOT applied by this lane — Sub-Plan H is dev-namespace manifest work; the
--   actual apply happens at the founder-gated cutover (offline-authored here). ***
--
-- ── ORDERING vs the schema-move migration (CRITICAL) ────────────────────────
--   Run order at deploy: (1) THIS script — creates schema `catalog` + role
--   `catalog_user` + grants — THEN (2) the backend Alembic upgrade a8f3b2e9c1d5
--   which does the 3× public→catalog SET SCHEMA moves. The schema must exist (this
--   script) before the migration moves the tables into it (the migration also emits
--   a belt-and-suspenders CREATE SCHEMA IF NOT EXISTS catalog, so either order is
--   safe). The migration runs as the superuser/migrator (it uses SET SCHEMA which
--   needs ownership AND runs the Risk#5 orphan pre-scan); catalog_user then owns
--   DML/DDL on the moved tables via the ALL-TABLES grant + ALTER DEFAULT PRIVILEGES
--   below. RE-RUN this script AFTER the migration too (idempotent) to pick up the 3
--   moved tables in the ALL TABLES grant — or rely on schema-ownership making
--   catalog_user the implicit owner; the defensive all-tables + default-privileges
--   grants cover both orderings.
--
-- ── MERGE ORDER (founder — from the migration docstring) ─────────────────────
--   SAFE: (1) iam PR #220 (users → iam, drops the user FK objects), (2) category
--   PR #221 (categories → category), (3) catalog MS-5 (this — moves the 3 spine
--   tables). The schema-move on the 3 catalog tables is orthogonal to the iam FK
--   drops + the category move; cross-schema FKs survive (PG supports them). Catalog
--   DROPS NO FK in the migration.
--
-- ── ROLE PASSWORD ──────────────────────────────────────────────────────────
--   The catalog_user password is NOT in this file (no secret in git — playbook
--   §0/§10). It is set out-of-band from GCP Secret Manager at bootstrap, e.g.:
--     ALTER ROLE catalog_user WITH PASSWORD :'catalog_user_pw';   -- psql -v catalog_user_pw=...
--   and the SAME value is composed into svc-catalog's DATABASE_URL in the
--   svc-catalog-secrets k8s Secret (deliverable I7). The placeholder ALTER below is
--   commented; run it with the SM-sourced value (NEW SM secret `dev-catalog-db-password`,
--   founder to create — mirrors svc-export's `dev-export-db-password`, svc-image's
--   `dev-image-db-password`, svc-pricing's `dev-pricing-db-password`,
--   svc-customer's `dev-customer-db-password`, svc-category's `dev-category-db-password`,
--   svc-iam's `dev-iam-db-password`). Never a literal here.
--
-- ── CONNECTION / search_path ────────────────────────────────────────────────
--   svc-catalog connects with role catalog_user and DATABASE_URL carrying
--   `?options=-csearch_path%3Dcatalog,public` so its session sees `catalog` first
--   (its owned catalogs/products/product_drafts tables) and `public` (for
--   audit_events). See I7.
--
-- ╔═══════════════════════════════════════════════════════════════════════════╗
-- ║ CATALOG IS READ-WRITE — full DML, not read-only.                          ║
-- ║                                                                           ║
-- ║ UNLIKE svc-category (whose 4 tables are read-only-at-runtime), catalog's   ║
-- ║ 3 spine tables are MUTATED on the hot path:                                ║
-- ║   • catalogs        — create_product / soft_delete                         ║
-- ║   • products        — create / patch(autosave) / autofill / soft_delete    ║
-- ║   • product_drafts  — patch_product autosave upsert (synchronous)          ║
-- ║ So catalog_user genuinely exercises INSERT/UPDATE/DELETE at runtime (not    ║
-- ║ just for the migration). It ALSO owns the `catalog` schema so the          ║
-- ║ schema-move migration's alembic_version table                              ║
-- ║ (version_table_schema="catalog") + future DDL run without a separate        ║
-- ║ migrator role (Sub-Plan H keeps it simple — a dedicated catalog_migrator    ║
-- ║ is V2 hardening).                                                          ║
-- ╚═══════════════════════════════════════════════════════════════════════════╝
-- ===========================================================================

-- 1. Schema -----------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS catalog;

-- 2. Role (LOGIN; NOSUPERUSER NOCREATEDB NOCREATEROLE — least privilege) ------
--    Created without a password here; password set out-of-band from Secret Manager.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'catalog_user') THEN
    CREATE ROLE catalog_user WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
  END IF;
END
$$;

-- Set the password from Secret Manager at bootstrap (run separately with -v):
-- ALTER ROLE catalog_user WITH PASSWORD :'catalog_user_pw';

-- 3. Schema ownership + usage -----------------------------------------------
--    catalog_user owns its schema so the schema-move migration's alembic_version
--    table (version_table_schema="catalog") and any future DDL run without a
--    separate migrator role. The 3 moved tables (catalogs, products,
--    product_drafts) become catalog-schema objects; schema ownership lets
--    catalog_user manage them.
ALTER SCHEMA catalog OWNER TO catalog_user;
GRANT USAGE ON SCHEMA catalog TO catalog_user;

-- 4. DML on all tables in `catalog` (current + future) -----------------------
--    Covers the 3 READ-WRITE spine tables once the schema-move migration lands
--    them in `catalog`, plus any table the Alembic chain adds. ALL of
--    SELECT/INSERT/UPDATE/DELETE are exercised AT RUNTIME (catalog is read-write:
--    create/patch/autosave/soft_delete mutate products/catalogs/product_drafts).
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA catalog TO catalog_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA catalog
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO catalog_user;
-- Sequences (UUID PKs use gen_random_uuid() so sequences are unlikely, but grant
-- defensively for any SERIAL/identity columns Alembic might add).
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA catalog TO catalog_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA catalog
  GRANT USAGE, SELECT ON SEQUENCES TO catalog_user;

-- 5. CROSS-SCHEMA AUDIT WRITE — handoff §4 / §H3.c; MASTER_PLAN §5.B ----------
--    *** THE BACKEND MERGE GATE DEPENDS ON THIS GRANT. ***
--    *** ONE GRANT COVERS TWO WRITERS (handoff §4): ***
--      (a) the vendored cost_tracker.py AI committed-cost write — every autofill
--          Gemini call's cost lands in public.audit_events (the SHARED AI cost
--          ledger; cost_tracker drops-on-failure with WARNING — without the grant
--          the ₹500 cap STILL enforces via the Valkey ai:cost:* keys but the AI
--          AUDIT TRAIL breaks), AND
--      (b) the audit_mw write-route audit rows for the 4 WRITE routes
--          (catalog.product.created / .updated / .deleted + catalog.autofill.invoked).
--    Both write to public.audit_events; this ONE grant covers both. catalog is the
--    FIRST service whose audit grant carries BOTH an AI-cost writer AND a
--    write-route audit_mw writer (svc-category had only the AI-cost writer; the
--    leaf consumers had only audit_mw). audit_events has NO FK and is append-only
--    (MASTER_PLAN §5.B) → INSERT only; NO SELECT/UPDATE/DELETE (least privilege — a
--    service cannot read or tamper with another service's audit rows). Mirrors the
--    export_user / pricing_user / customer_user / category_user / iam_user
--    audit-INSERT grants (§5.B pattern).
GRANT USAGE ON SCHEMA public TO catalog_user;
GRANT INSERT ON public.audit_events TO catalog_user;

-- 6. CROSS-SCHEMA FK RESOLUTION (Risk #5 — handoff §4) ------------------------
--    catalog's 3 tables carry cross-schema FK columns that survive the move
--    (catalog DROPS NO FK — migration a8f3b2e9c1d5 docstring):
--      catalog.catalogs.user_id      → users.id      (public → iam.users post #220)
--      catalog.catalogs.category_id  → categories.id (public → category.categories post #221)
--      catalog.products.user_id      → users.id
--      catalog.products.category_id  → categories.id
--      catalog.product_drafts.user_id→ users.id
--    NOTE on grants for FK targets: a FK constraint check at INSERT/UPDATE time
--    requires the writing role to have REFERENCES privilege OR (in practice for
--    PostgreSQL) only SELECT is needed for the existence check is NOT required —
--    PostgreSQL performs the FK integrity check with the privileges of the table
--    OWNER of the referencing table, executed internally, so catalog_user does NOT
--    need a grant on iam.users / category.categories to satisfy the FK at write
--    time. *** However *** the role's SESSION must be able to RESOLVE the schema
--    that holds the referenced tables for the planner — so we grant USAGE on the
--    schema(s) holding `users` and `categories` IF they have been extracted. These
--    grants are IDEMPOTENT + GUARDED: they only fire if the iam / category schema
--    exists at apply time (post #220 / #221). If users/categories are still in
--    `public` at apply time, the public USAGE grant above already covers it.
--    (Coordinate with iam's MS-4 schema grants per handoff §4 — iam_user owns the
--    iam schema; catalog_user needs only USAGE to resolve the FK target schema.)
DO $$
BEGIN
  IF EXISTS (SELECT FROM pg_catalog.pg_namespace WHERE nspname = 'iam') THEN
    EXECUTE 'GRANT USAGE ON SCHEMA iam TO catalog_user';
  END IF;
  IF EXISTS (SELECT FROM pg_catalog.pg_namespace WHERE nspname = 'category') THEN
    EXECUTE 'GRANT USAGE ON SCHEMA category TO catalog_user';
  END IF;
END
$$;

-- ── NOTE: NO cross-schema READ-grant on other services' DATA tables ─────────
--   catalog makes outbound calls to category-svc (×3) + customer-svc (×2) over
--   HTTP (the /internal/* shims, the §H5 caller side) — NOT via direct
--   cross-schema DB reads. So this script grants catalog_user NO SELECT on
--   iam.users / category.categories / customer.* tables. The USAGE grants in
--   step 6 are ONLY to resolve the FK-target schema for the planner, NOT to read
--   those tables. (The cross-schema FKs are FROM catalog's tables; FK enforcement
--   runs with the referencing-table owner's privileges internally.)

-- Done. Verify with:
--   \dn catalog
--   \dp public.audit_events           -- expect catalog_user=a (INSERT) in the ACL
--   SELECT has_table_privilege('catalog_user','public.audit_events','INSERT'); -- t
--   SELECT has_table_privilege('catalog_user','public.audit_events','SELECT'); -- f
--   SELECT has_schema_privilege('catalog_user','catalog','USAGE');             -- t
--   SELECT has_schema_privilege('catalog_user','public','USAGE');              -- t
--   -- after the schema move, the 3 spine tables are read-write:
--   SELECT has_table_privilege('catalog_user','catalog.products','UPDATE');     -- t
-- ===========================================================================
