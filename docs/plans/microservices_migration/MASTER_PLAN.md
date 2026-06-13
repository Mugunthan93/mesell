# MeeSell Microservices Migration — MASTER PLAN

STATUS: LOCKED 2026-06-10 — ratified by founder as the migration roadmap (per its own Lock target convention). **START CONDITION RE-KEYED 2026-06-12 (founder ruling "ms go"): execution unblocks at _dev-complete_, NOT post-V1-launch — see §3.A.1 "Execution Start Condition" + Revision History v1.3.**

> Scope: planning-only. Zero code changes. This document is the master roadmap for converting the MeeSell modular monolith into a set of independent FastAPI microservices, one per domain module. It does NOT itself migrate anything; it specifies HOW the migration will be carried out, in what ORDER, with which AGENTS, and against which RISKS.

> Authoritative inputs read for this plan:
> - `docs/BACKEND_ARCHITECTURE.md` (LOCKED — 26 sections, modular monolith contract; §2.D call matrix, §16 inter-module rules, §21 extraction roadmap are load-bearing for this plan)
> - `docs/MVP_ARCHITECTURE.md` (LOCKED 2026-06-10 — cross-cutting system map)
> - `docs/status/STATUS_BACKEND.md` (current backend state — V1 GO declared 2026-06-09)
> - `.claude/agent-memory/meesell-backend-coordinator/MEMORY.md` (Session 3 turn history through §22 acceptance audit attempt #3)

---

## 1. Current State Assessment

### 1.A What we have today (V1 — modular monolith)

V1 is a **single FastAPI process** containing **8 domain modules** that ALREADY follow the extraction-ready file layout locked at BACKEND_ARCHITECTURE §3.B / §3.C. The backend is V1-GO as of 2026-06-09 (`§22 Acceptance Audit Attempt #3 — 9/9 PASS`). Two replicas of the FastAPI pod + two replicas of the Celery worker pod run in the `dev` namespace on a single GCP VM K3s node.

**The 8 domain modules** (each at `backend/app/modules/<module>/`):

| Module | Owns tables | Endpoints | AI seam | Celery? | Cross-module callers |
|--------|-------------|-----------|---------|---------|----------------------|
| `iam` | `users` | 6 (4 auth + /me + razorpay webhook) | no | no | (via `core/auth.py` middleware — not a service call) |
| `customer` | `seller_profile` | 5 | no | no | catalog, dashboard, export |
| `category` | (reads `categories`, `templates`, `field_enum_values`, `field_aliases` — all GLOBAL) | 5 | yes (Smart Picker) | no | catalog, pricing, export |
| `catalog` | `catalogs`, `products`, `product_drafts` | 6 | yes (Auto-fill) | no (sync V1) | image, pricing, dashboard, export |
| `image` | `product_images` | 2 (upload 202 + poll) | yes (watermark) | yes (`image.precheck`) | catalog (ownership), export |
| `pricing` | `pricing_calcs` | 1 | no | no | (dashboard OPTIONAL summary) |
| `dashboard` | (none — pure composition) | 1 (`GET /api/v1/products`) | no | no | (no outbound — leaf consumer) |
| `export` | `exports` | 2 (initiate + poll) | no (deterministic) | yes (`export.xlsx`) | (no outbound — leaf consumer) |

**Endpoint inventory (locked at §17, audited at §22):** 28 routes wired in production (iam 6 / customer 5 / category 5 / catalog 6 / image 2 / pricing 1 / dashboard 1 / export 2). Auth posture: 23 JWT / 2 cookie / 2 public / 1 HMAC.

### 1.B Shared files that cross every module today

These are the cohesion points that make the V1 monolith one process. Each is a "shared file" in the sense that lifting any module out into its own process requires deciding what happens to its dependency on these:

- **`shared/database.py`** — single `create_async_engine` for PostgreSQL 16, single `AsyncSessionLocal`, single `Base` class, single `get_db` FastAPI dependency. Pool sized at 2 replicas × (10+5) = 30 conns < Postgres 100 budget. The `make_worker_session` `NullPool` helper for Celery lives here too.
- **`shared/valkey.py`** — 4 factory functions per Valkey DB: `get_valkey_otp` (DB 0), `get_valkey_broker` (DB 1), `get_valkey_results` (DB 2), `get_valkey_cache` (DB 3). All modules use these.
- **`shared/config.py`** — single `Settings` Pydantic class loading from `.env` (dev) / GCP Secret Manager (staging/prod). 11 env-var groups. Every module imports from this.
- **`shared/models/`** — 13 SQLAlchemy ORM model files (one per table) in a single Python package. The `Base.metadata` is the single source of truth for Alembic.
- **`core/auth.py`** — `get_current_user` FastAPI dependency. Every authenticated route depends on this. JWT claims `{sub, exp, plan}` per HS256.
- **`core/tenancy.py`** — `assert_owned` + `scope_to_user(user_id)` helpers, imported by every repository on owned tables. CI linter enforces this.
- **`core/cache.py`** — Valkey DB 3 read-through helper `get_or_set` with single-flight protection per §6.8. Heaviest user is `category` (5 cacheable endpoints, full-tree pre-warm).
- **`core/plan_guard.py`** — `enforce_plan_limit` for 4 V1 resources (`product_count=100`, `ai_autofill=50/h`, `smart_picker=100/h`, `create_product=20/h`).
- **`core/errors.py`** — `MeesellError` base + 4-field envelope `{detail, code, validation_message_id, request_id}`. Every module's exceptions are subclasses caught here.
- **`core/middleware/`** — 6 middlewares in locked order: `CORS → request_id → auth_mw → tenancy_mw → rate_limit_mw → plan_guard_mw → (route) → audit_mw`.
- **`ai_ops/client.py`** — sole import surface for AI calls. `call_gemini(ctx, workload, ...)` orchestrates cost tracking + 3-layer guardrail + ₹500 daily cap + LangFuse trace. Consumed by category (Smart Picker), catalog (Auto-fill), image (Watermark).
- **`adapters/`** — 5 vendor clients (gemini, msg91, gcs, razorpay, langfuse). Today every module that talks to a vendor imports the relevant adapter directly (with §3.G boundary: gemini ONLY via ai_ops/client.py).
- **`i18n/messages_en.py`** — locale-aware message registry. Every module's `validation_message_id` resolves here. Roughly 50 IDs populated as of V1.
- **`workers/celery_app.py`** — single Celery app instance with broker DB 1, results DB 2. Currently registers 2 task modules (`image.tasks`, `export.tasks`).

### 1.C Cross-module calls today (the §2.D call matrix)

The locked rule is **service-layer only**: a module's `service.py` is its PUBLIC interface; `repository.py` is PRIVATE. Cross-module reads NEVER go through repositories or direct SQL. The 8 ✓ cells in the matrix:

| Caller → Callee | Method on callee.service | Purpose |
|-----------------|--------------------------|---------|
| catalog → customer | `assert_eligible_for_super_id(user_id, super_id)` | 422 gate before product create |
| catalog → category | `assert_category_exists(category_id)` | 404 gate; also `fetch_schema` for autofill enum resolver |
| image → catalog | `assert_product_ownership(product_id, user_id)` | Cross-tenant leak prevention (philosophy M6) |
| pricing → category | `get_commission(category_id)` | P&L commission lookup |
| pricing → catalog | `assert_product_ownership(product_id, user_id)` | Same M6 seam |
| dashboard → customer | `get_profile_completeness(user_id)` | Status badge composition |
| dashboard → catalog | `list_products(user_id, Pagination)` | The listing itself |
| export → customer, category, catalog, image | `get_compliance_block`, `fetch_schema` + `get_field_enum` + `fetch_xlsx_aliases`, `get_product_for_export`, `get_image_bytes` | 9-step Export Adapter |

All other cells are `✗`. **`iam` is all-`✗`** by design: its contract to other modules is the `get_current_user` middleware, NOT a service call.

### 1.D What would break if modules were separated today

**Imports.** Every authenticated route depends on `from app.core.auth import get_current_user`. Splitting `iam` out without replacing this import with an HTTP call would break every other module's startup.

**Single AsyncSession.** Every service method receives an `AsyncSession` from `Depends(get_db)`. That session is bound to the single FastAPI process. The moment two services are in two processes, you can no longer pass the same session between them; you either (a) replicate the DB connection in both services, or (b) replace the call with HTTP and let each service own its own DB connection.

**Cross-module service calls (the 8 ✓ cells).** `catalog → customer.service.assert_eligible_for_super_id` is currently `await self.customer_service.assert_eligible_for_super_id(...)`. After extraction, this must become `await self.customer_client.assert_eligible_for_super_id(...)` where the client is an HTTP shim at `core/extracted_clients/customer_client.py`. The §16.G locked contract is that the call site stays byte-for-byte identical — only the imported symbol changes from `customer.service` to `customer_client` (re-exported from `customer.service`).

**Shared `ai_ops/`.** Three modules (category, catalog, image) call `ai_ops.client.call_gemini`. If they extract independently, each carries its own copy of `ai_ops/`, OR `ai_ops/` becomes a 4th "infrastructure" service. Decision deferred to Sub-Plan A (see §4).

**Shared `core/middleware/`.** Every service needs JWT validation, rate limiting, audit logging, request-id propagation. Either each extracted service ships its own copy of `core/middleware/`, OR these become an API Gateway concern. Decision deferred to §5.A.

**Single Celery app.** `image.tasks` (precheck pipeline) and `export.tasks` (XLSX build) share `celery_app.py` and Valkey DBs 1/2. If image and export extract to separate pods, each needs its own Celery app + worker, with its own queue, possibly its own Valkey instance.

**Cross-module exceptions caught centrally.** Today `core/errors.py` catches `MeesellError` and dispatches by subclass. If `iam.exceptions.OtpInvalidError` lives in a separate service, catalog's process can't catch it directly — the HTTP shim translates HTTP 401 from iam-service into an exception or response model on the catalog side.

**Shared Alembic head.** All 13 tables have a single Alembic head (`f31c75438e61`). The moment two services own different tables in different databases, each service has its own Alembic chain. Migrations stop being globally orderable.

**Shared i18n registry.** `i18n/messages_en.py` carries every module's validation strings. Splitting means each service ships its own messages file, OR i18n becomes a separate service (overkill for V1.5).

---

## 2. Target Architecture

### 2.A Vision — 8 services + 1 gateway + 1 shared infrastructure plane

After full migration (V2 end-state):

```
                    ┌─────────────────────────┐
                    │   Traefik Gateway       │
                    │   (cert-manager LE)     │
                    │   /api/v1/auth/*    →   iam
                    │   /api/v1/seller-*  →   customer
                    │   /api/v1/categories/*  →   category
                    │   /api/v1/products/*    →   catalog (+ image/pricing/export sub-routes)
                    │   /api/v1/exports/*     →   export
                    └─────────────────────────┘
                                │
              ┌─────────────────┴────────────────────────────────────┐
              │                                                      │
        ┌─────▼───────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─▼────────┐
        │ iam-svc     │  │customer- │  │category- │  │ catalog- │  │ image-svc│
        │ (FastAPI)   │  │  svc     │  │  svc     │  │   svc    │  │(FastAPI  │
        │             │  │          │  │          │  │          │  │+ Celery) │
        └─────┬───────┘  └─────┬────┘  └─────┬────┘  └─────┬────┘  └────┬─────┘
              │                │             │             │            │
        ┌─────▼────────────────▼─────────────▼─────────────▼────────────▼─────┐
        │     Shared infrastructure plane                                     │
        │     - PostgreSQL 16 (single instance, per-service SCHEMA isolation) │
        │     - Valkey 8 (DBs 0/1/2/3 + per-service prefixes)                 │
        │     - GCS bucket (meesell-images, meesell-exports — single bucket,  │
        │       per-tenant + per-service path prefixes)                       │
        │     - ai_ops shared lib (Python package OR ai-ops-svc — Sub-Plan A) │
        │     - i18n shared lib (vendored into each service image)            │
        └────────────────────────────────────────────────────────────────────┘
                                │                              │
                       ┌────────▼─────────┐          ┌────────▼─────────┐
                       │ pricing-svc      │          │ dashboard-svc    │
                       │ (FastAPI)        │          │ (FastAPI BFF)    │
                       └──────────────────┘          └──────────────────┘
                                │
                       ┌────────▼─────────┐
                       │ export-svc       │
                       │ (FastAPI+Celery) │
                       └──────────────────┘
```

Each of the 8 services is its own:
- K3s Deployment (own pod template, own replicas count, own resources)
- FastAPI application with its own `main.py`
- Service-specific `requirements.txt`
- Service-specific Dockerfile (FROM the same Python 3.12 base)
- Service-specific Alembic chain for its owned tables

### 2.B Service-to-service communication pattern

**Sync HTTP with internal JWT propagation (locked posture for V1.5).** Every cross-service call uses `httpx.AsyncClient` to the callee's K3s ClusterIP service (e.g. `http://customer-svc:8001/internal/seller-profile/{user_id}/eligibility/{super_id}`). The user's JWT is forwarded via `Authorization: Bearer <token>` header so the callee can re-validate ownership. **No async event bus in V1.5** — the audit_events table already absorbs cross-service event capture inline. Async events deferred to V2.

**Internal endpoints vs public endpoints.** Each service exposes:
- **Public endpoints** at `/api/v1/<resource>/*` reachable through Traefik (e.g. `POST /api/v1/products` on catalog-svc)
- **Internal endpoints** at `/internal/<resource>/*` reachable only through the K3s cluster network (e.g. `GET /internal/products/{id}/ownership-check` on catalog-svc, called by image-svc).

The internal endpoints are exactly the 6 distinct cross-module service methods that power the 8 ✓ cells in the §2.D matrix. Each becomes a thin HTTP route on the callee service. The §16.G locked contract guarantees the Python call site stays unchanged in the caller's code — the magic is in the `core/extracted_clients/<callee>_client.py` shim that translates the call into HTTP.

### 2.C API Gateway / routing layer

**Traefik IngressRoute (already in place).** Today Traefik routes `studio.mesell.xyz/*` to a single FastAPI ClusterIP service. After migration, Traefik routes to per-service ClusterIPs based on path prefix:

| Path prefix | Target ClusterIP |
|-------------|------------------|
| `/api/v1/auth/*` | iam-svc:8001 |
| `/api/v1/seller-profile/*` | customer-svc:8001 |
| `/api/v1/categories/*` | category-svc:8001 |
| `/api/v1/products/*` (except images, price-calc, exports) | catalog-svc:8001 |
| `/api/v1/products/{id}/images*` | image-svc:8001 |
| `/api/v1/products/{id}/price-calc` | pricing-svc:8001 |
| `/api/v1/exports/*` | export-svc:8001 |
| `/api/v1/products` (the dashboard listing) | dashboard-svc:8001 |
| `/metrics`, `/health` | local per-service |

**JWT validation at the gateway is REJECTED for V1.5.** Rationale: Traefik plugins exist for JWT validation but each service needs to re-attach the user object to its request state, look up plan claims, run plan_guard, scope_to_user on its own DB — none of which Traefik can do. JWT validation stays inside each service (via the shared `core/auth.py` lib vendored into each service image). Traefik does routing + TLS + path stripping only. See §5.A for full rationale.

**`/internal/*` is NOT exposed by Traefik.** The internal endpoints are reachable only via K3s cluster DNS (e.g. `http://customer-svc.dev.svc.cluster.local:8001`). NetworkPolicy enforces this in V2; for V1.5 the absence of a Traefik IngressRoute for `/internal/*` is sufficient.

### 2.D Database strategy — shared DB with schema isolation (V1.5), separate DBs (V2)

**V1.5 — shared PostgreSQL instance, per-service Postgres SCHEMA.**

Today all 13 tables sit in the `public` schema. The V1.5 extraction maps each module's owned tables to a dedicated Postgres schema:

| Service | Postgres schema | Tables |
|---------|-----------------|--------|
| iam-svc | `iam` | `users` |
| customer-svc | `customer` | `seller_profile` |
| category-svc | `category` | `categories`, `templates`, `field_enum_values`, `field_aliases` (GLOBAL — read-only after seed) |
| catalog-svc | `catalog` | `catalogs`, `products`, `product_drafts` |
| image-svc | `image` | `product_images` |
| pricing-svc | `pricing` | `pricing_calcs` |
| export-svc | `export` | `exports` |
| (shared) | `public` | `audit_events` (every service writes here via shared lib) |
| dashboard-svc | (none) | (composes via HTTP) |

Each service connects with a Postgres role scoped to its own schema (`GRANT USAGE ON SCHEMA iam TO iam_user; GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA iam TO iam_user;`). No cross-schema reads — a service that needs another service's data goes through HTTP, never SQL.

Each service has its own Alembic chain, rooted at the schema it owns. Alembic `version_table_schema` is set to the service's schema so the `alembic_version` row lives next to the tables it tracks.

**`audit_events` exception.** The audit table is shared because every service writes to it (audit_mw + 4 documented direct-write exceptions per §15.C). The shared library `core/audit.py` provides the write API. The table lives in `public`. Cross-schema writes need a separate Postgres role granted to all services. Trade-off: a centralized audit log keeps the operational story simple in V1.5; in V2 each service owns its own audit_events partition.

**Foreign keys across schemas — locked policy.** Today `products.user_id REFERENCES users(id)` etc. are real foreign keys. After schema isolation, `catalog.products.user_id REFERENCES iam.users(id)` still works in PostgreSQL but **we drop these cross-schema FKs** as part of the iam extraction. Rationale: cross-schema FKs are a hidden coupling that breaks when iam moves to a separate database in V2. We rely on application-layer enforcement (`assert_owned` + the existing `scope_to_user` predicates).

**V2 — separate PostgreSQL instances per service.** When traffic/team scale demands it, each service gets its own Postgres instance. The shared-schema model is a stepping stone, not the end state. The §16.G locked contract means call sites don't change; only `shared/config.py` per-service env vars change.

### 2.E Shared infrastructure — how each service accesses it

**PostgreSQL.** Each service ships `shared/database.py` (vendored from the V1 monolith) with its own `DATABASE_URL` pointing to its own schema. Pool sized per-service based on its traffic (catalog gets the largest pool, dashboard the smallest).

**Valkey.** All 4 DBs continue to be shared. Each service uses the same `shared/valkey.py` factories. **Key namespacing changes** — every key gains a `{service_name}:` prefix to prevent collisions (e.g. `category:smart_picker:{hash}` instead of `smart_picker:{hash}`). Existing keys at extraction time are migrated by a one-off backfill script.

**GCS.** Single bucket (`meesell-images`, `meesell-exports`) with path prefixes already enforcing tenancy (`{user_id}/{product_id}/{idx}.jpg`). Each service that touches GCS (image-svc, export-svc) gets its own GCP Service Account with `storage.objectAdmin` on its path prefix. No bucket split in V1.5.

**Gemini, MSG91, Razorpay, LangFuse.** Same API keys today. Each service that uses these (iam: msg91+razorpay, category/catalog/image: gemini+langfuse via ai_ops) gets the relevant key injected via Secret Manager. No vendor changes.

**`ai_ops/` placement — Sub-Plan A decision.** Two options:
- **Option A — Python package vendored into each AI-consuming service.** category-svc, catalog-svc, image-svc each ship a copy of `ai_ops/` in their image. Cost tracking, budget cap, guardrail run in-process. Simpler operationally; risk is budget-cap state desync across services (the ₹500 daily cap is a global counter — must remain in shared Valkey DB 0 to coordinate).
- **Option B — Dedicated `ai-ops-svc` microservice.** Single source of truth for cost tracking + budget cap. Every AI call from any service becomes an HTTP call to `ai-ops-svc` which then makes the upstream Gemini call. Operationally heavier; eliminates desync risk.

**Recommendation: Option A for V1.5, Option B for V2.** The budget-cap counter already lives in Valkey DB 0 (per §6A.F), so the cross-service state is already shared. Each service consumes the same Python lib. Move to a dedicated ai-ops-svc only when AI workload count grows beyond V1's 3 (smart_picker / autofill / watermark).

> **RESOLVED 2026-06-10 (founder ruling D6 / A1 — see Revision History v1.2).** No longer a deferred recommendation: **`ai_ops/` is a vendored Python-package copy per AI-consuming service (category/catalog/image) at V1.5; promoted to a dedicated `ai-ops-svc` at V2.** The ₹500 daily budget brake stays SHARED via Valkey DB 0 / the audit-DB counter across services regardless of code placement. Sub-Plan A's A1 (analysis+recommendation framing) is superseded by this LOCK.

---

## 3. Migration Strategy

### 3.A Approach — Strangler Fig (gradual)

**Rejected: Big Bang.** Cutting over all 8 services at once risks all 8 failing at once. The V1 monolith ships V1 in production with V1-GO at attempt #3; ripping it out wholesale forfeits that proven baseline. Big Bang also forces every cross-track stakeholder (FE, DATA, INFRA, AI) to coordinate a single cutover — risk that any one track slips blocks all 7 others.

**Chosen: Strangler Fig (gradual extraction, one module at a time).** The locked §16.G contract — call sites stay byte-for-byte identical across in-process vs HTTP modes — makes Strangler Fig safe to run module-by-module. While module N extracts, modules 1..N-1 are already extracted, module N+1..8 are still in-process. The hybrid posture is the defining characteristic of the V1.5 → V2 transition (per §21.F).

**Hybrid-mode CI gate.** During each module's extraction window, CI runs the full test suite TWICE:
1. **In-process mode** — the V1 monolith with all modules in one process (legacy mode, kept until last module extracts).
2. **HTTP shim mode** — the modules extracted so far are docker-compose'd as separate services; the module under extraction is tested in both shapes.

Both must pass before the extraction is declared complete. Locked at §21.F.4 / §16.G.4.

### 3.A.1 Execution Start Condition — RE-KEYED 2026-06-12 (founder ruling "ms go")

**Prior condition (v1.0–v1.2): execution begins _post-V1-launch_.** This is now SUPERSEDED.

**New condition (v1.3): execution unblocks at _dev-complete_.** The migration may begin extracting the moment the V1 feature build is dev-complete — it no longer waits for the V1 production launch.

> **Founder ruling — verbatim (2026-06-12, "ms go"):**
> "**The microservices migration's start condition is RE-KEYED from 'post-V1 launch' to 'dev-complete.'**"

**Rationale (recorded by the master session at ruling time):**
1. **All V1 feature lanes are finished** — Wave 6 (frontend API wiring), the AI lane, and the dual-pepper rotation are complete. The V1 dev build is at (or imminently at) dev-complete.
2. **Launch is deferred** — the production move is parked; there are no users yet.
3. **Extracting in dev with zero traffic is the lowest-risk window** — a Strangler-Fig extraction (§3.A) run against a no-traffic dev cluster carries none of the latency/rollback exposure that the same extraction would carry against live production traffic. Risk #1 (catalog autosave P95) and Risk #2 (iam blast radius) are de-fanged when there is no production load to blow a budget or page.
4. **By production time the MS architecture will be long-proven in dev** — extracting now means the 8-service hybrid posture has months of in-dev soak before it ever fronts a real user. Production cutover inherits a battle-tested topology rather than a fresh one.

**What this does NOT change:**
- The **A–H extraction order** (§3.B), the **per-module rollback contract** (§3.C), the **hybrid-mode CI gate** (§3.A), and **every locked decision** (D3–D7 / A1–A2) are untouched. Only the _gate that opens execution_ moved earlier.
- The **dev-complete declaration itself** is the trigger. Until the master session formally declares dev-complete, the lane stays READY-TO-EXECUTE (pending that declaration), not IN EXECUTION.

**EXPLICIT FRESH FOUNDER ASK on the VM spend trigger (standing rule).** Decision **D3** (VM upgrade to `e2-standard-4`, ~₹2,600/mo — pre-approved at the *plan* level) gets an **explicit fresh founder ask at the moment services outgrow the current node**, NOT at the moment execution begins. The pre-approval is for the plan; the spend-trigger is re-asked. Early extractions (Sub-Plan A `export`, B `dashboard`) fit the current node at their locked K3s sizing (50m CPU requests per pod) — the upgrade is a later-extraction event re-confirmed in real time, per the master-session standing rule. No money is committed by this re-key.

### 3.B Extraction order (locked at §16.H / §21.B)

The order is FIXED — established by founder-locked rulings on §16.H. Easiest first, hardest last:

| Order | Module | Why this position |
|-------|--------|-------------------|
| 1 | **`export`** | No downstream consumers — nothing in the codebase imports from `export.service`. Extracts cleanly with zero ripple. Owns 1 table. Worker pod (Celery) is already a separate process boundary. |
| 2 | **`dashboard`** | Owns ZERO tables (structural exception per §13.D). Pure composition over catalog + customer. Extracts as a thin BFF pod with no data migration. |
| 3 | **`image`** | Worker pod is already a separate process per §11.L. Extracts with its Celery worker. Cross-module call to catalog (ownership gate) becomes the FIRST live HTTP shim — proves the §16.G contract works in practice. |
| 4 | **`pricing`** | Deterministic compute, no AI. Owns 1 table. 2 cross-module HTTP shims (category + catalog) — easy to verify with golden P&L fixtures. |
| 5 | **`customer`** | Tenant-scoped, low call volume. Consumed by catalog + export + dashboard — by this point, all 3 consumers already have HTTP shim infrastructure in place. |
| 6 | **`category`** | Heavy cache consumer (full-tree pre-warm, top-100 schemas pre-warm, single-flight on 291 brand-pattern enums). Extraction must preserve cache contract — Valkey DB 3 mounts on the extracted pod with same pre-warm pattern. |
| 7 | **`iam`** | Consumed by EVERY authenticated route via `core/auth_mw`. Extraction last because every other service must have its `get_current_user` shim ready BEFORE iam goes out. The shim contract — a service validates the JWT using the public-key/secret it already has (no callback to iam-svc per token) — is what enables this ordering. |
| 8 | **`catalog`** | The spine — every other module is already calling catalog via HTTP shim by the time catalog extracts. Migration risk is concentrated here; 4 downstream consumers means 4 networking surfaces flip simultaneously. Per `§10.K`. |

**Why catalog is LAST.** Catalog has the most cross-module callers (image, pricing, dashboard, export — 4 services depending on catalog). Each of those 4 must already be running in HTTP-shim mode against an in-process catalog before catalog itself extracts. Schema fetch is the hot path (every PATCH on a product reads the schema); in-process is ~1ms, network is ~10ms. Catalog also runs the per-product PATCH at autosave frequency (every ~5s during typing); the network latency hit compounds. We extract catalog last so the operational pain lands once, after the team has 7 prior extractions of pattern-experience.

**Why iam is SECOND-TO-LAST.** Every authenticated route needs `get_current_user`. If iam extracts early, every still-in-process module has to make an HTTP call to iam-svc on every request — destroys latency for the still-monolithic part. By extracting iam late, we minimize the window during which the monolith does cross-service auth calls. The HS256 JWT secret can be vendored into each service via Secret Manager, eliminating the need for a per-request callback to iam — iam-svc owns OTP/login/refresh, but JWT VALIDATION runs locally in every service.

### 3.C Rollback plan per extraction

**Per-module rollback contract.** When extraction of module N fails (test regression > 10%, P95 latency budget blown, or contract drift detected), rollback procedure:

1. **Stop traffic** — Traefik IngressRoute for module N's paths is updated to point back at the monolith ClusterIP (was: `module-N-svc:8001`, now: `monolith-svc:8001`).
2. **Restore call sites** — `core/extracted_clients/<module_N>_client.py` re-exports the in-process `service.py` instead of the HTTP shim. The §16.G call-site contract guarantees this is a 1-line change (or one git-revert) — no caller code changes.
3. **Roll back database** — module N's schema goes back to `public`. If new migrations landed during extraction (rare — extractions don't typically add tables), they are reversed via `alembic downgrade -1` per migration.
4. **Tear down service pod** — `kubectl delete deployment module-N-svc`. Pod and ClusterIP deleted.
5. **Re-run hybrid-mode CI** in pure in-process mode to confirm green. Document root cause in the extraction sub-plan's "Rollback Log".

**Rollback IS allowed at any point before module N is declared complete.** A successful extraction is declared complete only when (a) hybrid-mode CI passes for ≥7 days, (b) P95 latency for the extracted module stays within its locked budget, (c) zero rollback-triggering audits land in `STATUS_BACKEND.md`. Until then, rollback is one Traefik update + one git revert away.

**Catastrophic rollback (post-completion).** If a module already declared complete must be reverted (rare), the rollback procedure includes a data migration step — the schema's data is copied back into `public.<table>` and the cross-schema FKs are restored. This step is documented per-extraction in Sub-Plan A through H.

---

## 4. Sub-Plans List

Each sub-plan is one module extraction (one file in `docs/plans/microservices_migration/`). The master plan lists them in order; sub-plan CONTENT is authored in separate files later (this master is ONE file per the constraint).

| # | Sub-plan filename | Module | Complexity | Blocking dependencies | Responsible agent | Estimated effort |
|---|-------------------|--------|------------|------------------------|-------------------|------------------|
| A | `SUB_PLAN_01_export_extraction.md` | `export` | **S** | None — first extraction | meesell-backend-coordinator (orchestrator) + meesell-services-builder (extracts service.py + tasks.py) + meesell-infra-builder (K3s manifest) | 3-5 days · **IN EXECUTION 2026-06-12** |
| B | `SUB_PLAN_02_dashboard_extraction.md` | `dashboard` | **S** | A complete (export-svc HTTP-callable for the optional dashboard-OPTIONAL summary surface) | meesell-services-builder + meesell-api-routes-builder + meesell-infra-builder | 2-3 days (smallest — owns no tables) |
| C | `SUB_PLAN_03_image_extraction.md` | `image` | **M** | A, B complete; catalog-svc HTTP-shim contract for `assert_product_ownership` proven against monolith | meesell-services-builder + meesell-api-routes-builder + meesell-image-precheck-builder (verifies Celery worker still operates) + meesell-infra-builder | 5-7 days (Celery worker extraction, GCS path adjustments, watermark via ai_ops) |
| D | `SUB_PLAN_04_pricing_extraction.md` | `pricing` | **S** | A, B, C complete; HTTP shims for category + catalog proven | meesell-services-builder + meesell-api-routes-builder + meesell-infra-builder | 3-4 days |
| E | `SUB_PLAN_05_customer_extraction.md` | `customer` | **M** | A, B, C, D complete; HTTP shims for customer's consumers (catalog, export, dashboard) ready | meesell-services-builder + meesell-api-routes-builder + meesell-database-builder (seller_profile schema migration) + meesell-infra-builder | 5-7 days |
| F | `SUB_PLAN_06_category_extraction.md` | `category` | **L** | A, B, C, D, E complete; cache contract preserved on extracted pod | meesell-services-builder + meesell-api-routes-builder + meesell-category-picker-builder (verifies Smart Picker ranking pipeline) + meesell-database-builder (4 global tables schema move) + meesell-infra-builder + Valkey DB 3 contract review | 7-10 days (heaviest cache layer, 4 global tables, single-flight on 291 brand-pattern enums) |
| G | `SUB_PLAN_07_iam_extraction.md` | `iam` | **L** | A, B, C, D, E, F complete; every other service has local JWT validation via vendored `core/auth.py`; refresh-token allowlist Valkey contract preserved | meesell-auth-builder + meesell-api-routes-builder + meesell-services-builder (MSG91/razorpay adapters) + meesell-database-builder (users schema migration) + meesell-infra-builder | 7-10 days (critical-path module, every other service depends on JWT validation working) |
| H | `SUB_PLAN_08_catalog_extraction.md` | `catalog` | **XL** | A-G complete; 4 downstream callers (image, pricing, dashboard, export) all running in HTTP-shim mode against monolithic catalog | meesell-services-builder + meesell-api-routes-builder + meesell-database-builder (3 tables schema migration: catalogs/products/product_drafts) + meesell-infra-builder + cross-coordinator review (FE for response shape, AI for autofill) | 10-15 days (the spine; 6 endpoints, autosave hot path, AI auto-fill seam, cross-module ownership assertion). **Program-completion note: catalog is the last extraction — the program (A–H) is NOT declared complete until the post-extraction repo-management compliance audit at §5.G passes.** |

**Total estimated effort:** 42-61 person-days across the 8 sub-plans. Assumes 1 specialist per dispatch with coordinator review interleaved; parallelization is limited by the strict order dependency.

> **Execution status (2026-06-12) — Sub-Plan A `export` IN EXECUTION.** dev-complete declared; founder "ms go" in force; §3.A.1 start condition satisfied. Phases A (Alembic schema-split, `e7a3c1f9b42d`), B (services + routes extraction, 4 HTTP shims), and C (lead integration: hybrid-mode test, frozen shim contract, CI note, rollback runbook) are built on `feature/microservices-export/backend`; infra lane on `feature/microservices-export/infra`. Group PRs → `feature/microservices-export/integration` are the backend-lead/infra-lead gates; integration → develop is the FOUNDER gate. The frozen `/internal/*` shim contract for the 6 callee endpoints (consumed by Sub-Plans C/E/F/H) lives in `SHIM_CONTRACT_export_callees.md`. **Pending founder approval:** the `BACKEND_ARCHITECTURE.md §14` amendment ("Extracted to svc-export V1.5" note) — §14 is LOCKED, so the amendment is NOT self-applied; it is carried to the founder-gate PR notes per §7.3.

**Sub-plan content scope (deferred — NOT in this master plan).** Each sub-plan file will contain:
- Pre-extraction snapshot (current state of the module — file inventory, table list, call sites)
- Target service definition (FastAPI app skeleton, Dockerfile, K3s manifest, env-var changes)
- Migration steps (in order — code moves, schema moves, K3s deploy, traffic cutover)
- Hybrid-mode CI configuration for the extraction window
- Per-extraction acceptance criteria (P95 budget, contract tests, rollback triggers)
- Per-extraction rollback procedure (detailed, not the generic §3.C version)
- Hand-off notes to coordinators of adjacent tracks
- Risk register specific to this module (a subset of §6 below filtered to this extraction)

---

## 5. Cross-Cutting Concerns

### 5.A Authentication — JWT validation in each service (NOT centralized at gateway)

**Locked policy: each service validates JWTs locally using a vendored `core/auth.py`.**

> **RESOLVED 2026-06-10 (founder ruling D7 / A2 — see Revision History v1.2).** Confirmed against the concrete export-svc middleware list: **the 6-middleware chain (CORS → request_id → auth_mw → tenancy_mw → rate_limit_mw → plan_guard_mw → audit_mw) is VENDORED per service, and JWT VERIFICATION runs LOCALLY in every service.** `iam-svc` owns OTP/login/refresh ONLY — it is NOT consulted per-request for token validation. **Gateway-JWT validation is REJECTED** (Traefik cannot attach the resolved `User`, run plan_guard, or scope_to_user). Sub-Plan A's A2 (analysis+recommendation framing) is superseded by this LOCK.

Rationale:
- Traefik plugins for JWT validation exist but cannot attach the resolved user to the downstream service's request state, run `plan_guard`, or scope DB queries to the tenant. Each service still needs the `User` object on `request.state.user`.
- Per-request callbacks to iam-svc for JWT validation would 2× the request count to iam-svc and add ~10ms latency to every authenticated request.
- HS256 with a shared symmetric secret is the simplest model. The secret lives in Secret Manager and is injected into each service's env at pod start. iam-svc OWNS the secret rotation; other services discover the new secret via Kubernetes secret reload (V1.5 — restart pod) or hot-reload from Secret Manager (V2).
- The §15.H locked FE-D5 ratification (in-memory access JWT + HttpOnly refresh cookie) does not change. The refresh cookie hits ONLY iam-svc (`Path=/api/v1/auth/`). Other services see the access JWT in the `Authorization` header.

**Internal-endpoint authentication.** When catalog-svc calls customer-svc's `/internal/seller-profile/{user_id}/eligibility/{super_id}` endpoint, the caller forwards the user's JWT. The callee validates it the same way it validates a public-endpoint JWT. There is NO separate service-to-service auth token in V1.5. In V2, mTLS via Istio/Linkerd may be introduced; V1.5 relies on K3s NetworkPolicy to block internal-endpoint access from outside the cluster.

### 5.B Audit logging — each service writes to a shared `audit_events` table (V1.5), per-service partitions (V2)

**Locked policy: shared `audit_events` table in `public` schema, all services GRANT INSERT on it.**

Rationale:
- The §11.4 locked autosave coalescing rule (`audit_mw` post-2xx with 5-min coalescing) cannot work if every service writes to its own audit log — the coalescing window crosses module boundaries (e.g. catalog autosave coalesce within one user). Centralized table preserves this.
- Operational story: a single `audit_events` table is one place to query for forensics, V1 acceptance auditing, and Prometheus metric extraction. Splitting it across 8 schemas multiplies operational complexity for no V1.5 benefit.
- Cross-schema write is supported by PostgreSQL — each service's Postgres role is granted `INSERT ON public.audit_events`. No FK from audit_events to other tables (already locked — `actor_user_id` is a raw UUID, not an FK).

**V2 plan: per-service audit_events partition.** When V2 introduces per-service Postgres instances, each service writes to its own partition (e.g. `catalog.audit_events`); a downstream ETL aggregates to a warehouse for forensics.

### 5.C Rate limiting — per-service (V1.5), with shared Valkey DB 0 for cross-service keys

**Locked policy: each service runs its own rate-limit middleware using the SHARED Valkey DB 0.**

Rationale:
- The §10.7 locked sliding-window rate limit is keyed per `(scope, key)` where `key` is `user_id` (or `phone` for OTP, or `IP` for fallback). The Valkey key space (`ratelimit:{scope}:{key}:{window}`) is already global — when the same user hits 3 different services in 1 hour, the cumulative count is correct as long as all services use the same Valkey DB 0.
- Each service ships `core/middleware/rate_limit_mw.py` (vendored from V1 monolith). Each service registers its own `@rate_limit(scope, limit, key)` decorators on its own routes.
- The 4-resource plan_guard (`product_count`, `ai_autofill`, `smart_picker`, `create_product`) is enforced WHERE THE RESOURCE LIVES:
  - `product_count` (cumulative cap) — enforced at catalog-svc (it owns the products count)
  - `ai_autofill_hourly` — enforced at catalog-svc (it invokes autofill)
  - `smart_picker_hourly` — enforced at category-svc (it invokes smart picker)
  - `create_product_hourly` — enforced at catalog-svc

No service-to-service callback needed for plan_guard — each resource's owner enforces its own cap with a Valkey counter.

### 5.D Config / secrets — each service has its own env vars

**Locked policy: each service has its own `shared/config.py` with its own `Settings` class containing ONLY the env vars it needs.**

Rationale:
- The V1 monolith's `Settings` carries env vars for every concern (Gemini, MSG91, GCS, Razorpay, LangFuse, Postgres, Valkey, JWT, etc.). After extraction, customer-svc doesn't need `GEMINI_API_KEY`; pricing-svc doesn't need `MSG91_AUTH_KEY`. Each service ships a trimmed Settings.
- GCP Secret Manager mounts only the secrets each pod needs. The §22 acceptance audit attempt #3 confirmed 3 GCP secrets are populated (`refresh-token-pepper`, `razorpay-webhook-secret`, `langfuse-secret-key`); these go to iam-svc only (`refresh-token-pepper`, `razorpay-webhook-secret`) and to the AI-consuming services (`langfuse-secret-key`).
- **Shared base env vars** (`DATABASE_URL` with per-service schema, `VALKEY_URL`, `JWT_SECRET`, `APP_ENV`) are common across all services.

**One env per service per environment.** `iam-svc` in `dev` namespace has its own ConfigMap + Secret. Same for `staging` and `prod`. The §15.B locked decision (RLS deferred to V1.5) does not affect this — each service's Postgres role is scoped to its schema with or without RLS.

### 5.E Inter-service communication — HTTP via `httpx.AsyncClient`, no service mesh in V1.5

**Locked policy: `httpx.AsyncClient` with connection pooling and retries per service.**

- Each service ships `core/extracted_clients/<callee>_client.py` shims as it goes online. The shim is a thin wrapper around `httpx.AsyncClient`.
- Connection pool size per shim: 50 (matching V1 monolith's Postgres pool sizing scale).
- Retry policy: 1 retry on 503/504 with 100ms backoff; no retry on 4xx. The retried request carries the same `X-Request-ID` header for trace correlation.
- Timeouts: 5s read timeout, 2s connect timeout. Catalog's `assert_product_ownership` shim has a tighter 500ms timeout because it's on the autosave hot path.
- **No service mesh** (Istio, Linkerd) in V1.5 — adds operational complexity that doesn't pay off until V2's mTLS requirement. K3s NetworkPolicy is sufficient for internal-endpoint isolation.

### 5.F Observability — Prometheus + LangFuse per service, shared scrape config

**Locked policy: each service mounts `/metrics`; Prometheus scrapes all 8.**

- Each service ships `core/metrics.py` with the same 7 singletons locked at §15.J (`HTTP_REQUEST_DURATION`, `HTTP_REQUESTS_TOTAL`, `AI_OPS_COST_INR`, `AI_OPS_BUDGET_ALARM`, `I18N_MISSING_KEY`, `CELERY_QUEUE_DEPTH`, `AUTH_TOKEN_REFRESH_FAILED`). Per-service label `service="<name>"` distinguishes them in queries.
- Prometheus ServiceMonitor (or scrape_config) updated to list all 8 ClusterIPs.
- LangFuse traces continue to flow from `ai_ops/client.py` in each AI-consuming service (category, catalog, image) with `service` tag — same dashboard, per-service breakdown.

### 5.G Program-completion gate — post-extraction repo-management compliance audit

**Post-extraction repo-management compliance audit (founder-mandated 2026-06-10).** Before the extraction program (A–H) is declared complete: (a) re-verify the Model C convention against the 8-service topology where a backend 'feature' = a service — branch model, PR templates, boards, merge gates, session naming; (b) verify hybrid-mode CI behaved as specified across extractions; (c) audit agent obedience during migration (worktrees, allowlists, boards, iteration caps, rollback contract adherence); (d) report to founder; (e) amend repo_management/MASTER_PLAN.md if drifted. Owner: meesell-backend-coordinator with master-session review.

---

## 6. Risk Register

Top 5 risks of this migration. Each carries an explicit mitigation per the §22A risk register convention.

### Risk #1 — **Catalog extraction breaks the autosave hot path (P95 budget blown)**

**Likelihood: HIGH.** **Impact: HIGH.**

The catalog PATCH endpoint runs on every keystroke during product wizard typing (~5s coalescing window). In-process call latency for the schema fetch and ownership-check seams is ~1ms each. After extraction, schema fetch becomes a network call to category-svc (~10ms incl. cache hit). The P95 budget for autosave is tight — locked at §15.E.

**Mitigation:**
- Catalog extracted LAST per §3.B. By the time catalog moves, all 7 other modules are extracted, and the team has ~50 days of HTTP-shim experience tuning timeouts, pool sizes, and retry budgets.
- Schema fetch is heavily cached on category-svc (full-tree pre-warm + top-100 schemas pre-warm per §6.7). Cache hit ratio should be ≥99% for established sellers.
- Ownership-check on catalog can be served by a thin in-memory cache on the caller's side (catalog's `assert_product_ownership` cache TTL 60s — a seller's products don't change ownership within that window).
- Pre-extraction load test: simulate the V1.5 autosave path with 10× current traffic against a dockerized catalog-svc + category-svc. If P95 exceeds budget by >20%, halt extraction.

### Risk #2 — **iam extraction breaks every authenticated route across all services**

**Likelihood: MEDIUM.** **Impact: CATASTROPHIC.**

iam-svc owns OTP/login/refresh. If JWT validation in other services depends on iam-svc being up (e.g. each service calls iam to validate every token), iam downtime takes down the entire platform.

**Mitigation:**
- Locked policy: JWT validation is LOCAL to each service via vendored `core/auth.py` + the shared `JWT_SECRET` from Secret Manager. Other services NEVER call iam-svc to validate a token. iam-svc downtime affects only login/refresh/logout — existing valid tokens continue to work for the access TTL (15 min) until refresh attempt.
- Pre-extraction: every other service is already in production with the local-validation path enabled. We verify zero callbacks to iam during the 7 prior extractions before extracting iam itself.
- iam runs at 2 replicas minimum (matching V1 monolith). HPA configured for 4-replica burst on OTP-send traffic spikes.
- Refresh-token allowlist Valkey DB 0 contract is preserved verbatim — same Lua EVAL rotation script, same HMAC-pepper keyspace. The Valkey instance is SHARED across services; iam-svc failing doesn't lose the allowlist state.

### Risk #3 — **Hybrid-mode CI cost explosion + flakiness**

**Likelihood: HIGH.** **Impact: MEDIUM.**

Each extraction window runs CI in BOTH modes (in-process + HTTP). The HTTP mode requires docker-compose'ing already-extracted services. By the time module 6 (category) extracts, CI is running 6 separate FastAPI services + Postgres + Valkey + (still-monolithic catalog + iam). Test execution time grows; flaky network tests proliferate; cost rises.

**Mitigation:**
- Each sub-plan documents which services need to be running for that extraction's HTTP-mode CI. Only the modules with cross-module call ✓ cells against the under-extraction module need to be docker-composed.
- HTTP-mode CI runs on a separate CI pipeline (parallel to in-process). Failures in HTTP-mode CI within the first 3 days of an extraction window do NOT block merges — they are tracked for mitigation but the in-process tests are still authoritative. After day 3, HTTP-mode CI is the gating signal.
- Retries on flake-prone HTTP calls (1 retry, 100ms backoff per §5.E). If a test fails 3 times in a row, escalate to root-cause investigation rather than retry-up.
- CI cost is monitored; if hybrid-mode CI exceeds 2× the V1 baseline, parallelization is reduced (run service-pair tests sequentially rather than the full graph).

### Risk #4 — **Shared `audit_events` table contention under cross-service load**

**Likelihood: MEDIUM.** **Impact: MEDIUM.**

All 8 services write to one Postgres table. The §11.4 coalescing rule reduces volume 30× but the table is still a single write hotspot. Catalog autosave volume × 8 services × cross-service propagation could create write-amplification.

**Mitigation:**
- Locked: `audit_events` is append-only with no FKs and no triggers — INSERT is the cheapest operation Postgres offers.
- The V1.5 milestone 7 (per §21.D) moves audit_mw to enqueue a Celery task instead of synchronous write — this milestone is brought FORWARD during the customer-svc or category-svc extraction window if write contention is observed.
- Partitioning audit_events by month is a V2 plan; if write contention surfaces in V1.5, partitioning is pulled forward as a mitigation step (per-month partition reduces hot-block contention).
- Connection-pool tuning per service: audit_events writes go through a separate small connection pool (5 conns) per service so they don't starve user-facing query connections.

### Risk #5 — **Cross-schema FK removal causes silent data integrity loss**

**Likelihood: LOW.** **Impact: HIGH.**

Today `products.user_id REFERENCES users(id)` enforces that every product has a real user. After iam extraction, this FK is dropped. A bug in catalog-svc could insert a product with a non-existent `user_id`; nothing in the database catches it.

**Mitigation:**
- Locked: `assert_owned` + `scope_to_user` at the application layer is the defense (§4.C). Every repository on owned tables uses `scope_to_user(user_id)` predicates — CI linter `check_scope_to_user.py` (Contract 8 of the 10 LOCKED) enforces this.
- Pre-extraction migration: a one-off integrity scan runs before the FK is dropped, verifying every existing row's `user_id` resolves to a real user. Scan output goes into the sub-plan's migration log.
- Post-extraction: a weekly forensic job re-runs the integrity check across all owned tables. Any orphan row triggers a P1 page.
- A new lint contract (Contract 11 — proposed for V1.5) verifies that every cross-module call site forwards the user's JWT, so the callee can re-verify ownership at the HTTP boundary.

---

## Document Header Metadata

| Field | Value |
|-------|-------|
| Document type | Master migration plan |
| Status | LOCKED 2026-06-10 |
| Produced by | meesell-backend-coordinator |
| Produced on | 2026-06-10 |
| Lock target | Founder review → STATUS: LOCKED |
| Cross-references | `docs/BACKEND_ARCHITECTURE.md` §2.D / §16 / §21 / §22A; `docs/MVP_ARCHITECTURE.md` (LOCKED 2026-06-10); `docs/status/STATUS_BACKEND.md` |
| Successor documents | `SUB_PLAN_01_export_extraction.md` through `SUB_PLAN_08_catalog_extraction.md` (not yet authored — content per §4 table) |

---

## Revision History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0 | 2026-06-10 | founder + master Director session | Ratified DRAFT → LOCKED as V1.5/V2 roadmap. Execution begins post-V1-launch. A–H order locked per §16.H. ai_ops + middleware decisions stay deferred to Sub-Plan A. Noted: full extraction forces VM upgrade e2-standard-2 → ≥e2-standard-4 (~₹2.5–6k/mo) at execution time. |
| 1.1 | 2026-06-10 | founder + master Director session | Embedded founder-mandated post-extraction repo-management compliance audit into program completion criteria. |
| 1.2 | 2026-06-10 | founder (rulings) + meesell-backend-coordinator (landing) | **D6 / A1 LOCKED** — `ai_ops/` vendored per AI-service at V1.5 → dedicated `ai-ops-svc` at V2; ₹500 budget brake stays shared via Valkey/DB. §2.E deferral marked RESOLVED. **D7 / A2 LOCKED** — 6-middleware chain vendored per service; JWT verification LOCAL in every service; `iam-svc` owns OTP/login/refresh only; gateway-JWT REJECTED. §5.A confirmed against export-svc middleware list and marked RESOLVED. (Companion infra rulings D3/D4/D5 landed in `docs/plans/infra/microservices_infra_plan.md` v1.1, now APPROVED.) |
| 1.3 | 2026-06-12 | founder (ruling "ms go") + meesell-backend-coordinator (landing) | **START CONDITION RE-KEYED — post-V1-launch → dev-complete.** Verbatim ruling + 4-point rationale + scope landed at new §3.A.1 "Execution Start Condition"; header STATUS line amended. All V1 feature lanes finished (Wave 6, AI, dual-pepper); launch deferred (no users); extracting in dev at zero traffic is the lowest-risk window; MS architecture will be long-proven in dev by production time. **No locked decision changed** — only the execution gate moved earlier. **D3 VM-spend trigger (~₹2,600/mo e2-standard-4) gets an EXPLICIT FRESH founder ask at the moment services outgrow the current node** — the pre-approval is plan-level only; the spend-trigger is re-asked (master-session standing rule). Early extractions (A `export`, B `dashboard`) fit the current node (50m sizing). |

---

**END OF MASTER PLAN — LOCKED 2026-06-10**
