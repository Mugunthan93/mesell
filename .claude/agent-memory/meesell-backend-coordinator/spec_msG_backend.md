# SPEC — Microservices Sub-Plan G (`iam` extraction) — BACKEND code work

**Session:** `mesell-ms-iam-session-1` (2026-06-12) — HYBRID rule STEP 1 (SPEC only, no code, no git ops, no dispatch)
**Author:** meesell-backend-coordinator
**Plan basis:** `docs/plans/microservices_migration/SUB_PLAN_0G_iam_extraction.md` + `MASTER_PLAN.md` v1.3 (§2.D, §3.B, §5.A A2/D7, §6 Risk #2)
**Execution gate:** PHASE 2 — GATED on Wave MS-3 complete (BOTH D pricing + E customer founder gates merged). Parallel partner MS-F (category).

> This is the hybrid STEP-2 spec the Phase-2 coding session pastes into specialist dispatches.
> NOT dispatched by this planning session. Iteration cap 3 per specialist; 3rd re-dispatch → founder consult.

---

## 0. GROUND TRUTH (re-verify at Phase-2 start — these are 2026-06-12 / develop `6d6ee51`)

- **iam module = 7 files** (NO tasks.py — no Celery). `backend/app/modules/iam/{__init__,domain,exceptions,repository,router,schemas,service}.py`.
- **6 MOUNTED routes** in `main.py:114` (`app.include_router(iam_router)`) → router.py decorators: `/auth/otp/send`(:105), `/auth/otp/verify`(:124), `/auth/refresh`(:152), `/auth/logout`(:194), `/auth/me`(:220), `/webhooks/razorpay`(:247). Count APIRoute objects, not schemas (row-26 lesson).
- **iam is ALL-✗** in the cross-module matrix → ZERO outbound shims, ZERO inbound `/internal/*`. iam's contract to other services = vendored `core/auth.py` + shared `JWT_SECRET`. MS-A froze NOTHING against iam (verified spec_msA §0.4).
- **`core/auth.py`** is the vendored-everywhere surface (import allowlist = `shared.*` + `core.errors` ONLY → cleanly vendorable). iam-svc is the only service that ALSO calls the issuance/rotation half from a route.
- **FE-D5 LIVE/FROZEN:** cookie Path `/api/v1/auth` (router.py:64), Domain `.mesell.xyz`, HttpOnly+Secure+SameSite=Strict (router.py:76-78); allowlist key `cache:refresh:v{N}:{hmac_sha256(token,pepper)}` (auth.py:370); dual-pepper read (auth.py:401-410); Lua rotation verbatim (auth.py:435-443).
- **6 cross-schema FKs to `users.id`** (DROP set — §0.7 of the sub-plan): audit_events(audit_event.py:54), seller_profile(:123 `fk_seller_profile_user_id`), catalogs(catalog.py:42), products(product.py:55), exports(export.py:48), product_drafts(:76 `fk_product_drafts_user_id`).
- **V1 gaps carried verbatim:** DPDP no-op (repository.py:91-99), webhook audit-log-not-row (service.py:597-632, returns audit_event_id=0).
- **Test count:** `grep -rn "def test_" backend/tests/` at start; assert MONOTONIC vs live baseline. Do NOT hardcode 823.

---

## 1. Builder sequence (3-phase)

```
PHASE A (parallel):
  meesell-database-builder → users schema-move (public→iam) + 6-FK DROP + Risk#5 pre-scan + tested downgrade
  [INFRA — meesell-infra-builder — handoff_msG_infra.md]

PHASE B (depends on A):
  meesell-services-builder  → repository/domain/exceptions + vendored shared/* + core/errors + 6-mw + core/metrics + i18n subset
                              (lands the scaffolding so auth-builder's main.py imports resolve)
  meesell-auth-builder      → THE HEAVY LIFT: service.py (6 methods) + core/auth.py byte-for-byte vendor
                              + MSG91/razorpay adapters + FE-D5 cookie/allowlist/dual-pepper + standalone main.py (6-mw)
  meesell-api-routes-builder→ router.py (6 routes + cookie helpers + rate-limit decorators) + schemas.py + OpenAPI
                              (once auth-builder freezes service signatures)

PHASE C (lead-owned):
  meesell-backend-coordinator → hybrid-mode CI; test_iam_extraction.py; merge-gate STEP 3; board MERGED
```

**Seam:** auth-builder owns `service.py` + `core/auth.py` vendor; services-builder owns repository/domain/exceptions + the REST of the vendored scaffolding. They must NOT both touch `core/auth.py`.

---

## 2. Branch plan (Model C)

Cut from `origin/develop` (live tip — re-verify `git ls-remote origin develop`).

| Branch | Cut from | Who commits |
|---|---|---|
| `feature/microservices-iam/integration` | `origin/develop` | backend lead (merge) + founder (integration→develop) |
| `feature/microservices-iam/backend` | `…/integration` | backend specialists |
| `feature/microservices-iam/infra` | `…/integration` | meesell-infra-builder |

Worktrees `/tmp/mesell-wt/msG-*`. NEVER `git add -A` — scope to `backend/services/svc-iam/`.
group→integration = LEAD squash gate; integration→develop = FOUNDER gate (left OPEN, lead does NOT approve, D1).
Shared-file discipline with MS-F: integration merges develop pre-gate; main.py removal additive-minimal; k8s/Traefik additive; union keep-both.

---

## 3. Paste-able specialist prompts

### 3.A meesell-auth-builder (opus) — the heavy lift

```
PROJECT BOUNDARY: project "mesell" at /Users/mugunthansrinivasan/Project/mesell (worktrees /tmp/mesell-wt/ included). DO NOT read/write outside.
SESSION: mesell-microservices-iam-backend-session-{N}

## Mandatory reads
- docs/plans/microservices_migration/SUB_PLAN_0G_iam_extraction.md (THIS plan — esp §0.4/§0.5/§0.6, Decisions G1/G2)
- docs/plans/microservices_migration/MASTER_PLAN.md §5.A (A2/D7 local-JWT lock) + §6 Risk #2
- backend/app/core/auth.py (the vendored-everywhere surface — ship BYTE-FOR-BYTE)
- backend/app/modules/iam/{service,router}.py (as-built — service.py 6 methods, router.py cookie helpers)
- .claude/agent-memory/meesell-auth-builder/MEMORY.md + .claude/agent-memory/meesell-backend-coordinator/auth_otp_feature.md

## Your mission
Extract `iam` into backend/services/svc-iam/. Move service.py (6 public methods) byte-for-byte.
VENDOR core/auth.py byte-for-byte (it is identical to every other service's copy; iam-svc is the
ONLY service that ALSO calls the issuance/rotation half — issue_access_token/issue_refresh_token/
rotate_refresh_token — from a route). Wire MSG91 + razorpay adapters. Build standalone main.py
with the FULL 6-mw chain (plan_guard_mw runs but is NO-OP for iam). Trimmed Settings.
The FE-D5 cookie/allowlist/dual-pepper contract is LIVE and FROZEN — ZERO drift.

## Acceptance (lead verifies at merge gate)
- [ ] `diff backend/services/svc-iam/app/core/auth.py backend/app/core/auth.py` == EMPTY (byte-identical vendor).
- [ ] Cookie helpers (_set_refresh_cookie/_clear_refresh_cookie): Path="/api/v1/auth", Domain=".mesell.xyz", secure/httponly/samesite=strict — byte-identical to router.py:68-93.
- [ ] Allowlist key derivation cache:refresh:v{N}:{hmac_sha256(token,pepper)} intact; dual-pepper read (current vN → fallback vN-1) intact; Lua rotation REFRESH_ROTATE_LUA verbatim.
- [ ] service.py 6 methods: pipeline byte-for-byte (iam imports NO other module — zero call-site rewrites); §7.I direct-ORM audit SAVEPOINT path preserved; DPDP no-op + webhook-log gaps preserved VERBATIM (do NOT fix).
- [ ] Trimmed Settings: HAS DATABASE_URL@iam, VALKEY_URL, JWT_SECRET+JWT_ALGORITHM, all FE-D5 fields, MSG91_*, RAZORPAY_* (incl RAZORPAY_WEBHOOK_SECRET), AUDIT_PII_SALT, CORS_*, APP_ENV. NO GEMINI/LANGFUSE/GCS.
- [ ] NO /internal/* route. NO Celery (no tasks.py, no celery_app). requirements.txt has NO gemini/langfuse/gcs/celery.
- [ ] PR template fully filled, no <> placeholders.

## Hard constraints
- DO NOT modify the monolith's backend/app/modules/iam/ or backend/app/core/auth.py (strangler — both coexist; core/auth.py STAYS the shared source-of-truth, never deleted).
- DO NOT invent an iam /internal/* endpoint (iam is all-✗ — §0.4). DO NOT add a per-request iam callback for token validation (A2/D7).
- DO NOT touch frontend/, k8s/, infra/ (infra lead owns manifests).
- DO NOT fix the DPDP or webhook V1 gaps (extraction preserves behavior).

## Files you MAY touch
backend/services/svc-iam/** ONLY.

## Final report
Files created (count+paths); `diff` result of core/auth.py vendor (target: EMPTY); cookie-attr confirmation; FE-D5 round-trip note; PR-template Test evidence block.
```
**Re-dispatch triggers:** core/auth.py drifted → quote §0.5 + A2/D7; /internal/* invented → §0.4; cookie Path changed → §0.6; gap "fixed" → §0.8.

### 3.B meesell-api-routes-builder (sonnet)

```
PROJECT BOUNDARY: project "mesell" at /Users/mugunthansrinivasan/Project/mesell. DO NOT read/write outside.
SESSION: mesell-microservices-iam-backend-session-{N}

## Mandatory reads
- docs/plans/microservices_migration/SUB_PLAN_0G_iam_extraction.md (esp §0.3 mounted-route table)
- backend/app/modules/iam/{router,schemas}.py (as-built — 6 routes, 7 schemas)

## Your mission
Move the 6 iam routes into backend/services/svc-iam/app/router.py + the 7 schemas into schemas.py.
Preserve the cookie helpers (_set_refresh_cookie/_clear_refresh_cookie) and rate-limit decorators
EXACTLY. Confirm NO /internal/* route (iam has zero inbound callers). Regenerate standalone OpenAPI.

## Acceptance
- [ ] 6 routes MOUNTED (count APIRoute objects in svc-iam main.py, not schema classes — row-26 lesson): otp/send 202, otp/verify 200+cookie, refresh 200+cookie, logout 204, me 200 (JWT), webhooks/razorpay 200 (HMAC).
- [ ] Rate-limit decorators preserved: otp_send 3/3600, otp_verify 10/3600, auth_refresh 60/3600; logout+me+webhook NONE.
- [ ] Handlers call iam_service methods only — no inlined business logic.
- [ ] OpenAPI: 6 endpoints + 7 schemas. NO /internal/* route.
- [ ] PR template filled.

## Hard constraints / MAY touch / must NOT touch
Same boundary as auth-builder; scoped to router.py + schemas.py. NO /internal/*. Do NOT touch the cookie Path.

## Final report
Mounted-route count (target 6); rate-limit decorator confirmation; OpenAPI endpoint/schema count; PR Test evidence.
```
**Re-dispatch:** route count ≠ 6 → §0.3; logic inlined → handlers-call-service rule; shape invented → re-cite router.py.

### 3.C meesell-services-builder (opus)

```
PROJECT BOUNDARY: project "mesell" at /Users/mugunthansrinivasan/Project/mesell. DO NOT read/write outside.
SESSION: mesell-microservices-iam-backend-session-{N}

## Mandatory reads
- docs/plans/microservices_migration/SUB_PLAN_0G_iam_extraction.md (Code surfaces table)
- backend/app/modules/iam/{repository,domain,exceptions}.py + backend/app/core/middleware/* + backend/app/shared/{config,valkey}.py

## Your mission
Extract repository.py + domain.py + exceptions.py into backend/services/svc-iam/app/. Vendor the
trimmed shared/{database,config,valkey}.py, core/errors.py, the 6-mw chain, core/metrics.py, and
the i18n messages_en.py SUBSET (only iam's validation_message_id strings + the 3 auth.token.* from
core/auth.py). Do NOT touch service.py or core/auth.py (auth-builder owns those).

## Acceptance
- [ ] repository.py bound to schema iam; DPDP no-op (repository.py:91-99) preserved VERBATIM.
- [ ] domain.py = 8 frozen dataclasses verbatim; exceptions.py = 9-class IamError hierarchy (3-segment validation_message_id).
- [ ] Trimmed Settings (per §Code-surfaces): NO GEMINI/LANGFUSE/GCS. valkey.py keeps DB 0 factory + load_lua_script/eval_lua_script.
- [ ] 6-mw chain vendored (plan_guard NO-OP for iam). core/metrics has AUTH_TOKEN_REFRESH_FAILED (used by service.py).
- [ ] i18n subset = iam's 9 + the 3 auth.token.* ONLY.
- [ ] PR template filled.

## Hard constraints
- DO NOT touch service.py or core/auth.py (auth-builder). DO NOT fix the DPDP gap.
- DO NOT touch the monolith iam module. DO NOT touch frontend/k8s/infra.

## Final report
Files created; Settings env-var list (confirm no GEMINI/LANGFUSE/GCS); DPDP-no-op preservation note; PR Test evidence.
```
**Re-dispatch:** §7.I audit path altered → re-cite service.py (but that's auth-builder's file — flag seam); DPDP fixed → §0.8.

### 3.D meesell-database-builder (sonnet) — Phase A, dispatch FIRST

```
PROJECT BOUNDARY: project "mesell" at /Users/mugunthansrinivasan/Project/mesell. DO NOT read/write outside.
SESSION: mesell-microservices-iam-backend-session-{N}

## Mandatory reads
- docs/plans/microservices_migration/SUB_PLAN_0G_iam_extraction.md (§0.7 the 6-FK DROP set)
- docs/plans/microservices_migration/MASTER_PLAN.md §2.D (schema-isolation + cross-schema-FK drop policy + Risk #5)
- backend/alembic/versions/935e55b4852c_v1_baseline_13_tables.py (lines 46/66/105/118/149/168/194)
- backend/app/shared/models/{user,audit_event,seller_profile,catalog,product,export,product_draft}.py
- .claude/agent-memory/meesell-database-builder/MEMORY.md (current head f31c75438e61)

## Your mission
Author the schema-move Alembic migration in backend/services/svc-iam/alembic/ moving `users` from
`public` to schema `iam`. Set version_table_schema="iam". Upgrade: ALTER TABLE users SET SCHEMA iam.
DROP the residual cross-schema FKs to users.id — the §0.7 set is 6 FKs, but waves MS-2/MS-3 may have
already dropped some during their own schema moves, so CROSS-CHECK LIVE:
  SELECT conname, conrelid::regclass FROM pg_constraint WHERE confrelid = 'users'::regclass;
and drop EXACTLY the residual cross-schema FKs (neither more nor less). Risk #5 integrity pre-scan
BEFORE any drop: verify every <table>.user_id resolves to a real users row; emit scan output to the
migration log. Tested downgrade: SET SCHEMA public + RESTORE the dropped FKs.

## Acceptance
- [ ] upgrade + downgrade round-trip clean locally.
- [ ] version_table_schema="iam" set; alembic_version lands in iam schema.
- [ ] dev applied BEFORE staging (NEVER reverse — head-divergence dev↔staging = P0 escalate).
- [ ] Risk #5 pre-scan output present in migration log; ZERO orphan user_id rows before drop.
- [ ] Exactly the residual cross-schema FKs to users dropped (pg_constraint cross-check documented in the migration comment).
- [ ] PR template filled.

## Hard constraints / MAY touch
backend/services/svc-iam/alembic/** + a migration file. Do NOT touch the monolith baseline migration.

## Final report
Migration file path; the live pg_constraint query result (which FKs were residual vs already-dropped); pre-scan orphan count; round-trip confirmation; PR Test evidence.
```
**Re-dispatch:** head divergence dev↔staging → P0 STOP escalate; FK over/under-drop → re-cite §0.7 + the pg_constraint query.

---

## 4. Validation floor (lead-owned merge gate) — Wave-6 LAW
- Full-suite `def test_` count MONOTONIC vs live baseline (quote at PR, no hardcode).
- iam tests green in BOTH monolith (pre-flip) AND svc-iam.
- 6 mounted routes in svc-iam main.py; NO /internal/*.
- `diff` core/auth.py vs monolith = EMPTY.
- FE-D5 round-trip test asserts REAL behavior (cookie Path, allowlist key rotation, cross-service local-validation) — NO tautologies (pricing lesson).
- ruff clean; import-linter no NEW violations; report TRUE branch tips.

## 5. Constraints honored
- dev cluster / dev namespace ONLY. iam-svc sizing fits current node at small footprint (api-only, no Celery, no XLSX/rembg). NO D3 VM ask unless the MS-4 wave deploy (iam + category + monolith remnant) overflows the node — then STOP and fresh founder ask.
- Infra surfaces = handoff_msG_infra.md (NOT specialist work).
- core/auth.py is NEVER deleted from the monolith (it stays the vendored source every service imports).
