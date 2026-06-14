-- k8s/svc-iam/schema-role.sql
-- ===========================================================================
-- svc-iam — Sub-Plan G (iam extraction, THE AUTH AUTHORITY), INFRA deliverable I5.
--
-- Postgres SCHEMA + ROLE + GRANTS bootstrap for the iam service.
-- Authority: handoff_msG_infra.md §1 I5 + MASTER_PLAN §2.D (schema-per-service)
--            + §5.B (shared public.audit_events, GRANT INSERT to every service)
--            + SUB_PLAN_0G §0.7 (the `users` schema-move + 6-FK DROP — BACKEND owns
--              the MOVE migration; infra owns ONLY this schema/role/grant bootstrap).
--
-- This is the infra-owned "step zero" bootstrap that runs against the shared
-- `meesell` database BEFORE svc-iam's own Alembic chain runs. The schema-move
-- migration (backend database-builder, Phase A) moves the `users` table from `public`
-- INTO the `iam` schema (version_table_schema="iam") AND DROPs the residual cross-
-- schema FKs that reference users.id (SUB_PLAN_0G §0.7 — the 6-FK set, cross-checked
-- live via pg_constraint at execution; Risk #5 integrity pre-scan FIRST). This script
-- creates the schema, the role, and the grants the role needs so that migration (and
-- the running service) can operate.
--
-- *** SCOPE BOUNDARY — infra creates schema/role/grants ONLY ***
--   The `public.users → iam.users` SET SCHEMA move + the 6-cross-schema-FK DROP +
--   the Risk #5 integrity pre-scan + the tested downgrade are BACKEND
--   (meesell-database-builder) work, on the backend branch — NOT infra
--   (handoff §1 I5; SUB_PLAN_0G §0.7 "infra only creates the schema + role + grants").
--   This SQL is the bootstrap the backend migration runs ON TOP OF.
--
-- ── HOW THIS RUNS ──────────────────────────────────────────────────────────
--   Applied once against the dev Postgres as a superuser (the `meesell` bootstrap
--   role) at deploy time:
--     kubectl exec postgres-0 -n dev -- psql -U meesell -d meesell -f - < schema-role.sql
--   It is IDEMPOTENT (IF NOT EXISTS / DO-block guards) — safe to re-run.
--
-- ── ORDERING vs the schema-move migration (CRITICAL) ─────────────────────────
--   Run order at deploy: (1) THIS script — creates schema `iam` + role `iam_user` +
--   grants — THEN (2) the backend Alembic upgrade which does the public→iam `users`
--   SET SCHEMA move + the 6-FK DROP. The schema must exist (this script) before the
--   migration moves the table into it. The migration runs as the superuser/migrator
--   (it can SET SCHEMA + DROP CONSTRAINT across schemas); iam_user then owns DML on
--   the moved `users` table via the ALTER DEFAULT PRIVILEGES below + the explicit
--   ALL-TABLES grant. Re-run this script AFTER the migration too (idempotent) to pick
--   up the moved `users` table in the ALL TABLES grant.
--
-- ── ROLE PASSWORD ──────────────────────────────────────────────────────────
--   The iam_user password is NOT in this file (no secret in git — playbook §0).
--   It is set out-of-band from GCP Secret Manager at bootstrap, e.g.:
--     ALTER ROLE iam_user WITH PASSWORD :'iam_user_pw';   -- psql -v iam_user_pw=...
--   and the SAME value is composed into svc-iam's DATABASE_URL in the iam-svc-secrets
--   k8s Secret (deliverable I6). The placeholder ALTER below is commented; run it with
--   the SM-sourced value (NEW SM secret `dev-iam-db-password`, founder to create —
--   mirrors svc-export `dev-export-db-password`, svc-customer `dev-customer-db-password`).
--   Never a literal here.
--
-- ── CONNECTION / search_path ────────────────────────────────────────────────
--   svc-iam connects with role iam_user and DATABASE_URL carrying
--   `?options=-csearch_path%3Diam,public` so its session sees `iam` first (its owned
--   `users` table) and `public` (for the cross-schema audit_events INSERT). See I6.
-- ===========================================================================

-- 1. Schema -----------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS iam;

-- 2. Role (LOGIN; NOSUPERUSER NOCREATEDB NOCREATEROLE — least privilege) ------
--    Created without a password here; password set out-of-band from Secret Manager.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'iam_user') THEN
    CREATE ROLE iam_user WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
  END IF;
END
$$;

-- Set the password from Secret Manager at bootstrap (run separately with -v):
-- ALTER ROLE iam_user WITH PASSWORD :'iam_user_pw';

-- 3. Schema ownership + usage -----------------------------------------------
--    iam_user owns its schema so its Alembic chain can DDL (the alembic_version
--    table with version_table_schema="iam", and any future iam tables) without a
--    separate migrator role. (Sub-Plan G keeps it simple — one role does DDL + DML on
--    its own schema. A dedicated iam_migrator role is a V2 hardening, infra plan §3.2.)
--    NOTE: the schema-move migration moves the EXISTING `users` table into `iam`;
--    making iam_user the schema owner lets it manage that table.
ALTER SCHEMA iam OWNER TO iam_user;
GRANT USAGE ON SCHEMA iam TO iam_user;

-- 4. DML on all tables in `iam` (current + future) ---------------------------
--    Covers the `users` table once the schema-move migration lands it in `iam`, plus
--    any table the Alembic chain adds.
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA iam TO iam_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA iam
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO iam_user;
-- Sequences (UUID PKs use gen_random_uuid() so sequences are unlikely, but grant
-- defensively for any SERIAL/identity columns Alembic might add).
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA iam TO iam_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA iam
  GRANT USAGE, SELECT ON SEQUENCES TO iam_user;

-- 5. CROSS-SCHEMA AUDIT WRITE — §7.I direct-ORM path (handoff §1 I5 / §5;
--    MASTER_PLAN §5.B; SUB_PLAN_0G §0.4/§0.8) -------------------------------
--    *** THE BACKEND MERGE GATE DEPENDS ON THIS GRANT. ***
--    iam's §7.I direct-ORM audit path writes auth.login.success / auth.token.refreshed
--    / auth.logout rows to public.audit_events (service.py, the in-request audit
--    write). The integration test asserts an audit row lands on login/refresh/logout
--    (SUB_PLAN_0G acceptance). So iam_user MUST be able to:
--      - resolve the public schema (USAGE), and
--      - INSERT into public.audit_events.
--    audit_events has NO FK (its user_id FK to users.id is FK #1 in the §0.7 DROP set —
--    dropped by the schema-move migration) and is append-only (MASTER_PLAN §5.B) →
--    INSERT only; NO SELECT/UPDATE/DELETE granted (least privilege — iam cannot read
--    or tamper with another service's audit rows).
--    NOTE (§0.8 webhook gap, carried VERBATIM not fixed): the Razorpay webhook audit
--    write LOGS rather than INSERTs (audit_events.user_id is NOT NULL and the webhook
--    has no user_id → audit_event_id=0 placeholder). So in practice iam's audit INSERTs
--    fire on the 3 auth events, not on the webhook. The grant covers the auth-event
--    INSERTs; the webhook-log gap is a V1.5 resolution (nullable user_id or a
--    webhook_events table), out of extraction scope.
GRANT USAGE ON SCHEMA public TO iam_user;
GRANT INSERT ON public.audit_events TO iam_user;

-- ── NOTE: iam owns `users` — the principal IS the row (no scope_to_user) ──────
--   UNLIKE the other services (whose tables carry a user_id scoped to the authenticated
--   user), iam's `users` table IS the identity table — the principal is the row itself
--   (SUB_PLAN_0G "Validation": CI Contract 8 check_scope_to_user.py is N/A for `users`,
--   per repository.py:11-16). iam needs no cross-schema READ grant to any other service's
--   schema (it is all-✗ in the dependency matrix — §0.4). The ONLY cross-schema grant is
--   the audit INSERT above. iam reads/writes ONLY its own `iam.users` + appends to
--   `public.audit_events`.

-- Done. Verify with:
--   \dn iam
--   \dp public.audit_events           -- expect iam_user=a (INSERT) in the ACL
--   SELECT has_table_privilege('iam_user','public.audit_events','INSERT');  -- t
--   SELECT has_schema_privilege('iam_user','iam','USAGE');                  -- t
--   SELECT has_schema_privilege('iam_user','public','USAGE');               -- t
