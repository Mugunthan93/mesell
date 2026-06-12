# SPEC — Microservices Sub-Plan B (`dashboard` extraction) — BACKEND code work

> **WORKTREE FALLBACK COPY.** The main-tree write to
> `/Users/mugunthansrinivasan/Project/mesell/.claude/agent-memory/meesell-backend-coordinator/spec_msB_backend.md`
> was BLOCKED by the bg-session worktree-isolation guard. This is the
> fallback copy under the docs worktree per the dispatch instruction. The
> session should relocate it to the main-tree memory dir.

**Session:** `mesell-ms-dashboard-session-1` (2026-06-12, HYBRID rule STEP 1 — SPEC only, no code, no git ops)
**Author:** meesell-backend-coordinator
**Plan basis:** `docs/plans/microservices_migration/MASTER_PLAN.md` (v1.3) + `SUB_PLAN_0B_dashboard_extraction.md` (authored this turn) + the SUB_PLAN_01 SHAPE TEMPLATE
**Execution gate:** **EXECUTION GATED — MS-2** (parallel with MS-C `image`). Phase 2 begins ONLY when (a) Sub-Plan A's founder gate is merged to `develop` AND (b) the validated MS-A extraction recipe exists in the lead's memory. Until both hold, do NOT dispatch the specialists below.

---

## 0. GROUND TRUTH — re-verified against SOURCE 2026-06-12 (worktree `/tmp/mesell-wt/msB-docs` @ `c859955`)

Full citation set lives in `SUB_PLAN_0B §0`. The load-bearing facts for the specialist dispatch:

- **Worktree TRUE tip = `c8599556cce073f4c38f8528ca578dd96105cfc1`** (= `c859955`), branch `docs/msB-subplan-0B`, == `origin/develop`. No divergence. Phase 2 cuts from `origin/develop` (re-verify live tip — develop moves past `c859955` once MS-A merges).
- **dashboard module = 6 files, NO `repository.py`** (deliberate §13.D deviation, `__init__.py:9-11`). Owns ZERO tables. `domain.py` is empty-but-legal (`__all__ = []`).
- **NO ai_ops, NO Celery, NO tasks.py** — dashboard is a pure read. svc-dashboard is api-only (NO worker pod, NO broker/result Valkey).
- **MOUNTED route inventory = exactly 1** (counted from `router.py` decorators, the row-26 lesson): `GET /api/v1/products` 200, `@rate_limit(scope="dashboard_list", limit=600, window=3600)` (router.py:86), `Depends(get_current_user)`+`Depends(get_db)`, `FEATURE_TRACKING_DASHBOARD_ENABLED` 404 guard (router.py:118). Mount: `main.py:43` import + `main.py:141` `app.include_router(dashboard_router)`.
- **2 cross-module call sites** in `dashboard/service.py`:
  - `:78` `catalog_service.list_products(user_id=user_id, pagination=pagination, db=db)` → `catalog/service.py:999` returns `PaginatedProductsInternal` (`catalog/domain.py:170`).
  - `:84` `customer_service.get_onboarding_completeness(user_id=user_id, db=db)` → `customer/service.py:682` returns `ProfileCompleteness` (`customer/domain.py:98`).
  - **PLAN-TEXT CORRECTION:** the method is `get_onboarding_completeness`, NOT the §1.C/plan-prose `get_profile_completeness`. A wrong name is a re-dispatch trigger.
- **dashboard is a LEAF CONSUMER** (zero inbound callers; only `main.py:43` imports it) → svc-dashboard exposes **NO `/internal/*`**. 2 outbound shims (catalog + customer), zero inbound.
- **A2/D7 applies:** vendor the 6-mw chain; plan_guard + audit present-but-INERT (dashboard is plan_guard-excluded per §13.I; audit NONE on read-only GET per §13.B). JWT LOCAL.
- **Test floor:** `def test_` full-suite = **698** in the worktree (develop moved past MS-A's 649); dashboard's own = **36**. Validation = MONOTONIC vs live baseline at PR time (re-count; do NOT hardcode 698 or 823).

---

## 1. Builder sequence (3-phase, per SUB_PLAN_01 §"Dispatch order")

```
PHASE A (parallel — no inter-dependency):
  meesell-database-builder → VERIFY-ONLY attestation (zero tables, no migration, no Alembic, no owned schema). TRIVIAL.
  [INFRA LANE — meesell-infra-builder, NOT a backend specialist — see handoff_msB_infra.md]

PHASE B (no schema dependency — dashboard owns no schema):
  meesell-services-builder  → extract service.py+domain.py+exceptions.py; 2-shim (catalog+customer) under core/extracted_clients/; vendor 3 callee dataclasses; trimmed Settings; standalone main.py (5-effective-mw, NO Celery)
  meesell-api-routes-builder→ extract router.py (1 route)+schemas.py; preserve rate_limit + FEATURE_TRACKING_DASHBOARD_ENABLED guard; NO /internal/*; regenerate OpenAPI
    (api-routes starts once services-builder freezes the single service signature — near-parallel within Phase B)

PHASE C (depends on B — integration; LEAD-owned, not specialist):
  meesell-backend-coordinator → hybrid-mode CI wiring (in-process + HTTP-shim per §3.A); test_dashboard_extraction.py; merge-gate review STEP 3; board MERGED flip
```

**Recommended dispatch order:** `database-builder` (Phase A VERIFY-ONLY — trivial) IN PARALLEL with the infra handoff → then `services-builder` (Phase B heavy lift) → then `api-routes-builder` (once the service signature is frozen) → then lead Phase C. Iteration cap 3 per specialist.

---

## 2. Branch plan (Model C — per SUB_PLAN_01 + MS-PAR-1 rule 6)

Cut from `origin/develop` (re-verify live tip at dispatch).

| Branch | Cut from | Purpose | Who commits |
|---|---|---|---|
| `feature/microservices-dashboard/integration` | `origin/develop` | Integration; merge commits only; F3 protection at creation | backend lead (merge approval) + founder (integration→develop gate) |
| `feature/microservices-dashboard/backend` | `…/integration` | All backend specialist extraction work | backend specialists |
| `feature/microservices-dashboard/infra` | `…/integration` | Dockerfile, K8s, Traefik route, ConfigMap flag, audit grant | meesell-infra-builder |

Worktrees `/tmp/mesell-wt/msB-*`. NEVER `git add -A` — scope every stage to `backend/services/svc-dashboard/`. **PR flow:** group → integration = LEAD gate (squash). integration → develop = **FOUNDER gate (left OPEN)** per D1.

**Parallel-lane discipline with MS-C image (MS-PAR-1 rule 4):** integration branch merges `origin/develop` BEFORE the founder-gate PR opens; shared-file edits (main.py mount removal, Traefik table) additive/keep-both; dashboard (`GET /api/v1/products`) and image (`/api/v1/products/{id}/images*`) touch DISJOINT path prefixes.

---

## 3. Per-specialist SPECs

### 3.A meesell-services-builder (opus) — the heavy lift

**TASK:** Extract `dashboard` service/domain/exceptions into `backend/services/svc-dashboard/app/`, rewire the 2 cross-module calls to HTTP shims, build standalone main.py + (NO Celery app).

**Files to CREATE (svc-dashboard tree):**
- `app/main.py` — standalone FastAPI; mounts dashboard router; registers 6-mw chain (plan_guard + audit INERT); `core/errors` handlers; `/health` + `/metrics`. **NO Celery app.**
- `app/service.py` — FROM `modules/dashboard/service.py`. Composition logic **byte-for-byte**; ONLY the import lines (service.py:36-42) change from `from app.modules.<callee> import service as <callee>_service` to `from app.core.extracted_clients import <callee>_client as <callee>_service` (re-export the SAME symbol so call sites at `:78`/`:84` are UNCHANGED per §16.G). Keep `_compose_response` a PURE function (no I/O, no await — §13.C).
- `app/domain.py` — FROM `modules/dashboard/domain.py`; empty-but-legal (`__all__ = []`), kept for subtree completeness.
- `app/exceptions.py` — FROM `modules/dashboard/exceptions.py` (`DashboardError` + `InvalidPaginationError`).
- `app/core/extracted_clients/catalog_client.py` — shim `list_products(user_id, pagination, db)` → `GET monolith-svc/internal/products?page&limit` (callee in-process during MS-2 → base URL = monolith ClusterIP). Vendors `PaginatedProductsInternal` + `Pagination` + `Product` dataclasses (`catalog/domain.py:170/219/35`).
- `app/core/extracted_clients/customer_client.py` — shim `get_onboarding_completeness(user_id, db)` → `GET monolith-svc/internal/seller-profile/{user_id}/onboarding-completeness`. Vendors `ProfileCompleteness` (`customer/domain.py:98`). **Method name = `get_onboarding_completeness`, NOT `get_profile_completeness`.**
- `app/shared/{database,config,valkey}.py` — vendored; TRIMMED Settings: `DATABASE_URL` (NO owned schema — mw/get_db wiring only), `VALKEY_URL`, `JWT_SECRET`, `FEATURE_TRACKING_DASHBOARD_ENABLED`, `APP_ENV` ONLY. **NO GEMINI/LANGFUSE/MSG91/RAZORPAY/GCS.** Very small pool (2–3 conns).
- `app/core/middleware/*` — vendored 6-mw chain.
- `app/i18n/messages_en.py` — vendored subset: `validation.dashboard.invalid_pagination` + `server.internal_error`.
- `requirements.txt` — fastapi, sqlalchemy, asyncpg, httpx, redis. **NO celery, NO openpyxl, NO gemini/langfuse.**

**ACCEPTANCE (merge-gate, I verify):**
- [ ] `git diff` of extracted `service.py` vs monolith shows ONLY the import-line changes (service.py:36-42) — ZERO changes to the 2 call sites (`:78`, `:84`). §16.G absolute contract.
- [ ] Both shims use `httpx.AsyncClient`, 5s read / 2s connect timeout, 1 retry on 503/504 only (§5.E), forward user JWT in `Authorization` + `X-Request-ID`, base URL = monolith ClusterIP.
- [ ] customer shim method is `get_onboarding_completeness`.
- [ ] Trimmed Settings carries NO gemini/langfuse/msg91/razorpay/GCS; DOES carry `FEATURE_TRACKING_DASHBOARD_ENABLED`.
- [ ] NO Celery app introduced.
- [ ] `_compose_response` remains a PURE function.
- [ ] PR template fully filled, no `<>` placeholders.

**RE-DISPATCH triggers:** call site changed beyond imports → §16.G + the 2-line list; shim missing JWT forward → §5.A; wrong customer method name → §0.5 of SUB_PLAN_0B; Celery app introduced → §0.3 "pure read"; AI dep introduced → §13.I "pure read".

### 3.B meesell-api-routes-builder (sonnet)

**TASK:** Move the 1 dashboard route + schemas into `backend/services/svc-dashboard/app/router.py` + `schemas.py`. Confirm NO `/internal/*` (dashboard has zero inbound callers).

**Files to CREATE:**
- `app/router.py` — FROM `modules/dashboard/router.py`. `prefix="/api/v1"`; `GET /products` 200 (preserve `@rate_limit(scope="dashboard_list", limit=600, window=3600)` + the `FEATURE_TRACKING_DASHBOARD_ENABLED` 404 guard BEFORE the service call). `async`, `Depends(get_current_user)` + `Depends(get_db)`, `page`/`limit` Query validators.
- `app/schemas.py` — FROM `modules/dashboard/schemas.py` (`DashboardQuery`, `ProductListItem`, `ProfileCompletenessSummary`, `DashboardResponse` — PRIVATE wire-shape).
- Regenerate standalone OpenAPI; the **mounted routes** are the inventory unit — confirm exactly 1 route mounts (row-26 lesson: count mounted APIRoute objects, not schema classes).

**ACCEPTANCE:** 1 route mounted; async; `Depends(get_current_user)`+`Depends(get_db)`; rate-limit decorator preserved; `FEATURE_TRACKING_DASHBOARD_ENABLED` 404 guard preserved BEFORE service call; NO business logic inlined (handler calls `list_products_for_dashboard` only); OpenAPI has 1 endpoint + 4 schemas; NO `/internal/*` route. PR template filled.

**RE-DISPATCH:** business logic inlined → §13.B "handlers call service methods only"; rate-limit/flag-guard dropped → re-cite router.py source; invented endpoint shape → re-cite router.py.

### 3.C meesell-database-builder (sonnet) — VERIFY-ONLY (B4), dispatch FIRST (trivial)

**TASK:** Confirm svc-dashboard owns ZERO tables. Author NO migration — dashboard has no owned schema (§13.D).

**Deliverable:** A one-line attestation for the merge gate: "svc-dashboard owns ZERO tables; NO model/migration/Alembic chain introduced; DATABASE_URL maps to NO owned schema (shared-session/get_db wiring only)."

**ACCEPTANCE:** attestation present; NO migration file created; NO model file created; NO Alembic chain rooted at a dashboard schema; single monolith head unchanged.

**RE-DISPATCH:** a migration/table/model was authored → re-dispatch quoting §13.D "owns ZERO tables" + B4.

---

## 4. Monolith-side strangler changes (LEAD-owned, NOT specialist; apply only AT cutover)
- `backend/app/modules/dashboard/` (6 files) — KEEP live until hybrid-mode CI green ≥7 days, THEN delete (§3.C). Both trees coexist during the window.
- `backend/app/main.py` — at cutover, remove the in-process `dashboard_router` mount (main.py:141; Traefik routes `GET /api/v1/products` to svc-dashboard). Until cutover, stays mounted. DISJOINT from MS-C image mount removal → keep-both on merge.
- **NO `workers/celery_app.py` change** — dashboard registers no Celery task (contrast svc-export).

---

## 5. Documentation deliverables (gate conditions — must land with the merge)
- svc-dashboard standalone OpenAPI (1 endpoint, 4 schemas).
- **Frozen `/internal/*` shim-contract section** — already authored inside `SUB_PLAN_0B` (2 endpoints: catalog `GET /internal/products`, customer `GET /internal/seller-profile/{user_id}/onboarding-completeness`). MS-E (customer) + MS-H (catalog) implement what is frozen.
- `BACKEND_ARCHITECTURE.md §13` amendment ("Extracted to svc-dashboard V1.5" note) — **§13 is LOCKED → FOUNDER APPROVAL REQUIRED** before this amendment lands (§7.3). Do NOT self-amend.
- `MASTER_PLAN.md §4 row B` annotation flip ("Sub-Plan B authored 2026-06-12; execution at MS-2") + the §1.C `get_profile_completeness` → `get_onboarding_completeness` correction (plan-prose fix; flag to founder).
- `docs/runbooks/svc-dashboard-rollback.md` (§3.C rollback specialized for dashboard).
- Hybrid-mode CI config note (NONE of dashboard's callees need standalone — during dashboard extraction the callees are in-process; shims point at monolith ClusterIP).

---

## 6. Validation (merge-gate, lead-owned)
- Full backend suite `def test_` count MONOTONIC vs live baseline at PR time (worktree = 698; re-count — do NOT hardcode 698 or 823).
- dashboard's own 36 tests green in BOTH the monolith (pre-flip) AND the extracted service (no-tunnel baseline: pure-function/contract subset green; infra-gated skips/errors documented per the auth-otp no-tunnel pattern).
- `ruff` clean on `backend/services/svc-dashboard/`.
- import-linter: svc-dashboard introduces NO domain→adapters edge (no adapters); no ai_ops edge (Contract 5 — dashboard never consumed ai_ops); dashboard's no-repository §13.D exception still allowlisted.
- Frozen `/internal/*` shim-contract section complete (2 methods, source-cited) — in SUB_PLAN_0B.
- Rollback runbook present (§3.C strangler-fig contract).
- **NO tautological tests (pricing lesson):** the hybrid-mode integration test asserts REAL behavior (a shim call forwards JWT + returns the callee's real `PaginatedProductsInternal`/`ProfileCompleteness` shape; the composed `DashboardResponse` maps fields correctly; empty inventory → 200 not 404), NOT `assert True`-class echoes.
- `FEATURE_TRACKING_DASHBOARD_ENABLED` 404 guard still fires in the extracted service.

---

## 7. Rollback (per MASTER_PLAN §3.C, specialized for dashboard)
1. Traefik IngressRoute for `GET /api/v1/products` → back to monolith ClusterIP.
2. `core/extracted_clients/<callee>_client.py` re-exports in-process `service.py` (1-line / 1-revert per §16.G).
3. **NO database rollback** (dashboard owns no schema — nothing to migrate back).
4. `kubectl delete deployment svc-dashboard`.
5. Re-run hybrid-mode CI in pure in-process mode; document root cause in runbook "Rollback Log".
Rollback allowed any time BEFORE Sub-Plan B declared complete (7-day green window). dashboard's rollback is the SIMPLEST of any service (no schema, no Celery, no inbound shims).

---

## 8. Constraints honored (from dispatch)
- dev cluster / dev namespace ONLY. svc-dashboard api 1 replica (NO worker), 50m/128Mi req — fits current node alongside monolith + svc-export + svc-image (MS-2). NO D3 VM change (fresh founder ask only at node-outgrow; if MS-2 deploy overflows the node, STOP + founder-ask). NO staging/prod. NO terraform beyond dev-scope (infra handoff flags anything bigger).
- Infra surfaces (Dockerfile, k8s, Traefik, ConfigMap flag, audit grant) = INFRA HANDOFF (`handoff_msB_infra.md`), NOT specialist work.
- PgBouncer (MS-DB-4) NOT a Sub-Plan-B blocker (dev/zero-traffic); dashboard owns no schema so its DB footprint is ~0.
- **EXECUTION GATED — MS-2:** do NOT dispatch until Sub-Plan A founder gate is merged to develop AND the MS-A recipe is in the lead's memory.
