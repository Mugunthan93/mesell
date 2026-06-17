# SUB-PLAN E — `customer` Service Extraction (Seller Profile / Legal-Metrology)

**STATUS: AUTHORED 2026-06-12 — EXECUTION GATED** (MS-3 wave: opens when MS-2
dashboard + image founder gates merged; runs in parallel with MS-D pricing).
Authored under session `mesell-ms-customer-session-1` (HYBRID rule 7 STEP 1 —
SPEC AUTHORING ONLY, no code, no git ops). This is the fifth extraction
(MASTER_PLAN §3.B order position 5) of the Microservices Migration MASTER_PLAN
(LOCKED 2026-06-10, v1.3 — §3.A.1 dev-complete start condition SATISFIED) under
the parallel-program upgrade (founder ruling MS-PAR-1, wave structure in
`docs/sub_session_prompts/microservices_execution/00-ms-parallel-program-dispatch.md`).

> **Execution gate — PLANNING ONLY.** Per MS-PAR-1, sub-plan AUTHORING for all
> services may proceed immediately (docs, fully parallel). EXECUTION of customer
> is GATED on the MS-2 wave (both B dashboard and C image founder gates merged to
> develop), then runs at MS-3 in parallel with MS-D pricing under shared-file
> discipline. The MS-1 (export) recipe in
> `.claude/agent-memory/meesell-backend-coordinator/spec_msA_backend.md` is the
> pattern this sub-plan copies.

> Authoritative inputs read for this sub-plan:
> - `docs/plans/microservices_migration/MASTER_PLAN.md` (LOCKED v1.3 — §1.A/§1.C/§2.B/§2.C/§2.D/§3.A/§3.B/§3.C/§5, §6 Risk #5)
> - `docs/plans/microservices_migration/SUB_PLAN_01_export_extraction.md` (the canonical SHAPE TEMPLATE; A1/A2 LOCKED)
> - `.claude/agent-memory/meesell-backend-coordinator/spec_msA_backend.md` + `handoff_msA_infra.md` (the MS-A pilot recipe)
> - `docs/sub_session_prompts/microservices_execution/00-ms-parallel-program-dispatch.md` (common rules + wave gating)
> - AS-BUILT source at develop **c859955**: `backend/app/modules/customer/` (7 files) + its mounts in `backend/app/main.py` + its callers (`export`, `dashboard`, `catalog`) + its tests
> - `backend/app/shared/models/seller_profile.py` (the owned table DDL)

---

## 0. GROUND TRUTH — verified against source at develop `c859955`

Everything below is re-verified from the live tree, cited `file:line`. Where the
dispatch prompt or the MASTER_PLAN §2.D matrix prose disagrees with source,
**source wins** (the Wave-6 fabricated-enum / row-26 discipline).

### 0.1 Branch / tree state — ACT ON THIS FIRST

- **origin/develop tip = `c8599556` (`c859955`)** — confirmed via `git ls-remote origin develop`. The doc-deliverable worktree `/tmp/mesell-wt/msE-spec` is already a checkout of this tip on branch `feature/microservices-customer/integration`.
- The MASTER-tree working copy was at `6d6ee51` (local develop) during authoring; the **customer module is byte-identical between `c859955` and `6d6ee51`** (`git diff c859955 6d6ee51 -- backend/app/modules/customer/` = empty). The only develop-tip delta touching the mount file is in `main.py` (a catalog feature-flag unwrap, NOT customer). So the customer grounding is identical on both commits. Cut the EXECUTION branches from **origin/develop** at execution time, never from a local-only commit.

### 0.2 Customer module = 7 files — CONFIRMED

`backend/app/modules/customer/`: `__init__.py`, `domain.py`, `exceptions.py`,
`repository.py`, `router.py`, `schemas.py`, `service.py` = **7 files** (the
canonical §3.C 7-file layout MINUS `tasks.py` — customer has NO Celery task, it
is a pure CRUD + cache module). Line counts: service 802, domain 299, repository
236, router 223, schemas 205, exceptions 195, __init__ 32.

### 0.3 Mounted routes — 5 endpoints, VERIFIED IN main.py (the row-26 lesson)

`customer_router` is imported at `backend/app/main.py:42`
(`from app.modules.customer import customer_router`) and **mounted at
`backend/app/main.py:117`** (`app.include_router(customer_router)`) — NOT
feature-flag-guarded (unlike catalog at :126). The router declares
`prefix="/api/v1"` (`router.py:69`) with **5 routes** (the §8.B LOCKED 2026-06-05
contract), cited from the route decorators in `router.py`:

| # | Method + path | Handler | Rate limit | Audit | Source |
|---|---|---|---|---|---|
| 1 | `GET  /api/v1/seller-profile` | `get_seller_profile` | none (per-IP floor) | none | `router.py:75` |
| 2 | `PATCH /api/v1/seller-profile` | `patch_seller_profile` | `@rate_limit(scope="profile_update", limit=60, window=3600)` | `@audit_event("customer.profile_updated")` | `router.py:101-107` |
| 3 | `PATCH /api/v1/seller-profile/active-categories` | `patch_active_categories` | `@rate_limit(scope="active_categories", limit=60, window=3600)` | `@audit_event("customer.active_categories.updated")` | `router.py:129-135` |
| 4 | `PATCH /api/v1/seller-profile/compliance/{super_id}` | `patch_compliance_extension` | `@rate_limit(scope="compliance_update", limit=60, window=3600)` | `@audit_event("customer.compliance_updated")` | `router.py:158-164` |
| 5 | `GET  /api/v1/seller-profile/required-fields` | `get_required_fields` | none (cached, per-IP floor) | none | `router.py:198` |

Every handler is `async def`, takes `Depends(get_current_user)` + `Depends(get_db)`,
returns a Pydantic response model, inlines NO business logic (orchestration only).
The §8-ROUTES-D1 decision (`router.py:33-38`) notes the `rate_limit` decorator
has no `key=` param — per-user keying is automatic via `request.state.user_id`,
matching §8.B intent (same as the iam D2 deviation). NO `/internal/*` route exists
anywhere in the codebase yet (`grep /internal backend/app/modules/` = 0) — the
extraction ADDS customer's `/internal/*` endpoints (the shims its 3 callers froze).

### 0.4 Customer's INBOUND surface — it is a CALLEE of THREE modules (4 distinct method calls + 2 domain imports)

This is the load-bearing contract: customer is called BY export, dashboard, and
catalog. **The dispatch prompt's "FROZEN MS-A shim" line cited only `get_compliance_block`
for customer — that is the EXPORT shim, but customer's full inbound surface is
LARGER.** Authoritative list of every cross-module reference to `customer`, cited
from caller source:

| # | Caller call site | Customer method invoked (signature from `customer/service.py`) | Returns | Freezing sub-plan |
|---|---|---|---|---|
| 1 | `export/service.py:503` `customer_service.get_compliance_block(user_id, db)` | `service.py:648` `get_compliance_block(user_id: UUID, db: AsyncSession) -> ComplianceBlock` | `ComplianceBlock` (frozen dataclass, `domain.py:75`) | **SUB_PLAN_0A (export) — FROZEN** (spec_msA_backend.md:181) |
| 2 | `dashboard/service.py:85` `customer_service.get_onboarding_completeness(user_id=user_id, db=db)` | `service.py:682` `get_onboarding_completeness(user_id: UUID, db: AsyncSession) -> ProfileCompleteness` | `ProfileCompleteness` (frozen dataclass, `domain.py:97`) | **SUB_PLAN_0B (dashboard) — owned by Session MS-B; see §1.1 DRAFT-PENDING-0B-RECONCILE** |
| 3 | `catalog/service.py:404` `customer_service.assert_eligible_for_super_id(user_id, super_id, db=db)` | `service.py:735` `assert_eligible_for_super_id(user_id: UUID, super_id: str, db: AsyncSession) -> None` (raises `ProfileIncompleteForCategoryError`) | `None` | **SUB_PLAN_0H (catalog) — but catalog stays in monolith until MS-5; see §2** |
| 4 | `catalog/service.py:837` `customer_service.get_compliance_block(user_id, db=db)` | same as #1 — `get_compliance_block` | `ComplianceBlock` | same shim as #1 (catalog reuses export's frozen contract) |

**Domain-import (NOT a service call — the §16 "exchange currency" pattern, becomes a vendored dataclass copy on the caller side):**
- `export/domain.py:49` `from app.modules.customer.domain import ComplianceBlock`
- `dashboard/service.py:42` `from app.modules.customer.domain import ProfileCompleteness`

So customer's INBOUND `/internal/*` surface is **3 distinct methods**:
`get_compliance_block` (export + catalog), `get_onboarding_completeness`
(dashboard), `assert_eligible_for_super_id` (catalog). Note `catalog` confirms
its docstring claim (`catalog/service.py:28` "imports `from app.modules.customer
import service` ONLY") — TRUE, but it calls **two** of customer's methods
(#3 + #4), not one.

### 0.5 Customer's OUTBOUND surface — NOT a pure callee (a correction over the dispatch premise)

The dispatch said "determine whether customer CALLS any other module in-process
(if truly none, customer is a pure callee — state that with grep evidence)."
**Grep evidence says customer is NOT a pure callee.** It does not import any other
module's `service.py` (`grep "from app.modules" customer/*.py` shows only
self-imports), BUT it reads the **`categories` table directly via ORM** — a table
owned by the `category` module/schema:

- `customer/service.py:66` `from app.shared.models.category import Category as CategoryORM`
- `customer/service.py:347` `stmt = select(CategoryORM.super_id).distinct().order_by(CategoryORM.super_id)` — `SELECT DISTINCT super_id FROM categories`, cached 3600s under key `customer.super_category_set` (`service.py:80-87`, `_get_super_id_set` at `:352`).

This is consumed by `set_active_categories` (`service.py:451`) to validate that
declared super_ids are real. **After schema isolation, this becomes a cross-schema
read of `category.categories` from `customer-svc`** — forbidden by MASTER_PLAN
§2.D ("No cross-schema reads — a service that needs another service's data goes
through HTTP, never SQL"). **Design decision required — see §3.** This is the
single most important as-built finding for the customer extraction, and it does
NOT exist in the export pilot (export's category reads go through
`category_service.fetch_schema`, already a service call; customer's goes through
raw ORM on a foreign table).

### 0.6 Customer's full outbound dependency enumeration (from source)

Every `app.*` import in `customer/*.py` (excluding self-imports), cited:

| Dependency | Imported by | Disposition on extraction |
|---|---|---|
| `app.core.auth` (`CurrentUser`, `get_current_user`) | `router.py:49` | VENDORED (A2/D7 — local JWT verify, 6-mw chain) |
| `app.core.middleware.audit_mw` (`audit_event`) | `router.py:50` | VENDORED (audit_mw + the 3 `@audit_event` decorators; writes to `public.audit_events`) |
| `app.core.middleware.rate_limit_mw` (`rate_limit`) | `router.py:51` | VENDORED (rate-limit mw; shared Valkey DB 0 keyspace, §5.C) |
| `app.core.errors` (`MeesellError`) | `exceptions.py:37` | VENDORED (`core/errors` envelope; `CustomerError` hierarchy) |
| `app.core.tenancy` (`scope_to_user`) | `repository.py:38` | VENDORED (§4.C grep-anchor preserved in all 4 repo methods) |
| `app.core.cache` (`get_or_set`) | `service.py:45` | VENDORED (Valkey DB 3 read-through; 2 cache keys — see §7) |
| `app.shared.database` (`get_db`) | `router.py:61` | VENDORED + TRIMMED Settings; pool bound to `customer` schema |
| `app.shared.config` (`settings`) | `service.py:323` | VENDORED + TRIMMED (no GEMINI/MSG91/RAZORPAY/LANGFUSE) |
| `app.shared.valkey` (`get_valkey_cache`) | `service.py:324` | VENDORED (DB 3 cache; `customer:` key prefix per §2.E) |
| `app.shared.models.seller_profile` (`SellerProfile` ORM) | `service.py:67`, `repository.py:39` | MOVED with the service (customer owns `seller_profile`) |
| `app.shared.models.category` (`Category` ORM) | `service.py:66` | **CROSS-SCHEMA — must be replaced; see §3** (the `categories` table stays in category-svc) |

### 0.7 Owned table — `seller_profile` (with a cross-table FK to `users`)

`customer-svc` owns exactly ONE table: `seller_profile` (`shared/models/seller_profile.py:34`).
Notable DDL facts the schema-split must handle:
- **PK == FK**: `user_id` is BOTH primary key AND a foreign key to `users.id` with `ondelete="CASCADE"` (`seller_profile.py:122-128` `ForeignKeyConstraint`). Plus a `relationship("User", back_populates="seller_profile")` (`:116`). **This is a cross-schema FK (`customer.seller_profile.user_id → iam.users.id`) after isolation — MASTER_PLAN §2.D locks that such cross-schema FKs are DROPPED (the iam extraction at MS-4 does this for the iam side; the customer side must drop its FK + relationship at customer's own cutover, replacing it with app-layer `scope_to_user` enforcement, Risk #5).**
- GIN index `idx_seller_profile_super_cats` on `active_super_categories` (`:131`) — moves with the table.
- JSONB `compliance_extensions`, `ARRAY(String)` `active_super_categories`, `onboarding_complete` bool (DB-aligned name per master ruling 2, migration `935e55b4852c`).

### 0.8 NO Celery — customer is synchronous CRUD

`grep -rn "shared_task\|celery" backend/app/modules/customer/` = 0. Customer has
no background task. The `tasks.py` file does not exist in its subtree (unlike
export/image). **customer-svc ships NO Celery app** — it is a pure FastAPI request/
response service. This makes it simpler than the export pilot in the worker
dimension, harder in the cross-schema-read dimension (§0.5).

### 0.9 Test inventory — re-counted from source (do NOT hardcode)

- `backend/tests/test_customer_routes.py` — **19** `def test_` (route-level)
- `backend/tests/modules/customer/` — **20** `def test_` across 5 files (`test_compliance_extension_validation_per_super_id.py`, `test_eye_serum_case.py`, `test_onboarding_complete_flag_recomputation.py`, `test_pincode_regex_enforcement.py`, `test_profile_upsert_idempotency.py`) + `conftest.py`
- `backend/tests/integration/test_customer_cross_module_eligibility.py` + `test_customer_full_onboarding_flow.py` — **6** `def test_`
- **Customer's own = 45** `def test_`.
- **Full-suite baseline = 649** `def test_` (`grep -rn "def test_" backend/tests/` at c859955 — IDENTICAL to the MS-A pilot baseline; nothing has landed since). **Validation rule (§9): the full-suite count must be MONOTONIC ≥ 649 — quote the LIVE count at PR time, do NOT hardcode.**

### 0.10 COMPLIANCE_EXTENSION_MAP — 11 keys / 6 source rules (a correction over older §8 memory)

The dispatch prompt's "6 super_ids" framing is the OLD count. The as-built
`domain.py:245` `COMPLIANCE_EXTENSION_MAP` is a `MappingProxyType` with **exactly
11 keys** built from **6 source rules** (master ruling 3, 2026-06-07): Grocery
("26", compulsory FSSAI), Kids ("13"), Electronics ("16"), Beauty (6 super_ids
19/36/37/14/88/34 sharing ONE `_BEAUTY_SPEC` instance, compulsory), Books ("80"),
Home & Kitchen ("30"). Cited `domain.py:157-247`. The extraction moves this constant
VERBATIM (it is pure Python, no DB) into `customer-svc`'s vendored `domain.py`.

---

## 1. Decisions

This sub-plan inherits the LOCKED program decisions (no new founder ruling needed
to author it). Customer-specific decisions:

### E1 — `ai_ops/` placement: NOT APPLICABLE (customer has zero AI)

`grep -rn "ai_ops" backend/app/modules/customer/` = 0. Customer is deterministic
CRUD — no Gemini, no autofill, no smart-picker. A1/D6 (ai_ops vendored per
AI-consuming service) does NOT touch customer. customer-svc `requirements.txt`
carries NO gemini/langfuse. CONFIRMED, no decision needed.

### E2 — Middleware: 6-mw chain VENDORED, local JWT (A2/D7 LOCKED)

customer-svc vendors the 6-mw chain (CORS → request_id → auth_mw → tenancy_mw →
rate_limit_mw → plan_guard_mw → audit_mw). Customer uses 5 of 6 actively:
`auth_mw` (both endpoints `Depends(get_current_user)`), `tenancy_mw`
(`request.state.user_id`), `rate_limit_mw` (3 PATCH routes @ 60/h), `request_id_mw`,
`audit_mw` (3 `@audit_event` decorators). **`plan_guard_mw` RUNS but is NO-OP for
customer** — customer participates in NO plan_guard resource (per §8 it is one of
3 plan_guard-excluded modules alongside pricing + dashboard). JWT verified LOCALLY
via vendored `core/auth.py` + shared `JWT_SECRET`. CONFIRMED, no decision needed.

### E3 — The `categories`-table cross-schema read (THE customer-specific decision) — see §3 for the full design

This is the one genuine design question. **Recommendation (lead, for founder/master-
session confirmation at MS-3 execution dispatch): Option E3-A — replace the direct
`SELECT DISTINCT super_id FROM categories` with an HTTP shim to category-svc's
`/internal/super-categories` endpoint, with a fallback for the strangler window.**
Full options table in §3.1. This is the REVERSE direction of customer's callee
role: customer becomes a CALLER of category-svc (a NEW edge that the §2.D matrix
does not list, because in the monolith it was a raw ORM read, not a service call).

### E4 — Extraction order / wave — CONFIRMATION of MS-PAR-1

customer extracts at **MS-3, in parallel with MS-D (pricing)**, GATED on MS-2
(B dashboard + C image founder gates merged). Per MASTER_PLAN §3.B customer is
order position 5 ("Tenant-scoped, low call volume. Consumed by catalog + export +
dashboard — by this point, all 3 consumers already have HTTP shim infrastructure
in place"). Confirmed, not a new ruling.

### 1.1 OPEN CONTRACT QUESTION — dashboard shim shape (DRAFT-PENDING-0B-RECONCILE) — MASTER-SESSION ESCALATION

**Customer's `/internal/seller-profile/{user_id}/completeness` endpoint contract
is OWNED by SUB_PLAN_0B (Session MS-B / dashboard), not by this sub-plan.** The
dispatch is explicit: "DO NOT invent dashboard's shim shapes." The as-built call
is `dashboard/service.py:85` `get_onboarding_completeness(user_id, db) ->
ProfileCompleteness`. This sub-plan PROPOSES the matching `/internal/*` endpoint as
**DRAFT-PENDING-0B-RECONCILE** (see §5 contract doc) but does NOT freeze it.

**Escalation path (per dispatch common-rule 5 + master-session coordination):**
because dashboard extracts at MS-2 (BEFORE customer at MS-3), Session MS-B's
dashboard-svc will carry a `customer_client` shim that points at the **monolith
ClusterIP** during MS-2 (customer still in-process). When dashboard freezes that
shim's `/internal/*` shape in SUB_PLAN_0B, customer (MS-3) must implement it
EXACTLY. **The two sub-plans MUST reconcile on the `get_onboarding_completeness`
→ `/internal/*` contract before customer's execution dispatch.** If SUB_PLAN_0B's
frozen shape differs from this sub-plan's DRAFT proposal in §5, the MASTER SESSION
resolves the conflict (never improvise a contract). Tracked as the open question
in this session's report-back.

---

## 2. Extraction-order context — who is already out, who is still in-monolith

Customer extracts at MS-3, so by the time it runs:

- **export (MS-1) is OUT.** export-svc carries a `customer_client` HTTP shim for
  `get_compliance_block` (frozen in spec_msA_backend.md:181 / SUB_PLAN_0A §5). During
  MS-1 that shim pointed at the **monolith ClusterIP** (customer was in-process).
  **At customer's cutover (MS-3), export-svc's `customer_client` base URL re-points
  from `monolith-svc:8001` to `customer-svc:8001`** — an infra Traefik/config flip,
  NOT a code change (§16.G: the call site never changed). This is an INFRA HANDOFF item.
- **dashboard (MS-2) is OUT.** Same pattern — dashboard-svc's `customer_client`
  (for `get_onboarding_completeness`) re-points from monolith to customer-svc at
  MS-3 cutover. Contract reconciliation per §1.1.
- **image (MS-2) is OUT** but does NOT call customer (image → catalog only). No customer interaction.
- **catalog (MS-5) is STILL IN THE MONOLITH** at customer's cutover. **This is the
  REVERSE-direction change unique to customer (and the pattern §16.G calls out):**
  the monolith's `catalog` module calls `customer_service.assert_eligible_for_super_id`
  (`catalog/service.py:404`) and `customer_service.get_compliance_block`
  (`catalog/service.py:837`) IN-PROCESS today. When customer extracts, the
  **monolith-side catalog module needs an OUTBOUND HTTP-shim client**
  (`core/extracted_clients/customer_client.py` IN THE MONOLITH) pointing at
  customer-svc. This is the mirror image of MS-A, where the EXTRACTED service got
  the shim; here the REMAINING monolith gets it. Spec'd in §4.
- **category (MS-4) is STILL IN THE MONOLITH** at customer's cutover. So customer's
  OUTBOUND `categories`-read shim (§0.5 / §3) points at the **monolith ClusterIP**
  during MS-3 (category not yet extracted), then re-points to category-svc at MS-4
  cutover. Same strangler hybrid posture as MS-A's outbound shims (§3.A, R4).

---

## 3. The `categories` cross-schema read — design (THE customer-specific work)

### 3.1 Options

Customer's `_load_super_id_set` (`service.py:340`) runs
`SELECT DISTINCT super_id FROM categories`. After schema isolation that table lives
in `category` schema / category-svc — a cross-schema read is forbidden (§2.D).

| Option | Description | Pros | Cons |
|---|---|---|---|
| **E3-A (RECOMMENDED)** | Replace `_load_super_id_set` with an HTTP shim `category_client.get_super_category_set()` → category-svc `GET /internal/super-categories` (returns `list[str]` of distinct super_ids). The result stays cached 3600s in customer's Valkey DB 3 exactly as today (`service.py:352` cache contract UNCHANGED — only the loader function body changes from ORM SELECT to httpx GET). | Honors §2.D (no cross-schema SQL). Cache amortizes the network hop to ~once/hour/instance — super_id set is global reference data. The §16.G call-site discipline applies: `_get_super_id_set` (the cached accessor) keeps its signature; only the inner `_load_super_id_set` loader swaps SQL→HTTP. During MS-3 the shim points at monolith ClusterIP (category in-process); re-points to category-svc at MS-4. | Adds category-svc as a NEW dependency of customer-svc (a new `/internal/super-categories` endpoint category-svc must expose — SUB_PLAN_0F deliverable; see §1.1-style reconcile note in §5). Until category extracts (MS-4), the shim hits the monolith. |
| **E3-B (rejected for V1.5)** | Seed/replicate the distinct super_id set into customer's own schema (a small reference table `customer.super_category_ref`, refreshed by a periodic job from category). | No runtime network hop. | Introduces a replication/staleness problem (super_id set changes on quarterly Meesho corpus refresh); a new ETL job; duplicate source of truth. Premature for V1.5; the set is tiny and cached. |
| **E3-C (rejected)** | Keep the cross-schema SELECT (grant customer_user SELECT on category.categories). | Zero code change. | Directly violates §2.D ("never SQL" cross-schema). Re-introduces the hidden coupling the migration exists to remove. Breaks when category moves to a separate DB instance in V2. |

**RECOMMENDATION: E3-A.** It is the §2.D-compliant path, preserves the 3600s cache
contract verbatim, and matches the strangler hybrid posture (shim → monolith during
MS-3, → category-svc at MS-4). It introduces a NEW `/internal/super-categories`
endpoint that **SUB_PLAN_0F (category) must implement** — flagged in §5 as a
cross-sub-plan contract (DRAFT-PENDING-0F-RECONCILE), escalated to the master
session the same way the 0B dashboard shim is (§1.1).

### 3.2 Net cross-service edges customer introduces

After E3-A, customer-svc has:
- **INBOUND** (customer is callee): 3 `/internal/*` endpoints it EXPOSES — `get_compliance_block`, `get_onboarding_completeness`, `assert_eligible_for_super_id`.
- **OUTBOUND** (customer is caller): 1 `/internal/*` endpoint it CONSUMES — category-svc `GET /internal/super-categories` (the super_id validation set).

So customer is a **bidirectional** node, not a pure leaf — a correction over the
dispatch's "pure callee" hypothesis, proven by §0.5 grep evidence.

---

## 4. Monolith-side strangler changes (LEAD-owned, NOT specialist; apply only AT cutover)

Per MASTER_PLAN §3.C + §16.G. During the strangler window BOTH trees coexist;
these changes land only at customer's founder-gated cutover flip.

- **NEW — `backend/app/core/extracted_clients/customer_client.py` (IN THE MONOLITH).**
  The remaining monolith's `catalog` module calls `customer_service.assert_eligible_for_super_id`
  (`catalog/service.py:404`) and `customer_service.get_compliance_block`
  (`catalog/service.py:837`). At cutover these two call sites must resolve to an
  OUTBOUND HTTP shim re-exporting the same two symbols (`assert_eligible_for_super_id`,
  `get_compliance_block`) over httpx to customer-svc. **§16.G: the call sites at
  `catalog/service.py:404` + `:837` stay BYTE-FOR-BYTE identical — only the import
  at `catalog/service.py:97` (`from app.modules.customer import service as customer_service`)
  flips to `from app.core.extracted_clients import customer_client as customer_service`.**
  This is the REVERSE of MS-A (the monolith gets the shim, not the extracted service).
- `backend/app/main.py` — at cutover, remove the in-process `customer_router` mount
  (`main.py:117`; Traefik routes `/api/v1/seller-profile/*` to customer-svc). Until
  cutover it stays mounted (both modes run). Shared-file discipline: minimal, additive,
  the integration branch merges origin/develop BEFORE the founder-gate PR opens.
- `backend/app/modules/customer/` (7 files) — KEEP live until hybrid-mode CI green
  ≥7 days, THEN delete (§3.C completion). Both trees coexist during the window.
- NO `celery_app.py` change (customer has no task — §0.8).

---

## 5. Documentation deliverables (gate conditions — must land with the merge)

- customer-svc standalone OpenAPI (5 public endpoints + the 3 `/internal/*` endpoints; `SellerProfileResponse`, `PatchProfileRequest`, `PatchActiveCategoriesRequest`, `PatchComplianceExtensionRequest`, `RequiredFieldsResponse`, `ComplianceBlockResponse` schemas).
- **HTTP-shim contract doc — customer's INBOUND `/internal/*` (the endpoints customer EXPOSES, that its callers froze):**
  - `customer-svc GET /internal/seller-profile/{user_id}/compliance-block` ← `get_compliance_block(user_id) -> ComplianceBlock` — **FROZEN by SUB_PLAN_0A (export), spec_msA_backend.md:181.** Serializes the 10-field `ComplianceBlock` dataclass (`domain.py:75`) to JSON; export-svc + monolith-catalog deserialize into their vendored `ComplianceBlock` copy. ZERO shape drift.
  - `customer-svc GET /internal/seller-profile/{user_id}/completeness` ← `get_onboarding_completeness(user_id) -> ProfileCompleteness` — **DRAFT-PENDING-0B-RECONCILE** (§1.1). Serializes the 5-int/bool `ProfileCompleteness` dataclass (`domain.py:97`: `base_complete_count`, `base_total_count`, `extension_complete_count`, `extension_total_count`, `onboarding_complete`). Shape proposed here; FROZEN by SUB_PLAN_0B; reconcile before customer execution.
  - `customer-svc POST /internal/seller-profile/{user_id}/eligibility/{super_id}` ← `assert_eligible_for_super_id(user_id, super_id) -> None` — **FROZEN by SUB_PLAN_0H (catalog)**, but catalog stays in-monolith until MS-5, so the monolith-side `customer_client` (§4) is the first consumer. Returns 204 on eligible, 422 `customer.profile.incomplete_for_category` envelope on miss (the `ProfileIncompleteForCategoryError` shape, `exceptions.py:155`). Reconcile the exact path/verb with SUB_PLAN_0H before catalog's MS-5 execution.
- **HTTP-shim contract doc — customer's OUTBOUND `/internal/*` (the endpoint customer CONSUMES):**
  - category-svc `GET /internal/super-categories` ← replaces `SELECT DISTINCT super_id FROM categories` (§3 E3-A). Returns `list[str]`. **DRAFT-PENDING-0F-RECONCILE** — category-svc (SUB_PLAN_0F, MS-4) must implement; during MS-3 the shim points at monolith ClusterIP. Escalate to master session if SUB_PLAN_0F's shape differs.
- **Shared domain-object serialization note** — `ComplianceBlock` (export/catalog) and `ProfileCompleteness` (dashboard) are frozen dataclasses crossing the HTTP boundary. The `/internal/*` JSON shape MUST be the dataclass field set, in field order, with zero added/dropped keys. The caller deserializes into its vendored copy. The integration test (§6) asserts byte-equivalence of the dataclass round-trip in-process vs over-HTTP.
- **LIVE frontend contract preservation** — the 5 public `/api/v1/seller-profile/*` responses are LIVE with the Angular onboarding wizard (Wave-6B wiring). `SellerProfileResponse` (`schemas.py:42`) + `RequiredFieldsResponse` (`schemas.py:146`) shapes are FROZEN — ZERO response-shape drift allowed across the extraction. The extracted router moves verbatim; the integration test asserts identical JSON for all 5 endpoints monolith-vs-customer-svc.
- **`BACKEND_ARCHITECTURE.md §8` amendment** ("Extracted to customer-svc V1.5" note) — **§8.B is LOCKED → FOUNDER APPROVAL REQUIRED** before this amendment lands. Do NOT self-amend a LOCKED section (§7.3 of repo-management master plan).
- **`MASTER_PLAN.md §4 row E** annotation flip ("Sub-Plan E authored 2026-06-12; execution GATED MS-3").
- **`docs/runbooks/customer-svc-rollback.md`** (§3.C rollback specialized for customer; includes the seller_profile schema→public restore + the monolith-catalog `customer_client` revert).
- **Hybrid-mode CI config note** — during customer extraction, customer's callers (export-svc MS-1, dashboard-svc MS-2) are already standalone and must be docker-composed to exercise the inbound shims; customer's OUTBOUND category read points at the in-process monolith (category not yet extracted). The monolith (with catalog still in it) must also run to exercise the monolith-catalog → customer-svc reverse shim.

---

## 6. Validation (merge-gate, lead-owned)

- Full backend suite `def test_` count MONOTONIC ≥ 649 baseline (§0.9) — quote LIVE count at PR time; do NOT hardcode.
- Customer's own 45 tests green in BOTH the monolith (pre-flip, in-process) AND the extracted customer-svc (or no-tunnel baseline: pure-function/contract subset green, infra-gated skips/errors documented per the auth-otp no-tunnel pattern).
- `ruff` clean on `backend/services/svc-customer/`.
- import-linter: the customer-svc tree must NOT re-introduce a cross-schema ORM read of `categories` (the E3-A shim replaces it). The §16 contracts (service.py PUBLIC, repository.py PRIVATE) hold inside the extracted tree.
- **NO tautological tests (the pricing reject-class lesson).** The hybrid-mode integration test MUST assert REAL behavior: (a) a `get_compliance_block` shim call returns a `ComplianceBlock` whose 10 fields equal the in-process result; (b) a `get_onboarding_completeness` shim returns identical 5-field counts; (c) `assert_eligible_for_super_id` raises the 422 envelope on a profile missing a compulsory compliance key; (d) an `audit_events` row lands in `public.audit_events` on a PATCH (cross-schema INSERT grant). NOT `assert True`-class echoes.
- LIVE frontend contract: all 5 public endpoints return byte-identical JSON monolith-vs-customer-svc for a golden profile fixture (zero response-shape drift, Wave-6B onboarding).
- HTTP-shim contract doc complete (3 inbound + 1 outbound, source-cited); 0B + 0F reconcile flags resolved or master-session-escalated.
- Rollback runbook present (§3.C strangler-fig contract).

---

## 7. Caching surface — what moves with customer-svc

Customer uses Valkey DB 3 (application cache) via `core/cache.get_or_set`. Two cache keys move with the service (per §2.E, re-prefixed `customer:`):
1. `customer.required_fields.{user_id}` (`service.py:317`) — TTL 60s (`service.py:75`), single_flight=False, invalidated on every PATCH via `_invalidate_required_fields_cache` (`service.py:320`, which builds the full key `meesell:{CACHE_VERSION}:customer.required_fields.{user_id}` at `service.py:327` and `DELETE`s it).
2. `customer.super_category_set` (`service.py:85`) — TTL 3600s (`service.py:80`), single_flight=True. **This is the cache fronting the §3 cross-schema read.** Under E3-A the cache contract is UNCHANGED; only the loader (`_load_super_id_set`) swaps SQL→HTTP. The cached value stays a `list[str]`.

The Valkey instance is SHARED across services (§2.E); customer-svc connects to the same Valkey DB 3 with the `customer:` key prefix. No data migration — keys are short-TTL and self-heal on first miss.

---

## 8. Database surface — schema-split for `seller_profile`

Mirrors MS-A's `exports`-schema move, specialized for `seller_profile`:
- Alembic schema-split migration: upgrade `ALTER TABLE seller_profile SET SCHEMA customer`; tested downgrade `SET SCHEMA public`.
- `version_table_schema="customer"` so customer-svc's `alembic_version` lands in the `customer` schema.
- **Cross-schema FK drop (Risk #5):** `seller_profile.user_id → users.id` (CASCADE) is a cross-schema FK after isolation. Per §2.D it is DROPPED at customer's cutover; app-layer `scope_to_user` (every repo method, §0.6) + an integrity pre-scan (verify every `seller_profile.user_id` resolves to a real `users` row BEFORE the FK drop, emit scan output to a migration log) is the defense. The SQLAlchemy `relationship("User", back_populates="seller_profile")` (`seller_profile.py:116`) + the matching `User.seller_profile` back-ref must be SEVERED in the customer-svc vendored ORM (customer-svc cannot import the iam `User` model — it lives in iam's schema). The `seller_profile` ORM in customer-svc keeps `user_id` as a plain UUID PK with NO `ForeignKeyConstraint` and NO `relationship`.
- GIN index `idx_seller_profile_super_cats` (`seller_profile.py:131`) moves with the table.
- Alembic discipline (MS-A pattern): dev applied BEFORE staging — NEVER reverse (head divergence dev↔staging = P0 escalate to founder immediately).

---

## 9. Builder sequence (3-phase, per SUB_PLAN_01 §"Dispatch order", specialized for customer)

```
PHASE A (parallel — no inter-dependency):
  meesell-database-builder → Alembic schema-split (seller_profile public→customer schema),
                             version_table_schema="customer", Risk#5 integrity pre-scan,
                             FK + relationship sever, tested downgrade
  [INFRA LANE — meesell-infra-builder, NOT a backend specialist — see handoff_msE_infra.md]

PHASE B (depends on A — service code targets the new schema):
  meesell-services-builder  → extract service.py + repository.py + domain.py + exceptions.py;
                              the E3-A category_client OUTBOUND shim (replaces the cross-schema
                              categories read); the 3 INBOUND /internal/* handlers
                              (get_compliance_block, get_onboarding_completeness,
                              assert_eligible_for_super_id); trimmed Settings; standalone main.py
                              (6-mw chain, plan_guard NO-OP); NO Celery app
  meesell-api-routes-builder→ extract router.py + schemas.py into standalone routes (5 public);
                              wire the 3 /internal/* routes onto the service surface;
                              regenerate OpenAPI
    (api-routes can start once services-builder freezes the service-method signatures —
     near-parallel within Phase B)

PHASE C (depends on B — integration; LEAD-owned, not specialist):
  meesell-backend-coordinator → monolith-side customer_client reverse shim (catalog call sites
                                §4); hybrid-mode CI wiring (in-process + HTTP-shim per §3.A);
                                test_customer_extraction.py; merge-gate review STEP 3;
                                board MERGED flip
```

**Recommended dispatch order:** `database-builder` (Phase A) FIRST + IN PARALLEL
with the infra handoff → then `services-builder` (Phase B, the heavy lift incl. the
E3-A outbound shim + 3 inbound handlers) → then `api-routes-builder` (Phase B, once
service signatures frozen) → then lead Phase C. Iteration cap 3 per specialist.

---

## 10. Branch plan (Model C — per SUB_PLAN_01 + dispatch common-rule 6)

Cut from **origin/develop** at execution time (§0.1). The doc-deliverable worktree
is already on `feature/microservices-customer/integration`; the EXECUTION branches
(`/backend`, `/infra`) are cut at MS-3 dispatch, not now.

| Branch | Cut from | Purpose | Who commits |
|---|---|---|---|
| `feature/microservices-customer/integration` | `origin/develop` | Integration; merge commits only; F3 protection at creation | backend lead (group gate) + founder (integration→develop gate) |
| `feature/microservices-customer/backend` | `…/integration` | All backend specialist extraction work | backend specialists |
| `feature/microservices-customer/infra` | `…/integration` | Dockerfile, K8s, Postgres schema/role, Traefik route, secrets | meesell-infra-builder |

Worktrees per dispatch under `/tmp/mesell-wt/msE-*`. NEVER `git add -A` in a
symlinked worktree — scope every stage to the exact `backend/services/svc-customer/`
path (MS-A op-learning). PR flow: group → integration = LEAD gate (squash);
integration → develop = **FOUNDER gate (left OPEN — lead does NOT approve)**, per D1.

```
feature/microservices-customer/backend ─(backend lead; squash)─┐
                                                               ├─► feature/microservices-customer/integration ─(FOUNDER; merge-commit)─► develop
feature/microservices-customer/infra   ─(infra lead; squash)───┘
```

---

## 11. Constraints honored (from dispatch + MASTER_PLAN)

- dev cluster / dev namespace ONLY; current hardware (customer-svc api 50m/128Mi req — query-light, no worker, no AI — fits current node per MASTER_PLAN §3.A.1 / MS-PAR-1 D3 checkpoint). NO D3 VM change at authoring; the spend gets a FRESH founder ask only when a wave's deploy doesn't fit the node (master-session standing rule). customer is small and parallel with pricing (also small) at MS-3 — D3 checkpoint re-evaluated by the master session at the MS-3 deploy.
- Infra surfaces (Dockerfile, k8s, Traefik, Postgres role/schema, secrets) = INFRA HANDOFF (see `handoff_msE_infra.md`), NOT specialist work.
- PgBouncer (MS-DB-4) NOT a customer blocker (dev/zero-traffic); MS-DB-3 pool right-size proceeds in the infra lane (MS-0 wave).
- Strangler-fig: monolith keeps serving `/api/v1/seller-profile/*` until the founder-gated cutover flip; rollback per §3.C / the runbook.
- NO frontend, NO k8s/terraform, NO Gemini prompt work in the backend lane (redirect per scope rules).

---

## Document Header Metadata

| Field | Value |
|-------|-------|
| Document type | Microservices extraction sub-plan E (customer) |
| Status | AUTHORED 2026-06-12 — EXECUTION GATED (MS-3) |
| Produced by | meesell-backend-coordinator (`mesell-ms-customer-session-1`, HYBRID step 1) |
| Grounding tree | develop `c859955` |
| Cross-references | `MASTER_PLAN.md` v1.3 §1.A/§1.C/§2.B/§2.C/§2.D/§3.B/§3.C/§5/§6; `SUB_PLAN_01_export_extraction.md`; `spec_msA_backend.md`; `BACKEND_ARCHITECTURE.md §8` (LOCKED); the parallel-program dispatch doc |
| Open contract questions | (1) dashboard `/internal/*` completeness shape — DRAFT-PENDING-0B-RECONCILE (§1.1); (2) category `/internal/super-categories` shape — DRAFT-PENDING-0F-RECONCILE (§3) |

---

## Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| v1 | 2026-06-12 | `mesell-ms-customer-session-1` (meesell-backend-coordinator, hybrid step 1) | Initial AUTHORED — EXECUTION GATED MS-3. Grounded against develop `c859955`, all enums/contracts/signatures cited file:line from SOURCE. Three as-built corrections over the dispatch premise recorded: (1) customer's inbound surface is 3 distinct methods across 3 callers (not just the export `get_compliance_block`); (2) customer is NOT a pure callee — it reads `categories` directly via ORM (`service.py:347`), a cross-schema read needing the E3-A shim; (3) COMPLIANCE_EXTENSION_MAP is 11 keys / 6 source rules (not "6 super_ids"). Two cross-sub-plan contract reconciles flagged for master-session escalation (0B dashboard, 0F category). |

---

**END OF SUB-PLAN E — AUTHORED 2026-06-12, EXECUTION GATED MS-3.**
