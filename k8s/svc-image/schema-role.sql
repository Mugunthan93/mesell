-- k8s/svc-image/schema-role.sql
-- ===========================================================================
-- svc-image — Sub-Plan C (image extraction), INFRA deliverable I5.
--
-- Postgres SCHEMA + ROLE + GRANTS bootstrap for the image service.
-- Authority: handoff_msC_infra.md §1 I5 + MASTER_PLAN §2.D (schema-per-service)
--            + §5.B (shared public.audit_events, GRANT INSERT to every service)
--            + PR #197 / develop d4aa572 — §0.10 RULED **OPTION B** (ownership HTTP
--              shim, NO cross-schema products read-grant).
--
-- This is the infra-owned "step zero" bootstrap that runs against the shared
-- `meesell` database BEFORE svc-image's own Alembic chain runs (Alembic moves
-- `product_images` into the `image` schema via ALTER TABLE ... SET SCHEMA image;
-- this script creates the schema, the role, and the grants the role needs).
-- Coordinate apply-order with the database-builder lane (A1): the schema must
-- exist + be owned by image_user BEFORE the Alembic `SET SCHEMA image` runs.
--
-- ── HOW THIS RUNS ──────────────────────────────────────────────────────────
--   Applied once against the dev Postgres as a superuser (the `meesell` bootstrap
--   role) at deploy time:
--     kubectl exec postgres-0 -n dev -- psql -U meesell -d meesell -f - < schema-role.sql
--   It is IDEMPOTENT (IF NOT EXISTS / DO-block guards) — safe to re-run.
--
-- ── ROLE PASSWORD ──────────────────────────────────────────────────────────
--   The image_user password is NOT in this file (no secret in git — playbook §0).
--   It is set out-of-band from GCP Secret Manager at bootstrap, e.g.:
--     ALTER ROLE image_user WITH PASSWORD :'image_user_pw';   -- psql -v image_user_pw=...
--   and the SAME value is composed into svc-image's DATABASE_URL in the
--   svc-image-secrets k8s Secret (deliverable I7). The placeholder ALTER below is
--   commented; run it with the SM-sourced value, never a literal here.
--
-- ── CONNECTION / search_path ────────────────────────────────────────────────
--   svc-image connects with role image_user and DATABASE_URL carrying
--   `?options=-csearch_path%3Dimage,public` so its session sees `image` first
--   (its owned `product_images` table) and `public` (for audit_events). See I7.
--
-- ╔═══════════════════════════════════════════════════════════════════════════╗
-- ║ §0.10 OPTION B GRANT SURFACE — *** NO products READ-GRANT *** (RULED)      ║
-- ║                                                                           ║
-- ║ The repository scopes by product_id ALONE (the products JOIN is removed   ║
-- ║ per spec §0.3). Tenancy is proven UPSTREAM by the catalog                 ║
-- ║ `assert_product_ownership` HTTP shim BEFORE every repository call, NOT by ║
-- ║ a cross-schema DB read. Therefore image_user is granted:                  ║
-- ║   • USAGE + ownership on schema `image` (its own tables), AND             ║
-- ║   • INSERT on public.audit_events (the cross-schema AUDIT WRITE only).    ║
-- ║ image_user is granted NO access of any kind to public.products /          ║
-- ║ schema catalog. The transitional Option-A `GRANT SELECT ON public.products║
-- ║ TO image_user` is DISCARDED (never granted). This file MUST NOT contain   ║
-- ║ any products grant — the backend merge gate asserts its absence.          ║
-- ╚═══════════════════════════════════════════════════════════════════════════╝
-- ===========================================================================

-- 1. Schema -----------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS image;

-- 2. Role (LOGIN; NOSUPERUSER NOCREATEDB NOCREATEROLE — least privilege) ------
--    Created without a password here; password set out-of-band from Secret Manager.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'image_user') THEN
    CREATE ROLE image_user WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
  END IF;
END
$$;

-- Set the password from Secret Manager at bootstrap (run separately with -v):
-- ALTER ROLE image_user WITH PASSWORD :'image_user_pw';

-- 3. Schema ownership + usage -----------------------------------------------
--    image_user owns its schema so its Alembic chain can DDL (the
--    `ALTER TABLE product_images SET SCHEMA image`, version_table_schema=image)
--    without a separate migrator role. (Sub-Plan C keeps it simple — one role does
--    DDL + DML on its own schema. A dedicated image_migrator role is V2 hardening.)
ALTER SCHEMA image OWNER TO image_user;
GRANT USAGE ON SCHEMA image TO image_user;

-- 4. DML on all tables in `image` (current + future) -------------------------
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA image TO image_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA image
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO image_user;
-- Sequences (UUID PKs use gen_random_uuid() so sequences are unlikely, but grant
-- defensively for any SERIAL/identity columns Alembic might add).
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA image TO image_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA image
  GRANT USAGE, SELECT ON SEQUENCES TO image_user;

-- 5. CROSS-SCHEMA AUDIT WRITE — handoff §1 I5 / §5; MASTER_PLAN §5.B -----------
--    *** THE BACKEND MERGE GATE DEPENDS ON THIS GRANT. ***
--    The integration test asserts an `image.precheck.completed` audit row lands in
--    public.audit_events (worker-path direct ORM write, tasks.py — spec §0.5,
--    §15.E cross-schema exception). svc-image writes there via the vendored
--    AuditEvent model bound to {"schema":"public"}, so image_user MUST be able to:
--      - resolve the public schema (USAGE), and
--      - INSERT into public.audit_events.
--    audit_events has NO FK and is append-only (MASTER_PLAN §5.B) → INSERT only;
--    NO SELECT/UPDATE/DELETE granted (least privilege — a service cannot read or
--    tamper with another service's audit rows).
GRANT USAGE ON SCHEMA public TO image_user;
GRANT INSERT ON public.audit_events TO image_user;

-- 6. §0.10 OPTION B — *** DELIBERATELY NOT GRANTED *** ------------------------
--    (left here as an explicit, reviewable NEGATIVE assertion — do NOT uncomment)
--    -- GRANT SELECT ON public.products TO image_user;   <-- DISCARDED (Option A).
--    image_user has ZERO access to public.products / schema catalog. Tenancy is the
--    upstream assert_product_ownership shim's job. Revisit ONLY if a future ruling
--    reverses §0.10 — which would itself be a fresh founder decision.

-- Done. Verify with:
--   \dn image
--   \dp public.audit_events           -- expect image_user=a (INSERT) in the ACL
--   SELECT has_table_privilege('image_user','public.audit_events','INSERT');  -- t
--   SELECT has_table_privilege('image_user','public.products','SELECT');      -- f  (Option B)
