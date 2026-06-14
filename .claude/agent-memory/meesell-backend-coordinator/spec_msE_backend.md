# SPEC — Microservices Sub-Plan E (`customer` extraction) — BACKEND code work

> **MS-3 EXECUTION REFRESH 2026-06-13** — Execution gate flipped GATED → **OPEN** (MS-3, develop `942eba7`, PR #208). Grounding re-stamped `c859955` → `942eba7` (customer module BYTE-IDENTICAL since c859955; `git diff --stat c859955..origin/develop -- backend/app/modules/customer/` = empty → every file:line citation below STILL HOLDS, not re-grepped). Test floor raised 649 → 698 (re-count live at PR time). **Both open contract questions RESOLVED** (§9): INBOUND completeness shim corrected to the FROZEN-0B path `/internal/seller-profile/{user_id}/onboarding-completeness`; OUTBOUND super-categories FROZEN-0E as customer-owned `list[str]`. All DRAFT-PENDING markers removed.

**Session:** `mesell-ms-customer-session-1` (authored 2026-06-12; MS-3 refresh 2026-06-13)
**Author:** meesell-backend-coordinator (HYBRID rule 7 STEP 1 — SPEC only, no code, no git ops)
**Plan basis:** `docs/plans/microservices_migration/MASTER_PLAN.md` (v1.3) + `SUB_PLAN_0E_customer_extraction.md` (AUTHORED 2026-06-12) + the MS-A pilot recipe (`spec_msA_backend.md`)
**EXECUTION GATE OPEN (MS-3, develop 942eba7) — hybrid steps 2-3 dispatching now.** MS-A/B/C founder gates all MERGED; MS-0 PgBouncer LIVE; svc-export + svc-dashboard + svc-image already on develop. MS-3 runs customer (E) ‖ pricing (D). MS-E adds svc-customer.

---

## 0. GROUND TRUTH — re-stamped against source at develop `942eba7`

(Full detail in SUB_PLAN_0E §0. Condensed pointers here for the dispatch. Customer module byte-identical since `c859955`; citations hold without re-grep.)

- **Tree:** origin/develop = `942eba7` (#208). Cut EXECUTION branches from origin/develop.
- **Module = 7 files** (no `tasks.py` — customer has NO Celery; `grep shared_task customer/` = 0).
- **5 mounted routes** at `main.py:117` (import :42), prefix `/api/v1`, all in `router.py` (§8.B LOCKED). Monolith has NO `/internal/*` (verified `git grep "internal/" origin/develop -- backend/app/` = empty → strangler hybrid posture: extracted-service shims are HYBRID-CI-ONLY; Traefik routes live traffic to monolith, no service cut over). MS-E adds NO monolith-side internal routes.
- **INBOUND (callee) — 3 distinct methods across 3 callers, ALL FROZEN:**
  - `get_compliance_block(user_id, db) -> ComplianceBlock` — `service.py:648`; called by export (`export/service.py:503`) + catalog (`catalog/service.py:837`). Path `/internal/seller-profile/{user_id}/compliance-block` — **FROZEN by SUB_PLAN_0A** (`spec_msA_backend.md:181`).
  - `get_onboarding_completeness(user_id, db) -> ProfileCompleteness` — `service.py:682`; called by dashboard (`dashboard/service.py:85`). Path `/internal/seller-profile/{user_id}/onboarding-completeness` — **FROZEN by SUB_PLAN_0B** (`SUB_PLAN_0B_dashboard_extraction.md:360`; dashboard-svc's `customer_client.get_onboarding_completeness` calls this exact path, returns `ProfileCompleteness` 5 fields). (Phase-1 spec's PROPOSED `/internal/seller-profile/{user_id}/completeness` was WRONG; customer is the callee and must match the frozen 0B path.)
  - `assert_eligible_for_super_id(user_id, super_id, db) -> None` — `service.py:735`; called by catalog (`catalog/service.py:404`). Path `/internal/seller-profile/{user_id}/eligibility` — FROZEN by SUB_PLAN_0H (frozen-0H; first consumer = monolith-catalog reverse shim).
  - Domain imports (exchange currency → vendored copy): `export/domain.py:49 ComplianceBlock`, `dashboard/service.py:42 ProfileCompleteness`.
- **OUTBOUND (caller) — NOT a pure callee:** `service.py:347` `SELECT DISTINCT super_id FROM categories` via `CategoryORM` (`service.py:66`). Cross-schema read → must become E3-A HTTP shim to category-svc `GET /internal/super-categories → list[str]` (**FROZEN-0E, customer-owned**; SUB_PLAN_0F MS-4 must conform). Cached 3600s (`customer.super_category_set`, `service.py:85`).
- **Owned table:** `seller_profile` (1 table). `user_id` PK==FK→`users.id` CASCADE (`seller_profile.py:122`) + `relationship("User", ...)` (`:116`) — both SEVERED on extraction (Risk #5; plain UUID PK, no FK, no relationship in customer-svc ORM). GIN idx moves.
- **COMPLIANCE_EXTENSION_MAP = 11 keys / 6 source rules** (`domain.py:245`, master ruling 3) — moves verbatim (pure Python).
- **Tests:** customer own = 45 (`test_customer_routes.py` 19 + `tests/modules/customer/` 20 + `tests/integration/test_customer_*` 6). Full-suite baseline = **698** `def test_` (was 649 at Phase-1 authoring). MONOTONIC >= 698; quote live at PR time.
- **4 repo methods** all `scope_to_user`-wrapped (`repository.py`: find_by_user_id, upsert, update_active_categories, update_compliance_extension).
- **9 service methods** (5 endpoint-mirror + 3 cross-module + 1 assertion) — `service.py:792 __all__`.
- **7 exceptions** (`CustomerError` base + 6 subclasses) — `exceptions.py:187`.

---

## 1. Builder sequence (3-phase)

PHASE A (parallel): meesell-database-builder → schema-split seller_profile public→customer; version_table_schema="customer"; Risk#5 integrity pre-scan; SEVER FK + relationship; tested downgrade. [INFRA — meesell-infra-builder, see handoff_msE_infra.md]
PHASE B (depends on A): meesell-services-builder → extract service.py + repository.py + domain.py + exceptions.py; E3-A category_client OUTBOUND shim (replaces categories ORM read); 3 INBOUND /internal/* handlers; trimmed Settings; standalone main.py (6-mw, plan_guard NO-OP); NO Celery. meesell-api-routes-builder → extract router.py (5 public) + schemas.py; wire 3 /internal/* routes; regenerate OpenAPI.
PHASE C (lead-owned): meesell-backend-coordinator → monolith-side customer_client REVERSE shim (catalog §4); hybrid-mode CI; test_customer_extraction.py; merge gate; board flip.

Dispatch order: database-builder FIRST (+ infra handoff in parallel) → services-builder → api-routes-builder → lead Phase C. Iteration cap 3 per specialist (3rd re-dispatch → founder consult).

---

## 2. Branch plan (Model C)

Cut from origin/develop (`942eba7`) at MS-3 dispatch.
- `feature/microservices-customer/integration` ← origin/develop (backend lead group gate + founder integration→develop)
- `feature/microservices-customer/backend` ← …/integration (backend specialists)
- `feature/microservices-customer/infra` ← …/integration (meesell-infra-builder)
Worktrees `/tmp/mesell-wt/msE-*`. NEVER `git add -A` in a symlinked worktree — scope to `backend/services/svc-customer/`. group→integration = LEAD squash gate; integration→develop = FOUNDER gate (lead does NOT approve, D1).

---

## 3. Per-specialist SPECs

### 3.A meesell-services-builder (opus) — heavy lift
TASK: extract customer service/repository/domain/exceptions into `backend/services/svc-customer/app/`; build E3-A OUTBOUND category shim; wire 3 INBOUND /internal/* surfaces; standalone main.py (6-mw, plan_guard NO-OP); NO Celery.
Key files: app/main.py (no Celery), app/service.py (byte-for-byte EXCEPT _load_super_id_set loader swaps SQL→`await category_client.get_super_category_set()` keeping `_get_super_id_set` signature; drop CategoryORM import), app/repository.py (schema customer, scope_to_user kept on all 4), app/domain.py (VERBATIM incl COMPLIANCE_EXTENSION_MAP 11 keys), app/exceptions.py (6 subclasses), app/internal_routes.py (3 /internal/* handlers — paths per §3.B), app/core/extracted_clients/category_client.py (E3-A OUTBOUND shim → `GET /internal/super-categories → list[str]`, monolith ClusterIP for MS-3 → category-svc MS-4), app/shared/{database,config,valkey}.py (TRIMMED: DATABASE_URL@customer, VALKEY_URL, JWT_SECRET, CACHE_VERSION, APP_ENV; NO GEMINI/LANGFUSE/MSG91/RAZORPAY/GCS), vendored core/middleware/* + core/{auth,tenancy,cache,errors}.py, i18n/messages_en.py (6 customer IDs), shared/models/seller_profile.py (SEVER FK + relationship, plain UUID PK, keep GIN), requirements.txt (NO celery/gemini/langfuse/openpyxl/gcs).
ACCEPTANCE: service.py diff = ONLY the loader swap + dropped CategoryORM import; E3-A shim httpx 5s/2s + 1 retry 503/504 + JWT/X-Request-ID forward + configurable base URL, deserializes `list[str]`; 3 /internal/* serialize ComplianceBlock(10)/ProfileCompleteness(5)/eligibility-None exact field set+order; seller_profile ORM no FK/no relationship + GIN; trimmed Settings no AI/SMS/payment/gcs + no Celery; cache keys `customer:` prefix, 2 cache contracts preserved (required_fields 60s / super_category_set 3600s); @audit_event preserved on 3 PATCH → public.audit_events; PR template filled.
RE-DISPATCH: logic changed beyond 2 sanctioned edits → §16.G+§0.5/§3; categories ORM read still present → §2.D "never SQL"; /internal serialization adds/drops field → §5 zero-drift; FK not severed → §8/Risk#5; AI/Celery dep introduced → §0.8/E1; outbound shim deserializes anything but list[str] → §9 FROZEN-0E.

### 3.B meesell-api-routes-builder (sonnet)
TASK: move 5 public routes + 6 schemas into svc-customer; wire 3 /internal/* routes; regenerate OpenAPI.
app/router.py (5 routes VERBATIM per §0.3 table; preserve 3 @rate_limit(60,3600) + 3 @audit_event; both GET no rate-limit; all async + Depends(get_current_user)+Depends(get_db)). app/schemas.py (6 models; pincode Field(pattern=r"^\d{6}$") preserved).
The 3 INBOUND /internal/* routes (FROZEN paths — match exactly):
  - `GET /internal/seller-profile/{user_id}/compliance-block` → ComplianceBlock (10 fields) — FROZEN-0A.
  - `GET /internal/seller-profile/{user_id}/onboarding-completeness` → ProfileCompleteness (5 fields) — FROZEN-0B.
  - `GET /internal/seller-profile/{user_id}/eligibility` → eligibility assertion (None/422 envelope) — frozen-0H.
OpenAPI: 5 public + 3 internal = 8 mounted APIRoute (row-26: count routes not schemas).
ACCEPTANCE: 5 public routes match §0.3 exactly; 3 /internal/* mounted at the FROZEN paths above; GETs no rate-limit; no business logic inlined; OpenAPI 8 endpoints + 6 schemas; SellerProfileResponse + RequiredFieldsResponse byte-identical to monolith (LIVE frontend). PR template filled.
RE-DISPATCH: logic inlined → §8.B; route drift → re-cite router.py; response shape drift on 5 public → §5 LIVE-frontend zero-drift; internal path drift → §9 FROZEN paths.

### 3.C meesell-database-builder (sonnet) — Phase A, FIRST
TASK: schema-split Alembic migration moving seller_profile public→customer, severing cross-schema FK.
alembic/ rooted at schema customer; version_table_schema="customer". upgrade: Risk#5 pre-scan (every seller_profile.user_id resolves to real users row, emit to log) → DROP CONSTRAINT fk_seller_profile_user_id → ALTER TABLE seller_profile SET SCHEMA customer. downgrade: SET SCHEMA public → re-add FK. GIN idx follows table.
ACCEPTANCE: upgrade+downgrade round-trip clean; version_table_schema="customer"; pre-scan emits output; FK dropped/restored; dev applied BEFORE staging (NEVER reverse — head divergence dev↔staging = P0 escalate founder).
RE-DISPATCH: head divergence → P0 STOP escalate; FK not handled → §8/Risk#5.

---

## 4. Monolith-side strangler changes (LEAD-owned, at cutover only)
- NEW backend/app/core/extracted_clients/customer_client.py (IN MONOLITH) — REVERSE shim. Monolith catalog calls assert_eligible_for_super_id (catalog/service.py:404) + get_compliance_block (catalog/service.py:837). At cutover flip import at catalog/service.py:97 to `from app.core.extracted_clients import customer_client as customer_service`. §16.G: call sites byte-for-byte identical.
- backend/app/main.py — remove customer_router mount (main.py:117) at cutover; Traefik routes /api/v1/seller-profile/* to customer-svc. Until cutover both run.
- backend/app/modules/customer/ (7 files) — KEEP until hybrid CI green >=7d, then delete (§3.C).
- export-svc + dashboard-svc customer_client base URLs re-point monolith→customer-svc at cutover (INFRA config flip).

---

## 5. Documentation deliverables (gate conditions)
- customer-svc OpenAPI (5 public + 3 internal; 6 schemas).
- HTTP-shim contract doc — 3 INBOUND + 1 OUTBOUND, ALL FROZEN (no DRAFT-PENDING), source-cited:
  - INBOUND `/internal/seller-profile/{user_id}/compliance-block` → ComplianceBlock (10 fields) — FROZEN-0A (spec_msA_backend.md:181).
  - INBOUND `/internal/seller-profile/{user_id}/onboarding-completeness` → ProfileCompleteness (5 fields) — FROZEN-0B (SUB_PLAN_0B_dashboard_extraction.md:360).
  - INBOUND `/internal/seller-profile/{user_id}/eligibility` → None/422 envelope — frozen-0H (monolith-reverse first consumer).
  - OUTBOUND `GET /internal/super-categories → list[str]` (distinct super_ids) — FROZEN-0E (customer-owned; SUB_PLAN_0F MS-4 must conform to list[str], NOT its draft list[SuperCategoryInfo]).
- BACKEND_ARCHITECTURE.md §8 "Extracted to customer-svc V1.5" note — §8.B LOCKED → FOUNDER APPROVAL (§7.3). Do NOT self-amend.
- MASTER_PLAN.md §4 row E annotation flip.
- docs/runbooks/customer-svc-rollback.md.
- Hybrid CI config note (export-svc + dashboard-svc docker-composed for inbound shims; monolith+catalog runs for reverse shim; outbound category read → monolith ClusterIP).

---

## 6. Validation (merge-gate, lead-owned)
- Full suite def test_ MONOTONIC >= 698; quote live.
- Customer 45 own tests green in BOTH monolith + customer-svc (or documented no-tunnel baseline).
- ruff clean svc-customer.
- import-linter: no cross-schema categories ORM read re-introduced; §16 boundaries hold.
- NO tautological tests (pricing lesson): assert REAL — (a) compliance-block 10-field equality in-process vs HTTP; (b) completeness 5-field equality; (c) eligibility 422 envelope on missing compulsory key; (d) audit row in public.audit_events on PATCH; (e) 5 public endpoints byte-identical JSON monolith vs customer-svc (LIVE zero-drift); (f) outbound super-categories shim returns list[str] of distinct super_ids.
- Rollback runbook present.

---

## 7. Rollback (§3.C, customer-specialized)
1. Traefik /api/v1/seller-profile/* → monolith ClusterIP. 2. monolith customer_client re-export → in-process service.py (catalog import :97 reverts). 3. export-svc + dashboard-svc customer_client base URLs → monolith. 4. seller_profile schema → public (downgrade; re-add FK). 5. kubectl delete deployment customer-svc. 6. Re-run hybrid CI in-process; log root cause in runbook. Allowed any time before customer declared complete (7-day green window).

---

## 8. Constraints honored
dev namespace ONLY; current hardware (~50m/128Mi api, query-light, no worker/AI, fits node). NO D3 at authoring; fresh founder ask at node-outgrow. customer+pricing both small at MS-3 — D3 re-evaluated by master at MS-3 deploy. Infra surfaces = handoff_msE_infra.md. PgBouncer LIVE (MS-0); not a customer blocker (dev/zero-traffic). NO frontend/k8s/terraform/Gemini in backend lane.

---

## 9. Contract questions RESOLVED (2026-06-13, MS-3 open)

1. **INBOUND completeness shim (was DRAFT-PENDING-0B-RECONCILE) — RESOLVED FROZEN-0B.** SUB_PLAN_0B (MS-B, MERGED `18d829e`) FROZE the dashboard→customer shim at `SUB_PLAN_0B_dashboard_extraction.md:360`: dashboard-svc's `customer_client.get_onboarding_completeness(user_id, db)` calls `GET customer-svc/internal/seller-profile/{user_id}/onboarding-completeness`, returning `ProfileCompleteness` (5 fields: base_complete_count, base_total_count, extension_complete_count, extension_total_count, onboarding_complete — `customer/domain.py:98`). Phase-1 spec's PROPOSED `/internal/seller-profile/{user_id}/completeness` was WRONG; customer is the CALLEE → INBOUND shim #2 corrected to the FROZEN `/internal/seller-profile/{user_id}/onboarding-completeness` (matches MS-A's frozen `/internal/seller-profile/{user_id}/compliance-block` path family). Marked FROZEN-BY-0B.

2. **OUTBOUND super-categories shim (was DRAFT-PENDING-0F-RECONCILE) — RESOLVED FROZEN-0E.** Customer is the CALLER of `/internal/super-categories`. Per common-rule 5 (callee services implement the shims their callers froze), CUSTOMER freezes this contract and SUB_PLAN_0F (MS-4, not yet built) must conform. SUB_PLAN_0F (`SUB_PLAN_0F_category_extraction.md:92-98, 363-367`) marks `list_super_categories` as latent/defensive — as-built grep found NO current caller — and explicitly defers. FROZEN customer-owned contract: `GET /internal/super-categories → list[str]` (distinct super_ids); category-svc must implement to this shape at MS-4. During MS-3 the E3-A outbound shim points at the monolith ClusterIP. Marked FROZEN-BY-0E (customer-owned). NOTE: SUB_PLAN_0F (MS-4) must conform to `list[str]`, NOT its draft `list[SuperCategoryInfo]`.
