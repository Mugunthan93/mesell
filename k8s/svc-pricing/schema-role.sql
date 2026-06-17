-- k8s/svc-pricing/schema-role.sql
-- ===========================================================================
-- svc-pricing — Sub-Plan D (pricing extraction), INFRA deliverable I5 (+ I9).
--
-- Postgres SCHEMA + ROLE + GRANTS bootstrap for the pricing service.
-- Authority: handoff_msD_infra.md §1 I5/I9 + MASTER_PLAN §2.D (schema-per-service)
--            + §5.B (shared public.audit_events, GRANT INSERT to every service)
--            + PR #197 / develop d4aa572 — §0.10 RULED **OPTION B** (ownership HTTP
--              shim, NO cross-schema products read-grant).
--
-- This is the infra-owned "step zero" bootstrap that runs against the shared
-- `meesell` database BEFORE svc-pricing's own Alembic chain runs. It creates the
-- schema, the role, and the grants the role needs.
-- Coordinate apply-order with the database-builder lane: the schema must exist +
-- be owned by pricing_user BEFORE the Alembic pricing chain runs.
--
-- ── HOW THIS RUNS (playbook Section 5 — PostgreSQL; applied via kubectl exec) ──
--   Applied once against the dev Postgres as a superuser (the `meesell` bootstrap
--   role) at the founder-gated cutover deploy time:
--     kubectl exec postgres-0 -n dev -- psql -U meesell -d meesell -f - < schema-role.sql
--   It is IDEMPOTENT (IF NOT EXISTS / DO-block guards) — safe to re-run.
--   *** NOT applied by this lane — Sub-Plan D is dev-namespace manifest work; the
--   actual apply happens at the founder-gated cutover (offline-authored here). ***
--
-- ── ROLE PASSWORD ──────────────────────────────────────────────────────────
--   The pricing_user password is NOT in this file (no secret in git — playbook §0/§10).
--   It is set out-of-band from GCP Secret Manager at bootstrap, e.g.:
--     ALTER ROLE pricing_user WITH PASSWORD :'pricing_user_pw';   -- psql -v pricing_user_pw=...
--   and the SAME value is composed into svc-pricing's DATABASE_URL in the
--   svc-pricing-secrets k8s Secret (deliverable I7). The placeholder ALTER below is
--   commented; run it with the SM-sourced value, never a literal here.
--   (Mirrors svc-export's dev-export-db-password / svc-image's dev-image-db-password.)
--
-- ── CONNECTION / search_path ────────────────────────────────────────────────
--   svc-pricing connects with role pricing_user and DATABASE_URL carrying
--   `?options=-csearch_path%3Dpricing,public` so its session sees `pricing` first
--   (its owned tables) and `public` (for audit_events). See I7.
--
-- ╔═══════════════════════════════════════════════════════════════════════════╗
-- ║ §0.10 OPTION B GRANT SURFACE — *** NO products READ-GRANT *** (I9, RULED)  ║
-- ║                                                                           ║
-- ║ pricing proves tenancy UPSTREAM via the catalog `assert_product_ownership`║
-- ║ HTTP shim (the §0.6 ownership shim, services-builder Phase B) BEFORE the  ║
-- ║ price-calc service call — NOT by a cross-schema DB read of public.products.║
-- ║ Therefore pricing_user is granted:                                        ║
-- ║   • USAGE + ownership on schema `pricing` (its own tables), AND            ║
-- ║   • INSERT on public.audit_events (the cross-schema AUDIT WRITE only).    ║
-- ║ pricing_user is granted NO access of any kind to public.products /        ║
-- ║ schema catalog. The transitional Option-A `GRANT SELECT ON public.products║
-- ║ TO pricing_user` (handoff I9) is DELIBERATELY NOT issued — see §6 below.   ║
-- ╚═══════════════════════════════════════════════════════════════════════════╝
-- ===========================================================================

-- 1. Schema -----------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS pricing;

-- 2. Role (LOGIN; NOSUPERUSER NOCREATEDB NOCREATEROLE — least privilege) ------
--    Created without a password here; password set out-of-band from Secret Manager.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'pricing_user') THEN
    CREATE ROLE pricing_user WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
  END IF;
END
$$;

-- Set the password from Secret Manager at bootstrap (run separately with -v):
-- ALTER ROLE pricing_user WITH PASSWORD :'pricing_user_pw';

-- 3. Schema ownership + usage -----------------------------------------------
--    pricing_user owns its schema so its Alembic chain can DDL (CREATE TABLE,
--    version_table_schema="pricing") without a separate migrator role. (Sub-Plan D
--    keeps it simple — one role does DDL + DML on its own schema. A dedicated
--    pricing_migrator role is V2 hardening.)
ALTER SCHEMA pricing OWNER TO pricing_user;
GRANT USAGE ON SCHEMA pricing TO pricing_user;

-- 4. DML on all tables in `pricing` (current + future) -----------------------
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA pricing TO pricing_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA pricing
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO pricing_user;
-- Sequences (UUID PKs use gen_random_uuid() so sequences are unlikely, but grant
-- defensively for any SERIAL/identity columns Alembic might add).
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA pricing TO pricing_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA pricing
  GRANT USAGE, SELECT ON SEQUENCES TO pricing_user;

-- 5. CROSS-SCHEMA AUDIT WRITE — handoff §1 I5 / §5; MASTER_PLAN §5.B -----------
--    *** THE BACKEND MERGE GATE DEPENDS ON THIS GRANT. ***
--    The @audit_event("pricing.calculated") decorator (pricing/router.py:76) writes
--    a cross-schema row to public.audit_events on 2xx (payload {product_id,
--    input_cost, mrp, profit_pct}). The integration test asserts that row lands.
--    svc-pricing writes there via the vendored AuditEvent model bound to
--    {"schema":"public"}, so pricing_user MUST be able to:
--      - resolve the public schema (USAGE), and
--      - INSERT into public.audit_events.
--    audit_events has NO FK and is append-only (MASTER_PLAN §5.B) → INSERT only;
--    NO SELECT/UPDATE/DELETE granted (least privilege — a service cannot read or
--    tamper with another service's audit rows).
GRANT USAGE ON SCHEMA public TO pricing_user;
GRANT INSERT ON public.audit_events TO pricing_user;

-- 6. I9 — TRANSITIONAL cross-schema SELECT — *** DELIBERATELY NOT GRANTED *** --
--    (left here as an explicit, reviewable NEGATIVE assertion — do NOT uncomment)
--    -- GRANT SELECT ON public.products TO pricing_user;   <-- OMITTED (handoff §1 I9).
--
--    CONDITION (handoff §1 I9): the PREFERRED §0.6 resolution is the catalog
--    `assert_product_ownership` /internal HTTP shim, which eliminates pricing's
--    public.products read ENTIRELY → this grant is NOT needed. pricing_user has ZERO
--    access to public.products / schema catalog.
--    ONLY add this grant IF the backend lead (services-builder Phase B) EXPLICITLY
--    confirms the §0.6 shim resolution did NOT land clean and pricing still performs
--    a direct cross-schema products read at MS-3. As of authoring, the shim is the
--    ruled path (§0.10 Option B, PR #197) → grant OMITTED. If later granted, it is
--    TRANSITIONAL — revoke when catalog extracts at MS-5.

-- Done. Verify with:
--   \dn pricing
--   \dp public.audit_events           -- expect pricing_user=a (INSERT) in the ACL
--   SELECT has_table_privilege('pricing_user','public.audit_events','INSERT');  -- t
--   SELECT has_table_privilege('pricing_user','public.audit_events','SELECT');  -- f
--   SELECT has_table_privilege('pricing_user','public.products','SELECT');      -- f  (Option B / I9 omitted)
-- ===========================================================================
