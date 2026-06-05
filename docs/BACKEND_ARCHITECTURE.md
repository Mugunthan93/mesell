# MeeSell — Backend Architecture (Construction Contract)

**Status:** SKELETON — section content authored per-section by founder review
**Date:** 2026-06-05
**Drives:** the 4 backend specialists (`meesell-database-builder`, `meesell-api-routes-builder`, `meesell-services-builder`, `meesell-auth-builder`)
**Supersedes:** any prior implicit layout of `backend/app/` from session-0 and session-1 drafts

> This document is the **construction contract** for the four MeeSell backend specialists. It defines a **Modular Monolith with extraction-ready boundaries** — one FastAPI process organized into eight self-contained domain modules plus adapters, core, and shared layers. Each section below will be authored in a separate founder-reviewed turn; specialists may NOT begin code on a section until that section is marked `STATUS: LOCKED`. This document peers with `docs/MVP_ARCHITECTURE.md` (which is the DATA track's source of truth) and extends it for backend construction without contradicting it.

---

## Table of Contents

0. [Architectural Premises](#section-0--architectural-premises)
1. [System Topology](#section-1--system-topology)
2. [Module Catalog](#section-2--module-catalog)
3. [File Structure](#section-3--file-structure)
4. [`core/` — Cross-Cutting Foundation](#section-4--core--cross-cutting-foundation)
5. [`shared/` — Foundation Layer](#section-5--shared--foundation-layer)
5A. [Presentation Layer Contract + i18n](#section-5a--presentation-layer-contract--i18n)
6. [`adapters/` — Third-Party Vendor Clients](#section-6--adapters--third-party-vendor-clients)
6A. [AI Operations Layer](#section-6a--ai-operations-layer)
7. [Module: `iam`](#section-7--module-iam)
8. [Module: `customer`](#section-8--module-customer)
9. [Module: `category`](#section-9--module-category)
10. [Module: `catalog`](#section-10--module-catalog)
11. [Module: `image`](#section-11--module-image)
12. [Module: `pricing`](#section-12--module-pricing)
13. [Module: `dashboard`](#section-13--module-dashboard)
14. [Module: `export`](#section-14--module-export)
15. [Cross-Cutting Systems Walkthrough](#section-15--cross-cutting-systems-walkthrough)
16. [Inter-Module Communication Rules](#section-16--inter-module-communication-rules)
17. [Endpoint Inventory](#section-17--endpoint-inventory)
18. [Background Jobs (Celery)](#section-18--background-jobs-celery)
19. [Test Strategy](#section-19--test-strategy)
20. [Deployment Topology (V1)](#section-20--deployment-topology-v1)
21. [Extraction Path (V1.5 / V2)](#section-21--extraction-path-v15--v2)
22. [Acceptance & Sign-Off](#section-22--acceptance--sign-off)
22A. [Risk Register & Mitigations](#section-22a--risk-register--mitigations)

---

## Section 0 — Architectural Premises

STATUS: SKELETON

This section enumerates the locked decisions that justify the rest of the document — Option A (Modular Monolith with extraction-ready boundaries), the authoritative 25-endpoint contract (§3 + §7.7 + §11.6 of MVP_ARCHITECTURE, founder-locked 2026-06-05), the inherited 13-table schema, founder rulings D1-D4 from session 2 close-out, and explicit compliance with the 10 mandates / 8 forbids / 5 structural patterns from `docs/CORE_PHILOSOPHY.md`. It is the "why this layout, why these boundaries" preamble that every later section depends on.

---

## Section 1 — System Topology

STATUS: SKELETON

This section describes the runtime topology of the V1 backend: one FastAPI pod (2 replicas) fronting Postgres 16, Valkey 8 (DBs 0/1/2), Celery workers (2 replicas), GCS, and Gemini 2.5 Flash. An ASCII diagram lives here showing request flow, queue flow, and external-vendor egress. This is the "what's running, what talks to what" map that the deployment topology section (§20) later concretizes into K3s manifests.

---

## Section 2 — Module Catalog

STATUS: SKELETON

This section enumerates the eight domain modules (`iam`, `customer`, `category`, `catalog`, `image`, `pricing`, `dashboard`, `export`) plus the three non-domain layers (`adapters/`, `core/`, `shared/`). Each module gets a two-line responsibility summary and a one-line "NOT responsible for" disclaimer so cross-module ownership is unambiguous. This is the table of contents specialists consult before dispatch to know who owns what.

---

## Section 3 — File Structure

STATUS: SKELETON

This section presents the canonical `backend/app/` tree showing `modules/`, `adapters/`, `core/`, `shared/`, `workers/`, and root files (`main.py`, `config.py`). Each module subtree follows the same internal layout (routes, schemas, service, repository, domain types, tests) so specialists can pattern-match across modules. This is the directory contract — specialists may not invent new top-level folders or restructure module internals without amending this section.

---

## Section 4 — `core/` — Cross-Cutting Foundation

STATUS: SKELETON

This section specifies the cross-cutting layer that every domain module depends on: `get_current_user` auth dependency, tenancy enforcement (app-level `user_id` scoping for V1, RLS deferred to V1.5), rate-limit middleware, audit middleware, cache helper, plan guard, structured error handlers, and the canonical middleware registration order. This is the shared toolkit each module imports rather than re-implements, ensuring philosophy mandates (M6, M7, F3) and security invariants apply uniformly. JWT claims shape is locked at `{sub, exp, plan}` per MVP_ARCHITECTURE §11.7, and the canonical middleware ordering places audit AFTER successful write so events log only on commit per §11.8.

---

## Section 5 — `shared/` — Foundation Layer

STATUS: SKELETON

This section specifies the foundation layer below `core/`: SQLAlchemy 2.0 async engine + session factory, Valkey async client, the 13 ORM models registry and their access pattern (one module's service NEVER reaches into another module's tables directly), and configuration loading via Pydantic Settings. This is the infrastructure-glue layer — stateless, no business logic, used identically by every module. The 13-table access pattern is locked module-by-module in §16; migration ordering is NOT duplicated here — the 10-step Alembic sequence in MVP_ARCHITECTURE §2.6 remains the single authoritative DDL source, and this section cites it rather than redefining it.

---

## Section 5A — Presentation Layer Contract + i18n

STATUS: SKELETON

This section locks the exact JSONB shape the backend READS at PATCH validation time and WRITES during template seed — the `templates.schema_jsonb.fields[]` structure carrying `name`, `canonical_name`, `marker`, `data_type`, `primitive`, `is_advanced`, `help_text`, `enum_resolver`, and the rest of the per-field metadata defined in MVP_ARCHITECTURE §5.6.1. It also locks the locale-aware Pydantic error message contract — every validator emits a `validation_message_id` (per §5.6.7) which the error handler resolves against the versioned `app/i18n/` package that `meesell-services-builder` began. This is the single backend-side source of truth for the `schema_jsonb` contract: the `category`, `catalog`, and `export` modules all read from this contract, none redefine it.

---

## Section 6 — `adapters/` — Third-Party Vendor Clients

STATUS: SKELETON

This section specifies the outbound adapter layer that isolates third-party vendor concerns from domain modules (philosophy M10, F8): `gemini`, `msg91`, `razorpay`, and `gcs`. Each adapter sub-section will define its interface contract, retry policy, cost-tracking hook, and failure-mode fallback. Domain modules call adapters through these interfaces only — vendor SDK quirks never leak into business logic. The `gcs` sub-adapter locks the bucket layout at `gs://meesell-images/{user_id}/{product_id}/{image_idx}.jpg` with signed URLs scoped per image and TTL 1 h per MVP_ARCHITECTURE §10.8 — the same layout is mirrored in §11 because the `image` module is the primary writer.

---

## Section 6A — AI Operations Layer

STATUS: SKELETON

This section specifies the platform layer that sits ABOVE the `gemini` adapter and OWNS the cross-call concerns that no single workload should re-implement: per-call cost tracking (tokens × ₹/1K persisted per request), the 3-layer hallucination guardrail (prompt-level constraint + parser-level enum rejection + Export Adapter re-validation per MVP_ARCHITECTURE §5.4 + §9.7), the daily ₹500 budget cap with 80% alarm and 100% hard-stop with graceful fallback, per-seller per-hour rate limits coordinated with the cross-cutting RL middleware, LangFuse tracing on every call, the prompt registry + versioning + A/B routing surface from §5.4, and the 3 golden eval sets (Smart Picker, Auto-fill, Watermark). It is NOT embedded in the `gemini` adapter because cost/eval/guardrail concerns span every AI workload and must outlive any single call site.

---

## Section 7 — Module: `iam`

STATUS: SKELETON

This section specifies the Identity & Access Management module: OTP send/verify flow (Feature 1), JWT issuance and verification, DPDP consent capture, and the `get_current_user` dependency that `core/` re-exports. It owns the `users` table exclusively. This is the unblocker module — every other module's authenticated endpoints depend on `iam.get_current_user`, so it is the first specialist dispatch target.

---

## Section 8 — Module: `customer`

STATUS: SKELETON

This section specifies the seller-profile module: profile CRUD, onboarding wizard data, the 9-field Legal Metrology compliance block, conditional compliance extensions per super-category (FSSAI, BIS, ISBN, License family), and the `/required-fields` endpoint that drives the frontend onboarding wizard. It owns the `seller_profile` table exclusively. The Export Adapter reads from this module's service layer (never directly from its table) to populate compliance columns at export time.

---

## Section 9 — Module: `category`

STATUS: SKELETON

This section specifies the category and schema module: AI-ranked Smart Picker (Feature 2), manual browse via pg_trgm fallback (the GIN indexes shipped in session 2), category tree retrieval, compiled wizard schema fetch, and field-enum lookup for Brand-pattern fields (the 291 same-name-different-source enums). It owns `categories`, `templates`, `field_enum_values`, and `field_aliases` tables. Catalog validation and Export Adapter both call this module's service to resolve schemas — they never read these tables directly.

---

## Section 10 — Module: `catalog`

STATUS: SKELETON

This section specifies the catalog/product module: draft creation, autosave (Feature 3), AI auto-fill orchestration (Feature 4), draft recovery on reload, and validation of submitted fields against the template schema fetched from `category`. It owns `catalogs` and `products` tables. This module is the **central spine** — image, pricing, dashboard, and export all reference products created here, and it relies on `category` for schema validation and `customer` for compliance gating. Draft recovery is exposed as the explicit endpoint `GET /products/{id}/draft` per MVP_ARCHITECTURE §11.6; it is one of the 25 endpoints in the locked contract and must be present at module sign-off.

---

## Section 11 — Module: `image`

STATUS: SKELETON

This section specifies the image module: image upload (Feature 5), the 5-step pre-check pipeline (JPEG, RGB/CMYK, ≥1500×1500 resolution, white-background heuristic, watermark vision via Gemini), and GCS storage orchestration. It owns the `product_images` table. The pre-check pipeline is dispatched as Celery jobs; the API endpoints write the upload metadata synchronously then poll status asynchronously. As the primary GCS writer, this module is bound to the bucket layout `gs://meesell-images/{user_id}/{product_id}/{image_idx}.jpg` with signed URLs scoped per image and TTL 1 h per MVP_ARCHITECTURE §10.8 (mirrored from §6 for completeness — the contract is identical).

---

## Section 12 — Module: `pricing`

STATUS: SKELETON

This section specifies the pricing module: P&L calculator (Feature 7), commission lookup from the category snapshot, GST snapshot at calc time, and suggested MRP based on target margin. It owns the `pricing_calcs` table. The latent `services/pricing_engine.py` import bug noted in session-2 close-out gets resolved here — `schemas/pricing.py` is re-authored as part of this module's contract, scoped to Feature 7 only.

---

## Section 13 — Module: `dashboard`

STATUS: SKELETON

This section specifies the read-only dashboard module: paginated catalog/product listing (Feature 8), draft listing, basic stats (counts by status), and recent-activity feed. It owns no tables — it is a pure read-aggregation layer over `catalog`, `image`, `pricing`, and `export` data. It demonstrates the "module without its own table" pattern and the inter-module read contract enforced in §16.

---

## Section 14 — Module: `export`

STATUS: SKELETON

This section specifies the export module and the Export Adapter (Feature 9, MVP_ARCHITECTURE §5.5): Meesho XLSX generation via the 9-step pipeline, compliance Strategy classes (standard 9-field vs collapsed Eye-Serum 3-field), round-trip validation (§5.7), per-marketplace adapter interface for V2 readiness, and the exports record lifecycle. It owns the `exports` table. This is the **only** module in the system that knows Meesho's wire format — philosophy mandate M10 lives here.

---

## Section 15 — Cross-Cutting Systems Walkthrough

STATUS: SKELETON

This section is the **single source of truth for cross-cutting concerns** as they participate across all eight modules: multi-tenancy (how `user_id` scoping is enforced in every query), caching (which keys, which TTLs, which Valkey DB), search indexing (the pg_trgm pattern from G4), audit log (per philosophy M8 traceability), AI ops (cost tracking + guardrails per M7/F3), and plan guard (free vs pro enforcement points). Each concern is described once here, then referenced from each module section rather than repeated.

---

## Section 16 — Inter-Module Communication Rules

STATUS: SKELETON

This section defines the contract between modules: what `catalog` IS allowed to do (call `category.service.fetch_schema` to validate fields), what it is NOT allowed to do (import `category.repository` or read `templates` directly via SQL), and the symmetric rule for every module pair. It also specifies how this discipline survives V1.5/V2 extraction — service-layer calls become network calls without changing call sites. This is the rule that keeps the modular monolith extractable rather than tangled.

---

## Section 17 — Endpoint Inventory

STATUS: SKELETON

This section is the locked 25-endpoint contract mapped to module owners. The table has columns: HTTP verb, path, module owner, V1_SPEC source (§3.1 / §3.2 / §3.3 / §3.4 / §5 / §7.7 / §11.6), and one-line summary. This is the master endpoint registry — when a specialist asks "who owns POST /api/v1/products/{id}/autofill?", they look here first. Cross-checked against the founder ruling 2026-06-05 that §3 + §7.7 + §11.6 supersedes §11.1's stale "20".

---

## Section 18 — Background Jobs (Celery)

STATUS: SKELETON

This section enumerates the Celery job catalog: which modules emit jobs (image, export, AI auto-fill), which workers consume them, the queue layout in Valkey DB 1 (broker) and DB 2 (result backend), and the retry/dead-letter policy. It also locks the `include=[]` + per-module worker registration pattern decided in session 2 close-out so import-bug regressions like the deleted `pricing_engine.py` cannot cascade to the broker.

---

## Section 19 — Test Strategy

STATUS: SKELETON

This section specifies the test pyramid: per-module unit tests (pure functions, validators, Strategy classes), per-module API integration tests (router + service + repository against test DB), cross-module end-to-end tests (the coordinator owns these — full catalog-to-export journey), round-trip golden fixtures (§5.7, one per super-category, 12 total), tenant isolation regression tests, and the performance budgets (3 s smart picker P95, 5 s auto-fill P95, 8 s image pre-check, 15 s export). It also defines the test-DB lifecycle and per-module pytest markers. Backend-wide performance budgets are consolidated HERE as the single assertion point: P95 schema fetch ≤ 50 ms (cache hit) and ≤ 200 ms (cache miss) per MVP_ARCHITECTURE §6.6, P95 manual-browse query ≤ 200 ms per §7.5, end-to-end export pipeline ≤ 30 s per §5.5.10, and per-call Gemini cost ≤ ₹0.05 average per §8.2 — module sections cite these targets rather than redefining them.

---

## Section 20 — Deployment Topology (V1)

STATUS: SKELETON

This section concretizes §1 into K3s manifests: pod layout (API ×2, worker ×2, Postgres ×1, Valkey ×1), env-var contracts, secret references, replica counts, resource requests/limits, liveness/readiness probes, and the rolling-update strategy. It is the bridge between this document and the `meesell-infra-builder` track — the infra builder consumes this section to author k8s YAML.

---

## Section 21 — Extraction Path (V1.5 / V2)

STATUS: SKELETON

This section is the per-module extraction cookbook: what changes when a module becomes its own pod (Dockerfile, service contract surface, JWT propagation), the database-split strategy (logical split first via schema, physical split second via separate Postgres), and the recommended extraction order (which module is safest to extract first — likely `export` since it is the most isolated, which is hardest — likely `catalog` since it is the spine). This section is the proof that "modular monolith" was the right choice — extraction is a planned migration, not a rewrite.

---

## Section 22 — Acceptance & Sign-Off

STATUS: SKELETON

This section is the V1-done checklist mirrored from `docs/V1_FEATURE_SPEC.md` §8, expressed at the backend granularity: per-module acceptance criteria, the 25-endpoint contract green-state assertion, golden-fixture round-trip pass rate, test-coverage threshold, and the founder sign-off ritual. When every checkbox here is ticked, the backend is V1-complete and the coordinator hands off to the deployment phase.

---

## Section 22A — Risk Register & Mitigations

STATUS: SKELETON

This section enumerates the 10 backend-specific architectural risks from MVP_ARCHITECTURE §13 alongside the mitigation each design choice in this document carries: RLS deferred (V1.5) → CI linter forbidding raw queries without `user_id` + per-PR isolation regression test; Valkey SPOF → Postgres fallback on cache miss + fail-open RL with alarm; AI cost overrun → daily ₹500 cap + graceful UX fallback per §6A; brand picker latency → server-side pagination + client cache; Eye-Serum dual-shape → Export Adapter Strategy class per §14; canonical-name vs XLSX raw header mismatch → `field_aliases.for_xlsx_export` reverse map; 1,831 unique field names → per-template visual smoke fixture; FSSAI compulsory-at-signup → onboarding wizard surfaces requirement pre-OTP; compulsory-field median 33 → wizard progress bar + AI autofill coverage; brand-master scale → deferred V1.5 builder. This is the canonical defense citation: future PRs that touch a constrained area cite this register to justify the design choice rather than re-litigating it.

---
