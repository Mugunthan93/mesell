# SUB-PLAN B — `dashboard` Service Extraction

**STATUS: DRAFT — awaiting founder review.** Authored under session
`mesell-ms-dashboard-session-1` (2026-06-12, HYBRID rule STEP 1 — SPEC/docs
only; no extraction code, no git ops). This is the **second** extraction
sub-plan of the Microservices Migration MASTER_PLAN (LOCKED 2026-06-10, v1.3).
It implements MASTER_PLAN §4 row **B** (`dashboard`, complexity **S**,
blocking dep: A complete).

> **Execution gate — WAVE MS-2 (parallel with MS-C `image`).** Per the
> founder-ruled parallel program (MS-PAR-1, `00-ms-parallel-program-dispatch.md`),
> the LOCKED serial order is upgraded to pilot-alone → parallel-pairs →
> riskiest-last. **Phase 1 (this document) is docs-only and authored NOW, in
> parallel with all other sub-plans.** **Phase 2 (execution) is GATED: it
> begins only when (a) Sub-Plan A's founder gate is merged to `develop` AND
> (b) the validated MS-A extraction recipe exists in the backend lead's
> memory** (`.claude/agent-memory/meesell-backend-coordinator/` —
> `spec_msA_backend.md` is the pattern; the recipe is recorded post-MS-A
> merge per the MS-A session deliverable). Until both hold, dashboard stays
> READY-TO-EXECUTE (pending MS-2 open), not IN EXECUTION.
>
> **D3 VM checkpoint.** The current `e2-standard-2` node fits roughly the
> monolith + 2–3 small services. `dashboard` owns ZERO tables and is the
> SMALLEST service (a thin BFF pod), so it fits the current node at the
> locked 50m-CPU-request sizing alongside the monolith remnant + svc-export.
> **No VM upgrade is triggered by Sub-Plan B.** The D3 spend
> (`e2-standard-4`, ~₹2,600/mo — plan-level pre-approval only per MASTER_PLAN
> §3.A.1) gets an EXPLICIT FRESH founder ask at the moment services outgrow
> the node — a later-wave event, NOT here. If the MS-2 deploy (monolith +
> svc-export + svc-dashboard + svc-image) overflows the node, STOP and ask
> the founder before any upgrade spend.
>
> **Parallel-lane discipline with MS-C (`image`).** dashboard's diffs stay in
> dashboard surfaces (`backend/services/svc-dashboard/**`). Shared files
> (`backend/app/main.py` router removal at cutover, gateway/Traefik config,
> `k8s/` shared manifests) get **minimal + additive** edits only; the
> integration branch merges `origin/develop` BEFORE the founder-gate PR
> opens; union-merge conflicts keep-both. image and dashboard touch DISJOINT
> service trees, so the only contention is the additive main.py mount-removal
> + the shared Traefik routing table — both additive/keep-both.

> Authoritative inputs read for this sub-plan:
> - `docs/plans/microservices_migration/MASTER_PLAN.md` (LOCKED v1.3 — §1.A/§1.C/§1.D, §2.B/§2.C/§2.D, §3.A/§3.A.1/§3.B/§3.C, §5.A/B/C/D/E/F, §6 risks)
> - `docs/plans/microservices_migration/SUB_PLAN_01_export_extraction.md` (the SHAPE TEMPLATE — canonical section structure mirrored here)
> - `docs/sub_session_prompts/microservices_execution/00-ms-parallel-program-dispatch.md` (MS-PAR-1 wave structure + 9 common rules)
> - `.claude/agent-memory/meesell-backend-coordinator/spec_msA_backend.md` + `handoff_msA_infra.md` (MS-A shim conventions — REUSED here)
> - `docs/BACKEND_ARCHITECTURE.md` §13 (dashboard module contract, LOCKED 2026-06-05, AMENDED §13.A.1 2026-06-07), §10.C (catalog `list_products`), §8.C (customer `get_onboarding_completeness`), §16 (inter-module rules), §16.G (call-site preservation), §21 (extraction roadmap)
> - As-built source (worktree `/tmp/mesell-wt/msB-docs` @ `origin/develop` `c859955`): `backend/app/modules/dashboard/` (6 files), `backend/app/main.py`, the catalog + customer callee signatures, `backend/tests/modules/dashboard/`, `backend/tests/integration/test_dashboard_*.py`

---

## 0. GROUND TRUTH — re-verified against SOURCE 2026-06-12 (worktree @ `c859955`)

The MASTER_PLAN §1.C call-matrix prose names dashboard's two callees as
`get_profile_completeness` and `list_products(user_id, Pagination)`. **One is
WRONG against source.** Per the Wave-6 no-invented-shapes discipline (rule 3),
every claim below is cited file:line from the AS-BUILT worktree, NOT plan prose.

### 0.1 Branch / tree state — TRUE tip

- **Worktree `/tmp/mesell-wt/msB-docs` HEAD = `c8599556cce073f4c38f8528ca578dd96105cfc1`** (= `c859955`), branch
  `docs/msB-subplan-0B`, tracking `origin/develop`. `git ls-remote origin develop` = the SAME `c859955`. The worktree IS the AS-BUILT current develop. No divergence (unlike the MS-A session, which found a stale local `develop` at `f23d84a`).
- **CONSEQUENCE:** Phase 2 cuts all branches from `origin/develop` (re-verify the live tip at dispatch time — develop will have moved past `c859955` by the time MS-2 opens, since MS-A merges first). Do NOT branch off a stale local develop.

### 0.2 Dashboard module = 6 files — CONFIRMED (5 logical + the deliberate no-repository deviation)

`backend/app/modules/dashboard/`: `__init__.py`, `domain.py`, `exceptions.py`,
`router.py`, `schemas.py`, `service.py` = **6 files**. **There is NO
`repository.py`** — a deliberate structural deviation from the §3.C canonical
7-file layout, LOCKED at §13.D and documented in `__init__.py:9-11`. dashboard
**owns ZERO tables** and reads NOTHING directly. The §19 CI linter
(`check_scope_to_user`) allowlists dashboard's no-repository exception
(`__init__.py:9` + domain.py docstring). `domain.py` is an empty-but-legal
module (`domain.py:__all__ = []`) — dashboard imports catalog/customer domain
types rather than declaring its own (per §16 Rule 4, domain.py is the
cross-module exchange currency).

### 0.3 NO ai_ops, NO Celery — CONFIRMED

- `grep ai_ops backend/app/modules/dashboard/` = **ZERO refs.** dashboard is a
  pure read; it makes NO AI calls. The svc-dashboard `requirements.txt` carries
  NO gemini/langfuse. A1/D6 (ai_ops vendored per AI-consuming service) does NOT
  touch dashboard.
- **NO `tasks.py`** in the dashboard subtree — dashboard has no Celery work.
  svc-dashboard ships NO Celery app, NO worker pod, NO broker/result Valkey DB
  1/2 usage. This is a key SIMPLIFICATION vs svc-export (which carried a
  single-task Celery app). svc-dashboard is api-only.

### 0.4 The MOUNTED route inventory — enumerated from `router.py` decorators (the row-26 lesson)

dashboard mounts **exactly 1 route** (NOT counted from plan prose — counted
from the `@router.<verb>` decorators in `router.py`):

| # | Route (verbatim from `router.py`) | Method | Status | Decorators / deps | Source |
|---|---|---|---|---|---|
| 1 | `/api/v1/products` | GET | 200 (`response_model=DashboardResponse`) | `@rate_limit(scope="dashboard_list", limit=600, window=3600)` (router.py:86); `Depends(get_current_user)` (router.py:88) + `Depends(get_db)` (router.py:89); `page: Query(ge=1)=1` + `limit: Query(ge=1, le=100)=20` | `router.py:81-92` |

`router = APIRouter(prefix="/api/v1", tags=["dashboard"])` (router.py:75). The
single handler `list_products` (router.py:87). **Mount:** `main.py:43`
`from app.modules.dashboard import dashboard_router`; `main.py:141`
`app.include_router(dashboard_router)` (the §13 comment block sits at
main.py:136-140). **NOTE on the path-key collision (§13-DASHBOARD-D2,
router.py:44-51):** `GET /api/v1/products` shares the path-key
`/api/v1/products` with catalog's `POST /api/v1/products`. FastAPI registers
them as **two distinct `APIRoute` objects** under one path key. This is a
LIVE concern for the Traefik routing table in §"Code surfaces" / the infra
handoff — Traefik must route by METHOD or path-prefix, because
`GET /api/v1/products` → svc-dashboard while `POST /api/v1/products` →
svc-catalog (which extracts LAST, at MS-5). Until catalog extracts, BOTH
share the monolith; the dashboard GET is the ONLY one routed to svc-dashboard
at MS-2.

### 0.4-FLAG Feature-flag guard — LIVE, must be preserved

`router.py:118` gates the handler behind
`if not settings.FEATURE_TRACKING_DASHBOARD_ENABLED: raise HTTPException(404,
"Tracking Dashboard is disabled in this environment")` — the D3 kill-switch
(404-on-read is intentional per the tracking-dashboard FEATURE_PLAN §2.2,
landed via the flag-parity sweep `mesell-flag-parity-sweep-session-1`). The
extracted svc-dashboard MUST carry `FEATURE_TRACKING_DASHBOARD_ENABLED` in its
trimmed Settings and preserve this guard byte-for-byte. (Infra: the flag is
injected via ConfigMap — see infra handoff.)

### 0.5 The 2 cross-module call sites — RE-CITED FROM SOURCE (plan mis-named 1 of them)

Authoritative list of every `<callee>_service.<method>` invocation in
`backend/app/modules/dashboard/service.py`:

| # | Call site (dashboard/service.py) | Callee method (signature cited from callee SOURCE) | Returns (frozen domain type) |
|---|---|---|---|
| 1 | `:78` `catalog_service.list_products(user_id=user_id, pagination=pagination, db=db)` | `catalog/service.py:999` `list_products(user_id: UUID, pagination: Pagination, db: AsyncSession) -> PaginatedProductsInternal` | `PaginatedProductsInternal` (`catalog/domain.py:170` — `items: tuple[Product, ...]`, `total: int`, `page: int`, `limit: int`) |
| 2 | `:84` `customer_service.get_onboarding_completeness(user_id=user_id, db=db)` | `customer/service.py:682` `get_onboarding_completeness(user_id: UUID, db: AsyncSession) -> ProfileCompleteness` | `ProfileCompleteness` (`customer/domain.py:98` — 5 ints/bool: `base_complete_count`, `base_total_count`, `extension_complete_count`, `extension_total_count`, `onboarding_complete`) |

**PLAN-TEXT CORRECTIONS (Wave-6 no-invented-shapes discipline):**

- MASTER_PLAN §1.C row "dashboard → customer" names the method
  **`get_profile_completeness`**. **WRONG against source.** The live method is
  **`get_onboarding_completeness`** (`customer/service.py:682`,
  `dashboard/service.py:84`, `__init__.py:15`). `grep get_profile_completeness
  backend/app/modules/customer/` = 0 runtime defs. The dispatch prompt's
  grounding facts also said `get_profile_completeness` — both are stale; the
  AS-BUILT name is `get_onboarding_completeness`. The §8.C-era memory note
  ("get_profile_completeness consumed by dashboard") reflects an early §8 LOCK
  name that was renamed during construction.
- MASTER_PLAN §1.C "dashboard → catalog" names `list_products(user_id,
  Pagination)`. The AS-BUILT signature is keyword `pagination:` (lowercase),
  carrying a `catalog.domain.Pagination` frozen dataclass (`catalog/domain.py:219`,
  2 fields `page`/`limit` per the §13.A.1 amendment). CONFIRMED — the only
  nuance is the kwarg name + the lowercase param.
- **ADDITIONAL domain-imports (NOT service calls, no shim):**
  `dashboard/service.py:36-42` imports `catalog.domain.{PaginatedProductsInternal,
  Pagination}` + `customer.domain.ProfileCompleteness`. These are the §16
  "domain exchange currency" pattern. In the extracted service they become
  **vendored copies** of those 3 dataclass shapes (the HTTP shim deserializes
  the callee-svc JSON into the local vendored dataclass) — NOT HTTP calls.
  `dashboard/domain.py` itself declares NO types (`__all__ = []`), so the
  vendored shapes live as small local dataclasses inside the shim modules.

### 0.6 Dashboard is a LEAF CONSUMER — zero inbound callers → NO `/internal/*` to expose

`grep -rn "modules.dashboard\|modules import dashboard" backend/app --include=*.py`
(excluding the dashboard subtree itself) = **only `main.py:43`** (the mount).
**NOTHING in the codebase imports from `app.modules.dashboard.*`** — confirmed
by `__init__.py` ("No other module reads from dashboard"). dashboard is a leaf
consumer on the §2.D matrix (it CALLS catalog + customer; nobody calls it).
**CONSEQUENCE:** svc-dashboard exposes **NO `/internal/*` routes** (no inbound
callers). It is purely an OUTBOUND shim consumer — like svc-export. The
MASTER_PLAN §4 row B note about "the optional dashboard-OPTIONAL summary
surface" (a dashboard→export call) is **NOT wired in V1**: dashboard's §2.D
matrix is held at exactly 8 ✓ (it does NOT opt into export/image/pricing
`.summary` OPTIONAL surfaces per the §13 LOCK — a V1.5 elevation, NOT V1). So
svc-dashboard has exactly **2 outbound shims** (catalog + customer), zero
inbound.

### 0.7 A2 (middleware vendored, local JWT) — applies; dashboard uses 5 of 6

svc-dashboard vendors the 6-mw chain (CORS → request_id → auth_mw → tenancy_mw
→ rate_limit_mw → plan_guard_mw → audit_mw). `plan_guard_mw` RUNS but is NO-OP
for dashboard (dashboard is one of the 3 plan_guard-EXCLUDED modules alongside
customer + pricing per §13.I). `audit_mw` RUNS but writes NOTHING (read-only
GET, NONE audit posture per §13.B / router.py:21). JWT verified LOCALLY via
vendored `core/auth.py` + shared `JWT_SECRET` (D7/A2). So dashboard exercises
~4 effective middlewares (CORS, request_id, auth, tenancy + rate_limit), with
plan_guard + audit present-but-inert.

### 0.8 D5 / PgBouncer sequencing — dev-scope read (SAME as MS-A)

Infra plan §3.2 / §6.3 (APPROVED v1.1): **MS-DB-3** (per-service pool
right-size in code + `max_connections=200`) ships BEFORE any service moves.
**MS-DB-4** (PgBouncer transaction-pool) is mandatory before traffic-bearing
PROD cutover — NOT before a dev extraction. dashboard is **dev-only /
zero-traffic** → PgBouncer is NOT a Sub-Plan-B blocker. **Special case:
dashboard owns ZERO tables → it has the SMALLEST DB footprint of any service.**
It connects to Postgres ONLY for the vendored `audit_mw` no-op path and the
shared `get_db` dependency wiring (which it passes through to the HTTP shims —
the shims do their OWN DB access on the callee side). In practice
svc-dashboard's DATABASE_URL is needed only because the vendored middleware
chain + `Depends(get_db)` signature expect a session; its query volume is ~0.
A very small pool (2–3 conns) suffices.

### 0.9 Test count — re-counted from SOURCE (the "823+" floor is a parametrize-expanded figure, not the `def test_` count)

`grep -rn "def test_" backend/tests/` = **698** test functions in the worktree
(higher than MS-A's 649 baseline — develop advanced between sessions).
dashboard's own = **36** (`tests/modules/dashboard/` 4 files —
`test_empty_state.py`, `test_feature_flag.py`, `test_pagination_validation.py`,
`test_response_composition.py` + `conftest.py` + `__init__.py`; plus
`tests/integration/test_dashboard_list_flow.py` +
`test_dashboard_cross_tenant.py`). The "~823+" figure in the common-rules
prompt is a COLLECTED-items count (parametrize expansion), NOT the `def test_`
count. **Validation rule for the merge gate: the full-suite `def test_` count
must be MONOTONIC (≥ the live baseline at PR time — re-count at dispatch since
develop moves) — the extraction ADDS svc-dashboard tests, removes none until
the strangler 7-day window closes.** Do NOT hardcode 823 or 698; re-count and
quote the live count at PR time (the MS-A lesson §0.9).

---

## Decisions

This section records the Sub-Plan-B-time decisions. **All inherit from
MASTER_PLAN's already-LOCKED rulings (D6/D7/A1/A2) — there is NOTHING new to
ratify here.** dashboard is the second extraction; the shim/middleware/ai_ops
conventions were all locked at MS-A.

### B1 — `ai_ops/` placement — NOT APPLICABLE (dashboard makes zero AI calls)

dashboard is a **pure read** — `grep ai_ops backend/app/modules/dashboard/` =
0 (§0.3). The A1/D6 ruling (ai_ops vendored per AI-consuming service) does NOT
touch dashboard. svc-dashboard ships NO ai_ops, NO gemini/langfuse deps.
**No decision required.**

### B2 — Shared `core/middleware/` placement — INHERITED LOCK (D7/A2, Option A)

Per MASTER_PLAN §5.A (LOCKED via founder ruling D7, 2026-06-10): the
6-middleware chain is VENDORED per service; JWT verification runs LOCALLY in
every service; gateway-JWT is REJECTED. svc-dashboard vendors the 6-mw chain
(plan_guard + audit present-but-inert per §0.7). **No decision required —
inherited from MS-A's A2 lock.**

### B3 — Extraction order — dashboard SECOND (CONFIRMATION of locked order)

**Question:** Confirm `dashboard` is the second extraction (first of the MS-2
parallel pair, alongside `image`).

**Answer:** CONFIRMED. MASTER_PLAN §3.B locks the order
`export → dashboard → image → ...`; the MS-PAR-1 wave structure runs
`dashboard ‖ image` as the MS-2 parallel pair, gated on A's founder gate.
dashboard is positioned second because:
- **Owns ZERO tables** (§13.D structural exception) — NO data migration, NO
  schema-split Alembic, the smallest possible extraction.
- **Pure composition over catalog + customer** — extracts as a thin BFF pod.
- **Leaf consumer** (§0.6) — zero inbound callers, so extracting it produces
  ZERO ripple in any other module's code (identical to export's "zero
  downstream consumers" property — both are leaf consumers).
- It exercises the **outbound** HTTP-shim path (2 shims) and reuses the shim
  infrastructure MS-A built; it adds NO new inbound-shim surface.

**Not locked here — already locked at §3.B + MS-PAR-1.** B3 is a confirmation.

### B4 — dashboard owns NO schema → `meesell-database-builder` is a VERIFY-ONLY dispatch

Unlike svc-export (which moved its `exports` table to a dedicated schema),
**svc-dashboard owns ZERO tables → there is NO schema-split migration, NO new
Alembic chain.** dashboard reads catalog + customer data exclusively via HTTP
shims; it never owns a table. The `meesell-database-builder` dispatch is
therefore a **VERIFY-ONLY** task (confirm no table/model/migration is
introduced; confirm svc-dashboard's DATABASE_URL points at NO owned schema —
it uses the shared-session wiring for the middleware/`get_db` signature only,
per §0.8). This is the cheapest database lane of any extraction.

---

## Agent lineup

| Lead | Specialists dispatched | What each specialist builds |
|---|---|---|
| `meesell-backend-coordinator` (lead) | — | Authors this sub-plan; owns the merge gate for `feature/microservices-dashboard/backend` → `feature/microservices-dashboard/integration`; reviews extracted code against §16.G call-site-preservation contract; updates `feature_board_backend.md`. Does NOT approve integration→develop (founder gate, D1). |
| `meesell-backend-coordinator` → `meesell-services-builder` (opus) | `meesell-services-builder` | The heavy lift. Extracts `service.py` + `domain.py` + `exceptions.py` into `backend/services/svc-dashboard/app/`; writes the **2** outbound HTTP-shim clients (`catalog_client`, `customer_client`) under `core/extracted_clients/`; vendors the 3 callee domain dataclasses (`PaginatedProductsInternal`, `Pagination`, `ProfileCompleteness`); preserves the §16.G call sites (`:78`, `:84`) byte-for-byte; builds the standalone `main.py` (5-effective-mw chain, NO Celery app). |
| `meesell-backend-coordinator` → `meesell-api-routes-builder` (sonnet) | `meesell-api-routes-builder` | Splits `router.py` into the new service's **1** public route (`GET /api/v1/products`); preserves the `@rate_limit(scope="dashboard_list", limit=600, window=3600)` decorator + the `FEATURE_TRACKING_DASHBOARD_ENABLED` 404 guard; confirms NO `/internal/*` route is needed (dashboard has zero inbound callers); moves `schemas.py`; regenerates the standalone OpenAPI. |
| `meesell-backend-coordinator` → `meesell-database-builder` (sonnet) | `meesell-database-builder` | **VERIFY-ONLY (B4).** Confirms svc-dashboard owns ZERO tables, introduces NO model/migration/Alembic chain, and its DATABASE_URL maps to NO owned schema. Emits a one-line "no schema work" attestation for the merge gate. NO migration authored. |
| `meesell-infra-builder` (standalone, via cross-lead memo) | — | Authors `svc-dashboard` Dockerfile, K8s Deployment + Service (api-only, NO worker), Traefik IngressRoute (`GET /api/v1/products` → svc-dashboard, METHOD-or-prefix-aware per §0.4 path-key collision), the `FEATURE_TRACKING_DASHBOARD_ENABLED` ConfigMap injection, the `INSERT ON public.audit_events` grant (for the inert audit_mw path), and the trimmed secret set. **Infra work is OWNED by infra lead** — see `handoff_msB_infra.md`. |

### Dispatch order (critical path)

```
PHASE A (parallel — no inter-dependency):
  meesell-database-builder  →  VERIFY-ONLY attestation (zero tables, no migration) — TRIVIAL, can run anytime
  [INFRA LANE — meesell-infra-builder, NOT a backend specialist — see handoff_msB_infra.md]

PHASE B (depends on nothing schema-side — dashboard owns no schema):
  meesell-services-builder  →  extract service.py + domain.py + exceptions.py; 2-shim (catalog+customer) under core/extracted_clients/; vendor 3 callee dataclasses; trimmed Settings; standalone main.py (5-effective-mw, NO Celery)
  meesell-api-routes-builder→  extract router.py (1 route) + schemas.py; preserve rate_limit + FEATURE_TRACKING_DASHBOARD_ENABLED guard; NO /internal/*; regenerate OpenAPI
    (api-routes can start once services-builder freezes the service-method signature — practically near-parallel within Phase B)

PHASE C (depends on B — integration; LEAD-owned, not specialist):
  meesell-backend-coordinator → hybrid-mode CI wiring (in-process + HTTP-shim per §3.A); test_dashboard_extraction.py; merge-gate review STEP 3; board MERGED flip
```

**Recommended dispatch order:** `database-builder` (Phase A, VERIFY-ONLY — trivial) IN PARALLEL with the infra handoff → then `services-builder` (Phase B, the heavy lift) → then `api-routes-builder` (Phase B, once the service signature is frozen) → then lead Phase C. **Iteration cap 3 per specialist** (the SUB_PLAN_01 review protocol); the 3rd re-dispatch on any specialist triggers a founder consult.

---

## Branch setup (Model C — per SUB_PLAN_01 §"Branch setup" + MS-PAR-1 rule 6)

Cut from `origin/develop` (re-verify the live tip at dispatch — develop will
have moved past `c859955` once MS-A merges).

| Branch | Cut from | Purpose | Who commits |
|---|---|---|---|
| `feature/microservices-dashboard/integration` | `origin/develop` | Integration; merge commits only; F3 protection (PR-only, review-count **0**, checks=[], no force-push/deletions, enforce_admins false) applied at creation | backend lead (merge approval) + founder (integration→develop gate) |
| `feature/microservices-dashboard/backend` | `…/integration` | All backend specialist extraction work | backend specialists |
| `feature/microservices-dashboard/infra` | `…/integration` | Dockerfile, K8s, Traefik route, ConfigMap flag, audit grant | meesell-infra-builder (infra lane) |

Worktrees per dispatch under `/tmp/mesell-wt/msB-*` (e.g.
`/tmp/mesell-wt/msB-services`, `/tmp/mesell-wt/msB-routes`,
`/tmp/mesell-wt/msB-db`). NEVER `git add -A` in a symlinked worktree — scope
every stage to the exact `backend/services/svc-dashboard/` path (the MS-A /
PILOT op-learning).

**PR flow:** group → integration is the LEAD gate (squash). integration →
develop is the **FOUNDER gate (left OPEN — I do NOT approve it)**, per D1.

```
feature/microservices-dashboard/backend ─(backend lead; squash)─┐
                                                                ├─► feature/microservices-dashboard/integration ─(FOUNDER; merge-commit)─► develop
feature/microservices-dashboard/infra   ─(infra lead; squash)───┘
```

**Parallel-lane note (MS-PAR-1 rule 4):** MS-C (`image`) runs concurrently.
Both integration branches merge `origin/develop` BEFORE their founder-gate PR
opens. The only shared-file contention is `backend/app/main.py` (each removes
its own router mount at cutover — additive, disjoint lines) + the shared
Traefik routing table (each adds its own path route — additive, keep-both).
dashboard touches `GET /api/v1/products`; image touches
`/api/v1/products/{id}/images*` — DISJOINT path prefixes, so no Traefik
conflict.

---

## Code surfaces

File-level inventory of the dashboard extraction. Paths are project-relative.
The `backend/services/svc-dashboard/` tree is the new home; the old
`backend/app/modules/dashboard/` tree is DELETED only after hybrid-mode CI
passes for ≥7 days (per MASTER_PLAN §3.C completion criteria) — until then both
coexist (strangler fig).

### Backend — new service tree (`backend/services/svc-dashboard/`)

| File | Tag | Description | Owning specialist |
|---|---|---|---|
| `app/main.py` | NEW | Standalone FastAPI app; mounts the 1 dashboard route; registers the 6-mw chain (plan_guard + audit present-but-inert per §0.7) + `core/errors` handlers; `/health` + `/metrics`. **NO Celery app** (§0.3). | services-builder |
| `app/router.py` | NEW (from `modules/dashboard/router.py`) | 1 public route (`GET /api/v1/products` 200) verbatim; preserve `@rate_limit(scope="dashboard_list", limit=600, window=3600)` + the `FEATURE_TRACKING_DASHBOARD_ENABLED` 404 guard; NO `/internal/*` (no inbound callers, §0.6). | api-routes-builder |
| `app/service.py` | NEW (from `modules/dashboard/service.py`) | `list_products_for_dashboard` + the pure `_compose_response`; cross-module imports rewired to `extracted_clients` shims (§16.G). The 2 call sites (`:78`/`:84`) stay BYTE-FOR-BYTE identical — only the imported symbols change. | services-builder |
| `app/schemas.py` | NEW (from `modules/dashboard/schemas.py`) | `DashboardQuery`, `ProductListItem`, `ProfileCompletenessSummary`, `DashboardResponse` (PRIVATE wire-shape). | api-routes-builder |
| `app/domain.py` | NEW (from `modules/dashboard/domain.py`) | Empty-but-legal (`__all__ = []`) — kept for §3.C subtree completeness. The 3 vendored callee dataclasses live in the shim modules, not here. | services-builder |
| `app/exceptions.py` | NEW (from `modules/dashboard/exceptions.py`) | `DashboardError` + `InvalidPaginationError` hierarchy. | services-builder |
| `app/core/extracted_clients/catalog_client.py` | NEW | HTTP shim: `list_products(user_id, pagination, db)` → `GET catalog-svc/internal/products` (paginated). Re-exports under the SAME symbol the call site used (`catalog_service`). During MS-2 the callee is STILL IN-PROCESS (monolith), so the shim base URL points at the **monolith ClusterIP** (`monolith-svc:8001`), NOT a not-yet-existent catalog-svc (catalog extracts LAST at MS-5; R4 / §3.A hybrid posture). Vendors the `PaginatedProductsInternal` + `Pagination` dataclasses (§0.5). | services-builder |
| `app/core/extracted_clients/customer_client.py` | NEW | HTTP shim: `get_onboarding_completeness(user_id, db)` → `GET customer-svc/internal/seller-profile/{user_id}/onboarding-completeness`. Same monolith-ClusterIP target during MS-2 (customer extracts at MS-3). Vendors the `ProfileCompleteness` dataclass (§0.5). **NOTE method name = `get_onboarding_completeness`, NOT `get_profile_completeness` (§0.5 correction).** | services-builder |
| `app/shared/{database,config,valkey}.py` | NEW (vendored) | TRIMMED Settings: `DATABASE_URL` (no owned schema — middleware/`get_db` wiring only, §0.8), `VALKEY_URL` (rate_limit DB 0 + the inert audit path), `JWT_SECRET`, `FEATURE_TRACKING_DASHBOARD_ENABLED`, `APP_ENV` ONLY. **NO GEMINI/LANGFUSE/MSG91/RAZORPAY/GCS** (dashboard has no AI/SMS/payment/storage). Very small pool (2–3 conns — §0.8). | services-builder |
| `app/core/middleware/*` | NEW (vendored) | 6-mw chain (plan_guard + audit inert). | services-builder |
| `app/i18n/messages_en.py` | NEW (vendored subset) | ONLY dashboard's `validation_message_id` strings (`validation.dashboard.invalid_pagination` + `server.internal_error`). | services-builder |
| `requirements.txt` | NEW | fastapi, sqlalchemy, asyncpg, httpx, redis. **NO celery, NO openpyxl, NO gemini/langfuse** (dashboard has no Celery/XLSX/AI). | services-builder |
| `Dockerfile` | NEW (placeholder) | FROM python:3.12-slim; infra lead authors the real one on the infra branch. | infra-builder |
| `tests/test_dashboard_extraction.py` | NEW | Hybrid-mode integration test (in-process + HTTP-shim). | backend-coordinator |

### Backend — monolith-side changes (during strangler window)

| File | Tag | Description | Owning specialist |
|---|---|---|---|
| `backend/app/modules/dashboard/` (6 files) | KEEP-then-DELETE | Stay live until hybrid-mode CI green ≥7 days, then deleted. | backend-coordinator |
| `backend/app/main.py` | MODIFY (additive, at cutover) | When traffic cuts over, the in-process `dashboard_router` mount (main.py:141) is removed (Traefik routes `GET /api/v1/products` to svc-dashboard). Until cutover, it stays mounted (both modes run). DISJOINT from MS-C's image mount removal — keep-both on merge. | backend-coordinator |

> **NO `celery_app.py` change** — dashboard registers no Celery task, so the
> monolith's `workers/celery_app.py` `include=[...]` is UNTOUCHED by this
> extraction (contrast svc-export, which removed `app.modules.export.tasks`).

### Infra (placeholders only — owned by infra lead, land on infra branch)

| File | Tag | Description | Owning specialist |
|---|---|---|---|
| `k8s/svc-dashboard/deployment.yaml` | NEW (placeholder) | **api 1 replica ONLY** (NO worker — dashboard has no Celery); req 50m/128Mi, lim 200m/256Mi (smaller mem than svc-export — no XLSX build). | infra-builder |
| `k8s/svc-dashboard/service.yaml` | NEW (placeholder) | ClusterIP `svc-dashboard:8001`. | infra-builder |
| Traefik IngressRoute | NEW (placeholder) | `GET /api/v1/products` → svc-dashboard:8001 (METHOD-or-prefix-aware per §0.4 path-key collision with catalog `POST /api/v1/products`). `/internal/*` NOT exposed. | infra-builder |
| `FEATURE_TRACKING_DASHBOARD_ENABLED` ConfigMap | EXISTING (re-point) | Already injected for the monolith (flag-parity sweep); svc-dashboard's ConfigMap carries the same flag (dev=true / staging=false). | infra-builder |
| Postgres role (audit grant) | NEW (placeholder) | `GRANT INSERT ON public.audit_events TO dashboard_user` — for the inert audit_mw path (audit_mw writes NOTHING on GET, but the grant keeps the vendored middleware import-safe). NO owned schema (§0.8). | infra-builder |

---

## Documentation deliverables

These must land alongside the merged extraction code (gate conditions in the
Acceptance gate §):

- **svc-dashboard standalone OpenAPI** — 1 endpoint (`GET /api/v1/products`
  200), 4 schemas (`DashboardQuery`, `ProductListItem`,
  `ProfileCompletenessSummary`, `DashboardResponse`).
- **The frozen `/internal/*` shim-contract section** (below — the 2 endpoints
  dashboard's callees catalog + customer must later expose). THIS IS A
  SUB-PLAN-B DELIVERABLE (freezes the interface now; MS-E customer + MS-H
  catalog implement what is frozen here).
- **`BACKEND_ARCHITECTURE.md` §13 amendment** ("Extracted to svc-dashboard
  V1.5" note documenting that the 2 outbound calls are now HTTP shims; §16.G
  call-site contract preserved). **§13 is LOCKED → FOUNDER APPROVAL REQUIRED
  before this amendment lands. Do NOT self-amend a LOCKED section (§7.3).**
- **`MASTER_PLAN.md` §4 row B** annotation flip ("Sub-Plan B authored
  2026-06-12; execution at MS-2") + the §1.C `get_profile_completeness` →
  `get_onboarding_completeness` correction (a doc-cohesion fix — flag to
  founder; §1.C is plan prose, not a LOCKED architecture section).
- **Runbook** — `docs/runbooks/svc-dashboard-rollback.md` (the §3.C rollback
  procedure specialized for dashboard).
- **Hybrid-mode CI config note** — documents which services must be
  docker-composed for dashboard's HTTP-mode CI (answer: NONE of dashboard's
  callees need to be standalone for dashboard's OWN extraction CI; during
  dashboard extraction the callees catalog + customer are still in-process, so
  the shims point at the `monolith-svc` ClusterIP — per §3.A hybrid posture).

---

## FROZEN `/internal/*` shim contracts — Sub-Plan B caller-side freeze

> **FROZEN 2026-06-12.** dashboard is a CALLER of **catalog** (MS-H, extracts
> LAST) and **customer** (MS-E, extracts at MS-3). The exact request/response
> shapes below are file:line-cited from the AS-BUILT callee signatures +
> return types. **The monolith serves these shims until catalog/customer
> extract.** MS-E (customer) and MS-H (catalog) MUST implement what is frozen
> here. **Style REUSED verbatim from MS-A's frozen shim contract**
> (`spec_msA_backend.md §5` + `handoff_msA_infra.md`): path prefix
> `/internal/<resource>/*` (cluster-DNS only, NOT Traefik-exposed); auth =
> forward the user's JWT in `Authorization: Bearer <token>` + `X-Request-ID`;
> error shape = the §4 4-field `MeesellError` envelope; `httpx.AsyncClient`
> with 5s read / 2s connect timeout, 1 retry on 503/504 only (§5.E). If MS-A
> froze a contract style, this COPIES it.

### Shim 1 — catalog (MS-H implements; dashboard freezes it now)

- **Caller site:** `dashboard/service.py:78`
  `await catalog_service.list_products(user_id=user_id, pagination=pagination, db=db)`
- **Callee source signature:** `catalog/service.py:999`
  `list_products(user_id: UUID, pagination: Pagination, db: AsyncSession) -> PaginatedProductsInternal`
- **Internal endpoint (catalog-svc):**
  `GET /internal/products?page={page}&limit={limit}` (the `user_id` is derived
  from the forwarded JWT `sub` claim on the callee side — the same scoping the
  in-process `scope_to_user(user_id)` enforces at `catalog_repo.list_paginated`
  per §10.D; the shim does NOT pass `user_id` in the URL, it forwards the JWT
  and the callee resolves the tenant — mirror MS-A's customer shim auth
  posture).
- **Request:** `page: int (ge=1, default 1)`, `limit: int (ge=1, le=100,
  default 20)` as query params; user JWT in `Authorization`.
- **Response (200) — JSON shape the shim deserializes into the vendored
  `PaginatedProductsInternal` (`catalog/domain.py:170`):**
  ```json
  {
    "items": [
      {
        "id": "<uuid>", "user_id": "<uuid>", "catalog_id": "<uuid>",
        "category_id": "<uuid>", "name": "<str|null>",
        "status": "draft|ready", "fields": {}, "ai_suggestions": {},
        "created_at": "<iso8601>", "updated_at": "<iso8601>",
        "deleted_at": null
      }
    ],
    "total": 0, "page": 1, "limit": 20
  }
  ```
  (The vendored shim dataclass on dashboard's side only READS `id`, `name`,
  `category_id`, `status`, `created_at`, `updated_at` — the fields
  `_compose_response` maps per `service.py:118-128` + `_orm_to_domain`. The
  full `Product` shape is serialized for fidelity; the shim deserializes the
  whole thing into the vendored `Product` dataclass `catalog/domain.py:35`.)
- **Errors:** 401 (invalid/absent JWT), 4-field `MeesellError` envelope on any
  service exception. Empty inventory is `items: [], total: 0` at **200** (NOT
  404 — first-time-seller valid state per router.py:102).

### Shim 2 — customer (MS-E implements; dashboard freezes it now)

- **Caller site:** `dashboard/service.py:84`
  `await customer_service.get_onboarding_completeness(user_id=user_id, db=db)`
- **Callee source signature:** `customer/service.py:682`
  `get_onboarding_completeness(user_id: UUID, db: AsyncSession) -> ProfileCompleteness`
- **Internal endpoint (customer-svc):**
  `GET /internal/seller-profile/{user_id}/onboarding-completeness` (path-param
  `user_id` matches the MS-A customer-shim convention
  `/internal/seller-profile/{user_id}/compliance-block` — REUSED verbatim from
  `spec_msA_backend.md §5`; the JWT is forwarded so the callee re-verifies the
  tenant matches the path `user_id`).
- **Request:** path `user_id: UUID`; user JWT in `Authorization`.
- **Response (200) — JSON shape the shim deserializes into the vendored
  `ProfileCompleteness` (`customer/domain.py:98`):**
  ```json
  {
    "base_complete_count": 0,
    "base_total_count": 10,
    "extension_complete_count": 0,
    "extension_total_count": 0,
    "onboarding_complete": false
  }
  ```
  (`base_total_count` is always 10 per §8.F / `customer/service.py:696`.
  First-time seller with NO profile row returns the all-zero / 10-base shape at
  200 — this branch deliberately does NOT raise per `customer/service.py:691`.)
- **Errors:** 401, 4-field `MeesellError` envelope. NO 404 on missing profile
  (returns the zero-shape at 200 per the source comment).

> **Shim count for svc-dashboard = exactly 2 distinct methods across 2 callees
> = catalog(1) + customer(1).** Zero inbound `/internal/*` (dashboard is a leaf
> consumer, §0.6). Contrast svc-export's 6-method/4-callee outbound surface.
> dashboard is the LIGHTEST shim surface of any extraction.

---

## Memory protocol

**Memories the coding-session leads MUST read at start (Phase 2):**
- `.claude/agent-memory/meesell-backend-coordinator/MEMORY.md` (extraction
  contracts, §16.G call-site rule, the MS-A recipe, dashboard as-built notes)
- `.claude/agent-memory/meesell-backend-coordinator/spec_msA_backend.md` +
  `handoff_msA_infra.md` (the MS-A pattern + shim conventions COPIED here)
- `.claude/agent-memory/meesell-services-builder/MEMORY.md` (dashboard
  service/compose build notes from V1)
- `.claude/agent-memory/meesell-infra-builder/MEMORY.md` (svc sizing,
  Traefik route patterns, the svc-export infra precedent)

**New memos created during this extraction:**
- `.claude/agent-memory/meesell-backend-coordinator/spec_msB_backend.md` (the
  task spec — authored this turn).
- `.claude/agent-memory/meesell-backend-coordinator/handoff_msB_infra.md` (the
  cross-lead memo to infra — authored this turn).
- `.claude/agent-memory/meesell-backend-coordinator/feature_microservices-dashboard.md`
  (Phase 2 close-out — created at execution time).

**Session-close memory entries:** each agent appends a session header,
decisions consumed (B1–B4), files-touched count, blockers carried, next-step
recommendation (= the MS-2 partner MS-C image, then MS-3).

---

## Review + iteration protocol

For each specialist named in the Agent lineup:

**meesell-services-builder — pre-approval checklist (backend lead inspects):**
- §16.G call-site preservation: `git diff` of the extracted `service.py`
  against the monolith shows ONLY the import-line changes (service.py:36-42) —
  ZERO changes to the 2 `await <callee>.<method>(...)` call sites (`:78`,
  `:84`). This is the §16.G absolute contract.
- Both shims forward the user JWT in `Authorization` + `X-Request-ID`;
  timeouts 5s read / 2s connect; 1 retry on 503/504 only (§5.E); base URL =
  monolith ClusterIP during MS-2 (callees still in-process).
- customer shim method is `get_onboarding_completeness`, NOT
  `get_profile_completeness` (§0.5 correction — a re-dispatch trigger if wrong).
- Trimmed `Settings` carries NO gemini/langfuse/msg91/razorpay/GCS vars; DOES
  carry `FEATURE_TRACKING_DASHBOARD_ENABLED`.
- **NO Celery app** introduced (§0.3 — a re-dispatch trigger if one appears).
- `_compose_response` stays a PURE function (no I/O, no await — §13.C).
- **PR-template gate:** `.github/PULL_REQUEST_TEMPLATE/backend.md`, every
  section filled, no `<>` placeholders.
- **Re-dispatch triggers:** call site changed beyond imports → re-dispatch
  quoting §16.G + the 2-line list; shim missing JWT forward → §5.A; wrong
  customer method name → §0.5; Celery app introduced → §0.3 "pure read".

**meesell-api-routes-builder — pre-approval checklist:**
- Exactly 1 route mounted (`GET /api/v1/products`); NO `/internal/*`;
  `@rate_limit(scope="dashboard_list", limit=600, window=3600)` preserved; the
  `FEATURE_TRACKING_DASHBOARD_ENABLED` 404 guard preserved BEFORE the service
  call.
- Handler calls `dashboard_service.list_products_for_dashboard` only — NO
  business logic inlined.
- OpenAPI regenerated; 1 endpoint + 4 schemas present.
- **Re-dispatch trigger:** business logic inlined → §13.B "handlers call
  service methods only"; rate-limit/flag-guard dropped → re-cite router.py
  source.

**meesell-database-builder — pre-approval checklist (VERIFY-ONLY, B4):**
- Attestation: svc-dashboard owns ZERO tables, introduces NO model/migration/
  Alembic chain, DATABASE_URL maps to NO owned schema.
- **Re-dispatch trigger:** a migration/table/model was authored → re-dispatch
  quoting §13.D "owns ZERO tables" + B4.

**Re-dispatch prompt shape:** original prompt + preamble "Previous run failed
on X; fix Y by reading Z (file + §)." **Iteration cap: 3.** The third
re-dispatch on any specialist triggers a founder consult.

---

## Acceptance gate

Sub-Plan B execution (Phase 2, at MS-2) is DONE when:

- [ ] `feature/microservices-dashboard/backend` PR merged to `.../integration` (backend lead gate)
- [ ] `feature/microservices-dashboard/infra` PR merged to `.../integration` (infra lead gate)
- [ ] Hybrid-mode CI green in BOTH modes (in-process monolith + svc-dashboard-as-pod calling in-process callees) per §3.A, for ≥7 days
- [ ] `cd backend && pytest services/svc-dashboard/tests/test_dashboard_extraction.py` green
- [ ] dashboard's own 36 tests green in BOTH the monolith (pre-flip) AND the extracted service (no-tunnel baseline: pure-function/contract subset green, infra-gated skips/errors documented per the auth-otp no-tunnel pattern)
- [ ] P95 for `GET /api/v1/products` stays within the §19 dashboard budget (P95 ≤ 200ms per §1.E — the 2 shim calls replace 2 in-process reads; load-test before cutover; the catalog `list_products` shim is the latency-sensitive one — §6 Risk #1 mitigation applies even though catalog is still in-process here)
- [ ] Documentation deliverables landed (OpenAPI, §13 amendment w/ founder approval, runbook, frozen `/internal/*` shim-contract section, §1.C method-name correction)
- [ ] V1_FEATURE_SPEC §F8 (Tracking Dashboard) acceptance criteria still met against the extracted service; `FEATURE_TRACKING_DASHBOARD_ENABLED` 404 guard still fires
- [ ] CI gates 1 (unit), 2 (smoke), 3 (lint) green; gates 4/5 advisory
- [ ] Full-suite `def test_` count MONOTONIC vs the live baseline at PR time (do NOT hardcode; re-count — §0.9)
- [ ] `ruff` clean on `backend/services/svc-dashboard/`
- [ ] import-linter: svc-dashboard tree introduces NO domain→adapters edge (it has no adapters); no ai_ops edge (Contract 5 — dashboard never consumed ai_ops); dashboard's no-repository §13.D exception still allowlisted
- [ ] NO tautological tests (the pricing lesson): the hybrid-mode integration test asserts REAL behavior (a shim call forwards the JWT + returns the callee's real `PaginatedProductsInternal` / `ProfileCompleteness` shape; the composed `DashboardResponse` maps fields correctly; empty-inventory → 200 not 404), NOT `assert True`-class echoes
- [ ] `feature_board_backend.md` row reflects MERGED (direct status-only commit per F2, since integration-branch review-count=0 per F3 — re-probe protection first)
- [ ] Founder approval on `feature/microservices-dashboard/integration` → `develop` PR
- [ ] **EXECUTION GATE precondition re-verified:** Sub-Plan A's founder gate is merged to develop AND the MS-A recipe exists in the lead's memory (else Phase 2 must not have started)

---

## Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | The catalog `list_products` shim adds latency to the dashboard load, blowing the §1.E P95 ≤ 200ms budget | Medium | Medium | The 2 shims replace 2 in-process reads (~1ms → ~10ms each). During MS-2 the callees are still IN-PROCESS (monolith ClusterIP), so the hop is intra-cluster localhost-ish — minimal added latency. dashboard page-size is bounded (limit ≤ 100). MASTER_PLAN §6 Risk #1 mitigations apply at the eventual catalog extraction (MS-5), not here. Load-test the 2-shim composition before cutover. |
| R2 | The `get_profile_completeness` plan-prose name is taken at face value and a non-existent customer method is shimmed | Medium | Medium | §0.5 corrects the name to `get_onboarding_completeness` (cited `customer/service.py:682`). The services-builder spec + the pre-approval checklist BOTH flag the correct name; a wrong name is a named re-dispatch trigger. The frozen shim contract endpoint is `/internal/seller-profile/{user_id}/onboarding-completeness`. |
| R3 | The §13-DASHBOARD-D2 path-key collision (`GET /api/v1/products` shared with catalog `POST /api/v1/products`) breaks Traefik routing | Low | Medium | §0.4 documents the collision; the infra handoff specifies METHOD-or-prefix-aware routing (`GET /api/v1/products` → svc-dashboard; `POST /api/v1/products` stays on monolith until catalog extracts at MS-5). Both share the monolith during MS-2; only the GET routes to svc-dashboard. Catalog extracts LAST, so the POST never moves during dashboard's window. |
| R4 | The `/internal/*` shim contract (catalog `list_products`, customer `get_onboarding_completeness`) does not yet exist — those callees are still in-process during dashboard extraction | Medium | Low | BY DESIGN per §3.A: during dashboard extraction the callees are monolithic, so the shims point at `monolith-svc` ClusterIP, not at not-yet-extracted per-service ClusterIPs. The `/internal/*` endpoints are added on the CALLEE side in MS-E (customer) + MS-H (catalog). The frozen shim-contract section above freezes the interface now so those later sub-plans implement it. |
| R5 | The inert `audit_mw` cross-schema INSERT grant is missing, causing a vendored-middleware import/startup failure | Low | Low | dashboard's audit posture is NONE (read-only GET, §13.B) — audit_mw writes NOTHING. But the vendored middleware import-chain expects the audit write API to be wired; the infra handoff includes `GRANT INSERT ON public.audit_events TO dashboard_user` so the import is safe even though no row is ever written. |
| R6 | The `FEATURE_TRACKING_DASHBOARD_ENABLED` flag guard is lost in the extraction, accidentally un-gating the dashboard in staging | Low | Medium | §0.4-FLAG flags the guard as LIVE (router.py:118). The api-routes-builder spec + pre-approval checklist require it preserved. The infra handoff re-injects the flag via svc-dashboard's ConfigMap (dev=true / staging=false). |

---

## Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| v1 | 2026-06-12 | mesell-ms-dashboard-session-1 (meesell-backend-coordinator, HYBRID STEP 1) | Initial DRAFT. Sub-Plan B authored per MASTER_PLAN §4 row B + the SUB_PLAN_01 SHAPE TEMPLATE, grounded in the AS-BUILT `backend/app/modules/dashboard/` at worktree `c859955`. Mounted-route inventory (1 route) + 2 cross-module call sites cited file:line from SOURCE. **PLAN-TEXT CORRECTION:** §1.C `get_profile_completeness` → `get_onboarding_completeness` (cited `customer/service.py:682`). Frozen `/internal/*` shim-contract section (2 endpoints: catalog `list_products`, customer `get_onboarding_completeness`) reusing the MS-A shim style verbatim. B1 (ai_ops N/A) + B2 (mw inherited D7) + B3 (order confirmation) + B4 (database-builder VERIFY-ONLY, dashboard owns no schema). EXECUTION GATED — MS-2 (parallel with MS-C image), opens on Sub-Plan A founder-gate merged + MS-A recipe in memory. Execution is PLANNING-ONLY this turn. |

---

**END OF SUB-PLAN B — DRAFT, awaiting founder review.**
