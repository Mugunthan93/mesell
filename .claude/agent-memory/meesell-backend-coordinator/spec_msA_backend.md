# SPEC — Microservices Sub-Plan A (`export` extraction) — BACKEND code work

**Session:** `mesell-ms-export-spec-session-1` (2026-06-12)
**Author:** meesell-backend-coordinator (HYBRID rule STEP 1 — SPEC only, no code, no git ops)
**Plan basis:** `docs/plans/microservices_migration/MASTER_PLAN.md` (v1.3 — §3.A.1 dev-complete start condition NOW SATISFIED) + `SUB_PLAN_01_export_extraction.md` (A1/A2 LOCKED)
**Execution gate:** dev-complete DECLARED 2026-06-12; founder "ms go" in force. This is the first extraction (MASTER_PLAN §3.B order position 1).

---

## 0. GROUND TRUTH — re-verified against source 2026-06-12 (NOT the 2026-06-10 plan text)

The plan was authored against an older develop. I re-verified everything against the live tree. **Findings (all cited file:line):**

### 0.1 Branch / tree state — ACT ON THIS FIRST
- **origin/develop tip = `afea672`** (PR #178 — the rekey; carries MASTER_PLAN §3.A.1 + v1.3). Confirmed via `git ls-remote origin develop`.
- **Local `develop` HEAD = `f23d84a`** is a DIVERGED local-only commit (`docs(memory): ui-styler …`) that is NOT an ancestor of `afea672` and does NOT contain §3.A.1. The local working-tree MASTER_PLAN.md is the PRE-rekey v1.2 text.
- **CONSEQUENCE for the coding session:** cut all branches from **`origin/develop` (`afea672`)**, NOT local `develop`. Do `git fetch origin && git checkout -b feature/microservices-export/integration origin/develop`. Do NOT branch off local `f23d84a`. (The local divergence is a master-tree hygiene matter; flag to founder but it does not block — just use origin as the cut point.)

### 0.2 Export module = 8 files — CONFIRMED
`backend/app/modules/export/`: `__init__.py`, `domain.py`, `exceptions.py`, `repository.py`, `router.py`, `schemas.py`, `service.py`, `tasks.py` = 8 files (plan's "8 files" confirmed exactly).

### 0.3 A1 (export has NO ai_ops dep) — CONFIRMED
`grep -rn "ai_ops" backend/app/modules/export/` = **ZERO refs.** Export is deterministic. The svc-export `requirements.txt` carries NO gemini/langfuse. A1 (ai_ops vendored only into AI-consuming services) does not touch export.

### 0.4 The 6 cross-module call sites — RE-CITED FROM SOURCE (plan mis-named 2 of them)
Authoritative list of every `<callee>_service.<method>` invocation in `backend/app/modules/export/service.py`:

| # | Call site (export/service.py) | Callee method (signature cited from callee source) | Returns |
|---|---|---|---|
| 1 | `:174` `catalog_service.assert_product_ownership(product_id, user_id, db=db)` | `catalog/service.py:919` `assert_product_ownership(product_id: UUID, user_id: UUID, db: AsyncSession) -> None` | None (raises ProductNotFoundError) |
| 2 | `:177` + `:314` `catalog_service.get_product_for_export(...)` | `catalog/service.py:943` `get_product_for_export(product_id: UUID, user_id: UUID, db: AsyncSession) -> ExportSnapshotInternal` | frozen ExportSnapshotInternal |
| 3 | `:452` `category_service.fetch_schema(category_id, db=db)` | `category/service.py:467` `fetch_schema(category_id: UUID, db: AsyncSession) -> dict` | §5A.B envelope dict |
| 4 | `:659` `category_service.get_field_enum(...)` | `category/service.py:491` `get_field_enum(category_id: UUID, field_name: str, db: AsyncSession) -> dict[str, Any]` | enum payload dict (single_flight) |
| 5 | `:503` `customer_service.get_compliance_block(user_id, db)` | `customer/service.py:648` `get_compliance_block(user_id: UUID, db: AsyncSession) -> ComplianceBlock` | ComplianceBlock dataclass |
| 6 | `:185` `image_service.list_images(user_id, product_id, db=db)` | `image/service.py:232` `list_images(user_id: UUID, product_id: UUID, *, db: AsyncSession) -> ImagesListResponse` | ImagesListResponse (signed GCS URLs, 1h TTL) |

**PLAN-TEXT CORRECTIONS (Wave-6 no-invented-shapes discipline):**
- The plan's shim list says **`image.get_image_bytes`** and **`category.fetch_xlsx_aliases`**. BOTH ARE WRONG against source:
  - Export calls **`image.list_images`** (service.py:185), NOT `get_image_bytes`. `get_image_bytes` exists (image/service.py:319) but export does not call it. The export pipeline consumes image **refs/signed-URLs** from `list_images`, not raw bytes.
  - Export NEVER calls `fetch_xlsx_aliases`. `grep fetch_xlsx_aliases backend/app/modules/export/` = 0 runtime calls; the only ref is a **comment** (service.py:720) noting `field_aliases.for_xlsx_export=TRUE` rows are consumed **at SEED time**, not via a runtime category service call. So the export-side shim count is **6 distinct methods across 4 callees = catalog(2) + category(2) + customer(1) + image(1)** — NOT a separate `fetch_xlsx_aliases` shim.
- ADDITIONAL domain-import (NOT a service call, no shim): `export/domain.py:49` `from app.modules.customer.domain import ComplianceBlock` — this is the §16 "domain exchange currency" pattern. In the extracted service it becomes a **vendored copy** of the ComplianceBlock dataclass shape (the HTTP shim deserializes customer-svc's JSON into the local ComplianceBlock), NOT an HTTP call.

### 0.5 Celery task — CONFIRMED
`export/tasks.py:41` `@shared_task(name="export.xlsx", ...)`; `export_xlsx_task` runs `asyncio.run(_run_export_pipeline(export_uuid, user_uuid))`; direct ORM audit writes for `export.completed` (after orchestrator returns) / `export.failed` (final retries-exhausted) via a `_write_audit` helper (tasks.py:132).

### 0.6 Router — CONFIRMED
`export/router.py:83` `APIRouter(prefix="/api/v1", tags=["export"])`; 2 routes:
- `:90` `POST /products/{product_id}/export-xlsx` → 202, `response_model=ExportInitiatedResponse`, `@rate_limit(scope="export_initiate", limit=10, window=3600)` (router.py:102), `Depends(get_current_user)` + `Depends(get_db)`.
- `:136` `GET /exports/{export_id}` → 200, `response_model=ExportResponse`, NO `@rate_limit` (per-IP only floor per §14.J), `Depends(get_current_user)` + `Depends(get_db)`.
NOTE the exact path is `/products/{product_id}/export-xlsx` (param name `product_id`, not the plan's `{id}`).

### 0.7 A2 (middleware vendored, local JWT) — applies; export uses 5 of 6
export-svc vendors the 6-mw chain (CORS → request_id → auth_mw → tenancy_mw → rate_limit_mw → plan_guard_mw → audit_mw). `plan_guard_mw` RUNS but is NO-OP for export (export participates in no plan_guard resource per §14.A). JWT verified LOCALLY via vendored `core/auth.py` + shared `JWT_SECRET`.

### 0.8 D5 / PgBouncer sequencing — dev-scope read
Infra plan §3.2 / §6.3 (APPROVED v1.1): **MS-DB-3** (per-service pool right-size in code + `max_connections=200`) ships BEFORE any service moves. **MS-DB-4** (PgBouncer transaction-pool) is **mandatory before traffic-bearing PROD cutover** — NOT before a dev extraction. Since Sub-Plan A is **dev-only / zero-traffic**, the extraction code may proceed IN PARALLEL with MS-DB-3; PgBouncer (MS-DB-4) is NOT a Sub-Plan-A blocker. svc-export's own pool is SMALL (worker-heavy, not query-heavy). The PgBouncer-async caveat (`pool_pre_ping=False`, `executemany_mode='values_only'`) is an infra-lane concern flagged in the infra handoff, not specialist code work here.

### 0.9 Test count — re-counted (prompt said "823+"; actual is lower)
`grep -rn "def test_" backend/tests/` = **649** test functions. Export's own = **42** (`tests/modules/export/` + `tests/integration/test_export_*.py`). The "823+" figure in the dispatch prompt is NOT the `def test_` count — likely a collected-items count (parametrize expansion) from a different measure. **Validation rule for the merge gate: the full-suite `def test_` count must be MONOTONIC (≥ 649) — the extraction ADDS svc-export tests, removes none until the strangler 7-day window closes.** Do NOT assert "823"; assert monotonic-vs-baseline-649 and quote the live count at PR time.

---

## 1. Builder sequence (3-phase, per SUB_PLAN_01 §"Dispatch order")

```
PHASE A (parallel — no inter-dependency):
  meesell-database-builder → Alembic schema-split (exports public→export schema), version_table_schema="export", Risk#5 integrity pre-scan, tested downgrade
  [INFRA LANE — meesell-infra-builder, NOT a backend specialist — see handoff_msA_infra.md]

PHASE B (depends on A — service code targets the new schema):
  meesell-services-builder  → extract service.py+tasks.py+repository.py+domain.py+exceptions.py; 6-method/4-callee HTTP shims under core/extracted_clients/; trimmed Settings; single-task Celery app; standalone main.py (5-active-mw)
  meesell-api-routes-builder→ extract router.py+schemas.py into standalone routes; NO /internal/* (export has zero inbound callers); regenerate OpenAPI
    (api-routes can start once services-builder freezes the service-method signatures — practically near-parallel within Phase B)

PHASE C (depends on B — integration; LEAD-owned, not specialist):
  meesell-backend-coordinator → hybrid-mode CI wiring (in-process + HTTP-shim per §3.A); test_export_extraction.py; merge-gate review STEP 3; board MERGED flip
```

**Recommended dispatch order:** `database-builder` (Phase A) FIRST and IN PARALLEL with the infra handoff to infra-builder → then `services-builder` (Phase B, the heavy lift) → then `api-routes-builder` (Phase B, once service signatures frozen) → then lead Phase C. Iteration cap 3 per specialist (SUB_PLAN_01 §"Review + iteration protocol").

---

## 2. Branch plan (Model C — per SUB_PLAN_01 §"Branch setup" + PILOT F1/F3)

Cut from **origin/develop (`afea672`)** — see §0.1.

| Branch | Cut from | Purpose | Who commits |
|---|---|---|---|
| `feature/microservices-export/integration` | `origin/develop` (afea672) | Integration; merge commits only; F3 protection (PR-only, review-count **0**, checks=[], no force-push/deletions, enforce_admins false) applied at creation | backend lead (merge approval) + founder (integration→develop gate) |
| `feature/microservices-export/backend` | `…/integration` | All backend specialist extraction work | backend specialists |
| `feature/microservices-export/infra` | `…/integration` | Dockerfile, K8s, Postgres schema/role, Traefik route, GCS SA | meesell-infra-builder (infra lane) |

Worktrees per dispatch under `/tmp/mesell-wt/msA-*` (e.g. `/tmp/mesell-wt/msA-services`, `/tmp/mesell-wt/msA-db`, `/tmp/mesell-wt/msA-routes`). NEVER `git add -A` in a symlinked worktree — scope every stage to the exact `backend/services/svc-export/` path (PILOT op-learning #3).

**PR flow:** group → integration is the LEAD gate (squash). integration → develop is the **FOUNDER gate (left OPEN — I do NOT approve it)**, per D1.

```
feature/microservices-export/backend ─(backend lead; squash)─┐
                                                             ├─► feature/microservices-export/integration ─(FOUNDER; merge-commit)─► develop
feature/microservices-export/infra   ─(infra lead; squash)───┘
```

---

## 3. Per-specialist SPECs

### 3.A meesell-services-builder (opus) — the heavy lift

**TASK:** Extract `export` service/tasks/repository/domain/exceptions into `backend/services/svc-export/app/`, rewire the 6 cross-module calls to HTTP shims, build standalone main.py + single-task Celery app.

**Files to CREATE (svc-export tree):**
- `app/main.py` — standalone FastAPI; mounts export router; registers 6-mw chain (plan_guard NO-OP); `core/errors` handlers; `/health` + `/metrics`.
- `app/service.py` — FROM `modules/export/service.py`. Pipeline logic **byte-for-byte**; ONLY the 4 cross-module import lines (service.py:57-59,83) change from `from app.modules.<callee> import service as <callee>_service` to `from app.core.extracted_clients import <callee>_client as <callee>_service` (re-export the SAME symbol name so call sites at :174/:177/:185/:314/:452/:503/:659 are UNCHANGED per §16.G).
- `app/tasks.py` — FROM `modules/export/tasks.py`. `export_xlsx_task` (`name="export.xlsx"`), `asyncio.run` internals, `_write_audit` direct-ORM `export.completed`/`export.failed` to `public.audit_events`.
- `app/repository.py` — FROM `modules/export/repository.py`; bound to schema `export`.
- `app/domain.py` — FROM `modules/export/domain.py`; the `from app.modules.customer.domain import ComplianceBlock` (domain.py:49) becomes a **vendored local ComplianceBlock dataclass** (shim deserializes JSON into it).
- `app/exceptions.py` — FROM `modules/export/exceptions.py` (ExportError hierarchy).
- `app/celery_app.py` — single-task (`include=["app.tasks"]`), queue `svc-export`, broker Valkey DB 1 / results DB 2, **keys prefixed `svc-export:`** (§2.E namespacing).
- `app/core/extracted_clients/catalog_client.py` — shims `assert_product_ownership` + `get_product_for_export` → catalog-svc `/internal/*`. During Sub-Plan A the callees are STILL IN-PROCESS (monolith), so the shim base URL points at the **monolith ClusterIP** (`monolith-svc:8001`), NOT a not-yet-existent catalog-svc (R4, §3.A hybrid posture).
- `app/core/extracted_clients/category_client.py` — shims `fetch_schema` + `get_field_enum`.
- `app/core/extracted_clients/customer_client.py` — shims `get_compliance_block`.
- `app/core/extracted_clients/image_client.py` — shims `list_images` (NOT get_image_bytes — see §0.4).
- `app/shared/{database,config,valkey}.py` — vendored; TRIMMED Settings: `DATABASE_URL`@schema `export`, `VALKEY_URL`, `JWT_SECRET`, `GCS_*`, `APP_ENV` ONLY. **NO GEMINI/LANGFUSE/MSG91/RAZORPAY.** Small pool (worker-heavy).
- `app/core/middleware/*` — vendored 6-mw chain.
- `app/i18n/messages_en.py` — vendored subset: ONLY export's `validation_message_id` strings.
- `requirements.txt` — fastapi, sqlalchemy, asyncpg, celery, openpyxl (PIN same version as monolith — R5), httpx, redis. NO gemini/langfuse.

**ACCEPTANCE (merge-gate, I verify):**
- [ ] `git diff` of extracted `service.py` pipeline vs monolith shows ONLY the 4 import-line changes (service.py:57-59,83) — ZERO changes to the 7 call sites (:174/:177/:185/:314/:452/:503/:659). This is the §16.G absolute contract.
- [ ] All 4 shims use `httpx.AsyncClient`, 5s read / 2s connect timeout, 1 retry on 503/504 only (§5.E), forward user JWT in `Authorization` + `X-Request-ID`.
- [ ] Trimmed Settings carries NO gemini/langfuse/msg91/razorpay.
- [ ] Celery keys carry `svc-export:` prefix; broker DB 1 / results DB 2.
- [ ] `export.completed`/`export.failed` direct-ORM-write to `public.audit_events` (cross-schema INSERT).
- [ ] image shim is `list_images` returning ImagesListResponse, NOT get_image_bytes.
- [ ] PR template fully filled, no `<>` placeholders.

**RE-DISPATCH triggers:** call site changed beyond imports → re-dispatch quoting §16.G + the 7-line list above; shim missing JWT forward → §5.A; AI dep introduced → §14.A "deterministic"; wrong image method → §0.4 of this spec.

### 3.B meesell-api-routes-builder (sonnet)

**TASK:** Move the 2 export routes + schemas into `backend/services/svc-export/app/router.py` + `schemas.py`. Confirm NO `/internal/*` (export has zero inbound callers — it is a leaf consumer).

**Files to CREATE:**
- `app/router.py` — FROM `modules/export/router.py`. `prefix="/api/v1"`; `POST /products/{product_id}/export-xlsx` 202 (preserve `@rate_limit(scope="export_initiate", limit=10, window=3600)`); `GET /exports/{export_id}` 200 (NO rate_limit). Both `async`, both `Depends(get_current_user)` + `Depends(get_db)`.
- `app/schemas.py` — FROM `modules/export/schemas.py` (`ExportRequest`, `ExportInitiatedResponse`, `ExportResponse` — PRIVATE wire-shape).
- Regenerate standalone OpenAPI; the **mounted routes** (not schemas) are the inventory unit — confirm exactly 2 routes mount (row-26 lesson: count mounted APIRoute objects, not schema classes).

**ACCEPTANCE:** 2 routes mounted; both async; both `Depends(get_current_user)`+`Depends(get_db)`; rate-limit decorator preserved on POST; NO business logic inlined (handlers call service methods only); OpenAPI has 2 endpoints + 3 schemas; NO `/internal/*` route. PR template filled.

**RE-DISPATCH:** business logic inlined → §14.B "handlers call service methods only"; invented endpoint shape → re-cite router.py source.

### 3.C meesell-database-builder (sonnet) — Phase A, dispatch FIRST

**TASK:** Author the schema-split Alembic migration in `backend/services/svc-export/alembic/` moving `exports` from `public` to schema `export`.

**Files to CREATE:**
- `alembic/` chain rooted at schema `export`; `version_table_schema="export"` so `alembic_version` lands in the export schema.
- Migration: upgrade `ALTER TABLE exports SET SCHEMA export`; tested downgrade `SET SCHEMA public`.
- Risk#5 integrity pre-scan: verify every `exports.user_id` resolves to a real `users` row BEFORE any cross-schema FK drop (export drops NO FK itself, but the scan is the documented §6-Risk#5 pattern — emit scan output to a migration log).

**ACCEPTANCE:** upgrade + downgrade round-trip clean locally; `version_table_schema="export"` set; **dev applied BEFORE staging** (NEVER reverse — head-divergence dev↔staging = P0 escalate to founder); single head, no divergence.

**RE-DISPATCH:** head divergence dev↔staging → P0 STOP, escalate immediately.

---

## 4. Monolith-side strangler changes (LEAD-owned, NOT specialist; apply only AT cutover)
- `backend/app/modules/export/` (8 files) — KEEP live until hybrid-mode CI green ≥7 days, THEN delete (§3.C completion). Both trees coexist during the window.
- `backend/app/main.py` — at cutover, remove the in-process `export_router` mount (Traefik routes export paths to svc-export). Until cutover, stays mounted (both modes run).
- `backend/app/workers/celery_app.py` — at cutover, remove `app.modules.export.tasks` from `include=[...]`.

---

## 5. Documentation deliverables (gate conditions — must land with the merge)
- svc-export standalone OpenAPI (2 endpoints, 3 schemas).
- **HTTP-shim contract doc** — the 6 `/internal/*` endpoints the CALLEE sub-plans (C image / E customer / F category / H catalog) must later implement, each cited from §0.4 source signatures. THIS DOC IS A SUB-PLAN-A DELIVERABLE (freezes the interface now). Corrected contents (NOT the plan's mis-named version):
  - catalog-svc `/internal/products/{id}/ownership-check` ← `assert_product_ownership(product_id,user_id)->None`
  - catalog-svc `/internal/products/{id}/export-snapshot` ← `get_product_for_export(product_id,user_id)->ExportSnapshotInternal`
  - category-svc `/internal/categories/{id}/schema` ← `fetch_schema(category_id)->dict`
  - category-svc `/internal/categories/{id}/field-enum/{field}` ← `get_field_enum(category_id,field_name)->dict`
  - customer-svc `/internal/seller-profile/{user_id}/compliance-block` ← `get_compliance_block(user_id)->ComplianceBlock`
  - image-svc `/internal/products/{id}/images` ← `list_images(user_id,product_id)->ImagesListResponse` (signed URLs)
- `BACKEND_ARCHITECTURE.md §14` amendment ("Extracted to svc-export V1.5" note) — **§14 is LOCKED → FOUNDER APPROVAL REQUIRED** before this amendment lands. Do NOT self-amend a LOCKED section (§7.3).
- `MASTER_PLAN.md §4 row A` annotation flip ("Sub-Plan A IN EXECUTION 2026-06-12").
- `docs/runbooks/svc-export-rollback.md` (§3.C rollback specialized for export).
- Hybrid-mode CI config note (which services docker-composed for export's HTTP-mode CI: NONE of export's callees need standalone — during export extraction the callees are still in-process; shim points at monolith ClusterIP).

---

## 6. Validation (merge-gate, lead-owned)
- Full backend suite `def test_` count MONOTONIC ≥ 649 baseline (§0.9) — quote live count at PR time; do NOT hardcode 823.
- Export's own 42 tests green (or no-tunnel baseline: pure-function/contract subset green, infra-gated skips/errors documented per the auth-otp no-tunnel pattern).
- `ruff` clean on `backend/services/svc-export/`.
- import-linter: svc-export tree must not re-introduce a domain→adapters.gemini edge (Contract 2); export's meesho-symbol exception (`check_no_meesho_symbols_outside_export`) must still hold — svc-export inherits the export module's M10 allowlist.
- HTTP-shim contract doc complete (6 methods, source-cited).
- Rollback procedure present (runbook) per §3.C strangler-fig contract.
- NO tautological tests (pricing lesson): the hybrid-mode integration test must assert REAL behavior (an audit row lands in public.audit_events; a shim call forwards JWT + returns the callee's real shape), not `assert True`-class echoes.

---

## 7. Rollback (per MASTER_PLAN §3.C, specialized for export)
1. Traefik IngressRoute for export paths → back to monolith ClusterIP.
2. `core/extracted_clients/<callee>_client.py` re-exports in-process `service.py` (1-line / 1-revert per §16.G).
3. `exports` schema → back to `public` (`alembic downgrade` the schema-split).
4. `kubectl delete deployment svc-export`.
5. Re-run hybrid-mode CI in pure in-process mode; document root cause in runbook "Rollback Log".
Rollback allowed any time BEFORE Sub-Plan A declared complete (7-day green window).

---

## 8. Constraints honored (from dispatch)
- dev cluster / dev namespace ONLY; current hardware (svc-export api 50m/128Mi req, worker 200m/512Mi req per infra §6.3 — fits current node). NO D3 VM change (fresh founder ask only at node-outgrow). NO staging/prod. NO terraform beyond dev-scope (infra handoff flags anything bigger).
- Infra surfaces (Dockerfile, k8s, Traefik, Postgres role/schema, GCS SA) = INFRA HANDOFF (see `handoff_msA_infra.md`), NOT specialist work.
- PgBouncer (MS-DB-4) NOT a Sub-Plan-A blocker (dev/zero-traffic); MS-DB-3 pool right-size may proceed in parallel (infra lane).
