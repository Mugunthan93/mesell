# SUB-PLAN A — `export` Service Extraction

**STATUS: DRAFT — awaiting founder review.** Authored under session
`mesell-microservices-backend-session-1` (2026-06-10). This is the first
extraction sub-plan of the Microservices Migration MASTER_PLAN (LOCKED
2026-06-10, v1.1). It implements MASTER_PLAN §4 row **A** (`export`,
complexity **S**, no upstream service deps).

> **Execution gate — PLANNING ONLY.** Per the MASTER_PLAN's post-V1
> framing, NO extraction code is written by this session. This document is
> the executable specification a future post-V1 coding session will follow.
> Three open decisions (§1 below) require founder ratification before the
> coding session is dispatched; two of them (ai_ops placement, middleware
> placement) are presented here as **analysis + recommendation only — NOT
> locked**. They are Sub-Plan-A-time founder decisions.

> Authoritative inputs read for this sub-plan:
> - `docs/plans/microservices_migration/MASTER_PLAN.md` (LOCKED v1.1 — §2.D, §3.B, §4 row A, §5.A/B/C/D/E/F, §6 risks)
> - `docs/plans/infra/microservices_infra_plan.md` (svc-export sizing §6.3, schema-per-service §3.1, PgBouncer §3.2, VM upgrade §6.1)
> - `docs/plans/repo_management/PILOT_REPORT.md` (F1 integration-branch naming, F2 board MERGED flip, F3 protection standard)
> - `docs/plans/features/_CANONICAL_PATTERN.md` (v2.1 — 11-section shape, adapted for an extraction sub-plan)
> - `docs/BACKEND_ARCHITECTURE.md` §14 (export module contract), §16 (inter-module rules), §16.G (call-site-preservation contract), §21 (extraction roadmap)
> - As-built source: `backend/app/modules/export/` (8 files), `backend/app/workers/celery_app.py`, `backend/app/main.py`

---

## Decisions

This section records the three Sub-Plan-A-time decisions. Decisions **A1–A2**
are **NOT locked** — they are presented as analysis + recommendation for the
founder to ratify when the coding session is dispatched. Decision **A3** is a
confirmation of an already-locked ordering.

> **A1 / A2 NOW LOCKED (founder rulings D6 / D7, 2026-06-10).** The "analysis + recommendation, NOT LOCKED" framing on both A1 and A2 below is SUPERSEDED. The founder ratified both decisions one-by-one on 2026-06-10 (recorded in MASTER_PLAN.md Revision History v1.2): **A1 (D6)** — `ai_ops/` is vendored per AI-consuming service at V1.5, promoted to a dedicated `ai-ops-svc` at V2; budget brake stays shared via Valkey/DB. **A2 (D7)** — the 6-middleware chain is vendored per service with LOCAL JWT verification in every service; gateway-JWT validation is REJECTED. The recommendations below are correct as written — they are now LOCKED, not pending.

### A1 — `ai_ops/` placement (~~analysis + recommendation, NOT LOCKED~~ — **LOCKED 2026-06-10, founder ruling D6**)

**Question (MASTER_PLAN §2.E / S2 open decision #1):** When `export` (and
later category/catalog/image) extracts, where does the shared `ai_ops/`
package live?

**Relevance to THIS sub-plan:** LOW-but-must-record. `export` is a
**deterministic** module — it makes **zero** AI calls. Grep of
`backend/app/modules/export/service.py` + `tasks.py` confirms no
`ai_ops.client` import. So the export extraction itself does NOT force the
ai_ops decision. BUT this sub-plan is the founder-designated place to record
the recommendation because Sub-Plan F (`category`) is the first extraction
that DOES carry ai_ops, and the decision must be locked before Sub-Plan F
authoring (per S2 dispatch "MUST DECIDE BEFORE Sub-Plan F").

| Option | Description | Pros | Cons |
|---|---|---|---|
| **A (recommended for V1.5)** | Vendor `ai_ops/` as a Python package inside each AI-consuming service image (category-svc, catalog-svc, image-svc). | No network hop on the AI hot path (autofill on every product, smart_picker on every suggest). Simpler ops — no 9th pod. The ₹500 daily budget-cap counter ALREADY lives in shared Valkey DB 0 (§6A.F), so cross-service cost coordination is already centralized regardless of code placement. | Three copies of the same Python lib drift if not version-pinned. Per-service AI cost attribution requires the Prometheus `service=` label (already locked §5.F), not a dedicated service boundary. |
| **B (recommended for V2)** | Dedicated `ai-ops-svc` microservice; category/catalog/image call it over HTTP. | Single source of truth for cost tracking + budget cap + guardrail. Per-service cost attribution is structural. | Adds a network hop to every AI call (autofill is on the catalog autosave hot path — Risk #1). Operationally heavier (9th pod, 9th Dockerfile, 9th CI surface). Premature while V1 has only 3 AI workloads. |

**RECOMMENDATION (for founder to ratify at Sub-Plan F dispatch, not now):**
**Option A in V1.5, Option B in V2.** The trigger to flip to B is AI workload
count growing beyond V1's 3 (`smart_picker` / `autofill` / `watermark`) OR a
need for per-service AI cost SLOs. **Export extraction proceeds with NO
ai_ops dependency either way** — this decision does not gate Sub-Plan A
execution.

### A2 — Shared `core/middleware/` placement (~~analysis + recommendation, NOT LOCKED~~ — **LOCKED 2026-06-10, founder ruling D7**)

**Question (MASTER_PLAN §1.D / §5.A):** Each extracted service needs JWT
validation, rate limiting, audit logging, request-id propagation. Are these
copied into each service image, or hoisted to an API Gateway concern?

**Relevance to THIS sub-plan:** DIRECT. export-svc needs `auth_mw`
(`get_current_user` on both endpoints), `rate_limit_mw`
(`@rate_limit(scope="export_initiate", limit=10, window=3600)` on POST),
`tenancy_mw` (`request.state.user_id`), `request_id_mw`, and `audit_mw`
(`export.initiated` post-2xx) — 5 of the 6 locked middlewares. So the export
extraction is the FIRST test of whichever option the founder picks.

| Option | Description | Pros | Cons |
|---|---|---|---|
| **A (recommended) — vendor `core/middleware/` into each service image** | Each service ships its own copy of the 6-middleware chain (CORS → request_id → auth_mw → tenancy_mw → rate_limit_mw → plan_guard_mw → audit_mw), vendored from the V1 monolith. JWT validated locally with the shared `JWT_SECRET` from Secret Manager. | Aligns with MASTER_PLAN §5.A LOCKED policy ("each service validates JWTs locally"). No per-request callback to iam-svc (Risk #2 mitigation). Rate-limit middleware uses shared Valkey DB 0, so cross-service counters stay correct (§5.C). Each service attaches its own `request.state.user` for `scope_to_user` — Traefik cannot do this. | Code duplication across service images; middleware bugfixes must be rolled to N images. Mitigated by vendoring from one source tree + version pin. |
| **B (rejected) — API Gateway (Traefik plugin) does JWT validation** | Traefik validates the JWT once at the edge; services trust a forwarded header. | One validation point. | Traefik CANNOT attach the resolved `User` to the downstream service request state, run `plan_guard`, or `scope_to_user` on the service's own DB. MASTER_PLAN §2.C explicitly REJECTS gateway JWT validation for V1.5. |

**RECOMMENDATION (for founder to ratify, NOT locked here):** **Option A —
vendor `core/middleware/` into each service.** This is already the LOCKED
posture at MASTER_PLAN §5.A/§2.C; this sub-plan surfaces it as an explicit
Sub-Plan-A decision so the founder confirms it against the concrete
export-svc middleware list before the first extraction runs. Traefik does
routing + TLS + path-strip only. **For export-svc specifically:**
`plan_guard_mw` is present in the chain but NO-OP for export (export does not
participate in plan_guard per §14.A) — the middleware runs but matches no
export resource.

### A3 — Extraction order — export first (CONFIRMATION of locked order)

**Question (S2 open decision #3):** Confirm `export` is the first extraction.

**Answer:** CONFIRMED. MASTER_PLAN §3.B locks the order
`export → dashboard → image → pricing → customer → category → iam → catalog`.
`export` is first because:
- **Zero downstream consumers** — grep confirms NOTHING in the codebase
  imports from `app.modules.export.*` (the module's own `__init__.py`
  documents this: "NO other module imports from `app.modules.export.*`").
  Extracting it produces zero ripple in caller code.
- **Owns 1 table** (`exports`) — smallest schema migration.
- **Celery worker is ALREADY a separate process boundary** (§11.L / §14.E) —
  the `export.xlsx` task already runs in the worker pod, so the
  process-split is half-done structurally.
- It exercises the **outbound** HTTP-shim path (export calls 4 callees) WITHOUT
  yet exercising the inbound path (no one calls export), de-risking the
  shim infrastructure before a bidirectional module (image, catalog) extracts.

**Not locked here — already locked at §3.B.** A3 is a confirmation, not a new
ruling.

---

## Agent lineup

| Lead | Specialists dispatched | What each specialist builds |
|---|---|---|
| `meesell-backend-coordinator` (orchestrator) | — | Authors this sub-plan; owns the merge gate for `feature/microservices-export/backend` → `feature/microservices-export/integration`; reviews extracted code against §16.G call-site-preservation contract; updates `feature_board_backend.md`. |
| `meesell-backend-coordinator` → `meesell-services-builder` | `meesell-services-builder` (opus) | Extracts `service.py` + `tasks.py` into the new `backend/services/svc-export/` tree; writes the 4 outbound HTTP-shim clients (`catalog_client`, `category_client`, `customer_client`, `image_client`) under `core/extracted_clients/`; preserves the §16.G call sites byte-for-byte; builds the new service `main.py` + Celery app. |
| `meesell-backend-coordinator` → `meesell-api-routes-builder` | `meesell-api-routes-builder` (sonnet) | Splits `router.py` into the new service's public routes (`POST /api/v1/products/{id}/export-xlsx`, `GET /api/v1/exports/{id}`); confirms no `/internal/*` route is needed (export has no inbound callers); regenerates OpenAPI for the standalone service. |
| `meesell-backend-coordinator` → `meesell-database-builder` | `meesell-database-builder` (sonnet) | Authors the Alembic schema-split migration moving `exports` from `public` to schema `export`; sets `version_table_schema="export"`; writes the integrity pre-scan + downgrade path. |
| `meesell-infra-builder` (standalone, via cross-lead memo) | — | Authors `svc-export` Dockerfile, K8s Deployment + Service + Celery worker manifest, Traefik IngressRoute (`/api/v1/exports/*`, `/api/v1/products/{id}/export-xlsx`), the `export` Postgres schema + role grant, the GCS service-account for export path prefix. **Infra work is OWNED by infra lead** — this sub-plan provides placeholders only; the actual k8s/terraform commits land on `feature/microservices-export/infra` per F1, reviewed by the infra lead. |

### Dispatch order (critical path)

```
PHASE A (parallel — no inter-dependency):
  meesell-database-builder  →  Alembic schema-split migration (exports → schema export)
  meesell-infra-builder     →  Dockerfile + K8s manifest placeholders + Postgres schema/role + GCS SA
                               (on feature/microservices-export/infra, infra-lead-reviewed)

PHASE B (depends on A — the service code targets the new schema + image):
  meesell-services-builder  →  extract service.py + tasks.py + 4 HTTP-shim clients + main.py + celery_app
  meesell-api-routes-builder→  extract router.py into standalone-service routes (parallel w/ services-builder
                               once the service-method signatures are frozen)

PHASE C (depends on B — integration):
  meesell-backend-coordinator → hybrid-mode CI wiring (in-process + HTTP-shim) per §3.A;
                                integration test test_export_extraction.py;
                                merge-gate review; board MERGED flip
```

---

## Code surfaces

File-level inventory of the export extraction. Paths are project-relative.
The `backend/services/svc-export/` tree is the new home; the old
`backend/app/modules/export/` tree is DELETED only after hybrid-mode CI passes
for ≥7 days (per MASTER_PLAN §3.C completion criteria) — until then both
coexist (strangler fig).

### Backend — new service tree (`backend/services/svc-export/`)

| File | Tag | Description | Owning specialist |
|---|---|---|---|
| `backend/services/svc-export/app/main.py` | NEW | Standalone FastAPI app; mounts export router; registers the 5-middleware chain (no plan_guard match) + `core/errors` handlers; `/health` + `/metrics`. | services-builder |
| `backend/services/svc-export/app/router.py` | NEW (from `modules/export/router.py`) | 2 public routes verbatim; no `/internal/*` (no inbound callers). | api-routes-builder |
| `backend/services/svc-export/app/service.py` | NEW (from `modules/export/service.py`) | `initiate_export`, `get_export`, `summary` + private pipeline helpers; cross-module imports rewired to `extracted_clients` shims (§16.G). | services-builder |
| `backend/services/svc-export/app/tasks.py` | NEW (from `modules/export/tasks.py`) | `export_xlsx_task` (`export.xlsx`); own Celery app, own queue `svc-export`. | services-builder |
| `backend/services/svc-export/app/repository.py` | NEW (from `modules/export/repository.py`) | `exports`-table repository; bound to schema `export`. | services-builder |
| `backend/services/svc-export/app/domain.py` | NEW (from `modules/export/domain.py`) | Frozen dataclasses (`XlsxRowSpec`, `ComplianceStrategy`, etc.). | services-builder |
| `backend/services/svc-export/app/schemas.py` | NEW (from `modules/export/schemas.py`) | `ExportRequest`, `ExportInitiatedResponse`, `ExportResponse` (PRIVATE wire-shape). | api-routes-builder |
| `backend/services/svc-export/app/exceptions.py` | NEW (from `modules/export/exceptions.py`) | `ExportError` hierarchy. | services-builder |
| `backend/services/svc-export/app/celery_app.py` | NEW | Single-task Celery app (`include=["app.tasks"]`, queue `svc-export`, broker Valkey DB 1, results DB 2, keys prefixed `svc-export:`). | services-builder |
| `backend/services/svc-export/app/core/extracted_clients/catalog_client.py` | NEW | HTTP shim: `get_product_for_export(product_id, user_id)` → `GET catalog-svc/internal/products/{id}/export-snapshot`. Re-exports under the same symbol the call site used. | services-builder |
| `backend/services/svc-export/app/core/extracted_clients/category_client.py` | NEW | HTTP shim: `fetch_schema` + `get_field_enum` + `fetch_xlsx_aliases` → category-svc `/internal/*`. | services-builder |
| `backend/services/svc-export/app/core/extracted_clients/customer_client.py` | NEW | HTTP shim: `get_compliance_block(user_id)` → customer-svc `/internal/*`. | services-builder |
| `backend/services/svc-export/app/core/extracted_clients/image_client.py` | NEW | HTTP shim: `get_image_bytes(...)` → image-svc `/internal/*`. | services-builder |
| `backend/services/svc-export/app/shared/{database,config,valkey}.py` | NEW (vendored) | Trimmed `Settings` (only export's env vars: `DATABASE_URL` @ schema `export`, `VALKEY_URL`, `JWT_SECRET`, `GCS_*`, `APP_ENV`); per-service pool sizing (small — export is worker-heavy not query-heavy). | services-builder |
| `backend/services/svc-export/app/core/middleware/*` | NEW (vendored) | 5-middleware chain (A2 Option A). | services-builder |
| `backend/services/svc-export/app/i18n/messages_en.py` | NEW (vendored subset) | Only export's `validation_message_id` strings. | services-builder |
| `backend/services/svc-export/requirements.txt` | NEW | Service-specific deps (fastapi, sqlalchemy, asyncpg, celery, openpyxl, httpx, redis). NO gemini/langfuse (export has no AI). | services-builder |
| `backend/services/svc-export/Dockerfile` | NEW (placeholder) | FROM python:3.12-slim; infra lead authors the real one on the infra branch. | infra-builder |
| `backend/services/svc-export/alembic/` | NEW | Own Alembic chain rooted at schema `export`; `version_table_schema="export"`. | database-builder |
| `backend/services/svc-export/tests/test_export_extraction.py` | NEW | Hybrid-mode integration test (in-process + HTTP-shim). | backend-coordinator |

### Backend — monolith-side changes (during strangler window)

| File | Tag | Description | Owning specialist |
|---|---|---|---|
| `backend/app/modules/export/` (8 files) | KEEP-then-DELETE | Stay live until hybrid-mode CI green ≥7 days, then deleted. | backend-coordinator |
| `backend/app/main.py` | MODIFY | When traffic cuts over, the in-process `export_router` mount is removed (Traefik routes export paths to svc-export). Until cutover, it stays mounted (both modes run). | backend-coordinator |
| `backend/app/workers/celery_app.py` | MODIFY | Remove `app.modules.export.tasks` from `include=[...]` at cutover (export worker moves to svc-export's own Celery app). | services-builder |

### Infra (placeholders only — owned by infra lead, land on infra branch)

| File | Tag | Description | Owning specialist |
|---|---|---|---|
| `k8s/svc-export/deployment.yaml` | NEW (placeholder) | api 1 replica + worker 1 replica; requests 50m/128Mi, limits 200m/512Mi (infra plan §6.3). | infra-builder |
| `k8s/svc-export/service.yaml` | NEW (placeholder) | ClusterIP :8001. | infra-builder |
| Traefik IngressRoute | NEW (placeholder) | `/api/v1/exports/*` + `/api/v1/products/{id}/export-xlsx` → svc-export:8001. | infra-builder |
| Postgres schema `export` + role grant | NEW (placeholder) | `CREATE SCHEMA export; GRANT ... TO export_user;` | infra-builder |

---

## Documentation deliverables

These must land alongside the merged extraction code (gate conditions in the
Acceptance gate §):

- **OpenAPI** — svc-export's standalone OpenAPI doc regenerated; the 2 export
  endpoints (`POST /api/v1/products/{id}/export-xlsx` 202, `GET /api/v1/exports/{id}` 200)
  documented with `ExportRequest` / `ExportInitiatedResponse` / `ExportResponse`.
- **`BACKEND_ARCHITECTURE.md` §14 amendment** — append an "Extracted to
  svc-export (V1.5)" note documenting that the 4 outbound calls
  (catalog/category/customer/image) are now HTTP shims; §16.G call-site
  contract preserved. **Founder approval required (§14 is LOCKED).**
- **`MASTER_PLAN.md` §4 row A** — flip the row's status annotation from
  "not yet authored" to "Sub-Plan A authored 2026-06-10; execution post-V1".
- **HTTP-shim contract doc** — the 6 `/internal/*` endpoint contracts that
  export's 4 callees must expose (catalog `get_product_for_export`, category
  `fetch_schema`+`get_field_enum`+`fetch_xlsx_aliases`, customer
  `get_compliance_block`, image `get_image_bytes`). Authored as the shared
  contract that Sub-Plans C/E/F/H will implement on the callee side.
- **Runbook** — `docs/runbooks/svc-export-rollback.md` (the §3.C rollback
  procedure specialized for export).
- **Hybrid-mode CI config note** — documents which services must be
  docker-composed for export's HTTP-mode CI (answer: none of export's
  callees need to be standalone for export's OWN extraction CI, because
  during export extraction the callees are still in-process; the shim points
  at the still-monolithic catalog/category/customer/image on the
  `monolith-svc` ClusterIP — per §3.A hybrid posture).

---

## Branch setup

Per PILOT_REPORT **F1**: the integration branch is
`feature/microservices-export/integration` (NOT a bare
`feature/microservices-export`). Group branches keep the canonical
`feature/{slug}/{group}` form.

| Branch | Cut from | Purpose | Who commits |
|---|---|---|---|
| `feature/microservices-export/integration` | `develop` | Integration branch; only merge commits | backend lead (merge approval) |
| `feature/microservices-export/backend` | `feature/microservices-export/integration` | All backend specialist extraction work | backend specialists |
| `feature/microservices-export/infra` | `feature/microservices-export/integration` | Dockerfile, K8s, Postgres schema/role, Traefik route, GCS SA | meesell-infra-builder |

> NOTE — this S2 planning session creates ONLY
> `feature/microservices-export/backend` (per S2 Step 2) as the home for the
> committed Sub-Plan. The `/integration` and `/infra` branches are created at
> coding-session dispatch time (post-V1), not now.

### Creation commands (run at post-V1 coding-session dispatch)

```bash
git checkout develop && git pull
git checkout -b feature/microservices-export/integration && git push -u origin feature/microservices-export/integration
git checkout -b feature/microservices-export/backend feature/microservices-export/integration && git push -u origin feature/microservices-export/backend
git checkout -b feature/microservices-export/infra feature/microservices-export/integration && git push -u origin feature/microservices-export/infra
```

### PR flow (coding stage)

```
feature/microservices-export/backend ──(backend lead reviews; squash)──┐
                                                                       ├─► feature/microservices-export/integration ──(FOUNDER reviews; merge-commit)──► develop
feature/microservices-export/infra  ──(infra lead reviews; squash)─────┘
```

Reviewer rule per MASTER_PLAN §6 + D1: group → integration is the owning
lead's gate; integration → develop is the founder's gate. The backend lead
does NOT approve the integration → develop PR.

### PR templates

| Group PR | Template |
|---|---|
| `feature/microservices-export/backend` → `.../integration` | `.github/PULL_REQUEST_TEMPLATE/backend.md` |
| `feature/microservices-export/infra` → `.../integration` | `.github/PULL_REQUEST_TEMPLATE/infra.md` |

### Rebase strategy

If the infra group PR lands on `/integration` first, the backend group PR
rebases onto the moved integration tip before the backend lead merges. Per
PILOT_REPORT operational learning #3, NEVER `git add -A` in the symlinked
worktree — scope every stage to the exact `backend/services/svc-export/` path.

---

## Memory protocol

**Memories the coding-session leads MUST read at start:**
- `.claude/agent-memory/meesell-backend-coordinator/MEMORY.md` (extraction
  contracts, §16.G call-site rule, export as-built notes)
- `.claude/agent-memory/meesell-services-builder/MEMORY.md` (export
  service/tasks build notes from V1)
- `.claude/agent-memory/meesell-infra-builder/MEMORY.md` (svc-export sizing,
  Postgres schema-per-service, Traefik route patterns)
- `.claude/agent-memory/meesell-database-builder/MEMORY.md` (current Alembic
  head `f31c75438e61`, schema-move procedure)

**Cross-feature memos consumed by this extraction:**
- export consumes `assert_product_ownership` / `get_product_for_export` from
  catalog — see `.claude/agent-memory/meesell-backend-coordinator/feature_catalog-form.md`
  for the catalog ownership-gate contract that becomes catalog-svc's
  `/internal/products/{id}/export-snapshot`.

**New memos created during this extraction:**
- `.claude/agent-memory/meesell-backend-coordinator/feature_microservices-export.md`
  (one convention — the `feature_{slug}.md` form, matching the existing
  `feature_catalog-form.md`).
- Cross-lead memo to infra:
  `.claude/agent-memory/meesell-backend-coordinator/handoff_svc_export_infra.md`
  (the K8s/Postgres/Traefik placeholders the infra lead must turn real).

**Session-close memory entries:** each agent appends a session header,
decisions ratified (A1/A2 outcome), files-touched count, blockers carried,
next-step recommendation (= Sub-Plan B dashboard).

---

## Dispatch templates

These are the paste-able prompts the post-V1 coding-session founder copies
into sub-sessions. **Not dispatched by this planning session.**

### meesell-services-builder

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell (worktrees under /tmp/mesell-wt/ included). DO NOT read/write outside.
SESSION: mesell-microservices-export-backend-session-{N}

## Mandatory reads (in this order)
- docs/plans/microservices_migration/SUB_PLAN_01_export_extraction.md (THIS plan)
- docs/plans/microservices_migration/MASTER_PLAN.md §2.B/§2.D/§3.A/§3.C/§5
- docs/BACKEND_ARCHITECTURE.md §14 (export contract) + §16.G (call-site preservation)
- backend/app/modules/export/{service,tasks,repository,domain,exceptions}.py (as-built)
- .claude/agent-memory/meesell-services-builder/MEMORY.md

## Your mission
Extract the `export` module from the monolith into backend/services/svc-export/.
Move service.py + tasks.py + repository.py + domain.py + exceptions.py + schemas.py
verbatim, then rewire the 4 cross-module imports (catalog/category/customer/image
.service) to HTTP-shim clients under core/extracted_clients/. The §16.G contract
is ABSOLUTE: every call site (e.g. `await catalog_service.get_product_for_export(...)`)
stays BYTE-FOR-BYTE identical — only the imported symbol changes from the
in-process `service` module to the shim that re-exports the same method name over
httpx. Build the standalone main.py (5-middleware chain, A2 Option A) and a
single-task Celery app (queue `svc-export`, keys prefixed `svc-export:`).

## Acceptance criteria
- [ ] All 4 HTTP-shim clients implemented with httpx.AsyncClient, 5s read / 2s connect timeout, 1 retry on 503/504 (§5.E), X-Request-ID forwarded, user JWT forwarded in Authorization header.
- [ ] Zero call-site diffs in service.py pipeline logic (diff against monolith service.py shows ONLY import-line changes).
- [ ] Trimmed Settings: NO GEMINI/LANGFUSE/MSG91/RAZORPAY env vars (export has no AI/SMS/payment).
- [ ] Celery app uses Valkey DB 1 broker / DB 2 results with `svc-export:` key prefix.
- [ ] export_xlsx_task emits export.completed/export.failed via direct ORM write to public.audit_events (cross-schema INSERT grant, §5.B).

## Hard constraints
- DO NOT modify the monolith's backend/app/modules/export/ during extraction (strangler — both coexist).
- DO NOT touch frontend/, k8s/, infra/terraform/ (infra lead owns the manifests).
- DO NOT introduce an AI dependency — export is deterministic.

## Files you MAY touch
backend/services/svc-export/** ONLY (plus this sub-plan's "Rollback Log" subsection if a rollback fires).

## Files you must NOT touch
backend/app/modules/export/**, backend/app/main.py, k8s/**, frontend/**, infra/**

## Final report format
Files created (count + paths); diff-line-count of service.py pipeline vs monolith (target: import lines only); shim timeout/retry config confirmation; PR-template-ready Test evidence block.
```

### meesell-api-routes-builder

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell. DO NOT read/write outside.
SESSION: mesell-microservices-export-backend-session-{N}

## Mandatory reads (in this order)
- docs/plans/microservices_migration/SUB_PLAN_01_export_extraction.md (THIS plan)
- backend/app/modules/export/router.py + schemas.py (as-built)
- docs/BACKEND_ARCHITECTURE.md §14.B (2 endpoint contracts)

## Your mission
Move the 2 export routes (POST /api/v1/products/{id}/export-xlsx 202; GET
/api/v1/exports/{id} 200) into backend/services/svc-export/app/router.py.
Preserve the rate-limit decorator (@rate_limit scope=export_initiate limit=10
window=3600) on POST and per-IP-only on GET. Confirm NO /internal/* route is
needed (export has zero inbound callers). Regenerate the standalone OpenAPI.

## Acceptance criteria
- [ ] 2 routes mounted; both async; both Depends(get_current_user); both Depends(get_db).
- [ ] No business logic inlined — handlers call export_service methods only.
- [ ] OpenAPI regenerated; 2 endpoints + 3 schemas present.

## Hard constraints / MAY touch / must NOT touch / report
(same boundary + report shape as the services-builder template above, scoped to router.py + schemas.py)
```

### meesell-database-builder

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell. DO NOT read/write outside.
SESSION: mesell-microservices-export-backend-session-{N}

## Mandatory reads (in this order)
- docs/plans/microservices_migration/SUB_PLAN_01_export_extraction.md (THIS plan)
- docs/plans/microservices_migration/MASTER_PLAN.md §2.D (schema-per-service)
- backend/alembic/ (current head f31c75438e61)
- .claude/agent-memory/meesell-database-builder/MEMORY.md

## Your mission
Author the schema-split Alembic migration moving the `exports` table from
`public` to a dedicated `export` schema. Set version_table_schema="export" so
the new svc-export Alembic chain tracks its own alembic_version inside the
export schema. Write an upgrade (ALTER TABLE exports SET SCHEMA export) + a
tested downgrade (SET SCHEMA public). Include the §6 Risk #5 pre-scan: verify
every exports.user_id resolves to a real users row BEFORE any cross-schema FK
is dropped (export drops no FK itself, but the scan is the documented pattern).

## Acceptance criteria
- [ ] upgrade + downgrade both tested locally (round-trip clean).
- [ ] No head divergence between dev and staging (apply dev FIRST per infra ordering rule).
- [ ] version_table_schema="export" set; alembic_version lands in export schema.

## Hard constraints / MAY touch / must NOT touch / report
(same boundary shape; scoped to backend/services/svc-export/alembic/** + a migration file)
```

---

## Review + iteration protocol

For each specialist named in §2:

**meesell-services-builder — pre-approval checklist (backend lead inspects):**
- §16.G call-site preservation: `git diff` of the extracted `service.py`
  pipeline against the monolith shows ONLY import-line changes — ZERO changes
  to `await <callee>.<method>(...)` call sites.
- All 4 shims forward the user JWT in `Authorization` and `X-Request-ID`;
  timeouts 5s read / 2s connect; 1 retry on 503/504 only (§5.E).
- Trimmed `Settings` carries NO gemini/langfuse/msg91/razorpay vars.
- Celery keys carry the `svc-export:` prefix (§2.E Valkey namespacing).
- `export.completed`/`export.failed` direct-ORM-write to `public.audit_events`.
- **PR-template gate:** `.github/PULL_REQUEST_TEMPLATE/backend.md`, every
  section filled, no `<>` placeholders.
- **Re-dispatch triggers:** call site changed beyond imports → re-dispatch
  quoting §16.G; shim missing JWT forward → re-dispatch quoting §5.A internal
  auth; AI dep introduced → re-dispatch quoting §14.A "deterministic".

**meesell-api-routes-builder — pre-approval checklist:**
- 2 routes only; no `/internal/*`; rate-limit decorator preserved on POST.
- Re-dispatch trigger: business logic inlined in a handler → re-dispatch
  quoting §14.B "handlers call service methods only".

**meesell-database-builder — pre-approval checklist:**
- Round-trip upgrade/downgrade green; `version_table_schema="export"` set;
  dev applied before staging.
- Re-dispatch trigger: head divergence dev↔staging → P0, escalate to founder.

**Re-dispatch prompt shape:** original prompt + preamble "Previous run failed
on X; fix Y by reading Z (file + §)."

**Iteration cap: 3.** The third re-dispatch on any specialist triggers a
founder consult.

---

## Acceptance gate

Sub-Plan A execution (post-V1) is DONE when:

- [ ] `feature/microservices-export/backend` PR merged to `.../integration` (backend lead gate)
- [ ] `feature/microservices-export/infra` PR merged to `.../integration` (infra lead gate)
- [ ] Hybrid-mode CI green in BOTH modes (in-process monolith + svc-export-as-pod calling in-process callees) per §3.A, for ≥7 days
- [ ] `cd backend && pytest services/svc-export/tests/test_export_extraction.py` green
- [ ] P95 for `POST export-xlsx` initiate stays within the §19 export budget (≤30s end-to-end build per §5.5.10, unchanged by extraction — the build is the same code)
- [ ] Documentation deliverables landed (OpenAPI, §14 amendment w/ founder approval, runbook, HTTP-shim contract doc)
- [ ] V1_FEATURE_SPEC §F9 (XLSX export) acceptance criteria still met against the extracted service
- [ ] CI gates 1 (unit), 2 (smoke), 3 (lint) green; gates 4/5 advisory
- [ ] `feature_board_backend.md` row reflects MERGED (direct status-only commit per F2, since integration-branch review-count=0 per F3 — re-probe protection first)
- [ ] Founder approval on `feature/microservices-export/integration` → `develop` PR

---

## Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | The 4 outbound HTTP shims (catalog/category/customer/image) add latency to the export build, blowing the ≤30s budget | Medium | Medium | Export is async + worker-bound; the build already does sequential per-row reads. Shim calls replace in-process reads (~1ms → ~10ms each). With ~50 products × 4 callees the added latency is bounded; load-test before cutover. Schema fetch is cached on category-svc (≥99% hit). MASTER_PLAN §6 Risk #1 mitigations apply. |
| R2 | `export.xlsx` Celery task loses its broker/result keyspace when moving from the shared monolith Celery app to svc-export's own app | Low | High | Keys re-prefixed `svc-export:` (§2.E); the one-off Valkey backfill script migrates in-flight task state at cutover. Tasks are row-level idempotent (per celery_app.py docstring) — a re-run is safe. |
| R3 | Cross-schema INSERT to `public.audit_events` fails because export's Postgres role lacks the grant | Low | Medium | Infra lead's role-grant placeholder (`GRANT INSERT ON public.audit_events TO export_user`) is a Phase-A acceptance item; integration test asserts an audit row lands. §5.B locked. |
| R4 | The HTTP-shim contract (`/internal/*` on the 4 callees) does not yet exist — those callees are still in-process during export extraction | Medium | Medium | This is BY DESIGN per §3.A: during export extraction the callees are monolithic, so the shim points at the `monolith-svc` ClusterIP, not at not-yet-extracted per-service ClusterIPs. The `/internal/*` endpoints are added on the CALLEE side in Sub-Plans C/E/F/H. The shim contract doc (Documentation deliverables) freezes the interface now so later sub-plans implement it. |
| R5 | OpenPyXL / XLSX build behaves differently under the trimmed svc-export deps than the monolith | Low | Medium | `requirements.txt` pins the same openpyxl version as the monolith; the golden-roundtrip CI gate (5) re-runs the §14 round-trip validation against the extracted service. |

---

## Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| v1 | 2026-06-10 | mesell-microservices-backend-session-1 | Initial DRAFT. Sub-Plan A authored per MASTER_PLAN §4 row A + canonical pattern v2.1 (adapted for extraction). A1 (ai_ops) + A2 (middleware) presented as analysis+recommendation — NOT locked, founder-ratified at coding dispatch. A3 (export-first) confirmed. Execution is post-V1. |
| v2 | 2026-06-10 | meesell-backend-coordinator (landing founder rulings D3–D7) | **A1 / A2 LOCKED** per founder rulings **D6 / D7** (recorded MASTER_PLAN v1.2). A1 (D6): `ai_ops/` vendored per AI-service at V1.5 → `ai-ops-svc` at V2; budget brake shared via Valkey/DB. A2 (D7): 6-mw chain vendored per service, LOCAL JWT verification in every service, gateway-JWT REJECTED, `iam-svc` owns OTP/login/refresh only. The "recommendation, NOT locked" framing on A1/A2 is superseded; recommendations stand as written, now LOCKED. A3 unchanged (already locked). |

---

**END OF SUB-PLAN A — DRAFT, awaiting founder review.**
