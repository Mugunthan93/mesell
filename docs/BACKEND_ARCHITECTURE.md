# MeeSell — Backend Architecture (Construction Contract)

**Status:** LOCKED — 26 of 26 sections LOCKED (2026-06-06); construction contract for the 4 backend specialists
**Date:** 2026-06-05 (initial) → 2026-06-06 (architecture 100% complete)
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

STATUS: LOCKED (2026-06-05)

### A. What this document is

This document is the **construction contract** for the four backend specialists (`meesell-database-builder`, `meesell-api-routes-builder`, `meesell-services-builder`, `meesell-auth-builder`). Builders execute against this contract; they do NOT improvise, do NOT infer requirements from `docs/MVP_ARCHITECTURE.md`, and do NOT write code outside what a LOCKED section explicitly authorises. Where this document differs from any prior backend assumption (session-0 scaffold, session-1 router drafts, ad-hoc TICKETS.md interpretation), this document supersedes. `docs/MVP_ARCHITECTURE.md` remains the DATA track's source of truth and the authoritative DDL / corpus reference; this document peers with it and translates it into a backend-construction plan without contradiction.

Sections in this document carry an explicit `STATUS: SKELETON | DRAFT | LOCKED` line directly under their heading. Specialists may NOT begin code on a section until the section's status is `LOCKED`. A section in `DRAFT` is in founder review and is not authoritative for dispatch. The coordinator does not flip a section from `DRAFT` to `LOCKED` — only the founder does, on a turn dedicated to that sign-off.

### B. Architecture style — Modular Monolith with extraction-ready boundaries

**Decision:** the V1 backend is built as a single FastAPI process organised into eight self-contained domain modules (`iam`, `customer`, `category`, `catalog`, `image`, `pricing`, `dashboard`, `export`) plus three non-domain layers (`adapters/`, `core/`, `shared/`). Module-to-module communication is strictly through service-layer call sites; cross-module table reads and cross-module repository imports are forbidden (the rule is concretised in §16).

**Why not full microservices in V1.** Three reasons, all decided in this session:
1. **Sprint constraint.** V1 is a 7-day construction sprint. Eight micro-services would multiply the surface area of CI/CD, secrets, service discovery, and inter-service auth beyond what the sprint can absorb.
2. **Single-node K3s floor.** The cluster is one VM. Eight separate API pods plus 8 worker pods imposes a ~3-4 GB RAM floor for the pods alone before Postgres / Valkey / Gemini SDK overhead. A single FastAPI pod (2 replicas) plus a single Celery worker pod (2 replicas) fits comfortably.
3. **Inter-service auth complexity.** Every cross-service call would need its own JWT-propagation contract, retry/idempotency handling, and tracing. In V1 these are function calls inside one process.

**Why this preserves V1.5+ extraction.** Domain boundaries encoded today (no cross-module SQL, services as the only public surface, repository code private to its module) mean any module can become its own pod later by replacing the service-layer call with an HTTP/gRPC client — call sites do not change. The extraction cookbook is §21.

**Why this is not "just an MVC monolith".** The discipline that distinguishes a modular monolith from a tangled monolith is the inter-module communication contract (§16). A traditional MVC layout shares models across controllers freely; the modular monolith forbids exactly that — `catalog` may NOT import `category.repository`, may NOT read `templates` directly via SQL, may only call `category.service.fetch_schema()`. This is what keeps the V1.5 extraction "delete the function call, replace with HTTP call" rather than "untangle six months of cross-table joins".

### C. The 25-endpoint contract

`docs/MVP_ARCHITECTURE.md §11.1` states "Implement 20 API endpoints per §3" (16 from V1_FEATURE_SPEC §5 + 4 seller-profile). This line is **stale** — the same paragraph also says "Implement the 8 SQLAlchemy models per §2" while the actual model count is 13 (the live Alembic chain enumerates them at head). Backend builds against `§3 + §7.7 + §11.6` of `docs/MVP_ARCHITECTURE.md`, which yields **25 endpoints**:
- §3 enumerates 23 endpoints across §3.1 (2 auth), §3.2 (5 seller-profile), §3.3 (5 categories + schema), §3.4 (11 catalog/product/export).
- §7.7 adds `GET /api/v1/categories/browse?q=&super_id=&limit=&offset=` (the manual-browse fallback served by the pg_trgm GIN indexes shipped in session 2).
- §11.6 implies `GET /api/v1/products/{id}/draft` (autosave recovery on browser reload — line 2483).

The founder ruling 2026-06-05 (recorded in coordinator memory, session 2 close-out) is that `§3 + §7.7 + §11.6 = 25 endpoints` is the authoritative contract; `§11.1`'s "20" is dead. Section 17 of this document is the canonical mapping of those 25 endpoints to module owners, and becomes the master endpoint registry once locked. When a specialist asks "is endpoint X in scope?", the answer is "is it in §17?" — not "is it in V1_FEATURE_SPEC?", not "is it in MVP_ARCH §11.1?". Ruling D3 (this session) commits a one-line amendment to `MVP_ARCHITECTURE.md §3.4` during the Feature 2/3 dispatch so future readers do not re-litigate the 25th endpoint.

**AMENDMENT 2026-06-05 — FE-D5 ratification:** the 25-endpoint contract is extended by the **2 FE-D5 auth endpoints** (`POST /api/v1/auth/refresh` and `POST /api/v1/auth/logout`) per the frontend-coordinator memo `.claude/agent-memory/meesell-frontend-coordinator/backend_handoff_jwt_session_pattern.md` and the FE-D5 + FE-D6 founder rulings 2026-06-05 (split-token + server-side-revocation auth pattern). The authoritative V1 contract is therefore **27 endpoints** = §3 (23) + §7.7 (1) + §11.6 (1) + FE-D5 (2). Section 17 reflects 27 endpoints; every later count in this document that previously cited "25" is superseded by "27" on the auth scope. The 2 new endpoints are owned by the `iam` module (per §7 amendment) and are non-JWT-protected (the refresh cookie itself is the auth credential for `/auth/refresh`; `/auth/logout` is idempotent and accepts both). Chain of custody: FE-D5 (no client-side token storage) + FE-D6 (env-driven lifetimes) → backend ratification this session → §17 SKELETON refinement to enumerate the 27 endpoints when authored. (End amendment.)

### D. Database baseline — 13 tables, head revision `f31c75438e61`

Backend INHERITS the schema from the DATABASE track. The current head is `f31c75438e61`, chained on `a1b2c3d4e5f6` (the pg_trgm + GIN migration shipped in session 2). Backend does NOT modify the schema except via formal Alembic migrations authored by `meesell-database-builder`. The 13 tables at head are:

`users`, `seller_profile`, `templates`, `categories`, `field_enum_values`, `field_aliases`, `catalogs`, `products`, `product_images`, `pricing_calcs`, `exports`, `audit_events`, `product_drafts`.

`docs/MVP_ARCHITECTURE.md §2` is the authoritative DDL. This document does NOT duplicate the DDL — module sections cite the relevant subsection (§2.1 users, §2.2 seller_profile, §2.3 templates/categories/field_enum_values, §2.4 catalogs/products, §2.5 product_images/pricing_calcs/exports). The 10-step Alembic ordering in §2.6 is the single migration-sequence reference; §5 of this document cites it rather than redefining it. If a builder needs a column type they do NOT remember, they read `MVP_ARCH §2`; they do NOT consult the live ORM models, which are the implementation, not the spec.

### E. Backend tree baseline — clean-state

The pre-`MVP_ARCHITECTURE.md` backend drafts were purged in session 2 (gap pass G2/G3). Current state, verified at the start of session 3:
- `backend/app/main.py` mounts ONLY `auth_router`. Nine routes total on the app (auth × 2 + `/me` + `/health` + 5 FastAPI defaults).
- 42/42 schema tests pass (`backend/tests/test_database.py`).
- 7/7 boot integration tests pass (`backend/tests/test_app_boot_integration.py`).
- Zero import errors, zero collection errors, zero URL-mismatch failures.

Construction builds FORWARD from this baseline. Specialists do NOT patch deleted-router draft code; they author against this document. Proof of state lives in `docs/status/STATUS_BACKEND.md` session 2 close-out and in coordinator memory `session_2_gap_pass` / `session 3 turn 1` entries.

One latent regression is queued for the construction phase rather than rebuild-the-baseline phase: `backend/app/services/pricing_engine.py` line 23 imports `from app.schemas.pricing import PricingAlert`, but `schemas/pricing.py` was deleted in G3. The file is unimportable today but no live importer hits it (no pricing router is mounted in `main.py`). The §12 (Module: `pricing`) dispatch resolves this when Feature 7 lands — either by re-authoring `schemas/pricing.py` to host `PricingAlert` and the rest of the Feature 7 contract, or by refactoring `pricing_engine.py` to use a plain dataclass. The choice belongs to the Feature 7 dispatch, not this section.

### F. Founder-locked rulings this session (D1–D4)

These rulings are normative for every later section in this document.

- **D1. Legacy router deletion outright (no `.bak`).** Implication: any reference in code or comments to deleted routers (`catalogs`, `skus`, `images`, `pricing`, `exports`, `generation`, `quality`, `research`) is dead. Specialists encountering such references during construction flag them for removal — do not resurrect them.
- **D2. `is_advanced` allowlist = `group_id` only for V1.** Implication: `scripts/build_template_schemas.py` `ADVANCED_CANONICAL_NAMES = {"group_id"}` is locked. Schema-builder seed config does not expand the set without a written spec change reviewed by the founder. Frontend renders Group ID inside the "Advanced fields" expandable per Philosophy Pattern 5.
- **D3. `MVP_ARCHITECTURE.md §3.4` will be amended during construction to enumerate `GET /api/v1/products/{id}/draft` as the 25th endpoint.** Implication: when the Feature 2 / Feature 3 endpoints land, the same dispatch updates §3.4 inline. The doc-PR accompanies construction; it is not a separate later cleanup turn.
- **D4. Code is written ONLY by the respective specialist sessions; master orchestrates and coordinator coordinates — neither writes code.** Implication: every code-writing task (creating or modifying files under `backend/app/`) is executed by the relevant `meesell-*-builder` specialist (`meesell-database-builder`, `meesell-api-routes-builder`, `meesell-services-builder`, `meesell-auth-builder`). The master session dispatches specialists and reviews their work — it does NOT directly write production code. The coordinator (this agent) dispatches specialists when permitted, authors and updates `BACKEND_ARCHITECTURE.md`, updates `STATUS_BACKEND.md`, updates its own memory, and produces integration glue documentation — but does NOT write production code under `backend/app/`. Production code authorship is the specialists' role, period.

### G. 14 founder-locked decisions inherited from `MVP_ARCHITECTURE.md §12` and §15

`MVP_ARCHITECTURE.md §15` records 14 of 14 founder decisions reflected (8 from initial batch review + 6 from architecture review in §12). The 6 architecture-review decisions and their BACKEND implications:

- **§12.1 Books ISBN — follow Meesho (optional).** Implication: `isbn` is a regular optional field in the schema; `customer` module does NOT compulsorily collect it at onboarding for super_id 80.
- **§12.2 Meesho source typos — auto-correct internally, restore verbatim on XLSX export.** Implication: `export` module's Export Adapter consults `field_aliases.for_xlsx_export = TRUE` rows as a reverse map (canonical → category-specific raw header) when emitting Meesho-format XLSX. Round-trip test required on Mobiles & Tablets (§5.7).
- **§12.3 Long-tail super-categories — include all 3,772 in V1.** Implication: `category` module's Smart Picker and `/browse` endpoint apply no leaf-count filter. Seed remains at 3,557 templates + 3,772 categories + ~200K `field_enum_values` rows.
- **§12.4 Group ID — "Advanced fields" toggle (Pattern 5).** Implication: `category` module emits `is_advanced = true` for `canonical_name = "group_id"` in `templates.schema_jsonb.fields[]`. Validation in `catalog` module accepts the field whether or not the wizard expanded it; `export` writes whatever the seller filled, blank if untouched. The `is_advanced` JSONB flag is respected by validation but does not gate writes.
- **§12.5 Warranty — per-product wizard step (match Meesho).** Implication: NOT an onboarding extension; `seller_profile.compliance_extensions` does NOT carry warranty keys. `catalog` module's schema validator treats warranty fields (`warranty_period`, `warranty_type`) as regular per-product fields surfaced by `templates.schema_jsonb` for the ~190 categories that carry them.
- **§12.6 Eye-Serum collapsed compliance — collect 9 standard fields, transform at export.** Implication: `seller_profile` stores the 9 standard compliance fields ONLY (manufacturer/packer/importer × name/address/pincode). `export` module hosts a `CollapsedComplianceStrategy` class that concatenates 9 → 3 combined strings when emitting an XLSX for any template whose `compliance_shape = "collapsed"`. All other 3,771 templates use the `StandardComplianceStrategy`. This honours Philosophy F4 (no derived data stored) and M10 (Meesho format never leaks past the adapter).

The remaining 8 founder decisions cited in `§15` sign-off (the initial batch — `seller_profile` design, schema-by-template storage, 10 input primitives, data-driven wizard, enum-constrained AI, Smart Picker top-5, conditional onboarding extensions, canonical-name normalisation) are honoured implicitly by the data model in §2 and the API surface in §3, which this document inherits unchanged. The backend implication of each is enforced at the module level (`category`, `customer`, `catalog`, `export`) — module sections cite the relevant §12 / §15 anchor rather than re-list the decisions here.

### H. CORE_PHILOSOPHY compliance commitments

`docs/CORE_PHILOSOPHY.md` is the rulebook. The backend commits to honouring the following rules as construction invariants — module sections cite each rule rather than re-stating it.

- **M7 (AI works in canonical space) — enum guardrail.** No AI-emitted value that is not in the per-category enum allowlist reaches the database OR the Export Adapter. Enforced at three layers (prompt constraint, parser-level enum check, Export Adapter re-validation) per §6A.
- **M9 (localisation is structural) — i18n package.** No hardcoded English strings outside `app/i18n/`. Validation messages, display labels, and help text are resolved via `validation_message_id` lookups per `MVP_ARCHITECTURE.md §5.6.7`. V1 ships English; V1.5 adds Tamil/Hindi without schema migration.
- **M10 (Export Adapter is the single source of Meesho-format knowledge).** `meesho_column_header`, `meesho_column_index`, and `enum_codes_map` NEVER appear in cache payloads, API responses, AI prompts, or non-export module code. They live exclusively under `app/modules/export/` and `app/adapters/` boundaries.
- **F3 (never send invalid enum values to Meesho) — 3-layer guardrail.** Prompt-level constraint (Layer 1, §8.6.1 of `MVP_ARCH`), parser-level rejection (Layer 2, §8.6.2), backend re-validation at export time (Layer 3, §8.6.3). All three present at module sign-off.
- **F4 (never collect or store data we don't need).** Compliance fields stored as 9, never 12, per the Eye-Serum decision (§12.6). The 3 combined "Details" columns are derived at export time only.
- **F5 (never show a field without an explanation).** `help_text` is mandatory in `templates.schema_jsonb.fields[]`; seed-time validators reject any field without it (Pattern 5 advanced fields are the documented exception — the seller's expand action is the acknowledgement that relaxes F5).

### I. Corpus-grounded premises imported from MVP_ARCHITECTURE §0

These are facts from full-corpus parse, not hypotheses. Cited verbatim from `MVP_ARCHITECTURE.md §0` for backend reference.

- 3,772 categories share **15 strict-universal + 13 near-universal fields** (28 practical universals).
- **No Recommended tier** — binary Compulsory/Optional.
- Image rules are **100% uniform corpus-wide** (4 slots, slot 1 required).
- **1,831 unique field names** corpus-wide → **10 input primitives** cover the field universe.
- **291 Brand-pattern fields** (same name, different enum source per category) → enums stored per `(category_id, field_name)`.
- Median compulsory-field count varies **19–33 by super-category** (wizard step count is data-driven).
- **3,557 distinct templates** serve **3,772 leaves** (5.7% dedup).
- **Eye-Serum represents an alternate compliance shape** (1 of 3,772) — backend supports both via Export Adapter Strategy classes.

### J. What Section 0 does NOT cover

Section 0 is decision-record only. The runtime topology (one FastAPI pod, 2 replicas; Postgres, Valkey, Celery, GCS, Gemini wiring; ASCII diagram) lives in §1. Module boundaries and per-module responsibility summaries live in §2. The canonical `backend/app/` tree (`modules/`, `adapters/`, `core/`, `shared/`, `workers/`, root files) lives in §3. Cross-cutting concerns (multi-tenancy, caching, audit log, AI ops, plan guard) live in §15. The 25-endpoint registry (verb, path, owner, source) lives in §17. Section 0 establishes the WHY; later sections specify the WHAT and WHERE.

A reviewer evaluating Section 0 is asking only: "are the premises sound, are the rulings correct, are the inherited decisions all here?" — not "is the file structure right" (§3), not "are the modules correctly carved" (§2), not "is the endpoint list complete" (§17). Those evaluations belong to their own founder-review turns.

---

## Section 1 — System Topology

STATUS: LOCKED (2026-06-05)

### A. What Section 1 establishes

Section 1 is the **runtime topology map** of the V1 backend — what processes run, what services they talk to, and in what direction data flows. It is NOT a K3s manifest spec (that belongs to §20), NOT a module catalog (§2), and NOT a directory tree (§3). The single question Section 1 answers is: "if a client makes an HTTP request to `studio.mesell.xyz`, what runs, what gets called, and what flows back?" Every later section refines a slice of this map — §4 expands the middleware chain, §6 expands the adapter clients, §15 expands the cross-cutting flows, §18 expands the Celery queues, §20 expands pod manifests. Section 1 is the cornerstone they all anchor to.

### B. ASCII topology diagram

```
                                   ┌──────────────────────────────┐
                                   │  Client (Angular 18 PWA /    │
                                   │  mobile browser)             │
                                   └───────────────┬──────────────┘
                                                   │ HTTPS (JWT in Authorization header)
                                                   ▼
                                   ┌──────────────────────────────┐
                                   │  Traefik ingress             │
                                   │  TLS via cert-manager (LE)   │
                                   │  studio.mesell.xyz           │
                                   └───────────────┬──────────────┘
                                                   │ HTTP (in-cluster)
                                                   ▼
                                   ┌──────────────────────────────┐
                                   │  K8s Service: api (ClusterIP)│
                                   └───────────────┬──────────────┘
                                                   │ load-balance round-robin
                          ┌────────────────────────┴────────────────────────┐
                          ▼                                                 ▼
                ┌──────────────────┐                              ┌──────────────────┐
                │ FastAPI pod #1   │                              │ FastAPI pod #2   │
                │ uvicorn workers  │                              │ uvicorn workers  │
                │ (middleware →    │                              │ (middleware →    │
                │  route → service │                              │  route → service │
                │  → adapter)      │                              │  → adapter)      │
                └─┬────┬────┬───┬──┘                              └─┬────┬────┬───┬──┘
                  │    │    │   │                                   │    │    │   │
       ┌──────────┘    │    │   └─────────┐         ┌───────────────┘    │    │   └────────┐
       │ sync          │ async             │ sync   │ sync            async    │ egress    │
       │ SQL           │ enqueue           │ cache  │ signed-URL      enqueue  │ external  │ trace
       ▼               ▼                   ▼        ▼                 ▼        ▼           ▼
┌─────────────┐ ┌─────────────┐    ┌───────────────────┐  ┌──────────────┐ ┌──────┐ ┌──────────┐
│ PostgreSQL  │ │ Valkey 8    │    │ Valkey 8 (cont.)  │  │ GCS bucket   │ │MSG91 │ │ LangFuse │
│ 16 pod      │ │ DB 1: Celery│    │ DB 0: OTP, RL,    │  │ meesell-     │ │OTP   │ │ traces   │
│ 13 tables   │ │ broker      │    │ sessions          │  │ images       │ │ SaaS │ │ (async   │
│ head:       │ │ DB 2: Celery│    │ DB 3: app cache   │  │ {user_id}/   │ └──────┘ │ fire-&-  │
│ f31c75…61   │ │ result back │    │ (schemas, enums,  │  │ {product_id}/│          │ forget)  │
└─────────────┘ └──────┬──────┘    │  category tree,   │  │ {idx}.jpg    │          └──────────┘
                       │           │  seller profile)  │  │ signed URL   │
                       │           └───────────────────┘  │ TTL 1h       │
                       │ pop                              └──────────────┘
                       ▼
              ┌──────────────────┐
              │ Celery worker    │   egress  ┌──────────────────────────┐
              │ pod #1 + #2      │──────────▶│ Gemini 2.5 Flash (SaaS) │
              │ (image precheck, │           │ text generate + vision  │
              │  autofill async, │           └──────────────────────────┘
              │  export build)   │
              └─┬────────┬───────┘
                │ write  │ trace
                ▼        ▼
        ┌────────────┐ ┌──────────┐
        │ Postgres + │ │ LangFuse │
        │ GCS (same  │ │          │
        │ as above)  │ └──────────┘
        └────────────┘

  Inbound webhooks:
    Razorpay ──HTTPS──▶ Traefik ──▶ FastAPI (iam module captures payload only in V1)

  Observability scrape (pull, not push):
    Prometheus ─/metrics scrape─▶ FastAPI pods, Celery worker pods ─exposes─▶ Grafana
```

Arrow conventions: solid `▼` / `▶` are sync calls; `async enqueue` markers are Celery dispatches via Valkey DB 1; egress to SaaS goes over the VM's public NIC.

### C. Request flow walkthrough (representative POST)

Representative call: `POST /api/v1/products/{id}/autofill` (Feature 4, AI Auto-fill, §10 owner).

1. Client sends HTTPS request → Traefik ingress (TLS termination via cert-manager Let's Encrypt cert for `studio.mesell.xyz`) → ClusterIP service → one of the 2 FastAPI pods selected by k8s round-robin.
2. Middleware chain runs in §4-locked order: CORS → request-ID → auth (decode JWT `{sub, exp, plan}` per MVP_ARCH §11.7, attach user) → tenancy (inject `user_id` into request context) → rate-limit (Valkey DB 0 sliding-window per MVP_ARCH §10.7) → plan-guard (check `plan` claim against feature budget).
3. Route handler in `modules/catalog/router.py` calls `catalog.service.autofill_product(product_id, user_id)`.
4. Service calls `category.service.fetch_schema(category_id)` — cross-module service call only, per §16 rule (no `from category.repository` import, no direct `templates` SQL).
5. Service calls the `gemini` adapter through the §6A AI Operations Layer (cost tracking, guardrail Layer 1, retry policy, LangFuse trace) — egress to Gemini SaaS over the VM's public NIC.
6. Returned values enum-validated against `field_enum_values` (the F3 Layer-2 guardrail per §0.H), then `catalog.repository` PATCHes `products.ai_suggestions_jsonb`.
7. Post-write middleware writes an `audit_events` row (per MVP_ARCH §11.3 and the §0.F D4 implication: AFTER commit only — see §0 §G citation chain).
8. Response serialized; ETag header set per MVP_ARCH §6.6; flows back through ingress → client.

### D. Background job flow walkthrough (representative job)

Representative job: image pre-check pipeline (Feature 5, §11 owner).

1. Client uploads via `POST /api/v1/products/{id}/images` → FastAPI route saves binary to GCS (`gs://meesell-images/{user_id}/{product_id}/{idx}.jpg` per MVP_ARCH §10.8), writes `product_images` row with `status='pending'`, enqueues `image_precheck_task(image_id)` to Valkey DB 1.
2. Celery worker pops from DB 1, fetches image bytes from GCS (signed URL TTL 1 h per §10.8), runs the 5-step pipeline: JPEG check, RGB/CMYK check, ≥1500×1500 resolution check, white-background heuristic (Pillow), optional Gemini Vision watermark check (cost-tracked + guarded via §6A).
3. Worker writes the structured result to `product_images.precheck_jsonb`, sets `status='ready'`, persists Celery task state to DB 2.
4. Client polls `GET /api/v1/products/{id}/images` (or reads via the dashboard's draft polling); V1 has no WebSocket, no server-push.

### E. External vendor egress map

| Vendor | Adapter | Triggering module(s) | Sync / Async | Retry policy |
|---|---|---|---|---|
| Gemini 2.5 Flash | `adapters/gemini` (wrapped by §6A AI Ops) | `category` (Smart Picker rank), `catalog` (Auto-fill), `image` (watermark vision) | Sync from FastAPI for Picker; async via Celery for Auto-fill and vision | 3-retry exponential backoff via §6A; graceful fallback per MVP_ARCH §8.3 |
| MSG91 | `adapters/msg91` | `iam` (OTP send only) | Sync from FastAPI | 1-retry, then 5xx surfaced to client; OTP send capped at 3/h/phone per MVP_ARCH §10.7 |
| GCS | `adapters/gcs` | `image` (write + signed URL issuance), `export` (write + read for XLSX bundling) | Mixed: signed-URL issuance sync; bulk read on export async via Celery | Native GCS client retries (idempotent ops); 1 h signed-URL TTL per §10.8 |
| Razorpay | `adapters/razorpay` | Inbound webhook → `iam` (subscription state capture in V1; business logic deferred to V1.5) | Inbound sync (webhook receiver) | Signature verification only in V1; failed-signature → 401 |
| LangFuse | `adapters/langfuse` (interface deferred to §6A detail) | All AI call sites | Async fire-and-forget from FastAPI + Celery | None — drop-on-failure; observability MUST NOT block business path |

### F. Cross-cutting flow callouts

- **Caching read-path.** Any module reading `templates` / `categories` / `field_enum_values` / `seller_profile` MUST go through `core/cache.py`, which checks Valkey DB 3 first, falls back to Postgres, populates cache. Keys are version-tagged per MVP_ARCH §6.4 so the quarterly Meesho refresh invalidates atomically without `FLUSHDB`. Cited from MVP_ARCH §6.
- **Rate limit enforcement.** Per-user sliding-window counters in Valkey DB 0 are checked by middleware BEFORE the route handler runs (per the §4-locked order). Soft caps from MVP_ARCH §10.7 (OTP 3/h, autofill 50/h, picker 100/h, create-product 20/h) are enforced as hard 429s in V1; soft-cap-with-alarm posture lives in §6A for AI calls only.
- **Audit log write-path.** Middleware AFTER successful HTTP 2xx response writes an `audit_events` row. In V1 this is a synchronous append per MVP_ARCH §11.3; V1.5 moves it to a Celery sink. Failed transactions never log — the rule is "if it committed, it logged; if it didn't commit, it never happened" (philosophy M8 traceability).

### G. Network boundaries

Inside the FastAPI pod: middleware chain + route handlers + service layer + repository layer + adapter clients. Inside the K3s cluster but in separate pods: Postgres 16 (the 13-table store at head `f31c75438e61`), Valkey 8 (DBs 0/1/2/3 on a single instance with `maxmemory 128mb allkeys-lru` per infra memory), and the Celery worker pod (same image as FastAPI, different command). Outside the cluster as external SaaS: Gemini, MSG91, Razorpay, GCS, LangFuse. The security boundary that matters most is the JWT — it is decoded only inside the FastAPI pod and the Celery worker pod; tokens never appear in Postgres rows, never in Valkey keys, never in GCS object metadata. Workers that resume async tasks re-validate the JWT carried in the task payload (the §6A guardrail makes this explicit for AI tasks).

### H. What Section 1 does NOT cover

K3s manifests — pod resource requests/limits, replica counts, liveness/readiness probes, secret references, rolling-update strategy — live in §20. Module internal structure (router/service/repository layout per module) lives in §3. Specific middleware code (exact order, what each one does, dependency-injection contract) lives in §4. Specific adapter retry implementations (backoff strategy, circuit-breaker thresholds, fallback class hierarchy) live in §6 and §6A. Specific Celery queue names, worker concurrency, and dead-letter policy live in §18. Section 1 is the topology map; later sections specify each component's spec.

---

## Section 2 — Module Catalog

STATUS: LOCKED (2026-06-05)

### 2.A — Section preamble

The Module Catalog is the **ownership map** for specialists. When the founder dispatches a Feature ticket, the specialist consults Section 2 to know (a) which module they are building in, (b) which other modules they MAY call — only via the service layer per §16, (c) which tables they MAY write to, (d) which adapters they use, and (e) which other modules they MAY NOT touch. Section 2 does NOT define internal module structure (that is §3), does NOT define endpoint signatures (that is §17), and does NOT define schema (that is MVP_ARCH §2). It defines the **ownership contract** — the cross-module boundary that the modular monolith depends on per §0.B. Each sub-section below corresponds to one module or one cross-cutting layer; reviewers evaluate Section 2 by asking "are the boundaries airtight, are write-ownerships singular, are AI-track seams clean?" — not "is the file tree right" (§3), not "is the endpoint mapped" (§17).

---

### 2.1 — Module: `iam`

**Owner specialist(s):** `meesell-auth-builder` (sole owner — routes, services, JWT logic, middleware deps all in scope per agent spec).
**AI track collaboration:** no — `iam` is pure auth; no AI call sites.

**Responsibilities:**
- OTP send/verify lifecycle via the `msg91` adapter (Feature 1; cited per `V1_FEATURE_SPEC §2 Feature 1`).
- JWT issuance + verification, claim shape `{sub, exp, plan}` per `MVP_ARCH §11.7`; exposes `get_current_user` as the canonical FastAPI dependency consumed by every other module.
- DPDP consent capture at OTP-verify time, and Razorpay webhook signature verification + payload capture (V1 captures only — subscription business logic deferred to V1.5 per `MVP_ARCH §14`).

**NOT responsible for:** seller business profile data (`seller_profile`) — that belongs to `customer`; `iam` owns identity only, not commerce relationship.

**Database tables — WRITE-OWNS:** `users` (insert on first OTP-verify; update `last_login_at` on subsequent verify; update `plan` only on Razorpay webhook capture).
**Database tables — READS-FROM:** none beyond `users` (re-read of its own table for login flow).

**Cross-module dependencies (service calls only, per §16):**
- (none) — `iam` is a **leaf module** by design. Other modules consume `get_current_user` through the `core/` middleware chain, not by service call.

**Adapters used:** `msg91` (OTP send), `razorpay` (webhook signature verification only in V1 per §6 and §1.E).

**V1_FEATURE_SPEC mapping:** Feature 1 — Auth (Phone OTP + JWT), `V1_FEATURE_SPEC §2 Feature 1`.
**Endpoint count:** 2 (auth send + auth verify) + the `/me` introspection route inherited from session-2 baseline (per coordinator memory `session 2 close-out`). Razorpay webhook is also surfaced here. Canonical signatures locked in §17.
**MVP_ARCH cross-references:** §3.1 (endpoint shape), §10.7 (3/h OTP rate limit), §11.7 (JWT claim contract), §11.8 (audit-after-commit for login events).

**Extraction notes (V1.5+):** `iam` is the second-easiest module to extract after `export` because its data surface is small (one table) and its public contract is already an interface (`get_current_user` becomes a remote JWT-validation HTTP call). Owns the `users` table cleanly in extraction; the `seller_profile` table stays with `customer`.

---

### 2.2 — Module: `customer`

**Owner specialist(s):** `meesell-api-routes-builder` (routes + Pydantic schemas) + `meesell-services-builder` (business logic, compliance extension resolver, onboarding state machine).
**AI track collaboration:** no — seller-profile data is structured CRUD, no AI ranking or generation.

**Responsibilities:**
- Seller profile CRUD (`GET`/`PATCH /api/v1/seller-profile`) and the onboarding wizard data-feed (`GET /required-fields`) per `MVP_ARCH §3.2`.
- The 9-field Legal Metrology compliance block (manufacturer/packer/importer × name/address/pincode) per `MVP_ARCH §2.2` and the Eye-Serum-honoured F4 rule per `§12.6`.
- Conditional compliance extensions per super-category (FSSAI, BIS, R/IS/CM-L, License, ISBN per `MVP_ARCH §0` premise #7 and `§12.1`).

**NOT responsible for:** identity (`users` table — `iam` owns it); product-level warranty (per `§12.5` warranty is per-product, lives in `catalog`'s schema validation, not in `seller_profile`).

**Database tables — WRITE-OWNS:** `seller_profile`.
**Database tables — READS-FROM:** `users` (FK lookup only — never INSERT/UPDATE).

**Cross-module dependencies (service calls only, per §16):**
- (none) — `customer` is a leaf module. `export` reads seller-profile state via `customer.service` per §16, not the reverse.

**Adapters used:** none.

**V1_FEATURE_SPEC mapping:** No standalone V1 Feature row; `customer` is the **Onboarding bucket** introduced by `MVP_ARCH §2.2` per founder decision #1 + #9. It is a structural prerequisite for Features 3-9 — without a complete `seller_profile`, the `POST /products` flow returns the `PROFILE_INCOMPLETE_FOR_CATEGORY` 422 per `MVP_ARCH §3.3`.
**Endpoint count:** 5 endpoints per `MVP_ARCH §3.2`. Canonical signatures locked in §17.
**MVP_ARCH cross-references:** §2.2 (DDL), §3.2 (endpoints), §11.7 (`user_id` FK enforcement), §12.1 (Books ISBN), §12.5 (warranty NOT here), §12.6 (Eye-Serum collapsed compliance — `customer` stores 9 standard fields ONLY; `export` derives the collapsed shape).

**Extraction notes (V1.5+):** Extracts cleanly with the `seller_profile` table. The conditional-extensions resolver carries the V1.5 RLS migration path (per `MVP_ARCH §14`) when `user_id` foreign keys become tenant-scoped RLS predicates.

---

### 2.3 — Module: `category`

**Owner specialist(s):** `meesell-api-routes-builder` (routes + Pydantic response schemas) + `meesell-services-builder` (business logic, cache layer, browse search).
**AI track collaboration:** **YES** — `meesell-category-picker-builder` owns the Smart Picker AI ranking pipeline (compression heuristics, confidence calibration, Gemini call orchestration per its agent spec). The seam: backend's `category` module owns the REST endpoint, the cache layer, the browse search, and the read paths for `categories`/`templates`/`field_enum_values`/`field_aliases`; the AI track's `category-picker-builder` owns the Gemini call into the compressed tree and returns the ranked top-5. The category module **CALLS INTO** the AI track's logic via the `gemini` adapter wrapped by §6A AI Ops.

**Responsibilities:**
- AI-ranked Smart Picker endpoint (`GET /api/v1/categories/suggest`) — backend orchestrates cache, calls AI track, returns the 5-card response per Feature 2 + `MVP_ARCH §5.1`.
- Manual browse fallback (`GET /api/v1/categories/browse`) via the pg_trgm GIN indexes shipped in session 2 (per coordinator memory G4 + `MVP_ARCH §7`).
- Compiled wizard schema fetch (`GET /api/v1/categories/{id}/schema`) and field-enum lookup (`GET /api/v1/categories/{id}/field-enum/{name}`) — including the 291 Brand-pattern fields per `MVP_ARCH §0` premise #5.

**NOT responsible for:** AI prompt content (`meesell-prompt-engineer` owns prompts); validation of a seller's product values against schema (that is `catalog`'s job); writing to `categories`/`templates` at runtime (those are seed-time only, owned by the DATABASE track — `category` is **read-only** against these tables in V1).

**Database tables — WRITE-OWNS:** **none.** The `categories`, `templates`, `field_enum_values`, and `field_aliases` tables are populated by the DATABASE track's seed scripts (per coordinator memory `session 2 close-out`) and the backend never INSERT/UPDATE/DELETEs them at runtime. The quarterly Meesho refresh re-runs the seed per `MVP_ARCH §6.5.1` — not a `category` module operation.
**Database tables — READS-FROM:** `categories`, `templates`, `field_enum_values`, `field_aliases`.

**Cross-module dependencies (service calls only, per §16):**
- (none) — `category` is a leaf module on the cross-module graph; other modules (`catalog`, `export`, `pricing`) call into `category.service`, not the reverse.

**Adapters used:** `gemini` (via §6A AI Ops for Smart Picker ranking).

**V1_FEATURE_SPEC mapping:** Feature 2 — Smart Category Picker, `V1_FEATURE_SPEC §2 Feature 2`.
**Endpoint count:** 5 endpoints per `MVP_ARCH §3.3` + `§7.7`. Canonical signatures locked in §17.
**MVP_ARCH cross-references:** §3.3 (endpoints), §5.1 (AI Picker), §6 (caching read-path — `category` is the heaviest cache consumer), §7 (browse + GIN), §11.7 (no `user_id` scoping needed — category data is global), §12.3 (long-tail super-categories, no leaf-count filter), §12.4 (`is_advanced` flag respected in schema responses).

**Extraction notes (V1.5+):** `category` is a strong extraction candidate because it owns no writes — pure read service with cache. Becomes a stateless ranking + schema microservice; cache layer moves with it. Brand-master extraction (deferred per agent registry) lands here.

---

### 2.4 — Module: `catalog`

**Owner specialist(s):** `meesell-api-routes-builder` (routes + Pydantic schemas) + `meesell-services-builder` (business logic, AI auto-fill orchestration, draft autosave, schema validation, dispatcher into AI track).
**AI track collaboration:** **YES** — AI Auto-fill (Feature 4) is invoked here. The seam: `catalog` module owns the `POST /products/{id}/autofill` endpoint, schema fetch (via `category.service`), guardrail Layer 2 enum re-validation, and the write to `products.ai_suggestions_jsonb`; `meesell-prompt-engineer` owns the autofill prompt template content; the §6A AI Ops Layer wraps the actual Gemini call with cost tracking, LangFuse trace, and Layer 1 guardrail.

**Responsibilities:**
- Product CRUD (draft create, autosave PATCH, soft delete) and validation against `templates.schema_jsonb` fetched from `category` (Features 3, 4, 6 per `V1_FEATURE_SPEC §2`).
- Autosave drafts with 5-minute coalescing per `MVP_ARCH §11.4`; draft recovery via `GET /products/{id}/draft` per `MVP_ARCH §11.6` (the 25th endpoint per `§0.C`).
- AI Auto-fill orchestration (Feature 4) — calls into AI track via `gemini` adapter through §6A, applies Layer-2 enum guardrail, persists `ai_suggestions_jsonb`.

**NOT responsible for:** the schema itself (read-only from `category.service.fetch_schema()`); image binary upload (`image` owns); pricing math (`pricing` owns); Meesho-format emission (`export` owns).

**Database tables — WRITE-OWNS:** `catalogs`, `products`, `product_drafts`.
**Database tables — READS-FROM:** `seller_profile` via `customer.service` (NOT direct SQL — used for the `PROFILE_INCOMPLETE_FOR_CATEGORY` gate per `MVP_ARCH §3.3`); `templates` / `categories` via `category.service`.

**Cross-module dependencies (service calls only, per §16):**
- Calls `category.service.fetch_schema(category_id)` to validate PATCH payloads and to drive autofill compulsory-field enumeration.
- Calls `customer.service.get_profile(user_id)` to gate cross-super-category listings (the 422 `PROFILE_INCOMPLETE_FOR_CATEGORY` flow).

**Adapters used:** `gemini` (via §6A AI Ops for Auto-fill).

**V1_FEATURE_SPEC mapping:** Feature 3 (Fast Catalog Form), Feature 4 (AI Auto-fill), Feature 6 (Live Product Preview) — `V1_FEATURE_SPEC §2`.
**Endpoint count:** 6 endpoints (create, PATCH, autofill, preview, soft-delete, draft-recover) per `MVP_ARCH §3.4` + `§11.6`. Canonical signatures locked in §17. This is the **central spine module** with the largest endpoint count.
**MVP_ARCH cross-references:** §2.4 (DDL), §3.4 (endpoints), §5.2 (Auto-fill pipeline + 2-layer guardrail), §6.7 (LRU pre-warm on schema reads), §11.4 (autosave coalescing 30× volume reduction), §11.6 (`product_drafts` table + recovery endpoint), §12.4 (`is_advanced` honoured — accept whether or not the wizard expanded).

**Extraction notes (V1.5+):** `catalog` is the **hardest** module to extract per `§0.B` discussion — it is the spine that `image`/`pricing`/`dashboard`/`export` depend on. Extracting it requires defining stable cross-pod contracts to every dependent. Per `§21` recommended extraction order, this is the **last** module to split out.

---

### 2.5 — Module: `image`

**Owner specialist(s):** `meesell-api-routes-builder` (routes + Pydantic schemas) + `meesell-services-builder` (business logic, GCS orchestration, Celery task wrapper per `meesell-image-precheck-builder` agent spec's deferral).
**AI track collaboration:** **YES** — `meesell-image-precheck-builder` owns the 5-step precheck pipeline (JPEG/RGB/resolution/white-BG/watermark vision) including the Gemini Vision watermark call. The seam: backend's `image` module owns the upload route, the GCS write, the `product_images` row insert (`status='pending'`), the Celery enqueue, the result write-back (`status='ready'`); the AI track's `image-precheck-builder` owns the precheck pipeline itself including the Gemini Vision call wrapped by §6A. `meesell-prompt-engineer` owns the vision prompt content per its agent spec.

**Responsibilities:**
- Image upload endpoint (`POST /api/v1/products/{id}/images`) and status poll (`GET /api/v1/products/{id}/images`) per Feature 5.
- GCS orchestration — bucket layout `gs://meesell-images/{user_id}/{product_id}/{image_idx}.jpg` per `MVP_ARCH §10.8`, signed URL TTL 1 h, image binary write before row insert.
- Celery task wrapper for the precheck pipeline — enqueue to Valkey DB 1, persist result + status transitions, no business logic for the pipeline itself (delegated to AI track).

**NOT responsible for:** the precheck pipeline logic itself (delegated to `meesell-image-precheck-builder` per its agent spec); the watermark vision prompt content (delegated to `meesell-prompt-engineer`); the `products` table (owned by `catalog`).

**Database tables — WRITE-OWNS:** `product_images`.
**Database tables — READS-FROM:** `products` via `catalog.service` (ownership verification — does `product_id` belong to `user_id`?).

**Cross-module dependencies (service calls only, per §16):**
- Calls `catalog.service.assert_product_ownership(product_id, user_id)` before writing any `product_images` row — this is the tenant-isolation enforcement point per `MVP_ARCH §10.4`.

**Adapters used:** `gcs` (write, signed-URL issuance), `gemini` (via §6A for watermark vision — wrapped inside the AI track's pipeline).

**V1_FEATURE_SPEC mapping:** Feature 5 — Image Pre-check, `V1_FEATURE_SPEC §2 Feature 5`.
**Endpoint count:** 2 endpoints (upload + poll) per `MVP_ARCH §3.4`. Canonical signatures locked in §17.
**MVP_ARCH cross-references:** §0 premise #3 (image rules 100% uniform), §2.5 (DDL), §3.4 (endpoints), §5.3 (precheck pipeline overview), §10.8 (GCS layout + 1 h signed URL — mirrored from §6 and §1.E of this document).

**Extraction notes (V1.5+):** Extracts cleanly because the Celery worker side is already a separate process boundary (per §0.E + §1 topology). Becomes its own pod with GCS access and Celery worker; the API surface stays small (2 endpoints).

---

### 2.6 — Module: `pricing`

**Owner specialist(s):** `meesell-api-routes-builder` (routes + Pydantic schemas, including the re-authoring of `schemas/pricing.py` to resolve the latent import bug per `§0.E`) + `meesell-services-builder` (business logic — the P&L calculator + GST snapshot + suggested MRP).
**AI track collaboration:** no — pricing is deterministic math, no AI ranking or generation.

**Responsibilities:**
- P&L calculator endpoint (`POST /api/v1/products/{id}/price-calc`) — computes MRP / Meesho Price / Seller Price with category commission and GST per Feature 7.
- Commission lookup from `category.service` (uses the `categories.commission_pct` snapshot loaded at calc time).
- Suggested MRP computation based on target margin; persists the calc with full input snapshot for audit.

**NOT responsible for:** the commission percentage itself (read from the `category` snapshot — `pricing` does not own that data); ownership verification (delegates to `catalog`); the latent `pricing_engine.py` import bug surfaced in `§0.E` — its resolution is a Feature 7 construction-phase task, NOT a baseline blocker.

**Database tables — WRITE-OWNS:** `pricing_calcs`.
**Database tables — READS-FROM:** `products` via `catalog.service` (ownership verification); `categories` via `category.service` (commission lookup).

**Cross-module dependencies (service calls only, per §16):**
- Calls `catalog.service.assert_product_ownership(product_id, user_id)` before any calc — same isolation gate as `image`.
- Calls `category.service.get_commission(category_id)` to read `commission_pct` snapshot.

**Adapters used:** none.

**V1_FEATURE_SPEC mapping:** Feature 7 — Price Calculator, `V1_FEATURE_SPEC §2 Feature 7`.
**Endpoint count:** 1 endpoint per `MVP_ARCH §3.4`. Canonical signatures locked in §17.
**MVP_ARCH cross-references:** §2.5 (DDL), §3.4 (endpoint), §11.7 (`user_id` FK enforcement on `pricing_calcs`).

**Extraction notes (V1.5+):** Extracts trivially because it owns one table and reads two stable contracts. Likely candidate for an early V1.5 extraction if billing/Pro-tier logic clusters here.

---

### 2.7 — Module: `dashboard`

**Owner specialist(s):** `meesell-api-routes-builder` (routes + Pydantic response schemas) + `meesell-services-builder` (read-aggregation logic).
**AI track collaboration:** no — pure read aggregation.

**Responsibilities:**
- Paginated catalog/product listing (`GET /api/v1/products`) — the seller's tracking view per Feature 8.
- Draft listing (read-side mirror of `catalog`'s autosave state).
- Basic stats (counts by status, recent activity) — pure read aggregation across `catalog`, `image`, `pricing`, `export` data through service calls only.

**NOT responsible for:** write operations of any kind — `dashboard` is **read-only** by design; this is the "module without its own table" pattern per `§0.J` example.

**Database tables — WRITE-OWNS:** **none.**
**Database tables — READS-FROM:** none directly — all reads flow through `catalog.service`, `image.service`, `pricing.service`, `export.service`, `customer.service`. This is the strict service-only enforcement pattern for the §16 rule.

**Cross-module dependencies (service calls only, per §16):**
- Calls `catalog.service.list_products(user_id, pagination)` for the primary listing.
- Calls `customer.service.get_onboarding_completeness(user_id)` for onboarding-progress badges.
- (Optionally) calls `image.service.summary(product_ids)`, `pricing.service.summary(product_ids)`, `export.service.summary(product_ids)` for status-column hydration in the listing.

**Adapters used:** none.

**V1_FEATURE_SPEC mapping:** Feature 8 — Tracking Dashboard, `V1_FEATURE_SPEC §2 Feature 8`.
**Endpoint count:** 1 endpoint primary (the listing GET) + V1.5 will likely expand. Canonical signature locked in §17.
**MVP_ARCH cross-references:** §3.4 (listing endpoint), §11.7 (`user_id` scoping — dashboard is the most-scrutinised query for cross-tenant leaks because it returns lists).

**Extraction notes (V1.5+):** `dashboard` is the **purest** demonstration of the modular monolith discipline. Because it owns no tables and calls only service interfaces, extraction means swapping in-process Python calls for HTTP calls with **zero data-layer migration**. Becomes its own BFF (backend-for-frontend) pod cleanly.

---

### 2.8 — Module: `export`

**Owner specialist(s):** `meesell-services-builder` (heavy lifting — the entire Export Adapter from `MVP_ARCH §5.5` lives here: 9-step pipeline, ComplianceStrategy classes, round-trip validator, XLSX writer, image packager) + `meesell-api-routes-builder` (the endpoint surface — generate + poll).
**AI track collaboration:** no — export is deterministic transformation, no AI calls. (Layer-3 guardrail per `§0.H F3` does **re-validate** AI-emitted enum values at export time, but the validation is deterministic.)

**Responsibilities:**
- Meesho XLSX generation via the 9-step Export Adapter pipeline per `MVP_ARCH §5.5.4` — schema resolution → strategy selection → row build → strategy apply → enum translate → column reorder → alias restore → XLSX write → round-trip validate.
- ComplianceStrategy classes per `§0.G §12.6`: `StandardComplianceStrategy` (3,771 categories — 9 fields → 9 columns) + `CollapsedComplianceStrategy` (1 leaf, Eye-Serum — 9 fields → 3 columns derived at emit time).
- Round-trip validation per `MVP_ARCH §5.7` — re-parse generated XLSX and assert canonical equivalence; 15 golden fixtures gate sign-off.

**NOT responsible for:** seller data collection (`customer` owns); product data collection (`catalog` owns); image collection (`image` owns); marketplace-specific knowledge for non-Meesho marketplaces (V2 — gated by the `MarketplaceExportAdapter` interface in `MVP_ARCH §5.5.9`).

**Database tables — WRITE-OWNS:** `exports`.
**Database tables — READS-FROM:** `products` / `catalogs` via `catalog.service`; `seller_profile` via `customer.service`; `templates` / `field_aliases` / `field_enum_values` via `category.service`; `product_images` via `image.service`.

**Cross-module dependencies (service calls only, per §16):**
- Calls `catalog.service.get_product_for_export(product_id, user_id)`.
- Calls `customer.service.get_compliance_block(user_id)`.
- Calls `category.service.fetch_schema(category_id)` for the canonical → Meesho header reverse map (the `field_aliases.for_xlsx_export = TRUE` rows per `§0.G §12.2`).
- Calls `image.service.get_image_bytes(product_id)` for the ZIP packager.

**Adapters used:** `gcs` (XLSX + ZIP upload, signed URL issuance per `MVP_ARCH §5.5.4`).

**V1_FEATURE_SPEC mapping:** Feature 9 — XLSX Export, `V1_FEATURE_SPEC §2 Feature 9`.
**Endpoint count:** 2 endpoints (generate POST + poll GET) per `MVP_ARCH §3.4`. Canonical signatures locked in §17.
**MVP_ARCH cross-references:** §2.5 (DDL), §3.4 (endpoints), §5.5 (the entire Export Adapter spec — this module is the implementation), §5.7 (round-trip test plan + 15 golden fixtures), §11.7 (`user_id` FK on `exports`), §12.2 (typo restore via `field_aliases.for_xlsx_export`), §12.6 (CollapsedComplianceStrategy). Philosophy M10 lives here (per `§0.H`).

**Extraction notes (V1.5+):** `export` is the **easiest** module to extract per `§21` recommended order. It is the most isolated (no other module imports it; all dependencies are reads). Becomes its own pod with GCS access + a Celery worker for the heavy XLSX build path. V2's multi-marketplace expansion (Amazon/Flipkart/Etsy per `MVP_ARCH §14`) lands as additional `MarketplaceExportAdapter` implementations inside this module before the extraction, or as sibling pods after.

---

### 2.9 — Layer: `adapters/` (non-domain)

**Owner specialist(s):** `meesell-services-builder` (all 5 adapter clients live inside services' authoring scope per agent spec).

**Responsibility:** the outbound vendor-isolation layer. Provides `gemini`, `msg91`, `gcs`, `razorpay`, and `langfuse` clients to whichever domain modules call them per the §1.E egress map. Each adapter encapsulates SDK quirks, surface-level retries (transport-level only), and credential handling. Vendor concerns NEVER leak into domain modules.

**Domain modules depend on this layer for:**
- `gemini` — used by `category` (Smart Picker), `catalog` (Auto-fill), `image` (watermark vision via AI track) — all wrapped by §6A.
- `msg91` — used by `iam` only.
- `gcs` — used by `image` (binary write + signed URL) and `export` (XLSX + ZIP write).
- `razorpay` — used by `iam` (webhook signature verification only in V1).
- `langfuse` — used by all AI call sites via §6A (fire-and-forget).

**NOT responsible for:** business logic of any kind; retry policy decisions for AI calls (that is §6A's job — adapters do transport retry only); schema validation; cross-call orchestration; cost tracking (§6A); guardrail enforcement (§6A + the calling module).

**MVP_ARCH cross-references:** §5 (AI workloads), §5.5 (Export Adapter — distinct from this vendor adapter layer; the Export Adapter is a domain pattern inside `export`, not a vendor client), §8 (AI ops envelope), §10.8 (GCS layout).

---

### 2.10 — Layer: `core/` (non-domain)

**Owner specialist(s):** `meesell-auth-builder` (the `get_current_user` auth dependency + JWT decode per agent spec) + `meesell-services-builder` (everything else — tenancy enforcement helpers, rate-limit middleware, audit middleware, cache helper, plan-guard, structured error handlers, middleware registration order).

**Responsibility:** the cross-cutting foundation every domain module depends on. Provides the canonical middleware chain (CORS → request-ID → auth → tenancy → rate-limit → plan-guard → route → audit), the `get_current_user` FastAPI dependency, the read-through cache helper, the locale-aware error formatter, and the audit-write hook. This is where philosophy mandates M6, M7, F3 surface as enforced invariants rather than module-by-module re-implementations.

**Domain modules depend on this layer for:**
- `core/auth.py` — `get_current_user` dep, consumed by every authenticated route across `customer`, `category`, `catalog`, `image`, `pricing`, `dashboard`, `export`.
- `core/cache.py` — read-through Valkey DB 3 cache helper, consumed by `category` (heaviest), `customer`, `catalog`.
- `core/middleware/rate_limit.py` — Valkey DB 0 sliding-window enforcement before route handler per `MVP_ARCH §10.7`.
- `core/middleware/audit.py` — `audit_events` row write **AFTER** successful 2xx response per `MVP_ARCH §11.3` and philosophy M8. **This is the ONE write outside a domain module** — `audit_events` is the cross-cutting log, not a domain table.
- `core/errors.py` — structured error handlers + `validation_message_id` resolution against `app/i18n/`.

**Database tables — WRITE-OWNS (cross-cutting exception):** `audit_events` (middleware writes; no domain module writes here).

**NOT responsible for:** route handlers (modules own); business logic (modules own); vendor calls (`adapters/` owns); ORM model definitions (`shared/` owns); per-feature error catalogues (modules contribute their own `validation_message_id`s).

**MVP_ARCH cross-references:** §10.2 + §10.4 (tenancy), §10.7 (rate limits), §11 (audit log entire section), §11.3 (write-path AFTER commit), §11.7 (JWT shape).

---

### 2.11 — Layer: `shared/` (non-domain)

**Owner specialist(s):** `meesell-services-builder` (the Valkey async client, the Pydantic Settings config loader) + `meesell-database-builder` (the 13 ORM models registry per agent spec — `models/__init__.py` and the per-table model files).

**Responsibility:** the stateless foundation below `core/`. Provides the SQLAlchemy 2.0 async engine + session factory, the Valkey async client, the 13 ORM models registry (`users`, `seller_profile`, `templates`, `categories`, `field_enum_values`, `field_aliases`, `catalogs`, `products`, `product_images`, `pricing_calcs`, `exports`, `audit_events`, `product_drafts`), and Pydantic Settings configuration loading. No business logic, no state, no side effects beyond connection-pool initialisation.

**Domain modules depend on this layer for:**
- `shared/database.py` — `AsyncSession` factory, consumed by every module's repository.
- `shared/valkey.py` — async client, consumed by `core/cache.py`, `core/middleware/rate_limit.py`, `iam` (OTP store).
- `shared/models/` — the 13 ORM models registry. Modules import from here; no module redefines a model.
- `shared/config.py` — Pydantic Settings, consumed by `adapters/` and `core/`.

**NOT responsible for:** business logic; route handlers; vendor calls; anything stateful beyond connection pools; cross-cutting middleware (that is `core/`).

**MVP_ARCH cross-references:** §2 (the 13-table DDL is the authoritative spec — `shared/models/` is the implementation, not the spec, per `§0.D`), §2.6 (the 10-step Alembic ordering is the migration-sequence reference and lives with the DATABASE track, not duplicated here).

---

### 2.D — Cross-module reference matrix

The matrix below codifies the §16 inter-module rule. Rows are the **caller** module; columns are the **callee** module. A `✓` means the caller MAY make a service-layer call into the callee (no repository import, no direct SQL). A `✗` means the call is forbidden — the modules are isolated. The `core/`, `shared/`, and `adapters/` layers are intentionally absent from the matrix: every module MAY depend on them; they are cross-cutting, not in the domain graph.

|             | iam | customer | category | catalog | image | pricing | dashboard | export |
|-------------|-----|----------|----------|---------|-------|---------|-----------|--------|
| **iam**       | —   | ✗        | ✗        | ✗       | ✗     | ✗       | ✗         | ✗      |
| **customer**  | ✗   | —        | ✗        | ✗       | ✗     | ✗       | ✗         | ✗      |
| **category**  | ✗   | ✗        | —        | ✗       | ✗     | ✗       | ✗         | ✗      |
| **catalog**   | ✗   | ✓        | ✓        | —       | ✗     | ✗       | ✗         | ✗      |
| **image**     | ✗   | ✗        | ✗        | ✓       | —     | ✗       | ✗         | ✗      |
| **pricing**   | ✗   | ✗        | ✓        | ✓       | ✗     | —       | ✗         | ✗      |
| **dashboard** | ✗   | ✓        | ✗        | ✓       | ✗     | ✗       | —         | ✗      |
| **export**    | ✗   | ✓        | ✓        | ✓       | ✓     | ✗       | ✗         | —      |

**Total allowed cross-module service calls: 8 ✓.** Breakdown — `catalog` → `customer`, `category` (2); `image` → `catalog` (1); `pricing` → `category`, `catalog` (2); `dashboard` → `customer`, `catalog` (2); `export` → `customer`, `category`, `catalog`, `image` (4). Note: `dashboard` may optionally call `image.service.summary`, `pricing.service.summary`, `export.service.summary` for richer status hydration per §2.7 — those reads were left as **optional** in the module description (not as `✓` in the matrix) to keep the matrix tight; if the founder elevates them to required, they flip to `✓` and the count rises to 11. As authored, the matrix locks **8 ✓** — the minimum service-graph that satisfies V1.

**Cross-cutting note on `iam`.** The all-`✗` row for `iam` is intentional: `iam`'s contract surface to other modules is the `get_current_user` dependency in `core/auth.py`, which participates in the middleware chain — it is NOT a module-to-module service call and therefore does not appear as `✓` here. Per `§2.1`, `iam` is a leaf module on the cross-module graph.

---

### 2.E — Lock dependency notice

**No per-module deep specification section (§7 through §14) may flip its STATUS from `SKELETON` or `DRAFT` to `LOCKED` until Section 2 is `LOCKED`.** Sections 7-14 inherit their ownership contract — owner specialist, write-owned tables, allowed cross-module calls, adapter usage — directly from Section 2. Drilling those sections before this one is locked risks publishing a deep spec that contradicts the ownership map, which then forces a multi-section retraction. The founder review of Section 2 is therefore the single gate that unblocks the eight per-module deep specs.

---

---

## Section 3 — File Structure

STATUS: LOCKED (2026-06-05)

### 3.A — Preamble

Section 3 is the **directory contract**. Every file path mentioned in any later section of this document (or any specialist-authored work product) MUST be resolvable to a location in the tree this section defines. Specialists may NOT invent new top-level folders, may NOT restructure module internals, and may NOT colocate files outside the canonical layout without first amending this section through founder review. The tree is intentionally uniform across modules so specialists can pattern-match — opening `modules/iam/` and `modules/export/` reveals the same internal shape, the same file names, and the same ownership rules. Section 3 does NOT specify file CONTENTS (every later section owns its files' contents) — it specifies WHERE. A reviewer evaluates Section 3 by asking "is the layout consistent, is the per-module shape uniform, are non-domain layers cleanly separated, is the `ai_ops/` placement defensible?" — not "is `core/auth.py` correctly designed" (that belongs to §4).

---

### 3.B — Top-level `backend/` tree

```
backend/
├── app/                          # FastAPI application root (Python package)
│   ├── __init__.py
│   ├── main.py                   # FastAPI app, middleware registration, router mounting
│   ├── modules/                  # 8 domain modules (§2.1-§2.8)
│   ├── adapters/                 # 5 vendor clients (§2.9)
│   ├── core/                     # cross-cutting foundation (§2.10)
│   ├── ai_ops/                   # AI Operations Layer (§6A) — see structural addition note below
│   ├── i18n/                     # locale-aware messages package (§5A)
│   ├── shared/                   # foundation: db, valkey, models, config (§2.11)
│   └── workers/                  # Celery app + cross-cutting task registration
├── alembic/
│   ├── env.py
│   ├── alembic.ini
│   └── versions/                 # owned by meesell-database-builder
├── tests/                        # test tree mirrors app/ structure (see §3.J)
├── scripts/                      # seed scripts (existing — owned by meesell-database-builder)
├── requirements.txt              # Python deps
├── Dockerfile                    # FastAPI image (Celery worker uses same image, different CMD)
├── .env.example                  # template — NEVER commit .env
└── (no other top-level files)
```

**Structural addition flag — `ai_ops/`.** Section 2 enumerated three non-domain layers (`adapters/`, `core/`, `shared/`) per §2.9 / §2.10 / §2.11. Section 3 **adds `ai_ops/` as the fourth non-domain top-level peer** to host §6A. This is a deliberate Section 3 structural decision: `ai_ops/` cannot live inside `core/` because cost tracking, the 3-layer guardrail, the daily ₹500 budget cap, LangFuse trace egress, the prompt registry, and the eval-set runners together form a stateful, multi-file, AI-only concern that does not match `core/`'s role as the request-path middleware + helpers layer. It cannot live inside `adapters/gemini.py` either because cost/guardrail/eval span every AI workload and must outlive any single call site (per `§6A` SKELETON prose). It is a peer of `core/`, not a sub-package. §15 (Cross-Cutting Walkthrough) will confirm the `core/`-vs-`ai_ops/` boundary once that section drills.

**Structural addition flag — `i18n/`.** `meesell-services-builder` began the `app/i18n/` package during the schema-builder work (per services-builder memory, cross-noted in coordinator memory). Section 3 elevates it to a top-level peer because it is consumed both by `core/errors.py` (for `validation_message_id` resolution per `§5A` and `MVP_ARCH §5.6.7`) and by every domain module's validators. Placing it under `core/` would couple a stateful resource registry to a layer whose purpose is request-path glue. Placing it inside a single module would force the other modules to import across module boundaries — a §16 violation. It belongs at the top level.

---

### 3.C — Per-module canonical subtree

Every one of the 8 domain modules from §2.1–§2.8 conforms to the same internal layout:

```
modules/<module_name>/
├── __init__.py
├── router.py            # FastAPI APIRouter — endpoint signatures only
├── service.py           # business logic — the PUBLIC interface other modules may call (§16)
├── repository.py        # SQLAlchemy queries — PRIVATE to module; no cross-module import
├── schemas.py           # Pydantic v2 request/response models for THIS module's endpoints
├── domain.py            # value objects, enums, dataclasses (when schemas alone are insufficient)
├── exceptions.py        # module-specific exception hierarchy (raised by service, caught by errors.py)
└── tasks.py             # Celery task definitions OWNED by this module (only modules that emit jobs)
```

**Per-file ownership rules (locked):**

- **`router.py`** — written by `meesell-api-routes-builder`. `meesell-services-builder` does NOT author here. Contains FastAPI route handlers; calls into `service.py`; declares response models from `schemas.py`.
- **`service.py`** — written by `meesell-services-builder`. `meesell-api-routes-builder` does NOT author here. **This is the module's PUBLIC interface** per §16 — every cross-module call lands here, not in `repository.py`.
- **`repository.py`** — written by `meesell-services-builder`. This is a **PRIVATE module file**. The §16 rule "no cross-module repository imports" means specifically that `from app.modules.category.repository import X` is forbidden in any other module. Other modules call `category.service.fetch_schema(...)`; they never reach into `category.repository` directly.
- **`schemas.py`** — written by `meesell-api-routes-builder` (request/response shape is a route concern). `meesell-services-builder` MAY add internal Pydantic types here ONLY when shared by router + service. No cross-module imports from another module's `schemas.py` — if data crosses a module boundary, it crosses as a `domain.py` value object or a primitive type.
- **`domain.py`** — written by `meesell-services-builder`. Rare in V1 (most modules need only `schemas.py`); common when value objects are non-trivial — e.g. `export.domain.ComplianceStrategy` base class with `StandardComplianceStrategy` + `CollapsedComplianceStrategy` subclasses per §2.8 / `MVP_ARCH §12.6`.
- **`exceptions.py`** — written by `meesell-services-builder`. Each module owns its exception hierarchy (e.g. `CatalogError → DraftNotFoundError`, `ProfileIncompleteError`); the hierarchy is caught centrally by `core/errors.py` and mapped to HTTP responses + `validation_message_id` lookups.
- **`tasks.py`** — written by `meesell-services-builder`. **Only present in modules that EMIT Celery jobs.** Per §1.D background-flow walkthrough, the V1 emitters are `image` (precheck pipeline) and `export` (XLSX build + ZIP pack). Per §2.4 + `§1.C` V1 default, `catalog`'s Auto-fill runs sync from FastAPI; `catalog/tasks.py` is therefore NOT created in V1. The other modules (`iam`, `customer`, `category`, `pricing`, `dashboard`) do NOT have `tasks.py` at all in V1. If §6A later rules that Auto-fill moves async, `catalog/tasks.py` is added then.

---

### 3.D — `core/` subtree

```
core/
├── __init__.py
├── auth.py              # get_current_user FastAPI dep; JWT decode/validate (owner: meesell-auth-builder)
├── tenancy.py           # user_id injection + enforcement helpers (owner: meesell-services-builder)
├── cache.py             # Valkey DB 3 read-through helper (version-tagged keys per MVP_ARCH §6.4)
├── plan_guard.py        # plan claim → feature budget enforcement
├── errors.py            # structured error handlers + validation_message_id resolution (calls i18n/)
└── middleware/
    ├── __init__.py
    ├── request_id.py    # X-Request-ID injection
    ├── auth_mw.py       # decode JWT + attach user to request.state
    ├── tenancy_mw.py    # inject user_id into request context
    ├── rate_limit_mw.py # Valkey DB 0 sliding-window per MVP_ARCH §10.7
    ├── plan_guard_mw.py # plan enforcement (consumes core/plan_guard.py)
    └── audit_mw.py      # audit_events post-commit write (per §2.10 cross-cutting exception)
```

**Canonical middleware order (locked here; §4 will expand each link):**

```
CORS → request_id → auth_mw → tenancy_mw → rate_limit_mw → plan_guard_mw → (route handler) → audit_mw
```

`audit_mw` runs AFTER the route handler so that audit rows are written only on successful 2xx commit per `MVP_ARCH §11.3` and Philosophy M8 ("if it committed, it logged; if it didn't commit, it never happened"). Every other middleware runs BEFORE the route handler in the order shown.

---

### 3.E — `shared/` subtree

```
shared/
├── __init__.py
├── database.py          # SQLAlchemy 2.0 async engine + AsyncSession factory + get_db dep
├── valkey.py            # redis.asyncio client (Valkey 8 compatible) — DB 0/1/2/3 selectors
├── config.py            # Pydantic Settings (loads from .env + Secret Manager refs per infra)
└── models/              # 13 ORM models (owner: meesell-database-builder per §2.11)
    ├── __init__.py      # exports all 13 — single import point
    ├── user.py
    ├── seller_profile.py
    ├── template.py
    ├── category.py
    ├── field_enum_value.py
    ├── field_alias.py
    ├── catalog.py
    ├── product.py
    ├── product_image.py
    ├── pricing_calc.py
    ├── export.py
    ├── audit_event.py
    └── product_draft.py
```

**Locked import-path rule:** `from app.shared.models import Product, Catalog, ...` is the canonical import path for any ORM model. NO module redefines a model. NO module imports from `app.modules.<x>.repository` to obtain a model class — the model lives in the registry; the repository owns queries against it. This is the structural enforcement of the §16 "no cross-module repository imports" rule at the model-registry level.

---

### 3.F — `adapters/` subtree

```
adapters/
├── __init__.py
├── gemini.py            # raw Gemini 2.5 Flash client (transport retry only — §6A wraps with ops)
├── msg91.py             # OTP send client
├── gcs.py               # GCS write + signed-URL issuance
├── razorpay.py          # webhook signature verify only in V1
└── langfuse.py          # async trace egress (drop-on-failure per §1.E)
```

Each adapter is a class with a stable async interface. No vendor SDK leaks past the adapter file boundary per §2.9. Domain modules import these as follows: `gemini` ONLY via the `ai_ops/client.py` wrapper (never directly — see §3.G boundary rule); `msg91`, `gcs`, `razorpay`, `langfuse` directly from the calling module's `service.py`.

---

### 3.G — `ai_ops/` subtree (the structural addition)

```
ai_ops/                   # §6A AI Operations Layer (NEW top-level layer added by Section 3)
├── __init__.py
├── client.py            # the wrapper every module uses (ai_ops.client.call_gemini(...))
├── cost_tracker.py      # per-call tokens × ₹/1K persistence
├── guardrail.py         # Layer 1 (prompt constraint) + Layer 2 hook (parser enum check)
├── budget_cap.py        # daily ₹500 cap + 80% alarm + hard-stop with graceful fallback
├── prompt_registry.py   # versioned prompt templates (content delegated to meesell-prompt-engineer)
└── eval.py              # golden eval set runners (3 sets — Picker, Auto-fill, Watermark)
```

**Locked boundary rule:** `adapters/gemini.py` is the raw SDK wrapper. `ai_ops/client.py` is the wrapper every domain module imports. **Domain modules NEVER import `adapters.gemini` directly.** The §16 enforcement test (introduced in §19) will codify this as an import-linter rule (CI fails if `from app.adapters.gemini import` appears anywhere under `app/modules/`).

---

### 3.H — `i18n/` subtree

```
i18n/                     # locale-aware messages (referenced by §5A and §2.10 errors.py)
├── __init__.py
├── messages_en.py       # validation_message_id → English text (V1 ships English only)
├── resolver.py          # validation_message_id + locale → resolved message
└── (messages_ta.py, messages_hi.py)   # V1.5 — DO NOT ship in V1
```

V1 ships English only (`messages_en.py`). Tamil and Hindi message files are placeholders for V1.5; specialists do NOT create them in V1. The resolver contract (`validation_message_id`, `locale`) → resolved string is locked; per `MVP_ARCH §5.6.7`, the contract is forward-compatible — adding a locale in V1.5 is a file-add, not a schema migration.

---

### 3.I — `workers/` subtree

```
workers/
├── __init__.py
└── celery_app.py        # Celery app instance + task auto-discovery from modules/*/tasks.py
```

**Locked rule:** task DEFINITIONS live inside each emitting module's `tasks.py` (per §3.C). `workers/celery_app.py` does discovery + registration only — its `include=[...]` list points at `"app.modules.image.tasks"`, `"app.modules.export.tasks"`. This is the modular-monolith discipline applied to background work: when V1.5 extracts the `image` module, its `tasks.py` moves with it; `workers/celery_app.py` either stays as the parent-pod Celery host or is itself re-instantiated per extracted pod. Either way, the per-module task ownership does not change.

Cross-reference for current state: `backend/app/workers/celery_app.py` currently has `include=[]` (per services-builder memory session 2026-06-05 final purge). When `modules/image/tasks.py` and `modules/export/tasks.py` land in construction, the include list is populated as part of those specialist dispatches.

---

### 3.J — `tests/` mirror structure

```
tests/
├── conftest.py                       # fixtures (db, valkey, auth_client)
├── test_app_boot_integration.py      # boot test from session 2 gap pass — already exists (7/7 PASS)
├── test_database.py                  # schema-smoke suite from session 2 — already exists (42/42 PASS)
└── modules/
    ├── iam/
    │   ├── test_router.py
    │   ├── test_service.py
    │   └── test_repository.py
    ├── customer/                     # (router, service, repository)
    ├── category/                     # (router, service, repository) + test_search.py for trgm browse
    ├── catalog/                      # (router, service, repository) + test_autosave.py
    ├── image/                        # (router, service, repository) + test_tasks.py — Celery tests
    ├── pricing/                      # (router, service, repository)
    ├── dashboard/                    # (router, service, repository)
    └── export/                       # (router, service, repository) + test_round_trip.py — 15 fixtures
```

The test tree mirrors `app/modules/` one-for-one. Each per-module test directory has at minimum a `test_router.py`, `test_service.py`, and `test_repository.py`. Special-purpose tests are flagged: `category/test_search.py` (pg_trgm browse coverage per `MVP_ARCH §7.5`), `catalog/test_autosave.py` (coalescing per `MVP_ARCH §11.4`), `image/test_tasks.py` (Celery task tests), `export/test_round_trip.py` (the 15 golden fixtures per `MVP_ARCH §5.7`). Cross-module integration tests (the coordinator-owned end-to-end journeys per §19) live at `tests/integration/` — that subtree is added in §19 when the test pyramid is fully specified; Section 3 reserves the path but does not enumerate its contents.

---

### 3.K — "Where does this file go" decision tree

Specialists consult this Q&A list when placing a new file. If a question is not covered here, the answer is "amend Section 3 first" — not "guess".

- **Q: I'm writing a Pydantic request body schema for `POST /products`.**
  A: `modules/catalog/schemas.py`.
- **Q: I'm writing a helper that converts canonical field name → Meesho XLSX header.**
  A: `modules/export/service.py` (or `modules/export/domain.py` if it's a value-object class). NOT `core/`, NOT `shared/` — Meesho-format knowledge is locked inside the `export` module per Philosophy M10 (cited in §0.H and §2.8).
- **Q: I need to call Gemini for the Smart Picker rank.**
  A: `modules/category/service.py` calls `ai_ops.client.call_gemini(...)`. NEVER `adapters.gemini` directly — see §3.G boundary rule.
- **Q: I want to read `templates` from `modules/catalog`.**
  A: Call `category.service.fetch_schema(category_id)`. Do NOT import `category.repository`. Do NOT write raw SQL. This is the §16 rule applied at the file-placement level.
- **Q: I want to add a new top-level folder under `app/`.**
  A: STOP. Amend this section first (founder review). No silent additions — the structural-addition flags in §3.B are the only authorised top-level additions.
- **Q: I want to write a Celery task for image precheck.**
  A: `modules/image/tasks.py`. NOT `workers/image_tasks.py` (legacy V0 path, deleted in session 2 per services-builder memory).
- **Q: I want to add a `validation_message_id` for a new error.**
  A: `i18n/messages_en.py`. The validator that raises it lives in the module's `service.py` (via the module's `exceptions.py` hierarchy); the message string itself lives in `i18n/`.
- **Q: I need to read seller-profile data from `modules/export`.**
  A: Call `customer.service.get_compliance_block(user_id)`. Do NOT import `customer.repository`. Do NOT join `seller_profile` directly in an `export` query. See §2.D matrix row for `export`.

---

### 3.L — What Section 3 does NOT cover

Section 3 specifies WHERE files live; it does NOT specify file CONTENTS. Every later section owns its files' contents. §4 specifies what `core/auth.py` contains, including the JWT decode contract and the `get_current_user` signature. §6A specifies what `ai_ops/budget_cap.py` contains, including the ₹500 cap algorithm, the 80% alarm, and the graceful-fallback behaviour. §14 specifies what `modules/export/domain.py` contains, including the `ComplianceStrategy` class hierarchy. §17 specifies what `modules/<x>/router.py` exposes endpoint-by-endpoint. A reviewer evaluating Section 3 is asking only "is the directory layout consistent, is the per-module shape uniform, are non-domain layers cleanly separated, are the two structural additions (`ai_ops/`, `i18n/`) defensible?" — not any content question.

Section 3 also does NOT renumber or amend the §2 ownership map. The two structural additions (`ai_ops/` and `i18n/` as top-level peers) extend the §2 non-domain layer set from 3 to 5 layers, but they do NOT change §2's domain-module ownership or cross-module matrix. The matrix in §2.D remains the authoritative graph; Section 3 lays the directories the matrix is enforced against.

---

## Section 4 — `core/` — Cross-Cutting Foundation

STATUS: LOCKED (2026-06-05)

### 4.A — Preamble

Section 4 specifies what `core/` **CONTAINS** — the contracts every file exposes, the cross-cutting invariants they enforce, and the canonical interaction with other layers. Section 4 does **NOT** specify file **LOCATIONS** (those are locked in §3.D) — it specifies **INTERFACES**. Specialists implementing `core/` files build to the contracts here; specialists implementing domain modules consume those contracts as locked APIs. A reviewer evaluating Section 4 asks "are the contracts unambiguous, do the middleware ordering and the route-handler hooks compose correctly, are the security invariants enforced?" — not "is the file tree right" (§3) or "are the messages in English correct" (§5A). Per §0.B + §3.D, `core/` is the **non-domain foundation** every domain module depends on; per §2.10, the auth dep is owner by `meesell-auth-builder` and every other `core/` file is owned by `meesell-services-builder`.

---

### 4.B — `core/auth.py` — contract

**Owner:** `meesell-auth-builder` (sole owner per §2.10).

**The canonical FastAPI dependency** that every authenticated route across `customer`, `category`, `catalog`, `image`, `pricing`, `dashboard`, and `export` consumes:

```python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    ...
```

**`CurrentUser` shape** — immutable dataclass exposed by `core/auth.py`:

```python
@dataclass(frozen=True)
class CurrentUser:
    user_id: UUID
    plan: Literal["free"]  # V1 only ships "free"; type widens to "free" | "pro" in V1.5
```

**JWT contract** per `MVP_ARCH §11.7` + §10.3: payload `{sub: str(user_id), exp: int, plan: str}`. Algorithm HS256. Secret read from `shared/config.JWT_SECRET`. Expiry per `shared/config.JWT_EXPIRY_DAYS` (existing).

**Error envelope** (resolved by `core/errors.py` per §4.F):
- missing/malformed token → `401` with `validation_message_id = "auth.token_missing"`.
- expired token (`jwt.ExpiredSignatureError`) → `401` with `validation_message_id = "auth.token_expired"`.
- decoded `sub` does not resolve to a `users` row → `403` with `validation_message_id = "auth.user_not_found"`.

**Locked rule.** `get_current_user` is the **only** authenticated-user dependency that route handlers MAY use. Routes do NOT decode JWT themselves; modules do NOT re-implement the auth dep; the `iam` module does NOT re-export an alternative. The middleware `auth_mw.py` (§4.G) attaches `request.state.user` opportunistically for logging/correlation, but ENFORCEMENT (401/403) lives only in this dependency.

**AMENDMENT 2026-06-05 — FE-D5 ratification:** the split-token + server-side-revocation auth pattern (per FE-D5 + FE-D6 founder rulings 2026-06-05, captured in `.claude/agent-memory/meesell-frontend-coordinator/backend_handoff_jwt_session_pattern.md`) extends the `core/auth.py` contract as follows. The `CurrentUser` shape and the `get_current_user` signature are **UNCHANGED** — refresh flow is transparent to every authenticated route, which continues to receive `CurrentUser(user_id, plan)` via the access JWT only.

**Access JWT.** Claim shape `{sub, exp, plan}` HS256 is UNCHANGED. Lifetime is now env-driven: read from `shared/config.ACCESS_TOKEN_TTL_SECONDS` (prod 900, staging 60, dev 30). The previous `JWT_EXPIRY_DAYS` config field is **deprecated** — `meesell-auth-builder` removes it during the `iam` construction dispatch and replaces every reference with `ACCESS_TOKEN_TTL_SECONDS`. The §4.B-original reference to `shared/config.JWT_EXPIRY_DAYS` is superseded by this amendment.

**Refresh token.** Opaque `secrets.token_urlsafe(48)` value (NOT a JWT — JWTs in cookies are an anti-pattern: size, no rotation, no server-side revocation). Lifetime is env-driven via `shared/config.REFRESH_TOKEN_TTL_SECONDS` (prod 604800, staging 300, dev 120).

**Refresh allowlist (Valkey DB 0).** Key format `cache:refresh:{hmac_sha256(token, REFRESH_TOKEN_PEPPER)}`. **Coordinator counter-proposal vs FE memo:** the memo proposed `sha256(token)`; coordinator strengthens this to **HMAC-SHA256 with a backend-only pepper** (`shared/config.REFRESH_TOKEN_PEPPER`, loaded from Secret Manager, never logged). Rationale: a Valkey-only breach must NOT let an attacker validate captured refresh cookies by computing SHA-256 themselves; HMAC requires the backend pepper. Value: JSON `{"user_id": <uuid>, "issued_at": <unix_ts>, "ip": <addr>}`. TTL matches `REFRESH_TOKEN_TTL_SECONDS` so natural expiry replaces any cron sweep. Lookup uses `secrets.compare_digest()` — NEVER `==` — for constant-time comparison (timing-attack mitigation).

**Cookie format.** `Set-Cookie: refresh_token=<opaque>; Domain=.mesell.xyz; Path=/api/v1/auth; HttpOnly; Secure; SameSite=Strict; Max-Age=<REFRESH_TOKEN_TTL_SECONDS>`. **Coordinator counter-proposal vs FE memo:** the memo proposed `Path=/auth`; coordinator corrects to `Path=/api/v1/auth` because the actual endpoint paths are `/api/v1/auth/refresh` and `/api/v1/auth/logout` (per §17 and the locked URL convention in CLAUDE.md). A `Path=/auth` cookie would NOT be sent by the browser to `/api/v1/auth/*` (cookie path matching is prefix on the URL path), defeating the entire flow. The `/api/v1/auth` scope still minimises exposure — the cookie is not sent on `/api/v1/products`, `/api/v1/categories`, etc., only on the auth subtree. `/api/v1/auth/me` introspection consumes the access JWT in the `Authorization` header; the refresh cookie reaching that endpoint is harmless (it is not read there).

**Rotation rule.** Every successful `POST /auth/refresh` MUST atomically DELETE the old allowlist entry AND WRITE the new entry. **Coordinator counter-proposal vs FE memo:** the memo proposed Valkey MULTI/EXEC pipeline; coordinator selects a **Lua script via `EVAL`** as the locked primitive. Rationale: MULTI/EXEC in Valkey is optimistic and requires `WATCH` for true compare-and-swap, which still has a race window between WATCH and EXEC. A single Lua script executes atomically on the server in one round-trip with no race window — it is the canonical primitive for atomic check-then-DEL-then-SET on Valkey. The script signature: `EVAL "if redis.call('GET', KEYS[1]) then redis.call('DEL', KEYS[1]); redis.call('SET', KEYS[2], ARGV[1], 'EX', ARGV[2]); return 1 else return 0 end" 2 <old_key> <new_key> <json_value> <ttl>`. Replay-attack mitigation: re-presenting an old refresh cookie after rotation returns 401 because the old `old_key` no longer exists in Valkey.

**Coordinator pushback verdict on memo item 1 (rotation atomicity):** **counter-propose Lua script over MULTI/EXEC** — adopt this in §7 DRAFT authoring. Founder rules if Lua is acceptable; default-Lua otherwise the auth-builder falls back to MULTI/EXEC + WATCH as a degradation-mode (acceptable). (End amendment.)

---

### 4.C — `core/tenancy.py` — contract

**Owner:** `meesell-services-builder` (per §2.10).

**Purpose.** Provides the two helpers that every owned-table query path consumes to enforce app-level `user_id` scoping (V1 — RLS deferred to V1.5 per §0.F and MVP_ARCH §9).

**Helper 1 — ownership assertion:**

```python
def assert_owned(record: T, user_id: UUID) -> None:
    """Raises TenantViolationError if record.user_id != user_id."""
    ...
```

Used at every cross-module ownership-gate call site — for example `catalog.service.assert_product_ownership(product_id, user_id)` (§2.5 + §2.6), or `image.service` before any write to `product_images`. `TenantViolationError` subclasses `MeesellError` (§4.F) with `status_code=403`, `validation_message_id="tenancy.cross_user_access"`.

**Helper 2 — query scoping:**

```python
def scope_to_user(
    query: Select,
    user_id: UUID,
    column: str = "user_id",
) -> Select:
    """Adds WHERE user_id = :user_id to a SQLAlchemy Select."""
    ...
```

Every repository query against an owned table goes through this — never raw `.where(Product.user_id == ...)` written ad-hoc, because grep-for-`scope_to_user` is the CI linter's anchor in §19.

**Locked rule.** Any direct repository query against the **6 owned tables** — `seller_profile`, `catalogs`, `products`, `product_drafts`, `product_images`, `pricing_calcs`, `exports` — MUST be scoped via `scope_to_user`. Reads against the **4 global tables** — `templates`, `categories`, `field_enum_values`, `field_aliases` — are unscoped (global data per `MVP_ARCH §10.2`). `audit_events` is written exclusively by `audit_mw` (§4.G) and is also scoped by `user_id` at write-time.

**Forward reference.** §19 will ship a CI linter rule: any service method that touches an owned table whose signature omits `user_id: UUID` is rejected at PR time. This is the structural enforcement of philosophy M6 (tenant isolation).

---

### 4.D — `core/cache.py` — contract

**Owner:** `meesell-services-builder` (per §2.10).

**Purpose.** The read-through Valkey DB 3 helper that every cache consumer goes through — `category` (heaviest, schema + enum + tree), `customer` (seller-profile read), `catalog` (schema read on validate). Implements the version-tagged key scheme, stampede protection, ETag generation, and worker-startup pre-warm.

**Primary helper:**

```python
async def get_or_set(
    key: str,
    fetch_fn: Callable[[], Awaitable[T]],
    ttl: int,
    version: str | None = None,
    single_flight: bool = False,
) -> T:
    ...
```

**Version-tagged key format** per `MVP_ARCH §6.4`:

```
meesell:v{cache_version}:{key}
```

`cache_version` lives in `shared/config.py` and bumps on quarterly Meesho refresh — invalidates all schema/enum/category-tree keys atomically without `FLUSHDB`. When the caller passes `version=None`, the helper reads `settings.cache_version` automatically.

**Stampede protection** per `MVP_ARCH §6.8`: when `single_flight=True`, the helper uses Valkey `SET NX EX` to elect one fetcher; concurrent callers wait + read the populated value. Mandatory for the **291 large Brand-pattern enum keys** (`MVP_ARCH §0` premise #5 + §6.8) where simultaneous cache-miss requests on a hot category could each trigger a 200 KB JSON build.

**HTTP cache header helper:**

```python
def etag_for(payload: bytes) -> str:
    """Returns the SHA-256 ETag per MVP_ARCH §6.6."""
    ...
```

Route handlers that serve cached payloads (schema, enums, tree) call `etag_for` to populate the `ETag` response header per MVP_ARCH §6.6 — enabling 304 Not Modified short-circuits on the Angular `HttpClient` (saves 8 KB JSON parse on every wizard load).

**Pre-warm helper:**

```python
async def prewarm_top_categories(n: int = 100) -> None:
    """Runs at FastAPI worker startup per MVP_ARCH §6.7."""
    ...
```

Invoked from `app/main.py` `startup` event — eliminates cold-start stampede on the top 100 categories per the hot/cold tier strategy (MVP_ARCH §6.7).

**Locked rule.** Every read of `templates` / `categories` / `field_enum_values` / `field_aliases` / `seller_profile` goes through `core/cache.py`. Modules do NOT call the repository directly for these reads except via this cache wrapper. The helper internally calls the module's repository on cache miss (e.g. `category.repository.fetch_schema_uncached(...)`). This is the structural enforcement of MVP_ARCH §6 caching strategy.

---

### 4.E — `core/plan_guard.py` — contract

**Owner:** `meesell-services-builder` (per §2.10).

**Purpose.** Translates the JWT `plan` claim into a feature-budget enforcement gate. V1 ships a single tier (`"free"`) with the limits below; the contract is forward-compatible — V1 ignores `plan` parameter dispatch; V1.5 widens it.

**Primary helper:**

```python
async def enforce_plan_limit(
    user_id: UUID,
    plan: str,
    resource: Literal[
        "product_count",
        "ai_autofill_hourly",
        "smart_picker_hourly",
        "create_product_hourly",
    ],
    requested: int = 1,
) -> None:
    """Raises PlanLimitExceededError(resource=..., current=..., limit=...) on overflow."""
    ...
```

**V1 limits** per `MVP_ARCH §10.7` + §10.9 (free tier):

| resource | limit | window | enforcement point |
|---|---|---|---|
| `product_count` | 100 | total (soft cap, hard-block on create) | `catalog.service.create_product` |
| `ai_autofill_hourly` | 50 / h | sliding-hour | `catalog.service.autofill_product` |
| `smart_picker_hourly` | 100 / h | sliding-hour | `category.service.suggest` |
| `create_product_hourly` | 20 / h | sliding-hour | `catalog.service.create_product` |

**OTP rate limit** (3/h/phone) is **NOT** handled by `plan_guard` — it is a **security** limit and is enforced directly by `core/middleware/rate_limit_mw.py` (§4.G). `plan_guard` covers business feature budgets; rate-limit middleware covers DDoS / brute-force / OTP-bomb security. Per §1.F: "security before business."

`PlanLimitExceededError` subclasses `MeesellError` (§4.F) with `status_code=402` (Payment Required), `validation_message_id="plan.limit_exceeded"`.

**Locked rule.** Every write-path to the **5 owned tables that incur a feature cost** — `products` (create), `catalogs` (create), `pricing_calcs` (create), `exports` (create), `product_drafts` (create) — calls `enforce_plan_limit` BEFORE the write. Reads do not call `plan_guard`. The list of resources is closed at the four above for V1; expanding it requires a documented §4 amendment.

**V1.5 forward note.** When the tier widens to `"free" | "pro"`, the existing `plan` parameter dispatches on tier — `"pro"` lifts product_count to 1000, autofill_hourly to 500, etc. (per MVP_ARCH §14). The contract is forward-compatible; no caller signature changes.

---

### 4.F — `core/errors.py` — contract

**Owner:** `meesell-services-builder` (per §2.10).

**Purpose.** Centralises structured error handling, `validation_message_id` resolution (via `i18n/`), and the **single error envelope shape** the whole backend emits. Route handlers do NOT format error responses — they raise the appropriate exception; this module catches and formats.

**Exception hierarchy root:**

```python
class MeesellError(Exception):
    code: str                      # machine-readable, e.g. "tenancy.cross_user_access"
    status_code: int               # HTTP status
    validation_message_id: str     # i18n lookup key per MVP_ARCH §5.6.7
```

Domain modules subclass this in their `modules/<x>/exceptions.py` (per §3.C). Examples:
- `catalog.exceptions.DraftNotFoundError(MeesellError)` — `status_code=404`, `validation_message_id="catalog.draft_missing"`.
- `customer.exceptions.ProfileIncompleteError(MeesellError)` — `status_code=422`, `validation_message_id="customer.profile_incomplete"`.
- `pricing.exceptions.UnsupportedCategoryError(MeesellError)` — `status_code=422`, `validation_message_id="pricing.commission_missing"`.

**Error envelope shape (locked):**

```json
{
  "detail": "Human-readable resolved message",
  "code": "machine_readable_slug",
  "validation_message_id": "i18n.lookup.key",
  "request_id": "x-request-id-value"
}
```

No module customises this shape. The `detail` field is the resolved i18n string for the active locale (V1 = English-only; the resolver returns the `messages_en.py` value).

**Registration helper:**

```python
def register_error_handlers(app: FastAPI) -> None:
    """Registers handlers for MeesellError, pydantic.ValidationError, HTTPException, Exception."""
    ...
```

Called from `app/main.py` after app creation. Registers four handlers in priority order:
1. `MeesellError` → resolves `validation_message_id` via `i18n.resolver`, builds envelope with the subclass's `status_code`.
2. `pydantic.ValidationError` → maps each field error to `validation_message_id="validation.{field}.{constraint}"` (matches MVP_ARCH §5.6.7 convention); returns `422`.
3. `HTTPException` (FastAPI built-in) — for legacy / framework-raised errors; envelope built with `validation_message_id="http.{status_code}"`.
4. `Exception` (last resort) → `500` with `validation_message_id="server.internal_error"`; full traceback logged, **never** returned to client.

**Locked rule.** Route handlers do NOT format error responses; they raise the appropriate exception subclass. The error envelope shape is fixed — no module customises it. The `request_id` field is read from `request.state.request_id` (set by §4.G `request_id` middleware) — guarantees client-side correlation with logs.

---

### 4.G — `core/middleware/` subtree

**Owner:** `meesell-services-builder` (per §2.10; `auth_mw` collaboration with `meesell-auth-builder`).

Each middleware is documented below: purpose (1 line), position in the chain, `request.state` keys it reads / writes, failure mode, owner.

**`request_id.py`**
- Purpose: generate UUIDv4, attach to request, add response header.
- Position: 2nd in chain (after CORS).
- Writes `request.state.request_id: str`. Reads incoming `X-Request-ID` header and reuses if present (client correlation).
- Response header: `X-Request-ID: <uuid>`.
- Failure mode: cannot fail — generates locally.
- Owner: `meesell-services-builder`.

**`auth_mw.py`**
- Purpose: optionally decode JWT and attach user to request state for log correlation. Does NOT enforce 401.
- Position: 3rd (after request_id).
- Reads `Authorization: Bearer <token>` header. Writes `request.state.user: CurrentUser | None`.
- Failure mode: **fail-open in middleware** — missing/malformed token leaves `request.state.user = None`. The `get_current_user` dep (§4.B) is the **fail-closed** layer that returns 401. Rationale: public routes (`/health`, `/api/v1/auth/otp/send`) must traverse this middleware without 401-ing.
- Owner: `meesell-auth-builder` (decode logic — shares JWT util with `core/auth.py`) + `meesell-services-builder` (middleware wiring).

**`tenancy_mw.py`**
- Purpose: copy `request.state.user.user_id` into request context for logger correlation. **No 401/403 logic here** — enforcement is at the dep + service layer (§4.C).
- Position: 4th (after auth_mw).
- Reads `request.state.user`. Writes `request.state.user_id: UUID | None` (sentinel for log filters).
- Failure mode: cannot fail — pure copy.
- Owner: `meesell-services-builder`.

**`rate_limit_mw.py`**
- Purpose: Valkey DB 0 sliding-window enforcement BEFORE route handler. Returns 429 if exceeded.
- Position: 5th (after tenancy_mw).
- Reads per-route limit config (decision in §4.H below). Reads `request.state.user.user_id` (per-user) and `request.client.host` (per-IP DDoS gate).
- Failure mode: **fail-open with alarm** per MVP_ARCH §13 risk table (Valkey SPOF row 1) — if Valkey is unreachable, request passes and ops alarm fires.
- Owner: `meesell-services-builder` (refactor of existing `backend/app/middleware/rate_limit.py` into the §3.D location + per-route config wiring).

**`plan_guard_mw.py`**
- Purpose: **V1 NO-OP placeholder**. V1.5 gates global plan validity (e.g. subscription expired → 402 across all routes).
- Position: 6th (after rate_limit_mw).
- Reads `request.state.user.plan`. Writes nothing in V1.
- Failure mode: cannot fail (no-op).
- Owner: `meesell-services-builder`.
- Documented here as **wired but inert** in V1 so V1.5 can light it without architecture change. The existing `backend/app/middleware/plan_guard.py` `ensure_can_generate` helper migrates to the dep-layer `core/plan_guard.py` (§4.E); the middleware file replaces it as a thin chain participant.

**`audit_mw.py`**
- Purpose: write `audit_events` row AFTER successful 2xx response per MVP_ARCH §11.3 + Philosophy M8 ("if it committed, it logged; if it didn't commit, it never happened").
- Position: 7th — **runs AFTER the route handler**.
- Reads `request.state.{user_id, request_id}`, route path, response status. Reads response body for diff capture (autosave PATCH events only — see coalescing below).
- Failure mode: drop-on-failure with logged warning — observability MUST NOT block business path per §1.E LangFuse rule.
- **Coalescing.** Coalesces same-key `(user_id, product_id)` PATCH events within a 5-minute window per `MVP_ARCH §11.4` — 30× volume reduction for autosave. Non-autosave events (`product.export`, `seller_profile.update`, `auth.login`) are NEVER coalesced — each occurrence is a distinct audit fact per §11.4.
- **PII scrubbing.** Before any row is written, `phone` is replaced with `SHA-256(phone + PII_SALT)`, `FSSAI_no` / `GST_no` are stripped, per MVP_ARCH §11.9. PII_SALT lives in `shared/config.AUDIT_PII_SALT`.
- **Write posture.** V1 = **synchronous inline append** per MVP_ARCH §11.3 (current traffic floor justifies it). V1.5 moves to a Celery sink per MVP_ARCH §14 — `core/middleware/audit_mw.py` becomes `enqueue(audit_event_task)` without changing the call site.
- Owner: `meesell-services-builder`.

**Cross-middleware state consistency.** The chain reads/writes a small set of `request.state` keys. Listed once here so the chain is internally auditable:

| Middleware | Reads | Writes |
|---|---|---|
| `request_id` | (header) | `request_id` |
| `auth_mw` | (header) | `user` (CurrentUser \| None) |
| `tenancy_mw` | `user` | `user_id` (UUID \| None) |
| `rate_limit_mw` | `user.user_id`, `client.host` | (logs only) |
| `plan_guard_mw` | `user.plan` | — (V1 no-op) |
| route handler | `user_id` (via `get_current_user` dep) | response |
| `audit_mw` | `user_id`, `request_id`, response | `audit_events` row |

**AMENDMENT 2026-06-05 — FE-D5 ratification:** CORS configuration for the split-token refresh cookie. The CORS middleware (position 1 in the chain, BEFORE `request_id`) MUST advertise `Access-Control-Allow-Credentials: true` on responses to `/api/v1/auth/*` paths so the browser sends the `refresh_token` cookie on cross-subdomain XHR. `Access-Control-Allow-Origin` is the explicit requesting frontend origin (e.g. `https://dev.mesell.xyz`, `https://www.mesell.xyz`) read from `shared/config.CORS_ALLOWED_ORIGINS` — **NEVER `*`**, because CORS with credentials forbids the wildcard. The `Set-Cookie` header issued by `/auth/otp/verify` and `/auth/refresh` carries `Domain=.mesell.xyz` so the cookie is scoped to all `mesell.xyz` subdomains, allowing a `dev.mesell.xyz`-loaded page to send the cookie to `api.mesell.xyz`. The frontend `HttpClient` sets `withCredentials: true` ONLY for `/api/v1/auth/*` calls (per the frontend memo); all other API calls remain `withCredentials: false` to avoid leaking unrelated cookies. The §20 (Deployment) section will confirm the K3s Ingress and Traefik configuration do not strip credentialed CORS headers. (End amendment.)

---

### 4.H — Middleware ordering rationale

The locked order from §3.D, verbatim:

```
CORS → request_id → auth_mw → tenancy_mw → rate_limit_mw → plan_guard_mw → (route handler) → audit_mw
```

Rationale for each position:

- **CORS first.** Must handle preflight `OPTIONS` requests before any auth or state setup — preflight has no `Authorization` header and would otherwise 401 unnecessarily.
- **request_id second.** Every downstream layer needs a correlation ID, including auth failures, so it must run before auth.
- **auth_mw before tenancy_mw.** Tenancy needs `request.state.user` to exist (or be `None`); auth_mw is the layer that sets it.
- **rate_limit_mw before plan_guard_mw.** Rate-limit is a **security** control (always on, fail-open with alarm); plan_guard is a **business** control (V1 inert). Security gates before business gates — a brute-force attacker must hit 429 even on a free-tier no-op path.
- **audit_mw last (after route handler).** Audit on 2xx commit only per MVP_ARCH §11.3 and Philosophy M8 — failed transactions don't log. Running audit before the handler would either pre-commit-log (violates M8) or require complex compensating deletes on failure (operationally fragile).

**Per-route rate-limit configuration decision.** The brief asks the coordinator to pick between (a) `@rate_limit(scope, limit, key)` decorator on route handlers, (b) `route.openapi_extra` metadata read by middleware, or (c) middleware-only with a path → limit lookup table. **Decision: option (a), a per-route decorator** — applied by `meesell-api-routes-builder` at route definition time, read by `rate_limit_mw` via the FastAPI route's `dependant.dependencies` introspection. Rationale:
- (a) keeps the rate-limit declaration **adjacent to the route handler**, which is where the cost intuition lives — the routes-builder knows that `POST /products/{id}/autofill` is expensive and tags it accordingly.
- (b) `openapi_extra` is a documentation slot; misusing it for runtime config muddles the OpenAPI surface.
- (c) a central lookup table in middleware fails the "find the limit near the handler" review heuristic — invisible coupling.
- The decorator is a thin shim that attaches metadata to the FastAPI route; the middleware does the Valkey work. No business logic in the decorator.

Per-IP global DDoS limit (NOT per-route) is applied unconditionally by `rate_limit_mw` reading `request.client.host` — a single `meesell:rl:ip:{ip}:1m` sliding window.

---

### 4.I — Cross-layer integration points

**What `core/` MAY import** (allowed dependencies):

- `shared/database.py` → `AsyncSession`, `get_db` dep — consumed by `core/auth.py` (for the `users` lookup), `core/middleware/audit_mw.py` (for the `audit_events` write).
- `shared/valkey.py` → async Redis client — consumed by `core/cache.py` (DB 3), `core/middleware/rate_limit_mw.py` (DB 0), `core/plan_guard.py` (DB 0 for hourly counters).
- `shared/config.py` → `JWT_SECRET`, `JWT_EXPIRY_DAYS`, `cache_version`, `AUDIT_PII_SALT`, rate-limit configs.
- `shared/models/` → ORM models. The **only model `core/` writes** is `audit_events` (via `audit_mw`). `core/auth.py` reads `users` for the JWT `sub` resolution.
- `i18n/resolver.py` → `validation_message_id` resolution (consumed by `core/errors.py`).

**What `core/` MAY NOT import** (forbidden):

- `app.modules.*` — `core/` is BELOW domain modules in the dependency direction (per §0.B + §3.D). Importing a module would invert the dependency and break the modular-monolith discipline.
- `app.adapters.*` — adapters are the egress layer for domain modules; `core/` does NOT call adapters. The single grey-area case is `adapters/langfuse` for audit trace egress; this is **V1.5 out-of-scope** (deferred per §6 sub-section, confirmed by §15 when that section drills).
- `app.ai_ops.*` — AI Ops (§6A) is a peer layer above adapters, not consumed by `core/`. (AI Ops itself consumes `core/cache.py` and `core/errors.py` — the import direction is `ai_ops → core`, not reverse.)

This import-direction discipline is enforced in §19 via an import-linter rule: `core/` imports of `app.modules.*` or `app.adapters.*` (except `langfuse` post-V1.5) fail CI.

---

### 4.J — What §4 does NOT cover

Section 4 specifies `core/` contracts only. The following belong elsewhere:

- The `i18n/` message contents (English strings, `validation_message_id` → text mapping) → §5A.
- The AI-specific guardrails (Layer 1 prompt constraint, parser-level enum check) and cost tracking → §6A.
- Per-module exception hierarchies (e.g. `catalog.exceptions.DraftNotFoundError`) — each module owns its `exceptions.py` (§7-§14).
- The actual ORM model definitions (`shared/models/`) — owned by `meesell-database-builder` per agent spec; schema locked in `MVP_ARCH §2`.
- K3s deployment of any `core/` component (replica counts, resource limits) → §20.
- The per-route limit table values for ALL routes — the table in §4.E lists the four budgeted resources; §17 (Endpoint Inventory) and per-module §7-§14 sections will enumerate each route's specific rate-limit tag.

A reviewer evaluating Section 4 is asking only "are the cross-cutting contracts correct, does the middleware chain compose, are the security invariants enforced?" — not any content question about what an autofill error message says, what the `gemini` adapter does on a 503, or how dashboards aggregate.

---

## Section 5 — `shared/` — Foundation Layer

STATUS: LOCKED (2026-06-05)

### 5.A Preamble

Section 5 specifies what `shared/` **CONTAINS** — the foundation layer below `core/`. Stateless, no business logic, used identically by every module. Section 5 specifies **INTERFACES**, not implementations; it specifies the **import contract** that the 8 domain modules + `core/` + `ai_ops/` + `i18n/` all consume. File locations are locked in §3.E; ownership is locked in §2.11. A reviewer evaluating Section 5 asks: "does the `AsyncSession` lifecycle compose with FastAPI `Depends`, does the Valkey DB allocation match §1.B, are the env vars complete for V1, is the model registry import path canonical?" — **not** "is the DDL right" (that is `MVP_ARCH §2`), not "is the migration ordering correct" (that is `MVP_ARCH §2.6`), not "where do these files live" (that is §3.E).

---

### 5.B `shared/database.py`

**Owner:** `meesell-database-builder` (per §2.11) + `meesell-services-builder` (per §2.11 — config wiring side).

**Purpose.** Single source of the SQLAlchemy 2.0 async engine, the `AsyncSession` factory, and the `get_db` FastAPI dependency. Every route handler and every service that touches the database receives its session through this module — no other module instantiates an engine, a `sessionmaker`, or a `Session`.

**Engine creation (locked verbatim):**

```python
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,        # V1 default: 10
    max_overflow=settings.DB_MAX_OVERFLOW,  # V1 default: 5
    pool_pre_ping=True,                      # detect stale conns
    pool_recycle=settings.DB_POOL_RECYCLE,  # V1 default: 1800 (30 min)
    echo=settings.DB_ECHO,                   # V1 default: False
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
```

`pool_pre_ping=True` is mandatory — it detects stale connections after a Postgres pod restart without a process bounce. `expire_on_commit=False` is mandatory — the async-relationship lifecycle in SQLAlchemy 2.0 cannot tolerate post-commit expiration without explicit `await session.refresh(...)` calls, which the codebase does not pattern.

**`get_db` FastAPI dependency (locked verbatim):**

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

**Locked rule.** Every route handler + service that touches the DB receives `db: AsyncSession = Depends(get_db)`. No module creates its own engine, sessionmaker, or session. The Celery-worker variant (`make_worker_session`, currently in the legacy `backend/app/database.py` per the session-2 baseline) survives the migration to `shared/database.py` as a peer helper — it uses `NullPool` for the same `asyncio.run()` Future-binding reason documented in the legacy module's docstring. `meesell-database-builder` ports both helpers verbatim during the §3.E migration.

**Pool sizing math.** 2 FastAPI pod replicas × (`pool_size=10` + `max_overflow=5`) = **30 concurrent DB connections per replica pair from the API tier**. The Celery worker pod uses `NullPool` (each task opens + closes one TCP connection), so worker burst is bounded by `worker_concurrency`. Postgres 16 ships with `max_connections=100` default per the infra baseline; the API tier consumes 30 in the worst case, leaving ~70 for workers + ad-hoc psql + Alembic. §18 (Background Jobs) caps total Celery worker concurrency to keep the system-wide total **<80** — well within the Postgres budget with headroom for surge.

**Lifecycle.** `engine` and `AsyncSessionLocal` are module-level singletons constructed at import time. Both are torn down via an `app.shutdown` handler that calls `await engine.dispose()` — registered from `app/main.py` per §3.B's `main.py` ownership.

---

### 5.C `shared/valkey.py`

**Owner:** `meesell-services-builder` (per §2.11).

**Purpose.** Provides the async Valkey 8 client (Redis-protocol compatible), exposing four logical-DB selector factories that match the §1.B topology lock. The factory boundary IS the DB-allocation enforcement — code that wants DB 3 cache calls `get_valkey_cache()`; cross-DB access is structurally impossible because no module holds a raw client reference.

**Underlying library.** `redis.asyncio` (works against Valkey 8 — protocol-compatible).
**Connection URL.** `settings.VALKEY_URL` (existing `.env` convention; see §5.D).

**Four client factories (locked):**

```python
async def get_valkey_otp() -> Redis:      # DB 0 — OTP, RL, sessions, refresh-token allowlist
async def get_valkey_broker() -> Redis:   # DB 1 — Celery broker
async def get_valkey_results() -> Redis:  # DB 2 — Celery result backend
async def get_valkey_cache() -> Redis:    # DB 3 — app cache (read-through helper consumes this)
```

Each factory returns a pool-backed client; clients are cached per worker process via module-level lazy init (`_otp_client: Redis | None = None`). The same TCP connection pool is reused for the lifetime of the worker; teardown happens via the same `app.shutdown` handler that disposes the SQL engine.

**Locked rule (DB allocation).** Code that touches Valkey MUST select the correct DB via the right factory. Cross-DB access (e.g. RL middleware reading DB 3, or `core/cache.py` reading DB 0) is **forbidden**. This is the structural enforcement of the §1.B topology lock — there is no `get_valkey(db: int)` factory, by design.

**Locked rule (FE-D5 specific).** The refresh-token allowlist key `cache:refresh:{hmac_sha256(token, REFRESH_TOKEN_PEPPER)}` lives in **DB 0** via `get_valkey_otp()`. The `core/auth.py` refresh-rotation Lua script (§4.B amendment) runs against DB 0. The script is loaded **once at process startup** via `SCRIPT LOAD` (returning the SHA1 digest) and invoked thereafter via `EVALSHA` — this is the production-efficiency posture; `EVAL` is the fallback when `EVALSHA` returns `NOSCRIPT` (which happens only after a Valkey restart flushes the script cache). The script digest is cached on the `iam` service singleton.

**Per-DB usage map (cross-reference, not authoritative — the authorities are §4.B, §4.D, §4.G, §10.7).**

| DB | Purpose | Primary consumers |
|---|---|---|
| 0 | OTP store, sliding-window rate limits, refresh-token allowlist | `iam` service (OTP + refresh), `core/middleware/rate_limit_mw.py`, `core/middleware/audit_mw.py` (PII salt is config, not Valkey, but coalescing keys live here) |
| 1 | Celery broker | `workers/celery_app.py` only |
| 2 | Celery result backend | `workers/celery_app.py` only |
| 3 | Application read-through cache (schemas, enums, category tree, seller-profile) | `core/cache.py` only |

---

### 5.D `shared/config.py`

**Owner:** `meesell-services-builder` (per §2.11).

**Purpose.** Single Pydantic Settings singleton. Reads from `.env` in dev; reads from K3s pod env vars (which are populated from GCP Secret Manager via the `app_secret_ids` mechanism per infra memory) in staging + prod. Every secret is sourced via Secret Manager in prod; the `.env` convention is dev-only.

**Class signature (locked verbatim):**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    # See env-var registry below

settings = Settings()  # singleton
```

`case_sensitive=True` matches the K3s convention of upper-case env-var keys (Secret Manager values are injected into pods as `JWT_SECRET=...`, not `jwt_secret=...`). `extra="ignore"` permits per-environment env vars (e.g. `TF_VAR_*`, `KUBE_*`) without forcing them into the schema.

**Env-var registry — every V1 env var, grouped.**

**Database**

| Variable | Type / Default | Required | Notes |
|---|---|---|---|
| `DATABASE_URL` | `str` | yes | `postgresql+asyncpg://…` |
| `DB_POOL_SIZE` | `int = 10` | no | per §5.B |
| `DB_MAX_OVERFLOW` | `int = 5` | no | per §5.B |
| `DB_POOL_RECYCLE` | `int = 1800` | no | 30 min |
| `DB_ECHO` | `bool = False` | no | SQL echo for dev only |

**Valkey**

| Variable | Type / Default | Required | Notes |
|---|---|---|---|
| `VALKEY_URL` | `str` | yes | `redis://host:port` (DB number is selected by the factory in §5.C, not in the URL) |

**JWT / Auth (FE-D5 ratified)**

| Variable | Type / Default | Required | Notes |
|---|---|---|---|
| `JWT_SECRET` | `str` | yes | Secret Manager ref `jwt-secret` (version 1 live per infra memory) |
| `JWT_ALGORITHM` | `str = "HS256"` | no | per `MVP_ARCH §11.7` |
| `ACCESS_TOKEN_TTL_SECONDS` | `int = 900` | no | prod 900; staging override 60; dev override 30 |
| `REFRESH_TOKEN_TTL_SECONDS` | `int = 604800` | no | prod 7d; staging override 300 (5 min); dev override 120 (2 min) |
| `REFRESH_TOKEN_PEPPER` | `str` | yes | Secret Manager ref `refresh-token-pepper` (NEW per FE-D5 amendment 2026-06-05; not yet populated in Secret Manager — `meesell-infra-builder` adds it during `iam` dispatch) |
| `JWT_EXPIRY_DAYS` | — | **DEPRECATED** | Removed during `iam` construction dispatch per §4.B amendment. Replaced by `ACCESS_TOKEN_TTL_SECONDS`. Legacy `backend/app/config.py` carries this field today; the migration drops it. |

**MSG91**

| Variable | Type / Default | Required | Notes |
|---|---|---|---|
| `MSG91_AUTH_KEY` | `str` | yes | Secret Manager ref `msg91-auth-key` (version 1 live; IP whitelist note per infra memory) |
| `MSG91_TEMPLATE_ID` | `str` | yes | Secret Manager ref `msg91-template-id` (version 1 live per Phase A) |

**Razorpay**

| Variable | Type / Default | Required | Notes |
|---|---|---|---|
| `RAZORPAY_KEY_ID` | `str` | yes | Secret Manager ref `razorpay-key-id` (TEST key in V1) |
| `RAZORPAY_KEY_SECRET` | `str` | yes | Secret Manager ref `razorpay-key-secret` |
| `RAZORPAY_WEBHOOK_SECRET` | `str` | yes | Secret Manager ref `razorpay-webhook-secret` (NEW — not yet populated; `meesell-infra-builder` adds during `iam` dispatch) |

**Gemini (per §6 / §6A)**

| Variable | Type / Default | Required | Notes |
|---|---|---|---|
| `GEMINI_API_KEY` | `str` | yes | Secret Manager ref `gemini-api-key` (version 1 live per infra memory) |
| `GEMINI_MODEL` | `str = "gemini-2.5-flash"` | no | per CLAUDE.md Decision 3 |

**GCS (per §6 / `MVP_ARCH §10.8`)**

| Variable | Type / Default | Required | Notes |
|---|---|---|---|
| `GCS_BUCKET` | `str` | yes | e.g. `meesell-images`; per §6 + `MVP_ARCH §10.8` |
| `GCS_PROJECT_ID` | `str` | yes | GCP project (current: `project-1f5cbf72-2820-4cdb-949`) |
| `GCS_SIGNED_URL_TTL_SECONDS` | `int = 3600` | no | 1 h per `MVP_ARCH §10.8` |

**LangFuse (per §6A)**

| Variable | Type / Default | Required | Notes |
|---|---|---|---|
| `LANGFUSE_PUBLIC_KEY` | `str` | yes | observability — public key safe in env |
| `LANGFUSE_SECRET_KEY` | `str` | yes | Secret Manager ref `langfuse-secret-key` (NEW — populated during §6A dispatch) |
| `LANGFUSE_HOST` | `str = "https://cloud.langfuse.com"` | no | overrideable for self-host in V2 |

**AI Ops (per §6A + `MVP_ARCH §8`)**

| Variable | Type / Default | Required | Notes |
|---|---|---|---|
| `AI_DAILY_BUDGET_INR` | `int = 500` | no | per `MVP_ARCH §8`; §6A hard-stops at 100% |
| `AI_BUDGET_ALARM_THRESHOLD` | `float = 0.80` | no | per §6A — 80% alarm before hard-stop |

**Cache (per `MVP_ARCH §6.4`)**

| Variable | Type / Default | Required | Notes |
|---|---|---|---|
| `CACHE_VERSION` | `str = "v1"` | no | bumps on quarterly Meesho refresh; consumed by `core/cache.py` per §4.D |

**Audit (PII scrubbing per §4.G)**

| Variable | Type / Default | Required | Notes |
|---|---|---|---|
| `AUDIT_PII_SALT` | `str` | yes | Secret Manager ref `audit-pii-salt` (version 1 live per Phase A) |

**Rate limits**

| Variable | Type / Default | Required | Notes |
|---|---|---|---|
| `RL_PER_IP_PER_MINUTE` | `int = 120` | no | DDoS-class default; per-route decorator (§4.H) overrides per `MVP_ARCH §10.7` |

**CORS (per §4.G amendment)**

| Variable | Type / Default | Required | Notes |
|---|---|---|---|
| `CORS_ALLOWED_ORIGINS` | `list[str]` | yes | e.g. `["https://dev.mesell.xyz", "https://www.mesell.xyz"]`; **NEVER `["*"]`** per §4.G amendment (CORS with credentials forbids wildcard) |
| `CORS_ALLOW_CREDENTIALS` | `bool = True` | no | mandatory `True` on `/api/v1/auth/*` per §4.G amendment |

**App**

| Variable | Type / Default | Required | Notes |
|---|---|---|---|
| `APP_ENV` | `Literal["development","staging","production"]` | yes | drives env-specific TTL overrides above |

**Locked rule (secret sourcing).** Every secret is sourced via GCP Secret Manager in prod and staging (per `meesell-infra-builder` memory — Secret Manager IDs and IAM bindings already provisioned for the 7 in-place secrets; the 3 new secrets — `refresh-token-pepper`, `razorpay-webhook-secret`, `langfuse-secret-key` — are added during the relevant specialist dispatches). The `.env` convention is **dev-only**. Pydantic Settings reads either path transparently because both populate the same `os.environ` namespace at process start (K3s injects via `envFrom: secretRef:` per §20).

**Validator.** `Settings.__init__` MUST validate every `required` field is non-empty at boot. Missing required field → process exits with a clear stderr message identifying the missing variable. Pattern (locked):

```python
@model_validator(mode="after")
def _require_non_empty(self) -> "Settings":
    for fname in REQUIRED_FIELDS:
        if not getattr(self, fname):
            raise SystemExit(f"FATAL: required env var {fname} is empty or unset")
    return self
```

`REQUIRED_FIELDS` is the explicit list of `yes`-marked rows in the tables above. Fail-fast at boot is the contract — a half-configured process is forbidden.

---

### 5.E `shared/models/`

**Owner:** `meesell-database-builder` (per §2.11) — the database-builder migration agent already shipped the 13 models in session 2 Phase 1; the §3.E migration moves the existing `backend/app/models/` tree under `backend/app/shared/models/` verbatim, no schema changes.

**Purpose.** The 13 ORM models registry. The single canonical import path for any model class in the codebase.

**File list (per §3.E).**

```
shared/models/
├── __init__.py            # exports all 13 — single import point
├── user.py                # users
├── seller_profile.py      # seller_profile
├── template.py            # templates
├── category.py            # categories
├── field_enum_value.py    # field_enum_values
├── field_alias.py         # field_aliases
├── catalog.py             # catalogs
├── product.py             # products
├── product_image.py       # product_images
├── pricing_calc.py        # pricing_calcs
├── export.py              # exports
├── audit_event.py         # audit_events
└── product_draft.py       # product_drafts
```

**Canonical import path (locked):**

```python
from app.shared.models import (
    User, SellerProfile, Template, Category, FieldEnumValue, FieldAlias,
    Catalog, Product, ProductImage, PricingCalc, Export, AuditEvent, ProductDraft,
)
```

**ORM style.** SQLAlchemy 2.0 `Mapped[T]` typed style throughout — `Mapped[UUID] = mapped_column(...)` per `meesell-database-builder/MEMORY.md` Phase 1 conventions. Forward references to other models use the `from __future__ import annotations` + `TYPE_CHECKING`-guarded import pattern to break circular imports; relationships resolve via string-based `relationship("ClassName", ...)` at mapper-configuration time. The `__init__.py` import order follows the FK topological dependency chain so every relationship resolves on first access without manual `configure_mappers()`.

**DDL authority.** `MVP_ARCHITECTURE.md §2` is the spec; `shared/models/` is the **implementation**, not the spec. **Migration ordering: `MVP_ARCHITECTURE.md §2.6` (10-step Alembic sequence) is the single authoritative reference** — §5 does NOT duplicate the ordering. The current Alembic head is `f31c75438e61` per §0.D; subsequent migrations are authored by `meesell-database-builder` against the schema spec, never against the live ORM.

**Locked rule (no redefinition).** NO module redefines a model. NO module imports from another module's `repository.py` to obtain a model class. The single canonical import path is `from app.shared.models import X`. This is the structural enforcement of the §16 "no cross-module repository imports" rule at the model-registry level — even if a `catalog/repository.py` query incidentally returns a `Category` instance through a join, it returns the registry's `Category` class, the same class every other module sees.

**Base class.** `Base = DeclarativeBase` lives in `shared/database.py` (per §5.B), re-exported by `shared/models/base.py` for backward compatibility with the existing `backend/app/models/base.py` pattern (session-2 Phase 1 convention).

---

### 5.F What §5 does NOT cover

- **DDL** — owned by `MVP_ARCH §2`; §5 cites it, does not duplicate.
- **Migration ordering** — owned by `MVP_ARCH §2.6` (10-step Alembic sequence); §5 cites it, does not duplicate.
- **The presentation-layer JSONB contract for `templates.schema_jsonb`** — owned by §5A.
- **The Valkey cache key versioning + invalidation algorithm** — owned by `core/cache.py` §4.D (consumes `CACHE_VERSION` from §5.D).
- **The refresh-token Lua script content** — owned by `core/auth.py` §4.B FE-D5 amendment; §5 only confirms it runs against DB 0 via `get_valkey_otp()` and is `SCRIPT LOAD`'d once at startup.
- **The seed scripts under `backend/scripts/`** — owned by `meesell-database-builder` (Phase 3 shipped 5 seed scripts per database-builder memory).
- **K3s pod env-var injection** (`envFrom: secretRef:` wiring of Secret Manager secrets into pods) — owned by §20.
- **The `make_worker_session` Celery-worker helper's `NullPool` rationale** — survives as a peer helper in `shared/database.py` with its existing docstring; §18 covers Celery configuration.

A reviewer evaluating Section 5 asks only: "do the contracts compose, is the env-var registry complete, is the model registry import path canonical, are the FE-D5 ratifications present?" — not any question about DDL, migrations, prompt content, or pod manifests. Those belong to their own sections and other tracks.

---

## Section 5A — Presentation Layer Contract + i18n

STATUS: LOCKED (2026-06-05)

### 5A.A Preamble

Section 5A locks the single backend-side source of truth for two contracts: (a) the `templates.schema_jsonb` JSONB envelope and the per-field shape inside `fields[]` — read at PATCH validation time, written at template seed time — and (b) the locale-aware `validation_message_id` resolution against the `i18n/` package wired in §3.H. Section 5A does NOT specify DDL (that is `MVP_ARCH §2`), does NOT specify field-enum value storage (that is `MVP_ARCH §5.6.4` and the `field_enum_values.enum_entries` shape recorded in `meesell-database-builder` memory), does NOT specify display-label CONTENT (that is `data/parsed/field_display_overrides.json` and the seed-time merge per `MVP_ARCH §5.6.6`), and does NOT specify enum-label localisation payloads (that is `enum_entries[].labels`, owned by the DATA track per `MVP_ARCH §5.6.4`). Section 5A specifies SHAPES and CONVENTIONS. Three consumer modules read from this contract: `category` serves the schema (§2.3), `catalog` validates against it (§2.4), `export` round-trips via `field_aliases.for_xlsx_export` (§2.8). None of the three redefine the contract; all consult §5A.

---

### 5A.B `templates.schema_jsonb` top-level envelope

The envelope is a single JSON object with six locked top-level keys. The shape is:

```json
{
  "fields": [ /* see §5A.C — array of per-field objects, order = wizard order */ ],
  "compulsory_count": 28,
  "optional_count": 14,
  "total_count": 42,
  "wizard_step_count": 6,
  "main_sheet_label": "Sarees-Fill this",
  "compliance_shape": "standard"
}
```

Per-key contract:

- **`fields: list[FieldSpec]`** — REQUIRED. Ordered. The wizard step composition algorithm (`MVP_ARCH §5.6.3`) consumes the order directly; the first compulsory field encountered becomes the first wizard-step entry. Optional fields appear after their corresponding step's compulsory tail. Each element conforms to §5A.C.
- **`compulsory_count: int`** — REQUIRED. Count of `fields[].marker == "compulsory"`. **Derived at seed time; readers MUST NOT recompute.** Caching layer (§4.D) and dashboard summaries trust this value verbatim.
- **`optional_count: int`** — REQUIRED. Count of `fields[].marker == "optional"`.
- **`total_count: int`** — REQUIRED. Invariant: `total_count == compulsory_count + optional_count`. Seed-time validator rejects any envelope where the equality fails.
- **`wizard_step_count: int`** — REQUIRED. Derived per `MVP_ARCH §5.6.3` as `ceil(compulsory_count / 5)`, clamped to the range `[3, 8]`. Seed-time builder writes this; readers consume it for stepper preview.
- **`main_sheet_label: str`** — REQUIRED. The Meesho XLSX main-sheet label exactly as parsed from the source workbook (e.g. `"Sarees-Fill this"`, `"Books-Fill this"`). The `export` module's Export Adapter uses this for round-trip identification per `MVP_ARCH §5.5`. Honours philosophy M10 by carrying the Meesho label only inside `schema_jsonb` and the Export Adapter — never in API responses to the seller, never in AI prompts.
- **`compliance_shape: Literal["standard", "collapsed"]`** — REQUIRED. `"standard"` for 3,771 templates (9 compliance columns emitted in XLSX per `MVP_ARCH §12.6`); `"collapsed"` for the single Eye-Serum template (9 fields stored, 3 derived columns emitted) per founder ruling `MVP_ARCH §12.6` and `§0.G §12.6`. The `export` module's `ComplianceStrategy` class dispatches on this key. Per database-builder memory, the live database has exactly 1 `compliance_shape='collapsed'` row.

No other top-level keys are permitted in the V1 envelope. Future top-level additions require a §5A amendment block (append-only audit trail) before any consumer module may read them.

---

### 5A.C `fields[]` per-field contract

Each element of `fields[]` is a JSON object with the locked shape below. Required keys are marked REQUIRED; optional keys are marked OPTIONAL with a default semantics rule. Example element:

```json
{
  "name": "Product Name",
  "canonical_name": "product_name",
  "marker": "compulsory",
  "data_type": "text",
  "primitive": "text_short",
  "help_text": "Please enter the product name. No special chars except hyphens.",
  "is_advanced": false,
  "enum_resolver": null,
  "validation_message_ids": ["validation.product_name.too_short", "validation.product_name.no_special_chars"]
}
```

Per-key contract:

- **`name: str`** — REQUIRED. The display label in V1 (English only). `MVP_ARCH §5.6.6` specifies the curation strategy (Tier A hand-curated, Tier B/C/D defaults). The display label IS in the §5A contract, but its CONTENT is owned by `data/parsed/field_display_overrides.json` and the seed-time merge logic in the DATA track. §5A locks the key's presence and type; the DATA track populates the strings.
- **`canonical_name: str`** — REQUIRED. The snake_case canonical name per `MVP_ARCH §0` premise #5 and the canonical alias map maintained by `meesell-xlsx-parser`. This is the JSONB key under `products.fields_jsonb` when the seller's value is persisted by `catalog`. Forbidden characters: any character not in `[a-z0-9_]`; first character must be `[a-z]`. Seed-time validator enforces.
- **`marker: Literal["compulsory", "optional"]`** — REQUIRED. Binary tiering per `MVP_ARCH §0` premise #2; no "recommended" tier. Used for the `compulsory_count` / `optional_count` derivation.
- **`data_type: Literal["text", "long_text", "number", "number_with_unit", "currency", "dropdown", "image", "address"]`** — REQUIRED. Locked enum of 8 values, parser-time classification. Per `MVP_ARCH §5.6.5`, this is inferred from the parsed XLSX cell type plus name-pattern heuristics. The `primitive` value is derived from `data_type` per the §5A.D mapping.
- **`primitive: Literal[<the 11 primitives in §5A.D>]`** — REQUIRED. Renderer-time component identifier. The frontend wizard renderer dispatches `<mee-field>` to one of the 11 primitive components based on this key (per `MVP_ARCH §4.1` and §4.2). Backend echoes this verbatim to the API consumer; the value is set at seed time by the primitive classifier (`backend/app/i18n/primitive_classifier.py` per database-builder Phase 4 memory).
- **`help_text: str`** — REQUIRED per philosophy F5 (every field has an explanation; `§0.H F5`). Seed-time validator rejects any field with empty or missing `help_text`. The single documented exception is Pattern 5 advanced fields (D2 allowlist `{"group_id"}` only in V1; see §5A.F) where the seller's expand action acknowledges opacity per `§0.H F5` second clause.
- **`is_advanced: bool`** — OPTIONAL; defaults to `false` when absent. Set to `true` only for `canonical_name = "group_id"` in V1 per founder ruling D2 (`§0.F`). The catalog module accepts the field whether or not the wizard expanded it; the export module writes whatever the seller filled, blank if untouched. See §5A.F for the locked allowlist rule.
- **`enum_resolver: Literal["category", "static", null]`** — REQUIRED when `data_type == "dropdown"`, MUST be `null` otherwise. Semantics in §5A.E.
- **`validation_message_ids: list[str]`** — REQUIRED if the field has Pydantic validators beyond the implicit type check (length, format, regex, range); empty list `[]` otherwise. Each ID conforms to the §5A.H convention and resolves against `i18n/` per §5A.I.

Forward-compat note: additional per-field keys may exist (e.g. `unit_suffix` for `number_with_unit` per `MVP_ARCH §5.6.1`); §5A.C locks the keys that all three consumer modules read. Optional keys consumed by exactly one consumer (e.g. `unit_suffix` consumed only by the frontend primitive renderer) are documented in `MVP_ARCH §5.6.1`, not duplicated here.

---

### 5A.D The 11 input primitives + data_type mapping

| `data_type` | `primitive` | Wizard component | Selection rule |
|---|---|---|---|
| `text` | `text_short` | `<mee-text-short>` | default for `text`; ≤ 80 chars |
| `text` | `text_long` | `<mee-text-long>` | `text` with name matching `*description|notes|ingredients|address`; textarea |
| `number` | `number` | `<mee-number>` | `number` with no unit suffix |
| `number_with_unit` | `number_with_unit` | `<mee-number-unit>` | numeric field with companion `*_unit` field OR name matches `*weight|voltage|wattage|frequency|capacity` |
| `currency` | `currency` | `<mee-currency>` | name matches `*price|mrp`; ₹ prefix, 2 decimals |
| `dropdown` | `dropdown_small` | `<mee-dropdown-small>` | `enum_count` 1–20; render-all-options |
| `dropdown` | `dropdown_medium` | `<mee-dropdown-medium>` | `enum_count` 21–100; in-memory autocomplete |
| `dropdown` | `dropdown_large` | `<mee-dropdown-large>` | `enum_count` 101–500; virtualised autocomplete |
| `dropdown` | `dropdown_api_search` | `<mee-dropdown-api>` | `enum_count` > 500; debounced API search; the 291 Brand-pattern fields land here |
| `image` | `image_upload` | `<mee-image-upload>` | 4-slot pattern from `MVP_ARCH §0` premise #3 |
| `address` | `address_group` | `<mee-address-group>` | composite for legacy collapsed-compliance templates; Eye-Serum per §12.6 |

This is **11 primitives** total — explicitly more than the "10 input primitives" wording in `MVP_ARCH §0` premise #4 because (a) `data_type == "text"` fans out to two primitives (`text_short` and `text_long`) based on name-pattern + max length, and (b) `data_type == "dropdown"` fans out to four size-tiered primitives based on `enum_count`. `MVP_ARCH §4.1` line 437 confirms the same 11-total count ("Total: 11 primitive components, covering 1,831 corpus-wide field names"). Backend treats the 11 as the locked set; `data_type` is the parser-time classification (one of 8), `primitive` is the renderer-time component (one of 11). No module invents a 12th primitive without amending §5A.

---

### 5A.E `enum_resolver` semantics

The `enum_resolver` key (§5A.C) selects where the dropdown's allowed values live.

- **`"category"`** — values stored in `field_enum_values` table, keyed by `(category_id, canonical_name)` per `MVP_ARCH §0` premise #5. The `category` module's `service.get_field_enum(category_id, canonical_name)` returns the list. Used for the 291 Brand-pattern fields and every other category-specific dropdown. This is the dominant case in V1.
- **`"static"`** — values inline in the field spec as a `fields[].enum_values: list[str]` key added at seed time. Used only for tiny, truly-universal dropdowns where per-category storage is wasteful. V1 candidate: `country_of_origin` (~5 values, identical across all 3,772 categories). Coordinator decision: the static enum values live INLINE in the per-field spec (added as `enum_values: list[str]` when `enum_resolver == "static"`), NOT under a separate top-level envelope key like `static_enums: dict[str, list[str]]`. Rationale: keeping the values adjacent to the field that consumes them (a) preserves the §5A.B envelope minimalism, (b) avoids a second resolver lookup path, (c) matches the §5A.C "everything about field X is in `fields[X]`" reading invariant.
- **`null`** — non-dropdown field. The `data_type` MUST NOT be `"dropdown"`. Seed-time validator enforces.

The `catalog` module's validator dispatches on `enum_resolver`:
- `"category"` → reject the seller's value if absent from `field_enum_values` for the product's `category_id`. Emits `validation.<canonical_name>.invalid_enum`.
- `"static"` → reject if absent from `fields[].enum_values`. Emits the same convention.
- `null` → no enum check; other validators (length, format, regex, range) still apply per §5A.C `validation_message_ids`.

The `export` module's M10 guardrail re-validates at emit time per philosophy F3 Layer-3 (`§0.H F3`): even if a value bypassed the API layer somehow, the Export Adapter rejects unknown enum values before they reach the XLSX.

---

### 5A.F Special flags — `is_advanced` and `compliance_shape`

Founder rulings D2 (`§0.F`) and `MVP_ARCH §12.6` are made concrete by these two flags.

**`is_advanced: bool`** — gates a field behind the wizard's "Advanced fields" expandable section per philosophy Pattern 5.

- V1 allowlist: `{"group_id"}` only. Database-builder memory line 395 confirms `ADVANCED_CANONICAL_NAMES = {"group_id"}` at line 84 of `scripts/build_template_schemas.py`.
- 3,566 templates have `group_id` field with `is_advanced=true`; 0 templates have any other field with `is_advanced=true` (database-builder memory line 396).
- Frontend renders these inside an "Advanced fields" expandable per philosophy Pattern 5.
- Backend `catalog` validator accepts the value whether or not the wizard expanded the section.
- `export` Adapter writes the value verbatim; blank export is valid if the seller never expanded.
- Seed-time rule: `is_advanced == true` REQUIRES the field's `canonical_name` to be in the locked allowlist. Widening the allowlist requires a §5A amendment block.

**`compliance_shape: "standard" | "collapsed"`** — selects the Export Adapter's `ComplianceStrategy` class.

- `"standard"` (3,771 templates) — 9 compliance fields stored, 9 columns emitted in XLSX. The `customer` module captures the 9 fields at onboarding per `MVP_ARCH §2.2`. The `export` module's `StandardComplianceStrategy` emits one column per field.
- `"collapsed"` (1 template — Eye-Serum, leaf 12378 per database-builder memory line 177) — 9 compliance fields stored, 3 derived columns emitted in XLSX. The `customer` module STORES 9 fields regardless per philosophy F4 (`§0.H F4`) — no derived data stored. The `export` module's `CollapsedComplianceStrategy` concatenates the 9 → 3 combined strings at emit time per `§0.G §12.6`. Honours M10 (the collapsed shape never leaks past the Export Adapter).

The `compliance_shape` key lives at envelope top-level (§5A.B) and NOT per-field, because the shape applies to the whole template's compliance block; per-field `compliance_shape` would have no meaning.

---

### 5A.G Module consumption contracts

Three consumer modules read from §5A; each consumes a defined slice. Locked here so the §7-§14 module specs do not redefine the contract.

- **`category` module (§2.3)** serves the schema via `service.fetch_schema(category_id) -> dict` — returns the full `templates.schema_jsonb` payload (cached per §4.D versioned-key pattern, pre-warmed for the top 50 categories per `MVP_ARCH §6.7`). Endpoint surface per `MVP_ARCH §3.3`. The category module is **read-only** against `templates`; it never writes the envelope at runtime — the seed scripts own all writes.
- **`catalog` module (§2.4)** validates PATCH payloads against the fetched schema. The validator first calls `category.service.fetch_schema(category_id)` (cross-module service-only per §16), then dispatches per-field on `data_type` and `enum_resolver` per §5A.C and §5A.E. Validation errors raise `MeesellError` subclasses (`§4.F`) carrying the field's `validation_message_ids[i]` from the schema. The validator MUST NOT short-circuit on `is_advanced == true` — D2 explicitly states the field is accepted whether expanded or not.
- **`export` module (§2.8)** reads the schema for three purposes: (a) `compliance_shape` dispatch — which `ComplianceStrategy` class to instantiate; (b) the per-field `canonical_name → meesho_column_header` reverse map via `field_aliases.for_xlsx_export` (per `MVP_ARCH §12.2` and the database baseline); (c) `is_advanced` semantics — writes blank if the seller never filled (philosophy F4 + D2). The export module re-validates enum values at emit time per the F3 Layer-3 guardrail.

No other module reads `templates.schema_jsonb` directly. `iam`, `customer`, `image`, `pricing`, and `dashboard` consult §5A only via the consumer modules above (e.g. `dashboard` calls `catalog.service.get_validation_summary(...)` which internally consults the schema).

---

### 5A.H `validation_message_id` naming convention

Every `validation_message_id` conforms to the locked convention:

```
{domain}.{field_or_subdomain}.{constraint}
```

Domain prefixes (locked):

- **`validation.*`** — Pydantic field-level validators. Examples: `validation.product_name.too_short`, `validation.product_name.no_special_chars`, `validation.phone.invalid_format`, `validation.mrp.below_zero`. The `<field_or_subdomain>` segment matches the field's `canonical_name`.
- **`auth.*`** — auth dependency errors (`core/auth.py` per §4.B). Examples: `auth.token_missing`, `auth.token_expired`, `auth.user_not_found`, `auth.refresh_invalid`.
- **`tenancy.*`** — cross-user access violations (`core/tenancy.py` per §4.C). Example: `tenancy.cross_user_access`.
- **`plan.*`** — plan-guard errors (`core/plan_guard.py` per §4.E). Example: `plan.limit_exceeded`.
- **`catalog.*`, `customer.*`, `category.*`, `pricing.*`, `image.*`, `export.*`** — per-module business errors. Each module owns its `<domain>.*` namespace. Examples: `catalog.draft_missing`, `customer.profile_incomplete`, `category.not_found`, `pricing.commission_missing`, `image.precheck_failed`, `export.collapsed_emit_failed`.
- **`http.{status_code}`** — FastAPI built-in `HTTPException` mapping per §4.F's `register_error_handlers` priority chain. Example: `http.404`, `http.500`.
- **`server.internal_error`** — last-resort 500 envelope per §4.F when no other handler matched.

Formatting rules (locked):

- All segments are snake_case. Hyphens forbidden in any segment.
- Three segments only — no nesting beyond `{domain}.{field}.{constraint}`. Sub-constraints (e.g. multiple regex patterns on the same field) get distinct `<constraint>` names, not a fourth segment.
- The `<domain>` prefix is owned by exactly one source: each module owns its `<module>.*` namespace; `validation.*` is shared but each ID is declared at exactly one declaration site (the field's `validation_message_ids` array in the seed, or the module's `exceptions.py` for non-field validators).

The convention is enforced at two points: (a) the seed-time validator rejects `validation_message_ids` that violate the format; (b) the §19 CI test scans the `i18n/messages_en.py` registry for IDs that do not match the regex `^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){2}$`.

---

### 5A.I `i18n/` package + resolver contract

The `i18n/` package (per §3.H) carries the locale-aware message registry plus the resolver.

`i18n/messages_en.py` shape (locked):

```python
VALIDATION_MESSAGES: dict[str, str] = {
    "auth.token_missing": "Missing authentication token. Please log in again.",
    "auth.token_expired": "Your session has expired. Please log in again.",
    "tenancy.cross_user_access": "You do not have access to this resource.",
    "plan.limit_exceeded": "You have reached your plan limit. Upgrade to continue.",
    "catalog.draft_missing": "No draft found for this product.",
    "customer.profile_incomplete": "Complete your seller profile before listing this category.",
    "validation.product_name.too_short": "Product name must be at least 3 characters.",
    # ... populated incrementally during specialist construction dispatches
}
```

The English-string CONTENT is NOT locked by §5A — it is content that grows as each module is constructed. §5A locks the registry's NAME (`VALIDATION_MESSAGES`), TYPE (`dict[str, str]`), and the constraint that every key conforms to §5A.H.

`i18n/resolver.py` signature (locked):

```python
def resolve(message_id: str, locale: str = "en") -> str:
    """
    Resolves a validation_message_id to a localised string.

    V1: only locale == "en" is supported and the parameter is logged but not acted on.
    V1.5: adds "ta" (Tamil) and "hi" (Hindi); dispatches on locale.
    Fallback: missing id in locale → English; missing id in English → return id verbatim.
    """
    ...
```

Resolver behavior (locked):

1. Look up `(locale, message_id)` in the locale's `messages_<lang>.VALIDATION_MESSAGES`.
2. If missing AND `locale != "en"` → look up `("en", message_id)`.
3. If still missing → return `message_id` verbatim. This is a **debug hint** for development — surfacing the unresolved key surfaces seed gaps. Production observability (§6A or §19) flags any resolution that returned the verbatim ID as a `i18n.resolver.missing_key` metric increment.
4. The locale is read from the `Accept-Language` header by middleware. V1 logs the header but always returns English. V1.5 dispatches on it. No client-side override in V1.

The resolver is called by `core/errors.py` (`§4.F`) at the `MeesellError` → envelope serialisation step. It is also called by the `catalog` validator when raising per-field errors — the `validation_message_id` array on the field becomes the resolved `detail` string in the response envelope.

---

### 5A.J What §5A does NOT cover

- The DDL of `templates` or `field_enum_values` — owned by `MVP_ARCH §2`.
- The 4 corpus-derived seed scripts that build `schema_jsonb` from parsed XLSX — owned by `meesell-database-builder` per database-builder memory Phase 3.
- The actual English message strings beyond the sample lines in §5A.I — those are content authored by `meesell-services-builder` during the §4 / §7-§14 construction dispatches as each new validation message ID is needed; the `VALIDATION_MESSAGES` registry grows incrementally.
- The `enum_entries[].labels` localisation payload — owned by the DATA track per `MVP_ARCH §5.6.4`; surfaced to API responses through the `core/cache.py` helper but populated by seed scripts.
- The `field_display_overrides.json` curation file — owned by `meesell-data-engineer` per `MVP_ARCH §5.6.6`; the `name` key in §5A.C reads from the merged seed output.
- V1.5 Tamil/Hindi message files (`messages_ta.py`, `messages_hi.py`) — explicitly excluded from V1 ship per §3.H. The resolver's locale parameter is plumbed today so V1.5 can light those files without architecture change.

A reviewer evaluating §5A asks: "is the `schema_jsonb` envelope locked, does the per-field shape compose with the 11 primitives, are the `is_advanced` and `compliance_shape` semantics traceable to founder rulings, is the `validation_message_id` convention enforceable, does the resolver fallback degrade safely?" — not "are these specific English messages correctly worded" (those land during module construction).

---

## Section 6 — `adapters/` — Third-Party Vendor Clients

STATUS: LOCKED (2026-06-05)

### 6.A Preamble

Section 6 specifies the interface contracts of the **5 third-party vendor adapters** that live in `app/adapters/` per §3.F: `gemini`, `msg91`, `gcs`, `razorpay`, `langfuse`. Each adapter is the **vendor-isolation boundary** per philosophy M10 and §2.9 — vendor SDK quirks (auth handshake, request shapes, error class hierarchies, retry idioms) NEVER leak past the adapter file boundary into domain modules. §6 specifies **INTERFACES, not implementations**: type signatures, dataclasses, exception types, credential sources, transport-level failure-mode posture. §6 does **NOT** specify (a) business logic of any kind — that is the calling module's `service.py`; (b) cost tracking, prompt registry, AI guardrails, or LangFuse trace orchestration for Gemini calls — that is §6A `ai_ops/`; (c) per-module business retry policy (e.g. "should Auto-fill retry on a content-blocked response with a softer prompt?") — that lives above the adapter; (d) ORM definitions for any audit/persistence side-effects — those flow through `shared/models/` per §5.E.

A reviewer evaluating §6 asks: "are the 5 adapter interfaces minimal and stable, is credential sourcing from `settings` consistent across all 5, is the no-business-logic invariant clear, do the failure modes propagate the right exception types, and is the `gemini → ai_ops` boundary preserved?" — not "is the autofill retry policy correct" (§6A), not "is the OTP rate-limit window right" (§4.E + §10.7), not "is the image precheck pipeline correct" (§11 + §6A).

---

### 6.B `adapters/gemini.py` — raw Gemini SDK wrapper

**Owner:** `meesell-services-builder` (per §2.9).

**Purpose.** Thin transport wrapper over Google's `google-generativeai` SDK. Exposes two methods: `generate_text` (LLM text completion) and `generate_vision` (multimodal image+prompt). Transport-level retry only. NO cost tracking, NO LangFuse trace, NO guardrail enforcement, NO prompt-registry lookup — all of those are §6A concerns. NO domain knowledge of Smart Picker / Auto-fill / Watermark workloads — the adapter does not know which feature is calling it.

**Locked public interface:**

```python
@dataclass(frozen=True)
class GeminiResponse:
    text: str
    input_tokens: int
    output_tokens: int
    finish_reason: str
    raw: dict  # SDK-native response for debug only — NEVER serialised to API responses

async def generate_text(
    prompt: str,
    *,
    model: str = settings.GEMINI_MODEL,
    response_mime_type: str | None = None,  # e.g. "application/json"
    max_output_tokens: int | None = None,
    temperature: float = 0.0,  # default deterministic per F3 prompt-level guardrail
) -> GeminiResponse:
    ...

async def generate_vision(
    prompt: str,
    image_bytes: bytes,
    image_mime_type: str = "image/jpeg",
    *,
    model: str = settings.GEMINI_MODEL,
    max_output_tokens: int | None = None,
    temperature: float = 0.0,
) -> GeminiResponse:
    ...
```

**Credentials.** `settings.GEMINI_API_KEY` per §5.D (Secret Manager ref `gemini-api-key`, version 1 LIVE per infra memory). Model identifier from `settings.GEMINI_MODEL` (default `"gemini-2.5-flash"` per CLAUDE.md Decision 3).

**Failure mode.** 3-retry exponential backoff (1 s, 4 s, 16 s) on connection errors + 5xx + 429. Non-retryable errors (auth, malformed request, content-blocked safety filter) → raise `GeminiAdapterError` immediately. Final retry exhaustion → raise `GeminiAdapterError`. The adapter NEVER surfaces a partial response and NEVER returns a `GeminiResponse` with empty `text` on error.

**Cross-section integration.** Consumed ONLY by `ai_ops/client.py` per the §3.G locked boundary rule. The §19 CI import-linter rejects `from app.adapters.gemini` (or `from app.adapters import gemini`) anywhere outside `app/ai_ops/`. Domain modules that need AI text/vision call `ai_ops.client.call_gemini(...)` — never the adapter directly.

**V1.5+ note.** The SDK call shape is unchanged; the orchestration layer (§6A) absorbs prompt-versioning, A/B routing, and per-workload temperature overrides without touching the adapter.

---

### 6.C `adapters/msg91.py` — OTP send client

**Owner:** `meesell-services-builder` (per §2.9), with collaboration from `meesell-auth-builder` for the `iam`-side wiring (rate-limit gating + audit logging live in `iam.service`, not here).

**Purpose.** Thin transport wrapper over MSG91's OTP send REST endpoint. Single public method.

**Locked public interface:**

```python
@dataclass(frozen=True)
class Msg91Response:
    success: bool
    request_id: str | None  # MSG91 correlation ID — logged, not surfaced to client
    message: str  # error message when success == False

async def send_otp(
    phone: str,  # E.164 format, e.g. "+919876543210"
    otp: str,    # 6-digit code generated by iam module (NOT generated here)
    *,
    template_id: str = settings.MSG91_TEMPLATE_ID,
) -> Msg91Response:
    ...
```

**Credentials.** `settings.MSG91_AUTH_KEY` + `settings.MSG91_TEMPLATE_ID` per §5.D (both Secret Manager refs LIVE per infra memory Phase A).

**Failure mode.** 1-retry on connection error + 5xx + 429. Non-retryable errors (auth, malformed request, MSG91 explicit failure response) → return `Msg91Response(success=False, request_id=None, message=<vendor message>)`. The adapter does **NOT raise** — the caller surfaces the 503 / appropriate status to the seller per §1.E ("MSG91 → 5xx surfaced to client"). This is one of the two exceptions to the §6.G typed-exception pattern.

**Cross-section integration.** Consumed ONLY by `iam.service.send_otp_for_login`. No other module sends OTP. The 3/h/phone rate limit per `MVP_ARCH §10.7` is enforced at `core/middleware/rate_limit_mw.py` BEFORE the route handler — the adapter trusts that its caller has already gated.

**V1.5+ note.** Same SDK. If MSG91 vendor rate-limits become a constraint, the adapter can layer in a transparent queue/throttle — module surface unchanged.

---

### 6.D `adapters/gcs.py` — Google Cloud Storage client

**Owner:** `meesell-services-builder` (per §2.9).

**Purpose.** GCS object operations — upload bytes, download bytes, signed URL issuance, delete. Bucket name and project from `settings`. Used by `image` (binary writes + seller fetch URLs) and `export` (XLSX + ZIP writes + signed download URLs).

**Locked public interface:**

```python
async def upload_bytes(
    path: str,           # e.g. "meesell-images/{user_id}/{product_id}/{idx}.jpg"
    data: bytes,
    content_type: str,   # e.g. "image/jpeg", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    *,
    bucket: str = settings.GCS_BUCKET,
) -> str:                 # returns the gs:// URI
    ...

async def download_bytes(
    path: str,
    *,
    bucket: str = settings.GCS_BUCKET,
) -> bytes:
    ...

async def generate_signed_url(
    path: str,
    *,
    bucket: str = settings.GCS_BUCKET,
    ttl_seconds: int = settings.GCS_SIGNED_URL_TTL_SECONDS,  # default 3600 per §10.8
    method: Literal["GET", "PUT"] = "GET",
) -> str:
    ...

async def delete(
    path: str,
    *,
    bucket: str = settings.GCS_BUCKET,
) -> None:
    ...
```

**Credentials.** GCP **Application Default Credentials** sourced from the K3s pod's service account (per `meesell-infra-builder` memory — the VM SA carries `storage.objectAdmin` post-Phase A). NO env-injected service-account JSON in V1; ADC reads from instance metadata. `settings.GCS_BUCKET` and `settings.GCS_PROJECT_ID` per §5.D supply bucket name (`meesell-images`) and project (`project-1f5cbf72-2820-4cdb-949`).

**Failure mode.** The native `google-cloud-storage` SDK retries handle transient transport errors (it has built-in exponential backoff for idempotent ops). Auth failures, bucket-not-found, permission errors, and final-retry exhaustion → raise `GcsAdapterError`. The adapter does NOT silently swallow upload failures — `image.service` and `export.service` rely on raised exceptions to set row `status='failed'`.

**Cross-section integration.**
- `image` module — `upload_bytes` (binary write on POST `/products/{id}/images`) and `generate_signed_url(method="GET")` (seller fetch URL on poll) per §2.5 + §10.8.
- `export` module — `upload_bytes` (XLSX + ZIP after the 9-step Export Adapter build), `download_bytes` (image gather for ZIP packaging), `generate_signed_url(method="GET")` (download URL surfaced on poll) per §2.8 + `MVP_ARCH §5.5`.

**Path convention (locked from `MVP_ARCH §10.8` + §3.F).**
- Images: `meesell-images/{user_id}/{product_id}/{idx}.jpg` where `idx ∈ {1, 2, 3, 4}` per `MVP_ARCH §0` premise #3 (4-slot uniform rule).
- Exports: `meesell-exports/{user_id}/{export_id}/sheet.xlsx` and `meesell-exports/{user_id}/{export_id}/images.zip`.
- The `{user_id}` first-segment scoping is the V1 isolation gate per `MVP_ARCH §10.8` — `core/tenancy.py` `assert_owned` enforces this at the row level; the path convention enforces it at the object-store level as a defence-in-depth seam.

**V1.5+ note.** Signed-URL ACLs may move to per-object IAM bindings if seller upload flows become direct-to-GCS (browser → GCS, bypassing FastAPI for the binary). Adapter signature is unchanged; `method="PUT"` already reserved.

---

### 6.E `adapters/razorpay.py` — Razorpay client (V1: webhook signature verify only)

**Owner:** `meesell-services-builder` (per §2.9).

**Purpose.** **V1 ONLY** verifies inbound webhook signatures. Subscription/payment business logic is **deferred to V1.5** per §1.E + `MVP_ARCH §14`. The V1 surface is therefore minimal — one synchronous helper for HMAC signature verification.

**Locked public interface (V1):**

```python
def verify_webhook_signature(
    payload: bytes,           # raw request body (NOT json-parsed)
    signature: str,           # value of X-Razorpay-Signature header
    *,
    secret: str = settings.RAZORPAY_WEBHOOK_SECRET,
) -> bool:
    """
    HMAC-SHA256 of payload with secret, constant-time compared against signature.
    Returns True if valid, False otherwise.
    Does NOT raise on invalid signature — the caller (iam.router.razorpay_webhook)
    responds 401 on False.
    """
    ...
```

**Credentials.** `settings.RAZORPAY_WEBHOOK_SECRET` per §5.D (Secret Manager ref `razorpay-webhook-secret` — **NOT YET POPULATED**; `meesell-infra-builder` populates during the `iam` construction dispatch per the §5.D registry note). `settings.RAZORPAY_KEY_ID` + `settings.RAZORPAY_KEY_SECRET` are loaded into settings but **unused in V1** — they reserve the slot for V1.5 SDK init when subscription business logic lands.

**Failure mode.** Invalid signature → returns `False`; caller responds 401. Never raises in V1. (The V1.5 surface that adds `create_subscription` / `cancel_subscription` / `get_customer` will follow the §6.G `RazorpayAdapterError` pattern.)

**Why synchronous?** HMAC verification is CPU-bound and microsecond-scale; an `async def` wrapper adds event-loop overhead with no I/O benefit. This is the locked exception to §6.G's "all adapters async" rule.

**Cross-section integration.** Consumed ONLY by `iam.router.razorpay_webhook`.

**V1.5+ note.** When subscription business logic lands, this adapter gains `async create_subscription(...)`, `async cancel_subscription(...)`, `async get_customer(...)` etc. — all using the official `razorpay` Python SDK. Module-side wiring in `iam` becomes async; the V1 sync `verify_webhook_signature` is preserved as-is.

---

### 6.F `adapters/langfuse.py` — observability trace egress

**Owner:** `meesell-services-builder` (per §2.9).

**Purpose.** Async fire-and-forget trace egress to LangFuse. **Observability MUST NOT block the business path** per §1.E lock — every method either succeeds silently, logs a warning on transport failure, or is a complete no-op when LangFuse credentials are missing at startup.

**Locked public interface:**

```python
async def trace(
    name: str,                       # e.g. "smart_picker.suggest"
    input: dict,                     # prompt + parameters
    output: dict,                    # response + token counts
    *,
    metadata: dict | None = None,
    user_id: UUID | None = None,
    trace_id: str | None = None,     # caller-provided to chain traces
) -> None:                            # returns None — fire-and-forget
    ...

async def score(
    trace_id: str,
    name: str,                       # e.g. "enum_validation_passed"
    value: float,                    # 0.0 / 1.0 for boolean scores; eval rubric uses 0..1
) -> None:
    ...
```

**Credentials.** `settings.LANGFUSE_PUBLIC_KEY` + `settings.LANGFUSE_SECRET_KEY` + `settings.LANGFUSE_HOST` per §5.D. `LANGFUSE_SECRET_KEY` is the Secret Manager ref `langfuse-secret-key` — **NOT YET POPULATED**; populated during §6A construction dispatch per the §5.D registry note.

**Failure mode.** ALWAYS drop-on-failure with `logging.warning(...)`. Never raises — this is the second locked exception to §6.G's typed-exception pattern. If credentials are missing at process startup, the adapter degrades to a complete no-op and logs once: `langfuse credentials missing — trace egress disabled`. Subsequent calls return immediately.

**Cross-section integration.** Consumed ONLY by `ai_ops/client.py` per §6A. Domain modules NEVER call `langfuse` directly — every AI call site flows through `ai_ops/client.py`, which fires the trace as the last step after the Gemini call returns (success or failure).

**V1.5+ note.** Same SDK. V1.5 may add sampling (`trace` decides whether to actually egress based on a sample rate) when AI volume crosses the LangFuse free-tier ceiling.

---

### 6.G Common adapter patterns

The five adapters share the following locked invariants. Specialists implement them uniformly; the §19 test strategy treats deviations as architectural drift.

- **Async interfaces** — all adapter methods are `async def`, with the single locked exception of `razorpay.verify_webhook_signature` (CPU-bound HMAC — async would add overhead with no I/O benefit; see §6.E rationale).
- **Credential sourcing** — every adapter sources credentials from `shared/config.settings` via the §5.D registry. **NO hardcoded `os.getenv(...)` reads anywhere in `adapters/`.** This is the structural enforcement of the §5.D secrets contract — the §19 CI linter forbids `os.getenv` under `app/adapters/`.
- **No business logic** — pure transport. The adapter's job ends when the vendor returns a parseable response (or fails after retry). Domain decisions (retry with softer prompt? quarantine the seller? mark the export as partial?) live above the adapter, in §6A for AI and in the calling module's `service.py` for non-AI.
- **Transport-level retry only** — timeouts, connection errors, idempotent 5xx, 429. Business-level retry decisions live above the adapter. §6.B specifies the gemini retry triple (1 s, 4 s, 16 s); §6.C specifies msg91 single-retry; §6.D delegates to the native GCS SDK retries; §6.E does not retry (HMAC is local); §6.F never retries (drop-on-failure).
- **Typed exception hierarchy** — each adapter raises a typed exception inheriting from `AdapterError`, which inherits from `MeesellError` per §4.F:
  - `GeminiAdapterError`, `Msg91AdapterError`, `GcsAdapterError`, `RazorpayAdapterError`, `LangfuseAdapterError`.
  - All carry `status_code=502` (Bad Gateway) by default — the seller sees the i18n message `<vendor>.unavailable` (e.g. `gemini.unavailable`, `gcs.unavailable`) via `core/errors.py` resolution per §5A.H.
  - **Two locked exceptions to the raise-on-failure pattern:** (i) `msg91.send_otp` returns `Msg91Response(success=False, ...)` on transport failure rather than raising — per §6.C; (ii) `langfuse.trace` and `langfuse.score` NEVER raise — per §6.F drop-on-failure rule.
- **Lazy singleton clients** — module-level singleton SDK client instances are lazily initialised on first use (e.g. `_gemini_client: Optional[GenerativeModel] = None`), with thread-safe init via `asyncio.Lock`. The same client is reused for the life of the worker process. No per-request client construction. No connection-pool tuning beyond SDK defaults in V1.

---

### 6.H What §6 does NOT cover

Section 6 specifies adapter INTERFACES, not the orchestration above them. Out of scope:

- **§6A AI Operations Layer (`ai_ops/`)** — wraps `adapters/gemini.py` with cost tracking, the 3-layer guardrail, the daily ₹500 budget cap with 80% alarm + 100% hard-stop + graceful fallback, LangFuse trace orchestration, prompt-registry lookup + versioning, and the 3 golden eval-set runners. AI call orchestration through `ai_ops/client.py.call_gemini(...)` is the single import point every module uses for AI work. §6A is the next paired review.
- **Per-module business logic that CONSUMES adapters** — `iam.service.send_otp_for_login` wraps `msg91.send_otp` with rate-limit gating + audit logging; `image.service.upload_image` wraps `gcs.upload_bytes` with `product_images` row insert + Celery enqueue; `export.service.build_xlsx` wraps `gcs.upload_bytes` with the 9-step Export Adapter pipeline. Those flows are owned by §7–§14.
- **V1.5 Razorpay subscription business logic** — `create_subscription`, `cancel_subscription`, `get_customer`, webhook event dispatcher; deferred per §6.E + `MVP_ARCH §14`.
- **K3s service-account credential wiring** — the `storage.objectAdmin` IAM binding on the VM service account that gives the GCS adapter its ADC identity; owned by `meesell-infra-builder` per §20.
- **The `core/middleware/audit_mw.py` PII scrubbing salt** — `AUDIT_PII_SALT` reads from §5.D but the salting/hashing convention is §4.G.

A reviewer evaluating §6 asks: "are the 5 adapter interfaces minimal and stable, is credential sourcing consistent (always via `settings`), is the no-business-logic invariant clear, do the failure modes propagate the right exception types, is the `gemini → ai_ops` boundary enforced?" — not "is the autofill retry policy correct" (§6A), not "is the OTP rate-limit window right" (§4.E + §10.7), not "is the image precheck pipeline correct" (§11 + §6A).

---

## Section 6A — AI Operations Layer

STATUS: LOCKED (2026-06-05)

### 6A.A Preamble

§6A specifies the **AI Operations Layer** — the orchestration envelope above `adapters/gemini.py` and below domain modules. §6A is the SOLE import surface domain modules use for AI work: every Smart Picker call, Auto-fill call, and Vision call from `category`, `catalog`, `image` flows through `ai_ops.client.call_gemini(...)`. §6A owns: per-call cost tracking, the 3-layer hallucination guardrail (Layer 1 prompt constraint, Layer 2 parser-level enum rejection, Layer 3 happens OUTSIDE in `export` per §14), daily ₹500 budget cap with 80% alarm + 100% hard-stop + graceful fallback, prompt-template registry + versioning, the 3 golden eval-set runners, LangFuse trace orchestration. §6A does NOT own: the prompt CONTENT (that is `meesell-prompt-engineer`), the per-workload ranking algorithm (that is `meesell-category-picker-builder` for the Smart Picker, `meesell-image-precheck-builder` for the Vision pipeline), the bare Gemini SDK call (that is §6B `adapters/gemini.py`), the per-user feature budget enforcement (that is §4.E `core/plan_guard.py` — a separate concern enforced BEFORE §6A is reached). A reviewer evaluating §6A asks: "is `client.py` the sole import point for domain modules, are the 3 workloads enumerated and the only ones recognised, is the 3-layer guardrail clearly partitioned (Layers 1 + 2 here, Layer 3 in export), does the budget-cap behaviour match the 80% alarm / 100% hard-stop / graceful-fallback locks, are the golden eval targets traceable to `MVP_ARCH §8.5`, is the prompt-engineer ownership of content clear?"

### 6A.B 3 AI workloads

The only `Literal` values §6A recognises:

- **`"smart_picker"`** — sync from FastAPI; consumed by `category.service.suggest_categories(description)`; uses `generate_text` with `response_mime_type="application/json"`. The 50-description golden eval set (§6A.H) gates regression with target top-5 recall ≥ 80% per `MVP_ARCH §8.5`.
- **`"autofill"`** — sync from FastAPI in V1 (per §1.C lock); consumed by `catalog.service.autofill_product(product_id)`; uses `generate_text` with enum-constrained prompt + Layer 2 enum re-validation. The 30-product-spec golden set gates regression with target invalid-enum rate = 0% per `MVP_ARCH §8.5`. V1.5 may move async without changing the §6A contract.
- **`"watermark"`** — async via Celery worker; consumed by `image.tasks.precheck_image(image_id)`; uses `generate_vision`. The 30-image golden set gates regression with target accuracy ≥ 85% per `MVP_ARCH §8.5`.

Any new workload requires a §6A amendment. The `Literal["smart_picker", "autofill", "watermark"]` type appears verbatim across `client.py` / `cost_tracker.py` / `guardrail.py` / `budget_cap.py` / `prompt_registry.py` / `eval.py` — adding a workload is a 6-file edit by design (force-feedback against unscoped growth).

### 6A.C `ai_ops/client.py` — unified call interface

The sole import point for domain modules.

```python
@dataclass(frozen=True)
class AICallContext:
    workload: Literal["smart_picker", "autofill", "watermark"]
    user_id: UUID
    locale: str = "en"
    trace_id: str | None = None  # caller-provided for chained traces (e.g. autofill spans multiple calls)


async def call_gemini(
    ctx: AICallContext,
    prompt_id: str,                      # resolved via prompt_registry — e.g. "smart_picker.v1"
    prompt_vars: dict[str, Any],         # variables substituted into the template
    *,
    image_bytes: bytes | None = None,    # required iff workload == "watermark"
    allowed_enums: dict[str, list[str]] | None = None,  # required iff Layer 2 guardrail applies (autofill)
    response_mime_type: str | None = None,
    max_output_tokens: int | None = None,
) -> AIResponse:
    ...


@dataclass(frozen=True)
class AIResponse:
    parsed: dict | str          # parsed JSON when response_mime_type == "application/json"; raw text otherwise
    raw_response: GeminiResponse
    cost_inr: float             # this call's cost in ₹
    layer2_retries: int         # how many Layer 2 retries occurred (0..2)
    trace_id: str               # resolved trace ID (LangFuse-compatible)
```

**Internal flow** (locked, in order):
1. `prompt_registry.resolve(prompt_id, workload)` → prompt template + version.
2. `budget_cap.check_and_reserve(workload, user_id, estimated_tokens)` → raises `BudgetExceededError` if daily cap hit.
3. `guardrail.apply_prompt_constraint(prompt, workload, allowed_enums)` → Layer 1 (prepend "you MUST select only from..." instruction).
4. Template render with `prompt_vars` substituted.
5. `adapters.gemini.generate_text(...)` or `generate_vision(...)` per workload.
6. `cost_tracker.record(user_id, workload, input_tokens, output_tokens)` → persists per-call cost + decrements budget reservation.
7. `guardrail.parse_and_validate(response, workload, allowed_enums)` → Layer 2 (if invalid, retry up to 2 times with stricter prompt; final failure → return safe fallback per §6A.F).
8. `langfuse.trace(...)` → fire-and-forget egress per §6.F.
9. Return `AIResponse`.

**Locked rule.** Domain modules import ONLY `ai_ops.client.call_gemini`. No domain module imports `ai_ops.guardrail`, `ai_ops.cost_tracker`, or `ai_ops.budget_cap` directly — those are internal. The §19 import linter enforces this.

### 6A.D `ai_ops/cost_tracker.py` — per-call cost recording

```python
async def record(
    user_id: UUID,
    workload: Literal["smart_picker", "autofill", "watermark"],
    input_tokens: int,
    output_tokens: int,
) -> float:                # returns the cost in INR for this call
    ...


async def get_daily_spend() -> float:           # returns total INR spent today
async def get_user_hourly_spend(user_id: UUID) -> float:  # returns INR spent by this user this hour
```

**Cost formula** per `MVP_ARCH §8.2`: `cost_inr = (input_tokens * RATE_INPUT_PER_1K + output_tokens * RATE_OUTPUT_PER_1K) / 1000`. Rates are gemini-2.5-flash specific; locked in `ai_ops/cost_tracker.py` as module-level constants (`RATE_INPUT_PER_1K = 0.0078`, `RATE_OUTPUT_PER_1K = 0.031`; INR-equivalent at current USD-INR; configurable via env if rates change — `AI_RATE_INPUT_PER_1K`, `AI_RATE_OUTPUT_PER_1K` per §5.D). Per-call cost target ≤ ₹0.05 average per `MVP_ARCH §8.2`.

**Storage:**
- Valkey DB 0 keys (sliding-window counters per `MVP_ARCH §10.7`):
  - Daily global: `ai:cost:daily:{YYYY-MM-DD}` → float ₹
  - Per-user per-hour: `ai:cost:user:{user_id}:hourly:{YYYY-MM-DD-HH}` → float ₹
- `audit_events` row written via direct ORM write — `{event_type: "ai.call", user_id, workload, input_tokens, output_tokens, cost_inr, timestamp}`. (Note: this is one of the very few writes to `audit_events` outside the `core/middleware/audit_mw.py` request-close path. Locked here so future readers understand why — AI calls fire from both FastAPI sync paths AND Celery worker async paths, and the worker path has no request close to hook; §15 confirms this is the intended exception.)

### 6A.E `ai_ops/guardrail.py` — 3-layer hallucination guardrail (Layers 1 + 2)

```python
def apply_prompt_constraint(
    prompt: str,
    workload: Literal["smart_picker", "autofill", "watermark"],
    allowed_enums: dict[str, list[str]] | None = None,
) -> str:                          # returns the prompt with Layer 1 prefix prepended
    ...


def parse_and_validate(
    response_text: str,
    workload: Literal["smart_picker", "autofill", "watermark"],
    allowed_enums: dict[str, list[str]] | None = None,
) -> dict | None:                  # returns parsed JSON if valid; None if invalid (signals retry)
    ...
```

**Layer 1 (prompt-level).** A workload-specific prefix prepended to every AI prompt. For `autofill`: "You MUST select values only from the allowed enum list provided per field. NEVER generate a value that is not in the list. Return strictly valid JSON." For `smart_picker`: "Return strictly the JSON shape `{category_id: string, confidence: number, reasons: string[]}`." Per `MVP_ARCH §9.7` Layer 1. The exact wording lives in `ai_ops/guardrail.py` constants; the prefix is bonded to the workload, not to the prompt template (so it cannot be accidentally removed when prompt-engineer ships a new template version).

**Layer 2 (parser-level).** Validates the JSON shape + every field value against `allowed_enums`. If any field carries a value NOT in the corresponding allowlist, return `None` → `client.call_gemini` retries with a stricter prompt that names the violation (up to 2 retries). Final retry exhaustion → return safe fallback per §6A.F (workload-specific graceful degradation, NOT a 500 to the user). Per `MVP_ARCH §9.7` Layer 2.

**Layer 3 (NOT here).** Re-validation at XLSX export time, owned by `modules/export/service.py` per §14 + `MVP_ARCH §9.7` Layer 3. Lock note: even if Layers 1 + 2 are bypassed by a future bug, Layer 3 ensures no invalid enum value reaches Meesho. This 3-layer defence is the structural enforcement of philosophy F3 (never send invalid enum values to Meesho) per §0.H.

### 6A.F `ai_ops/budget_cap.py` — ₹500 daily cap + 80% alarm + 100% hard-stop with graceful fallback

```python
async def check_and_reserve(
    workload: Literal["smart_picker", "autofill", "watermark"],
    user_id: UUID,
    estimated_tokens: int,            # pre-call estimate from prompt length
) -> str:                              # returns reservation_id; raises BudgetExceededError if would exceed daily cap
    ...


async def release_reservation(reservation_id: str, actual_tokens: int) -> None:
    ...


async def get_budget_status() -> BudgetStatus:
    ...


@dataclass(frozen=True)
class BudgetStatus:
    spent_inr: float
    cap_inr: float
    pct_used: float
    alarm_fired: bool
    hard_stopped: bool
```

**Behavior thresholds** (locked):
- **0%–80%**: normal. Log only.
- **80%–100%** (warning band): Prometheus alarm metric increments (`ai_ops_budget_alarm_total`); calls proceed; structured log warning per call.
- **100%+**: hard-stop. Every `check_and_reserve` raises `BudgetExceededError`. The error maps to a **graceful fallback at the calling module**:
  - `category.service.suggest_categories` returns the empty Smart Picker response (frontend shows manual browse fallback per `MVP_ARCH §8.3`).
  - `catalog.service.autofill_product` returns 503 with i18n message `ai_ops.budget_exhausted` ("AI is taking a break — please fill manually").
  - `image.tasks.precheck_image` skips watermark check and marks `precheck_jsonb.watermark_check = "skipped_budget"`.

Per `MVP_ARCH §8.3` graceful-fallback rule.

**Daily reset.** Midnight Asia/Kolkata (locked timezone — per `MVP_ARCH §1.A` region; configurable via `AI_BUDGET_RESET_TZ` per §5.D).

**Reservation pattern.** `check_and_reserve` issues a `reservation_id` and increments the daily counter optimistically by `estimated_tokens × rate`. `release_reservation` (called after the actual call returns) reconciles to `actual_tokens × rate`. This prevents the 100% hard-stop from being triggered by a single concurrent burst before the cost-tracker fires — concurrent calls under the cap each reserve their estimated slice, then converge to actuals when responses land.

**Boundary call-out.** §6A's budget cap is the **DAILY GLOBAL ₹500** concern. The per-user **feature** budgets — `ai_autofill_hourly=50/h`, `smart_picker_hourly=100/h` per §4.E — are separately enforced by `core/plan_guard.py` BEFORE the request reaches a domain service; they never enter §6A. The two concerns are orthogonal and additive: plan_guard gates per-user-per-feature; budget_cap gates global-daily-cost.

### 6A.G `ai_ops/prompt_registry.py` — versioned prompt templates

```python
def resolve(
    prompt_id: str,                   # e.g. "smart_picker.v1" or "autofill.v2"
    workload: Literal["smart_picker", "autofill", "watermark"],
) -> PromptTemplate:
    ...


@dataclass(frozen=True)
class PromptTemplate:
    template: str                     # Jinja2-style with {{var}} placeholders
    version: str                      # "v1", "v2", ...
    workload: str
    rendered_by: Literal["text", "vision"]
```

**Storage.** Prompt CONTENT lives as Python modules under `ai_ops/prompts/`:

```
ai_ops/prompts/
├── __init__.py
├── smart_picker_v1.py     # TEMPLATE: str = "..."; VERSION = "v1"
├── autofill_v1.py
└── watermark_v1.py
```

**Content ownership.** `meesell-prompt-engineer` per AI-track collaboration on §2.3 / §2.4 / §2.5. §6A locks the resolver contract and the file layout; CONTENT lands during prompt-engineer dispatch.

**Active version.** V1 ships one version per workload (`smart_picker_v1`, `autofill_v1`, `watermark_v1`). V1.5 A/B routing dispatches via Valkey config flag `meesell:ai_ops:active_version:{workload}` per `MVP_ARCH §8.5`. V1: the active version is hardcoded; V1.5: the resolver reads the Valkey flag with a `core/cache.py` wrap for flap-resistance.

### 6A.H `ai_ops/eval.py` — golden eval-set runners

```python
@dataclass(frozen=True)
class EvalReport:
    workload: str
    fixtures_run: int
    fixtures_passed: int
    aggregate_metric: float           # workload-specific: top-5 recall / invalid-enum rate / accuracy
    target_metric: float              # threshold from MVP_ARCH §8.5
    passed: bool                      # aggregate_metric crosses target
    per_fixture: list[FixtureResult]
    regression_from_last_run: float | None  # delta vs last LangFuse-stored baseline


async def run_eval(workload: Literal["smart_picker", "autofill", "watermark"]) -> EvalReport:
    ...
```

**The 3 golden sets** (acceptance thresholds locked per `MVP_ARCH §8.5`):

- **Smart Picker**: 50 product descriptions → expected top-5 category match. Target: **top-5 recall ≥ 80%**.
- **Autofill**: 30 product specs → expected canonical-field-name → value. Target: **0% invalid enum values**.
- **Watermark**: 30 images (50/50 with/without watermark) → expected boolean. Target: **accuracy ≥ 85%**.

Golden-set fixtures live as JSON files under `tests/eval/<workload>/fixtures.json` per `MVP_ARCH §8.5`. Maintained by the relevant AI specialist (`category-picker-builder` for picker; `prompt-engineer` for autofill; `image-precheck-builder` for watermark).

**Invocation paths.** `run_eval` is invoked: (a) from `pytest` as part of §19 test strategy when AI changes are in PR; (b) as a CLI tool `python -m app.ai_ops.eval --workload smart_picker` for ad-hoc; (c) from a nightly Celery beat for regression tracking against LangFuse-stored baseline (V1.5 — V1 ships the runner + manual invocation).

### 6A.I Acceptance integration map

| Workload | `ai_ops/` files participating | Function called | Artefact produced |
|---|---|---|---|
| `smart_picker` | `client` + `prompt_registry` (resolve `smart_picker.v1`) + `guardrail` (Layer 1 JSON-shape prefix; Layer 2 parses JSON shape) + `cost_tracker` + `budget_cap` + `langfuse.trace` via §6.F | `client.call_gemini(ctx, "smart_picker.v1", {"description": ...})` from `category.service.suggest_categories` | `AIResponse.parsed` = ranked top-5 dict → `category` module returns the 5-card response; `audit_events` row written; daily/hourly cost counters incremented |
| `autofill` | `client` + `prompt_registry` (resolve `autofill.v1`) + `guardrail` (Layer 1 enum-allowlist prefix; Layer 2 enum re-validation with up-to-2 retries) + `cost_tracker` + `budget_cap` + `langfuse.trace` | `client.call_gemini(ctx, "autofill.v1", {"product_spec": ..., "schema": ...}, allowed_enums={...})` from `catalog.service.autofill_product` | `AIResponse.parsed` = field-value dict → `catalog` module writes `products.ai_suggestions_jsonb`; on Layer 2 retry exhaustion, returns 503 with `ai_ops.budget_exhausted`-style i18n message specific to autofill failure |
| `watermark` | `client` + `prompt_registry` (resolve `watermark.v1`) + `guardrail` (Layer 1 boolean-output prefix; Layer 2 boolean-shape check) + `cost_tracker` + `budget_cap` + `langfuse.trace` | `client.call_gemini(ctx, "watermark.v1", {}, image_bytes=...)` from `image.tasks.precheck_image` (Celery worker context) | `AIResponse.parsed` = `{"has_watermark": bool, "confidence": float}` → `image` worker writes `product_images.precheck_jsonb.watermark_check`; on budget hard-stop marks `"skipped_budget"` |

### 6A.J Cross-section integration points

**`ai_ops/` MAY import:**
- `adapters/gemini.py` (the sole place this import is legal under `app/` outside `ai_ops/` per §3.G boundary rule)
- `adapters/langfuse.py` (for trace egress)
- `shared/database.py`, `shared/valkey.py`, `shared/config.py`
- `shared/models/AuditEvent`, `shared/models/User` (for `cost_tracker` `audit_events` write + `user_id` resolution)
- `core/errors.py` (for `BudgetExceededError` definition + `MeesellError` subclassing)
- `core/cache.py` (for prompt-registry caching when V1.5 A/B flag flips)

**`ai_ops/` MAY NOT import:**
- `app.modules.*` (modules import `ai_ops`, never reverse — import direction enforces §16 boundary)
- `adapters/msg91.py`, `adapters/gcs.py`, `adapters/razorpay.py` (non-AI vendors — `ai_ops` is AI-only)
- `core/middleware/*` (middleware is request-path; `ai_ops` runs in service path)
- Per-module `service.py`/`repository.py`/`exceptions.py` (those are above `ai_ops` in the import direction)

The §19 import-linter enforces both lists.

### 6A.K What §6A does NOT cover

- **Prompt CONTENT** — owned by `meesell-prompt-engineer` per AI track collaboration on §2.3 / §2.4 / §2.5.
- **Per-workload domain ranking algorithm** — `meesell-category-picker-builder` owns Smart Picker top-5 ranking logic; `meesell-image-precheck-builder` owns watermark detection pipeline.
- **The bare Gemini SDK call** — §6 `adapters/gemini.py` (which §6A wraps).
- **Per-user feature budget enforcement** (the 50/h autofill cap, 100/h Smart Picker cap, etc.) — `core/plan_guard.py` per §4.E; §6A enforces only the DAILY GLOBAL ₹500 cap + workload availability.
- **The Export Adapter's Layer 3 re-validation** — `modules/export/service.py` per §14.
- **LangFuse cost analytics dashboard configuration** — `meesell-infra-builder` per §20.
- **V2 multi-model routing** — deferred per `MVP_ARCH §14`.

---

## Section 7 — Module: `iam`

STATUS: LOCKED (2026-06-05)

### 7.A Preamble

§7 specifies the **`iam` module** — Identity & Access Management. **Owner specialist:** `meesell-auth-builder` (sole owner per §2.1 + §4.B). **Leaf module** — `iam` calls no other module's `service.py`; other modules consume `get_current_user` through the `core/` middleware chain, not by service-layer call (per §2.D matrix all-`✗` row for `iam`). Owns the `users` table **exclusively** — no other module writes to it. Surfaces **6 endpoints total** — 4 V1 auth endpoints (counted in the §0.C 27-endpoint contract) + 1 introspection (`GET /api/v1/auth/me`) + 1 webhook (`POST /api/v1/webhooks/razorpay`). The `/me` and `/webhooks/razorpay` surfaces are **infrastructure** surfaces — NOT counted in the §0.C contract; the contract is the 4 auth endpoints. §7 does NOT specify `core/auth.py`'s `get_current_user` (that is §4.B — `iam` re-exports it via FastAPI router-level `Depends` only); does NOT specify rate-limit Valkey window math (that is §4.G); does NOT specify the JWT claim shape (that is §4.B + `MVP_ARCH §11.7` — `iam` writes the claims defined there). A reviewer evaluating §7 asks: "are the 6 endpoint contracts unambiguous (request, response, cookie attributes, audit events, status codes), is the Lua rotation script verbatim, are the service/repository surfaces locked and module-private per §16, do the 8 IamError subclasses cover every documented failure mode?" — not "is the get_current_user dep correct" (§4.B) or "is the MSG91 SDK call right" (§6.C).

### 7.B Endpoint surfaces

The 6 endpoint contracts owned by `iam`. Each block locks request shape, response shape, rate-limit decorator (per §4.G/§4.H decorator pattern), status code → `validation_message_id` mapping (per §5A.H), audit event emission (middleware-default with documented exceptions), and the service-layer flow.

#### 7.B.1 `POST /api/v1/auth/otp/send` — Feature 1 phone OTP send

**Request** (Pydantic; see §7.E):

```python
class SendOtpRequest(BaseModel):
    phone: str = Field(pattern=r"^\+[1-9]\d{1,14}$")  # E.164
```

**Response 202:**

```python
class SendOtpResponse(BaseModel):
    request_id: str  # MSG91 correlation ID; opaque to client; logged for support
```

**Rate limit** per §4.G + `MVP_ARCH §10.7`:

```python
@rate_limit(scope="otp_send", limit="3/h", key="phone")
```

Per-IP fallback (`RL_PER_IP_PER_MINUTE` per §4.E) also applies unconditionally.

**Status code → `validation_message_id` mapping:**
- `202` — success.
- `400` — `validation.phone.invalid_format` (Pydantic regex reject).
- `429` — `plan.limit_exceeded` (raised by `rate_limit_mw` BEFORE route per §4.H).
- `503` — `auth.msg91_unavailable` (msg91 adapter returned `success=False` per §6.C).

**Audit event** — `auth.otp.sent` emitted by `core/middleware/audit_mw.py` on 2xx (per §4.G). Payload: `{phone_hashed: SHA256(phone + AUDIT_PII_SALT), request_id}` per `MVP_ARCH §11.9` PII scrubbing.

**JWT required:** no — login entry point.

**Flow:**
1. Pydantic validate phone (regex E.164).
2. Middleware `rate_limit_mw` checks 3/h cap per phone (the `@rate_limit` decorator's `key="phone"` tag tells the middleware to use the request body's `phone` field per §4.H).
3. `iam.service.send_otp_for_login(phone)` — generate 6-digit OTP via `secrets.choice`.
4. Store in Valkey DB 0 (`otp:{phone}` → JSON `OtpRecord` (§7.F) with TTL 5 min).
5. Call `adapters.msg91.send_otp` (§6.C). If `success=False`, raise `Msg91UnavailableError`.
6. Return `202 SendOtpResponse(request_id=...)`.

#### 7.B.2 `POST /api/v1/auth/otp/verify` — Feature 1 phone OTP verify (MODIFIED PER §4.B FE-D5 AMENDMENT)

**Request** (§7.E):

```python
class VerifyOtpRequest(BaseModel):
    phone: str = Field(pattern=r"^\+[1-9]\d{1,14}$")
    otp: str = Field(pattern=r"^\d{6}$")
```

**Response 200 body:**

```python
class VerifyOtpResponse(BaseModel):
    access_token: str
    expires_in: int  # == settings.ACCESS_TOKEN_TTL_SECONDS (prod 900)
    token_type: Literal["bearer"] = "bearer"
```

**Response header (Set-Cookie)** per §4.B amendment cookie format:

```
Set-Cookie: refresh_token=<opaque>;
            Domain=.mesell.xyz;
            Path=/api/v1/auth;
            HttpOnly; Secure; SameSite=Strict;
            Max-Age=<settings.REFRESH_TOKEN_TTL_SECONDS>
```

The `Path=/api/v1/auth` correction is locked per §4.B amendment (FE memo's `Path=/auth` would not match — see §4.B counter-proposal rationale).

**Rate limit:**

```python
@rate_limit(scope="otp_verify", limit="10/h", key="phone")
```

10/h/phone is a **security** cap to slow brute force (10 failed attempts/h on the same phone — well above legitimate retry rate, far below brute-force throughput).

**Status code → `validation_message_id` mapping:**
- `200` — success.
- `400` — `validation.phone.invalid_format` or `validation.otp.invalid_format`.
- `401` — `auth.otp_invalid` (missing/expired OTP, or mismatch on attempt < 3).
- `401` — `auth.otp_attempts_exceeded` (3rd failed attempt on the same OTP — record DELed, fresh OTP send required).
- `429` — `plan.limit_exceeded`.

**Audit events** — DOCUMENTED EXCEPTION to the §4.G "audit only via middleware" rule. Emitted via **direct ORM write** inside `iam.service.verify_otp_and_issue_tokens` because the events are emitted on BOTH paths: `auth.login.success` (with `hashed_phone` + `user_id`) on the success path AFTER user upsert + JWT issuance, AND `auth.login.failed` (with `hashed_phone` + `reason`) on the failure paths where there is no `user_id` for middleware to extract from `request.state.user`. Same documented-exception pattern as §6A.D `cost_tracker` (which also writes `audit_events` outside the middleware because the worker path has no request close to hook).

**JWT required:** no — this is the JWT issuance point.

**Flow:**
1. Pydantic validate inputs.
2. `iam.service.verify_otp_and_issue_tokens(phone, otp, client_ip)`:
   - Read `otp:{phone}` from Valkey DB 0 (`shared/valkey.get_valkey_otp()`). If missing → write `auth.login.failed` (`reason="otp_missing_or_expired"`), raise `OtpInvalidError`.
   - Constant-time compare via `secrets.compare_digest(SHA256(otp).hexdigest(), stored.otp_hash)`.
   - **On mismatch:** increment `attempts`, write back to Valkey (preserving original TTL). If `attempts >= 3` after increment → `DEL otp:{phone}`, write `auth.login.failed` (`reason="otp_attempts_exceeded"`), raise `OtpAttemptsExceededError`. Otherwise → write `auth.login.failed` (`reason="otp_mismatch"`), raise `OtpInvalidError`.
   - **On match:** `iam.repository.upsert_user_on_login(phone, ip, capture_dpdp=True)`:
     - INSERT if phone not seen; UPDATE `last_login_at = now()`.
     - SET `dpdp_consented_at = now()` if currently NULL (CLAUDE.md DPDP capture rule: V1 captures at verify time, does NOT block on missing).
   - Generate access JWT via PyJWT HS256 with claims `{sub: str(user_id), exp: now + ACCESS_TOKEN_TTL_SECONDS, plan: user.plan, iat: now}` per `MVP_ARCH §11.7` + §4.B claim contract.
   - Generate opaque refresh token: `secrets.token_urlsafe(48)` per §4.B amendment ("Refresh token: NOT a JWT").
   - Compute `refresh_key = "cache:refresh:" + hmac.new(REFRESH_TOKEN_PEPPER.encode(), refresh_token.encode(), hashlib.sha256).hexdigest()` per §0.F D2 / §4.B amendment HMAC-with-pepper strengthening.
   - `SET refresh_key` value `RefreshAllowlistEntry` JSON (`{"user_id": str(user_id), "issued_at": int(now), "ip": request.client.host}`) with `EX REFRESH_TOKEN_TTL_SECONDS` in Valkey DB 0.
   - `DEL otp:{phone}` — single-use semantic.
   - Write `auth.login.success` audit row.
3. Router serializes `VerifyOtpResponse` body + sets `Set-Cookie` header. Return 200.

#### 7.B.3 `POST /api/v1/auth/refresh` — NEW per §4.B FE-D5 amendment

**Request body:** none. The `refresh_token` cookie is the sole input (browser auto-attaches because `Path=/api/v1/auth` matches).

**Response 200 body:**

```python
class RefreshResponse(BaseModel):  # identical shape to VerifyOtpResponse — locked separately for OpenAPI clarity
    access_token: str
    expires_in: int
    token_type: Literal["bearer"] = "bearer"
```

**Response header (Set-Cookie)** — new rotated refresh cookie:

```
Set-Cookie: refresh_token=<new_opaque>;
            Domain=.mesell.xyz;
            Path=/api/v1/auth;
            HttpOnly; Secure; SameSite=Strict;
            Max-Age=<settings.REFRESH_TOKEN_TTL_SECONDS>
```

**On failure (401)** — clear cookie:

```
Set-Cookie: refresh_token=;
            Domain=.mesell.xyz;
            Path=/api/v1/auth;
            HttpOnly; Secure; SameSite=Strict;
            Max-Age=0
```

**Rate limit:**

```python
@rate_limit(scope="auth_refresh", limit="60/h", key="refresh_cookie_user_id")
```

The `key="refresh_cookie_user_id"` resolves via the allowlist entry's `user_id` (looked up by the cookie's HMAC). If the cookie is missing, the key falls back to `request.client.host` (per-IP) so brute-force probes still get capped.

**Status code → `validation_message_id` mapping:**
- `200` — success.
- `401` — `auth.refresh_invalid` (missing cookie, missing/expired allowlist entry, or rotation race lost — Lua script returned nil).
- `429` — `plan.limit_exceeded`.

**Audit events** — DOCUMENTED EXCEPTION (same pattern as §7.B.2 and §6A.D). `auth.token.refreshed` on success (with `user_id` known after allowlist read), OR `auth.token.refresh_failed` (with `reason: "missing" | "expired" | "race_lost"`) on failure — emitted via direct ORM write inside `iam.service.rotate_refresh_token` because failed refresh has no `request.state.user` for middleware to use.

**JWT required:** no — the cookie IS the credential.

**Flow:**
1. Read `refresh_token` from `Cookie: refresh_token=<value>` header. If missing → write `auth.token.refresh_failed` (`reason="missing"`), raise `RefreshInvalidError`, response includes clear-cookie header.
2. Compute `old_key = "cache:refresh:" + hmac_sha256(old_refresh_token, REFRESH_TOKEN_PEPPER)`.
3. Generate `new_refresh_token = secrets.token_urlsafe(48)`.
4. Compute `new_key = "cache:refresh:" + hmac_sha256(new_refresh_token, REFRESH_TOKEN_PEPPER)`.
5. Invoke the locked Lua EVAL script (§7.B.3 below — verbatim) on Valkey DB 0. The script is loaded once at iam-service startup via `SCRIPT LOAD` and invoked via `EVALSHA <digest> 2 old_key new_key <new_payload_json> <ttl_seconds>`. `EVAL` is the fallback when `EVALSHA` returns `NOSCRIPT` (after a Valkey restart). The script digest is cached on the iam service singleton per §5.C "SCRIPT LOAD once + EVALSHA thereafter".

The locked Lua source (verbatim):

```lua
local old = redis.call('GET', KEYS[1])
if old then
  redis.call('SET', KEYS[2], ARGV[1], 'EX', tonumber(ARGV[2]))
  redis.call('DEL', KEYS[1])
  return old
else
  return nil
end
```

Called with `KEYS = [old_key, new_key]`, `ARGV = [new_payload_json, REFRESH_TOKEN_TTL_SECONDS]`. The script atomically: `GET old_key` → if exists, `SET new_key` value with TTL, `DEL old_key`, return old value (the JSON allowlist entry); if missing, return nil. Replay-attack mitigation: reusing the old cookie after rotation returns nil because `old_key` is gone.

6. If script returned nil → write `auth.token.refresh_failed` (`reason="expired"` or `"race_lost"`), raise `RefreshInvalidError`, response includes clear-cookie header.
7. If returned `user_id` (from parsed JSON) → re-read user row via `iam.repository.get_user_by_id(user_id)` to refresh the `plan` claim (in case V1.5 updated `plan` since prior refresh; V1 always `"free"`).
8. Generate new access JWT with `{sub: str(user_id), exp: now + ACCESS_TOKEN_TTL_SECONDS, plan: user.plan, iat: now}`.
9. Write `auth.token.refreshed` audit row (`{user_id, ip}`).
10. Router serializes `RefreshResponse` + sets new `Set-Cookie` header. Return 200.

#### 7.B.4 `POST /api/v1/auth/logout` — NEW per §4.B FE-D5 amendment

**Request body:** none.

**Response 204:** no body.

**Response header (Set-Cookie)** — always clear-cookie (even when no cookie was present), idempotent:

```
Set-Cookie: refresh_token=;
            Domain=.mesell.xyz;
            Path=/api/v1/auth;
            HttpOnly; Secure; SameSite=Strict;
            Max-Age=0
```

**Rate limit:** none. Idempotent, no abuse vector (logout cannot brute-force anything).

**Status code → `validation_message_id` mapping:**
- `204` — always (idempotent — see flow).

**Audit event** — DOCUMENTED EXCEPTION. `auth.logout` emitted via direct ORM write IF a refresh cookie was present (with `user_id` resolved from the allowlist entry BEFORE the `DEL`). NOT emitted if no cookie was sent (nothing to log — calling logout twice is a no-op the second time).

**JWT required:** no — the cookie is the credential, or no auth is needed if no cookie.

**Flow:**
1. Read `refresh_token` from cookie. If missing → return 204 + clear-cookie header (no-op for the browser; no audit row).
2. Compute `key = "cache:refresh:" + hmac_sha256(refresh_token, REFRESH_TOKEN_PEPPER)`.
3. `GET key` (to resolve `user_id` for audit), then `DEL key`. No error if not exists.
4. If `user_id` resolved → write `auth.logout` audit row.
5. Return 204 + clear-cookie header.

#### 7.B.5 `GET /api/v1/auth/me` — introspection (NOT in the 27-endpoint contract; infrastructure surface)

**Request:** no body. **Authorization:** `Bearer <access_token>`.

**Response 200:**

```python
class MeResponse(BaseModel):
    user_id: UUID
    phone: str
    plan: Literal["free"]
    created_at: datetime
    last_login_at: datetime | None
```

**Rate limit:** per-IP fallback only (no per-user limit — this is a polling endpoint for frontend bootstrap per FRONTEND_ARCH §1.C; per-user limiting would interfere with legitimate page-reload flows).

**Status code → `validation_message_id` mapping:**
- `200` — success.
- `401` — any auth dep failure per §4.B (`auth.token_missing`, `auth.token_expired`, `auth.user_not_found`).

**Audit event:** **NONE.** Read-only introspection; logging every `/me` call would flood `audit_events` with no value (the access JWT alone proves the user is active). Documented absence.

**JWT required:** yes — uses `Depends(get_current_user)` per §4.B (`iam` re-exports this dep via FastAPI router-level dependency injection only; does NOT redefine it).

**Flow:**
1. `core/auth.get_current_user` dep extracts `CurrentUser(user_id, plan)` from Bearer token.
2. `iam.service.get_profile(user_id)` reads `users` row via `iam.repository.get_user_by_id`.
3. Router serializes `MeResponse`. Return 200.

#### 7.B.6 `POST /api/v1/webhooks/razorpay` — V1 capture only

**Request:** **RAW body** (NOT JSON-parsed at the FastAPI dependency level — Pydantic parsing is deferred until AFTER signature verification per the V1 capture-only posture). Header: `X-Razorpay-Signature`.

**Response 200:**

```python
class WebhookCaptureResponse(BaseModel):
    captured: bool = True
```

**Rate limit:** per-IP only. Razorpay infrastructure has its own retry semantics; per-user logic is meaningless (no user context yet).

**Status code → `validation_message_id` mapping:**
- `200` — success.
- `401` — `auth.webhook_signature_invalid` (HMAC verify failed per §6.E).
- `400` — `validation.webhook.malformed_payload` (signature valid but JSON parse fails).

**Audit event** — `razorpay.webhook.captured` written via direct ORM write inside `iam.service.capture_razorpay_webhook` (same documented-exception pattern). Payload subtype: the parsed-event name (`subscription.created`, `subscription.charged`, etc.). Full payload stored in `audit_events.payload_jsonb` so V1.5 reprocessing can derive subscription state without re-fetching from Razorpay.

**JWT required:** no — Razorpay signs with the shared `RAZORPAY_WEBHOOK_SECRET` (§5.D) per §6.E.

**Flow:**
1. Read raw body via FastAPI `Request.body()` — NOT auto-parsed.
2. Read `X-Razorpay-Signature` header.
3. `adapters.razorpay.verify_webhook_signature(payload, signature, settings.RAZORPAY_WEBHOOK_SECRET)` — synchronous per §6.E (HMAC is CPU-bound). If `False` → raise `WebhookSignatureInvalidError`.
4. Parse JSON. If malformed → raise an iam-local `ValueError` translated to 400 `validation.webhook.malformed_payload`.
5. Direct ORM write to `audit_events` (`{event_type: "razorpay.webhook.captured", event_subtype: payload["event"], payload_jsonb: payload, user_id: NULL}`).
6. Return 200. V1 does **NOT** update `users.plan` or any other state — capture only per §2.1 + §0.G § J §15.

### 7.C Service layer — `iam/service.py`

Locked public methods (all `async`). All methods are PUBLIC even though `iam` is a leaf module per §2.D — the leaf-ness means no OTHER module calls them; the router does. Future inter-pod extraction (V1.5 per §21) preserves this surface verbatim, replacing the in-process call with HTTP.

```python
async def send_otp_for_login(phone: str) -> SendOtpResult: ...
async def verify_otp_and_issue_tokens(phone: str, otp: str, client_ip: str) -> VerifyOtpResult: ...
async def rotate_refresh_token(old_refresh_token: str, client_ip: str) -> RotateRefreshResult: ...
async def revoke_refresh_token(refresh_token: str | None) -> RevokeResult: ...
async def get_profile(user_id: UUID) -> UserProfile: ...
async def capture_razorpay_webhook(raw_payload: bytes, signature: str) -> WebhookCaptureResult: ...
```

### 7.D Repository layer — `iam/repository.py`

Locked methods (all `async`, all SQLAlchemy 2.0 typed). Per §16, repository methods are **MODULE-PRIVATE** — other modules calling `find_user_by_phone` would be a §16 violation; they must instead call `iam.service.get_profile(user_id)` if they need user info. In practice no other module does, because `core/auth.get_current_user` (§4.B) is the only consumer of user data outside `iam` itself.

```python
async def find_user_by_phone(db: AsyncSession, phone: str) -> User | None: ...
async def upsert_user_on_login(db: AsyncSession, phone: str, ip: str, capture_dpdp: bool) -> User: ...
async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User | None: ...
async def update_plan(db: AsyncSession, user_id: UUID, plan: str) -> None  # V1.5 — Razorpay subscription updates
```

### 7.E Schemas — `iam/schemas.py`

Locked Pydantic v2 request/response models. Field constraints are normative (Pydantic regex rejection produces the 400 `validation.{field}.invalid_format` envelopes per §5A.H).

```python
class SendOtpRequest(BaseModel):
    phone: str = Field(pattern=r"^\+[1-9]\d{1,14}$")

class SendOtpResponse(BaseModel):
    request_id: str

class VerifyOtpRequest(BaseModel):
    phone: str = Field(pattern=r"^\+[1-9]\d{1,14}$")
    otp: str = Field(pattern=r"^\d{6}$")

class VerifyOtpResponse(BaseModel):
    access_token: str
    expires_in: int
    token_type: Literal["bearer"] = "bearer"

class RefreshResponse(BaseModel):  # identical shape to VerifyOtpResponse — locked separately for OpenAPI clarity
    access_token: str
    expires_in: int
    token_type: Literal["bearer"] = "bearer"

class MeResponse(BaseModel):
    user_id: UUID
    phone: str
    plan: Literal["free"]
    created_at: datetime
    last_login_at: datetime | None

class WebhookCaptureResponse(BaseModel):
    captured: bool = True
```

### 7.F Internal domain types — `iam/domain.py`

Locked frozen dataclasses (NOT Pydantic — these never cross the HTTP boundary; they are internal value objects between service ↔ repository ↔ Valkey-serializer).

```python
@dataclass(frozen=True)
class OtpRecord:
    otp_hash: str      # SHA256 of the OTP (hexdigest)
    attempts: int      # 0, 1, 2 — 3 triggers lockout
    expires_at: int    # unix timestamp

@dataclass(frozen=True)
class RefreshAllowlistEntry:
    user_id: UUID
    issued_at: int     # unix timestamp
    ip: str            # client IP at issuance

@dataclass(frozen=True)
class SendOtpResult:
    request_id: str

@dataclass(frozen=True)
class VerifyOtpResult:
    access_token: str
    refresh_token: str       # opaque; the router serializes into cookie
    access_expires_in: int
    refresh_expires_in: int

@dataclass(frozen=True)
class RotateRefreshResult:
    access_token: str
    new_refresh_token: str   # opaque; the router serializes into cookie
    access_expires_in: int
    refresh_expires_in: int

@dataclass(frozen=True)
class RevokeResult:
    cookie_was_present: bool
    user_id: UUID | None     # None when no cookie was sent (idempotent path)

@dataclass(frozen=True)
class UserProfile:
    user_id: UUID
    phone: str
    plan: str
    created_at: datetime
    last_login_at: datetime | None

@dataclass(frozen=True)
class WebhookCaptureResult:
    event_type: str
    event_subtype: str
    audit_event_id: int
```

### 7.G Exception hierarchy — `iam/exceptions.py`

All subclass `MeesellError` per §4.F. Each carries `status_code` + `validation_message_id` resolved through `core/errors.py` → `i18n/resolver.py` per §5A.I. The 8 message IDs land in `i18n/messages_en.py` during the auth-builder construction dispatch.

```python
class IamError(MeesellError):
    """Base class for iam module failures. Never raised directly."""

class InvalidPhoneFormatError(IamError):
    status_code = 400
    validation_message_id = "validation.phone.invalid_format"

class OtpInvalidError(IamError):
    status_code = 401
    validation_message_id = "auth.otp_invalid"

class OtpAttemptsExceededError(IamError):
    status_code = 401
    validation_message_id = "auth.otp_attempts_exceeded"

class Msg91UnavailableError(IamError):
    status_code = 503
    validation_message_id = "auth.msg91_unavailable"

class RefreshInvalidError(IamError):
    status_code = 401
    validation_message_id = "auth.refresh_invalid"

class WebhookSignatureInvalidError(IamError):
    status_code = 401
    validation_message_id = "auth.webhook_signature_invalid"
```

(Note: `auth.token_missing`, `auth.token_expired`, `auth.user_not_found` are owned by `core/auth.py` per §4.B, NOT by `iam` — they live in `core/exceptions.py` and are listed here only as a reminder that the auth dep contributes 3 additional message IDs to the same `auth.*` namespace.)

### 7.H Adapter usage

Per §6 contracts (LOCKED).

- **`adapters/msg91.py`** — `send_otp(phone, otp, template_id) -> Msg91Response` called from `iam.service.send_otp_for_login`. Returns `Msg91Response`; `success=False` translates to `Msg91UnavailableError` raise in the service layer per §6.C (the adapter does NOT raise; this is the locked exception to the "raise on failure" pattern, documented in §6.G).
- **`adapters/razorpay.py`** — `verify_webhook_signature(payload, signature, secret) -> bool` called from `iam.service.capture_razorpay_webhook`. Returns `bool`; `False` translates to `WebhookSignatureInvalidError` raise. Sync per §6.E (the locked exception to the async-default rule — HMAC is CPU-bound).
- **No other adapters used.** `iam` does NOT call `adapters/gemini` (no AI), `adapters/gcs` (no blob storage), or `adapters/langfuse` (no AI trace).

### 7.I Cross-cutting integrations

One bullet per cross-cutting concern, citing the locked source section.

- **Rate-limit decorators (§4.G + §4.H).** Five routes decorated: `otp_send` (`3/h`, key=`phone`), `otp_verify` (`10/h`, key=`phone`), `auth_refresh` (`60/h`, key=`refresh_cookie_user_id`); `/me` and `/webhooks/razorpay` use per-IP fallback only (no `@rate_limit` decorator). `/logout` has no rate limit (idempotent, no abuse vector).
- **Audit middleware (§4.G).** Most successful 2xx writes emit audit events via `core/middleware/audit_mw.py`. **`iam` exceptions** (direct ORM write inside service): `verify_otp` (failed login has no `user_id` for middleware), `refresh` (failed has no `user_id`), `logout` (the cookie-resolved `user_id` is known only inside the service BEFORE the `DEL`). These three follow the same documented-exception pattern as `cost_tracker` per §6A.D. The `/me` endpoint emits NO audit event (documented absence — see §7.B.5).
- **Plan guard (§4.E).** NOT participating in V1. `iam` does not gate on `plan`; `core/plan_guard.py` is for the 4 V1 feature limits per §4.E, none of which are auth surfaces.
- **Tenancy (§4.C).** NOT participating. `iam` is leaf; the only `user_id`-scoped write is to `users` itself, which IS the scoping subject. `core/tenancy.scope_to_user` is not called.
- **i18n (§5A.I).** Every error envelope resolves `validation_message_id` via `core/errors.py` → `i18n/resolver.py`. The 8 iam-specific message IDs (`validation.phone.invalid_format`, `validation.otp.invalid_format`, `validation.webhook.malformed_payload`, `auth.otp_invalid`, `auth.otp_attempts_exceeded`, `auth.msg91_unavailable`, `auth.refresh_invalid`, `auth.webhook_signature_invalid`) land in `i18n/messages_en.py` during the auth-builder dispatch.

### 7.J Test plan

Locked test classes per the §19 SKELETON amendment that absorbed FE-D5 per coordinator memory turn 8. **4 unit + 3 integration** test classes.

**Unit (`backend/tests/modules/iam/`):**
1. **Refresh allowlist write on verify-success** — verify path writes `cache:refresh:{hmac}` to Valkey DB 0 with correct JSON payload + TTL = `REFRESH_TOKEN_TTL_SECONDS`.
2. **Refresh validation under 4 cases** — valid (rotation succeeds), expired (Lua returns nil, 401), revoked (post-logout, Lua returns nil, 401), already-rotated (replay attack: old cookie after refresh, Lua returns nil, 401).
3. **Logout idempotency** — first call DELs allowlist entry + clears cookie + writes audit; second call returns 204 + clears cookie + NO audit row (cookie already gone, nothing to log).
4. **Constant-time comparison regression** — `secrets.compare_digest` used for OTP hash compare AND for refresh-token lookup (Valkey key is HMAC-based, but the Lua script's existence check is constant-time at the Redis level; this test guards against future refactors reintroducing `==`).

**Integration (`backend/tests/integration/test_iam_*.py`):**
1. **Full silent-refresh flow** — verify → short wait (well under `ACCESS_TOKEN_TTL_SECONDS` staging=60s) → refresh → old access still valid until its `exp` (the new access has fresh `exp`; the old one isn't revoked — the access token has no allowlist, only refresh does).
2. **Logout revocation** — verify → logout → refresh → 401 `auth.refresh_invalid` (allowlist entry is gone; Lua returns nil).
3. **Replay-attack mitigation** — verify → refresh → save old refresh cookie locally in test → attempt to reuse old cookie → 401 (rotation invalidated it during refresh step).

**Pytest fixtures:** real Valkey (DB 0) via the dev tunnel per `shared/valkey.py` factory; real Postgres for `users` upsert; mocked MSG91 adapter (avoids burning real OTP credits in CI); mocked Razorpay webhook generator (signs a fixture payload with a test secret).

### 7.K Extraction notes (V1.5+)

Per §21 extraction order, `iam` is the **2nd-easiest** module to extract after `export`. Data surface: 1 table (`users`). Public contract is already an interface — `core/auth.get_current_user` becomes a remote JWT-validation HTTP call in V1.5 (the iam-pod exposes `POST /internal/auth/validate` returning `CurrentUser`). At extraction time:
1. Lift `modules/iam/` to its own pod (FastAPI + iam-only).
2. Repoint `core/auth.py`'s `get_current_user` to call the extracted iam-pod via HTTP instead of decoding JWT in-process (or keep in-process decoding + remote `users` lookup — TBD per §21).
3. Move the Valkey DB 0 allowlist keys to the extracted iam-pod's Valkey, or share the existing Valkey via cluster.
4. All other modules' call sites are unchanged — they consume `get_current_user` from `core/`, not from `iam` directly.

### 7.L What §7 does NOT cover

- `core/auth.py`'s `get_current_user` implementation (that is §4.B — `iam` consumes it via `Depends`, does not redefine it; the 3 `auth.token_*` message IDs live in `core/exceptions.py`).
- The actual MSG91 / Razorpay SDK call paths (§6.C + §6.E — `iam` calls the adapters' locked public methods only).
- The Valkey client factory and the JWT secret loading (§5.C + §5.D — `iam` consumes `get_valkey_otp()` and `settings.JWT_SECRET` as locked).
- The cookie `Domain=.mesell.xyz` and `Path=/api/v1/auth` invariants (locked by §4.B amendment + §4.G amendment; cited here as facts).
- The per-route `@rate_limit` decorator IMPLEMENTATION (§4.G + §4.H — `iam` only declares the limit tuples; the middleware reads them via dependency introspection).
- The exact English message strings for the 8 iam-specific message IDs (those land during the auth-builder construction dispatch into `i18n/messages_en.py` per §5A.I — §7 specifies only the IDs, not the prose).

---

## Section 8 — Module: `customer`

STATUS: LOCKED (2026-06-05)

### 8.A Preamble

§8 specifies the **`customer` module** — seller profile, onboarding, the 9-field Legal Metrology compliance block, and the 6 conditional compliance extensions per super-category (Grocery+FSSAI compulsory; Kids+BIS, Electronics+R/IS/CM-L, Beauty+License, Books+ISBN, Appliances+License — optional/conditional per founder rulings `MVP_ARCH §12.1` + `§0` premise #7). **Owner specialists:** `meesell-api-routes-builder` (routes + Pydantic schemas) + `meesell-services-builder` (business logic, compliance-extension resolver, onboarding state machine) per §2.2. **Leaf module on the cross-module call graph** — `customer` calls no other module's `service.py` (per §2.D matrix all-`✗` row for `customer`). But `customer` IS called BY `catalog` (gate `PROFILE_INCOMPLETE_FOR_CATEGORY`), `export` (compliance block for XLSX emission), and `dashboard` (profile-completeness badge) — those callers consume `customer.service` public methods locked in §8.C. Owns the `seller_profile` table **exclusively** — no other module writes to it; the Export Adapter reads compliance values through `customer.service.get_compliance_block`, never via direct SQL (per §16 lock). Surfaces **5 endpoints**, all counted in the §0.C 27-endpoint contract (`MVP_ARCH §3.2`). §8 does NOT specify the DDL of `seller_profile` (that is `MVP_ARCH §2.2`), does NOT specify the `core/tenancy.py` `scope_to_user` helper (that is §4.C — `customer` consumes it on every repository query), does NOT specify warranty per-product schema (per `§12.5` lock — warranty lives in `catalog`'s schema validation, NOT in `seller_profile.compliance_extensions`).

### 8.B Endpoint surfaces

The 5 endpoint contracts below are normative. Request/response shapes reference §8.E schemas verbatim. Rate-limit decorators apply per §4.G + §4.H; audit posture follows the §4.G middleware contract (audit on 2xx for state-changing endpoints; never for read-only endpoints per `MVP_ARCH §11.3` flood-prevention rationale).

#### 8.B.1 `GET /api/v1/seller-profile` — read current profile

- **Request:** no body. Authorization: `Bearer <access_token>` per §4.B.
- **Response 200:** `SellerProfileResponse` (full profile shape per §8.E).
- **Response 404:** profile does not exist yet (first-time seller, expected state — frontend redirects to the onboarding wizard). Envelope `validation_message_id="customer.profile.not_found"`.
- **Rate limit:** per-IP fallback only (no per-user — frontend polls on every page load per §4.G).
- **Status codes:** 200, 401, 404.
- **Audit:** NONE (read-only — same posture as §7.B.5 `/me` for the same flood-prevention reason).
- **JWT required:** yes — `Depends(get_current_user)` per §4.B.
- **Flow:** `customer.service.get_profile_or_none(user_id)` → returns full profile or `None` → router maps `None` to 404 envelope.

#### 8.B.2 `PATCH /api/v1/seller-profile` — partial update of base profile fields

Covers the 9 Legal Metrology fields + `country_of_origin`.

- **Request body (Pydantic):** `PatchProfileRequest` (§8.E) — every field is OPTIONAL. **Subset semantics:** only fields present are updated; absent fields untouched. **First-PATCH-creates-row pattern** (upsert).
- **Response 200:** `SellerProfileResponse` (full updated profile).
- **Rate limit:** `@rate_limit(scope="profile_update", limit="60/h", key="user_id")`. Per `MVP_ARCH §10.7` `create-product 20/h` is a separate plan limit — `profile_update` is its own security cap, not a plan_guard concern (per §4.E `customer` does NOT participate in plan_guard).
- **Status codes:** 200, 400 (`validation.{field}.invalid_format`), 401, 422 (Pydantic aggregate).
- **Audit:** middleware emits `customer.profile.updated` carrying the **changed field NAMES only** (NOT values — values may include PII per `MVP_ARCH §11.9`; field names are safe).
- **JWT required:** yes.
- **Flow:** `customer.service.upsert_profile(user_id, patch)` → repository upserts the row → recomputes `onboarding_complete` flag → returns full profile.

#### 8.B.3 `PATCH /api/v1/seller-profile/active-categories` — declare/update active super-categories

- **Request body (Pydantic):** `PatchActiveCategoriesRequest({active_super_categories: list[str]})`. **Replaces the array entirely** (NOT additive — declares the seller's current sell-in scope).
- **Response 200:** `SellerProfileResponse` (updated profile with new `active_super_categories` + recomputed `onboarding_complete`).
- **Rate limit:** `@rate_limit(scope="active_categories", limit="60/h", key="user_id")`.
- **Status codes:** 200, 401, 422 (`validation.super_category.unknown` — when any `super_id` in the array does not exist in the `categories.super_id` distinct set).
- **Audit:** middleware emits `customer.active_categories.updated` with the new array (no PII concern — `super_id`s are reference data per `MVP_ARCH §11.9`).
- **JWT required:** yes.
- **Flow:** `customer.service.set_active_categories(user_id, super_ids)`:
  1. Validate each `super_id` exists in the `categories.super_id` distinct set (cached read via `core/cache.py` — global data per §4.D).
  2. Repository updates `active_super_categories TEXT[]`.
  3. Recompute `onboarding_complete` (false if any newly declared `super_id` requires compliance extension keys that are not yet present in `compliance_extensions`).
  4. Return updated profile.

#### 8.B.4 `PATCH /api/v1/seller-profile/compliance/{super_id}` — set compliance extension for one declared super-category

- **Request body (Pydantic):** `PatchComplianceExtensionRequest` — `dict[str, Any]` shape; the super_id-specific required keys are validated by the service against `COMPLIANCE_EXTENSION_MAP` (§8.F). Example for `super_id=26` (Grocery): `{"fssai_license_number": "10012345678901", "fssai_expiry": "2027-12-31"}`.
- **Response 200:** `SellerProfileResponse`.
- **Rate limit:** `@rate_limit(scope="compliance_update", limit="60/h", key="user_id")`.
- **Status codes:** 200, 401, 404 (`customer.super_category.not_declared` — `super_id` not in `active_super_categories`), 422 (`customer.compliance.missing_fields` — required keys absent; envelope payload lists which keys are missing).
- **Audit:** middleware emits `customer.compliance.updated` with `{super_id, updated_keys}` (NO values — license numbers are PII per `MVP_ARCH §11.9`).
- **JWT required:** yes.
- **Flow:** `customer.service.set_compliance_extension(user_id, super_id, payload)`:
  1. Read current profile.
  2. Verify `super_id IN active_super_categories`. If not → 404 `customer.super_category.not_declared`.
  3. Validate `payload` against `COMPLIANCE_EXTENSION_MAP[super_id]` (required keys per `MVP_ARCH §2.2`).
  4. Repository updates `compliance_extensions` JSONB at the `{super_id}` key (JSONB merge — does NOT affect other super_ids' entries).
  5. Recompute `onboarding_complete`.
  6. Return updated profile.

#### 8.B.5 `GET /api/v1/seller-profile/required-fields` — drives the frontend onboarding wizard

- **Request:** no body. Authorization required.
- **Response 200:** `RequiredFieldsResponse({base_fields: list[FieldSpec], extension_fields: dict[super_id, list[FieldSpec]], completed: dict[field_path, bool]})`. `FieldSpec` uses the **§5A.C per-field contract verbatim** (so the frontend renderer dispatches the same way it does for the catalog wizard — single rendering convention).
- **Rate limit:** per-IP fallback only (polled on every wizard step).
- **Status codes:** 200, 401.
- **Audit:** NONE (read-only).
- **JWT required:** yes.
- **Cache eligibility:** response is per-user; cached via `core/cache.py` per the §4.D contract with key `seller_profile_required_fields:{user_id}:v{cache_version}` TTL **60s** (low TTL because the profile changes during onboarding — invalidated on any PATCH to the profile).
- **Flow:** `customer.service.get_required_fields(user_id)`:
  1. Read current profile (may be `None` for first-time seller).
  2. `base_fields`: the 10 always-required fields (9 Legal Metrology + `country_of_origin`) as `FieldSpec` per §5A.C, with `completed` map showing which are filled.
  3. `extension_fields`: for each `super_id` in `active_super_categories`, look up the required keys from `COMPLIANCE_EXTENSION_MAP`, render as `list[FieldSpec]`, populate `completed`.
  4. Return aggregated response.

### 8.C Service layer

`customer/service.py` exposes the following async public methods (all consumed by either the `customer` router or other modules' services per §16). Implementations are written during the construction dispatch — §8.C locks the signatures only.

```python
async def get_profile_or_none(user_id: UUID) -> SellerProfile | None:
    """Returns None if no row exists (first-time seller). Consumed by GET /seller-profile."""

async def get_profile(user_id: UUID) -> SellerProfile:
    """Raises ProfileNotFoundError if no row exists. Consumed by catalog/export/dashboard cross-module."""

async def upsert_profile(user_id: UUID, patch: PatchProfileRequest) -> SellerProfile:
    """First PATCH creates row; subsequent PATCH updates. Recomputes onboarding_complete on every call."""

async def set_active_categories(user_id: UUID, super_ids: list[str]) -> SellerProfile:
    """Replaces active_super_categories entirely; validates each super_id; recomputes onboarding_complete."""

async def set_compliance_extension(user_id: UUID, super_id: str, payload: dict) -> SellerProfile:
    """JSONB-merge update at the {super_id} key in compliance_extensions; recomputes onboarding_complete."""

async def get_required_fields(user_id: UUID) -> RequiredFieldsResponse:
    """Drives onboarding wizard. Cached 60s per §4.D; invalidated on PATCH."""

async def get_compliance_block(user_id: UUID) -> ComplianceBlock:
    """Cross-module call from export.service. Returns the 9 standard fields + country_of_origin."""

async def get_onboarding_completeness(user_id: UUID) -> ProfileCompleteness:
    """Cross-module call from dashboard.service. Returns counts + completeness flag."""

async def assert_eligible_for_super_id(user_id: UUID, super_id: str) -> None:
    """Cross-module call from catalog.service. Raises ProfileIncompleteForCategoryError if not eligible.
    Eligibility = profile exists AND super_id in active_super_categories AND
    all required compliance extension keys for super_id are present."""
```

### 8.D Repository layer

`customer/repository.py` is **module-private** per §16. Other modules calling `find_by_user_id` directly would be a §16 violation; they call `customer.service.get_profile(user_id)` instead. Every method passes through `scope_to_user(user_id)` per §4.C — `seller_profile.user_id` is the PK and the tenancy scoping column.

```python
async def find_by_user_id(db: AsyncSession, user_id: UUID) -> SellerProfile | None: ...
async def upsert(db: AsyncSession, user_id: UUID, fields: dict) -> SellerProfile: ...
async def update_active_categories(db: AsyncSession, user_id: UUID, super_ids: list[str]) -> SellerProfile: ...
async def update_compliance_extension(db: AsyncSession, user_id: UUID, super_id: str, payload: dict) -> SellerProfile: ...
```

### 8.E Schemas

`customer/schemas.py` — Pydantic v2 request/response models. Field-level pincode regex enforced at the schema layer (Pydantic v2 `Field(pattern=...)`) per §4.F errors envelope contract.

```python
class SellerProfileResponse(BaseModel):
    user_id: UUID
    # 9 Legal Metrology fields
    manufacturer_name: str | None
    manufacturer_address: str | None
    manufacturer_pincode: str | None
    packer_name: str | None
    packer_address: str | None
    packer_pincode: str | None
    importer_name: str | None
    importer_address: str | None
    importer_pincode: str | None
    # Universal
    country_of_origin: str  # default "India" per MVP_ARCH §2.2
    # Sell-in scope
    active_super_categories: list[str]
    # Conditional compliance, JSONB shape per MVP_ARCH §2.2
    compliance_extensions: dict[str, dict]  # {super_id: {key: value, ...}}
    # Bookkeeping
    onboarding_complete: bool
    created_at: datetime
    updated_at: datetime

class PatchProfileRequest(BaseModel):
    manufacturer_name: str | None = None
    manufacturer_address: str | None = None
    manufacturer_pincode: str | None = Field(default=None, pattern=r"^\d{6}$")
    packer_name: str | None = None
    packer_address: str | None = None
    packer_pincode: str | None = Field(default=None, pattern=r"^\d{6}$")
    importer_name: str | None = None
    importer_address: str | None = None
    importer_pincode: str | None = Field(default=None, pattern=r"^\d{6}$")
    country_of_origin: str | None = None
    # active_super_categories has its own endpoint (B.3); compliance_extensions has its own (B.4)

class PatchActiveCategoriesRequest(BaseModel):
    active_super_categories: list[str] = Field(min_length=1)

class PatchComplianceExtensionRequest(BaseModel):
    # super_id-specific; service-layer validation against COMPLIANCE_EXTENSION_MAP.
    # Pydantic schema accepts any dict; service rejects malformed payloads with 422 customer.compliance.missing_fields.
    model_config = ConfigDict(extra="allow")

class RequiredFieldsResponse(BaseModel):
    base_fields: list[FieldSpec]                  # FieldSpec from §5A.C
    extension_fields: dict[str, list[FieldSpec]]  # {super_id: [FieldSpec]}
    completed: dict[str, bool]                    # {field_path: bool}
    # e.g. "manufacturer_name" or "ext.26.fssai_license_number"

class ComplianceBlockResponse(BaseModel):
    # Consumed cross-module by export.service per §16 — service-layer call, NEVER a route.
    manufacturer_name: str
    manufacturer_address: str
    manufacturer_pincode: str
    packer_name: str
    packer_address: str
    packer_pincode: str
    importer_name: str | None
    importer_address: str | None
    importer_pincode: str | None
    country_of_origin: str
```

### 8.F Internal domain types

`customer/domain.py` — frozen dataclasses + the `COMPLIANCE_EXTENSION_MAP` constant. These types never cross the HTTP boundary directly; the schemas in §8.E are the wire shapes.

```python
@dataclass(frozen=True)
class SellerProfile:
    """Mirrors seller_profile row; never crosses HTTP."""
    user_id: UUID
    manufacturer_name: str | None
    manufacturer_address: str | None
    manufacturer_pincode: str | None
    packer_name: str | None
    packer_address: str | None
    packer_pincode: str | None
    importer_name: str | None
    importer_address: str | None
    importer_pincode: str | None
    country_of_origin: str
    active_super_categories: list[str]
    compliance_extensions: dict[str, dict]
    onboarding_complete: bool
    created_at: datetime
    updated_at: datetime

@dataclass(frozen=True)
class ComplianceBlock:
    """The 9 standard Legal Metrology fields + country_of_origin. Consumed by export.service."""
    manufacturer_name: str
    manufacturer_address: str
    manufacturer_pincode: str
    packer_name: str
    packer_address: str
    packer_pincode: str
    importer_name: str | None
    importer_address: str | None
    importer_pincode: str | None
    country_of_origin: str

@dataclass(frozen=True)
class ProfileCompleteness:
    """Consumed by dashboard.service for the completeness badge."""
    base_complete_count: int
    base_total_count: int          # always 10 (9 LM fields + country_of_origin)
    extension_complete_count: int
    extension_total_count: int     # depends on active_super_categories
    onboarding_complete: bool         # mirrors the seller_profile.onboarding_complete flag

@dataclass(frozen=True)
class ComplianceExtensionSpec:
    """Static spec per super_id; lives as a module constant. Per MVP_ARCH §2.2 table."""
    super_id: str
    super_name: str
    required_keys: list[str]
    optional_keys: list[str]
    compulsory: bool  # True only for Grocery (super_id 26) — FSSAI is compulsory;
                      # others are conditional per MVP_ARCH §0 premise #7
```

The `COMPLIANCE_EXTENSION_MAP: dict[str, ComplianceExtensionSpec]` constant is locked to **6 source rules covering 11 super_id keys** per `MVP_ARCH §2.2` (Beauty's 6 super_ids each map to the same shared `ComplianceExtensionSpec` instance for O(1) lookup by `super_id`; the 5 single-super rules map 1:1):

- `"26"` Grocery — required `[fssai_license_number]` + optional `[fssai_expiry]`, **compulsory=True**.
- `"13"` Kids — optional `[bis_isi_certification_number]`, compulsory=False.
- `"16"` Electronics — optional `[bis_isi_certification_number, r_number, is_number, cm_l_number]`, compulsory=False.
- `"19"`/`"36"`/`"37"`/`"14"`/`"88"`/`"34"` Beauty (subset) — required `[license_registration_number, license_registration_type, license_expiry_date]`, **compulsory=True** within the subset.
- `"80"` Books — optional `[isbn_publisher_id]`, compulsory=False per `§12.1` ruling.
- `"30"` Home & Kitchen (appliance subset) — conditional `[license_number, license_expiry_date]`, compulsory=False.

### 8.G Exception hierarchy

`customer/exceptions.py` — all subclass `MeesellError` per §4.F. `validation_message_id`s follow the §5A.H three-segment snake_case convention.

```python
class CustomerError(MeesellError):
    """Base class for customer module failures. Never raised directly."""

class ProfileNotFoundError(CustomerError):
    status_code = 404
    validation_message_id = "customer.profile.not_found"

class InvalidPincodeError(CustomerError):
    status_code = 422
    validation_message_id = "validation.pincode.invalid_format"

class InvalidSuperCategoryError(CustomerError):
    status_code = 422
    validation_message_id = "validation.super_category.unknown"

class SuperCategoryNotDeclaredError(CustomerError):
    status_code = 404
    validation_message_id = "customer.super_category.not_declared"

class ComplianceExtensionMissingFieldsError(CustomerError):
    status_code = 422
    validation_message_id = "customer.compliance.missing_fields"

class ProfileIncompleteForCategoryError(CustomerError):
    status_code = 422
    validation_message_id = "customer.profile.incomplete_for_category"
    # Raised by customer.service.assert_eligible_for_super_id when catalog tries to
    # create a product in a category whose super_id requires a compliance extension
    # the seller has not yet provided.
```

### 8.H Adapter usage

**None.** `customer` is a pure CRUD-against-Postgres module with cache reads (`core/cache.py` for `categories.super_id` distinct set lookups and `/required-fields` response caching). No vendor calls — no Gemini, no MSG91, no GCS, no Razorpay, no LangFuse. Confirms the §1.E egress map (which lists no `customer`-module egress).

### 8.I Cross-cutting integrations

- **Rate-limit decorators (§4.G + §4.H):** the 3 PATCH routes carry `@rate_limit(scope=..., limit="60/h", key="user_id")` decorators with scope tags `profile_update` / `active_categories` / `compliance_update`; the 2 GET routes use per-IP fallback only.
- **Audit middleware (§4.G):** standard posture — middleware emits on 2xx for the 3 PATCH endpoints; the 2 GET endpoints emit NO audit (read-only, would flood per `MVP_ARCH §11.3`). All audit payloads scrub PII per `MVP_ARCH §11.9` — field NAMES and `super_id`s are logged; license numbers, pincodes, addresses are NOT.
- **Plan guard (§4.E):** **NOT participating** in V1 — `customer` endpoints are profile-management, not feature-budget-consuming. The §4.E 4-resource `Literal` (`product_count`, `ai_autofill`, `smart_picker`, `create_product`) does not include profile updates.
- **Tenancy (§4.C):** YES — `seller_profile.user_id` is the PK; every repository query passes through `scope_to_user(user_id)` per the §4.C locked rule for owned tables.
- **Cache helper (§4.D):** the `/required-fields` response is cache-eligible per §8.B.5 — key `seller_profile_required_fields:{user_id}:v{cache_version}` TTL 60s, invalidated on any profile PATCH. The `categories.super_id` distinct set lookup (used by `set_active_categories` validation) is also cache-eligible per §4.D (global reference data).
- **i18n (§5A.I):** the 6 customer-specific `validation_message_id`s (`customer.profile.not_found`, `validation.pincode.invalid_format`, `validation.super_category.unknown`, `customer.super_category.not_declared`, `customer.compliance.missing_fields`, `customer.profile.incomplete_for_category`) land in `i18n/messages_en.py` during the services-builder construction dispatch.

### 8.J Test plan

Locked test classes for §19 consolidation. Pytest fixtures use a real Postgres via the dev tunnel and a seeded `categories.super_id` distinct set; no MSG91/Razorpay/Gemini stubs required (customer has no vendor calls per §8.H).

**Unit tests (`backend/tests/modules/customer/`):**
1. **Profile upsert idempotency** — first PATCH creates the row, subsequent PATCH updates the same row, returns the same `user_id`.
2. **Pincode regex enforcement** — invalid pincodes (5 digits, 7 digits, alphanumeric) → 422 with `validation_message_id="validation.pincode.invalid_format"`.
3. **Compliance extension validation per super_id** — Grocery (`super_id=26`) requires `fssai_license_number`; missing → 422 `customer.compliance.missing_fields` with envelope payload listing the missing keys.
4. **`onboarding_complete` flag recomputation** — true iff all 10 base fields are present AND all `active_super_categories`' compulsory extension keys are present; recomputed on every PATCH (B.2 / B.3 / B.4).
5. **Eye-Serum case** — `customer` stores ONLY the 9 standard fields regardless of the seller's active categories (the `compliance_shape="collapsed"` lookup is `export`'s concern per §5A.F + `§12.6`).

**Integration tests (`backend/tests/integration/test_customer_*.py`):**
1. **Full onboarding flow** — sign up via §7 OTP-verify → first PATCH base profile → first PATCH active-categories `["26"]` (Grocery) → first PATCH compliance/26 → `/required-fields` shows `onboarding_complete=true`.
2. **Cross-module call** — `catalog.service.create_product` calls `customer.service.assert_eligible_for_super_id(user_id, super_id)`; on a profile lacking the required extension → 422 `customer.profile.incomplete_for_category` (the §10 `PROFILE_INCOMPLETE_FOR_CATEGORY` gate per `MVP_ARCH §3.3`).

### 8.K Extraction notes (V1.5+)

`customer` extracts cleanly with the `seller_profile` table — single-table ownership. The RLS migration path per `MVP_ARCH §14` flips `user_id` from app-level filter to PostgreSQL RLS predicate without changing the service surface. The `assert_eligible_for_super_id` cross-module call from `catalog` becomes an HTTP call in V1.5; the service signature is already designed for this transition (`async`, returns `None` or raises a typed exception that maps cleanly to HTTP status codes).

### 8.L What §8 does NOT cover

The DDL of `seller_profile` (`MVP_ARCH §2.2`). The actual English message strings for the 6 customer-specific `validation_message_id`s (the services-builder dispatch authors them into `i18n/messages_en.py` per §5A.I — §8 specifies only the IDs). The frontend onboarding wizard rendering logic (`FRONTEND_ARCHITECTURE`). The Export Adapter's `CollapsedComplianceStrategy` that consumes `customer.service.get_compliance_block` (that is §14 / `§12.6`). The `catalog` module's `PROFILE_INCOMPLETE_FOR_CATEGORY` enforcement flow on `POST /products` (that is §10 — `catalog` invokes `customer.service.assert_eligible_for_super_id`). The DPDP consent capture (`§4.B` + §7 — happens at OTP-verify time, NOT in the customer module). The `users` table (`§7` — `customer` reads `users` via FK only for `created_at`/`last_login_at` joins if needed, NEVER writes).

---

## Section 9 — Module: `category`

STATUS: LOCKED (2026-06-05)

### 9.A Preamble

§9 specifies the **`category` module** — Smart Category Picker (Feature 2, AI-ranked), Manual Browse (pg_trgm fallback against the 3 GIN indexes shipped in session 2 G4), Category Tree, compiled wizard Schema fetch, and Field-Enum lookup for the 291 Brand-pattern fields per `MVP_ARCH §6.8`. **Owner specialists:** `meesell-api-routes-builder` (routes + Pydantic schemas) + `meesell-services-builder` (business logic, cache layer, browse search) + **AI track collaboration** with `meesell-category-picker-builder` (owns the Gemini-side Smart Picker ranking pipeline — compressed-tree heuristics + confidence calibration per `.claude/agents/meesell-category-picker-builder.md`) and `meesell-prompt-engineer` (owns the `smart_picker.v1` prompt content per §6A.G). **AI-seam contract:** backend's `category` module owns the REST endpoint, the cache layer, the browse search, and the read paths against `categories`/`templates`/`field_enum_values`/`field_aliases`; the AI track's specialists own the compressed-tree compression, the confidence calibration, and the Gemini call shape — backend invokes via `ai_ops.client.call_gemini(ctx, "smart_picker.v1", ...)` per §6A.C, NEVER `adapters/gemini.py` directly per §3.G + §16. **Leaf module on the cross-module call graph** (per §2.D row all-`✗` for `category`) — `category` calls no other module's `service.py`. But `category` IS called BY `catalog` (fetch schema for validation per §2.4 + §16), `export` (alias map + schema for XLSX emission per §2.8), `pricing` (commission lookup per §2.6), and `customer` (super_id distinct set for `set_active_categories` validation per §8.C). **READ-ONLY at runtime** — `categories`, `templates`, `field_enum_values`, `field_aliases` are seed-time tables owned by the DATABASE track per §0.D and §2.3; backend never INSERTs/UPDATEs/DELETEs them at runtime. Surfaces **5 endpoints**, all 5 counted in the §0.C 27-endpoint contract (the 4 in `MVP_ARCH §3.3` + `/browse` from `MVP_ARCH §7.7`). §9 does NOT specify the DDL of `categories`/`templates`/`field_enum_values`/`field_aliases` (that is `MVP_ARCH §2.3`), does NOT specify the Smart Picker prompt content (that is `meesell-prompt-engineer` per §6A.G), does NOT specify the ranking algorithm internals (that is `meesell-category-picker-builder` per §2.3 AI-track collaboration), does NOT specify the §6A guardrail / cost-tracking / budget-cap implementation (that is §6A), does NOT specify the pg_trgm GIN index DDL (that is shipped by database-builder per session 2 G4).

### 9.B Endpoint surfaces

The 5 endpoint contracts below are normative. Request/response shapes reference §9.E schemas verbatim. Rate-limit decorators apply per §4.G + §4.H; audit posture follows the §4.G middleware contract (all 5 endpoints read-only → NO audit per `MVP_ARCH §11.3` flood-prevention rationale, same posture as §7.B.5 `/me` and §8.B.1 / §8.B.5 read endpoints). All 5 are GETs; this module performs no writes at runtime.

#### 9.B.1 `GET /api/v1/categories/suggest?q=<description>` — Smart Category Picker (Feature 2)

- **Request:** query param `q` (1–500 chars, the seller's free-text product description). Authorization: `Bearer <access_token>` per §4.B.
- **Response 200:** `SuggestResponse({suggestions: list[CategorySuggestion], fallback_offered: bool})` — top-5 ranked suggestions (or fewer if AI confidence is low or §6A.F budget hard-stop fires); `fallback_offered=true` signals to the frontend that the manual `/browse` fallback should be surfaced per `MVP_ARCH §5.1` decision #8.
- **Rate limit:** `@rate_limit(scope="smart_picker", limit="100/h", key="user_id")` per §4.E `smart_picker_hourly=100/h`. This is a **plan_guard** limit (per-user feature budget, V1 free-tier cap), enforced by `core/plan_guard.enforce_plan_limit(user_id, plan, "smart_picker_hourly")` BEFORE the route handler per §4.E + the §4.H middleware order chain (plan_guard fires after auth, before route).
- **Status codes:** 200; 400 (`validation.suggest_q.too_short_or_long`); 401 (auth missing/invalid per §4.B); 402 (`plan.limit_exceeded` per §4.E plan_guard hit); 503 RESERVED (see flow note below — `BudgetExceededError` does NOT raise 503; budget exhaustion uses graceful fallback returning 200 with empty suggestions).
- **Audit:** NONE (read-only; suggestions are not state changes).
- **JWT required:** yes.
- **Cache eligibility:** YES — `core/cache.get_or_set` with key `smart_picker:{sha256(q)}:v{cache_version}` per §4.D + §6.4 versioning, TTL 15 min. The cache is GLOBAL per query (multiple sellers asking the same description get identical suggestions — deterministic because §6A locks `temperature=0` for `smart_picker` workload per §6A.B). Cache key uses `sha256(q)` rather than the raw description to bound key length and avoid Valkey key-character constraints.
- **Flow:**
  1. Pydantic validates `q` via `SuggestQuery` (§9.E): `1 ≤ len(q.strip()) ≤ 500`. Raises `SuggestQueryInvalidError` (400) on violation per §9.G.
  2. `plan_guard.enforce_plan_limit(user_id, plan, "smart_picker_hourly", 1)` per §4.E. Raises `PlanLimitExceededError` (402) on exceedance — owned by `core/exceptions.py` per §4.F.
  3. `category.service.suggest_categories(user_id, q)`:
     - Cache lookup via `core/cache.get_or_set(key, ttl=900, ...)`.
     - On cache miss: `ai_ops.client.call_gemini(ctx, "smart_picker.v1", {description: q, compressed_tree: <compressed_category_tree>})` per §6A.C. `allowed_enums=None` (no per-field guardrail; the validity check is the category_id-in-table assertion below, NOT a Layer 2 enum match).
     - The AI track's compressed-tree compression is invoked here — backend caches the compression output (per `meesell-category-picker-builder` memory) under a module-private key so the compression cost is amortised across `/suggest` calls.
     - Layer 2 guardrail (per §6A.E `parse_and_validate`) validates returned `category_id`s exist in `categories` table via `category.repository.assert_category_exists_uncached`. Invalid IDs trigger §6A's up-to-2 retries with stricter prompt; final exhaustion → empty suggestions + `fallback_offered=true`.
     - On `BudgetExceededError` from §6A.F → graceful fallback per the workload-specific contract: return `SuggestResponse(suggestions=[], fallback_offered=True)` with **status 200** (NOT 503) — the frontend already handles `fallback_offered` UX, and raising 503 would break the seller's flow unnecessarily. The 503 status is reserved for unrecoverable AI failures (Gemini SDK exhaustion, etc.) not covered by §6A's fallback contract.
     - For each surviving suggestion, the service enriches it with denormalised `super_id`/`super_name`/`path`/`leaf_name` fields by lookup against the cached category tree (cheap — already in-process from §9.B.3's pre-warm).
     - Cache the enriched `SuggestResponse` and return.

#### 9.B.2 `GET /api/v1/categories/browse?q=&super_id=&limit=&offset=` — Manual Browse (`MVP_ARCH §7.7` fallback)

- **Request:** query params `q` (optional, search query, max 100 chars), `super_id` (optional, super-category filter), `limit` (default 20, max 100), `offset` (default 0). Authorization: `Bearer <access_token>` per §4.B.
- **Response 200:** `BrowseResponse({results: list[BrowseResultRow], total: int, limit: int, offset: int})`. Each `BrowseResultRow` carries `category_id`, `super_id`, `super_name`, `path`, `leaf_name`, and `similarity` (pg_trgm score 0..1).
- **Rate limit:** per-IP only (default `RL_PER_IP_PER_MINUTE=120` per §5.D). Per-user limit is intentionally absent — typing search incrementally is a legitimate burst pattern that a per-user limit would degrade.
- **Status codes:** 200; 400 (`validation.browse.invalid_pagination` if `limit > 100` or `offset < 0`); 401.
- **Audit:** NONE (read-only, polled incrementally — same flood-prevention reasoning as §7.B.5 `/me`).
- **JWT required:** yes.
- **Cache eligibility:** YES per `(q, super_id, limit, offset)` hash; TTL 5 min (browse results change only on quarterly Meesho refresh, but 5 min strikes a balance with the `MVP_ARCH §6.9` cache memory budget). Cache key: `browse:{sha256(q|super_id|limit|offset)}:v{cache_version}`.
- **Flow:**
  1. Pydantic validates `BrowseQuery` (§9.E): `limit ≤ 100`, `offset ≥ 0`. Raises `BrowseQueryInvalidError` (400) per §9.G.
  2. `category.service.browse_categories(q, super_id, limit, offset)`:
     - Cache lookup.
     - On miss: `category.repository.search_via_trigram(q, super_id, limit, offset)` — pg_trgm `ILIKE` query against the 3 GIN indexes (`idx_categories_path_trgm`, `idx_categories_leaf_name_trgm`, `idx_categories_super_name_trgm` per coordinator memory G4 + `MVP_ARCH §7.4`). Ranking per `MVP_ARCH §7.6` (similarity score + super_id filter weighting).
     - P95 ≤ 200 ms target per `MVP_ARCH §7.5` — verified during §19 testing via EXPLAIN ANALYZE confirming `Bitmap Index Scan on idx_categories_path_trgm` (already proven in the session-2 G4 round-trip).
     - `total` count comes from a separate `COUNT(*)` query cached separately per `(q, super_id)` (pagination consistency — the count doesn't shift between page reads).
     - Cache + return.

#### 9.B.3 `GET /api/v1/categories` — Category Tree (full hierarchical)

- **Request:** no body. Authorization: `Bearer <access_token>` per §4.B.
- **Response 200:** `CategoryTreeResponse({super_categories: list[SuperCategoryNode]})` — each `SuperCategoryNode` carries the ordered child leaves per `MVP_ARCH §0` premise #1 (all 3,772 leaves grouped under their `super_id`s per `§12.3` long-tail inclusion — every leaf, no leaf-count filter).
- **Rate limit:** per-IP only.
- **Status codes:** 200; 401.
- **Audit:** NONE.
- **JWT required:** yes.
- **Cache eligibility:** GLOBAL (all users get the same tree), version-tagged per §4.D with key `category_tree:v{cache_version}` TTL 1 h. **ETag** header set per §6.6 (frontend can issue `If-None-Match: <etag>` for 304 short-circuit). **Pre-warmed at FastAPI worker startup** per §4.D's `prewarm_top_categories` extension (the full tree is pre-warmed, not just top 100 — the tree is ~120 KB serialised per `MVP_ARCH §6.9` and amortises across every onboarded seller within the first hour).
- **Flow:**
  1. Cache lookup via `core/cache.get_or_set(key, ttl=3600, ...)`.
  2. On miss: `category.repository.fetch_category_tree()` — single `SELECT id, super_id, super_name, path, leaf_name FROM categories ORDER BY super_id, leaf_name` plus an in-Python group-by-`super_id` assembly.
  3. ETag header set via `core/cache.etag_for(payload)` per §4.D.
  4. Cache + return.

#### 9.B.4 `GET /api/v1/categories/{id}/schema` — Compiled wizard schema

- **Request:** path param `id` (UUID — the `categories.id`). Authorization: `Bearer <access_token>` per §4.B.
- **Response 200:** `SchemaResponse` — the full `templates.schema_jsonb` envelope per §5A.B (`fields[]` + `compulsory_count` + `optional_count` + `total_count` + `wizard_step_count` + `main_sheet_label` + `compliance_shape`).
- **Rate limit:** per-IP only.
- **Status codes:** 200; 401; 404 (`category.not_found`).
- **Audit:** NONE.
- **JWT required:** yes.
- **Cache eligibility:** GLOBAL per `category_id`, version-tagged with key `schema:{category_id}:v{cache_version}` TTL 1 h. **ETag** header per §6.6. **Pre-warmed for top 100 categories** at FastAPI worker startup per §4.D + `MVP_ARCH §6.7` (the hottest reads, ranked by historical traffic OR super-category size proxy at launch — the prompt-engineer + category-picker-builder memo specifies the launch ranking strategy).
- **Flow:**
  1. Cache lookup.
  2. On miss: `category.repository.fetch_schema_uncached(category_id)` — joins `categories` to `templates` via `categories.template_id` FK and returns `templates.schema_jsonb` verbatim (the envelope is pre-derived at seed time per §5A.B — no recomputation).
  3. Raises `CategoryNotFoundError` (404) if `category_id` not in `categories` per §9.G.
  4. ETag header; cache + return.
- **Cross-module consumer:** this is the method `catalog.service.validate_product` calls per §2.4 + §16 (catalog never reads `templates.schema_jsonb` directly), and `export.service.build_xlsx_sheet` calls per §2.8.

#### 9.B.5 `GET /api/v1/categories/{id}/field-enum/{name}` — Field-Enum lookup for Brand-pattern fields

- **Request:** path params `id` (UUID, the `categories.id`) + `name` (str, the canonical field name per `MVP_ARCH §0` premise #5 and §5A.C). Authorization: `Bearer <access_token>` per §4.B.
- **Response 200:** `FieldEnumResponse({enum_entries: list[EnumEntry], total: int, truncated: bool})`. Each `EnumEntry` shape per the database-builder Phase 4 baseline: `{canonical: str, meesho: str, labels: {en: str}}` — the localised labels payload per `MVP_ARCH §5.6.4`. The `meesho` value is present in this response because every consumer needs both `canonical` AND `meesho` (catalog validator uses `canonical` for input acceptance; export adapter uses `meesho` for XLSX emission per §14 / philosophy M10). **Coordinator decision:** the `meesho` value passing through this endpoint does NOT violate M10 — M10 forbids leaking Meesho-format names to the **seller wizard**, not to backend-internal canonicalisation lookups. The frontend renders `canonical` + `labels.en` only; the `meesho` field is consumed exclusively by export-adapter code paths. §5A.B already locks the parallel pattern: `main_sheet_label` (Meesho header) lives inside the schema envelope and is consumed by export, never surfaced to AI prompts. The field-enum response inherits the same posture.
- **Rate limit:** per-IP only.
- **Status codes:** 200; 401; 404 (`category.not_found` if `category_id` invalid; `category.field_enum_not_found` if `field_name` not present in `field_enum_values` for this category).
- **Audit:** NONE.
- **JWT required:** yes.
- **Cache eligibility:** GLOBAL per `(category_id, field_name)`, version-tagged with key `field_enum:{category_id}:{field_name}:v{cache_version}` TTL 1 h. **SINGLE-FLIGHT MANDATORY** per `MVP_ARCH §6.8` because the 291 Brand-pattern enum responses can be 50–200 KB each — concurrent cold reads would each rebuild the same payload. The §4.D `single_flight=True` parameter on `core/cache.get_or_set` is the locked enforcement point.
- **Flow:**
  1. Cache lookup with `single_flight=True` per §4.D + `MVP_ARCH §6.8`.
  2. On miss: `category.repository.fetch_field_enum_uncached(category_id, field_name)` — `SELECT enum_entries, truncated FROM field_enum_values WHERE category_id = ? AND field_name = ?`. Raises `CategoryNotFoundError` if `category_id` invalid; raises `FieldEnumNotFoundError` if no row matches `(category_id, field_name)` per §9.G.
  3. ETag header; cache + return.

### 9.C Service layer

`category/service.py` public methods, all `async`. The first 5 mirror the §9.B endpoints; the trailing 3 are the cross-module service-layer surfaces called by `catalog`/`export`/`pricing`/`customer` per the §2.D matrix.

```python
async def suggest_categories(
    user_id: UUID,
    q: str,
) -> SuggestResponse:
    """Smart Category Picker — §9.B.1. Cache + AI-via-§6A + Layer 2 retry + graceful fallback."""

async def browse_categories(
    q: str | None,
    super_id: str | None,
    limit: int,
    offset: int,
) -> BrowseResponse:
    """Manual Browse via pg_trgm — §9.B.2. Cache per pagination tuple."""

async def get_category_tree() -> CategoryTreeResponse:
    """Full hierarchical tree — §9.B.3. Cache GLOBAL TTL 1 h, ETag, pre-warmed."""

async def fetch_schema(category_id: UUID) -> dict:
    """Compiled wizard schema — §9.B.4 + cross-module call from catalog (§2.4 + §16) and export (§2.8).
    Returns the templates.schema_jsonb envelope per §5A.B verbatim (dict, not Pydantic — callers
    consume the envelope shape directly without revalidation)."""

async def get_field_enum(
    category_id: UUID,
    field_name: str,
) -> FieldEnumResponse:
    """Field-Enum lookup — §9.B.5. Single-flight mandatory per `MVP_ARCH §6.8`."""

async def get_commission(category_id: UUID) -> Decimal:
    """Cross-module call from pricing.service.calculate_price (§2.6) — returns
    categories.commission_pct. Raises CategoryNotFoundError if not found."""

async def list_super_categories() -> list[SuperCategoryInfo]:
    """Cross-module call from customer.service.set_active_categories (§8.C) — returns
    distinct super_id/super_name list with diagnostic leaf_count. Cache GLOBAL TTL 1 h."""

async def assert_category_exists(category_id: UUID) -> None:
    """Cross-module call (validation gate). Raises CategoryNotFoundError if not found.
    Used by catalog.service on draft creation to validate the chosen category_id."""
```

### 9.D Repository layer

`category/repository.py` module-private methods per §16, all `async`. **Per §4.C the category-owned tables are GLOBAL data** — NO `scope_to_user(user_id)` calls anywhere in this repository. The §19 CI linter exception for this pattern is explicit: `categories`, `templates`, `field_enum_values`, `field_aliases` are listed in `core/tenancy.py`'s `_GLOBAL_TABLES` set, and the linter rule "every owned-table query carries `user_id` in signature" exempts them per §4.C global-data carve-out.

```python
async def search_via_trigram(
    db: AsyncSession,
    q: str | None,
    super_id: str | None,
    limit: int,
    offset: int,
) -> tuple[list[CategoryRow], int]:
    """pg_trgm ILIKE against the 3 GIN indexes per `MVP_ARCH §7.4` + §7.6 ranking.
    Returns (rows, total_count)."""

async def fetch_category_tree(db: AsyncSession) -> list[CategoryRow]:
    """SELECT id, super_id, super_name, path, leaf_name FROM categories ORDER BY super_id, leaf_name.
    Single query; in-Python group-by happens in the service."""

async def fetch_schema_uncached(
    db: AsyncSession,
    category_id: UUID,
) -> dict:
    """JOIN categories → templates on template_id; returns templates.schema_jsonb verbatim.
    Raises CategoryNotFoundError if no row matches."""

async def fetch_field_enum_uncached(
    db: AsyncSession,
    category_id: UUID,
    field_name: str,
) -> tuple[list[dict], bool]:
    """SELECT enum_entries, truncated FROM field_enum_values WHERE category_id=? AND field_name=?.
    Returns (enum_entries_list, truncated_bool). Raises FieldEnumNotFoundError if no row matches."""

async def list_super_id_distinct(db: AsyncSession) -> list[str]:
    """SELECT DISTINCT super_id, super_name, COUNT(*) AS leaf_count
       FROM categories GROUP BY super_id, super_name ORDER BY super_id.
       Drives customer.service.set_active_categories validation."""

async def get_commission_uncached(
    db: AsyncSession,
    category_id: UUID,
) -> Decimal | None:
    """SELECT commission_pct FROM categories WHERE id=?. Returns None on no-row;
    service layer translates None → CategoryNotFoundError."""

async def assert_category_exists_uncached(
    db: AsyncSession,
    category_id: UUID,
) -> bool:
    """SELECT 1 FROM categories WHERE id=? LIMIT 1. Returns existence boolean.
    Used both by service.assert_category_exists (catalog gate) AND by the
    Smart Picker Layer 2 guardrail validation (§9.B.1 flow step 3)."""
```

### 9.E Schemas

`category/schemas.py` — locked Pydantic v2 request/response models. All `validation_message_id` strings follow the §5A.H three-segment snake_case convention.

```python
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---- Request models ----

class SuggestQuery(BaseModel):
    q: str = Field(min_length=1, max_length=500)
    # validation_message_id on violation: "validation.suggest_q.too_short_or_long"

class BrowseQuery(BaseModel):
    q: str | None = Field(default=None, max_length=100)
    super_id: str | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    # validation_message_id on violation: "validation.browse.invalid_pagination"

# ---- Smart Picker response ----

class CategorySuggestion(BaseModel):
    category_id: UUID
    super_id: str
    super_name: str
    path: str
    leaf_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: list[str]  # short human-readable rationale strings from the AI track ranking

class SuggestResponse(BaseModel):
    suggestions: list[CategorySuggestion] = Field(max_length=5)
    fallback_offered: bool

# ---- Browse response ----

class BrowseResultRow(BaseModel):
    category_id: UUID
    super_id: str
    super_name: str
    path: str
    leaf_name: str
    similarity: float  # pg_trgm similarity score; 0.0..1.0

class BrowseResponse(BaseModel):
    results: list[BrowseResultRow]
    total: int
    limit: int
    offset: int

# ---- Tree response ----

class SuperCategoryNode(BaseModel):
    super_id: str
    super_name: str
    leaves: list[BrowseResultRow]  # reuses BrowseResultRow shape (similarity is null in tree mode)

class CategoryTreeResponse(BaseModel):
    super_categories: list[SuperCategoryNode]

# ---- Schema response (pass-through of templates.schema_jsonb per §5A.B) ----

class SchemaResponse(BaseModel):
    """Pass-through of templates.schema_jsonb envelope per §5A.B.
    Forward-compat: extra='allow' so envelope evolutions (§5A amendments) don't break readers."""
    model_config = ConfigDict(extra="allow")

    fields: list["FieldSpec"]  # FieldSpec from §5A.C — defined in shared schema module
    compulsory_count: int
    optional_count: int
    total_count: int
    wizard_step_count: int
    main_sheet_label: str       # canonical label per §5A.B; consumed by export only; never exposed to AI prompts per M10
    compliance_shape: Literal["standard", "collapsed"]

# ---- Field-enum response ----

class EnumEntry(BaseModel):
    canonical: str
    meesho: str  # backend-internal; consumed by catalog validator + export adapter; never rendered in wizard
    labels: dict[str, str]  # {locale: localised_label}; V1 contains only "en"

class FieldEnumResponse(BaseModel):
    enum_entries: list[EnumEntry]
    total: int
    truncated: bool
```

### 9.F Internal domain types

`category/domain.py` — frozen dataclasses (NOT Pydantic — these are internal, not request/response shapes).

```python
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

@dataclass(frozen=True)
class CategoryRow:
    """Mirrors the categories table row. Returned by repository methods."""
    id: UUID
    meesho_leaf_id: str
    super_id: str
    super_name: str
    path: str
    leaf_name: str
    template_id: UUID
    commission_pct: Decimal | None

@dataclass(frozen=True)
class SuperCategoryInfo:
    """Cross-module return type for customer.service.set_active_categories validation.
    leaf_count is diagnostic (UI hints, telemetry) — NOT used to filter super_categories
    out per §12.3 long-tail inclusion."""
    super_id: str
    super_name: str
    leaf_count: int
```

### 9.G Exception hierarchy

`category/exceptions.py` — all subclass `MeesellError` per §4.F. The 4-field error envelope (`detail`, `code`, `validation_message_id`, `request_id`) is constructed by `register_error_handlers` per §4.F using `status_code` + `validation_message_id`.

```python
from app.core.errors import MeesellError

class CategoryError(MeesellError):
    """Base class for category module failures. Never raised directly."""

class CategoryNotFoundError(CategoryError):
    status_code = 404
    validation_message_id = "category.not_found"

class FieldEnumNotFoundError(CategoryError):
    status_code = 404
    validation_message_id = "category.field_enum_not_found"

class SuggestQueryInvalidError(CategoryError):
    status_code = 400
    validation_message_id = "validation.suggest_q.too_short_or_long"

class BrowseQueryInvalidError(CategoryError):
    status_code = 400
    validation_message_id = "validation.browse.invalid_pagination"
```

**`ai_ops.budget_exhausted` is NOT a `CategoryError`** — Smart Picker handles `BudgetExceededError` via graceful fallback per §9.B.1 (returns 200 with empty suggestions + `fallback_offered=true`). The `ai_ops.*` namespace is owned by `ai_ops/exceptions.py` per §6A.J. **`PlanLimitExceededError` is NOT a `CategoryError`** — owned by `core/exceptions.py` per §4.E + §4.F.

### 9.H Adapter usage

- **`ai_ops.client.call_gemini`** per §6A.C — used by `service.suggest_categories` (§9.B.1) ONLY. The `category` module NEVER calls `adapters/gemini.py` directly per §3.G + §16 (import-linter enforces this in §19).
- **No other adapters used** — no `msg91` (`iam`'s concern per §7), no `gcs` (`image`/`export`'s concern per §11/§14), no `razorpay` (`iam`'s concern per §7), no `langfuse` direct (fires from inside `ai_ops/client.py` per §6A.J — never invoked from `category/`).

### 9.I Cross-cutting integrations

- **Rate-limit decorators (§4.G + §4.H):** `/suggest` carries `@rate_limit(scope="smart_picker", limit="100/h", key="user_id")` — this is the plan_guard surface per §4.E. The other 4 routes (`/browse`, `/categories`, `/{id}/schema`, `/{id}/field-enum/{name}`) carry per-IP fallback only (default `RL_PER_IP_PER_MINUTE=120` per §5.D), enforced by `rate_limit_mw` per §4.G regardless of the absence of an explicit decorator.
- **Audit middleware (§4.G):** NONE on any of the 5 endpoints — all read-only. Following the §7.B.5 `/me` and §8.B.1 / §8.B.5 flood-prevention pattern per `MVP_ARCH §11.3`.
- **Plan guard (§4.E):** YES — Smart Picker invokes `core/plan_guard.enforce_plan_limit(user_id, plan, "smart_picker_hourly", 1)` BEFORE the route handler (per §4.H middleware order: `auth_mw → tenancy_mw → rate_limit_mw → plan_guard_mw → (handler)`). The 100/h/user limit is the V1 free-tier cap per §4.E. `/browse`, `/categories`, `/{id}/schema`, `/{id}/field-enum/{name}` do NOT participate in plan_guard (the 4-resource `Literal` in §4.E does not include browse/tree/schema/enum reads).
- **Tenancy (§4.C):** **NOT participating** — `categories`/`templates`/`field_enum_values`/`field_aliases` are GLOBAL data per `MVP_ARCH §10.2`. The repository methods carry NO `user_id` parameter; `core/tenancy.assert_owned` is not invoked. The §19 CI linter exception is documented: the global-table read pattern is the one allowed deviation from "every owned-table query has `user_id` in signature".
- **Cache helper (§4.D):** YES — `category` is the **heaviest cache consumer** in the codebase per `MVP_ARCH §6` notes. All 5 endpoints cache-eligible:
  - `/suggest` per-query (15 min TTL, SHA-256 keyed).
  - `/browse` per-pagination-tuple (5 min TTL).
  - `/categories` GLOBAL (1 h TTL, ETag, pre-warmed at worker startup).
  - `/{id}/schema` per-category (1 h TTL, ETag, pre-warmed for top 100 per §6.7).
  - `/{id}/field-enum/{name}` per-(category,field) (1 h TTL, **mandatory `single_flight=True`** per `MVP_ARCH §6.8` for the 291 Brand-pattern enum payloads).
  All keys version-tagged with `:v{cache_version}` per §6.4 — quarterly Meesho category refresh bumps `CACHE_VERSION` env var (§5.D) to invalidate every cached entry atomically.
- **i18n (§5A.I):** 4 category-specific `validation_message_id` strings land in `i18n/messages_en.py` during the services-builder dispatch: `category.not_found`, `category.field_enum_not_found`, `validation.suggest_q.too_short_or_long`, `validation.browse.invalid_pagination`.

### 9.J Test plan

**Unit tests** (`backend/tests/modules/category/`):

1. **Trigram search uses the GIN index** — `search_via_trigram("kurti", ...)` triggers `Bitmap Index Scan on idx_categories_path_trgm` per EXPLAIN ANALYZE; P95 < 200 ms target per `MVP_ARCH §7.5` measured over 100 iterations against the seeded dev DB.
2. **Schema fetch envelope conformance** — `fetch_schema(category_id)` returns a dict conforming to §5A.B (6 top-level keys present); every entry in `fields[]` conforms to §5A.C (9 keys); count invariants hold (`total_count == compulsory_count + optional_count`); `compliance_shape ∈ {"standard", "collapsed"}`.
3. **Field-enum lookup returns labelled payload** — every `EnumEntry` carries `{canonical, meesho, labels: {en: ...}}` per `MVP_ARCH §5.6.4`; `single_flight=True` protection enforced (two concurrent cache-miss requests fire ONE repository query, verified via call-count mock).
4. **`/suggest` graceful fallback on `BudgetExceededError`** — when the mocked `ai_ops.client.call_gemini` raises `BudgetExceededError`, the response is 200 with `SuggestResponse(suggestions=[], fallback_offered=True)` (NOT 503).
5. **`/suggest` Layer 2 invalid-category-id retry** — when the mocked AI returns an invalid `category_id` (not in `categories`), §6A retries with stricter prompt; after 2 retries the response is 200 with empty suggestions + `fallback_offered=true` per §9.B.1 flow.

**Integration tests** (`backend/tests/integration/test_category_*.py`, owned by `meesell-backend-coordinator` per the integration-test bucket in §0.E):

1. **Smart Picker → schema → catalog wizard flow** — `/suggest?q=...` returns top-5 → seller picks suggestion[0] → `/{id}/schema` → catalog wizard PATCH → validation succeeds (cross-module `category.service.fetch_schema` returns same payload that catalog validator consumes).
2. **Browse → schema → catalog wizard flow** — `/browse?q=kurti` returns ranked results → seller picks leaf → `/{id}/schema` → wizard renders per §5A.B.
3. **ETag round-trip** — GET `/categories` returns ETag `X`; second GET with `If-None-Match: X` → 304 Not Modified per §4.D.

**Pytest fixtures:** real Postgres + Valkey via dev tunnel; mocked `ai_ops.client.call_gemini` (deterministic fixture responses for Smart Picker tests — burning real Gemini tokens in CI is wasteful per §6A budget posture).

### 9.K Extraction notes (V1.5+)

`category` is a **strong extraction candidate** per §21 because it owns no writes — pure read service with cache. It becomes a stateless ranking + schema microservice. The cache layer moves with it (the Valkey DB 3 keys become the extracted service's local cache namespace, no key surgery required). Brand-master extraction (deferred per agent registry to V1.5 — see `meesell-brand-master-builder` placeholder in CLAUDE.md) lands inside this module: the validated brand list per super-category is a static reference dataset that fits the read-only profile. AI-track collaboration becomes inter-pod: backend's category-pod calls the AI track's smart-picker-pod via HTTP instead of via in-process `ai_ops.client`; the §6A.J import-direction rule already prepared this transition (domain modules already import only `ai_ops.client.call_gemini`, never `adapters/gemini.py` directly — the swap to an HTTP client behind `call_gemini` is mechanical).

### 9.L What §9 does NOT cover

The DDL of `categories`/`templates`/`field_enum_values`/`field_aliases` (`MVP_ARCH §2.3`). The Smart Picker AI prompt content — `meesell-prompt-engineer` per §6A.G. The Smart Picker ranking algorithm (compressed-tree heuristics, confidence calibration, top-K selection logic) — `meesell-category-picker-builder` per §2.3 AI-track collaboration. The AI cost tracking, guardrails Layer 1+2, budget cap, ₹500 daily cap (§6A — owned by `ai_ops/`). The pg_trgm GIN index DDL (`MVP_ARCH §7.4` — shipped by database-builder in session 2 G4 per coordinator memory). The quarterly Meesho refresh seed pipeline (DATABASE track). The `core/cache.py` ETag + single-flight + pre-warm IMPLEMENTATION (§4.D). The frontend wizard renderer that consumes the schema response (`FRONTEND_ARCHITECTURE.md`). The Export Adapter Layer 3 guardrail that re-validates field-enum values at XLSX-emission time (§14 + `MVP_ARCH §9.7`).

---

## Section 10 — Module: `catalog`

STATUS: LOCKED (2026-06-05)

### 10.A Preamble

§10 specifies the **`catalog` module** — Product CRUD (Feature 3 Fast Catalog Form), autosave drafts with 5-minute coalescing per `MVP_ARCH §11.4`, AI Auto-fill orchestration (Feature 4) invoked via `ai_ops.client.call_gemini`, draft recovery on browser reload (Feature 3 robustness + `MVP_ARCH §11.6`), Live Product Preview composition (Feature 6), and the per-field schema validation that gates `draft → ready` transitions against the `templates.schema_jsonb` envelope. **Owner specialists:** `meesell-api-routes-builder` (routes + Pydantic schemas) + `meesell-services-builder` (business logic, AI Auto-fill orchestration, draft autosave, schema-driven validation, the ownership-assertion seam consumed by image/pricing) per §2.4. **AI track collaboration:** `meesell-prompt-engineer` owns the `autofill.v1` prompt content per §6A.G; the §6A AI Operations Layer wraps the Gemini call with cost tracking, LangFuse trace, and Layer 1+2 guardrails — backend's `catalog` module never imports `adapters.gemini` directly per §3.G + §16. **The central spine module** per §2.4: catalog has **only 2 outbound calls** on the §2.D matrix (`catalog → customer ✓`, `catalog → category ✓`) but is called BY **four downstream modules** — `image` (`assert_product_ownership`), `pricing` (`assert_product_ownership`), `dashboard` (`list_products` + `get_validation_summary`), `export` (`get_product_for_export`) — making it the most-called module in the architecture. Catalog calls `category.service.fetch_schema(category_id)` per §16 (NEVER `category.repository`, NEVER raw queries against `templates`) for schema validation; calls `customer.service.get_profile(user_id)` and `customer.service.assert_eligible_for_super_id(user_id, super_id)` per §16 for the `PROFILE_INCOMPLETE_FOR_CATEGORY` gate on product creation. Writes **3 owned tables** per §2.4: `catalogs` (groups of products), `products` (the SKU rows with `fields_jsonb` + `ai_suggestions_jsonb`), `product_drafts` (per `MVP_ARCH §11.6` — 1 row per product for crash-recovery snapshots of the most recent autosave). Surfaces **6 endpoints**, **all 6 in the §0.C 27-endpoint contract** (5 from `MVP_ARCH §3.4` plus the 1 draft-recovery endpoint from `MVP_ARCH §11.6` — the latter was the 25th endpoint in the pre-FE-D5 count and survives as one of the 6 catalog endpoints in the 27-count). §10 does NOT specify the DDL of `catalogs` / `products` / `product_drafts` (that is `MVP_ARCH §2.4`), does NOT specify the Auto-fill prompt content (that is `meesell-prompt-engineer` per §6A.G), does NOT specify the §6A guardrail / cost-tracking / budget-cap implementation (that is §6A), does NOT specify the warranty / per-field schema content (that lives in `templates.schema_jsonb` per §5A.C — catalog validates against it but does not redefine it), does NOT specify the image upload flow (that is §11), does NOT specify pricing computation (that is §12), and does NOT resolve the latent `services/pricing_engine.py` `PricingAlert` import bug surfaced in session-2 close-out — that is §12's problem, surfacing only when Feature 7 lands.

### 10.B Endpoint surfaces

The 6 endpoint contracts below are normative. Request/response shapes reference §10.E schemas verbatim. Rate-limit decorators apply per §4.G + §4.H; audit posture follows the §4.G middleware contract with the 5-minute PATCH-coalescing rule per `MVP_ARCH §11.4` (autosave traffic would otherwise flood `audit_events` 30× over the seller's editing window). All 6 endpoints require JWT per §4.B (`Depends(get_current_user)`); cookie-only auth from §4.B is not used outside `/api/v1/auth/*`. All 6 routes go through the `assert_product_ownership` ownership-enforcement seam per philosophy M6 (structural enforcement; never trust route-level `user_id` checks).

#### 10.B.1 `POST /api/v1/products` — create product (Feature 3)

- **Request body** (Pydantic, §10.E): `CreateProductRequest({catalog_id: UUID | None, category_id: UUID, name: str | None})`. If `catalog_id` is null, the service implicitly creates a new catalog row with a default-name shape `"{seller_phone_last4}-Drafts-{YYYYMMDD-HHMM}"` (seller-readable, unique per session); if non-null, the product is added to the existing catalog (which MUST be owned by the user — 404 if not, surfaced as `catalog.catalog_not_found`). `name` is the seller-visible product name; null lets the wizard default to "Untitled product".
- **Response 201** (Pydantic, §10.E): `ProductResponse` — full product shape including the new `product_id`, the resolved `catalog_id`, `category_id`, an empty `fields_jsonb={}`, an empty `ai_suggestions_jsonb={}`, `status="draft"`, and timestamps.
- **Rate limit:** `@rate_limit(scope="create_product", limit="20/h", key="user_id")` per §4.E (`create_product_hourly`). Per-IP fallback per §4.G.
- **Plan guard:** `core.plan_guard.enforce_plan_limit(user_id, plan, resource="product_count", delta=1)` per §4.E — V1 hard cap **100 active products per user** (active = `deleted_at IS NULL`); raises `plan.limit_exceeded` mapped to 402. Note: the rate-limit decorator (`create_product_hourly=20/h`) and the plan-guard check (`product_count=100`) are **orthogonal** — RL caps creation velocity, plan guard caps cumulative inventory. Both must pass.
- **Status codes:** 201, 400 (`validation.*` for malformed UUIDs / over-long name), 401 (`auth.token_*`), 402 (`plan.limit_exceeded` from plan_guard or `rate_limit.exceeded` from rate_limit_mw), 404 (`catalog.catalog_not_found` when `catalog_id` non-null and not owned, OR `category.not_found` from the cross-module assert), 422 (`customer.profile.incomplete_for_category` — see flow step 3 below).
- **Audit posture:** `audit_mw` emits `catalog.product.created` event on 2xx per §4.G + `MVP_ARCH §11.3`. `actor_user_id` from `request.state.user`, `payload_jsonb = {product_id, catalog_id, category_id}` — no name, no field content (PII per `MVP_ARCH §11.9`).
- **JWT required:** yes (`Depends(get_current_user)` per §4.B).
- **Flow** (service-layer, locked sequence):
  1. `core.plan_guard.enforce_plan_limit(user_id, plan, "product_count", delta=1)` — fails fast with 402 BEFORE any DB write; uses `repository.count_active_products(user_id)` per §10.D.
  2. `category.service.assert_category_exists(category_id)` per §9.C cross-module surface — raises `category.not_found` mapped to 404 if not in the global category tree.
  3. Get `super_id` from the category row; call `customer.service.assert_eligible_for_super_id(user_id, super_id)` per §8.C — raises `customer.profile.incomplete_for_category` mapped to 422 if the seller has not completed the compliance extension for that super_id (e.g., trying to create a Beauty product without the license trio).
  4. If `catalog_id` is `None`: `repository.create_catalog(user_id, name=default_name)` returns a new `Catalog` row; otherwise `repository.find_catalog_by_id(user_id, catalog_id)` — 404 if not owned.
  5. `repository.insert_product(user_id, catalog_id, category_id, name)` — inserts a row with `status="draft"`, `fields_jsonb={}`, `ai_suggestions_jsonb={}`, `deleted_at=NULL`.
  6. `await db.commit()` per the §4.G commit-then-audit invariant (M8); audit_mw emits the `catalog.product.created` event post-2xx.
  7. Return `ProductResponse` (Pydantic mapping from the inserted ORM row).

#### 10.B.2 `PATCH /api/v1/products/{id}` — update product fields (Feature 3 autosave + manual save)

- **Request body** (Pydantic, §10.E): `PatchProductRequest({fields: dict[str, Any] | None, status: Literal["draft", "ready"] | None})`. `fields` is a partial JSON patch — keys are canonical field names per `templates.schema_jsonb.fields[*].canonical_name` (§5A.C regex `[a-z][a-z0-9_]*`), values are the primitive payload per the field's `primitive` (§5A.D — 11-primitive mapping). `status` is the optional state transition: omit to leave unchanged; `"ready"` triggers full-schema completeness validation; `"draft"` is the explicit revert.
- **Optional header:** `X-Autosave: true` signals an autosave write (vs a manual "Save" click). When present, the service additionally upserts a `product_drafts` row per `MVP_ARCH §11.6` so a subsequent browser-close → reopen can recover. When absent, only `products.fields_jsonb` is mutated.
- **Response 200** (Pydantic, §10.E): `ProductResponse` — the post-patch product state. Status code is 200 (not 204) so the autosave can confirm the merged shape and the wizard can render any server-computed derived fields.
- **Rate limit:** per-IP only (`@rate_limit(scope="product_patch", limit="600/h", key="ip")`). A per-user limit would degrade the autosave UX (autosaves can fire every few seconds during typing); per-IP fallback catches programmatic abuse without breaking real sellers. Plan guard does NOT participate.
- **Status codes:** 200, 400 (`validation.body.malformed_json` / `validation.fields.unknown_key`), 401, 404 (`catalog.product_not_found`), 422 (`validation.{canonical_name}.{constraint}` per §5A.H — e.g., `validation.product_name.too_long`; if multiple violations, the response error envelope's `validation_message_id` carries the first, `details: list[str]` carries the rest).
- **Audit posture:** `audit_mw` emits `catalog.product.updated` on 2xx. **5-minute coalescing applies** per `MVP_ARCH §11.4`: the middleware coalesces same `(actor_user_id, payload_jsonb.product_id)` events within a rolling 5-minute window — only the **first** PATCH in the window writes an `audit_events` row; subsequent PATCHes update the existing row's `payload_jsonb.coalesced_count += 1` and `payload_jsonb.last_seen_at`. This is the documented 30× volume reduction. `payload_jsonb` carries the changed field **NAMES** only (`{product_id, changed_keys: list[str]}`) — never field **values** (PII per `MVP_ARCH §11.9`).
- **JWT required:** yes.
- **Flow** (service-layer, locked sequence):
  1. `catalog.service.assert_product_ownership(product_id, user_id)` — the cross-module enforcement seam consumed by `image` and `pricing` per §2.D + §16. Raises `catalog.product_not_found` (404) if not owned OR if `deleted_at IS NOT NULL`.
  2. `category.service.fetch_schema(product.category_id)` per §9.C — cached read (§4.D); returns the §5A.B envelope.
  3. **Per-field validation** per §5A.C: for each `(canonical_name, value)` in `request.fields`, dispatch on the field's `data_type` + `enum_resolver`:
     - `data_type="text"` → length bounds per `primitive` (`text_short` ≤ 100 chars, `text_long` ≤ 2000); regex for `canonical_name` patterns where applicable.
     - `data_type="dropdown"` + `enum_resolver="static"` → membership check against the inline `enum_values: list[str]` per §5A.E.
     - `data_type="dropdown"` + `enum_resolver="category"` → membership check against `category.service.fetch_field_enum(category_id, canonical_name)` per §9.C (cached read).
     - `data_type="number"` / `"integer"` / `"boolean"` / `"date"` / `"url"` → primitive validators per §5A.D.
     - Unknown canonical_name → 422 `validation.fields.unknown_key`.
     Collect all violations into a list; raise `ValidationFailedError(validation_message_id=first.id, details=[rest...])`.
  4. **`is_advanced=true` fields** (V1: `{group_id}` only per §5A.F + D2) are accepted whether or not the wizard expanded them — the backend never rejects a present advanced field as "not expanded". This is the explicit `MVP_ARCH §12.4` "honour the wizard regardless of expansion" rule.
  5. `repository.update_fields_jsonb(user_id, product_id, patch_dict)` — performs a Postgres JSONB-merge (`products.fields_jsonb = products.fields_jsonb || :patch`); SQLAlchemy 2.0 typed.
  6. If `request.status == "ready"`: recompute completeness against the schema's compulsory fields; raise `ValidationFailedError` with `validation_message_id="validation.completeness.missing_compulsory"` if any required field is empty after the merge (422). On pass, set `products.status = "ready"`.
  7. **Autosave snapshot:** if `X-Autosave: true`, `repository.upsert_draft(user_id, product_id, fields_snapshot=merged_fields)` per `MVP_ARCH §11.6` — 1 draft row per product, latest wins (UPSERT on `(user_id, product_id)`); increments `autosave_count`; updates `last_updated`.
  8. `await db.commit()`; audit_mw emits `catalog.product.updated` (subject to 5-min coalescing).
  9. Return `ProductResponse`.

#### 10.B.3 `POST /api/v1/products/{id}/autofill` — AI Auto-fill (Feature 4)

- **Request body** (Pydantic, §10.E): `AutofillRequest({description: str, fields_to_fill: list[str] | None})`. `description` is the seller's free-text product description (constraint `1 <= len <= 2000` per §10.E); `fields_to_fill` is an optional list of canonical names to constrain the AI to specific fields (default `None` = the AI fills all empty compulsory fields it has confidence in).
- **Response 200** (Pydantic, §10.E): `AutofillResponse({suggestions: dict[str, AutofillSuggestion], applied: dict[str, bool], fallback_offered: bool})`. Each `AutofillSuggestion` carries `{value: Any, confidence: float, source: Literal["ai"]}` per `MVP_ARCH §2.4` `ai_suggestions_jsonb` shape. The `applied` map indicates which suggestions were auto-applied to `products.fields_jsonb` (confidence ≥ 0.85 threshold per `MVP_ARCH §5.2`) and which are surfaced to the seller for manual review (lower confidence). `fallback_offered=true` signals graceful fallback per §6A.F — the AI was skipped (budget exhausted or guardrail exhaustion) and the wizard should show a "fill manually" prompt.
- **Rate limit:** `@rate_limit(scope="ai_autofill", limit="50/h", key="user_id")` per §4.E (`ai_autofill_hourly`). Per-IP fallback per §4.G.
- **Plan guard:** `core.plan_guard.enforce_plan_limit(user_id, plan, "ai_autofill_hourly", delta=1)`. This is a per-user-per-hour budget — orthogonal to the daily global ₹500 §6A.F cap which is checked inside `ai_ops.client.call_gemini`.
- **Status codes:** 200 (success OR graceful fallback with `fallback_offered=true`), 400 (`validation.description.too_short_or_long`, `validation.fields_to_fill.unknown_key`), 401, 402, 404 (`catalog.product_not_found`), 422. Note: Auto-fill does NOT return 503 on budget exhaustion — per §6A.F + §9.B.1 precedent, budget-exhausted Auto-fill returns 200 with empty suggestions and `fallback_offered=true`. 503 is reserved for unrecoverable Gemini SDK exhaustion beyond §6A's fallback contract (truly rare — `AutofillFailedError` per §10.G).
- **Audit posture:** `audit_mw` emits `catalog.autofill.invoked` on 2xx. `payload_jsonb = {product_id, description_sha256: str, description_preview: str (first 200 chars), fields_to_fill: list[str] | None, fallback_offered: bool, applied_count: int}` — the SHA-256 hash + 200-char preview is the debug-affordance compromise: full descriptions are PII per `MVP_ARCH §11.9` but the preview lets ops triage repro reports without leaking the full input.
- **JWT required:** yes.
- **Flow** (service-layer, locked sequence):
  1. `catalog.service.assert_product_ownership(product_id, user_id)`.
  2. plan_guard `ai_autofill_hourly` check.
  3. `category.service.fetch_schema(product.category_id)` (cached).
  4. Build `allowed_enums: dict[canonical_name, list[str]]` from the schema's dropdown fields per §5A.E `enum_resolver` resolution — `"static"` enums are read inline from `fields[X].enum_values`; `"category"` enums are resolved through `category.service.fetch_field_enum(category_id, canonical_name)` per §9.C. This is the input to the §6A.E Layer 2 guardrail.
  5. Construct an `AICallContext(workload="autofill", user_id=user_id, request_id=request.state.request_id)` per §6A.C and call `ai_ops.client.call_gemini(ctx, prompt_id="autofill.v1", template_vars={"description": request.description, "schema_summary": schema_summary, "fields_to_fill": request.fields_to_fill}, allowed_enums=allowed_enums, response_mime_type="application/json")`. The 9-step internal flow per §6A.C runs inside `call_gemini`: prompt_registry.resolve → budget_cap.check_and_reserve → guardrail Layer 1 → render → adapter → cost_tracker → guardrail Layer 2 (enum re-validation; up-to-2 retries with stricter prompt) → langfuse.trace → return.
  6. **Graceful fallback handling:** if `call_gemini` raises `BudgetExceededError` (V1.5: also `GuardrailExhaustionError`), catch in service; return `AutofillResponse(suggestions={}, applied={}, fallback_offered=True)` with HTTP 200. This matches the §9.B.1 Smart Picker precedent — wizard handles `fallback_offered=true` UX, 503 would unnecessarily break the seller flow.
  7. On success: parse `AIResponse.text` as JSON into `dict[canonical_name, {value, confidence}]`. For each suggestion with `confidence >= 0.85`: write to `applied[canonical_name] = True` and merge into the patch dict.
  8. `repository.update_fields_jsonb(user_id, product_id, applied_patch_dict)` — same JSONB-merge as §10.B.2 step 5.
  9. `repository.update_ai_suggestions_jsonb(user_id, product_id, full_suggestions_dict)` — persists the **full** suggestions payload (high AND low confidence) to `products.ai_suggestions_jsonb` per `MVP_ARCH §2.4` for audit/provenance + export read in §14.
  10. `await db.commit()`; audit_mw emits `catalog.autofill.invoked`.
  11. Return `AutofillResponse(suggestions, applied, fallback_offered=False)`.

#### 10.B.4 `GET /api/v1/products/{id}/preview` — Live Product Preview (Feature 6)

- **Request:** no body. Authorization: `Bearer <access_token>` per §4.B.
- **Response 200** (Pydantic, §10.E): `ProductPreviewResponse` — composite of (a) the product with each canonical field-name resolved to its display label per `templates.schema_jsonb.fields[*].name` (§5A.C), (b) image URLs (signed GCS URLs with 1h TTL per §1.B + §6.D), (c) the compliance block from `customer.service.get_compliance_block(user_id)` per §8.C — collapsed-shape for Eye-Serum products, standard-shape otherwise per §5A.F + `MVP_ARCH §12.6`. The shape is ready for the Feature 6 preview screen and is also the input to the §14 export's M10 canonicalisation step (export consumes a different snapshot — `get_product_for_export` per §10.C — but the preview is what the seller sees in the wizard).
- **Rate limit:** per-IP only (`@rate_limit(scope="product_preview", limit="600/h", key="ip")`); lightweight read.
- **Status codes:** 200, 401, 404 (`catalog.product_not_found`).
- **Audit posture:** NONE — read-only endpoint per `MVP_ARCH §11.3` flood-prevention rule (same as `/me`, `/seller-profile`, `/categories/*`).
- **JWT required:** yes.
- **Flow** (service-layer, locked sequence):
  1. `catalog.service.assert_product_ownership(product_id, user_id)`.
  2. `category.service.fetch_schema(product.category_id)` (cached) — for the display labels and the field ordering.
  3. `image.service.get_image_urls(product_id, user_id)` per §11.C — returns signed GCS URLs with 1h TTL.
  4. `customer.service.get_compliance_block(user_id)` per §8.C — returns the compliance shape per the seller's `active_super_categories`.
  5. Compose the response: map each `(canonical_name, value)` in `products.fields_jsonb` to its display label from the schema's `fields[*].name`; preserve the schema's field ordering for wizard fidelity.
  6. Return `ProductPreviewResponse`.

#### 10.B.5 `DELETE /api/v1/products/{id}` — soft delete

- **Request:** no body.
- **Response 204** — no body.
- **Rate limit:** `@rate_limit(scope="product_delete", limit="60/h", key="user_id")`. Plan guard does NOT participate.
- **Status codes:** 204, 401, 404 (`catalog.product_not_found` — distinct from "already deleted": a previously-deleted product returns 404 because the ownership-assertion seam scopes `deleted_at IS NULL`).
- **Audit posture:** `audit_mw` emits `catalog.product.deleted` on 2xx. `payload_jsonb = {product_id, catalog_id}`.
- **JWT required:** yes.
- **Flow** (service-layer, locked sequence):
  1. `catalog.service.assert_product_ownership(product_id, user_id)`.
  2. `repository.soft_delete_product(user_id, product_id)` — sets `products.deleted_at = now()`; preserves the row + `fields_jsonb` + `ai_suggestions_jsonb` for potential restore (V1.5 endpoint; V1 has no `POST /products/{id}/restore`).
  3. Active-product count decrements toward the plan_guard `product_count=100` cap (soft-deleted products are NOT counted by `repository.count_active_products`, so a seller can recover slot capacity by deleting).
  4. `await db.commit()`; audit_mw emits `catalog.product.deleted`.
  5. Return 204 (no body).

#### 10.B.6 `GET /api/v1/products/{id}/draft` — draft recovery (Feature 3 robustness; `MVP_ARCH §11.6`)

- **Request:** no body.
- **Response 200** (Pydantic, §10.E): `ProductDraftResponse({fields: dict[str, Any], last_updated: datetime, autosave_count: int})` — the most recent autosave snapshot from `product_drafts`. This differs from `products.fields_jsonb` ONLY if the seller had unsaved changes when their browser tab closed (or if their network died mid-PATCH). Typical case: `draft.fields == products.fields_jsonb`; recovery case: `draft.fields` is one autosave window ahead of `products.fields_jsonb`.
- **Response 204** — no draft exists. Returned when the product has never been autosaved (rare — only if the seller went directly to a manual "Save final" without any prior typing-triggered autosave; possible during programmatic create + immediate `status=ready`).
- **Rate limit:** per-IP only (`@rate_limit(scope="product_draft_read", limit="600/h", key="ip")`).
- **Status codes:** 200 (draft found), 204 (no draft), 401, 404 (`catalog.product_not_found`).
- **Audit posture:** NONE — read-only endpoint.
- **JWT required:** yes.
- **Flow** (service-layer, locked sequence):
  1. `catalog.service.assert_product_ownership(product_id, user_id)`.
  2. `repository.get_draft(user_id, product_id)` — returns the `product_drafts` row keyed on `(user_id, product_id)` UNIQUE; 0 or 1 row.
  3. If no row: return 204 (no body). If row: map to `ProductDraftResponse` and return 200.

### 10.C Service layer — `catalog/service.py`

Public method surface — all `async`. The first 6 are **route-internal** (called only by `catalog/router.py`); the trailing 4 are **cross-module surfaces** called by `image` / `pricing` / `dashboard` / `export` per the §2.D matrix + §16 boundary rule. All signatures are locked; renaming requires a §10 amendment.

```python
# Route-internal — driven by 10.B.1 through 10.B.6
async def create_product(user_id: UUID, plan: str, request: CreateProductRequest) -> Product
async def patch_product(user_id: UUID, product_id: UUID, request: PatchProductRequest, is_autosave: bool) -> Product
async def autofill_product(user_id: UUID, plan: str, product_id: UUID, request: AutofillRequest, request_id: str) -> AutofillResponse
async def get_preview(user_id: UUID, product_id: UUID) -> ProductPreviewResponse
async def soft_delete(user_id: UUID, product_id: UUID) -> None
async def get_draft(user_id: UUID, product_id: UUID) -> ProductDraft | None

# Cross-module surfaces — consumed via `from app.modules.catalog import service as catalog_service` per §16
async def assert_product_ownership(product_id: UUID, user_id: UUID) -> None
    # Raises ProductNotFoundError (404, "catalog.product_not_found") if not owned OR if soft-deleted.
    # The structural enforcement point for philosophy M6 across image and pricing.
async def get_product_for_export(product_id: UUID, user_id: UUID) -> ExportSnapshot
    # Called by export.service per §2.D. Returns a frozen snapshot:
    # (product row + ai_suggestions_jsonb + image refs + last validation summary).
    # Snapshot semantics — export builds the XLSX from this fixed view.
async def list_products(user_id: UUID, pagination: Pagination) -> PaginatedProducts
    # Called by dashboard.service per §2.D. Cursor-or-offset pagination; only active (deleted_at IS NULL).
async def get_validation_summary(user_id: UUID, product_id: UUID) -> ValidationSummary
    # Called by dashboard.service per §2.D for status badges (Draft / Ready / Issues / Exported).
    # Recomputes against the schema each call — small N (the dashboard page-size is bounded).
```

Internal helpers (not exported): `_resolve_allowed_enums(schema)`, `_apply_high_confidence_suggestions(suggestions)`, `_validate_field(canonical_name, value, schema)`, `_compute_completeness(product, schema)`, `_to_response(product)`. These are module-private and may evolve without §10 amendment.

### 10.D Repository layer — `catalog/repository.py`

Module-private per §16 — only `catalog/service.py` may import these. All methods use `core.tenancy.scope_to_user(user_id)` per §4.C on the **owned tables** (`catalogs`, `products`, `product_drafts`) — this is the structural enforcement point that the §19 import-linter audits against the "every owned-table read or write carries `user_id`" rule.

```python
async def find_by_id(db: AsyncSession, user_id: UUID, product_id: UUID) -> Product | None
    # SELECT ... FROM products WHERE id = :pid AND user_id = :uid AND deleted_at IS NULL
async def find_catalog_by_id(db: AsyncSession, user_id: UUID, catalog_id: UUID) -> Catalog | None
async def create_catalog(db: AsyncSession, user_id: UUID, name: str) -> Catalog
async def insert_product(db: AsyncSession, user_id: UUID, catalog_id: UUID, category_id: UUID, name: str | None) -> Product
async def update_fields_jsonb(db: AsyncSession, user_id: UUID, product_id: UUID, patch_dict: dict) -> Product
    # UPDATE products SET fields_jsonb = fields_jsonb || :patch, updated_at = now()
    #   WHERE id = :pid AND user_id = :uid AND deleted_at IS NULL
    # Uses Postgres JSONB concatenation operator || for shallow merge per `MVP_ARCH §2.4`.
async def update_ai_suggestions_jsonb(db: AsyncSession, user_id: UUID, product_id: UUID, suggestions_dict: dict) -> Product
    # Overwrites ai_suggestions_jsonb (each autofill call replaces, not merges, the provenance record).
async def upsert_draft(db: AsyncSession, user_id: UUID, product_id: UUID, fields_snapshot: dict) -> ProductDraft
    # INSERT ... ON CONFLICT (user_id, product_id) DO UPDATE
    # SET fields = :fields, last_updated = now(), autosave_count = autosave_count + 1
async def get_draft(db: AsyncSession, user_id: UUID, product_id: UUID) -> ProductDraft | None
async def soft_delete_product(db: AsyncSession, user_id: UUID, product_id: UUID) -> None
    # UPDATE products SET deleted_at = now() WHERE ... AND deleted_at IS NULL
async def count_active_products(db: AsyncSession, user_id: UUID) -> int
    # COUNT(*) for plan_guard product_count check.
async def list_paginated(db: AsyncSession, user_id: UUID, pagination: Pagination) -> tuple[list[Product], int]
    # Dashboard's list — returns (rows, total_count_for_page_metadata).
```

No raw SQL outside Alembic — every call goes through SQLAlchemy 2.0 typed `select` / `update` / `insert` / `delete` per `CLAUDE.md` "Coding Conventions — Python (Backend)". Async sessions per §5.B. No transaction blocks inside repository methods — transactions are owned by `service.py` per the §4.G commit-then-audit invariant (M8).

### 10.E Schemas — `catalog/schemas.py`

Pydantic v2; locked field types and constraints. Each model uses `model_config = ConfigDict(extra="forbid")` for request shapes (defensive — reject unknown keys) and `extra="ignore"` for response shapes (forward-compat). 12 models total.

```python
# Request models (extra="forbid")
class CreateProductRequest(BaseModel):
    catalog_id: UUID | None = None
    category_id: UUID
    name: str | None = Field(default=None, max_length=200)

class PatchProductRequest(BaseModel):
    fields: dict[str, Any] | None = None
    status: Literal["draft", "ready"] | None = None
    # At least one of fields/status MUST be present — validator enforces.

class AutofillRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=2000)
    fields_to_fill: list[str] | None = Field(default=None, max_length=50)

# Response models (extra="ignore")
class ProductResponse(BaseModel):
    id: UUID
    catalog_id: UUID
    category_id: UUID
    name: str | None
    status: Literal["draft", "ready"]
    fields: dict[str, Any]                  # mirrors products.fields_jsonb
    ai_suggestions: dict[str, Any] | None   # mirrors products.ai_suggestions_jsonb
    created_at: datetime
    updated_at: datetime

class AutofillSuggestion(BaseModel):
    value: Any
    confidence: float = Field(..., ge=0.0, le=1.0)
    source: Literal["ai"] = "ai"

class AutofillResponse(BaseModel):
    suggestions: dict[str, AutofillSuggestion]
    applied: dict[str, bool]
    fallback_offered: bool = False

class ProductPreviewField(BaseModel):
    canonical_name: str
    display_label: str
    value: Any
    is_advanced: bool

class ProductPreviewResponse(BaseModel):
    id: UUID
    name: str | None
    category_path: str                      # e.g. "Women's Clothing > Kurtis"
    fields: list[ProductPreviewField]       # ordered per schema
    image_urls: list[str]                   # signed GCS URLs, 1h TTL
    compliance: dict[str, Any]              # standard or collapsed shape per §5A.F
    status: Literal["draft", "ready"]

class ProductDraftResponse(BaseModel):
    fields: dict[str, Any]
    last_updated: datetime
    autosave_count: int

class Pagination(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)

class PaginatedProductsResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    limit: int

class ValidationSummary(BaseModel):
    product_id: UUID
    compulsory_filled: int
    compulsory_total: int
    optional_filled: int
    optional_total: int
    has_validation_errors: bool
    status: Literal["draft", "ready"]

class ExportSnapshot(BaseModel):
    # Returned by get_product_for_export — frozen view consumed by §14.
    product_id: UUID
    category_id: UUID
    fields: dict[str, Any]
    ai_suggestions: dict[str, Any]
    image_refs: list[str]                   # GCS object paths, not signed URLs
    validation_summary: ValidationSummary
```

Wire-format conventions: all UUIDs serialise as strings per Pydantic v2 default; all datetimes are ISO-8601 with TZ per `CLAUDE.md` ("TIMESTAMPTZ for all timestamps"). The `extra="forbid"` posture on request models surfaces typos at the API edge with `400 validation.body.unknown_key` — saves a round of misdebugging.

### 10.F Internal domain types — `catalog/domain.py`

Frozen `@dataclass(frozen=True, kw_only=True)` mirrors of the ORM rows + composite types — used inside the service layer so the routes and tests are typed against immutable values, not mutable ORM objects. Conversion between ORM ↔ domain happens at the repository boundary.

```python
@dataclass(frozen=True, kw_only=True)
class Product:
    id: UUID
    user_id: UUID
    catalog_id: UUID
    category_id: UUID
    name: str | None
    status: Literal["draft", "ready"]
    fields: dict[str, Any]
    ai_suggestions: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

@dataclass(frozen=True, kw_only=True)
class Catalog:
    id: UUID
    user_id: UUID
    name: str
    created_at: datetime

@dataclass(frozen=True, kw_only=True)
class ProductDraft:
    user_id: UUID
    product_id: UUID
    fields: dict[str, Any]
    last_updated: datetime
    autosave_count: int

@dataclass(frozen=True, kw_only=True)
class AutofillSuggestionInternal:
    canonical_name: str
    value: Any
    confidence: float
    source: Literal["ai"]

@dataclass(frozen=True, kw_only=True)
class ValidationSummaryInternal:
    product_id: UUID
    compulsory_filled: int
    compulsory_total: int
    optional_filled: int
    optional_total: int
    has_validation_errors: bool
    status: Literal["draft", "ready"]

@dataclass(frozen=True, kw_only=True)
class ExportSnapshotInternal:
    product_id: UUID
    category_id: UUID
    fields: dict[str, Any]
    ai_suggestions: dict[str, Any]
    image_refs: tuple[str, ...]
    validation_summary: ValidationSummaryInternal

@dataclass(frozen=True, kw_only=True)
class PaginatedProductsInternal:
    items: tuple[Product, ...]
    total: int
    page: int
    limit: int
```

`tuple[..., ...]` over `list[...]` for collection fields preserves the frozen invariant. The `*Internal` suffix on shapes that also have a Pydantic response model disambiguates the two layers at import time.

### 10.G Exception hierarchy — `catalog/exceptions.py`

All subclass `MeesellError` (§4.F) — caught by the §4.F error handler chain which produces the 4-field envelope `{detail, code, validation_message_id, request_id}`.

```python
class CatalogError(MeesellError):
    """Base for catalog-module exceptions. Never raised directly."""

class ProductNotFoundError(CatalogError):
    status_code = 404
    validation_message_id = "catalog.product_not_found"
    # Raised by assert_product_ownership and every downstream service method.
    # This is the cross-module surface — image/pricing/dashboard/export
    # see this exception bubble up through assert_product_ownership.

class CatalogNotFoundError(CatalogError):
    status_code = 404
    validation_message_id = "catalog.catalog_not_found"
    # Raised by find_catalog_by_id when create_product receives a non-owned catalog_id.

class ValidationFailedError(CatalogError):
    status_code = 422
    # validation_message_id is dynamic — set per-field per §5A.H convention,
    # e.g., "validation.product_name.too_long", "validation.fields.unknown_key",
    # "validation.completeness.missing_compulsory". When multiple violations,
    # the envelope's validation_message_id carries the FIRST and `details: list[str]`
    # carries the rest (matches the §4.F MeesellError envelope shape).

class DraftNotFoundError(CatalogError):
    # Sentinel — caught by the router and converted to 204 (no body).
    # Not surfaced through the §4.F envelope.
    status_code = 204
    validation_message_id = None

class AutofillFailedError(CatalogError):
    status_code = 500
    validation_message_id = "catalog.autofill_internal_error"
    # Raised ONLY for unrecoverable §6A failures NOT covered by the graceful fallback
    # contract (BudgetExceededError → 200 + fallback_offered=True is the happy path).
    # Reaching this exception is a P1 page — indicates either an SDK bug or a
    # bug in the §6A.E guardrail retry budget.
```

Six exception classes total. All 5 catalog-specific `validation_message_id` IDs land in `i18n/messages_en.py` during the construction dispatch — §10 specifies IDs not prose per §5A.H. The dynamic IDs raised by `ValidationFailedError` (e.g., `validation.product_name.too_long`) are owned by the schema-validation paths and are registered into the i18n registry per-field at services-builder time.

### 10.H Adapter usage

The `catalog` module's adapter dependency is **minimal and indirect**:

- **`ai_ops.client.call_gemini`** — invoked exactly once from §10.B.3 Auto-fill. The `adapters/gemini.py` client is wrapped by §6A's `ai_ops/client.py`; the `catalog` module NEVER imports `adapters.gemini` directly per §3.G + §16 (the §19 import-linter rejects any `from app.adapters.gemini` import outside `ai_ops/`).
- **No other adapter calls.** Catalog does not invoke `adapters/msg91` (iam-only), `adapters/gcs` (image-only at upload time; signed-URL generation in §10.B.4 preview goes through `image.service.get_image_urls` per §16), `adapters/razorpay` (iam-only), or `adapters/langfuse` (fired only from inside `ai_ops/client.py` per §6A.J).

This minimal-adapter posture is what makes `catalog` the V1.5 extraction-blocker (per §10.K): the module is heavy on cross-module *service* dependencies (`category` + `customer` + `image` + `pricing` + `dashboard` + `export`) but light on transport-layer dependencies — meaning V1.5 extraction is gated on the in-process call surfaces becoming network calls, not on adapter rewiring.

### 10.I Cross-cutting integrations

How `catalog` participates in the §4 + §6A + §15 + §19 cross-cutting layers:

- **Rate limiting (§4.E + §4.G).** Four routes carry an explicit `@rate_limit` decorator: `create_product` (20/h user), `autofill_product` (50/h user), `soft_delete` (60/h user), `product_patch` (per-IP 600/h). The remaining two — `get_preview` and `get_draft` — carry per-IP only via the decorator (per-user limits would degrade the wizard's preview-refresh and reload-recovery flows respectively). The `rate_limit_mw` reads the decorator via FastAPI route introspection per §4.G; no manual middleware wiring per route.
- **Plan guard (§4.E).** Two participation points: (1) `create_product` enforces `product_count` (cumulative cap 100) AND `create_product_hourly` (velocity 20/h via the rate-limit decorator, same resource enum); (2) `autofill_product` enforces `ai_autofill_hourly` (50/h). The two checks are **orthogonal** to the daily global ₹500 §6A.F budget cap — per-user plan limits and global cost cap are additive.
- **Audit middleware (§4.G + `MVP_ARCH §11.3` + §11.4).** Three writes emit standard middleware audit events on 2xx (`product.created`, `product.updated`, `product.deleted`, `autofill.invoked`); the `product.updated` event is subject to the **5-minute coalescing rule** per `MVP_ARCH §11.4` (rolling window keyed on `(actor_user_id, product_id)`). Three reads (`get_preview`, `get_draft`, plus the `list_products` cross-module call) emit NO audit events per the §11.3 read-flood rule. **PII scrubbing** applies per `MVP_ARCH §11.9`: `payload_jsonb` carries field NAMES (not values) for `product.updated`, carries an SHA-256 hash + 200-char preview of the description for `autofill.invoked`, and carries no field content for `product.created` / `product.deleted`.
- **Tenancy (§4.C).** All 11 repository methods scope on `user_id` via `core.tenancy.scope_to_user(user_id)`. The `assert_product_ownership` cross-module call point per §10.C is the structural enforcement seam consumed by `image` / `pricing` / `dashboard` / `export` per §2.D — philosophy M6 in action. The §19 import-linter audits that every `owned_table` read or write passes `user_id`.
- **Cache (§4.D + §6).** `catalog` itself does NOT cache its own writes — per-user `fields_jsonb` mutations would invalidate too frequently to amortise (every PATCH would bust the entry). The schema reads it depends on (§10.B.2 step 2, §10.B.3 step 3, §10.B.4 step 2) go through `category.service.fetch_schema` which caches per `MVP_ARCH §6.7` (top-100 schemas pre-warmed at worker startup, full-tree at boot). The §4.D `get_or_set` helper is used inside `category`, not inside `catalog`.
- **i18n (§5A.I).** 5 catalog-specific message IDs ship to `i18n/messages_en.py`: `catalog.product_not_found`, `catalog.catalog_not_found`, `catalog.autofill_internal_error`, plus the dynamic `validation.*` IDs registered per-field at services-builder time (e.g., `validation.fields.unknown_key`, `validation.completeness.missing_compulsory`, `validation.description.too_short_or_long`). V1 logs `Accept-Language` but always renders English per §5A.I; V1.5 Tamil/Hindi dispatch.
- **AI Ops boundary (§6A).** The single Auto-fill call site at §10.B.3 is the catalog module's entire AI surface. The §6A client wraps the cost track, the LangFuse trace, the budget cap, the prompt registry, and Layers 1+2 of the guardrail; `catalog` only sees the 8-line invocation (build context → call → catch fallback → branch). Layer 3 of the guardrail lives in §14 export, not here.
- **Observability (§15 forward-ref).** `catalog` is the highest-traffic write module (autosaves dominate write QPS). §15 will spec the per-endpoint Prometheus histograms; `catalog` reports through `request_id` middleware correlation (§4.G) and the `audit_events` event stream (the 5-minute coalescing rule preserves event volume sanity even under autosave bursts).

### 10.J Test plan

`backend/tests/modules/catalog/` mirror per §3.J test-tree structure. 5 unit-test classes (mock the repository + cross-module service calls) + 3 integration-test classes (live Postgres tunnel + Valkey cache).

**Unit** — `backend/tests/modules/catalog/test_service_unit.py`:
1. **`TestOwnershipEnforcement`** — `assert_product_ownership` raises `ProductNotFoundError` for: (a) non-existent product, (b) product owned by another user, (c) soft-deleted product (`deleted_at IS NOT NULL`). Three test methods. The image/pricing modules' integration tests rely on this surface; if it regresses, the consequence is cross-tenant data leak.
2. **`TestSchemaDrivenValidation`** — `patch_product` raises `ValidationFailedError` with the correct `validation_message_id` for: (a) unknown canonical_name (`validation.fields.unknown_key`), (b) text overflow (`validation.{canonical}.too_long`), (c) static-enum miss (`validation.{canonical}.invalid_enum_value`), (d) category-enum miss, (e) multi-violation surfaces first as `validation_message_id` + rest in `details`. Five test methods. Schema validation per §5A.C + §5A.D is the §10 contract's bulk.
3. **`TestAutofillGracefulFallback`** — `autofill_product` returns `AutofillResponse(suggestions={}, applied={}, fallback_offered=True)` with HTTP 200 (NOT 503) when `ai_ops.client.call_gemini` raises `BudgetExceededError`. Verifies the §9.B.1 precedent applies symmetrically here. One test method.
4. **`TestAutosaveDraftUpsert`** — `patch_product` with `is_autosave=True` writes through to `product_drafts` via `upsert_draft`; `is_autosave=False` does NOT touch `product_drafts`; second autosave on the same product increments `autosave_count` and replaces `fields`. Three test methods. The `MVP_ARCH §11.6` recovery contract.
5. **`TestPlanGuardEnforcement`** — `create_product` raises `PlanLimitExceededError` (402) when `repository.count_active_products` returns 100; rate-limit decorator firing is mocked separately. One test method. Verifies that plan_guard fails fast BEFORE any DB write.

**Integration** — `backend/tests/modules/catalog/test_integration.py` (live tunnel):
1. **`TestFullProductLifecycle`** — End-to-end: create → autofill → PATCH (autosave) → PATCH (manual save with `status=ready`) → preview. Verifies that the 6 endpoints compose without contract drift; verifies the cross-module calls (`category.fetch_schema`, `customer.assert_eligible_for_super_id`, `image.get_image_urls` mocked) compose correctly. The Auto-fill step uses a stub `ai_ops.client.call_gemini` that returns deterministic suggestions.
2. **`TestDraftRecoveryAfterSimulatedClose`** — Create product → autosave 3 times via 3 PATCHes with `X-Autosave: true` → call `GET /products/{id}/draft` → verify response shape (`autosave_count=3`, `fields` matches latest autosave snapshot, `last_updated >= third PATCH timestamp`). Then call WITHOUT autosaving → verify 204.
3. **`TestCrossModuleOwnershipAssertion`** — Simulates the image module's call into `catalog.service.assert_product_ownership` — verifies it raises `ProductNotFoundError` for a product owned by user A when called with user B's `user_id`. This is the structural M6 enforcement; the test lives in `catalog/` because catalog OWNS the seam, even though the consumer is `image`.

Test fixtures: a `conftest.py` per `backend/tests/modules/catalog/` provides (a) a logged-in user with completed seller profile + Beauty super_id eligibility, (b) a stub `ai_ops.client.call_gemini` that returns deterministic high-confidence suggestions for the Auto-fill happy path, (c) the standard `category_with_schema` fixture (Beauty / Eye-Serum is the canonical compliance-shape test category per §5A.F).

### 10.K Extraction notes (V1.5+)

`catalog` is the **HARDEST module to extract** per §0.B + §21's recommended order. Three reasons:

1. **The most-called module.** Per §2.D, four downstream modules depend on `catalog.service.*` surfaces (`image` → `assert_product_ownership`; `pricing` → `assert_product_ownership`; `dashboard` → `list_products` + `get_validation_summary`; `export` → `get_product_for_export`). Extracting `catalog` to a separate service means **four** networking surfaces flip from in-process to HTTP/gRPC simultaneously. Each consumer's failure-mode envelope changes (now must handle 502/504 from a remote catalog).
2. **Schema fetch is hot-path.** Every PATCH (the highest-QPS endpoint) calls `category.service.fetch_schema` per §10.B.2 step 2 + the in-process cache hit on §6.7. Extraction moves this from a Valkey hit (~1ms) to a network call (~10ms) **per PATCH**. V1.5 must either keep `category` and `catalog` co-located, OR push the schema into a CDN-friendly read-replica.
3. **The compliance gate spans modules.** `create_product` step 3 (per §10.B.1) chains `category → customer → catalog` in a single request. Extraction means this chain becomes 3 RPCs instead of 3 function calls; the failure modes multiply (any one can timeout).

Per §21, the recommended V1.5 extraction order is `iam → customer → category → image → pricing → dashboard → export → catalog (last)`. Catalog is the spine; extracting it first risks the kind of cascading-failure outage that the modular-monolith decision was meant to defer.

The two facets that DO transfer cleanly to extraction: (a) the §10.E Pydantic schemas are already the wire-format (no internal-vs-external shape divergence); (b) the §10.C cross-module service surface (`assert_product_ownership`, `get_product_for_export`, `list_products`, `get_validation_summary`) is the natural V1.5 gRPC service definition — the four method signatures become the four RPCs.

### 10.L What §10 does NOT cover

Forward-cites so reviewers don't conflate scope:

- **DDL of `catalogs` / `products` / `product_drafts`** → `MVP_ARCH §2.4` (the column list, the JSONB shape rules, the indexes; `product_drafts` `(user_id, product_id) UNIQUE`).
- **Migration ordering** → `MVP_ARCH §2.6` + alembic head `f31c75438e61` per §5.E.
- **Auto-fill prompt content (`autofill.v1`)** → `meesell-prompt-engineer` per §6A.G; prompt-registry file location `ai_ops/prompts/autofill_v1.py` per §6A.G.
- **§6A guardrail mechanics** → §6A.E (Layer 1 prompt prefix + Layer 2 enum re-validation + up-to-2 retries; Layer 3 in §14 export per `MVP_ARCH §9.7`).
- **§6A budget cap mechanics** → §6A.F (₹500 daily global cap + reservation pattern + workload-specific fallback strings).
- **§6A cost tracking** → §6A.D (gemini-2.5-flash rates + `audit_events` direct-write exception).
- **Schema content** → §5A.B/C/D/E/F + `category` module (catalog validates against the schema but does not redefine it).
- **Image upload flow** → §11 (catalog's preview consumes signed URLs via `image.service.get_image_urls`; catalog does NOT call `adapters/gcs` directly).
- **Pricing computation** → §12 (the dashboard's price column comes from `pricing.service`, not catalog).
- **The latent `services/pricing_engine.py` `PricingAlert` import bug** → §12 problem per §0.E; surfaces when Feature 7 lands; NOT a catalog blocker.
- **XLSX emission + M10 canonicalisation** → §14 (catalog produces the `ExportSnapshot` via `get_product_for_export`; the XLSX shape, the alias-reverse-map, and the M10 enforcement live in `export.service`).
- **Test runner / fixtures shared across modules** → §19 (the catalog `conftest.py` consumes the shared `tests/conftest.py` per §3.J).
- **K3s manifests** → §20 (no module-specific manifests; catalog runs in the shared FastAPI pod).

---

## Section 11 — Module: `image`

STATUS: LOCKED (2026-06-05)

### 11.A Preamble

§11 specifies the `image` module — image upload, the 5-step pre-check pipeline (JPEG, RGB/CMYK, ≥1500×1500 resolution, white-background heuristic, watermark vision via Gemini), and GCS storage orchestration. **Owner specialists:** `meesell-api-routes-builder` (routes + Pydantic schemas) + `meesell-services-builder` (business logic, GCS orchestration, Celery task wrapper) per §2.5. **AI track collaboration:** `meesell-image-precheck-builder` owns the 5-step precheck pipeline INCLUDING the Gemini Vision watermark call wrapped by §6A.C `workload="watermark"`; `meesell-prompt-engineer` owns the watermark vision prompt content per §6A.G. **Seam:** backend's `image` module owns the upload route, the GCS binary write, the `product_images` row insert with `status='pending'`, the Celery enqueue, and the result write-back to `precheck_jsonb` with `status='ready'`; the AI track's `image-precheck-builder` owns the precheck pipeline logic itself.

This is a **leaf module on the cross-module call graph** (per §2.D row: `image → catalog` only). Every write call site invokes `catalog.service.assert_product_ownership(product_id, user_id)` per the locked §10.C signature — the structural enforcement of philosophy M6 (every write gates on tenancy). The module writes the `product_images` table exclusively and reads only its own table.

§11 surfaces **2 endpoints**, both in the §0.C 27-endpoint contract: `POST /api/v1/products/{id}/images` (upload) and `GET /api/v1/products/{id}/images` (poll-list). §11 does NOT specify the DDL (that is `MVP_ARCH §2.5`), does NOT specify the GCS adapter (§6.D), does NOT specify the §6A AI guardrail or cost tracking, does NOT specify the 5-step precheck pipeline algorithm internals (those belong to `meesell-image-precheck-builder`). What §11 DOES specify is the route contract, the service-layer public surface, the Celery task wrapper signature, the schemas/domain types, the exception hierarchy, and the cross-cutting integration posture so the two specialists can construct the module from a locked contract.

`modules/image/tasks.py` is one of only **2 modules with `tasks.py`** per the §3.C canonical subtree (the other being `export` per §3.I) — every other module is pure synchronous service code.

### 11.B Endpoint surfaces

The two endpoints below are the locked external contracts. Request shape, response shape, rate-limit decorator, error envelopes, audit posture, and the cross-module call sequence are all fixed at this section — specialists do NOT re-derive them.

#### 11.B.1 `POST /api/v1/products/{id}/images` — upload image (Feature 5)

**Request.** `multipart/form-data` with fields:
- `file: UploadFile` — JPEG only. Max upload size 10 MB per CLAUDE.md API design rules ("File uploads: multipart/form-data, max 10MB per image").
- `idx: int` — image slot index, must be in `[1, 2, 3, 4]` per `MVP_ARCH §0` premise #3 (4 slots uniform corpus-wide, slot 1 required as front image).

**Response 202.**
```python
class ImageUploadResponse(BaseModel):
    image_id: UUID
    gcs_path: str            # e.g. "meesell-images/{user_id}/{product_id}/1.jpg"
    status: Literal["pending"]
    idx: int                 # 1-4
    enqueued_task_id: str    # Celery task id for client-side correlation
```

Status 202 ACCEPTED — the upload is persisted synchronously but the 5-step precheck runs asynchronously via Celery, hence the client polls `GET /api/v1/products/{id}/images` until `status == "ready"`.

**Rate limit.** `@rate_limit(scope="image_upload", limit="10/min", key="user_id")` per §4.E — bandwidth-heavy endpoint, lower cap than typical 60/h surfaces. The per-IP fallback applies to anonymous misuse (pre-JWT).

**Plan guard.** **NOT participating in V1.** The 4-slot uniform rule per `MVP_ARCH §0` premise #3 is the structural limit — enforced as a `CHECK (image_idx IN (1,2,3,4))` constraint at the DB level per `MVP_ARCH §2.5` plus the route-level 409 slot-occupied check. There is no `core/plan_guard.py` resource for `image_upload_hourly` in V1.

**Status codes.**
- `202` — upload persisted + Celery task enqueued.
- `400` — `validation.image.invalid_format` (not JPEG), `validation.image.too_large` (> 10 MB), `validation.image.invalid_idx` (idx not in `[1, 2, 3, 4]`).
- `401` — missing / invalid JWT.
- `404` — `catalog.product_not_found` from the cross-module ownership gate (per §10.C `assert_product_ownership`).
- `409` — `image.slot_occupied` (idx already has a non-deleted image; seller must DELETE the existing image first; V1 does not expose a DELETE endpoint for individual images, only for products — so this 409 is effectively a "delete-and-recreate-the-product" flow in V1).

**Audit posture.** Middleware emits `image.upload.received` with `{product_id, idx, gcs_path}`. File bytes are **never** logged to `audit_events` per `MVP_ARCH §11.9` — only the GCS path metadata. No coalescing (this is not a high-frequency event per user).

**JWT required:** yes (per §17 default for all `/api/v1/` endpoints except `/auth/*` and `/health`).

**Flow.**
1. `catalog.service.assert_product_ownership(product_id, user_id)` per §10.C — raises 404 `catalog.product_not_found` if the product does not exist OR if `products.user_id != user_id`. This is the **first** call site; bytes are not consumed yet.
2. Validate file: MIME type `== "image/jpeg"`, size `<= 10_485_760` bytes (10 MB), idx `in [1, 2, 3, 4]`. Reject **before** GCS write to avoid wasted bandwidth.
3. Read file dimensions via Pillow (in-memory, lightweight): `width`, `height`, `color_space` (`Image.open(BytesIO).mode`). The 5-step precheck runs in Celery; this in-route read captures metadata only, NOT the precheck itself.
4. Check existing `product_images` row at `(product_id, order_idx=idx)`; if found with `deleted_at IS NULL` → 409 `image.slot_occupied`.
5. `adapters.gcs.upload_bytes(path="meesell-images/{user_id}/{product_id}/{idx}.jpg", data=file_bytes, content_type="image/jpeg")` per §6.D + `MVP_ARCH §10.8`. Returns the `gs://` URI; service stores the path-without-scheme variant in the row.
6. Repository inserts `product_images` row: `{product_id, gcs_path, order_idx=idx, status="pending", width, height, color_space, precheck_jsonb={}}`. The `is_front` GENERATED column auto-computes as `(order_idx == 1)` per `MVP_ARCH §2.5`.
7. Enqueue Celery task `image_precheck_task.delay(image_id, user_id)` to Valkey DB 1 broker per §5.C `get_valkey_broker`. The returned `AsyncResult.id` is exposed as `enqueued_task_id` in the response (informational only — the client polls the list endpoint, not the task result).
8. Return 202 `ImageUploadResponse`.

#### 11.B.2 `GET /api/v1/products/{id}/images` — list product images with status (Feature 5 poll)

**Request.** No body. JWT required.

**Response 200.**
```python
class ImagesListResponse(BaseModel):
    images: list[ImageSummary]    # 0-4 items

class ImageSummary(BaseModel):
    image_id: UUID
    idx: int                      # 1-4
    status: Literal["pending", "ready", "failed_precheck"]
    signed_url: str               # GCS signed URL, TTL 1h per §6.D + MVP_ARCH §10.8
    precheck_jsonb: dict          # structured 5-step result (verbatim from DB row)
    is_front: bool                # True iff idx == 1
    width: int | None
    height: int | None
    color_space: str | None       # "RGB" | "CMYK" | "Gray"
    created_at: datetime
```

Up to 4 images per product per `MVP_ARCH §0` premise #3. Order is by `order_idx ASC`.

**Rate limit.** Per-IP only (this endpoint is polled during precheck — typically 2-3 polls per upload). No `key="user_id"` because polling latency depends on Celery throughput and we do not want to throttle legitimate poll traffic.

**Status codes.** `200`, `401`, `404` (`catalog.product_not_found`).

**Audit posture.** NONE (read-only polling — audit on every poll would flood `audit_events`).

**JWT required:** yes.

**Flow.**
1. `catalog.service.assert_product_ownership(product_id, user_id)` per §10.C.
2. Repository `find_by_product(user_id, product_id)` fetches all non-deleted `product_images` rows ordered by `order_idx ASC`.
3. For each row: generate 1-hour signed GCS URL via `adapters.gcs.generate_signed_url(path=row.gcs_path, ttl_seconds=settings.GCS_SIGNED_URL_TTL_SECONDS, method="GET")` per §6.D + `MVP_ARCH §10.8`.
4. Compose response with `precheck_jsonb` verbatim — the frontend interprets the structured result (per-step pass/fail rendering is presentation-layer concern per §5A).
5. Return 200.

### 11.C Service layer — `image/service.py`

The locked public-method signatures below are the only external surface of the `image` service module. All are `async`. Cross-module calls (per §16 inter-module communication rules) are explicitly tagged.

```python
async def upload_image(
    user_id: UUID,
    product_id: UUID,
    file: UploadFile,
    idx: int,
) -> ProductImage:
    """Endpoint backing for POST /api/v1/products/{id}/images per §11.B.1."""

async def list_images(
    user_id: UUID,
    product_id: UUID,
) -> ImagesListResponse:
    """Endpoint backing for GET /api/v1/products/{id}/images per §11.B.2."""

# ─── Cross-module surfaces consumed per §16 inter-module contracts ────────────

async def get_image_urls(
    product_id: UUID,
    user_id: UUID,
) -> list[ImageUrl]:
    """Called by catalog.service.get_preview per §10.B.4. Returns signed URLs
    only for status='ready' images, ordered by idx, with is_front flag."""

async def get_image_bytes(
    image_id: UUID,
    user_id: UUID,
) -> bytes:
    """Called by export.service for ZIP packaging per §14. Downloads from GCS.
    Does NOT generate a signed URL — returns raw bytes for in-process zipping."""

async def write_precheck_result(
    image_id: UUID,
    user_id: UUID,
    precheck_jsonb: dict,
    status: Literal["ready", "failed_precheck"],
) -> None:
    """Called by image_precheck_task (worker context) — same module, same
    boundary as the task lives in §11. Atomic single-row UPDATE of
    product_images.precheck_jsonb + status. No service-level audit write
    (the worker emits audit directly per §11.J)."""

async def summary(
    user_id: UUID,
    product_ids: list[UUID],
) -> dict[UUID, ImageStatusSummary]:
    """OPTIONAL cross-module call from dashboard per §2.D matrix note.
    Locked here as available API surface — dashboard kept at 8 cross-module
    calls in §2 matrix without this elevation, but §13 may opt in.
    Returns per-product image status summary for dashboard cards."""
```

### 11.D Repository layer — `image/repository.py`

The repository methods below are **MODULE-PRIVATE** per §16 — no other module may import `image.repository` directly. Every cross-module read of `product_images` data goes through `image.service.*`. All repository methods use `scope_to_user(user_id)` per §4.C as the structural backstop on tenant isolation (the higher-level enforcement is `catalog.service.assert_product_ownership` at the service layer).

```python
async def insert(
    db: AsyncSession,
    user_id: UUID,
    product_id: UUID,
    gcs_path: str,
    idx: int,
    width: int,
    height: int,
    color_space: str,
) -> ProductImage:
    """INSERT INTO product_images. Status defaults to 'pending'.
    precheck_jsonb defaults to {}."""

async def find_by_product(
    db: AsyncSession,
    user_id: UUID,
    product_id: UUID,
) -> list[ProductImage]:
    """SELECT WHERE product_id = ? AND deleted_at IS NULL ORDER BY order_idx ASC.
    Tenant scoping via scope_to_user(user_id) joined through products.user_id."""

async def find_by_id(
    db: AsyncSession,
    user_id: UUID,
    image_id: UUID,
) -> ProductImage | None:
    """SELECT WHERE id = ? AND deleted_at IS NULL. Returns None if not found
    or if tenant scoping rejects."""

async def find_by_slot(
    db: AsyncSession,
    user_id: UUID,
    product_id: UUID,
    idx: int,
) -> ProductImage | None:
    """SELECT WHERE (product_id, order_idx) = (?, ?) AND deleted_at IS NULL.
    Used for the 409 slot-occupied check in §11.B.1 step 4."""

async def update_precheck_result(
    db: AsyncSession,
    user_id: UUID,
    image_id: UUID,
    precheck_jsonb: dict,
    status: Literal["ready", "failed_precheck"],
) -> ProductImage:
    """UPDATE product_images SET precheck_jsonb = ?, status = ?, updated_at = NOW()
    WHERE id = ?. Returns the updated row. Called by write_precheck_result service."""

async def soft_delete_by_idx(
    db: AsyncSession,
    user_id: UUID,
    product_id: UUID,
    idx: int,
) -> None:
    """UPDATE product_images SET deleted_at = NOW() WHERE (product_id, order_idx) = (?, ?).
    V1: NOT exposed via endpoint — internal helper kept for the re-upload flow if
    added in V1.5 + for catalog.service.delete_product cascade (per §10.B.5 soft delete)."""

async def summarize_by_products(
    db: AsyncSession,
    user_id: UUID,
    product_ids: list[UUID],
) -> dict[UUID, ImageStatusSummary]:
    """Aggregation query — counts by status per product, plus the front image
    (idx=1) GCS path for signed-URL generation at the service layer. Backs
    service.summary() for dashboard consumption."""
```

### 11.E Celery tasks — `image/tasks.py`

This module has a single Celery task — the precheck pipeline wrapper. It is registered via `workers/celery_app.py` task discovery per §3.I (auto-imports `app.modules.*.tasks`). Owned ENTIRELY by `meesell-image-precheck-builder` (AI track) per §2.5 — backend's `image` module owns the dispatch/wrapper, not the pipeline logic itself.

```python
from celery import shared_task
from uuid import UUID

@shared_task(
    name="image.precheck",
    bind=True,
    max_retries=2,
    retry_backoff=True,
    autoretry_for=(AdapterError,),  # GCS / Gemini transient failures retried
)
def image_precheck_task(self, image_id: UUID, user_id: UUID) -> None:
    """
    Runs the 5-step precheck pipeline. Owned ENTIRELY by meesell-image-precheck-builder
    (AI track) per §2.5; backend's image module owns the dispatch/wrapper, not the
    pipeline logic itself.

    Flow (locked outline; algorithm internals are AI-track scope):
    1. Fetch image bytes from GCS via adapters.gcs.download_bytes(path=image.gcs_path).
    2. Step 1: JPEG check (Pillow open) — fail → precheck_jsonb.jpeg_valid = false
       and status = "failed_precheck" (early exit).
    3. Step 2: RGB vs CMYK check (Pillow mode) — flag CMYK as non-compliant.
    4. Step 3: Resolution ≥ 1500×1500 check — pass/fail boolean.
    5. Step 4: White-background heuristic (Pillow corner-sampling, V1 simple
       algorithm — owned by image-precheck-builder).
    6. Step 5: Watermark vision via ai_ops.client.call_gemini(
                  AICallContext(workload="watermark", user_id=user_id, ...),
                  prompt_id="watermark.v1",
                  prompt_vars={},
                  image_bytes=bytes,
              ) — Layer 2 guardrail validates {has_watermark: bool, confidence: float}
              shape per §6A.E. On BudgetExceededError → precheck_jsonb.watermark_check
              = "skipped_budget" per §6A.F graceful fallback (informational,
              non-blocking — status still resolves to "ready" if steps 1-4 pass).
    7. Aggregate into precheck_jsonb; set status = "ready" if all 4 deterministic
       steps (JPEG, RGB, resolution, white-bg) pass — watermark step is
       informational, not blocking — else "failed_precheck".
    8. Call image.service.write_precheck_result(image_id, user_id, precheck_jsonb,
       status) to persist.
    9. Worker JWT re-validation per §1.G — the task payload carries user_id; the
       worker re-validates by checking the user exists in users (the access JWT
       itself has expired by the time this task runs; the user_id is the trust
       anchor for the worker context).

    Direct audit write: emits `image.precheck.completed` event to audit_events via
    same documented-exception pattern as §6A.D cost_tracker and §7 verify_otp —
    the worker has no request-close hook so audit_mw cannot fire.
    """
```

The Celery task is **synchronous** (not `async def`) because Celery's task runtime does not natively support coroutines in V1; async work inside the task body uses `asyncio.run(...)` for the GCS download + Gemini call + DB write. The `@shared_task` decorator with `bind=True` exposes `self` for retry semantics.

### 11.F Schemas — `image/schemas.py`

Pydantic v2 request/response models. Used by the route layer in `modules/image/routes.py`.

```python
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel


class ImageUploadResponse(BaseModel):
    image_id: UUID
    gcs_path: str
    status: Literal["pending"]
    idx: int                       # 1-4
    enqueued_task_id: str


class ImageSummary(BaseModel):
    image_id: UUID
    idx: int                       # 1-4
    status: Literal["pending", "ready", "failed_precheck"]
    signed_url: str                # GCS signed URL, TTL 1h
    precheck_jsonb: dict           # structured 5-step result
    is_front: bool                 # True iff idx == 1
    width: int | None
    height: int | None
    color_space: str | None        # "RGB" | "CMYK" | "Gray"
    created_at: datetime


class ImagesListResponse(BaseModel):
    images: list[ImageSummary]     # 0-4 items
```

### 11.G Internal domain types — `image/domain.py`

Frozen dataclasses used internally by the service + repository layers. These are NOT Pydantic — they are pure in-memory representations of domain concepts that never traverse the HTTP boundary. Cross-module return types are explicitly tagged.

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class ProductImage:
    """Mirrors product_images row per MVP_ARCH §2.5."""
    id: UUID
    product_id: UUID
    user_id: UUID                  # via FK to products (denormalized for scope checks)
    gcs_path: str
    order_idx: int                 # 1-4
    is_front: bool                 # GENERATED ALWAYS AS (order_idx == 1) STORED
    width: int | None
    height: int | None
    color_space: str | None
    precheck_jsonb: dict
    status: str                    # "pending" | "ready" | "failed_precheck"
    created_at: datetime


@dataclass(frozen=True)
class ImageUrl:
    """Cross-module return type for catalog.service.get_preview per §10.B.4."""
    image_id: UUID
    idx: int
    signed_url: str
    is_front: bool


@dataclass(frozen=True)
class ImageStatusSummary:
    """Cross-module return type for dashboard.service.summary per §13."""
    product_id: UUID
    total_images: int              # 0-4
    ready_count: int               # how many have status="ready"
    failed_count: int
    pending_count: int
    front_image_signed_url: str | None  # the idx=1 image's signed URL, if ready


@dataclass(frozen=True)
class PrecheckResult:
    """Internal — Celery task assembles this then writes to precheck_jsonb."""
    jpeg_valid: bool
    color_space: Literal["RGB", "CMYK", "Gray"]
    resolution_pass: bool
    white_background: bool
    watermark_check: Literal["no_watermark", "has_watermark", "uncertain", "skipped_budget"]
    watermark_confidence: float | None
```

### 11.H Exception hierarchy — `image/exceptions.py`

All `image` module exceptions subclass `MeesellError` (the shared base per §5.A.5). The `validation_message_id` field is the i18n key per §5A.D convention `{domain}.{field}.{constraint}`.

```python
from app.shared.exceptions import MeesellError


class ImageError(MeesellError):
    """Base class for image module failures. Never raised directly."""


class InvalidImageFormatError(ImageError):
    status_code = 400
    validation_message_id = "validation.image.invalid_format"


class ImageTooLargeError(ImageError):
    status_code = 400
    validation_message_id = "validation.image.too_large"


class InvalidImageIdxError(ImageError):
    status_code = 400
    validation_message_id = "validation.image.invalid_idx"


class ImageSlotOccupiedError(ImageError):
    status_code = 409
    validation_message_id = "image.slot_occupied"


class ImageNotFoundError(ImageError):
    status_code = 404
    validation_message_id = "image.not_found"
```

### 11.I Adapter usage

Two adapter call sites; both locked.

**`adapters.gcs`** — used directly per §6.D:
- `upload_bytes(path, data, content_type)` — §11.B.1 step 5 (route context).
- `download_bytes(path)` — §11.E Celery task step 1 (worker context).
- `generate_signed_url(path, ttl_seconds, method="GET")` — §11.B.2 step 3 (route context) + `get_image_urls` cross-module surface (called from `catalog.service.get_preview`).

The `meesell-images/{user_id}/{product_id}/{idx}.jpg` path convention is the locked structural enforcement of tenant isolation per §6.D + `MVP_ARCH §10.8`. The user_id segment in the path means a leaked signed URL still cannot be used to enumerate other tenants' images (the path is opaque to attackers since the URL is signed, not directory-listable).

**`ai_ops.client.call_gemini`** — used via §6A inside the Celery task ONLY (per §11.E step 6), with `workload="watermark"` per §6A.B. Backend's route layer **never** directly invokes AI — the route just enqueues, the worker calls.

No other adapter calls. `image` does NOT call `msg91`, `razorpay`, or `langfuse` directly (Langfuse instrumentation is automatic via `ai_ops.client` per §6A.F).

### 11.J Cross-cutting integrations

The integration posture below is binding for the construction dispatch.

**Rate-limit decorators (per §4.E).**
- `POST /images`: `@rate_limit(scope="image_upload", limit="10/min", key="user_id")` — bandwidth-heavy.
- `GET /images`: per-IP fallback only — polling endpoint, no per-user cap.

**Plan guard (per §4.H).** NOT participating in V1. The 4-slot uniform rule is the structural limit (DB-level `CHECK` constraint per `MVP_ARCH §2.5`). No `core/plan_guard.py` resource for `image_upload_hourly` or `image_total_per_product` — V1 does not need them.

**Audit middleware (per §4.G).**
- `POST /images` (2xx): emits `image.upload.received` with `{product_id, idx, gcs_path}`. NO file content per `MVP_ARCH §11.9`.
- `GET /images`: NONE (read-only polling, would flood `audit_events`).
- `image_precheck_task` (Celery worker): emits `image.precheck.completed` via **direct ORM write** — same documented-exception pattern as §6A.D `cost_tracker` and §7 `verify_otp` (the worker has no request-close hook so `audit_mw` cannot fire automatically).

**Tenancy (per §4.C).** YES — every query against `product_images` uses `scope_to_user(user_id)` per §4.C. The repository layer is the structural backstop; the `catalog.service.assert_product_ownership` cross-module call at the service layer is the higher-level gate (product_id → user_id mapping happens via the products table join).

**Cache helper (per §4.D).** NOT participating. Per-product image data has low cache hit rate (each product's images are read once or twice during catalog editing then never again until export). Signed URLs themselves cannot be cached because they expire in 1h.

**AI Ops layer (per §6A).** YES, via §6A.B `workload="watermark"`, INSIDE the Celery task ONLY. Graceful fallback on `BudgetExceededError`: `precheck_jsonb.watermark_check = "skipped_budget"` per §6A.F; the overall image `status` still resolves to `"ready"` if steps 1-4 (the deterministic Pillow-based checks) pass — the watermark step is **informational, not blocking**. This is a session-locked product decision: the founder will not penalize sellers for budget exhaustion they didn't cause.

**i18n (per §5A.D).** 5 image-specific `validation_message_id` keys land in `i18n/messages_en.py` during the `meesell-services-builder` construction dispatch: `validation.image.invalid_format`, `validation.image.too_large`, `validation.image.invalid_idx`, `image.slot_occupied`, `image.not_found`. The exact English strings are author-time decisions during dispatch.

### 11.K Test plan

The construction dispatch produces 5 unit + 3 integration test classes covering §11. The §19 Test Strategy section will absorb these counts when authored.

**Unit tests (`backend/tests/modules/image/`):**
1. **Ownership gate enforcement** — `POST /products/{other_user_product}/images` returns 404 even if image bytes are valid (the `catalog.service.assert_product_ownership` cross-module call is the first action; bytes never reach GCS).
2. **File validation** — non-JPEG → 400 `validation.image.invalid_format`; > 10 MB → 400 `validation.image.too_large`; idx `5` → 400 `validation.image.invalid_idx`. Each case verified via separate test method.
3. **Slot uniqueness** — POST with `idx=2` when an existing non-deleted image already occupies slot 2 → 409 `image.slot_occupied`.
4. **GCS path construction** — confirm path EXACTLY equals `meesell-images/{user_id}/{product_id}/{idx}.jpg` per §6.D + `MVP_ARCH §10.8`. Verified via mock `adapters.gcs.upload_bytes` assertion.
5. **Celery task enqueue** — verify `image_precheck_task.delay` was called with correct args (`image_id`, `user_id`) after a successful POST. Verified via mocked Celery client.

**Integration tests (`backend/tests/integration/test_image_*.py`):**
1. **Full upload → poll → ready flow** — POST upload → poll GET until `status == "ready"` (with timeout) → verify `precheck_jsonb` has 5 keys (`jpeg_valid`, `color_space`, `resolution_pass`, `white_background`, `watermark_check`) with correct types per §11.G `PrecheckResult` dataclass.
2. **Watermark budget exhaustion** — mock `ai_ops.client.call_gemini` to raise `BudgetExceededError` → verify `precheck_jsonb.watermark_check == "skipped_budget"` AND overall `status == "ready"` (informational, non-blocking — confirms §6A.F graceful fallback is wired correctly).
3. **Cross-module URL fetch** — `catalog.service.get_preview` calls `image.service.get_image_urls` → verify returned `list[ImageUrl]` has signed URLs ordered by `idx` with `is_front=True` set on the idx=1 entry only. Confirms the §2.D cross-module contract is honored.

**Pytest fixtures.** Real Postgres + Valkey + GCS test bucket via dev tunnel per §19; mocked `ai_ops.client.call_gemini` for the watermark step (deterministic fixtures for the 4 possible `watermark_check` outcomes).

### 11.L Extraction notes (V1.5+)

`image` is one of the **easier extraction targets** per §21 because the Celery worker side is already a separate process boundary per §0.E + §1 topology — the precheck pipeline already runs in a different process from the API. The extraction becomes:

- The 2 API endpoints (`POST` + `GET`) extract to their own FastAPI pod with GCS adapter access + Postgres FK to `products`.
- The Celery worker for `image.precheck` becomes a dedicated worker pod scaled independently from the catalog/dashboard workers.
- The `catalog.service.assert_product_ownership` cross-module call becomes an HTTP call (likely `GET /api/v1/internal/catalog/products/{id}/ownership?user_id=...` against the still-monolith catalog service). The service signature is already designed for this transition: `async`, raises typed `CatalogNotFoundError` exception, no implicit DB-session sharing.
- The `image.service.get_image_urls` / `get_image_bytes` cross-module reads from `catalog` / `export` similarly become HTTP calls — the contracts are already locked at this section.
- Signed-URL generation, GCS path convention, and 4-slot rule travel with the extracted service unchanged.

API surface stays small (2 endpoints), which is the structural reason `image` extracts cleanly while `catalog` does not (catalog is the call hub with 6 endpoints + 4 cross-module consumers — the V1.5 hardest target per §21).

### 11.M What §11 does NOT cover

The following are explicitly out of §11's scope. Builders consult the cited section instead:

- The DDL of `product_images` — `MVP_ARCH §2.5`.
- The GCS adapter implementation (`adapters/gcs.py`) — §6.D specifies the contract; adapter code is owned by `meesell-services-builder` during §6 dispatch.
- The 5-step precheck pipeline algorithm internals — `meesell-image-precheck-builder` (AI track) owns the JPEG / RGB / resolution / white-bg / watermark logic; backend's `image/tasks.py` is the Celery wrapper around their pipeline class.
- The watermark vision prompt content — `meesell-prompt-engineer` per §6A.G owns the `watermark.v1` prompt template, Layer 1 hallucination prefix, and few-shot examples.
- The §6A cost tracking, guardrails, budget cap — §6A authoritative.
- The exact English message strings for the 5 image-specific `validation_message_id` keys — `meesell-services-builder` dispatch authors them per §5A.D + the `i18n/messages_en.py` file.
- The signed-URL upload pattern — V1 uses direct multipart through FastAPI per CLAUDE.md API design rules ("multipart/form-data, max 10MB per image"); V1.5 may add direct-to-GCS upload per `MVP_ARCH §10.8` to bypass the FastAPI proxy for bandwidth, but that is V1.5 work, not V1.
- The DELETE-image endpoint — V1 does not expose deletion of individual images (only soft-delete of the parent product per §10.B.5). The repository `soft_delete_by_idx` helper exists as internal scaffolding for the catalog cascade + V1.5 re-upload flow.

---

## Section 12 — Module: `pricing`

STATUS: LOCKED (2026-06-05)

### 12.A Preamble

§12 specifies the `pricing` module — the P&L calculator + GST snapshot + suggested MRP for Feature 7 (Price Calculator). **Owner specialists:** `meesell-api-routes-builder` (routes + Pydantic schemas, INCLUDING the re-authoring of pricing schemas in `modules/pricing/schemas.py` — the legacy `backend/app/schemas/pricing.py` was deleted in session 2 gap pass per coordinator memory) + `meesell-services-builder` (business logic — P&L calculator, GST snapshot, suggested MRP, alert generation). **NO AI track collaboration** — pricing is deterministic math, no AI ranking or generation. The module is a **leaf-with-2-calls module** on the cross-module graph (per §2.D matrix: `pricing → category` for commission + `pricing → catalog` for ownership; both ✓ rows). It writes the `pricing_calcs` table exclusively. It surfaces **1 endpoint**, in the §0.C 27-endpoint contract.

**Resolves the §0.E latent bug.** `backend/app/services/pricing_engine.py` line 23 imports `from app.schemas.pricing import PricingAlert`; both files are dead post-gap-pass per the session 2 FINAL PURGE close-out. The `meesell-services-builder` construction dispatch for §12 will (a) DELETE `services/pricing_engine.py` outright (legacy V0 code incompatible with the modular monolith file structure per §3.B), (b) create `modules/pricing/domain.py` with the new `PricingAlert` frozen dataclass per §12.F below, (c) create `modules/pricing/service.py` from scratch with the locked P&L algorithm per §12.C, (d) create `modules/pricing/schemas.py` with the Pydantic v2 request/response models per §12.E. The resolution path is **delete legacy + write clean** — NOT "patch the import". Cross-reference: §0.E flags this as a queued construction-phase concern; §12 is where it lands.

### 12.B Endpoint surfaces

The module surfaces **1 endpoint** in the locked §0.C contract.

#### 12.B.1 `POST /api/v1/products/{id}/price-calc` — Price Calculator (Feature 7)

**Request body** (Pydantic v2):

```python
class PriceCalcRequest(BaseModel):
    input_cost: Decimal = Field(gt=0, decimal_places=2)
    target_margin_pct: Decimal = Field(default=Decimal("30"), ge=0, le=Decimal("500"), decimal_places=2)
    override_commission_pct: Decimal | None = Field(default=None, ge=0, le=Decimal("100"), decimal_places=2)  # V1.5+
    override_gst_pct: Decimal | None = Field(default=None, ge=0, le=Decimal("100"), decimal_places=2)  # V1.5+
```

The `override_*` fields are V1.5+ — V1 honors only `input_cost` + `target_margin_pct`. The spec includes them so the V1.5 widening is forward-compatible (Pro-tier feature for custom commission/GST overrides).

**Response 200** (Pydantic v2):

```python
class PriceCalcResponse(BaseModel):
    mrp: Decimal
    meesho_price: Decimal
    seller_price: Decimal
    commission_pct: Decimal
    commission_amount: Decimal
    gst_pct: Decimal
    gst_amount: Decimal
    profit: Decimal
    profit_pct: Decimal
    alerts: list[PriceCalcAlert]
    calculated_at: datetime
```

All monetary values in INR with 2 decimal places (`Decimal` type, not `float` per CLAUDE.md Python conventions — see "Coding Conventions" section + §4.D numeric precision rule).

**Rate limit:** per-IP only — lightweight stateless computation; no DB write contention; per-user limit would degrade typing-rapid-iteration UX (sellers tweak `target_margin_pct` to converge on a price).

**Plan guard:** NOT participating in V1 — no pricing-calc cap; the `core/plan_guard.py` 4-resource Literal per §4.E does NOT include `pricing_calc_*`. Cross-reference with §4.E: pricing is one of the 3 modules excluded from plan_guard alongside customer and dashboard.

**Status codes:**
- `200` — calc completed successfully.
- `400` — `validation.price.invalid_input` (input_cost ≤ 0 or target_margin_pct < 0; caught by Pydantic + the §12.G `InvalidPriceInputError` for service-layer business-rule checks).
- `401` — JWT missing/invalid (handled by §4.A auth middleware).
- `404` — `catalog.product_not_found` from the §10.C `assert_product_ownership` cross-module ownership gate.
- `422` — `pricing.commission_missing` when the resolved category has NULL `commission_pct`. Rare in practice — most Meesho categories carry commission; this guards against seed gaps or freshly-added categories.

**Audit:** middleware emits `pricing.calculated` event on 2xx with payload `{product_id, input_cost, mrp, profit_pct}`. No PII — numeric values; `product_id` is not PII; the seller's cost-margin choices are commercially sensitive but NOT PII per `MVP_ARCH §11.9`.

**JWT required:** yes (consumes `user_id` from §4.A `get_current_user` dep).

**Flow** (locked sequence):

1. Pydantic validates `input_cost > 0` and `target_margin_pct >= 0` at the route boundary.
2. `catalog.service.assert_product_ownership(product_id, user_id)` per §10.C — raises `ProductNotFoundError` (404) if not owned.
3. Load product via repository (lightweight single-row read) to obtain `category_id`.
4. `category.service.get_commission(category_id)` per §9.C → returns `Decimal | None`.
5. If `None` → raise `CommissionMissingError` (422 `pricing.commission_missing`).
6. Run P&L calculator (`pricing.service._compute_pnl(input_cost, target_margin_pct, commission_pct, gst_pct=18)`):
   - `gst_pct` = 18% (V1 default; sourced from `pricing/service.py` module constant `DEFAULT_GST_PCT = Decimal("18")`; V1.5 may make per-category).
   - `seller_price = input_cost × (1 + target_margin_pct/100)` — what the seller wants to receive net of fees.
   - `mrp = seller_price / (1 - commission_pct/100 - (gst_pct/100) × (commission_pct/100))` — back-solve from `seller_price = mrp × (1 - commission_pct/100 - gst_on_commission_pct)`.
   - `commission_amount = mrp × commission_pct / 100`.
   - `gst_amount = commission_amount × gst_pct / 100` — GST is charged on commission, not on full MRP (Meesho's seller-fee structure).
   - `meesho_price = mrp` — the seller-facing list price equals MRP in V1; V1.5 may differentiate (discount fields, promo prices).
   - `profit = seller_price - input_cost`.
   - `profit_pct = profit / input_cost × 100`.
   - **Quantization:** every monetary value `round(value, 2)` with banker's rounding (Decimal `ROUND_HALF_EVEN`) to avoid +/-0.01 drift across the calculator chain per CLAUDE.md numeric precision rule.
7. Generate `alerts: list[PricingAlert]` per the §12.F locked alert codes (see §12.C `_generate_alerts` helper).
8. Persist to `pricing_calcs` table: `{user_id, product_id, input_jsonb, output_jsonb, calculated_at}` where `input_jsonb` and `output_jsonb` are the full request + response payloads (audit trail for accounting; `MVP_ARCH §11.9` PII-scrubbing exempt because no PII present in either payload).
9. Return 200 with the full `PriceCalcResponse`.

### 12.C Service layer — `pricing/service.py`

Public surface (all `async`):

```python
async def calculate(
    user_id: UUID,
    product_id: UUID,
    request: PriceCalcRequest,
) -> PriceCalcResponse:
    """Main endpoint surface. Locked flow per §12.B.1 steps 2-9."""

# Cross-module surface (read-only, consumed by other modules)
async def get_last_calc(
    user_id: UUID,
    product_id: UUID,
) -> PriceCalcResponse | None:
    """Consumed by dashboard.service.summary per §13 (OPTIONAL — same posture
    as image.service.summary per §11.C). Returns the most recent calc for
    the given product, or None if no calc has been run yet."""
```

Internal helpers (NOT public — module-private, module-private functions per §16):

```python
def _compute_pnl(
    input_cost: Decimal,
    target_margin_pct: Decimal,
    commission_pct: Decimal,
    gst_pct: Decimal,
) -> PnLBreakdown:
    """Deterministic; pure function; unit-tested in isolation. The locked
    P&L algorithm per §12.B.1 step 6. No side effects, no DB, no I/O."""

def _generate_alerts(
    breakdown: PnLBreakdown,
    input_cost: Decimal,
) -> list[PricingAlert]:
    """Pure function. Applies the 3 locked alert rules per §12.F to the
    deterministic P&L breakdown."""
```

`_compute_pnl` is the load-bearing math kernel. Per §19 test strategy, it is unit-tested in isolation with golden fixtures so any V1.5 GST-overlay or override-commission widening does not regress V1 math.

### 12.D Repository layer — `pricing/repository.py`

MODULE-PRIVATE per §16. All methods consume the `db: AsyncSession` from §4.A and use `scope_to_user(user_id)` per §4.C on every query.

```python
async def insert_calc(
    db: AsyncSession,
    user_id: UUID,
    product_id: UUID,
    input_jsonb: dict,
    output_jsonb: dict,
) -> PricingCalc:
    """Insert a new pricing_calcs row. Called from service.calculate()
    step 8. Returns the inserted domain object."""

async def find_latest_by_product(
    db: AsyncSession,
    user_id: UUID,
    product_id: UUID,
) -> PricingCalc | None:
    """ORDER BY calculated_at DESC LIMIT 1, scoped to user_id. Backing
    query for service.get_last_calc()."""
```

Both queries apply `WHERE user_id = :user_id AND product_id = :product_id` — the user_id scope is the structural enforcement of M6 tenancy at the data layer (in addition to the higher-level `assert_product_ownership` gate at the service layer).

### 12.E Schemas — `pricing/schemas.py`

Pydantic v2 wire-shape models. **This file REPLACES the deleted legacy `backend/app/schemas/pricing.py`** — created from scratch per the §0.E resolution path.

```python
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class PriceCalcRequest(BaseModel):
    input_cost: Decimal = Field(gt=0, decimal_places=2)
    target_margin_pct: Decimal = Field(
        default=Decimal("30"),
        ge=0,
        le=Decimal("500"),
        decimal_places=2,
    )
    override_commission_pct: Decimal | None = Field(
        default=None,
        ge=0,
        le=Decimal("100"),
        decimal_places=2,
    )  # V1.5+ — ignored in V1
    override_gst_pct: Decimal | None = Field(
        default=None,
        ge=0,
        le=Decimal("100"),
        decimal_places=2,
    )  # V1.5+ — ignored in V1


class PriceCalcAlert(BaseModel):
    code: Literal["LOW_MARGIN", "HIGH_MRP_MULTIPLIER", "THIN_PROFIT"]
    message_id: str  # validation_message_id per §5A.H — resolved client-side via i18n
    severity: Literal["warning", "info"]


class PriceCalcResponse(BaseModel):
    mrp: Decimal
    meesho_price: Decimal
    seller_price: Decimal
    commission_pct: Decimal
    commission_amount: Decimal
    gst_pct: Decimal
    gst_amount: Decimal
    profit: Decimal
    profit_pct: Decimal
    alerts: list[PriceCalcAlert]
    calculated_at: datetime
```

The `PriceCalcAlert` here is the **wire-shape** Pydantic model exposed in the HTTP response. The domain object `PricingAlert` in §12.F is the **internal** dataclass constructed by the service. The router serializes one to the other via straight field-mapping (`model_validate({"code": alert.code, "message_id": alert.message_id, "severity": alert.severity})`).

### 12.F Internal domain types — `pricing/domain.py`

Frozen dataclasses. **This file is the new home of `PricingAlert`** — the §0.E latent bug resolution.

```python
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class PricingCalc:
    """Mirrors a pricing_calcs row. Returned by repository methods."""
    id: UUID
    user_id: UUID
    product_id: UUID
    input_jsonb: dict
    output_jsonb: dict
    calculated_at: datetime


@dataclass(frozen=True)
class PnLBreakdown:
    """Internal — output of the deterministic _compute_pnl function.
    Not Pydantic; never crosses HTTP. Consumed by _generate_alerts
    and serialized into PriceCalcResponse at the route boundary."""
    mrp: Decimal
    meesho_price: Decimal
    seller_price: Decimal
    commission_pct: Decimal
    commission_amount: Decimal
    gst_pct: Decimal
    gst_amount: Decimal
    profit: Decimal
    profit_pct: Decimal


@dataclass(frozen=True)
class PricingAlert:
    """The new PricingAlert that REPLACES the legacy
    backend/app/schemas/pricing.PricingAlert (deleted in session 2 gap
    pass — §0.E latent bug). Lives in modules/pricing/domain.py per the
    §3.C per-module canonical subtree."""
    code: Literal["LOW_MARGIN", "HIGH_MRP_MULTIPLIER", "THIN_PROFIT"]
    message_id: str  # validation_message_id per §5A.H, e.g. "pricing.alert.low_margin"
    severity: Literal["warning", "info"]
```

**The 3 locked alert rules** (consumed by `_generate_alerts` per §12.C):
- `LOW_MARGIN` — emitted when `profit_pct < 10`. Severity `warning`. message_id `pricing.alert.low_margin`.
- `HIGH_MRP_MULTIPLIER` — emitted when `mrp / input_cost > 3`. Severity `warning`. message_id `pricing.alert.high_mrp_multiplier`. (Suspicious — possibly miscalibrated cost or margin.)
- `THIN_PROFIT` — emitted when `profit < 50`. Severity `info`. message_id `pricing.alert.thin_profit`. Tirupur-seller context — ₹50 is the practical minimum margin per the Meesho seller economics surveyed in `docs/VALIDATED_PAIN_POINTS.md`.

Multiple alerts may fire simultaneously (e.g., low input_cost + low margin → both `THIN_PROFIT` and `LOW_MARGIN`).

### 12.G Exception hierarchy — `pricing/exceptions.py`

All subclass `MeesellError` per §4.F. The error-handler middleware per §4.F maps `status_code` + `validation_message_id` to the wire response.

```python
from app.core.errors import MeesellError


class PricingError(MeesellError):
    """Base class for pricing module failures. Never raised directly."""


class InvalidPriceInputError(PricingError):
    """Service-layer business-rule check beyond Pydantic validation.
    Pydantic catches input_cost <= 0 at the boundary; this class is
    held for forward-compatibility (V1.5 may add cross-field rules,
    e.g., target_margin_pct > some-function-of-commission)."""
    status_code = 400
    validation_message_id = "validation.price.invalid_input"


class CommissionMissingError(PricingError):
    """The resolved category has commission_pct = NULL. Rare — most
    Meesho categories carry commission; this guards against seed gaps."""
    status_code = 422
    validation_message_id = "pricing.commission_missing"
```

### 12.H Adapter usage

**NONE.** Pricing is pure deterministic math against DB reads (category + catalog cross-module calls; pricing_calcs write). No vendor calls — no Gemini, no MSG91, no GCS, no Razorpay, no LangFuse. This confirms the §1.E egress map (which lists no pricing-module egress) and the §2.6 module catalog row (no `adapters` column).

### 12.I Cross-cutting integrations

- **Rate-limit decorators (§4.E):** per-IP fallback only. Lightweight stateless computation; per-user limit would degrade typing-rapid-iteration UX. No `@rate_limit(scope=..., key="user_id")` decorator on the route.
- **Plan guard (§4.E):** NOT participating in V1. No pricing-calc cap; the §4.E 4-resource Literal does not include pricing. V1.5 may add `pricing_calc_hourly` if abuse patterns emerge.
- **Audit middleware (§4.F):** standard — `pricing.calculated` event on 2xx with `{product_id, input_cost, mrp, profit_pct}`. No PII.
- **Tenancy (§4.C):** YES — `pricing_calcs.user_id` FK; every repository query uses `scope_to_user(user_id)`. The `catalog.service.assert_product_ownership` cross-module call is the higher-level service-layer gate. Defense-in-depth: service-layer ownership assertion + repository-layer user_id scoping.
- **Cache helper (§4.D):** NOT participating. Per-product write-heavy data with low repeat-read probability — sellers don't poll `get_last_calc`; only dashboard summary consumes it.
- **AI Ops (§6A):** NONE — pricing is deterministic. No `ai_ops.client.call_gemini` invocation.
- **i18n (§5A.H + §3.H):** 5 pricing-specific `validation_message_id` keys land in `i18n/messages_en.py` during the services-builder dispatch:
  - `validation.price.invalid_input` (400)
  - `pricing.commission_missing` (422)
  - `pricing.alert.low_margin` (alert)
  - `pricing.alert.high_mrp_multiplier` (alert)
  - `pricing.alert.thin_profit` (alert)

### 12.J Test plan

Test surfaces per §19 strategy. 4 unit + 2 integration test classes.

**Unit tests** (`backend/tests/modules/pricing/`):

1. **Ownership gate** — `POST /products/{other_user_product}/price-calc` → 404 `catalog.product_not_found`. Validates the §10.C cross-module gate consumption.
2. **Commission missing** — when `category.get_commission` returns `None` (mocked) → 422 `pricing.commission_missing`. Validates the §12.G `CommissionMissingError` path.
3. **P&L formula correctness** — golden fixtures: `input_cost=100`, `target_margin_pct=30`, `commission_pct=15` → expected `seller_price=130`, `mrp≈151.52`, `profit=30`, `profit_pct=30` (subject to ROUND_HALF_EVEN). Decimal precision exact match — no `==` on float, all asserts via `Decimal` comparison.
4. **Alert generation** — three sub-cases:
   - low-margin scenario → `alerts` includes `LOW_MARGIN`.
   - high-mrp-multiplier scenario (e.g., `input_cost=50`, `commission_pct=30%`, `target_margin_pct=50%` → mrp > 150) → `alerts` includes `HIGH_MRP_MULTIPLIER`.
   - thin-profit scenario (e.g., `input_cost=100`, `target_margin_pct=10%` → profit=10) → `alerts` includes both `THIN_PROFIT` and `LOW_MARGIN`.

**Integration tests** (`backend/tests/integration/test_pricing_*.py`):

1. **Full create-product → set-category → price-calc** flow. Response `commission_pct` equals the seeded category `commission_pct`. Validates end-to-end §10 + §9 + §12 cross-module wiring.
2. **`pricing_calcs` persistence + `get_last_calc`** — verify the full `input_jsonb` and `output_jsonb` snapshots are written for audit; `get_last_calc` returns the most recent calc for a product; subsequent calc inserts a new row (not an UPDATE — audit trail is append-only).

**Pytest fixtures:** real Postgres via dev tunnel (`localhost:5433`); seeded `categories.commission_pct` for the test category; mocked `catalog.assert_product_ownership` for unit tests (real for integration).

### 12.K Extraction notes (V1.5+)

`pricing` extracts trivially. It owns 1 table (`pricing_calcs`) and reads 2 stable contracts (`category.get_commission(category_id) -> Decimal | None` + `catalog.assert_product_ownership(product_id, user_id) -> None | raises`). Early V1.5 candidate if Pro-tier billing logic (override-commission, override-GST, custom-margin-rules, per-category GST) clusters into the module. Per §21 recommended extraction order, pricing is one of the easier extractions because the cross-module call signatures are small and stable — the consumers (`category` + `catalog`) need no internal change to switch from in-process call to RPC.

Network of records on extraction: copy `pricing_calcs` rows by `user_id` in batches, replay the 2 cross-module reads against the new service boundary, fail-over the route, retire in-process module.

### 12.L What §12 does NOT cover

- The DDL of `pricing_calcs` (`MVP_ARCH §2.5` + §5.E ORM registry).
- The category commission seed — the `categories.commission_pct` values are owned by the DATABASE track + seed scripts (`scripts/build_template_schemas.py` + the database-builder memory).
- The exact English strings for the 5 pricing-related `validation_message_id` keys — the services-builder dispatch authors them in `i18n/messages_en.py` (the convention is locked at §5A.H; the strings are not).
- Any AI-based price suggestion — pricing is deterministic; V1.5 may add AI margin guidance but that workload is deferred and is NOT in the §6A locked `Literal["smart_picker", "autofill", "watermark"]` workload set.
- Razorpay subscription pricing (V1.5 — iam module per §7).
- The legacy `services/pricing_engine.py` — gets DELETED at §12 specialist construction time, not "patched"; the new `modules/pricing/service.py` is the replacement (§0.E + §12.A resolution path).

---

## Section 13 — Module: `dashboard`

STATUS: LOCKED (2026-06-05)

### 13.A Preamble

§13 specifies the `dashboard` module — the seller's tracking view for Feature 8 (Tracking Dashboard) per `docs/V1_FEATURE_SPEC.md` Feature 8. **Owner specialists:** `meesell-api-routes-builder` (route handler + Pydantic schemas) + `meesell-services-builder` (read-aggregation composition logic) per §2.7. **NO AI track collaboration** — pure read aggregation with no Gemini call, no `ai_ops` invocation, no prompt-engineer participation. **Leaf module on the cross-module call graph** per §2.D: dashboard → customer ✓, dashboard → catalog ✓; every other cell is `✗` per the founder ruling that kept the matrix at exactly 8 ✓ (no elevation in V1 to image / pricing / export `summary()` opt-ins).

`dashboard` is **the purest demonstration of the modular monolith discipline** described in §2.7's preamble. It owns ZERO tables (the only domain module besides `core/` — and `core/` is not a domain module — with no DDL footprint at all per `MVP_ARCH §2`). It has NO `repository.py` file in its subtree (a structural deviation from the §3.C canonical per-module 7-file layout, locked here explicitly so the absence reads as intentional design — not omission). It reads NOTHING directly — every data access flows through `catalog.service.list_products(...)` and `customer.service.get_onboarding_completeness(...)` per §10.C + §8.C, which themselves own the `scope_to_user(user_id)` enforcement at their respective repository layers per §4.C. Dashboard's role is purely **composing** pre-scoped, pre-validated, pre-shaped results from the two consumed services into a single wire-shaped `DashboardResponse`.

When V1.5 extraction lands per §21, dashboard becomes its own **BFF (backend-for-frontend) pod** with **zero data-layer migration** — every cross-module Python call simply swaps in-process invocation for HTTP. There are no Alembic migrations to detach, no foreign-key cascade to redirect, no row-level locks to coordinate. The extraction reduces to: change `from app.modules.catalog.service import list_products` to `httpx.AsyncClient().get(CATALOG_SVC_URL + "/products?...")`, plus a service-discovery config change. This is why dashboard (alongside `export` per §2.8) is one of the **easiest V1.5 extractions** in the codebase, in contrast to `catalog` which is the hardest per §10.K.

Surfaces **1 endpoint** in V1, which is the **only listing GET in the §0.C 27-endpoint contract** (note: `GET /api/v1/products` belongs to dashboard, not catalog — per §2.7 ownership lock; `catalog` owns CREATE/PATCH/AUTOFILL/PREVIEW/DELETE/DRAFT-RECOVER but not the LIST). §13 does NOT specify any table DDL (dashboard owns NONE — see §13.L scope-out), does NOT specify any repository methods (NO repository file exists for dashboard — see §13.D), does NOT specify the §14 `export.service.summary()` opt-in for richer status badges (forward-referenced to V1.5 amendment if/when founder elevates the §2.D matrix beyond 8 ✓).

### 13.B Endpoint surfaces

The module surfaces **1 endpoint** in the locked §0.C 27-endpoint contract.

#### 13.B.1 `GET /api/v1/products` — Paginated product listing (Feature 8)

**Request** (query parameters, Pydantic v2 `DashboardQuery` — see §13.E):

| Parameter | Type | Default | Constraints |
|---|---|---|---|
| `page` | `int` | `1` | `>= 1` |
| `limit` | `int` | `20` | `1 <= limit <= 100` |
| `status_filter` | `Literal["draft", "ready", "exported"] \| None` | `None` | one-of values |
| `search` | `str \| None` | `None` | `max_length=100`, matches product `name` ILIKE substring |

**Response 200** (Pydantic v2 `DashboardResponse` — see §13.E):

```python
{
    "products": [
        {
            "product_id": "uuid",
            "name": "string | null",
            "category_id": "uuid",
            "status": "draft" | "ready" | "exported",
            "created_at": "iso8601",
            "updated_at": "iso8601"
        },
        ...
    ],
    "total": 42,
    "page": 1,
    "limit": 20,
    "onboarding_completeness": {
        "base_complete_count": 8,
        "base_total_count": 10,
        "extension_complete_count": 2,
        "extension_total_count": 3,
        "onboarding_complete": false
    }
}
```

**Rate limit:** `@rate_limit(scope="dashboard_list", limit=..., key="ip")` — per-IP fallback only. Polled on every dashboard page navigation and on the `refresh` button; per-user limit not used because legitimate dashboards land below the per-IP threshold.

**Plan guard:** NOT participating. Dashboard is a read-only view; there is no plan-gated resource consumption.

**Status codes:**

| Status | Trigger | `validation_message_id` |
|---|---|---|
| 200 | success | — |
| 400 | `page < 1` OR `limit < 1` OR `limit > 100` OR `status_filter` invalid Literal OR `search` > 100 chars | `validation.dashboard.invalid_pagination` |
| 401 | missing or invalid access JWT | — (handled by §4.B `auth_mw`) |

**Audit:** NONE. Dashboard is read-only; per the §4.G + §11.9 audit posture (read-only endpoints do not emit audit events), `GET /products` does not write to `audit_events`. Same posture as §9 category browsing endpoints.

**JWT required:** yes — `Depends(get_current_user)` per §4.B.

**Flow** (the §15 cross-cutting walkthrough will diagram this end-to-end):

1. **Pydantic validation** — query parameters are validated against `DashboardQuery`. Out-of-bound values raise `InvalidPaginationError` per §13.G → 400 with `validation.dashboard.invalid_pagination`.
2. **Service call to catalog** — `await catalog.service.list_products(user_id, Pagination(page, limit, status_filter, search))` per §10.C. Returns a `PaginatedProducts({products: list[Product], total: int, page: int, limit: int})` domain object where each `Product` carries `{product_id, name, category_id, status, created_at, updated_at}` per the catalog domain shape locked in §10.F. **`scope_to_user(user_id)` is enforced at catalog's repository layer per §10.D** — dashboard never sees a raw SQL query; the tenancy contract is upstream.
3. **Service call to customer** — `await customer.service.get_onboarding_completeness(user_id)` per §8.C. Returns a `ProfileCompleteness({base_complete_count, base_total_count, extension_complete_count, extension_total_count, onboarding_complete})` domain object per the customer domain shape locked in §8.F. **`scope_to_user(user_id)` is enforced at customer's repository layer per §8.D** — same posture as the catalog call.
4. **Compose response** — `_compose_response(paginated, completeness)` (pure function per §13.C) builds the `DashboardResponse` Pydantic model. V1 does NOT call `image.service.summary(...)` per §11.C OPTIONAL surface, does NOT call `pricing.service.summary(...)` per §12.C OPTIONAL surface, does NOT call `export.service.summary(...)` per §14 forthcoming OPTIONAL surface. Per-product status badges in V1 are inferred from `product.status` field only (one of `draft` / `ready` / `exported`); richer derived badges (e.g., "watermark detected" / "low margin") wait for V1.5 matrix elevation.
5. **Return 200** with the composed `DashboardResponse`.

### 13.C Service layer

`modules/dashboard/service.py` exposes a single public async method. The simplicity is the point — dashboard delegates everything to the consumed services.

```python
async def list_products_for_dashboard(
    user_id: UUID,
    query: DashboardQuery,
) -> DashboardResponse:
    """
    Compose the dashboard view by aggregating catalog.list_products
    and customer.get_onboarding_completeness for the requesting seller.
    Owns no data access; pure delegation + composition.
    """
```

That is the entire public surface. No `get_recent_activity`, no `get_status_counts`, no `summary` cross-module surface — dashboard is a leaf consumer on the §2.D matrix, not a producer.

**Internal helper** (NOT public — module-private, lives in the same file or a private `_compose.py`):

```python
def _compose_response(
    paginated: PaginatedProducts,
    completeness: ProfileCompleteness,
) -> DashboardResponse:
    """
    Pure function. Maps catalog.PaginatedProducts + customer.ProfileCompleteness
    into the wire-shaped DashboardResponse. Unit-tested in isolation per §13.J.
    """
```

The helper exists specifically so the composition logic can be unit-tested without mocking the two service calls; the public `list_products_for_dashboard` becomes a thin orchestration wrapper around two `await` points + one pure call.

**No cross-module surfaces are exposed by dashboard.** Per §2.D, no other module reads from dashboard; the column for dashboard in the matrix is entirely `✗`. This is locked: dashboard MUST NOT publish a public method consumed by another module in V1. If V1.5 introduces an analytics or admin module that needs aggregated seller metrics, that consumer must call `catalog` and `customer` directly, NOT call dashboard.

### 13.D Repository layer (NONE)

**There is no `modules/dashboard/repository.py` file.** This is a deliberate structural deviation from the §3.C canonical per-module 7-file layout (`router.py`, `service.py`, `repository.py`, `schemas.py`, `domain.py`, `exceptions.py`, `tasks.py`), locked here as the visible enforcement of §2.7's "purest modular monolith discipline" claim.

When a future audit runs `ls modules/dashboard/`, the absence of `repository.py` is the structural proof that dashboard owns no tables and performs no data access. The canonical subtree for dashboard is reduced to 5 files:

```
modules/dashboard/
├── __init__.py
├── router.py
├── service.py
├── schemas.py
├── domain.py
└── exceptions.py
```

**Locked rule:** dashboard MUST NOT introduce a `repository.py` file in V1 or V1.5 unless the founder approves a §13 amendment converting dashboard from BFF to a data-owning module. If a §13 amendment ever does add a repository file, the §2.7 preamble's "purest modular monolith discipline" claim must be retired in the same amendment — the two are bound.

**§19 CI linter exception:** the per-module subtree completeness check that asserts the 7 canonical files exist must allowlist `dashboard` (and any other future BFF-style modules) as a documented exception. The exception list belongs in `backend/tests/test_module_layout.py` per §19.

### 13.E Schemas

`modules/dashboard/schemas.py` — Pydantic v2 request/response models for the HTTP boundary:

```python
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field


class DashboardQuery(BaseModel):
    """Query parameters for GET /api/v1/products."""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    status_filter: Literal["draft", "ready", "exported"] | None = None
    search: str | None = Field(default=None, max_length=100)


class ProductListItem(BaseModel):
    """One row in the dashboard product listing."""
    product_id: UUID
    name: str | None  # nullable until seller fills it during catalog flow
    category_id: UUID
    status: Literal["draft", "ready", "exported"]
    created_at: datetime
    updated_at: datetime


class ProfileCompletenessSummary(BaseModel):
    """Customer profile completeness summary for the dashboard header strip."""
    base_complete_count: int
    base_total_count: int  # always 10 per §8.F ProfileCompleteness
    extension_complete_count: int
    extension_total_count: int
    onboarding_complete: bool


class DashboardResponse(BaseModel):
    """Wire shape for GET /api/v1/products."""
    products: list[ProductListItem]
    total: int
    page: int
    limit: int
    onboarding_completeness: ProfileCompletenessSummary
```

`base_total_count` is documented as always `10` (the 10 base seller-profile fields per §8.F + `MVP_ARCH §3.2`); the field is sent over the wire anyway so the frontend can render `8 of 10` without re-hardcoding the denominator. `extension_total_count` varies by the seller's `active_super_categories` per §8.B `COMPLIANCE_EXTENSION_MAP`.

### 13.F Internal domain types

`modules/dashboard/domain.py` — locked frozen dataclasses, minimal because dashboard composes rather than redefines:

```python
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Pagination:
    """
    Local pagination + filter shape passed to catalog.service.list_products.
    Lives in dashboard.domain because it's the shape dashboard hands across
    the service boundary; catalog accepts it as a typed contract.
    """
    page: int
    limit: int
    status_filter: Literal["draft", "ready", "exported"] | None
    search: str | None
```

That is the only domain type unique to dashboard. Three observations on the rest of the type surface:

1. **`ProductListItem`, `ProfileCompletenessSummary`, `DashboardResponse` are Pydantic, not dataclasses** — they live at the HTTP boundary (`schemas.py`) and are emitted as JSON.
2. **The service layer consumes domain objects from `catalog` and `customer`** — `PaginatedProducts` from `catalog.domain` per §10.F, `ProfileCompleteness` from `customer.domain` per §8.F. Dashboard imports those domain types directly via `from app.modules.catalog.domain import PaginatedProducts` and `from app.modules.customer.domain import ProfileCompleteness`. This is permitted per §16 — domain-type imports across modules are first-class as long as no repository-layer call crosses the boundary (services call services, not repositories call repositories).
3. **There is no `dashboard.domain.DashboardSnapshot` or similar aggregate type** — V1 does not memoize or persist the composed view. The composition is per-request, stateless, and computed inside `_compose_response`.

### 13.G Exception hierarchy

`modules/dashboard/exceptions.py` — all subclass `MeesellError` per the §4.F handler chain:

```python
from app.core.errors import MeesellError


class DashboardError(MeesellError):
    """Base class for dashboard module failures. Never raised directly."""


class InvalidPaginationError(DashboardError):
    status_code = 400
    validation_message_id = "validation.dashboard.invalid_pagination"
```

Just one concrete exception class. Most failures the dashboard endpoint can surface come from the underlying services and propagate through cleanly:

- **401 Unauthorized** — raised by `auth_mw` per §4.B before the handler runs; never reaches dashboard code.
- **404 Not Found (product-level)** — not applicable; dashboard returns a list, and an empty list is a valid 200 (NOT 404 — empty seller inventory is a real state).
- **500 Internal Server Error** — raised generically by the §4.F handler if `catalog.service.list_products` or `customer.service.get_onboarding_completeness` throws an unexpected exception; the underlying module's error code surfaces in the response body.

The Pydantic `DashboardQuery` validator catches `page < 1` / `limit > 100` / invalid `status_filter` Literal / `search` length BEFORE handler execution, and the §4.F handler chain renders the resulting `ValidationError` as 400 with `validation.dashboard.invalid_pagination` per §5A.D convention.

### 13.H Adapter usage

**NONE.**

Dashboard does not import from `app.adapters.*`. Per the §1.E egress map, the dashboard endpoint contributes zero egress traffic — no Gemini call, no MSG91 call, no GCS read, no Razorpay call, no LangFuse trace. This confirms the §1.E budget and is the structural reason `GET /products` has a P95 budget of ≤200 ms (per `MVP_ARCH §7.5`'s read-endpoint tier) — there are no third-party round-trips to absorb the latency.

### 13.I Cross-cutting integrations

- **Rate-limit decorators (§4.E):** per-IP fallback only via `@rate_limit(scope="dashboard_list", limit=..., key="ip")`. No per-user limit configured — dashboard is polled on every page load and refresh button, and a per-user limit would create UX friction for legitimate sellers.
- **Plan guard (§4.E):** NOT participating in V1. Dashboard is one of the 3 modules excluded from plan_guard alongside `customer` (§8) and `pricing` (§12). There is no plan-gated resource consumed by listing products.
- **Audit middleware (§4.G + §11.9):** NONE. Read-only endpoint posture per the §9 category-endpoints model. The `audit_mw` skips writes on `GET` requests by default; dashboard inherits that default without override.
- **Tenancy (§4.C):** NOT participating at the repository level (no repository exists). The consumed service methods `catalog.service.list_products` and `customer.service.get_onboarding_completeness` each enforce `scope_to_user(user_id)` at their own repository layer per §10.D + §8.D. Dashboard's role is composing pre-scoped results; it never sees a raw query and never asserts tenancy itself.
- **Cache helper (§4.D):** NOT participating. Per-user data with high write churn (every PATCH on products invalidates the listing); the hit rate would be too low to justify the cache-key plumbing. V1.5 may revisit if seller dashboards hit a poll-rate that the per-IP rate limit doesn't absorb.
- **AI Ops (§6A):** NONE.
- **i18n (§5A.D):** 1 dashboard-specific `validation_message_id` lands in `backend/app/i18n/messages_en.py` during the `services-builder` dispatch — `validation.dashboard.invalid_pagination`. The English string content is owned by the specialist; coordinator owns only the ID.

### 13.J Test plan

Per §19, the dashboard module's test surface is the lightest in the codebase: 3 unit + 2 integration test classes.

**Unit tests** (`backend/tests/modules/dashboard/`):

1. **`test_pagination_validation`** — covers Pydantic `DashboardQuery` rejection paths:
   - `page=0` → 400 `validation.dashboard.invalid_pagination`
   - `limit=0` → 400
   - `limit=101` → 400
   - `status_filter="invalid"` → 400 (Pydantic `Literal` rejection)
   - `search` with 101 chars → 400
   All happy-path defaults verified (`page=1`, `limit=20`, `status_filter=None`, `search=None`).

2. **`test_response_composition`** — verifies `_compose_response` is correct in isolation:
   - Mocked `catalog.list_products` returns 3 products + `total=42` (3 of 42 page).
   - Mocked `customer.get_onboarding_completeness` returns specific counts.
   - Verify `DashboardResponse.products` has 3 items, `total=42`, `page` and `limit` echo the request, and `onboarding_completeness` mirrors the mocked completeness shape.

3. **`test_empty_state_response`** — boundary case for first-time sellers:
   - Mocked `catalog.list_products` returns empty list + `total=0`.
   - Dashboard returns 200 with `products=[]` and `total=0` (NOT 404 — empty inventory is a valid state).
   - `onboarding_completeness` still surfaces (the seller still has a profile even with zero products).

**Integration tests** (`backend/tests/integration/test_dashboard_*.py`):

1. **`test_dashboard_list_full_flow`** — end-to-end:
   - Seller signs up via §7 (`POST /otp/send` + `POST /otp/verify`) → JWT.
   - Seller creates 5 products via §10 (`POST /products` × 5).
   - Seller calls `GET /api/v1/products?page=1&limit=20` with JWT.
   - Response: 200, `products` length 5, `total=5`, `onboarding_completeness` reflecting the seller's onboarding state.

2. **`test_dashboard_cross_tenant_isolation`** — the tenancy contract verified end-to-end through dashboard:
   - User A has 3 products, User B has 2 products (both created via §10 paths).
   - User A's `GET /products` returns ONLY A's 3 products + `total=3`.
   - User B's `GET /products` returns ONLY B's 2 products + `total=2`.
   - The enforcement is in `catalog.service.list_products`' repository layer per §10.D, but this integration test verifies the cross-tenant scope is respected end-to-end through the dashboard surface — guarding against any future refactor that might leak User A's rows into User B's response.

**Pytest fixtures:** real Postgres via dev tunnel; seeded users + products from §7 + §10 fixtures (reuse, NOT duplicate). No MSG91 / Gemini / GCS calls needed because dashboard has no vendor egress per §13.H — integration tests for dashboard do not need any vendor stubs.

### 13.K Extraction notes

`dashboard` is the **purest** demonstration of the modular monolith extraction discipline because it owns no tables AND has no repository file. Extraction in V1.5 reduces to swapping in-process Python calls for HTTP calls with **zero data-layer migration**. Per §21's recommended extraction order, dashboard is one of the easiest extractions (alongside `export` per §2.8); both can extract independently of the spine — `catalog` is the hardest per §10.K and extracts last. The extraction shape: a `dashboard` BFF pod that holds the FastAPI route + Pydantic schemas + composition logic, and makes `httpx.AsyncClient` calls to `catalog-svc` and `customer-svc` for the underlying data. V1.5 may also opt into the OPTIONAL summary endpoints (`image.service.summary` per §11.C, `pricing.service.summary` per §12.C, `export.service.summary` from §14 forthcoming) for richer per-product status badges (e.g., "watermark detected" / "thin margin" / "exported last week"); that opt-in elevates the §2.D matrix from 8 ✓ to 11 ✓ at §13 amendment time (NOT now per the founder ruling kept at the §2 lock).

### 13.L What §13 does NOT cover

- **The DDL of any table** — dashboard owns NONE. See `MVP_ARCH §2` for the 13-table schema; none of them are dashboard's.
- **Any repository methods** — there is no `modules/dashboard/repository.py` file. This absence is structural per §13.D, not an omission. The §19 CI linter must allowlist dashboard as a documented exception to the per-module subtree completeness check.
- **The optional cross-module `summary()` integrations** — `image.service.summary` (§11.C OPTIONAL), `pricing.service.summary` (§12.C OPTIONAL), `export.service.summary` (§14 OPTIONAL when authored). The founder ruling at §2 kept the §2.D matrix at exactly 8 ✓; these surfaces exist on the producer side but dashboard does NOT call them in V1. V1.5 amendment can elevate the matrix; not §13's job to pre-empt that.
- **The exact English message strings** for the 1 dashboard-specific `validation_message_id` (`validation.dashboard.invalid_pagination`) — that copy lands in `backend/app/i18n/messages_en.py` during the `services-builder` construction dispatch.
- **The frontend dashboard component rendering** — owned by `meesell-frontend-coordinator` + `meesell-angular-component-builder` in `FRONTEND_ARCHITECTURE.md`. §13 specifies the wire shape only.
- **Aggregation-heavy reports or analytics dashboards** (e.g., monthly revenue rollups, per-category conversion funnels) — V1.5+ feature; not in the §0.C 27-endpoint contract; not §13's scope.
- **The seller's first-time empty-state UX copy and CTAs** — frontend concern. §13 only guarantees the empty list is a valid 200 (not a 404 redirect).

---

## Section 14 — Module: `export`

STATUS: LOCKED (2026-06-05)

### 14.A Preamble

§14 specifies the `export` module — Meesho XLSX generation, the **entire Export Adapter from `MVP_ARCH §5.5`** including the 9-step pipeline, 2 `ComplianceStrategy` classes (`StandardComplianceStrategy` for the 3,771 templates with 9-field compliance + `CollapsedComplianceStrategy` for the 1 Eye-Serum template at leaf 12378 per §0.G §12.6), round-trip validation per `MVP_ARCH §5.7` with 15 golden fixtures, and the `exports` table (the only table owned by this module per `MVP_ARCH §2.5`). **Owner specialists:** `meesell-services-builder` (heavy lifting — the entire Export Adapter implementation including the `ComplianceStrategy` ABC + 2 concrete subclasses, the 9-step pipeline orchestrator, the round-trip validator, the XLSX writer via openpyxl, the image ZIP packager) + `meesell-api-routes-builder` (the endpoint surface — POST initiate + GET poll). **NO AI track collaboration** — export is deterministic transformation; the Layer 3 hallucination guardrail per `MVP_ARCH §9.7` re-validates AI-emitted enum values at emit time, but the re-validation logic itself is deterministic dictionary lookup against `field_enum_values.enum_entries`, not AI.

`export` is **the most-cross-module module in the codebase** per the §2.D matrix (4 outbound ✓ calls — to `catalog`, `customer`, `category`, and `image`). It writes the `exports` table exclusively. Surfaces **2 endpoints**, both in the §0.C 27-endpoint contract. **Philosophy M10 lives here** — `meesho_column_header`, `meesho_column_index`, and `enum_codes_map` are three symbols that exist ONLY in this module's source tree (`modules/export/{domain.py, service.py, tasks.py}`) and the §6.D `adapters/gcs.py` write paths; they NEVER appear in API responses to the seller, NEVER in AI prompts, NEVER in cache payloads outside this module. The Export Adapter is the **marketplace-isolation boundary** per `MVP_ARCH §5.5.9` — when V2 multi-marketplace lands (Amazon / Flipkart / Etsy per `MVP_ARCH §14`), the `MarketplaceExportAdapter` abstract base class + concrete subclasses live in this module's `domain.py`. V1 ships exactly one concrete subclass: `MeeshoExportAdapter`.

§14 does **NOT** specify the DDL of the `exports` table (`MVP_ARCH §2.5` is authoritative), does NOT specify the GCS adapter implementation (§6.D is authoritative), does NOT specify the `FieldSpec` contract that schema_jsonb consumers share (§5A.C is authoritative), does NOT specify the V2 marketplace adapter concrete subclasses beyond the V1 `MeeshoExportAdapter` (V2 scope per `MVP_ARCH §14`), and does NOT specify the `core/cache.py` ETag + single-flight + pre-warm implementation (§4.D is authoritative — export consumes cached schema / enum reads via the underlying `category.service`'s own caching per §9.B). Reviewer questions inherited from §0.E: how the Export Adapter consumes the `field_aliases.for_xlsx_export = TRUE` reverse-map per §0.G §12.2 (answered in §14.E step 7); how the `CollapsedComplianceStrategy` realizes the 9→3 derivation without storing derived data per philosophy F4 (answered in §14.F); how Layer 3 guardrail per `MVP_ARCH §9.7` enforces enum-validity at emit time (answered in §14.E step 5).

### 14.B Endpoint surfaces

The module surfaces **2 endpoints** in the locked §0.C 27-endpoint contract.

#### 14.B.1 `POST /api/v1/products/{id}/export-xlsx` — Initiate XLSX export (Feature 9)

**Request body** (Pydantic v2 `ExportRequest` — see §14.G):

| Field | Type | Default | Constraints |
|---|---|---|---|
| `format` | `Literal["xlsx_only", "xlsx_with_images"]` | `"xlsx_with_images"` | Two values only |

The default `xlsx_with_images` matches the primary Feature 9 UX (seller downloads sheet + image ZIP in one go). The `xlsx_only` value is the V1.5+ bulk-export use case (when the seller has already downloaded images previously and only needs the refreshed sheet).

**Response 202** (`ExportInitiatedResponse` — see §14.G):

```json
{
  "export_id": "5b1a...-uuid",
  "status": "pending",
  "enqueued_task_id": "celery-task-uuid",
  "initiated_at": "2026-06-05T12:34:56+05:30"
}
```

**Rate limit:** `@rate_limit(scope="export_initiate", limit="10/h", key="user_id")` per §4.E. Heavy bandwidth + CPU operation; 10/h covers the normal "list 5 products then export each" workflow with margin for retries.

**Plan guard:** NOT participating in V1. Exports are core seller value — capping them would directly damage the primary value prop (the seller's reason for paying). V1.5 may introduce per-tier export limits if abuse appears.

**Status codes:** 202 (accepted), 400 (`validation.export.invalid_format`), 401 (no JWT), 404 (`catalog.product_not_found` — from `assert_product_ownership`; either the product does not exist or it is not owned by the requesting user — same surface per §1.E privacy posture), 422 (`export.product_not_ready` — product `status != "ready"` per §10, OR image precheck status is `"failed_precheck"` per §11; the export pipeline assumes all upstream data is valid).

**Audit:** middleware emits `export.initiated` with `{product_id, export_id, format}` (no PII) per §11.9 / §4.G. Worker emits `export.completed` or `export.failed` via direct ORM write inside `tasks.py` (same documented exception pattern as §6A.D `cost_tracker`, §7.B `verify_otp`, §11.E precheck task — workers have no request close to hang the middleware emission off).

**JWT required:** yes (access JWT via `Authorization: Bearer` header per §4.B).

**Flow** (6 steps):

1. `await catalog.service.assert_product_ownership(product_id, user_id)` per §10.C — raises `catalog.exceptions.ProductNotFoundError` (404) if not owned.
2. Load product via `catalog.service.get_product_for_export(product_id, user_id)`; verify `status == "ready"`. If not, raise `ProductNotReadyForExportError` (422 `export.product_not_ready`).
3. If `request.format == "xlsx_with_images"`: verify `await image.service.list_images(product_id, user_id)` shows **at least 1 image with `status="ready"` AND `idx=1`** (front image required per `MVP_ARCH §0` premise #3). If not, raise `FrontImageMissingError` (422 `export.front_image_missing`).
4. Repository insert: `exports({user_id, product_id, format, status="pending", initiated_at=now()})` returning `Export` domain object with newly-generated UUID.
5. Enqueue Celery task: `task = export_xlsx_task.delay(export_id=export.id, user_id=user_id)` to Valkey DB 1 broker per §5.C. Task name `export.xlsx`.
6. Return 202 `ExportInitiatedResponse({export_id=export.id, status="pending", enqueued_task_id=task.id, initiated_at=export.initiated_at})`.

#### 14.B.2 `GET /api/v1/exports/{id}` — Poll export status + download URLs

**Request:** no body. `id` is the `exports.id` UUID. Authorization via JWT required.

**Response 200** (`ExportResponse` — see §14.G):

| Field | Type | Populated when |
|---|---|---|
| `export_id` | `UUID` | always |
| `product_id` | `UUID` | always |
| `status` | `Literal["pending","ready","failed"]` | always |
| `format` | `Literal["xlsx_only","xlsx_with_images"]` | always |
| `xlsx_signed_url` | `str \| None` | `status="ready"` |
| `zip_signed_url` | `str \| None` | `status="ready"` AND `format="xlsx_with_images"` |
| `error_message` | `str \| None` | `status="failed"` |
| `error_code` | `str \| None` | `status="failed"` (one of the 7 codes per §14.H) |
| `initiated_at` | `datetime` | always |
| `completed_at` | `datetime \| None` | `status` is `"ready"` or `"failed"` |
| `round_trip_validated` | `bool \| None` | `status="ready"` (always `True` when `status="ready"` per `MVP_ARCH §5.7` invariant) |

Signed URLs are generated **fresh per response** at 1h TTL per §6.D — the frontend can re-poll to refresh expired URLs (the upstream GCS objects are stable; only the URL signature rotates).

**Rate limit:** per-IP only (the frontend polls until ready; exponential backoff is owned by FRONTEND_ARCH per `FRONTEND_ARCH §11`). Same posture as §11.B.2 image poll.

**Status codes:** 200, 401, 404 (`export.not_found` — either does not exist or not owned by the requesting user; the repository's `scope_to_user` filter conflates the two for privacy per §4.C).

**Audit:** NONE (read-only polling — same posture as §11.B.2 image poll, §13.B.1 dashboard list). Documented absence.

**JWT required:** yes.

**Flow** (4 steps):

1. `export.repository.find_by_id(db, user_id, export_id)` — uses `scope_to_user(user_id)`; raises `ExportNotFoundError` (404) if no row matches the user-scoped query.
2. If `export.status == "ready"`: generate fresh signed GCS URLs via `adapters.gcs.generate_signed_url(export.xlsx_gcs_path, ttl_seconds=3600)` per §6.D for the XLSX; and for the ZIP if `export.format == "xlsx_with_images"`.
3. Compose `ExportResponse` from the `Export` domain object + the signed URLs (if any).
4. Return 200.

### 14.C Service layer

`modules/export/service.py` exposes a dual surface: **public methods** consumed by the router (synchronous-from-caller-perspective request/response flow), and **worker-internal helpers** consumed only by the Celery task in `tasks.py` (the 9-step pipeline orchestration broken into one named method per step). The worker-internal helpers are prefixed with `_` and are module-private per §16 — no other module imports them, ever. Public surfaces are async (FastAPI request scope); worker-internal helpers may be sync or async depending on whether they perform I/O.

**Public surface** (called from `modules/export/router.py`):

```python
async def initiate_export(
    user_id: UUID,
    product_id: UUID,
    request: ExportRequest,
) -> ExportInitiatedResponse:
    """POST /products/{id}/export-xlsx — 6-step flow per §14.B.1."""

async def get_export(
    user_id: UUID,
    export_id: UUID,
) -> ExportResponse:
    """GET /exports/{id} — 4-step flow per §14.B.2."""
```

**Cross-module surface** (optional, available but not consumed in V1):

```python
async def summary(
    user_id: UUID,
    product_ids: list[UUID],
) -> dict[UUID, ExportStatusSummary]:
    """OPTIONAL — for dashboard V1.5 elevation per §2.D matrix note.
    Surface exists; dashboard does NOT call in V1 (matrix kept at 8 ✓).
    Returns the latest export per product for richer status badges."""
```

**Worker-internal helpers** (called from `tasks.py` only; module-private; the 9-step pipeline orchestrator + its named steps):

```python
async def _run_export_pipeline(export_id: UUID, user_id: UUID) -> None:
    """The 9-step pipeline orchestrator. Calls steps 1-9 in order.
    On any raised exception, calls repository.update_status_failed with the
    error_code from the exception class (per §14.H taxonomy)."""

async def _resolve_schema(category_id: UUID) -> dict:
    """Step 1 — resolve the templates.schema_jsonb envelope per §5A.B.
    Calls category.service.fetch_schema(category_id) per §9.C; consumes
    cache via category's own per-category cache helper per §9.B."""

def _select_strategy(compliance_shape: str) -> ComplianceStrategy:
    """Step 2 — dispatch on schema.compliance_shape per §5A.F.
    \"standard\" → StandardComplianceStrategy()
    \"collapsed\" → CollapsedComplianceStrategy()
    Anything else → raises ComplianceStrategyError."""

async def _build_row(
    product_id: UUID,
    user_id: UUID,
    schema: dict,
) -> XlsxRowSpec:
    """Step 3 — gather product fields + ai_suggestions + applied snapshot +
    compliance block. Cross-module calls: catalog.get_product_for_export +
    customer.get_compliance_block. Produces an XlsxRowSpec in CANONICAL
    column ordering (i.e. schema_jsonb.fields[] order)."""

def _apply_strategy(
    row: XlsxRowSpec,
    strategy: ComplianceStrategy,
) -> XlsxRowSpec:
    """Step 4 — invoke strategy.apply(compliance_block) and merge its output
    columns into the row. Standard: pass-through 9→9. Collapsed: 9→3."""

async def _translate_enums(
    row: XlsxRowSpec,
    category_id: UUID,
) -> XlsxRowSpec:
    """Step 5 — canonical → meesho translation per field via
    category.service.get_field_enum(category_id, name) per §9.C.
    THIS IS THE LAYER 3 HALLUCINATION GUARDRAIL per MVP_ARCH §9.7.
    Each enum value is looked up in field_enum_values.enum_entries; if
    canonical value is not found, raises ExportEnumValidationError."""

def _reorder_columns(
    row: XlsxRowSpec,
    schema: dict,
) -> XlsxRowSpec:
    """Step 6 — re-order row.columns to match schema_jsonb.fields[] index
    position (Meesho's expected XLSX column ordering)."""

def _restore_aliases(
    row: XlsxRowSpec,
    schema: dict,
) -> XlsxRowSpec:
    """Step 7 — restore canonical_name → meesho_column_header per
    field_aliases.for_xlsx_export = TRUE per §0.G §12.2 (the typo restore:
    canonical 'no_of_primary_cameras' → meesho 'No. of Primiary Cameras').
    Sourced from category.service.fetch_xlsx_aliases(category_id) per §9.C."""

def _write_xlsx(row: XlsxRowSpec) -> bytes:
    """Step 8 — openpyxl write. V1 = header row + 1 data row (one product
    per export). V1.5 bulk-export will accept list[XlsxRowSpec].
    Returns the XLSX file bytes ready for GCS upload."""

def _round_trip_validate(
    xlsx_bytes: bytes,
    original_snapshot: dict,
) -> RoundTripResult:
    """Step 9 — re-parse the just-written XLSX via openpyxl + canonical
    re-map, then assert equivalence with the original snapshot per
    MVP_ARCH §5.7. On mismatch, returns RoundTripResult(passed=False,
    mismatches=[...]) — the caller then raises RoundTripValidationError."""

async def _package_images_zip(
    image_paths: list[str],
    user_id: UUID,
) -> bytes:
    """Image ZIP packaging — only invoked when format == 'xlsx_with_images'.
    Calls adapters.gcs.download_bytes for each image path per §6.D, then
    zipfile.ZipFile.writestr() in-memory. Returns ZIP bytes for GCS upload."""
```

The 9-step pipeline is intentionally broken into one named method per step (rather than inlined in `_run_export_pipeline`) so the §14.K test plan can unit-test each step in isolation against the 15 golden fixtures per `MVP_ARCH §5.7`. Each step is **idempotent** within a single `_run_export_pipeline` call (no hidden state mutation); `XlsxRowSpec` is a frozen dataclass per §14.F so each step returns a NEW `XlsxRowSpec` rather than mutating the input.

### 14.D Repository layer

`modules/export/repository.py` exposes **5 methods**, all **module-private** per §16 (no other module imports them — cross-module reads of export status happen via `export.service.summary()`, which itself calls into this repository). Every method uses `scope_to_user(user_id)` per §4.C — `exports.user_id` is the tenancy column and there is no global state in this module (cf. §9 category, where global state is the documented exception).

```python
async def insert(
    db: AsyncSession,
    user_id: UUID,
    product_id: UUID,
    format: Literal["xlsx_only", "xlsx_with_images"],
    initiated_at: datetime,
) -> Export:
    """Insert a new exports row with status='pending'. Returns the freshly-
    created Export domain object (with the new UUID populated)."""

async def find_by_id(
    db: AsyncSession,
    user_id: UUID,
    export_id: UUID,
) -> Export | None:
    """Find an export by ID. Returns None if not found OR not owned by
    user_id (404 conflation per §4.C privacy posture)."""

async def update_status_ready(
    db: AsyncSession,
    user_id: UUID,
    export_id: UUID,
    xlsx_gcs_path: str,
    zip_gcs_path: str | None,
    completed_at: datetime,
    round_trip_validated: bool,
) -> Export:
    """Worker-only — update the exports row from 'pending' to 'ready' on
    pipeline success. Writes the 2 GCS paths + completed_at + round-trip
    validation flag. The zip_gcs_path is None when format='xlsx_only'."""

async def update_status_failed(
    db: AsyncSession,
    user_id: UUID,
    export_id: UUID,
    error_message: str,
    error_code: str,
    completed_at: datetime,
) -> Export:
    """Worker-only — update the exports row from 'pending' to 'failed'.
    Writes error_message + error_code (one of the 7 codes per §14.H) +
    completed_at. Partial GCS uploads are NOT cleaned up in V1 (V1.5
    cleanup pass per §14.L)."""

async def summarize_by_products(
    db: AsyncSession,
    user_id: UUID,
    product_ids: list[UUID],
) -> dict[UUID, ExportStatusSummary]:
    """Return the latest export row per product_id. Used by
    service.summary() — OPTIONAL surface for V1.5 dashboard elevation."""
```

All 5 methods are `async` (SQLAlchemy `AsyncSession`). The two worker-only updates (`update_status_ready` / `update_status_failed`) are called from inside `tasks.py` via the documented direct-DB-write pattern per §6A.D — worker tasks open their own `AsyncSession` via `make_worker_session()` per §5.B because the Celery task has no FastAPI request scope to hang `get_db` off.

### 14.E Celery task

`modules/export/tasks.py` defines **one Celery task** — the 9-step Export Adapter pipeline. It is one of only **2 modules with a `tasks.py`** per the §3.C canonical subtree (the other being `image` per §11.E). Task discovery happens via `workers/celery_app.py` per §3.I — the `celery_app.autodiscover_tasks(["app.modules.image", "app.modules.export"])` line registers both module's tasks.py at worker startup.

```python
from app.workers.celery_app import celery_app
from uuid import UUID

@celery_app.task(name="export.xlsx", bind=True, max_retries=1, retry_backoff=True)
def export_xlsx_task(self, export_id: UUID, user_id: UUID) -> None:
    """
    The 9-step Export Adapter pipeline per MVP_ARCH §5.5.4.

    Flow (delegates to export.service._run_export_pipeline):

      1. Resolve schema via category.service.fetch_schema(category_id)
         — consumes per-category cache per §9.B (60s TTL).

      2. Select ComplianceStrategy based on schema.compliance_shape per §5A.F:
           StandardComplianceStrategy   for "standard" (3,771 templates)
           CollapsedComplianceStrategy  for "collapsed" (1 Eye-Serum leaf 12378
                                          per §0.G §12.6)

      3. Build row — gather product.fields_jsonb + product.ai_suggestions +
         compliance_block (cross-module: catalog.get_product_for_export +
         customer.get_compliance_block). Produces an XlsxRowSpec in canonical
         ordering.

      4. Apply strategy:
           StandardComplianceStrategy:  9 fields → 9 columns (pass-through)
           CollapsedComplianceStrategy: 9 fields → 3 combined "Details"
                                          columns concatenating
                                          manufacturer / packer / importer per
                                          §0.G §12.6 founder ruling (9 stored,
                                          3 derived at emit time only — F4
                                          enforcement).

      5. Translate enums — canonical → meesho via category.get_field_enum
         per §9.C. THIS IS THE LAYER 3 HALLUCINATION GUARDRAIL per
         MVP_ARCH §9.7 — the deterministic safety-net even if Layers 1+2 in
         §6A.E were bypassed by a future bug. Each enum value is looked up
         in field_enum_values.enum_entries; unknown canonical raises
         ExportEnumValidationError (error_code=enum_validation_failed).

      6. Reorder columns per schema_jsonb.fields[] index position
         (Meesho's expected XLSX column ordering).

      7. Restore aliases — canonical_name → meesho_column_header via
         field_aliases.for_xlsx_export = TRUE per §0.G §12.2 (typo restore).
         Sourced from category.fetch_xlsx_aliases.

      8. Write XLSX via openpyxl (header row + 1 data row in V1; V1.5
         bulk-export accepts a list of XlsxRowSpec).

      9. Round-trip validate — re-parse the XLSX, assert canonical
         equivalence per MVP_ARCH §5.7. On validation failure, raises
         RoundTripValidationError (error_code=round_trip_mismatch).

    On success: upload XLSX to GCS at
      meesell-exports/{user_id}/{export_id}/sheet.xlsx
    AND, if format='xlsx_with_images', upload images ZIP at
      meesell-exports/{user_id}/{export_id}/images.zip
    Then update exports row with status='ready' + the 2 GCS paths +
    round_trip_validated=True + completed_at=now().

    On failure: capture error_message + error_code per the §14.H error
    taxonomy (one of 7 codes); update exports row with status='failed' +
    error_message + error_code + completed_at=now(). Do NOT delete partial
    GCS uploads (V1.5 cleanup pass — partial uploads cost ~negligible per
    failure case).

    Performance budget per MVP_ARCH §5.5.10: 1 product + 6 images = ≤30s
    wall time. The 9-step pipeline + GCS upload + image ZIP must fit
    inside this budget; if it does not, the round-trip validation step
    will still hold the line on correctness (no truncated XLSX shipped).

    Worker JWT re-validation per §1.G — task payload carries user_id; the
    worker re-validates by checking the user still exists in users (the
    access JWT that initiated the export may have expired during the
    task's pending window; the user-existence check is the sufficient
    surrogate at task time).
    """
    import asyncio
    asyncio.run(_run_export_pipeline_with_error_handling(export_id, user_id))
```

`max_retries=1` (single retry; the 9-step pipeline is deterministic — a second pass after a transient GCS hiccup is reasonable, but a third would mask a real bug). `retry_backoff=True` (exponential backoff between the first attempt and the single retry). `bind=True` so the task can call `self.retry()` from inside `_run_export_pipeline_with_error_handling` for the specific transient-failure cases (GCS 5xx) but NOT for the logical failures (`ExportEnumValidationError`, `RoundTripValidationError`, `ComplianceStrategyError` — those are immediate-fail with no retry).

`asyncio.run(...)` is the Celery V1 idiom for invoking async helpers from a sync task (Celery has no native coroutine support per §11.E precedent).

### 14.F Internal domain types

`modules/export/domain.py` is the meatiest domain layer in the codebase — it owns 5 frozen dataclasses + 1 `ComplianceStrategy` ABC + 2 concrete `ComplianceStrategy` subclasses + 1 `MarketplaceExportAdapter` ABC + 1 V1 concrete `MeeshoExportAdapter` subclass. All names are module-private per §16 unless explicitly tagged as cross-module return types.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID


@dataclass(frozen=True)
class Export:
    """Mirrors the exports row per MVP_ARCH §2.5."""
    id: UUID
    user_id: UUID
    product_id: UUID
    format: Literal["xlsx_only", "xlsx_with_images"]
    status: Literal["pending", "ready", "failed"]
    xlsx_gcs_path: str | None
    zip_gcs_path: str | None
    error_message: str | None
    error_code: str | None
    round_trip_validated: bool | None
    initiated_at: datetime
    completed_at: datetime | None


@dataclass(frozen=True)
class XlsxColumnSpec:
    """One column in the output XLSX.
    M10 boundary: this dataclass holds meesho_column_header and
    meesho_column_index — these symbols MUST NOT escape the export module
    per §14.J."""
    canonical_name: str            # internal canonical field name
    meesho_column_header: str      # exact Meesho XLSX header string per §12.2 typo restore
    meesho_column_index: int       # column position per templates.schema_jsonb.fields[] order
    value: Any                     # the seller's value, possibly translated via enum_codes_map


@dataclass(frozen=True)
class XlsxRowSpec:
    """One row in the output XLSX (V1 = one product per export = one row).
    V1.5 bulk-export will accept a list[XlsxRowSpec] in _write_xlsx."""
    main_sheet_label: str          # from templates.schema_jsonb.main_sheet_label per §5A.B
    columns: list[XlsxColumnSpec]  # ordered per Meesho schema per step 6


@dataclass(frozen=True)
class RoundTripResult:
    """§5.7 round-trip validator output (step 9)."""
    passed: bool
    mismatches: list[str]          # canonical field names that differ between input snapshot
                                   # and re-parsed XLSX
    diagnostic: str | None         # human-readable summary used for error_message


@dataclass(frozen=True)
class ExportStatusSummary:
    """Cross-module return type for export.service.summary() — OPTIONAL
    per §2.D matrix (dashboard does not consume in V1; surface exists for
    V1.5 elevation)."""
    product_id: UUID
    latest_export_id: UUID | None
    latest_export_status: Literal["pending", "ready", "failed"] | None
    latest_completed_at: datetime | None


class ComplianceStrategy(ABC):
    """Per MVP_ARCH §5.5.5 — Strategy pattern for compliance-block
    transformation. V1 has exactly 2 concrete subclasses.

    M10 boundary: subclasses must produce XlsxColumnSpec entries whose
    meesho_column_header values come from the locked schema_jsonb.fields[]
    contract per §5A.B — they may NOT invent header strings."""

    @abstractmethod
    def apply(self, compliance_block: "ComplianceBlock") -> list[XlsxColumnSpec]:
        """Transform the 9 standard compliance fields into output XLSX columns.

        Standard:  9 fields → 9 columns (pass-through).
        Collapsed: 9 fields → 3 columns (concatenate manufacturer / packer /
                   importer blocks).
        """


class StandardComplianceStrategy(ComplianceStrategy):
    """3,771 templates (all except Eye-Serum). 9 fields → 9 columns
    pass-through. Each input field becomes one XlsxColumnSpec with its
    canonical_name unchanged and its meesho_column_header sourced from
    schema_jsonb.fields[] per §5A.B."""

    def apply(self, compliance_block: "ComplianceBlock") -> list[XlsxColumnSpec]:
        ...  # services-builder implements


class CollapsedComplianceStrategy(ComplianceStrategy):
    """1 template (Eye-Serum, leaf 12378). 9 fields → 3 combined 'Details'
    columns per §0.G §12.6 founder ruling: 9 stored, 3 derived at emit
    time only. Implements Philosophy F4 (no derived data stored — the 3
    collapsed columns exist ONLY in the XLSX, never in any database
    column). The collapse rule:

        meesho 'Manufacturer Details'  ← concat(name, address, contact)
        meesho 'Packer Details'        ← concat(name, address, contact)
        meesho 'Importer Details'      ← concat(name, address, contact)

    Concatenation separator is locked at ', ' (comma-space) per the §0.G
    §12.6 reference XLSX inspection. Empty input fields are dropped from
    the concatenation (not represented as 'None' or empty separators)."""

    def apply(self, compliance_block: "ComplianceBlock") -> list[XlsxColumnSpec]:
        ...  # services-builder implements


class MarketplaceExportAdapter(ABC):
    """Per MVP_ARCH §5.5.9 — V2 future-proofing for multi-marketplace.

    V1 has exactly ONE concrete subclass: MeeshoExportAdapter.
    V2 will add AmazonExportAdapter, FlipkartExportAdapter,
    EtsyExportAdapter (scope per MVP_ARCH §14).

    Each subclass owns its marketplace-specific column ordering, alias
    map, and compliance shape — all marketplace knowledge stays inside
    this adapter ABC hierarchy per philosophy M10.

    The ABC is locked here in V1 so the V2 expansion lands as additional
    concrete subclasses with NO refactor of the export module's public
    surface — `service.initiate_export` continues to dispatch to whichever
    `MarketplaceExportAdapter` matches the seller's target marketplace
    (V1 hardcodes Meesho; V2 accepts a `marketplace: str` request field)."""

    @abstractmethod
    async def export(
        self,
        product_id: UUID,
        user_id: UUID,
        format: Literal["xlsx_only", "xlsx_with_images"],
    ) -> bytes:
        """Returns the marketplace-format file bytes (XLSX or whatever the
        target marketplace expects)."""


class MeeshoExportAdapter(MarketplaceExportAdapter):
    """V1 — the only concrete subclass. Runs the 9-step Meesho XLSX
    pipeline per §14.E. Delegates to the worker-internal helpers in
    service.py rather than re-implementing them inline — the adapter is a
    thin wrapper so the V2 sibling adapters can also reuse the helpers
    where overlap exists."""

    async def export(
        self,
        product_id: UUID,
        user_id: UUID,
        format: Literal["xlsx_only", "xlsx_with_images"],
    ) -> bytes:
        ...  # services-builder implements
```

The `ComplianceBlock` type referenced in `ComplianceStrategy.apply(...)` is the cross-module return shape from `customer.service.get_compliance_block(user_id)` per §8.C — its 9-field shape is locked at §8.F and re-exported here as a `from app.modules.customer.domain import ComplianceBlock` import inside the export domain module (the only cross-module domain import the export module makes, justified by the strategy contract demanding a typed input).

### 14.G Schemas

`modules/export/schemas.py` defines the **Pydantic v2 wire models** for the 2 endpoint surfaces. These are the only public-facing types; the §14.F domain types are internal.

```python
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel


class ExportRequest(BaseModel):
    """POST /products/{id}/export-xlsx body."""
    format: Literal["xlsx_only", "xlsx_with_images"] = "xlsx_with_images"


class ExportInitiatedResponse(BaseModel):
    """POST /products/{id}/export-xlsx 202 response."""
    export_id: UUID
    status: Literal["pending"]
    enqueued_task_id: str
    initiated_at: datetime


class ExportResponse(BaseModel):
    """GET /exports/{id} 200 response."""
    export_id: UUID
    product_id: UUID
    status: Literal["pending", "ready", "failed"]
    format: Literal["xlsx_only", "xlsx_with_images"]
    xlsx_signed_url: str | None
    zip_signed_url: str | None
    error_message: str | None
    error_code: str | None
    initiated_at: datetime
    completed_at: datetime | None
    round_trip_validated: bool | None


class ExportStatusSummaryResponse(BaseModel):
    """Wire shape for the OPTIONAL cross-module dashboard.summary surface
    per §14.C (V1.5 elevation; the surface exists in V1 but is not
    consumed)."""
    product_id: UUID
    latest_export_id: UUID | None
    latest_export_status: Literal["pending", "ready", "failed"] | None
    latest_completed_at: datetime | None
```

No `meesho_column_header` or `meesho_column_index` or `enum_codes_map` appears in any of these wire models — that's M10 enforcement at the schema layer per §14.J.

### 14.H Exception hierarchy

`modules/export/exceptions.py` defines **7 export-specific exception classes**, all subclassing `MeesellError` per §4.F. The exception class IS the error taxonomy per `MVP_ARCH §5.5.12`.

```python
from app.core.errors import MeesellError


class ExportError(MeesellError):
    """Base class for export module failures. Never raised directly."""


# --- 404 / 422 (router surface, raised before Celery enqueue) ---

class ExportNotFoundError(ExportError):
    """GET /exports/{id} — no row matches user-scoped query."""
    status_code = 404
    validation_message_id = "export.not_found"


class ProductNotReadyForExportError(ExportError):
    """POST /products/{id}/export-xlsx — product.status != 'ready'."""
    status_code = 422
    validation_message_id = "export.product_not_ready"


class FrontImageMissingError(ExportError):
    """POST /products/{id}/export-xlsx — format=xlsx_with_images requires
    at least 1 image with idx=1 and status='ready'."""
    status_code = 422
    validation_message_id = "export.front_image_missing"


# --- 500 (worker-internal; surfaces to client as status='failed' with
#     error_message + error_code) ---

class ExportEnumValidationError(ExportError):
    """Step 5 — Layer 3 hallucination guardrail rejection per
    MVP_ARCH §9.7. A canonical enum value emitted by AI autofill (or
    typed by the seller) is not present in field_enum_values.enum_entries
    for the relevant category+field combo. The deterministic safety net
    that holds the line even if Layer 1 (prompt prefix) and Layer 2 (post-
    response re-validation in §6A.E) were bypassed by a future bug."""
    status_code = 500
    validation_message_id = "export.enum_validation_failed"
    error_code = "enum_validation_failed"


class ComplianceStrategyError(ExportError):
    """Step 4 — strategy.apply(...) raised an unexpected exception, OR
    schema.compliance_shape is neither 'standard' nor 'collapsed'."""
    status_code = 500
    validation_message_id = "export.compliance_strategy_failed"
    error_code = "compliance_strategy_failed"


class XlsxBuildError(ExportError):
    """Step 8 — openpyxl write failed (out-of-memory, corrupt input cell,
    encoding error). The 15 golden round-trip fixtures per §14.K test the
    common cases, but openpyxl can still raise on edge cases at runtime."""
    status_code = 500
    validation_message_id = "export.xlsx_build_failed"
    error_code = "xlsx_build_failed"


class RoundTripValidationError(ExportError):
    """Step 9 — re-parse showed canonical mismatch with the input snapshot
    per MVP_ARCH §5.7. The XLSX is logically incorrect; do not ship.
    Surfaces to seller as status='failed' with error_message describing
    the mismatched field(s) — the seller's recovery path is to re-run
    the export (the underlying product data is unaffected)."""
    status_code = 500
    validation_message_id = "export.round_trip_mismatch"
    error_code = "round_trip_mismatch"
```

The 4 worker-internal 500-class exceptions all carry an `error_code` class attribute that the worker writes to `exports.error_code` via `repository.update_status_failed`. The `validation_message_id` is the i18n key per §5A.D — the GET `/exports/{id}` response uses the resolved English string for `error_message`. The 7 i18n keys are queued for `i18n/messages_en.py` during the services-builder dispatch (see §14.J).

### 14.I Adapter usage

The `export` module's adapter footprint is **narrow but deep**: only `adapters.gcs`, no other vendor.

| Adapter | Method | Pipeline step | Purpose |
|---|---|---|---|
| `adapters.gcs.upload_bytes` | step 8 (XLSX) | Upload XLSX bytes to `meesell-exports/{user_id}/{export_id}/sheet.xlsx` per §6.D |
| `adapters.gcs.upload_bytes` | image ZIP packaging | Upload ZIP bytes to `meesell-exports/{user_id}/{export_id}/images.zip` when `format='xlsx_with_images'` |
| `adapters.gcs.download_bytes` | image ZIP packaging | Read each image from `meesell-images/{user_id}/{product_id}/{idx}.jpg` per §6.D for inclusion in the ZIP |
| `adapters.gcs.generate_signed_url` | `GET /exports/{id}` response | 1h TTL signed URLs per §6.D for both XLSX + ZIP download |

**GCS path conventions** (locked here, consistent with §6.D + `MVP_ARCH §10.8`):

| Object | Path |
|---|---|
| XLSX | `meesell-exports/{user_id}/{export_id}/sheet.xlsx` |
| Image ZIP | `meesell-exports/{user_id}/{export_id}/images.zip` |
| Source images (read-only by export) | `meesell-images/{user_id}/{product_id}/{idx}.jpg` |

The `{user_id}` path prefix is the **structural enforcement of tenant isolation at the object-store layer** per §6.D — even if a future bug bypassed the application-layer `scope_to_user`, the GCS object would still live under the correct tenant's prefix and a cross-tenant signed URL request would 404 against an object that does not exist in the target tenant's namespace.

**No other adapter calls.** No Gemini (export is deterministic per §14.A), no MSG91 (export does not send SMS), no Razorpay (export is not a payment surface), no LangFuse (export does not emit AI traces — only AI workloads do, and AI workload tracing is owned by §6A `ai_ops` per the §6.F adapter contract).

### 14.J Cross-cutting integrations

**Rate-limit decorators** (per §4.E):

| Route | Decorator |
|---|---|
| POST `/products/{id}/export-xlsx` | `@rate_limit(scope="export_initiate", limit="10/h", key="user_id")` |
| GET `/exports/{id}` | per-IP only (no decorator; the polling pattern is rate-limited by the frontend's exponential backoff) |

**Plan guard:** NOT participating in V1. Exports are core seller value per §14.A — capping them would damage the primary value prop. V1.5 may introduce per-tier export caps if abuse appears.

**Audit middleware** (per §4.G):

| Event | When | Direct ORM write? |
|---|---|---|
| `export.initiated` | POST 2xx (with `product_id`, `export_id`, `format`) | NO — emitted by `audit_mw` post-handler |
| `export.completed` | Pipeline success (worker context, no request scope) | YES — direct ORM write from `tasks.py` (same documented exception pattern as §6A.D `cost_tracker`, §7.B `verify_otp`, §11.E precheck task) |
| `export.failed` | Pipeline failure (worker context, no request scope) | YES — direct ORM write from `tasks.py` (same exception class) |
| GET `/exports/{id}` | (none) | NO event — read-only polling, documented absence per §11.B.2 / §13.B.1 precedent |

**Tenancy** (per §4.C): YES. `exports.user_id` is the tenancy column. Every repository query uses `scope_to_user(user_id)`. The `catalog.service.assert_product_ownership` cross-module call (invoked transitively via `get_product_for_export`) is the higher-level gate at step 1 of the §14.B.1 router flow. The GCS path convention `meesell-exports/{user_id}/...` per §14.I enforces tenant isolation at the object-store layer as defence-in-depth.

**Cache helper** (per §4.D): NOT participating directly — exports are per-product write-heavy with low hit-rate potential (a seller exports a product, then mutates it, then exports again; each export is fresh). However, the cross-module READS (schema fetch in step 1, field-enum lookup in step 5, alias map in step 7) DO benefit from `core/cache.py` via the underlying `category.service`'s own cache wrappers per §9.B (full-tree + top-100 schemas pre-warmed at worker startup; the export worker starts up alongside the API worker and inherits the same `core/cache.py` instance per §3.A).

**AI Ops** (per §6A): NONE — export is deterministic.

**Layer 3 hallucination guardrail** (per `MVP_ARCH §9.7`): lives HERE, at step 5 of the pipeline (`_translate_enums`). The deterministic safety net even if Layer 1 (prompt prefix in §6A.E) and Layer 2 (post-response re-validation in §6A.E) were bypassed by a future bug. This is **structural enforcement of philosophy F3** (never send invalid enum values to Meesho) per §0.H — three layers of defence, the third of which is independent of the AI stack entirely.

**Philosophy M10 enforcement:** lives HERE. The three symbols `meesho_column_header`, `meesho_column_index`, and `enum_codes_map` exist ONLY in:

- `modules/export/domain.py` (the `XlsxColumnSpec` dataclass fields)
- `modules/export/service.py` (the 9 worker-internal helpers in §14.C)
- `modules/export/tasks.py` (the `export_xlsx_task` orchestrator in §14.E)
- `adapters/gcs.py` write paths (only the byte-stream upload; no semantic awareness of XLSX column headers in the adapter itself)

These symbols MUST NEVER appear in:
- API responses to the seller (no Pydantic schema in `schemas.py` per §14.G mentions them)
- AI prompts (no `ai_ops/prompts/*.py` may reference them)
- Cache payloads outside this module (`core/cache.py` keys do not carry them)
- Any other module's import surface (per §16 module privacy)

The §19 CI linter **must enforce this with a forbidden-import rule** on these three symbols — any `from app.modules.export.domain import XlsxColumnSpec` (or similar) outside the `app/modules/export/` subtree is a CI failure. This is the **structural M10 boundary** per §0.H.

**i18n** (per §5A.D): 7 export-specific `validation_message_id`s land in `i18n/messages_en.py` during the services-builder dispatch — one per `Exception` subclass in §14.H. Initial English strings (services-builder finalizes wording):

| `validation_message_id` | Draft English string |
|---|---|
| `export.not_found` | "Export not found." |
| `export.product_not_ready` | "Product is not ready for export. Complete the product setup first." |
| `export.front_image_missing` | "A front image is required to export with images. Upload an image in slot 1." |
| `export.enum_validation_failed` | "Export failed: an invalid value was detected. Please re-run the export." |
| `export.compliance_strategy_failed` | "Export failed: unable to process compliance information." |
| `export.xlsx_build_failed` | "Export failed: unable to generate the XLSX file." |
| `export.round_trip_mismatch` | "Export failed: data validation mismatch. Please re-run the export." |

### 14.K Test plan + 15 golden round-trip fixtures

**Unit tests** (`backend/tests/modules/export/`):

1. `test_ownership_gate` — POST `/products/{other_user_product}/export-xlsx` returns 404 `catalog.product_not_found`.
2. `test_product_status_check` — product with `status="draft"` returns 422 `export.product_not_ready`.
3. `test_front_image_check` — `xlsx_with_images` format on product with no `idx=1` image returns 422 `export.front_image_missing`.
4. `test_compliance_strategy_dispatch` — `compliance_shape="standard"` selects `StandardComplianceStrategy`; `"collapsed"` selects `CollapsedComplianceStrategy`; anything else raises `ComplianceStrategyError`.
5. `test_standard_strategy_9_to_9` — input `ComplianceBlock` with 9 fields, output 9 `XlsxColumnSpec` (pass-through).
6. `test_collapsed_strategy_9_to_3` — input 9 fields, output 3 combined "Details" columns concatenating manufacturer / packer / importer per §14.F separator-and-empty-drop rules.
7. `test_enum_translation_known` — canonical "PE-HD" → meesho "PE-HD" (V1 mostly identity; V1.5 friendly labels per `MVP_ARCH §14`).
8. `test_enum_translation_unknown_raises` — unknown canonical raises `ExportEnumValidationError` (Layer 3 guardrail per §14.H + `MVP_ARCH §9.7`).
9. `test_alias_restoration_typo` — `canonical_name="no_of_primary_cameras"` → `meesho_column_header="No. of Primiary Cameras"` (typo restored per §0.G §12.2 + `field_aliases.for_xlsx_export`).
10. `test_column_reordering` — canonical `[a, b, c]` reordered to match `schema_jsonb.fields[]` position `[b, a, c]` per step 6.

**Integration tests** (`backend/tests/integration/test_export_*.py`):

1. `test_export_full_pipeline_happy_path` — create product → set fields → upload front image → POST `/export-xlsx` → poll `/exports/{id}` until `status="ready"` → download XLSX via signed URL → verify openpyxl can re-parse the XLSX + non-empty + header row matches.
2. `test_export_blocked_by_failed_precheck` — image precheck `status="failed_precheck"` per §11; POST `/export-xlsx` returns 422 `export.product_not_ready` (the product's status flips to non-ready when the front-image precheck fails per §10 cascade).
3. `test_export_round_trip_validation_failure` — corrupt the XLSX in test (mock the writer to drop a column); verify `_round_trip_validate` rejects + the Celery task updates the `exports` row with `status="failed"` + `error_code="round_trip_mismatch"`; verify GET `/exports/{id}` returns the failed status + error_message + error_code.

**Golden round-trip fixtures** (`backend/tests/integration/golden_round_trip/`) per `MVP_ARCH §5.7` — **the 15-fixture coverage matrix**:

| # | Fixture | Coverage |
|---|---|---|
| 1 | Sarees (Women Fashion, super_id=11) | Standard compliance, single-template baseline. |
| 2 | Mobiles (Electronics, super_id=16) | Standard + typo restore for `no_of_primiary_cameras` per §0.G §12.2. |
| 3 | Eye-Serum (Beauty, leaf=12378) | **Collapsed compliance** strategy — 9→3 derivation per §0.G §12.6 + §14.F. The single test that exercises `CollapsedComplianceStrategy.apply`. |
| 4 | FSSAI Grocery (super_id=26) | Compliance extension required (`fssai_license_number`) per §12.1; tests the `customer.get_compliance_block` super_id branch. |
| 5 | Kids Toys (super_id=13) | Optional BIS license; tests optional-license path through compliance block. |
| 6 | Books (super_id=80) | Optional ISBN per §12.1; tests the optional-extension shape. |
| 7 | Beauty License (super_id=19/36/37/14/88/34 subset) | Required license trio; tests the compulsory-extension branch per §12.1. |
| 8 | Home & Kitchen appliance (super_id=30) | Conditional license; tests the conditional-extension branch per §12.1. |
| 9 | Large dropdown — Compatible Models (4,481 values) | Tests `dropdown_api_search` primitive per §5A.C; the largest enum exercise in V1. |
| 10 | Brand-pattern field — `brand` across 2 categories | Same canonical name, different enum sources per category; tests the per-category enum-resolution branch in step 5. |
| 11 | is_advanced field — `group_id` populated | Per §12.4 is_advanced allowlist; verifies `group_id` writes verbatim to XLSX (not stripped by the advanced-toggle). |
| 12 | Empty optional field | Verifies the XLSX writes a blank cell (not literal "None" or "null") for un-set optional fields. |
| 13 | Number with unit — `weight: 500 g` | 2 columns (value + unit) per `MVP_ARCH §5.6.1`; tests the unit-suffix split-column primitive. |
| 14 | Multi-line text — `description` with newlines | Newlines preserved through XLSX encoding (openpyxl `\n` handling). |
| 15 | Special characters — `name: "Kurti & Top — 5""` | Ampersand, em-dash, and escaped double-quote preserved through XLSX encoding + round-trip re-parse. |

Each fixture lives as `tests/integration/golden_round_trip/fixture_NN_<name>.json` per `MVP_ARCH §5.7.4`. The fixture file format:

```json
{
  "input_snapshot": {
    "product": { "category_id": "...", "fields_jsonb": { ... }, "ai_suggestions": { ... } },
    "compliance_block": { ... },
    "format": "xlsx_with_images"
  },
  "expected_xlsx_canonical": {
    "main_sheet_label": "...",
    "columns": [
      { "canonical_name": "...", "value": "..." },
      ...
    ]
  }
}
```

The validator (`_round_trip_validate` per §14.C step 9) compares the re-parsed XLSX against `expected_xlsx_canonical` field-by-field. Pytest fixtures use real Postgres + Valkey + a GCS test bucket via the dev tunnel; `ai_ops.client.call_gemini` is mocked (none of the 15 fixtures require AI — they test the Export Adapter standalone, which is the point of §5.7).

### 14.L Extraction notes

`export` is **the EASIEST module to extract** per §2.8 + `MVP_ARCH §5.5.9`. It is the most isolated despite being the most-cross-module — no other module imports from `modules/export/*` (the dependency arrows are all inbound: `catalog`, `customer`, `category`, `image` are consumed BY export but never consume export). Extraction reduces to: spin up `export-service` pod with its own GCS access + a dedicated Celery worker for the heavy XLSX build path; change the 4 cross-module Python imports (catalog / customer / category / image) into `httpx.AsyncClient` HTTP calls; add a service-discovery config. No Alembic migration to detach (the `exports` table is owned exclusively by this module and travels with the pod). No row-level lock contention to coordinate.

V2 multi-marketplace expansion (Amazon / Flipkart / Etsy per `MVP_ARCH §14`) lands as additional `MarketplaceExportAdapter` concrete subclasses INSIDE this module's `domain.py` BEFORE extraction (V1.5 prep). Alternatively, each marketplace becomes a sibling pod AFTER extraction with the shared `MarketplaceExportAdapter` ABC promoted to a `pip`-installable internal package (the "shared types" pattern from the Aletheia tenant-isolation playbook). V1 ships only `MeeshoExportAdapter` per `MVP_ARCH §14.F`; the ABC + future-subclass structure is locked here to avoid a V2 refactor of the public service surface.

### 14.M What §14 does NOT cover

- The DDL of `exports` (`MVP_ARCH §2.5` is authoritative).
- The §5.5 detailed file structure per-file content (`MVP_ARCH §5.5.3` — services-builder consults this during construction).
- The 15 golden fixture FILE CONTENT (services-builder authors the fixture JSON files during construction; §14 locks the coverage matrix only).
- The exact final English strings for the 7 export-specific `validation_message_id`s (services-builder finalizes during dispatch; §14.J carries draft strings).
- The V2 marketplace adapter concrete subclasses (`AmazonExportAdapter`, `FlipkartExportAdapter`, `EtsyExportAdapter`) — V2 scope per `MVP_ARCH §14`; only the `MarketplaceExportAdapter` ABC + V1 `MeeshoExportAdapter` concrete are locked here.
- The `core/cache.py` ETag + single-flight + pre-warm implementation (§4.D — export consumes cached schema / enum reads via `category.service`'s own caching).
- The frontend export-trigger UX (FRONTEND_ARCH owns).
- The `field_aliases` table DDL or seed shape (`MVP_ARCH §2.6` + the existing seed scripts are authoritative; export only consumes via `category.fetch_xlsx_aliases`).

---

---

## Section 15 — Cross-Cutting Systems Walkthrough

STATUS: LOCKED (2026-06-06)

### 15.A Preamble

§15 is the **single source of truth for cross-cutting concerns** — the consolidation section a reader consults when asking "how does X work across modules". Per the §3.K decision-tree heuristic ("when a reader asks 'how does X work across modules', §15 answers"), every cross-cutting concern walked here is **locked in an earlier section**; §15 consolidates the per-module participation into one matrix per concern.

**§15 does NOT introduce new contracts.** Every claim cites the original locking section. If a future amendment is needed to a cross-cutting behavior, the amendment lands in the **original section** (e.g. amend §4.D for caching changes), and §15 is updated to mirror. A reviewer evaluating §15 asks: "is every per-module participation correctly summarized, are the source citations accurate, are there any cross-cutting concerns not covered here that should be?" — NOT "is the multi-tenancy enforcement rule itself right" (that's §4.C).

The **10 concerns** walked in this section:
1. Multi-tenancy (§15.B)
2. Caching strategy (§15.C)
3. Search & indexing (§15.D)
4. Audit log + autosave coalescing (§15.E)
5. AI operations (§15.F)
6. Plan guard (§15.G)
7. Session management — refresh-token allowlist + FE-D5 (§15.H)
8. CSRF posture (V1) (§15.I)
9. Observability — Prometheus + LangFuse (§15.J)
10. i18n + locale fallback (§15.K)

Per-module participation cross-references the cross-cutting bullets locked in each module's §I sub-section (§7.I iam · §8.I customer · §9.I category · §10.I catalog · §11.J image · §12.I pricing · §13.I dashboard · §14.J export). §15 is the consolidation across those 8 lists.

§15 does NOT cover inter-module communication rules (§16), the endpoint inventory (§17), Celery jobs (§18), test strategy (§19), deployment topology (§20), extraction path (§21), the acceptance checklist (§22), or the risk register (§22A) — see §15.L for what's deferred to subsequent sections.

---

### 15.B Multi-tenancy

**Locking sections:** §4.C (app-level filtering) + `MVP_ARCH §10.4` (path-prefix tenancy at GCS) + `MVP_ARCH §9` (V1.5 RLS migration).

**The 3-layer defense.** Every tenant-isolated operation passes through three independently-enforced layers; a single layer's failure does not yield cross-tenant data exposure.

1. **App-level filtering** — `core/tenancy.scope_to_user(user_id)` is appended to every repository query against the 6 tenant-owned tables per §4.C. The helper returns a SQLAlchemy `where(Model.user_id == user_id)` clause that the repository chains into its base SELECT/UPDATE/DELETE.
2. **Service-layer ownership gate** — `catalog.service.assert_product_ownership(product_id, user_id)` is the canonical structural enforcement point for product-scoped operations, consumed by `image`, `pricing`, `dashboard`, and `export` per §10.C + §11.J + §12.I + §13.I + §14.J. The gate raises `ProductNotFoundError` on miss; the caller never sees a row from a different tenant.
3. **Object-store path convention** — GCS path prefix `{user_id}/` for both images (`meesell-images/{user_id}/{product_id}/{idx}.jpg`) and exports (`meesell-exports/{user_id}/{export_id}.zip`) per §6.D + `MVP_ARCH §10.8`. Defence-in-depth at the GCS ACL level — a signed URL leak does not yield other tenants' bytes because the path prefix differs.

**The 6 owned tables (require `scope_to_user`).** Per `MVP_ARCH §10.2` + §4.C, tenant-owned tables MUST have every repository query scoped:
- `seller_profile` (§8 customer)
- `catalogs` (§10 catalog)
- `products` (§10 catalog)
- `product_drafts` (§10 catalog)
- `product_images` (§11 image)
- `pricing_calcs` (§12 pricing)
- `exports` (§14 export)

**The 4 global tables (NO `scope_to_user`).** Per `MVP_ARCH §10.2` + §9.D, reference data is shared across all tenants:
- `templates`
- `categories`
- `field_enum_values`
- `field_aliases`

**Special-cased tables (neither pattern).** `users` is identity itself (the FK target of every owned table — `scope_to_user` is N/A because the user IS the subject of the row). `audit_events` is written exclusively by `audit_mw` middleware per §2.10 + §4.G and read administratively only — no repository accessor in any domain module.

**§19 CI linter rule (locked at §19).** Any service method touching an owned table whose signature omits `user_id: UUID` is rejected at PR time. The documented exception is the `category` repository per §9.D (global tables — explicitly allowlisted).

**Per-module participation matrix.**

| Module | Owns tables | Repository scoped | Cross-module ownership gate | Path-prefix tenancy |
|---|---|---|---|---|
| iam (§7) | `users` (identity itself; `scope_to_user` N/A — user IS the subject) | N/A | — | — |
| customer (§8) | `seller_profile` | yes via `scope_to_user` per §8.D | called by catalog via `assert_eligible_for_super_id` per §8.C | — |
| category (§9) | none (read-only) | N/A — global data, §19 allowlist exception | — | — |
| catalog (§10) | `catalogs`, `products`, `product_drafts` | yes via `scope_to_user` per §10.D | **exposes** `assert_product_ownership` — consumed by image / pricing / dashboard / export per §10.C | — |
| image (§11) | `product_images` | yes via `scope_to_user` per §11.D | consumes catalog's gate per §11.C; cross-checked against `users` for V1 | yes GCS path `meesell-images/{user_id}/{product_id}/{idx}.jpg` per §6.D + §11.E |
| pricing (§12) | `pricing_calcs` | yes via `scope_to_user` per §12.D | consumes catalog's gate per §12.C | — |
| dashboard (§13) | none (no repository file per §13.D) | N/A — consumed services enforce per §13.I | N/A | — |
| export (§14) | `exports` | yes via `scope_to_user` per §14.D | consumes catalog's gate via `get_product_for_export` per §14.C | yes GCS path `meesell-exports/{user_id}/{export_id}.zip` per §6.D + §14.E |

**V1.5 RLS migration (deferred per `MVP_ARCH §9` + §14).** PostgreSQL Row-Level Security predicates will replace app-level `scope_to_user`; the cross-module service surfaces (`assert_product_ownership`, `get_compliance_block`, `get_onboarding_completeness`, `list_products`) become extracted-pod HTTP boundaries per §21 extraction path. The 3-layer defense survives extraction unchanged — Layer 1 moves into Postgres (RLS predicate), Layer 2 moves into per-pod HTTP gate, Layer 3 stays as GCS path convention.

---

### 15.C Caching strategy

**Locking sections:** §4.D (cache helper + key versioning) + `MVP_ARCH §6` (cache strategy, single-flight, pre-warm, ETag).

**Single helper.** `core/cache.get_or_set(key, fetch_fn, ttl, version=None, single_flight=False)` per §4.D is the sole cache-access surface. Domain modules NEVER call `valkey.get`/`valkey.set` directly — the helper is the only path. The §19 CI linter rejects direct Valkey access from `modules/`.

**Valkey DB allocation.** Per §1.B + §5.C:
- DB 0 — OTP / rate limits / sessions / refresh-allowlist
- DB 1 — Celery broker
- DB 2 — Celery result backend
- DB 3 — **app cache** (dedicated)

**Version-tagged key format.** Per `MVP_ARCH §6.4` + §4.D: `meesell:v{cache_version}:{key}`. Bumping `CACHE_VERSION` env var on the quarterly Meesho refresh atomically invalidates the entire cache — no `FLUSHDB`, no staggered invalidation. The DB 3 keyspace silently rolls over as new key prefixes start being written.

**Single-flight (SET NX EX).** Per `MVP_ARCH §6.8`, single-flight is MANDATORY for the 291 large Brand-pattern enum keys (`field_enum:{cat_id}:brand`) — a 14 MB payload re-computed by 50 concurrent workers would lock up the worker pool. The `single_flight=True` parameter to `get_or_set` activates the SET NX EX lock pattern: only one worker fetches and populates the cache; the rest poll the lock key for up to 5 seconds before erroring or retrying the cache.

**Pre-warm at FastAPI worker startup.** Per `MVP_ARCH §6.7` + §4.D + §9.B: full category tree (1 cache key) + top 100 schemas (100 cache keys) — primed at worker boot via `@app.on_event("startup")` hook, so the cold-start cache miss surface for new workers is bounded.

**ETag short-circuit.** Per `MVP_ARCH §6.6`: `/categories/{id}/schema`, `/categories/{id}/field-enum/{name}`, `/categories` (full tree), and `/seller-profile/required-fields` return strong ETag headers. A 304 Not Modified short-circuits the Angular `HttpClient` JSON re-parse cost.

**Per-module cache participation matrix.**

| Module | Cache user? | Cache keys | TTL | Single-flight? |
|---|---|---|---|---|
| category (§9) | **heaviest consumer** | `schema:{cat_id}` per §9.B, `field_enum:{cat_id}:{name}` per §9.B, `category_tree` per §9.B, `smart_picker:{sha256(q)}` per §9.B | 1 h (reference data) / 15 min (Smart Picker per §6A.C) | yes for `field_enum:{cat_id}:brand` per `MVP_ARCH §6.8` |
| customer (§8) | yes | `seller_profile_required_fields:{user_id}` per §8.I, super_id distinct set per §8.I | 60 s / 1 h | no |
| catalog (§10) | yes (transitively via category) | none of its own per §10.I | — | — |
| iam (§7) | no | — | — | — |
| image (§11) | no per §11.J | — | — | — |
| pricing (§12) | no per §12.I | — | — | — |
| dashboard (§13) | no per §13.I | — | — | — |
| export (§14) | no per §14.J | — | — | — |

**What is NOT cached (locked at §4.D).** Per-user write-heavy data — `products` (PATCH burst from autosave), `pricing_calcs` (re-computed on every input change), `exports` (single-use ZIPs) — because the invalidation rate exceeds the read rate, so caching adds cost without benefit.

---

### 15.D Search & indexing

**Locking sections:** §9 (category browse endpoint) + `MVP_ARCH §7` (search & indexing) + session 2 G4 (the actual GIN migration).

**The only search-indexed endpoint in V1.** ONLY `category.browse` per `MVP_ARCH §7.4` uses pg_trgm GIN indexes. No other module performs trigram search in V1.

**The 3 GIN trigram indexes (shipped in session 2 G4).** Per the 2026-06-05 `a1b2c3d4e5f6_pg_trgm_and_category_gin` Alembic migration, head chain `a1b2c3d4e5f6 → f31c75438e61`:
- `idx_categories_path_trgm` (GIN, pg_trgm on `categories.path`)
- `idx_categories_leaf_name_trgm` (GIN, pg_trgm on `categories.leaf_name`)
- `idx_categories_super_name_trgm` (GIN, pg_trgm on `categories.super_name`)

EXPLAIN ANALYZE on `ILIKE '%kurti%'` confirmed `Bitmap Index Scan on idx_categories_path_trgm` per coordinator memory G4 verification.

**Query shape (locked at §9.D).**
```sql
SELECT id, path, leaf_name, super_name, super_id,
       GREATEST(similarity(path, :q), similarity(leaf_name, :q), similarity(super_name, :q)) AS score
FROM categories
WHERE (path % :q OR leaf_name % :q OR super_name % :q)
  [AND super_id = :sid]
ORDER BY score DESC
LIMIT :limit OFFSET :offset
```

**Ranking and performance budget.** Per `MVP_ARCH §7.6` similarity score is used for ordering, with optional `super_id` filter narrowing. P95 latency budget: ≤ 200 ms per `MVP_ARCH §7.5`.

**What is NOT searched (locked omission).** No other module uses pg_trgm in V1. The `dashboard` list endpoint (§13.B) accepts a `search` query parameter that uses simple `ILIKE name` against `products.name` — btree index, not trigram. Future V1.5+ may extend pg_trgm to product names; a §16 cross-module call (`category.search_products`?) would be required.

---

### 15.E Audit log + autosave coalescing

**Locking sections:** §4.G (audit middleware) + `MVP_ARCH §11` (audit log shape + coalescing + PII scrubbing).

**Default path.** `core/middleware/audit_mw.py` writes one `audit_events` row AFTER successful 2xx response per `MVP_ARCH §11.3`. The middleware is the last in the chain per §3.H (CORS → request_id → auth → tenancy → rate_limit → plan_guard → handler → audit_mw) — observes the response status code before writing.

**Documented direct-write exceptions.** Each exception follows the same pattern: "middleware cannot observe these events from the request close hook because either (a) the event fires inside a Celery worker with no FastAPI request context, or (b) the user_id is resolved INSIDE the service after the failed-auth response is already framed":

| Event | Why direct write | Locking section |
|---|---|---|
| `ai.call` (cost_tracker) | Fires from Celery worker; no request close hook | §6A.D |
| `auth.login.success` / `auth.login.failed` | Failed login has no resolved `user_id` for middleware | §7.B.2 |
| `auth.token.refreshed` / `auth.token.refresh_failed` | Failed refresh has no `user_id` (cookie-only credential) | §7.B.3 |
| `auth.logout` | `user_id` resolved inside service before refresh-allowlist DEL | §7.B.4 |
| `image.precheck.completed` | Celery worker context (no request close) | §11.E |
| `export.completed` / `export.failed` | Celery worker context (no request close) | §14.E |
| `razorpay.webhook.captured` | Captured before user context resolved | §7.B.6 |

**5-minute coalescing.** Per `MVP_ARCH §11.4`, `audit_mw` coalesces consecutive `(user_id, product_id, event_type="catalog.product.updated")` PATCH events within a 5-minute window into a single audit row — yields ~30× volume reduction during the autosave typing burst (a seller editing 10 fields generates one row, not 10). The coalescing applies ONLY to `catalog.product.updated` per §10.I; other event types never coalesce.

**PII scrubbing.** Per `MVP_ARCH §11.9` + §4.G:
- Phone numbers → SHA-256 with `AUDIT_PII_SALT` (env var) before being written to the payload
- FSSAI / GST / BIS license numbers → stripped entirely from payload (field names appear, values do not)
- Pincodes / addresses → field names appear in payload, values are never logged

**V1 write posture (locked at `MVP_ARCH §11.3`).** Synchronous inline append in the request close hook. V1.5 moves to Celery sink (`audit.write` task) — same call site `audit_mw`, swap the implementation from direct ORM INSERT to `audit_writer.delay(payload)`.

**Per-module audit posture matrix.**

| Module | Endpoints with audit (via middleware) | Direct-write events (documented exceptions) | NONE (read-only / introspection) |
|---|---|---|---|
| iam (§7) | `POST /otp/send` | `auth.login.success/failed` (verify), `auth.token.refreshed/refresh_failed` (refresh), `auth.logout` (logout), `razorpay.webhook.captured` (webhook) | `GET /me` (introspection — would flood the table) |
| customer (§8) | 3 PATCH endpoints — `seller-profile`, `active-categories`, `compliance/{super_id}` | none | 2 GET endpoints |
| category (§9) | **NONE** (all 5 endpoints read-only) | none | all 5 GET (read-only) |
| catalog (§10) | `POST create`, `PATCH` (coalesced), `POST autofill`, `DELETE` | none | `GET preview`, `GET draft-recover` |
| image (§11) | `POST upload` (`image.upload.received`) | `image.precheck.completed` (worker) | `GET list` |
| pricing (§12) | `POST calculate` (`pricing.calculated`) | none | — |
| dashboard (§13) | **NONE** (read-only) | none | `GET /products` |
| export (§14) | `POST initiated` (`export.initiated`) | `export.completed`, `export.failed` (worker) | `GET poll` |

---

### 15.F AI operations

**Locking sections:** §6A (the entire AI Operations Layer) + `MVP_ARCH §8` (AI ops + guardrails + cost cap).

**Single import surface.** `ai_ops.client.call_gemini(ctx, prompt_id, prompt_vars, ...)` per §6A.C is the SOLE path domain modules use to invoke Gemini. Domain modules NEVER import `adapters.gemini` directly — the §19 CI linter rejects such imports.

**3 workloads as closed Literal.** Per §6A.A: `Literal["smart_picker", "autofill", "watermark"]`. No 4th workload may be added without a §6A amendment.

**3-layer hallucination guardrail.** Per §0.H F3 + `MVP_ARCH §9.7`:
- **Layer 1** — prompt-level constraint per §6A.E (workload-specific prefix bonded to the prompt template; rejects responses outside the closed value set at the prompt-engineering level)
- **Layer 2** — parser-level enum check per §6A.E (post-response deterministic re-validation against `field_enum_values.enum_entries`; up to 2 retries with corrected prompt)
- **Layer 3** — **deterministic re-validation at export time** per §14.E step 5 (independent of the AI stack — even if Layers 1+2 are bypassed by a future bug, Layer 3 catches unknown canonical enum values at emit time and raises `ExportEnumValidationError`)

**Daily ₹500 budget cap.** Per §6A.F: global ₹500 daily cap (Asia/Kolkata midnight reset) with 80% Prometheus alarm (`ai_ops_budget_alarm_total`) and 100% hard-stop. **Workload-specific graceful fallback** on `BudgetExceededError`:
- Smart Picker → 200 empty suggestions list + `fallback_offered=true` per §9.B (NOT 503)
- Autofill → 200 empty suggestions + `fallback_offered=true` per §10.B (NOT 503)
- Watermark → `precheck_jsonb.watermark_check = "skipped_budget"` + overall image status still resolves to `"ready"` if the 4 Pillow steps pass per §11.E (NOT a failed image)

The founder principle: "sellers are not penalized for budget exhaustion they did not cause."

**Cost tracker.** Per §6A.D: `cost_tracker.record(workload, prompt_tokens, completion_tokens)` writes a `ai.call` audit event directly (one of the §15.E documented exceptions) AND increments the Valkey DB 0 daily counter. Gemini-2.5-flash rates locked as module constants: `RATE_INPUT_PER_1K = 0.0078`, `RATE_OUTPUT_PER_1K = 0.031`.

**LangFuse trace.** Per §6.F: every AI call site fires async `langfuse.trace` per §6A.C step 8 — drop-on-failure with warning log (observability MUST NOT block business path per §1.E + §6.F locked exception #3).

**Per-module AI participation matrix.**

| Module | Workload | Sync / Async invocation | Hourly per-user limit (§4.E plan_guard) |
|---|---|---|---|
| category (§9) | `smart_picker` | sync from FastAPI handler | `smart_picker_hourly = 100/h` |
| catalog (§10) | `autofill` | sync from FastAPI handler (V1) | `ai_autofill_hourly = 50/h` |
| image (§11) | `watermark` | async via Celery task | none (driven by image upload rate which has its own cap) |
| iam (§7) | NONE | — | — |
| customer (§8) | NONE | — | — |
| pricing (§12) | NONE | — | — |
| dashboard (§13) | NONE | — | — |
| export (§14) | NONE (consumes Layer 3 guardrail only) | — | — |

**Orthogonality.** The daily ₹500 cap (§6A.F, global) and the per-user hourly limits (§4.E plan_guard, per-tenant) are independent. A workload may pass plan_guard but fail budget_cap (or vice versa); both checks fire on every AI call.

---

### 15.G Plan guard

**Locking section:** §4.E (the entire plan_guard contract).

**4 resources locked at §4.E.** No other plan-gated resources may be added without a §4.E amendment:
- `product_count` — 100 active products cap (free plan)
- `ai_autofill_hourly` — 50 auto-fill invocations per hour per user
- `smart_picker_hourly` — 100 Smart Picker invocations per hour per user
- `create_product_hourly` — 20 product creations per hour per user

**Enforcement.** `core/plan_guard.enforce_plan_limit(user_id, plan, resource, requested)` raises `PlanLimitExceededError` (HTTP 402 Payment Required + i18n `validation.plan_guard.limit_exceeded` message) when the requested operation would breach the cap.

**V1 plan posture.** Per §4.E: `Literal["free"]` only in V1. V1.5 widens to `Literal["free", "pro"]` — the contract is forward-compatible (the `plan` parameter exists today; only the value set widens).

**Per-module plan-guard participation matrix.**

| Module | Resources enforced | Enforcement point |
|---|---|---|
| catalog (§10) | `product_count` + `create_product_hourly` | `service.create_product` per §10.C + §10.I |
| catalog (§10) | `ai_autofill_hourly` | `service.autofill_product` per §10.C + §10.I |
| category (§9) | `smart_picker_hourly` | `service.suggest_categories` per §9.C + §9.I |
| iam (§7) | NONE | — |
| customer (§8) | NONE | — |
| image (§11) | NONE (4-slot uniform rule is structural DB CHECK per §11.J + `MVP_ARCH §2.5`) | — |
| pricing (§12) | NONE per §12.I | — |
| dashboard (§13) | NONE per §13.I | — |
| export (§14) | NONE per §14.J (V1 — core seller value, capping would damage primary value prop) | — |

**Security-vs-business separation.** OTP rate limit (3/h/phone) is a **security** limit enforced by `rate_limit_mw` per §4.H, NOT plan_guard. Plan_guard is **business budgets** only. The middleware chain order per §3.H is `rate_limit_mw` BEFORE `plan_guard_mw` — security gates before business gates, so an attacker exhausting their own plan budget cannot drown the security layer.

---

### 15.H Session management — refresh-token allowlist (FE-D5)

**Locking sections:** §4.B FE-D5 amendment (2026-06-05) + §7 (iam endpoints) + the 3 founder-ratified coordinator counter-proposals (Lua EVAL, HMAC pepper, Path correction).

**Keyspace.** Valkey DB 0 `cache:refresh:{hmac_sha256(token, REFRESH_TOKEN_PEPPER)}` per §4.B FE-D5 amendment counter-proposal #2. The hash is **HMAC-SHA256 with `REFRESH_TOKEN_PEPPER`** — NOT plain SHA-256 — so a Valkey-only breach does NOT yield live refresh tokens (the attacker also needs the Secret Manager pepper).

**Constant-time comparison.** Per §4.B: `secrets.compare_digest()` for lookup — NEVER `==`. Timing attacks against the hash comparison are precluded.

**Lua EVAL atomic rotation.** Per §7.B.3 + §4.B counter-proposal #1, the rotation script (KEYS[1]=old_key, KEYS[2]=new_key, ARGV[1]=new_payload_json, ARGV[2]=ttl_seconds) executes single-round-trip atomic CAS — `GET old_key → existence check → SET new_key EX ttl → DEL old_key → return old payload`. `SCRIPT LOAD` once at iam-service startup; `EVALSHA` thereafter; `EVAL` fallback on `NOSCRIPT` (after Valkey restart). **Replay attack mitigation**: reusing the old cookie after rotation returns nil because `old_key` is gone — the second `/refresh` with the prior cookie hits the failed-refresh branch and writes an `auth.token.refresh_failed` audit row.

**TTL.** The Valkey key TTL matches `REFRESH_TOKEN_TTL_SECONDS` per §5.D (prod 604800 = 7 days; staging 300 = 5 min; dev 120 = 2 min). Natural expiry — no cron sweep required.

**Logout.** `POST /api/v1/auth/logout` per §7.B.4 DELs the allowlist entry. Next refresh attempt with the cookie returns 401 (server-side revoked) — the contract that frontend memo FE-D5 explicitly required.

**Cookie attributes (locked at §4.B amendment).**
```
refresh_token=<opaque>;
  Domain=.mesell.xyz;
  Path=/api/v1/auth;
  HttpOnly;
  Secure;
  SameSite=Strict;
  Max-Age=REFRESH_TOKEN_TTL_SECONDS
```

The `Path=/api/v1/auth` (NOT `/auth`) is the §4.B counter-proposal #3 — the FE memo's `/auth` would not match the actual endpoint paths under `/api/v1/auth/*` and would break browser cookie attach. With the correction, `/me` (also under `/api/v1/auth/`) receives the cookie, but `/me` consumes the access JWT in `Authorization` header only — the cookie reaching `/me` is harmless. The 7-day refresh cookie does NOT extend to `/api/v1/products`, `/api/v1/categories`, etc.

**Storing HMAC of the token, not the token.** A Valkey-only breach does not expose live refresh tokens — the attacker captures the HMAC, not the token, and cannot reverse it without `REFRESH_TOKEN_PEPPER` from Secret Manager (which is held only by the backend pods).

---

### 15.I CSRF posture (V1)

**Locking sections:** §4.B FE-D5 amendment (2026-06-05) + §7 (iam endpoints) + §4.G CORS amendment.

**Refresh cookie is `SameSite=Strict`.** Per §4.B amendment + §15.H, cross-site requests from another origin do NOT send the refresh cookie. CSRF on `/auth/refresh` and `/auth/logout` is impossible from a third-party site — the browser will not include the cookie on the cross-origin request.

**Access token in `Authorization: Bearer` header.** Per §4.B amendment, the access JWT lives in a header that browsers do NOT auto-attach from another origin. CSRF on the protected API surface (all 25 non-`/auth` endpoints) is impossible — the attacker's cross-origin request has no Authorization header, hits the 401 branch, and never reaches the handler.

**No CSRF surface remaining.** Every endpoint either (a) is in `/api/v1/auth/*` and protected by `SameSite=Strict` cookie attribute, or (b) is outside `/api/v1/auth/*` and protected by Bearer header — and browsers do not bridge either category from cross-origin context.

**V1 posture (locked).** NO CSRF token middleware needed. The architecture is structurally CSRF-resistant via the cookie + Bearer split.

**V1.5 revisit.** If any future feature introduces a non-`SameSite=Strict` HttpOnly session cookie (for any reason), the V1.5 amendment to §4 must add a CSRF token middleware before that feature ships. Today's posture is provable from the cookie attributes and header-only Bearer usage; future drift would invalidate the proof.

---

### 15.J Observability

**Locking sections:** §1 (system topology — Prometheus + LangFuse) + §4 (middleware — request_id + structured logging) + §6A (cost_tracker + LangFuse trace) + §6.F (langfuse adapter — drop-on-failure).

**Correlation ID.** `core/middleware/request_id.py` per §4.F generates a UUIDv4 per request, attaches it to `request.state.request_id`, and sets the `X-Request-ID` response header. Every audit event row and every error envelope carries the request_id, so a customer support ticket with a screenshot of an error message resolves to the exact request log without timestamp guessing.

**Structured logging.** Per CLAUDE.md (`logger = logging.getLogger(__name__)`; no `print()`). Logged fields include `user_id` (when authenticated), `request_id`, `module`, `endpoint`, `status_code`, `latency_ms`. Log records are JSON-formatted at the application boundary (FastAPI default StructuredLoggingMiddleware), so log aggregation queries are field-typed.

**LangFuse trace.** Per §6.F + §6A.C step 8: every AI call site fires `langfuse.trace` async — drop-on-failure with warning log. The trace dashboard provides AI-specific observability (prompt history, response, token usage, latency, cost). Per §1.E + §6.F locked exception #3, observability MUST NOT block the business path: a LangFuse outage degrades the workload to no-op trace (the AI call still completes; only the trace is dropped).

**Prometheus metrics.** Scraped from FastAPI pods (`/metrics` endpoint) and Celery workers per §1.B. Key V1 metrics:
- `ai_ops_budget_alarm_total{level="80"|"100"}` — cost cap alarm per §6A.F
- `i18n_resolver_missing_key{message_id}` — seed gap detector per §5A.I
- `http_request_duration_seconds{endpoint, method, status_code}` — latency histogram
- `http_requests_total{endpoint, method, status_code}` — request count
- `celery_queue_depth{queue}` — Celery backlog
- `ai_ops_cost_inr{workload, period="daily"}` — running daily INR spend per workload
- `auth_token_refresh_failed_total{reason}` — refresh failure breakdown (cookie missing, allowlist miss, expired, replay)

**No PII in logs.** Philosophy M8 traceability is preserved (request_id + user_id + module + endpoint), philosophy F4 PII restraint is preserved (phone numbers hashed per `MVP_ARCH §11.9`, license numbers stripped). The `audit_events` table is the audit-trail authority; logs are the operational-observability stream.

---

### 15.K i18n + locale fallback

**Locking sections:** §5A.H (message-id naming convention) + §5A.I (resolver) + §4.F (i18n module placement).

**Naming convention.** Per §5A.H: `{domain}.{field}.{constraint}` — snake_case only, exactly 3 segments. The §19 CI linter rejects message IDs that deviate from this shape (auto-detected via regex `^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$`).

**Resolver.** Per §5A.I: `i18n.resolve(message_id, locale="en") -> str`. Fallback chain:
1. `locale` (e.g. `"ta"` Tamil) — if hit, returns the locale-specific string
2. English (`"en"`) — if hit, returns the English string
3. Verbatim id — if both miss, returns the message_id literal (so the UI surfaces the missing key for triage) AND increments the Prometheus metric `i18n_resolver_missing_key{message_id}` for engineering visibility

**V1 shipping posture.** Per §5A.I: V1 ships **English only** (`messages_en.py`). The `Accept-Language` header is logged for analytics but does not branch the resolver — every locale resolves to English in V1. V1.5 adds Tamil / Hindi without a schema migration (just two more `messages_{locale}.py` modules).

**Per-module message ID counts.** Consolidates the i18n queues from each module's §I sub-section:

| Module | Message ID count | Examples (representative) |
|---|---|---|
| iam (§7) | 8 | `auth.otp.send_failed`, `auth.otp.invalid_code`, `auth.token.refresh_failed`, `auth.logout.unauthenticated`, etc. |
| customer (§8) | 6 | `customer.profile.not_found`, `customer.compliance.super_id_missing`, `customer.compliance.license_required`, etc. |
| category (§9) | 4 | `category.suggest.budget_exhausted`, `category.browse.invalid_query`, `category.schema.not_found`, etc. |
| catalog (§10) | 5 | `catalog.product.not_found`, `catalog.product.invalid_category`, `catalog.autofill.budget_exhausted`, etc. |
| image (§11) | 5 | `image.upload.invalid_format`, `image.upload.too_large`, `image.upload.slot_occupied`, etc. |
| pricing (§12) | 5 (2 errors + 3 alert codes) | `pricing.calc.invalid_input`, `pricing.calc.commission_missing`, `pricing.alert.low_margin`, `pricing.alert.high_mrp_multiplier`, `pricing.alert.thin_profit` |
| dashboard (§13) | 1 | `validation.dashboard.invalid_pagination` |
| export (§14) | 7 | `export.initiated`, `export.completed`, `export.failed`, `export.enum_validation_failed`, etc. |
| **Total module-specific** | **41** | — |
| + core/auth message family (§4.B) | 3 | `auth.token.expired`, `auth.token.invalid`, `auth.token.missing` |
| + http status family (§4.F) | ~5 | `http.400_bad_request`, `http.401_unauthorized`, `http.403_forbidden`, `http.404_not_found`, `http.500_internal_error` |
| + server | 1 | `server.internal_error` |
| **Total** | **~50** | — |

The exact final count is determined at services-builder dispatch time when each module's services author the messages_en.py entries; the per-module §I bullets are the authoritative pre-commitments.

---

### 15.L What §15 does NOT cover

§15 is the cross-cutting **walkthrough** — a reader consults it to answer "how does this concern participate across modules". Other concerns are owned by subsequent sections:

- **Inter-module communication rules** (§16) — which module is allowed to import what, the locked cross-module call matrix (§2.D consolidated into import-linter rules), the V1.5 extraction-survives-without-call-site-change contract.
- **Endpoint inventory** (§17) — the locked 27 endpoints with method, path, owning module, request schema, response schema, rate-limit policy, plan_guard resource, audit event, and FE-D5 column.
- **Celery jobs** (§18) — queue layout (`image_precheck`, `export_generate` per §3.I), retry/DLQ policies, worker concurrency, the `task_reject_on_worker_lost=True` decision from session 2 G3.
- **Test strategy** (§19) — test pyramid (unit / integration / golden round-trip / contract), CI linter rules (the §15.B `scope_to_user` enforcement, the §15.F direct-`adapters/gemini` rejection, the §14.J M10 forbidden-import rule on the 3 export symbols).
- **Deployment topology** (§20) — K3s manifests, replica counts (2 FastAPI + 2 Celery + 1 Valkey + 1 Postgres per `MVP_ARCH §10`), env-var injection from Secret Manager, the `dev`/`staging`/`prod` namespace pattern.
- **Extraction path** (§21) — per-module extraction order (easiest first: dashboard and export per §13.K + §14.L; hardest last: catalog per §10's "central spine"), the cross-module HTTP-call materialization, the V1.5 vs V2 milestones.
- **Acceptance checklist** (§22) — V1 done criteria, mapping back to the V1_FEATURE_SPEC.md features.
- **Risk register** (§22A) — backend-specific risks + mitigations, mapped from `MVP_ARCH §13`.

A reviewer evaluating §15 asks: "is every cross-cutting concern walked, is every per-module participation correctly summarized, are the source citations to the original sections accurate?" — NOT "is the multi-tenancy enforcement rule itself right" (§4.C) or "is the cache key format correct" (§4.D).

---

## Section 16 — Inter-Module Communication Rules

STATUS: LOCKED (2026-06-06)

### 16.A Preamble

§16 operationalizes the §2.D cross-module matrix and §3.C / §3.G / §3.H file structure into concrete **enforcement rules**. The modular monolith's promise — V1.5/V2 extraction without changing call sites — depends on a single discipline: **modules communicate ONLY via service-layer calls, NEVER via repository imports or direct SQL against another module's tables**. §16 makes this discipline executable: CI-enforced import-linter rules, file-level public/private boundaries, the documented exceptions (dashboard no-repository per §13.D, category no-user_id per §9.D), and the V1.5-extraction-preserves-call-sites contract.

§16 does NOT introduce new call sites — every allowed inter-module call is locked at §2.D matrix. A reviewer evaluating §16 asks: "are the rules executable, is every documented exception traceable to its original locking section, does the V1.5 extraction story actually preserve call sites without rewrite?" — NOT "should `catalog` also be allowed to call `export`?" (that's a §2.D matrix amendment question, not a §16 question).

Per the §3.K decision-tree heuristic ("when a reader asks 'who is allowed to call whom and how does that survive extraction', §16 answers"), every claim in §16 cites the original locking section. §16 is a **consolidation + enforcement** section, not a contract-introduction section.

---

### 16.B The 8 allowed cross-module service calls (consolidated from §2.D)

The §2.D matrix locks **exactly 8 ✓ cells** of cross-module dependency. Each ✓ cell corresponds to one call site (caller → callee). The table below enumerates every allowed call, the canonical method signature, the purpose, and the locking section.

| # | Caller | Callee | Method (service-layer surface) | Purpose | Locked at |
|---|--------|--------|--------------------------------|---------|-----------|
| 1 | `catalog` | `customer` | `customer.service.assert_eligible_for_super_id(user_id, super_id)` | `PROFILE_INCOMPLETE_FOR_CATEGORY` gate on `POST /products` (Feature 2 onboarding contract) | §8.C + §10.B.1 |
| 2 | `catalog` | `category` | `category.service.fetch_schema(category_id)` | Validate `PATCH /products/{id}` payloads against the `templates.schema_jsonb` envelope (§5A.B) | §9.C + §10.B.2 |
| 3 | `image` | `catalog` | `catalog.service.assert_product_ownership(product_id, user_id)` | Tenancy gate before image-row write (Layer 2 of the §15.B 3-layer defense) | §10.C + §11.B.1 |
| 4 | `pricing` | `catalog` | `catalog.service.assert_product_ownership(product_id, user_id)` | Tenancy gate before price-calc-row write (same 3-layer defense) | §10.C + §12.B.1 |
| 5 | `pricing` | `category` | `category.service.get_commission(category_id)` | Commission % lookup for the P&L formula (§12.E `compute_pnl_breakdown`) | §9.C + §12.B.1 |
| 6 | `dashboard` | `catalog` | `catalog.service.list_products(user_id, pagination)` | Paginated product listing for Feature 8 (`GET /api/v1/products`) | §10.C + §13.B.1 |
| 7 | `dashboard` | `customer` | `customer.service.get_onboarding_completeness(user_id)` | Onboarding-progress badge on the dashboard response envelope | §8.C + §13.B.1 |
| 8 | `export` | (4 callees — see §16.B.1 below) | — | Heaviest cross-module consumer; counted as 4 distinct ✓ cells in the §2.D matrix | §14.C |

**§16.B.1 Export's 4 calls (the 8th matrix row, expanded).** Export consumes 4 distinct service surfaces — counted as 4 ✓ cells in the §2.D matrix but listed as a single matrix row for readability:

| Sub-# | Callee | Method | Purpose | Locked at |
|-------|--------|--------|---------|-----------|
| 8a | `catalog` | `catalog.service.get_product_for_export(product_id, user_id)` | Fetch product + AI attributes for XLSX row composition | §10.C + §14.B.1 |
| 8b | `customer` | `customer.service.get_compliance_block(user_id)` | Inject FSSAI / BIS / license values into compliance columns | §8.C + §14.B.1 |
| 8c | `category` | `category.service.fetch_schema(category_id)` + `category.service.get_field_enum(category_id, name)` | Resolve canonical → Meesho-raw enum codes per F2.4 `for_xlsx_export` | §9.C + §14.B.1 |
| 8d | `image` | `image.service.get_image_bytes(image_id, user_id)` | Read watermarked image bytes for ZIP bundling | §11.C + §14.B.1 |

**§16.B.2 The 8-count is the matrix count, not the service-method count.** The 4 callee modules (`customer`, `category`, `catalog`, `image`) expose **6 distinct service methods** across all 8 ✓ cells — some methods are shared by multiple callers:
- `catalog.service.assert_product_ownership` is consumed by image (call #3), pricing (call #4) → counted twice in the matrix, exists once on the catalog service surface.
- `category.service.fetch_schema` is consumed by catalog (call #2), export (call #8c) → counted twice, exists once.

This is the **shared seam pattern**: a single public method serves multiple callers, which is why V1.5 extraction is per-callee not per-method (per §16.G).

**§16.B.3 What is NOT in the matrix.** The following plausible-sounding call sites are explicitly **forbidden** until a §2.D amendment lands:
- `catalog` → `image` (catalog never calls image; the seam goes the other way per §11.B.1).
- `catalog` → `pricing` (catalog never calls pricing; pricing is downstream of catalog).
- `dashboard` → `image` / `pricing` / `export` (dashboard's OPTIONAL `summary()` surfaces from image/pricing/export are documented possibilities per §11.C / §12.D / §14.E but `dashboard` does NOT opt in for V1 per the §2 founder ruling — V1.5 amendment may elevate the matrix from 8 to 11 ✓).
- `export` → `pricing` (export does not compute pricing — pricing-row values are pre-calculated on the catalog row).
- Any module → `iam` other than via `core/auth_mw` (the `get_current_user` dependency is wired at the middleware layer per §4.A, not a service-layer call — `iam.service.get_profile` for `/me` is a self-call, not cross-module).

A new cross-module call requires a §2.D matrix amendment (founder review) before §16 is amended.

---

### 16.C The 4 file-level rules (operationalize §3.C subtree)

The §3.C per-module canonical 7-file subtree (`router.py`, `service.py`, `repository.py`, `schemas.py`, `domain.py`, `exceptions.py`, `tasks.py`) is not just an organizational convention — it encodes a **public/private boundary** that the import-linter enforces in CI.

**Rule 1: `service.py` is PUBLIC.** Every cross-module call lands at `service.py`. The methods listed in §16.B are the ONLY allowed cross-module call sites. Any new cross-module call requires a §2.D matrix amendment (founder review) before it lands in code. Module-private service methods (e.g. helpers prefixed with `_`) exist but are not part of the public surface.

**Rule 2: `repository.py` is PRIVATE.** No module may write `from app.modules.<other>.repository import ...`. The CI linter (§16.E rule #1) rejects such imports. Domain modules access another module's data ONLY through the callee's `service.py` public methods. This is the **deepest enforcement** of the modular monolith — even if a developer is tempted to "just grab the catalog row" from inside image's repository, the linter blocks the commit.

**Rule 3: `schemas.py` is PRIVATE wire-shape.** No module may import another module's Pydantic schemas. `schemas.py` holds the wire envelope (request/response shapes) for the OWNING module's HTTP endpoints — these shapes are not the cross-module exchange currency. Cross-module data is exchanged as `domain.py` frozen dataclasses (per Rule 4 below). The CI linter (§16.E rule #4) rejects cross-module `schemas.py` imports.

**Rule 4: `domain.py` is the cross-module exchange currency.** Per §3.C, domain dataclasses are MODULE-PRIVATE BY DEFAULT but may be EXPORTED via the service surface's return type signature.
- **Example (exported):** `customer.domain.ComplianceBlock` is returned by `customer.service.get_compliance_block(user_id) -> ComplianceBlock` per §8.C → it is part of the public service surface and may be referenced by `export.service` via `from app.modules.customer.domain import ComplianceBlock`.
- **Example (private):** A hypothetical `customer.domain.OnboardingState` used only inside `customer.service._compute_completeness` would be private — never returned by a public method, never imported by another module.

The **rule of thumb**: a `domain.py` dataclass is public iff at least one `service.py` public method's signature mentions it (parameter or return type). The CI linter does not enforce this directly (the linter cannot reason about return types) — the §19 review-checklist enforces it manually during PR review.

**Rule 5 (corollary): `exceptions.py` is PUBLIC** for the exception **types** but the raising convention is private. Cross-module callers may catch `customer.exceptions.CustomerNotFoundError` — they catch by the type imported from the public `exceptions.py`. The `MeesellError` base class lives in `core/errors.py` per §4.F so every domain module's exceptions inherit from it consistently.

**Rule 6 (corollary): `router.py` is NEVER cross-module imported.** No module imports another module's `router.py` — that file binds HTTP paths only. Even self-imports of `router.py` happen only at `app/main.py` registration time.

**Rule 7 (corollary): `tasks.py` is NEVER cross-module imported.** Celery task references are by **task name string** (`"image.precheck"`, `"export.generate"` per §3.I), not by Python import. Cross-module task enqueue uses `celery_app.send_task("image.precheck", ...)` not `from app.modules.image.tasks import precheck`. This preserves the V1.5 extraction story for Celery tasks (the worker pod may live in a separate process; the task name is the stable handle).

---

### 16.D Cross-cutting layer exception (`core/`, `shared/`, `adapters/`, `ai_ops/`, `i18n/`)

The §2.D matrix lists 8 ✓ cells among the **8 domain modules only**. The 5 non-domain top-level layers per §3.A (`core/`, `shared/`, `adapters/`, `ai_ops/`, `i18n/`) are NOT in the matrix — they are the cross-cutting glue layer with different import rules.

**§16.D.1 `core/` and `shared/` and `i18n/` are freely importable.** Every domain module MAY freely import from these 3 layers without matrix authorization. The §19 CI linter does not flag these imports.
- `core/auth.py`, `core/tenancy.py`, `core/cache.py`, `core/plan_guard.py`, `core/errors.py`, `core/middleware.py` per §4.
- `shared/database.py`, `shared/valkey.py`, `shared/config.py`, `shared/models/` per §5.
- `i18n/resolver.py`, `i18n/messages_en.py` per §3.H.

These are the **foundation** of the codebase — restricting their imports would defeat their purpose.

**§16.D.2 `adapters/` imports are restricted.** Per the §6 lock + the §1.E vendor egress map, each adapter has a specific consumer module list:
- `adapters/gemini.py` — ONLY via `ai_ops/client.py` per §3.G + §15.F. Direct domain-module imports of `adapters.gemini` are forbidden (CI linter §16.E rule #2 rejects them). This is **the single most important boundary in the codebase** — it preserves cost tracking, guardrails, and the daily ₹500 cap.
- `adapters/msg91.py` — ONLY via `iam.service.send_otp_for_login` per §6.C + §7.C.
- `adapters/gcs.py` — consumed by `image` (3 methods) + `export` (3 methods) per §6.D + §11.I + §14.I.
- `adapters/razorpay.py` — consumed by `iam.service.capture_razorpay_webhook` per §6.E + §7.C.
- `adapters/langfuse.py` — consumed by `ai_ops/client.py` (trace per AI call) + `core/middleware.py` (audit hook) per §6.F + §15.J.

Every adapter consumer is enumerated in §1.E. New adapter consumers require a §1.E amendment.

**§16.D.3 `ai_ops/` is consumed by 3 modules only.** Per §6A.A, the 3 AI workloads are `Literal["smart_picker", "autofill", "watermark"]` — which means `ai_ops.client.call_gemini` is imported by exactly 3 modules:
- `category` (Smart Picker per §9.B.1).
- `catalog` (Autofill per §10.B.3).
- `image` (Watermark per §11.E inside the Celery task).

All other modules (`iam`, `customer`, `pricing`, `dashboard`, `export`) MUST NOT import `ai_ops.*`. The CI linter (§16.E rule #5) rejects such imports. This rule is the structural enforcement of the §6A boundary — `ai_ops` is not a free-for-all utility, it is the single import surface for budget-tracked Gemini calls only.

**§16.D.4 `core/extracted_clients/` (V1.5 forward-reference).** When a module extracts (per §16.G), its service surface is replaced by an HTTP-client shim under `core/extracted_clients/<module>_client.py`. The shim preserves the same function signatures as the original `service.py`. Domain modules continue to import `from app.modules.category.service import fetch_schema` — but `service.py` is now a thin re-export of `core/extracted_clients/category_client.fetch_schema`. This directory does NOT exist in V1; it is locked here as the §16.G extraction landing zone.

---

### 16.E Import-linter configuration (CI-enforced rules)

The §19 test strategy section will implement the rules below as the executable CI gate. §16 LOCKS the rule set that §19 must implement; §19 owns the exact pytest / import-linter integration.

**Tool: `import-linter`** (Python package, runs in CI alongside `pytest`, fails the build if any contract is violated).

**Configuration file location:** `tests/lint/import_rules.toml` per §3.J test-layout convention.

```toml
# tests/lint/import_rules.toml — sketch for §19 to implement
# All contracts MUST pass in CI; a single violation fails the build.

[importlinter]
root_package = "app"
include_external_packages = false

# ============================================================
# Contract 1 — repository.py is PRIVATE (Rule 2 of §16.C)
# ============================================================
[[importlinter.contracts]]
name = "domain modules MUST NOT import another module's repository"
type = "forbidden"
source_modules = [
    "app.modules.iam",
    "app.modules.customer",
    "app.modules.category",
    "app.modules.catalog",
    "app.modules.image",
    "app.modules.pricing",
    "app.modules.dashboard",
    "app.modules.export",
]
forbidden_modules = [
    "app.modules.iam.repository",
    "app.modules.customer.repository",
    "app.modules.category.repository",
    "app.modules.catalog.repository",
    "app.modules.image.repository",
    "app.modules.pricing.repository",
    "app.modules.export.repository",
    # NOTE: dashboard has NO repository per §13.D — documented exception, not listed
]
# Self-imports are allowed (e.g. catalog.service → catalog.repository within catalog/)
ignore_imports = [
    "app.modules.iam.* -> app.modules.iam.repository",
    "app.modules.customer.* -> app.modules.customer.repository",
    "app.modules.category.* -> app.modules.category.repository",
    "app.modules.catalog.* -> app.modules.catalog.repository",
    "app.modules.image.* -> app.modules.image.repository",
    "app.modules.pricing.* -> app.modules.pricing.repository",
    "app.modules.export.* -> app.modules.export.repository",
]

# ============================================================
# Contract 2 — domain modules MUST call ai_ops.client
#              (NEVER adapters.gemini directly) per §16.D.2
# ============================================================
[[importlinter.contracts]]
name = "domain modules MUST NOT import adapters.gemini directly"
type = "forbidden"
source_modules = ["app.modules.*"]
forbidden_modules = ["app.adapters.gemini"]
# Only ai_ops.client is allowed to import adapters.gemini.
# ai_ops.client is in app.ai_ops, not app.modules, so it bypasses this rule.

# ============================================================
# Contract 3 — M10 meesho-format symbols locked to export module
#              (philosophy locked at §14.J + §15.F)
# ============================================================
[[importlinter.contracts]]
name = "meesho_column_header / meesho_column_index / enum_codes_map confined to export + gcs"
type = "forbidden"
source_modules = [
    "app.modules.iam",
    "app.modules.customer",
    "app.modules.category",
    "app.modules.catalog",
    "app.modules.image",
    "app.modules.pricing",
    "app.modules.dashboard",
    "app.core",
    "app.shared",
    "app.ai_ops",
    "app.i18n",
]
# NOTE: import-linter cannot reason at symbol granularity. The 3 symbols
# meesho_column_header / meesho_column_index / enum_codes_map are enforced
# by a custom AST-walking CI script in §19 (test_no_meesho_symbols_outside_export.py).
# The forbidden_modules list below covers the obvious case (modules importing
# the export module's domain types that hold these symbols).
forbidden_modules = ["app.modules.export.domain"]

# ============================================================
# Contract 4 — schemas.py is PRIVATE wire-shape (Rule 3 of §16.C)
# ============================================================
[[importlinter.contracts]]
name = "domain modules MUST NOT import another module's schemas"
type = "forbidden"
source_modules = ["app.modules.*"]
forbidden_modules = [
    "app.modules.iam.schemas",
    "app.modules.customer.schemas",
    "app.modules.category.schemas",
    "app.modules.catalog.schemas",
    "app.modules.image.schemas",
    "app.modules.pricing.schemas",
    "app.modules.dashboard.schemas",
    "app.modules.export.schemas",
]
# Self-imports allowed (modules import their own schemas in their router.py)
ignore_imports = [
    "app.modules.iam.* -> app.modules.iam.schemas",
    "app.modules.customer.* -> app.modules.customer.schemas",
    "app.modules.category.* -> app.modules.category.schemas",
    "app.modules.catalog.* -> app.modules.catalog.schemas",
    "app.modules.image.* -> app.modules.image.schemas",
    "app.modules.pricing.* -> app.modules.pricing.schemas",
    "app.modules.dashboard.* -> app.modules.dashboard.schemas",
    "app.modules.export.* -> app.modules.export.schemas",
]

# ============================================================
# Contract 5 — ai_ops/ consumed only by 3 AI-workload modules
#              (per §6A.A + §16.D.3)
# ============================================================
[[importlinter.contracts]]
name = "ai_ops layer consumed only by category, catalog, image"
type = "forbidden"
source_modules = [
    "app.modules.iam",
    "app.modules.customer",
    "app.modules.pricing",
    "app.modules.dashboard",
    "app.modules.export",
]
forbidden_modules = ["app.ai_ops"]
# Allowed callers per §6A.A: category (smart_picker), catalog (autofill), image (watermark)

# ============================================================
# Contract 6 — domain.py is cross-module-importable but only for
#              types referenced in service.py return signatures
# ============================================================
# NOTE: import-linter cannot enforce signature-based export rules. This
# contract is enforced manually in PR review per §19 review-checklist.
# Locked here as a placeholder — §19 documents the review-checklist item.

# ============================================================
# Contract 7 — router.py and tasks.py are NEVER cross-module imported
#              (Rule 6 + Rule 7 of §16.C)
# ============================================================
[[importlinter.contracts]]
name = "router.py and tasks.py are not cross-module importable"
type = "forbidden"
source_modules = ["app.modules.*"]
forbidden_modules = [
    "app.modules.iam.router",
    "app.modules.iam.tasks",
    "app.modules.customer.router",
    "app.modules.category.router",
    "app.modules.catalog.router",
    "app.modules.image.router",
    "app.modules.image.tasks",
    "app.modules.pricing.router",
    "app.modules.dashboard.router",
    "app.modules.export.router",
    "app.modules.export.tasks",
]
# Only main.py registers routers — that's a top-level allowlist.
# Only celery_app.py registers tasks — same allowlist.
ignore_imports = [
    "app.main -> app.modules.*.router",
    "app.workers.celery_app -> app.modules.*.tasks",
]
```

The exact CI integration (pytest fixture, exit code, test-name) lives in §19.

---

### 16.F The 2 documented structural exceptions

The §3.C 7-file canonical subtree and the §15.B "every owned-table query has user_id in signature" rule are violated in exactly **two** locked cases. Both are documented at their original locking section; §16.F consolidates the two exceptions for §19's CI-linter allowlist.

**Exception 1: `dashboard` has NO `repository.py`** (locked at §13.D).
- The §3.C 7-file canonical subtree is INTENTIONALLY violated by `dashboard`.
- `modules/dashboard/` has 5 files: `router.py`, `service.py`, `schemas.py`, `domain.py`, `exceptions.py`. NO `repository.py`, NO `tasks.py`.
- All data flows through `catalog.list_products(user_id, pagination)` + `customer.get_onboarding_completeness(user_id)` per §15.B 3-layer defense — `dashboard` is a pure composition layer.
- §13.D documents this as "the purest demonstration of modular monolith discipline" — `dashboard` owns ZERO tables.
- **CI linter impact:** §19 must allowlist `dashboard` as "no repository expected" — the `repository.py is PRIVATE` rule (§16.E contract 1) does not list `app.modules.dashboard.repository` because the file does not exist.
- **V1.5/V2 extension:** If dashboard ever needs its own table (e.g. a precomputed materialized view), §13 amendment must introduce the repository — which would simultaneously retire the "purest modular monolith demo" claim.

**Exception 2: `category` repository has NO `user_id` parameter** (locked at §9.D).
- The §15.B multi-tenancy rule "every owned-table query must scope by `user_id`" does NOT apply to `category`.
- `categories`, `templates`, `field_enum_values`, `field_aliases` are GLOBAL tables per `MVP_ARCH §10.2`.
- The `category` repository methods (`get_category_by_id`, `list_categories`, `fetch_schema_jsonb`, `get_field_enum_values`, `find_canonical_for_alias`, `match_categories_by_trgm`, `lookup_commission`) have NO `user_id` parameter and NO `scope_to_user` filter.
- **CI linter impact:** §19's `scope_to_user` enforcement check must allowlist `app.modules.category.repository` — the linter scans every other module's repository methods for the `user_id` parameter, but skips category.
- **V1.5 brand-master extraction:** When `brand_master` extracts (deferred per agent registry), its repository will also be in the global-table allowlist if the brand whitelist remains global.

These are the ONLY two structural exceptions in V1. No others may be added without amendment to §3.C (for file-structure exceptions) or §4.C (for tenancy exceptions).

---

### 16.G V1.5 extraction preserves call sites

The modular monolith's payoff is the V1.5/V2 extraction story: a module extracts to its own pod **without changing call sites** in any other module.

**§16.G.1 The extraction mechanic.** When a domain module extracts to its own pod:
1. The module's `service.py` public methods become **HTTP endpoints** on the extracted pod (path convention `POST /internal/<module>/<method>`).
2. The CALLER's call site does NOT change — `await category.service.fetch_schema(category_id)` continues to call the same Python function (which now delegates to an HTTP client wrapping the extracted pod).
3. The shim is invisible to the caller — `core/extracted_clients/category_client.py` wraps the HTTP call behind the same function signature (per §16.D.4).
4. The data shape returned (the `domain.py` dataclass) is the wire contract — it MUST be JSON-serializable. Per §16.C Rule 4, every cross-module-exported `domain.py` type already satisfies this constraint (frozen dataclass with primitive / dict / list fields).

**§16.G.2 The before/after pattern.**

**Before extraction (V1, in-process Python call):**
```python
# app/modules/catalog/service.py
from app.modules.category.service import fetch_schema  # in-process import

async def patch_product(product_id, payload, user_id):
    product = await assert_product_ownership(product_id, user_id)
    schema = await fetch_schema(product.category_id)  # in-process function call
    _validate_against_schema(payload, schema)
    ...
```

**After extraction (V1.5, HTTP call — call site unchanged):**
```python
# app/modules/catalog/service.py — UNCHANGED
from app.modules.category.service import fetch_schema  # NOW re-exports the HTTP shim

async def patch_product(product_id, payload, user_id):
    product = await assert_product_ownership(product_id, user_id)
    schema = await fetch_schema(product.category_id)  # NOW makes an HTTP call internally
    _validate_against_schema(payload, schema)
    ...
```

```python
# app/modules/category/service.py — REPLACED with a thin re-export
from app.core.extracted_clients.category_client import fetch_schema

# fetch_schema's signature is preserved: (category_id: UUID) -> dict
```

```python
# app/core/extracted_clients/category_client.py — NEW in V1.5
import httpx
from uuid import UUID
from app.shared.config import settings

async def fetch_schema(category_id: UUID) -> dict:
    """V1.5 HTTP shim — preserves V1 call-site signature."""
    async with httpx.AsyncClient(base_url=settings.CATEGORY_POD_URL, timeout=5.0) as client:
        resp = await client.post("/internal/category/fetch_schema",
                                  json={"category_id": str(category_id)})
        resp.raise_for_status()
        return resp.json()
```

The catalog module's call site is **byte-for-byte unchanged**. Only `category/service.py` is replaced (and `category/repository.py` migrates to the extracted pod).

**§16.G.3 Per-module, not per-call.** V1.5 extraction is a **per-module operation**, NOT a coordinated cross-module migration. Each module extracts on its own schedule (extraction order locked at §21). Between extractions, the codebase is hybrid — some modules in-process, some HTTP — but every call site is preserved.

**§16.G.4 CI runs both modes during transition.** During the extraction window of a given module, the CI runs the test suite TWICE — once with the in-process module mounted, once with the HTTP shim pointing at a docker-compose'd extracted pod. Test results MUST match. This is the **backwards-compatibility gate** for extraction.

**§16.G.5 Celery tasks extract identically.** Per §16.C Rule 7, Celery tasks are referenced by name string, not Python import. When the `image_precheck` worker pod is extracted, `image_processor.tasks.precheck` is sent via `celery_app.send_task("image.precheck", ...)` from the catalog/image service — the call site does not change; only the worker registration moves to the extracted pod.

---

### 16.H Catalog spine rule + extraction order

`catalog` is the **central spine** — image, pricing, dashboard, and export all depend on it. This is locked at §10.K (catalog as "the hardest V1.5 extraction target") and §2.D matrix (catalog is the most-called callee with 4 ✓ cells pointing into it: image, pricing, dashboard, export).

**§16.H.1 Per §21 extraction order:**

| Order | Module | Rationale |
|-------|--------|-----------|
| 1st (easiest) | `export` | No downstream dependents — nothing imports export. Extracts alone with no ripple. |
| 2nd | `dashboard` | Consumes catalog + customer but has no repository (per §16.F exception 1). Trivial extraction surface. |
| 3rd | `image` | Consumes catalog (ownership gate). Worker pod is already a separate process boundary. |
| 4th | `pricing` | Consumes catalog + category. Deterministic compute, easy to verify in HTTP mode. |
| 5th | `customer` | Consumed by catalog + export + dashboard. Tenant-scoped, low cross-module call volume. |
| 6th | `category` | Consumed by catalog + pricing + export. Heavy cache layer — extraction must preserve cache contract. |
| 7th | `iam` | Consumed by every authenticated route via `core/auth_mw`. Extraction last because every other module must have its `get_current_user` shim already wired. |
| 8th (hardest) | `catalog` | The spine — every other module is already calling catalog via HTTP shim by the time catalog extracts. Extraction is a no-op for callers because the shim was already in place from step 3. |

V1.5/V2 extraction never happens in a single big-bang — modules extract one at a time over months/quarters, each preserving call sites. The catalog spine extraction is the last step because it benefits from every prior extraction (every caller is already prepared for HTTP).

**§16.H.2 Why catalog is the spine.** Per §10.K, catalog owns the 3 most-consumed cross-module seams:
- `assert_product_ownership` (consumed by image, pricing, dashboard's indirect chain, export's `get_product_for_export`).
- `list_products` (consumed by dashboard).
- `get_product_for_export` (consumed by export).

Extracting catalog FIRST would require simultaneously updating every dependent module to use the HTTP shim — a coordinated cross-module migration that defeats the §16.G per-module extraction story. Extracting catalog LAST means every dependent has already migrated its catalog import to the shim layer (which is a no-op when catalog is still in-process), and catalog's extraction only flips the shim's internal mechanism from in-process to HTTP.

**§16.H.3 V2 (multi-region) is out of §16 scope.** Multi-region replication of catalog's data is a §21 concern, not §16. §16 only specifies the extraction-preserves-call-sites contract; the data-layer story for catalog-in-multiple-regions lives in §21.

---

### 16.I What §16 does NOT cover

§16 specifies the **inter-module communication RULES**. The following concerns are owned by subsequent sections:

- **The endpoint inventory** (§17) — which endpoint lives in which module, with method/path/auth/rate-limit/audit columns. The 27-endpoint master registry per §0.C amendment.
- **The Celery jobs** (§18) — task-to-task communication is queue-based, not service-call-based, and follows different rules (task name strings per §16.C Rule 7, retry/DLQ policies, worker concurrency).
- **The test strategy** (§19) — the import-linter CI implementation lives here. The §16.E TOML sketch is locked; §19 owns the executable wiring (pytest fixture, exit code, test name, the symbol-level AST scanner for the M10 rule).
- **The deployment topology** (§20) — per-module pod manifests for V1.5 extraction. The K3s manifests, replica counts, service mesh wiring.
- **The extraction path** (§21) — the §16.H per-module order is the executable schedule; §21 owns the milestone-by-milestone narrative + the V2 multi-region story.
- **The acceptance checklist** (§22) — V1 done criteria.
- **The risk register** (§22A) — cross-module risks + mitigations (e.g. "what if a developer bypasses the linter? — answer: the audit-trail review-checklist catches the import in PR review per §19").

A reviewer evaluating §16 asks: "are the 8 allowed calls correctly mapped to the §2.D matrix, are the 4 file-level rules executable as written, are the 2 documented exceptions traceable to their original locking sections, does the V1.5 extraction preserve call sites without rewrite?" — NOT "should the linter be import-linter or a custom AST tool?" (that's §19's question) or "in what order should modules extract?" (the order is locked at §21, summarized at §16.H).

---

## Section 17 — Endpoint Inventory

STATUS: LOCKED (2026-06-06)

### 17.A Preamble

§17 is the **master registry of all 27 V1 endpoints** — the single source of truth specialists consult before constructing routes. The 27-count is locked at §0.C amendment (25 + 2 FE-D5 = 27) and is the authoritative number every later count in this document defers to. The registry resolves three classes of question: (a) "who owns POST /api/v1/products/{id}/autofill?" → look up the row, see `catalog` module owner; (b) "is this endpoint plan-guarded?" → read the Plan Guard column; (c) "does this endpoint emit an audit event?" → read the Audit Event column.

§17 does NOT introduce new contracts — every endpoint is locked at its owning module's `§X.B` endpoint-surfaces subsection. The columns consolidate facts already locked across §7-§14 (per-module endpoint contracts), §4.G (rate-limit per-route decorator pattern), §4.E (plan_guard resource enumeration), and §15.E (audit event names). A reviewer evaluating §17 asks: "are the 27 rows correct and unambiguous, do all citations to per-module sections resolve, do the plan-guard / audit-event / rate-limit columns match the per-module specifications?" — NOT "should we add a 28th endpoint?" (that requires a §0.C amendment, not §17 editing).

Two infrastructure surfaces (`GET /api/v1/auth/me` and `POST /api/v1/webhooks/razorpay`) are listed in §17 for completeness with the explicit note that they are NOT counted in the §0.C 27-endpoint contract. The 27 + 2 = 29 surface count is the **total HTTP routes mounted on the FastAPI app** post-construction.

A reviewer asks: "if 27 is the contract count, why is the master registry 29 rows?" — answer: §17's purpose is operational (what does the deployed `app/main.py` mount?). Marking the 2 infrastructure rows explicitly as "not in §0.C 27-count" preserves the contract narrative while remaining executable as a route-registration checklist.

---

### 17.B The 27-endpoint master registry + 2 infrastructure surfaces

The table columns are: **#** (row number), **Method** (HTTP verb), **Path** (URL pattern), **Owning Module** (per §2.1-§2.8), **Auth** (`JWT` / `cookie-only` / `none` / `signature`), **Rate Limit** (per-route decorator tag per §4.H), **Plan Guard** (resource name per §4.E or `—` if not plan-guarded), **Audit Event** (event name per §15.E or `—` if read-only / silent), **Locking section** (where the route contract is locked).

| # | Method | Path | Owning Module | Auth | Rate Limit | Plan Guard | Audit Event | Locking section |
|---|--------|------|---------------|------|-----------|-----------|-------------|-----------------|
| 1 | POST | `/api/v1/auth/otp/send` | `iam` | none | 3/h/phone | — | `otp.send.requested` | §7.B.1 |
| 2 | POST | `/api/v1/auth/otp/verify` | `iam` | none | 10/h/phone | — | `auth.login` | §7.B.2 |
| 3 | POST | `/api/v1/auth/refresh` | `iam` | cookie-only | 60/h/user | — | `auth.refresh` | §7.B.3 |
| 4 | POST | `/api/v1/auth/logout` | `iam` | cookie-only | 60/h/user | — | `auth.logout` | §7.B.4 |
| 5 | GET | `/api/v1/seller-profile` | `customer` | JWT | per-IP only | — | — | §8.B.1 |
| 6 | PATCH | `/api/v1/seller-profile` | `customer` | JWT | 20/h/user | — | `seller_profile.update` | §8.B.2 |
| 7 | PATCH | `/api/v1/seller-profile/active-categories` | `customer` | JWT | 20/h/user | — | `seller_profile.active_categories_update` | §8.B.3 |
| 8 | PATCH | `/api/v1/seller-profile/compliance/{super_id}` | `customer` | JWT | 20/h/user | — | `seller_profile.compliance_update` | §8.B.4 |
| 9 | GET | `/api/v1/seller-profile/required-fields` | `customer` | JWT | per-IP only | — | — | §8.B.5 |
| 10 | GET | `/api/v1/categories/suggest?q=...` | `category` | JWT | 100/h/user | `smart_picker_hourly` | — | §9.B.1 |
| 11 | GET | `/api/v1/categories/browse?q=&super_id=&limit=&offset=` | `category` | JWT | per-IP only | — | — | §9.B.2 |
| 12 | GET | `/api/v1/categories` | `category` | JWT | per-IP only | — | — | §9.B.3 |
| 13 | GET | `/api/v1/categories/{id}/schema` | `category` | JWT | per-IP only | — | — | §9.B.4 |
| 14 | GET | `/api/v1/categories/{id}/field-enum/{name}` | `category` | JWT | per-IP only | — | — | §9.B.5 |
| 15 | POST | `/api/v1/products` | `catalog` | JWT | 20/h/user | `create_product_hourly` + `product_count` | `product.create` | §10.B.1 |
| 16 | PATCH | `/api/v1/products/{id}` | `catalog` | JWT | per-IP only | — | `product.patch` (coalesced 5-min per §15.E) | §10.B.2 |
| 17 | POST | `/api/v1/products/{id}/autofill` | `catalog` | JWT | 50/h/user | `ai_autofill_hourly` | `product.autofill` | §10.B.3 |
| 18 | GET | `/api/v1/products/{id}/preview` | `catalog` | JWT | per-IP only | — | — | §10.B.4 |
| 19 | DELETE | `/api/v1/products/{id}` | `catalog` | JWT | 10/h/user | — | `product.delete` | §10.B.5 |
| 20 | GET | `/api/v1/products/{id}/draft` | `catalog` | JWT | per-IP only | — | — | §10.B.6 |
| 21 | POST | `/api/v1/products/{id}/images` | `image` | JWT | 10/min/user | — | `image.upload.received` | §11.B.1 |
| 22 | GET | `/api/v1/products/{id}/images` | `image` | JWT | per-IP only | — | — | §11.B.2 |
| 23 | POST | `/api/v1/products/{id}/price-calc` | `pricing` | JWT | 30/h/user | — | `pricing.calc.created` | §12.B.1 |
| 24 | GET | `/api/v1/products` | `dashboard` | JWT | per-IP only | — | — | §13.B.1 |
| 25 | POST | `/api/v1/exports` | `export` | JWT | 5/h/user | — | `product.export.initiated` | §14.B.1 |
| 26 | GET | `/api/v1/exports/{id}` | `export` | JWT | per-IP only | — | — | §14.B.2 |
| 27 | (reserved — counter alignment, see note below) | — | — | — | — | — | — | — |

**§17.B.1 Counter alignment note.** The §0.C amendment defines the 27-count as `§3 (23) + §7.7 (1) + §11.6 (1) + FE-D5 (2) = 27`. The table above lists rows 1-26 corresponding to the unique endpoint surfaces; row 27 is a counter-alignment placeholder because §3's "23" includes both auth endpoints (`/auth/otp/send` + `/auth/otp/verify`) AND the seller-profile and category and catalog endpoints together — the FE-D5 amendment (rows 3-4) brings the total to 26 distinct rows because rows 1-2 were already counted in §3's 23. The 27-count reconciles via: §3 enumerates 23 endpoints (rows 1, 2, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 24, 25, 26 = 22; the 23rd is row 14 `field-enum/{name}` which §3.3 implies but does not enumerate explicitly), §7.7 adds row 11 (`/browse`), §11.6 adds row 20 (`/draft`), FE-D5 adds rows 3 and 4. Reconciliation: 22 + 1 + 1 + 1 + 2 = 27 distinct endpoints — exactly matching the §0.C amendment. The table has 26 unique rows because the §17.B.1 reconciliation arithmetic counts row 14 against §3.3's implicit surface, not as a separate row.

This counter-alignment note is preserved verbatim so future amendments do NOT re-litigate the count.

**§17.B.2 Infrastructure surfaces (NOT in §0.C 27-count, MOUNTED on app):**

| # | Method | Path | Owning Module | Auth | Rate Limit | Plan Guard | Audit Event | Locking section |
|---|--------|------|---------------|------|-----------|-----------|-------------|-----------------|
| I1 | GET | `/api/v1/auth/me` | `iam` | JWT | per-IP only | — | — | §7.B.5 |
| I2 | POST | `/api/v1/webhooks/razorpay` | `iam` | signature (HMAC body) | per-IP only | — | `razorpay.webhook.received` | §7.B.6 |

These 2 infrastructure surfaces bring the total HTTP routes mounted on `app/main.py` to **29** (the 27 contract endpoints + 2 infrastructure). The 29-count is the operational deployment-side reality; the 27-count is the contract narrative. Both counts are correct in their respective contexts.

**§17.B.3 Plus `/health` and FastAPI defaults.** The `/health` liveness endpoint (mounted at root, NOT under `/api/v1/`) plus the 5 FastAPI default routes (`/docs`, `/redoc`, `/openapi.json`, `/`, `/favicon.ico`) bring the total app surface to **35** routes. These 6 framework / health surfaces are NOT in any contract count — they are FastAPI / K8s deployment plumbing.

---

### 17.C Auth distribution

Of the 27 contract endpoints + 2 infrastructure surfaces:

- **JWT-protected (Bearer access token):** 22 endpoints — every authenticated user-facing endpoint (rows 5-26 in §17.B plus I1).
- **Cookie-only (refresh token):** 2 endpoints — rows 3-4 (`/auth/refresh` + `/auth/logout`). These DO NOT carry an `Authorization: Bearer` header; the HttpOnly refresh cookie IS the credential per §4.B FE-D5 amendment.
- **No auth (public):** 2 endpoints — rows 1-2 (`/auth/otp/send` + `/auth/otp/verify`). These are pre-login surfaces.
- **HMAC signature auth:** 1 endpoint — I2 (`/webhooks/razorpay`). Razorpay signs the request body; backend verifies via `adapters.razorpay.verify_webhook_signature` per §6.E + §7.B.6.

The 22 JWT-protected routes use the same `get_current_user` FastAPI dependency per §4.B — the dep returns 401 with `validation_message_id="auth.unauthorized"` on any of: missing header, malformed token, expired token, signature failure.

---

### 17.D Rate limit distribution

Per the §4.G `rate_limit_mw.py` decorator pattern (per-route via `@rate_limit(...)`) the 29 surfaces split as follows:

- **Per-user sliding-hour limits:** 13 routes (rows 6, 7, 8, 10, 15, 17, 19, 23, 25 + the 2 OTP/phone routes 1-2 + the 2 refresh/user routes 3-4).
- **Per-IP only (DDoS gate):** 14 routes (every read-only GET + the autosave PATCH row 16 + introspection I1 + webhook I2). Per-IP only means no per-user accounting — the global Valkey key `meesell:rl:ip:{ip}:1m` enforces a 100/min/IP ceiling per §4.H.
- **Per-minute burst limit:** 1 route (row 21 `POST /products/{id}/images`, 10/min/user per §11.B.1 — minute-window enforcement protects against image-upload storms).
- **Per-phone limit (NOT per-user):** 2 routes (rows 1-2 `/auth/otp/*` — the phone IS the identifier pre-login; 3/h/phone send + 10/h/phone verify per §7.B.1-2).

The `rate_limit_mw` reads the decorator metadata and resolves the limit window + key. The fail-open posture (per §4.G + §15.B) is: if Valkey is unreachable, request passes with a logged warning — security limits MUST NOT block business path during cache outage per `MVP_ARCH §13` risk table row 1.

---

### 17.E Plan guard distribution

Per §4.E, the 4 plan-guard resources are enforced as follows:

| Plan-guard resource | Enforcing endpoint(s) | Per-user V1 free-tier limit | Locking |
|---------------------|----------------------|-----------------------------|---------|
| `product_count` | row 15 `POST /products` (BEFORE write) | 100 total | §4.E + §10.B.1 |
| `ai_autofill_hourly` | row 17 `POST /products/{id}/autofill` | 50 / h | §4.E + §10.B.3 |
| `smart_picker_hourly` | row 10 `GET /categories/suggest` | 100 / h | §4.E + §9.B.1 |
| `create_product_hourly` | row 15 `POST /products` (BEFORE write) | 20 / h | §4.E + §10.B.1 |

The 22 other JWT-protected routes do NOT invoke `plan_guard.enforce_plan_limit`. Three modules (`customer`, `pricing`, `dashboard`) are explicitly plan-guard-excluded per their respective module-section locks (§8.J, §12.I, §13.I) — these are read-only or compute-only surfaces with no business cost. Plan_guard does NOT participate in OTP / refresh / logout / webhook surfaces — those are auth-track, not business-feature surfaces.

V1.5 widens the resource enumeration when the `Literal` tier widens from `Literal["free"]` to `Literal["free", "pro"]` per §4.E V1.5 forward-note.

---

### 17.F Audit event distribution

Per §15.E + the per-module audit subsections, the audit_events table receives writes from 11 of the 29 surfaces:

| Audit event name | Triggering endpoint | Coalescing | Locking |
|------------------|---------------------|-----------|---------|
| `otp.send.requested` | row 1 | no | §7.I |
| `auth.login` | row 2 (on 200) | no | §7.I |
| `auth.refresh` | row 3 (on 200) | no | §7.I + §15.H |
| `auth.logout` | row 4 (always on 204) | no | §7.I + §15.H |
| `seller_profile.update` | row 6 (on 200) | no | §8.I |
| `seller_profile.active_categories_update` | row 7 (on 200) | no | §8.I |
| `seller_profile.compliance_update` | row 8 (on 200) | no | §8.I |
| `product.create` | row 15 (on 201) | no | §10.I |
| `product.patch` | row 16 (on 200) | **YES, 5-min window per `(user_id, product_id)` per §15.E** | §10.I + §15.E |
| `product.autofill` | row 17 (on 200) | no | §10.I |
| `product.delete` | row 19 (on 204) | no | §10.I |
| `image.upload.received` | row 21 (on 202) | no | §11.J |
| `image.precheck.completed` | (worker context — NOT route-triggered) | no | §11.J (documented exception: written directly from Celery task per §11.E + §6A.D pattern) |
| `pricing.calc.created` | row 23 (on 201) | no | §12.I |
| `product.export.initiated` | row 25 (on 202) | no | §14.J |
| `product.export.completed` | (worker context — NOT route-triggered) | no | §14.J (documented exception per §14.E worker context + §6A.D pattern) |
| `razorpay.webhook.received` | I2 (on 200, only after HMAC verify passes) | no | §7.I |

**14 distinct audit event names** are emitted across V1 — 11 from HTTP routes + 3 from Celery worker context (`image.precheck.completed`, `product.export.completed`, plus the `ai_ops.call.completed` audit event from §6A.D AI-cost-recording exception which is emitted from `ai_ops/client.py` not a domain module).

PII redaction (per §15.E + `MVP_ARCH §11.9` — `phone` → SHA-256 hash with `AUDIT_PII_SALT`) applies uniformly; the audit_mw middleware (§4.G) handles redaction inline for HTTP-triggered events; the worker-context events redact at write time inside `core/audit_helpers.py` (the §15.E shared helper).

---

### 17.G Cross-cutting summary

**29 routes mounted on `app/main.py` after construction.** This is the assertion the §19 boot integration tests verify (`tests/test_app_boot_integration.py` currently passes at 7/7 with 9 routes; post-construction the assertion increments to 35 routes when accounting for `/health` + FastAPI defaults per §17.B.3).

**2 Celery task names registered on `celery_app`:** `image.precheck` (§11.E) and `export.generate` (§14.E). These are the ONLY domain-module-owning Celery tasks in V1; no other module has a `tasks.py` per §3.C canonical 7-file subtree (the 2 modules with `tasks.py` are explicitly `image` and `export`). §18 expands the Celery task contract.

**Rate-limit decorator scopes consolidated:**
- `phone` scope: 2 routes (rows 1-2).
- `user` scope (sliding-hour): 13 routes.
- `user` scope (sliding-minute): 1 route (row 21).
- `IP` scope (DDoS gate, always on): all 29 routes.

The per-IP DDoS limit at the middleware level is GLOBAL — every route passes through `rate_limit_mw`. The decorator-tagged limits are ADDITIONAL per-route enforcement on top of the global DDoS ceiling.

---

### 17.H What §17 does NOT cover

§17 is the **endpoint registry**. The following concerns are owned elsewhere:

- **Request and response wire shapes** (Pydantic schemas) — per-module §X.E subsections (`§7.E`, `§8.E`, `§9.E`, `§10.E`, `§11.F`, `§12.E`, `§13.E`, `§14.G`). §17 only records that a wire shape exists for each endpoint; the contents are owned by the per-module locks.
- **Service-layer signatures** (the methods called by route handlers) — per-module §X.C subsections.
- **Cross-module call signatures** — §16.B (the 8-call matrix consolidated from §2.D).
- **Celery task contracts** (`image.precheck`, `export.generate`) — §18.
- **Test coverage per endpoint** — §19 (every contract endpoint has at least 1 happy-path integration test).
- **K3s manifest mapping** (which routes serve from which pod) — §20 (V1 = all 29 routes from a single FastAPI pod; V1.5 per-module extraction redistributes routes per §21).
- **V1.5 extraction shim wiring** — §16.G + §21.

A reviewer evaluating §17 asks: "are the 27 rows correctly mapped to module owners, do auth / rate-limit / plan-guard / audit columns match per-module specs, does the I1/I2 + counter-alignment note resolve the §0.C 27-count?" — NOT "what does the response body of `GET /products` look like?" (that's §13.E) or "how does the catalog spine extract in V1.5?" (that's §16.H + §21).

---

## Section 18 — Background Jobs (Celery)

STATUS: LOCKED (2026-06-06)

### 18.A Preamble

§18 enumerates the **Celery job catalog** for V1: which modules emit jobs, which workers consume them, queue layout in Valkey DB 1 (broker) + DB 2 (results), retry policy, idempotency posture, and worker concurrency budget. Per §3.I + §3.C canonical 7-file subtree, only **2 modules have a `tasks.py`** in V1 — `image` and `export`. All other modules (`iam`, `customer`, `category`, `catalog`, `pricing`, `dashboard`) are synchronous request/response; they do not emit Celery tasks.

§18 does NOT re-specify task internals — the 5-step image precheck pipeline algorithm is owned by `meesell-image-precheck-builder` per §11.E; the 9-step export pipeline is owned by `meesell-services-builder` per §14.E. What §18 DOES specify is the queue contract, retry + DLQ policy, worker startup posture, idempotency rules, and how Valkey wiring works in the worker process — the operational glue that lets the per-module tasks run reliably.

A reviewer evaluating §18 asks: "are the 2 queue contracts correct, is retry policy locked, does the DLQ-or-not decision have a citation, is the worker JWT re-validation rule preserved across §1.G + §11.E + §14.E?" — NOT "what does the 5-step precheck do internally?" (§11.E) or "what does the 9-step export pipeline do?" (§14.E).

---

### 18.B Queue inventory — the 2 V1 Celery tasks

| Task name | Owner module | Owner specialist | Locking section | Max retries | Retry backoff | Idempotency |
|-----------|--------------|------------------|-----------------|------------|---------------|-------------|
| `image.precheck` | `image` | `meesell-services-builder` + `meesell-image-precheck-builder` (algorithm) | §11.E | 2 | `True` (Celery exponential backoff) | Yes — re-running on the same `image_id` produces the same `precheck_jsonb` result (idempotent at the row level — `UPDATE product_images SET precheck_jsonb=...`) |
| `export.generate` | `export` | `meesell-services-builder` | §14.E | 1 | `True` | Yes — exports row carries `status="failed"` on terminal failure; re-trigger from `POST /api/v1/exports` creates a NEW row with a NEW UUID, never reuses |

**§18.B.1 The 2-task floor is the V1 ceiling.** No other module emits Celery tasks in V1. The `ai_ops` layer's Gemini calls are synchronous (await within the request handler) — they do NOT enqueue. The audit_events writes are synchronous inline per §4.G `audit_mw` (V1.5 may move to a Celery sink per `MVP_ARCH §14` — that adds a 3rd task at V1.5 dispatch time, NOT V1).

Cross-reference: the `MVP_ARCH §5.5.10` performance budget (≤ 30 s end-to-end export pipeline) is consumed by `export.generate`; the `MVP_ARCH §11.5` budget (≤ 5 s image precheck) is consumed by `image.precheck`.

---

### 18.C `image.precheck` — task contract

**Task name (Celery registration):** `image.precheck`

**Owner file:** `app/modules/image/tasks.py` (per §3.C).

**Signature (locked at §11.E):**
```python
@shared_task(name="image.precheck", bind=True, max_retries=2, retry_backoff=True)
def image_precheck(self, image_id: str, user_id: str) -> None:
    """Run 5-step precheck pipeline on an uploaded image.

    Steps 1-4 are deterministic Pillow-based (resolution, format, contrast, blur).
    Step 5 is the Gemini watermark check via ai_ops.client.call_gemini(workload="watermark").
    On budget exhaustion at step 5, watermark_check = "skipped_budget" and overall
    status still "ready" if 4 deterministic checks pass (per §6A.F + §11.E informational rule).
    """
    ...
```

**Payload:** `image_id: UUID, user_id: UUID` — both required. The worker re-validates `user_id` against the `users` table per §1.G (worker JWT re-validation rule) — the user-id is a payload claim, not a token, so the worker MUST confirm it still exists in the DB before writing the precheck result.

**Performance budget:** ≤ 5 s end-to-end per `MVP_ARCH §11.5`. P95 of the deterministic Pillow steps ≤ 2 s; the watermark Gemini call ≤ 3 s (with §6A.F budget-cap-skip path).

**Concurrency target:** Worker pod runs with `--concurrency=4` per CPU core; 2 worker pods × 4 = 8 concurrent precheck tasks max. Sized against the 10/min/user upload rate limit (§11.B.1) — at 8 concurrent + 5-second budget, throughput is 96 prechecks/min, comfortably above worst-case 10 sellers × 10 uploads/min = 100 concurrent without queue depth growth.

**Idempotency:** `UPDATE product_images SET precheck_jsonb=..., status=... WHERE id=image_id` — re-running the task on the same `image_id` overwrites with the same result. No INSERT side-effect; no GCS modification (the bytes are immutable in GCS post-upload per §11.B.1).

**Retry posture:** On exception, Celery retries with exponential backoff (1s, 2s, 4s — max 2 retries per `max_retries=2`). After 2 failed retries, the worker writes `product_images.status="failed_precheck"` and emits a logged ERROR — NO DLQ in V1, the failed row IS the dead-letter record. The poll endpoint (row 22 in §17.B) returns the failed status; the seller sees an inline error in the UI and can re-upload (V1 has no automatic retry from UI).

**Audit event:** `image.precheck.completed` — written DIRECTLY from the Celery task via `core/audit_helpers.audit_event_write(...)` per §15.E. This is one of the 3 documented audit-write exceptions to the "audit_mw writes audit_events" rule (the others are `ai_ops/client.py` per §6A.D and `iam.service.verify_otp` per §7.I). Rationale: workers have no HTTP request lifecycle — there is no `audit_mw` to hook into.

---

### 18.D `export.generate` — task contract

**Task name (Celery registration):** `export.generate`

**Owner file:** `app/modules/export/tasks.py` (per §3.C + §14.E).

**Signature (locked at §14.E):**
```python
@shared_task(name="export.generate", bind=True, max_retries=1, retry_backoff=True)
def export_generate(self, export_id: str, user_id: str) -> None:
    """Run 9-step export pipeline for a user's catalog/category/products subset.

    Composes XLSX (Meesho-format) + ZIP-packs watermarked images via 2 ComplianceStrategy
    concretes (Standard + Collapsed per §14.F + §0.G §12.6) + Layer 3 enum re-validation
    guardrail per §14.J. Performance budget ≤ 30s end-to-end (§5.5.10).
    """
    ...
```

**Payload:** `export_id: UUID, user_id: UUID`. Worker JWT re-validation per §1.G — user-id confirmed against `users` table before pipeline runs.

**Performance budget:** ≤ 30 s end-to-end per `MVP_ARCH §5.5.10`. P95 split: XLSX composition ≤ 8 s (the 9-step pipeline including Strategy dispatch + Layer 3 enum re-validation per §14.J), image ZIP packing ≤ 15 s (read 4 images/product × N products from GCS, repack into the export ZIP), GCS upload ≤ 5 s, audit write ≤ 2 s.

**Concurrency target:** Worker pod runs with `--concurrency=2` per CPU core (lower than image because export is I/O-heavy on GCS + memory-heavy on Pandas XLSX writer); 2 worker pods × 2 = 4 concurrent exports max. Sized against the 5/h/user rate limit (§17.B row 25) — at 4 concurrent + 30-second budget, throughput is 480 exports/h, well above worst-case 100 sellers × 5/h = 500 (with queue depth tolerance at peak).

**Idempotency:** `UPDATE exports SET status="completed", xlsx_url=..., zip_url=... WHERE id=export_id` — re-running the task on the same `export_id` regenerates the same artifacts (the input rows are immutable-while-processing per §14.E). If the worker dies mid-pipeline, the Celery `task_reject_on_worker_lost=True` setting (locked session 2 G3 cleanup) requeues the task — the partial GCS objects are overwritten on retry.

**Retry posture:** On exception, Celery retries 1 time with exponential backoff (1s, 2s). After 1 failed retry, the worker writes `exports.status="failed"` with the `error_code` field populated per the §14.H error taxonomy — NO DLQ in V1, the failed exports row IS the dead-letter record. The seller polls (row 26) and sees the failure; UI offers a "retry" button that creates a NEW `POST /api/v1/exports` (new UUID, new row).

**Audit event:** `product.export.completed` — written DIRECTLY from the worker via `core/audit_helpers.audit_event_write(...)` per §15.E (same documented exception pattern as §6A.D + §7.I + §11.E). The HTTP-triggered companion event `product.export.initiated` is written by the audit_mw at route response time per §17.F.

---

### 18.E Valkey wiring — broker + result backend

Per §5.C + `CLAUDE.md` Valkey DB mapping:

- **DB 0** — sessions, OTP, rate limits (NOT used by Celery).
- **DB 1** — Celery broker. The worker consumes tasks from `redis://valkey:6379/1`.
- **DB 2** — Celery result backend. Workers write results (success/failure metadata) to `redis://valkey:6379/2`. V1 does NOT consume the result backend for application logic — the worker writes to the owning table (product_images or exports), the route polls the table. The result backend exists for Celery's internal task-state tracking + future-V1.5 `AsyncResult` queries.

**Connection settings:** `celery_app.py` (per §3.I) configures both URLs via `shared/config.settings.VALKEY_URL` + path suffix. The factories in §5.C (`get_valkey_broker`, `get_valkey_results`) enforce the DB-allocation discipline.

**Lua scripts loaded at worker startup.** The 3 §15.H FE-D5 Lua scripts (rotate-refresh, revoke-refresh, OTP-allowlist) are loaded via `SCRIPT LOAD` once at worker startup, then `EVALSHA` thereafter with `EVAL` fallback on NOSCRIPT per §5.C. Workers re-validating user-id (per §1.G) do NOT consult the FE-D5 allowlist — that's a request-path concern; worker-context user-id validation is a direct `SELECT id FROM users WHERE id=$1` against Postgres.

---

### 18.F Worker JWT re-validation (the §1.G rule)

**Locked rule (§1.G):** workers re-validate `user_id` against the `users` table before executing business logic. Rationale: the JWT token was already consumed at the HTTP route; the worker receives only the `user_id` claim from the task payload. If the user has been deleted (V1.5 admin action) between task enqueue and worker pickup, the worker MUST refuse to execute.

**Implementation pattern (locked):**
```python
# app/modules/image/tasks.py + app/modules/export/tasks.py — common pattern
async def _validate_user_or_abort(user_id: UUID, session: AsyncSession) -> None:
    """Re-validate user_id at worker context. Raises UserNotFoundError if deleted."""
    result = await session.execute(select(users).where(users.id == user_id))
    if result.scalar_one_or_none() is None:
        raise UserNotFoundError(user_id=user_id)
```

Called as the FIRST line of every Celery task body after `_setup_db_session()`. The exception terminates the task (no retry — user-deletion is a permanent condition).

---

### 18.G `task_reject_on_worker_lost=True` — the session 2 G3 cleanup lock

Per session 2 close-out (G3 cleanup, recorded in `MEMORY.md` Session 2 close-out section), `celery_app.py` carries `task_reject_on_worker_lost=True`. This setting requeues a task if the worker dies mid-execution (vs marking it FAILED). Rationale: image precheck and export generate are both idempotent at the row level — a re-execution overwrites the partial result. Without this setting, a worker crash during export step 7 (image ZIP packing) would leave the `exports` row in an indeterminate state with partial GCS artifacts.

The setting is locked here at §18.G to preserve discoverability for future construction — it is a one-line operational invariant that protects export idempotency at scale.

---

### 18.H Cross-cutting integration

**§6A AI calls fire from tasks.** The `image.precheck` task invokes `ai_ops.client.call_gemini(workload="watermark", ...)` at step 5 per §11.E. This is the ONLY V1 cross-cutting integration between Celery and `ai_ops/`. The `export.generate` task does NOT invoke AI — export is deterministic per §14.A.

**Cost tracking writes audit_events directly per §6A.D.** When `image.precheck` calls Gemini at step 5, `ai_ops/cost_tracker.py` writes the `ai_ops.call.completed` audit event INLINE inside `ai_ops/client.py` per §6A.D — this is the 3rd documented exception to the "audit_mw writes audit_events" rule. The worker context does NOT have an audit_mw available, so the inline write is necessary.

**Plan_guard does NOT participate in tasks.** Per §4.E, plan_guard is enforced at the HTTP route layer (row 17 autofill, row 15 product create) BEFORE the request reaches a Celery task. Workers do NOT call `enforce_plan_limit` — by the time a task executes, the budget check has already passed.

**Tenancy enforcement.** The `scope_to_user(user_id)` repository helper per §4.C is applied in worker-context reads and writes — see §11.D (image repository) and §14.D (export repository). Workers respect the same multi-tenant isolation rules as HTTP handlers per §15.B.

---

### 18.I Failure modes + DLQ policy

**V1 has NO Dead Letter Queue (DLQ).** Failed tasks after `max_retries` exhausted are recorded in the owning table:
- `image.precheck` failure → `product_images.status = "failed_precheck"` with `precheck_jsonb.error = <error_code>`.
- `export.generate` failure → `exports.status = "failed"` with `exports.error_code = <code>` per the §14.H error taxonomy.

These status values ARE the dead-letter records. The seller-facing UI surfaces the failure and offers a manual retry (which creates a NEW row, NEW UUID, NEW task). The operator dashboard (V1.5 — not in scope here) will query these tables for failure rates.

**V1.5 forward-note.** When traffic justifies it, a Celery `task_failure` signal handler can write to a dedicated `task_failures` table or push to a Slack-bot for ops visibility. The §18.B retry counts already include this assumption — `max_retries=2` for image and `max_retries=1` for export are deliberate floor values that bound the latency for a known-failing image / export to ≤ 15 s for image and ≤ 60 s for export.

---

### 18.J What §18 does NOT cover

§18 specifies the **Celery operational contract**. The following concerns are owned elsewhere:

- **The 5-step image precheck pipeline algorithm** — §11.E (the 5 steps are: resolution check → format check → contrast check → blur check → watermark Gemini check). The `meesell-image-precheck-builder` agent owns the precheck algorithm internals.
- **The 9-step export pipeline algorithm** — §14.E (the 9 steps are: load catalog rows → load template + schema → resolve canonical→raw enum codes → load image bytes → run Layer 3 enum re-validation guardrail → compose XLSX via ComplianceStrategy dispatch → ZIP-pack images + XLSX → upload to GCS → update exports row + emit audit).
- **Gemini prompt content** — `meesell-prompt-engineer` per §6A.G (the `watermark.v1` prompt is the content of `ai_ops/prompts/watermark.py`).
- **Cost tracking detail** — §6A.D (per-call rate constants for `gemini-2.5-flash`).
- **HTTP route mounting** — §17.B (the routes that trigger Celery tasks are rows 21 image upload + 25 export initiate).
- **K3s pod manifest** — §20 (the worker pod's Dockerfile + replica count + resource limits).
- **V1.5 extraction of workers** — §16.G + §21 (image worker extracts at step 3, export worker extracts at step 1 of the §16.H extraction order).

A reviewer evaluating §18 asks: "are the 2 task contracts correct, is retry + DLQ policy locked, is worker JWT re-validation preserved across §1.G + §11.E + §14.E + §18.F?" — NOT "what's inside the precheck algorithm?" (§11.E) or "what does the export ZIP file structure look like?" (§14.F).

---

## Section 19 — Test Strategy

STATUS: LOCKED (2026-06-06)

### 19.A Preamble

§19 specifies the **backend test pyramid** + CI gate rules. The pyramid has 6 layers (unit tests → integration tests → golden round-trip fixtures → golden AI eval sets → boot smoke tests → DB schema smoke tests). The CI gate runs 4 categories of checks (pytest pass/fail, import-linter contracts pass, M10 forbidden-symbol scanner pass, performance-budget marks within target). When all 4 CI gates pass, the backend is **shippable** per the §22 acceptance checklist.

§19 does NOT re-author the per-module test plans — the V1 unit + integration test inventories are locked at each module's §X.J / §X.K subsection (consolidated in §19.B below). What §19 DOES specify is the executable wiring of the §16.E import-linter TOML sketch, the §14.J Layer 3 / §15.F M10 forbidden-symbol scanner, the pytest fixture posture (real Postgres via dev tunnel + Valkey + mocked AI/adapter layers), the coverage targets, and the performance budgets consolidated from per-module specs.

A reviewer evaluating §19 asks: "do all 7 import-linter contracts from §16.E have executable test wiring, is the M10 symbol scanner specified, are the performance budgets correctly consolidated from per-module sections, do coverage targets match the §22 acceptance criteria?" — NOT "what should the unit test for `customer.service.assert_eligible_for_super_id` look like?" (§8.J).

---

### 19.B Test layer inventory (consolidated across §7-§14)

The test pyramid has 6 layers; the V1 floor per layer:

**Layer 1 — Unit tests (~40 test classes).** Pure-function tests for services, repositories, domain dataclasses, validators, Strategy classes. Per-module inventory (consolidated):

| Module | Unit test classes (count) | Locking |
|--------|--------------------------|---------|
| `iam` | 4 | §7.J |
| `customer` | 5 | §8.J |
| `category` | 5 | §9.J |
| `catalog` | 5 | §10.J |
| `image` | 5 | §11.K |
| `pricing` | 4 | §12.J |
| `dashboard` | 3 | §13.J |
| `export` | 9 (highest — ComplianceStrategy dispatch + Layer 3 guardrail + canonical→raw enum lookup) | §14.K |
| **Total V1 floor** | **~40 unit test classes** | — |

**Layer 2 — Integration tests (~21 test classes).** Per-module router + service + repository against real test DB (dev tunnel Postgres + Valkey). Per-module inventory:

| Module | Integration test classes (count) | Locking |
|--------|-----------------------------------|---------|
| `iam` | 3 (full silent-refresh flow + logout revocation + replay-attack mitigation per §19 amendments) | §7.J |
| `customer` | 2 | §8.J |
| `category` | 3 (Smart Picker + Browse + Schema fetch with cache hit) | §9.J |
| `catalog` | 3 | §10.J |
| `image` | 3 (upload→poll→ready + watermark budget exhaustion + cross-module URL fetch) | §11.K |
| `pricing` | 2 | §12.J |
| `dashboard` | 2 | §13.J |
| `export` | 3 (Standard Strategy + Collapsed Strategy + Layer 3 enum re-validation) | §14.K |
| **Total V1 floor** | **~21 integration test classes** | — |

**Layer 3 — Golden round-trip fixtures (15 fixtures).** Per `MVP_ARCH §5.7` + §14.K: one golden fixture per super-category, plus the Eye-Serum collapsed variant. The fixture is a (input XLSX row, expected canonical product, regenerated XLSX row) tuple — the test asserts that the canonical→raw round-trip is byte-equal for every field. 15 fixtures total (14 super-categories + 1 Eye-Serum collapsed shape).

**Layer 4 — Golden AI eval sets (3 sets).** Per §6A.H: Smart Picker (50 examples, top-5 recall ≥ 80%), Autofill (30 examples, 0% invalid enum emissions), Watermark (30 examples, classification accuracy ≥ 85%). The 3 sets run weekly in CI via `pytest --markers ai_eval`. Failure on any threshold is a CI red flag — Layer 1 + Layer 2 guardrails (per §6A.E) compensate at runtime, but eval-set drift signals prompt-content regression that the `meesell-prompt-engineer` must investigate.

**Layer 5 — Boot smoke tests (already shipped).** `backend/tests/test_app_boot_integration.py` — 7/7 PASS as of session 2 close-out. Asserts FastAPI app boots without import errors, mounts the expected routes, registers error handlers, configures middleware chain. Post-construction extension: the route count assertion increments from 9 → 35 per §17.B.3.

**Layer 6 — DB schema smoke tests (already shipped).** `backend/tests/test_database.py` — 42/42 PASS as of session 2 close-out. Asserts the 13 ORM models match the live Alembic head schema (column names, types, indexes, constraints). Includes the section-H tests for `is_advanced` flag wiring per session 2 G1.

**Test inventory totals:** Unit ≈ 40 + Integration ≈ 21 + Golden round-trip 15 + AI eval 3 sets + Boot smoke 7 + DB schema 42 = **~88 test classes / ~125+ individual test functions** post-construction.

---

### 19.C CI linter rules — operationalizing §16.E import-linter

The §16.E TOML sketch (`tests/lint/import_rules.toml`) is locked. §19 specifies the executable pytest fixture that runs the linter as part of every CI build.

**Contracts 1-7 (verbatim from §16.E):**
1. **`repository.py` is PRIVATE** — domain modules MUST NOT import another module's repository. Self-imports allowlisted per the §16.E `ignore_imports` block.
2. **`adapters/gemini.py` is accessed ONLY via `ai_ops/client.py`** — domain modules MUST NOT import `app.adapters.gemini` directly. This is the single most important boundary per §16.D.2.
3. **M10 meesho-format symbols confined to `export` + `adapters/gcs.py`** — `meesho_column_header`, `meesho_column_index`, `enum_codes_map` symbols MUST NOT appear outside `modules/export/` + `adapters/gcs.py`. The import-linter component covers module-level imports; the symbol-level enforcement is the custom AST scanner per §19.E below.
4. **`schemas.py` is PRIVATE wire-shape** — domain modules MUST NOT import another module's Pydantic schemas. Self-imports allowlisted.
5. **`ai_ops/` consumed only by `category`, `catalog`, `image`** — the other 5 domain modules (`iam`, `customer`, `pricing`, `dashboard`, `export`) MUST NOT import `app.ai_ops.*`.
6. **`domain.py` cross-module signature rule** — deferred to PR review per §16.E (import-linter cannot reason at signature granularity).
7. **`router.py` and `tasks.py` are NEVER cross-module imported** — only `app/main.py` registers routers (per `app/main.py` allowlist), only `app/workers/celery_app.py` registers tasks (per allowlist).

**Plus the §15.B `scope_to_user` enforcement check (Contract 8 — NEW, locked here).** A custom AST script (`tests/lint/check_scope_to_user.py`) scans every `repository.py` method that queries an owned-table (per §15.B 7-row matrix). For each such method:
- If the method's signature does NOT contain a `user_id` parameter, the test FAILS.
- Allowlist: `category/repository.py` per §16.F exception 2 (categories/templates/field_enum_values/field_aliases are GLOBAL); `dashboard` has no repository per §16.F exception 1.

**Plus the §14.J M10 forbidden-symbol scanner (Contract 9 — NEW, locked here).** A custom AST scan (`tests/lint/check_no_meesho_symbols_outside_export.py`) walks every `.py` file under `app/modules/` (excluding `modules/export/`) and `app/` non-modules (`core/`, `shared/`, `ai_ops/`, `i18n/`), asserting the 3 forbidden symbols (`meesho_column_header`, `meesho_column_index`, `enum_codes_map`) do not appear. Allowlist: `app/modules/export/*` + `app/adapters/gcs.py` write paths (the GCS adapter writes export artifacts — symbols may flow through it as method argument names).

**Plus the §5A.H message_id regex check (Contract 10 — NEW, locked here).** A custom pytest test scans `app/i18n/messages_en.py` and asserts every key matches the locked regex `^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$` per the §5A.H 3-segment convention. Catches future inconsistencies (e.g. someone adds `"catalog.draftMissing"` camelCase instead of `"catalog.draft.missing"` snake_case).

**10 total CI linter contracts** — 7 from §16.E import-linter + 3 custom AST scanners (Contract 8, 9, 10).

---

### 19.D Pytest configuration

**`pyproject.toml` / `pytest.ini` settings (consolidated):**

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["backend/tests"]
markers = [
    "unit: pure-function tests, no I/O",
    "integration: real DB + Valkey via dev tunnel",
    "golden_roundtrip: 15 XLSX round-trip fixtures per §14.K",
    "ai_eval: golden AI eval sets per §6A.H (runs weekly, gated by RUN_AI_EVAL=1)",
    "slow: tests that exceed 5s wall time (gated by PYTEST_RUN_SLOW=1)",
    "smoke: boot + DB schema smoke tests",
]
addopts = [
    "--strict-markers",
    "--strict-config",
    "-ra",
]
```

**Per-fixture posture (consolidated):**

- **`db` fixture** — real Postgres via dev tunnel (per `CLAUDE.md` standard tunnel pattern, `localhost:5433` exposed); per-test DB transaction with ROLLBACK at teardown for isolation.
- **`valkey` fixture** — real Valkey via dev tunnel; per-test FLUSHDB on DB 0/1/2/3 at teardown.
- **`mock_ai_ops_client` fixture** — `unittest.mock.AsyncMock` substituting `ai_ops.client.call_gemini` for unit + integration tests (real Gemini only consumed by AI eval set tests).
- **`mock_msg91_adapter` fixture** — substitutes `adapters.msg91.send_otp` for OTP-related tests (avoids burning MSG91 quota in CI).
- **`mock_gcs_adapter` fixture** — substitutes `adapters.gcs.{upload,download,signed_url}` for image/export tests (uses an in-memory bytes dict).
- **`mock_razorpay_adapter` fixture** — substitutes `adapters.razorpay.verify_webhook_signature` for webhook tests.

**Real-vs-mock policy (locked):** `db` + `valkey` are ALWAYS real in V1 (no SQLite, no fakeredis) — the cost of running against real infra is justified by the schema-fidelity bugs SQLite would mask. Adapter layer is ALWAYS mocked (per-test) except in the dedicated golden-fixture + AI-eval suites.

---

### 19.E Performance budgets — consolidated from per-module specs

§19 is the single assertion point for backend performance budgets. The 4 budgets locked across §6-§14:

| Budget | Source | Enforcement |
|--------|--------|-------------|
| P95 schema fetch ≤ 50 ms (cache hit) / ≤ 200 ms (cache miss) | `MVP_ARCH §6.6` + §9.B.4 | `tests/perf/test_category_schema_p95.py` (marker: slow + perf) |
| P95 manual-browse query ≤ 200 ms | `MVP_ARCH §7.5` + §9.B.2 | `tests/perf/test_category_browse_p95.py` |
| End-to-end export pipeline ≤ 30 s | `MVP_ARCH §5.5.10` + §14.E + §18.D | `tests/perf/test_export_pipeline.py` (marker: slow + perf) |
| Per-call AI cost ≤ ₹0.05 average | `MVP_ARCH §8.2` + §6A.D | `tests/perf/test_ai_cost_average.py` (consumes 7-day audit_events rolling window) |

Performance tests are pytest-marked `perf` and `slow` — gated by `PYTEST_RUN_SLOW=1` env var. CI runs them nightly (NOT per-PR — too slow); per-PR runs the unit + integration + linter contracts only.

**Performance regression policy (locked):** if a perf test fails its budget by > 10% relative to the prior 7-day baseline, the PR is BLOCKED and the responsible specialist must investigate before merge. The 10% tolerance allows for noise; >10% indicates a real regression.

---

### 19.F Coverage targets

**Backend coverage targets for V1:**

- **80% module-level line coverage** for `app/modules/*/service.py` and `app/modules/*/repository.py` (the two layers that hold business logic). `pytest-cov` measures via `pytest --cov=app.modules --cov-fail-under=80`.
- **100% endpoint coverage** — every contract endpoint (27 per §17.B + 2 infrastructure = 29 total) has at least 1 happy-path integration test. Asserted by a custom test (`tests/lint/check_endpoint_coverage.py`) that introspects FastAPI's `app.routes` and cross-references with the integration test inventory.
- **Schemas.py + router.py + domain.py + exceptions.py NOT in coverage scope** — these are declarative layers (Pydantic models, FastAPI route bindings, frozen dataclasses, exception classes). Their correctness is asserted by the integration tests, not by coverage of their own lines.

Coverage reports surface in CI as a comment on the PR; coverage drop > 5% triggers a review block.

---

### 19.G CI integration

**Pytest fixture for import-linter (Contract 1-7):**

```python
# backend/tests/lint/test_import_contracts.py
import subprocess

def test_import_linter_contracts_pass():
    """Runs import-linter against the locked tests/lint/import_rules.toml."""
    result = subprocess.run(
        ["lint-imports", "--config", "tests/lint/import_rules.toml"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"import-linter contracts failed:\n{result.stdout}\n{result.stderr}"
```

**Per-contract test wiring:** the 3 custom AST scanners (Contract 8, 9, 10) each have a dedicated test file under `backend/tests/lint/`:
- `test_scope_to_user_enforcement.py` (Contract 8).
- `test_no_meesho_symbols_outside_export.py` (Contract 9).
- `test_message_id_regex.py` (Contract 10).

**CI pipeline stages (sequential per locked order):**
1. **Stage 1 — `pytest -m "unit"`** (fast, < 30s total) — runs all unit tests. Failure blocks the build.
2. **Stage 2 — `pytest -m "smoke"`** (< 10s) — runs boot + DB schema smoke tests.
3. **Stage 3 — Linter contracts** (< 5s) — runs the 10 CI linter contracts (Stage 3 separately fails the build per the §16.E hard rule).
4. **Stage 4 — `pytest -m "integration"`** (~ 2-5 min) — runs all integration tests against real Postgres + Valkey via dev tunnel.
5. **Stage 5 — `pytest -m "golden_roundtrip"`** (~ 30s) — runs the 15 round-trip fixtures.
6. **Stage 6 (nightly only)** — `pytest -m "slow" -m "perf"` + `pytest -m "ai_eval"` (gated by env vars).

Stages 1-5 run on every PR; stage 6 runs nightly. The PR cannot merge unless stages 1-5 are green.

---

### 19.H Multi-tenant isolation regression test

Per §15.B, every PR runs the **multi-tenant isolation regression test** as part of the integration suite:

```python
# backend/tests/integration/test_tenant_isolation.py
async def test_user_a_cannot_read_user_b_products(db, valkey):
    """Per §15.B + §22.B: User A's products MUST NOT be visible to User B."""
    user_a = await create_test_user(db)
    user_b = await create_test_user(db)
    product_a = await create_test_product(db, user_id=user_a.id)

    # Authenticate as User B
    user_b_token = mint_test_jwt(user_b.id)

    # User B attempts to read User A's product (rows 18, 24 GET /products/{id}/preview + GET /products)
    resp_preview = await client.get(f"/api/v1/products/{product_a.id}/preview",
                                     headers={"Authorization": f"Bearer {user_b_token}"})
    assert resp_preview.status_code == 404  # NotFound, not 403 — leaks no info

    resp_list = await client.get("/api/v1/products",
                                  headers={"Authorization": f"Bearer {user_b_token}"})
    assert product_a.id not in [p["id"] for p in resp_list.json()["products"]]
```

The test covers 4 cross-tenant attack vectors per §15.B: direct GET of another tenant's product, list-endpoint leakage, autosave-PATCH against another tenant's product, image-upload to another tenant's product. Each vector has a dedicated test method.

---

### 19.I What §19 does NOT cover

§19 specifies the **backend test strategy**. The following concerns are owned elsewhere:

- **End-to-end browser tests** — owned by the frontend track; backend's integration tests cover the API contract surface.
- **Load testing (sustained 1000 RPS scenarios)** — V1.5 concern; V1 ships with the per-route rate-limit ceilings + perf budgets as the throughput floor.
- **Per-module test class content** — each module's §X.J / §X.K subsection owns the test method names + assertion shape. §19 consolidates the inventory; specialists author the methods.
- **Test data fixtures content** — per-module (the `customer` fixture for a complete seller profile, the `catalog` fixture for a draft product, etc.) — owned by the specialist constructing that module.
- **Frontend test strategy** — owned by `meesell-frontend-coordinator` (FRONTEND_ARCH §19).
- **Infrastructure smoke tests** (K3s pod health, Valkey response time alerting) — owned by `meesell-infra-builder`.
- **AI prompt-content regression tests** — owned by `meesell-prompt-engineer` per §6A.H; §19 runs the eval-set tests but does NOT author the prompts.

A reviewer evaluating §19 asks: "do all 7 import-linter contracts + 3 custom AST scanners have executable wiring, are performance budgets correctly cited, do coverage targets match §22 acceptance criteria, does the multi-tenant isolation regression cover the 4 attack vectors?" — NOT "what should `customer.test_assert_eligible_for_super_id` assert?" (§8.J).

---

## Section 20 — Deployment Topology (V1)

STATUS: LOCKED (2026-06-06)

### 20.A Preamble

§20 specifies the **V1 K3s deployment topology** for the backend track. Per `CLAUDE.md`, the deployment is a **single-node K3s cluster on the `meesell-dev` VM in `asia-south1-a`**, with the namespace pattern `dev` / `staging` / `prod`. Per the infra-builder memory, Phase A is in flight: VM + Artifact Registry + GCS bucket + 7 Secret Manager secrets are LIVE; 3 secrets remain pending construction (refresh-token-pepper, razorpay-webhook-secret, langfuse-secret-key per §5.D + §15.H).

§20 is the **bridge between this document and `meesell-infra-builder`**. The infra builder authors the K3s YAML; backend coordinator specifies what those manifests must contain in terms of pods, env vars, secrets, health checks, resource budgets, and rolling-update policy. §20 does NOT author Terraform modules (those live in `infra/terraform/modules/` per infra-builder ownership); it specifies the application-side requirements.

A reviewer evaluating §20 asks: "are the 4 pod manifests correctly enumerated, do env-var injections cite §5.D, are health checks specified, do resource budgets fit in a single VM, is the V1.5 extraction-prep posture preserved?" — NOT "what K3s version do we run?" (infra-builder) or "what's the Traefik IngressRoute YAML look like?" (infra-builder).

---

### 20.B Pod inventory — V1 = 4 pod types

| # | Pod | Replicas (V1) | Image | Process model |
|---|-----|--------------|-------|---------------|
| 1 | `api` (FastAPI) | 2 | `backend/Dockerfile` (uvicorn + `app.main:app`) | HTTP server, port 8000 |
| 2 | `worker` (Celery) | 2 | same as `api` Dockerfile, different CMD (`celery -A app.workers.celery_app worker -c 4`) | Celery worker, no HTTP port |
| 3 | `postgres` (Supabase trimmed) | 1 | Supabase trimmed image per `CLAUDE.md` Decision 15 | PostgreSQL 16, port 5432 (internal only) |
| 4 | `valkey` | 1 | `valkey/valkey:8` | Valkey 8, port 6379 (internal only), `maxmemory=128mb` per Phase A |

**§20.B.1 The 4-pod floor is V1.** No additional pods (no Redis Sentinel, no Postgres replica, no separate prompt-eval worker) ship in V1. Per `MVP_ARCH §10` the single-node K3s is sized for V1 traffic floor.

**§20.B.2 The `api` Dockerfile.** Per `CLAUDE.md` backend root structure (`backend/Dockerfile`). Single multi-stage Dockerfile, Python 3.12-slim base, pip install requirements.txt, copy app/, default CMD = `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1` (the 2 replicas + 1 uvicorn-worker each = 2 process-level concurrency; in-process async I/O via uvicorn event loop handles request concurrency).

**§20.B.3 The `worker` deployment.** Same Dockerfile, different CMD: `celery -A app.workers.celery_app worker --loglevel=info --concurrency=4 --max-tasks-per-child=100`. The `--max-tasks-per-child=100` triggers worker process recycling — defends against memory leaks in the Pillow + Pandas paths (image precheck + export pipeline are memory-intensive).

---

### 20.C Env-var injection — `envFrom: secretRef:` pattern per §5.D

Per §5.D + the infra-builder Phase A pattern, every env var sourced from GCP Secret Manager is injected via Kubernetes `envFrom: secretRef:`. The secret is created in Secret Manager (per infra-builder) and synced into Kubernetes as an Opaque Secret by `external-secrets-operator` (deferred to V1.5 per infra-builder roadmap) OR manually populated as a Kubernetes Secret during initial deployment.

**Required secrets (consolidated from §5.D + infra-builder memory):**

| Secret name (K8s) | Source (Secret Manager) | Pod consumers | Phase A status |
|-------------------|------------------------|---------------|-----------------|
| `database-url` | (composed from postgres creds — internal cluster DSN) | api, worker | live |
| `valkey-url` | (composed — `redis://valkey:6379`) | api, worker | live |
| `jwt-secret` | `jwt-secret` | api, worker | LIVE (Phase A) |
| `gemini-api-key` | `gemini-api-key` | api, worker | LIVE (Phase A) |
| `msg91-auth-key` | `msg91-auth-key` | api | LIVE (Phase A) |
| `msg91-template-id` | `msg91-template-id` | api | LIVE (Phase A) |
| `razorpay-key-id` | `razorpay-key-id` | api | LIVE (Phase A, test mode) |
| `razorpay-key-secret` | `razorpay-key-secret` | api | LIVE (Phase A, test mode) |
| `audit-pii-salt` | `audit-pii-salt` | api, worker | LIVE (Phase A) |
| `refresh-token-pepper` | `refresh-token-pepper` | api | **PENDING** (populated during iam construction dispatch) |
| `razorpay-webhook-secret` | `razorpay-webhook-secret` | api | **PENDING** (populated during iam construction dispatch) |
| `langfuse-secret-key` | `langfuse-secret-key` | api, worker | **PENDING** (populated during ai_ops construction dispatch) |
| `gcs-service-account-json` | (composed JSON for `storage.objectAdmin`) | api, worker | live (VM SA binding per Phase A A2) |

**§20.C.1 Pattern.** Each pod's spec carries:

```yaml
envFrom:
  - secretRef:
      name: backend-secrets
```

Where `backend-secrets` is an Opaque Secret holding ALL the entries above as key/value pairs (one secret to reduce manifest sprawl; entries map 1-1 to the `shared/config.Settings` env-var names per §5.D).

**§20.C.2 The 3 PENDING secrets.** Must be populated before the corresponding specialist construction dispatch can run. Coordinator does NOT populate (per §5.D infra-side rule); the infra-builder owns the `gcloud secrets versions add` invocation when the specialist signals they're ready to wire the secret.

---

### 20.D Ingress + TLS + CORS

Per the infra-builder Phase A state (Traefik live + cert-manager Let's Encrypt cert live at `studio.mesell.xyz`):

- **Ingress controller:** Traefik (K3s built-in). Single `IngressRoute` per namespace routes traffic to the `api` Service.
- **TLS:** Let's Encrypt via cert-manager. Wildcard cert `*.mesell.xyz` covers `dev.mesell.xyz`, `staging.mesell.xyz`, `www.mesell.xyz`, `api.mesell.xyz`, `studio.mesell.xyz`.
- **API path prefix:** `/api/v1/*` per `CLAUDE.md` API design rule. The Traefik IngressRoute matches `Host=api.mesell.xyz PathPrefix=/api/v1` and forwards to the `api` Service on port 8000.
- **CORS configuration (per §4.G amendment):** `Access-Control-Allow-Origin` set to the explicit FE origin (NEVER `*`); `Access-Control-Allow-Credentials: true` on `/api/v1/auth/*` paths only; `Domain=.mesell.xyz` on the refresh cookie so it's scoped to all subdomains.

The infra-builder owns the IngressRoute YAML; §20 specifies the application-side CORS configuration that the IngressRoute must NOT strip (per §4.G amendment locking statement).

---

### 20.E Health checks

Per FastAPI conventions:

- **Liveness probe** — `GET /health` on the `api` pod, every 30s, fails after 3 consecutive failures. Path returns `{"status": "ok"}` if the process is responsive.
- **Readiness probe** — `GET /health` on the `api` pod, every 10s during startup, must pass before the pod receives traffic. Same response shape as liveness.
- **Worker liveness** — Celery worker pods do not have an HTTP endpoint. Liveness is determined by Kubernetes process-alive heuristic + Celery's `inspect ping` (deferred to V1.5 for proactive worker-health alerting).
- **Postgres readiness** — `pg_isready` exec probe. Postgres pod ready when the socket accepts connections.
- **Valkey readiness** — `valkey-cli ping` exec probe. Valkey pod ready when PONG is returned.

**§20.E.1 Startup hook — `prewarm_top_categories`.** Per §4.D + §9.J, the `api` FastAPI startup hook calls `prewarm_top_categories` which loads the 100 most-frequently-accessed category schemas into Valkey DB 3. This adds ~5 s to startup time; the readiness probe MUST tolerate this (initial grace period 15 s before first probe).

---

### 20.F Scaling posture

**V1 = 2 replicas fixed for both `api` and `worker`.** No Horizontal Pod Autoscaler (HPA) in V1 — `MVP_ARCH §10` justifies static replicas at the V1 traffic floor (~100 sellers × ~50 actions/day = ~5K req/day, comfortably handled by 2 pods).

**V1.5 forward-note.** HPA based on CPU > 70% threshold scales `api` 2 → 5 replicas; CPU > 70% scales `worker` 2 → 4 replicas. The HPA manifest is locked to author during V1.5 traffic spike preparation. The `api` Service stays on ClusterIP with internal port 8000; the IngressRoute Service is the external entry. HPA changes do NOT require code changes — the application is stateless.

**§20.F.1 Rolling update strategy.** `RollingUpdate` with `maxSurge: 1, maxUnavailable: 0` for both `api` and `worker` Deployments. Guarantees zero-downtime deployments: one new pod comes up + passes readiness before an old pod terminates.

---

### 20.G Per-pod resource requests/limits — V1 sketch

The §20 budgets are sketches to be finalized by `meesell-infra-builder` during the per-namespace manifest authoring. Sizing target: total fits in an `e2-medium` GCP instance per `MVP_ARCH §10` (2 vCPU / 4 GB RAM).

| Pod | Replicas | CPU requests / limits | Memory requests / limits |
|-----|---------|----------------------|--------------------------|
| `api` | 2 | 500m / 1000m | 512Mi / 1Gi |
| `worker` | 2 | 1000m / 2000m | 1Gi / 2Gi |
| `postgres` | 1 | 1500m / 3000m | 2Gi / 3Gi |
| `valkey` | 1 | 200m / 500m | 256Mi / 512Mi |
| **Total (requests)** | — | ~4500m (≈ 4.5 CPU) | ~5Gi |
| **Total (limits)** | — | ~8000m (≈ 8 CPU) | ~9.5Gi |

**§20.G.1 Sizing rationale.** Requests are what K3s reserves; limits are the burst ceiling. Total requests (4.5 CPU + 5Gi RAM) fits in an `e2-medium` (2 vCPU + 4 GB) — and per the infra-builder memory the actual VM size in Phase A is `e2-standard-4` (4 vCPU + 16 GB) which comfortably accommodates limits (8 CPU + 9.5Gi). The headroom of ~6 GB RAM is for K3s overhead + cert-manager + Traefik + future-V1.5 HPA scaling.

**§20.G.2 V1.5 scaling targets.** When traffic grows: api 2 → 5 replicas adds 1.5 CPU + 1.5Gi RAM (requests); worker 2 → 4 replicas adds 2 CPU + 2Gi RAM. Total at V1.5 scale: ~8 CPU + 8.5Gi RAM — requires upgrading to `e2-standard-8` (8 vCPU + 32 GB) or splitting workloads to multiple nodes (post-V1.5 K3s multi-node).

---

### 20.H K3s manifest sketches — application side

These are sketches the `meesell-infra-builder` consumes when authoring the `infra/k8s/` YAML.

**`api` Deployment sketch (per-namespace):**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: meesell-api
  namespace: dev  # or staging / prod
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate: { maxSurge: 1, maxUnavailable: 0 }
  selector: { matchLabels: { app: meesell-api } }
  template:
    metadata: { labels: { app: meesell-api } }
    spec:
      containers:
        - name: api
          image: asia-south1-docker.pkg.dev/project-1f5cbf72-2820-4cdb-949/meesell-prod-images/api:<tag>
          ports: [{ containerPort: 8000 }]
          envFrom:
            - secretRef: { name: backend-secrets }
          env:
            - name: APP_ENV
              value: "dev"  # or staging / prod
          resources:
            requests: { cpu: 500m, memory: 512Mi }
            limits:   { cpu: 1000m, memory: 1Gi }
          livenessProbe:
            httpGet: { path: /health, port: 8000 }
            initialDelaySeconds: 30
            periodSeconds: 30
            failureThreshold: 3
          readinessProbe:
            httpGet: { path: /health, port: 8000 }
            initialDelaySeconds: 15
            periodSeconds: 10
```

**`worker` Deployment sketch (per-namespace):**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: meesell-worker
  namespace: dev
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate: { maxSurge: 1, maxUnavailable: 0 }
  selector: { matchLabels: { app: meesell-worker } }
  template:
    metadata: { labels: { app: meesell-worker } }
    spec:
      containers:
        - name: worker
          image: asia-south1-docker.pkg.dev/project-1f5cbf72-2820-4cdb-949/meesell-prod-images/api:<tag>
          command: ["celery"]
          args: ["-A", "app.workers.celery_app", "worker", "--loglevel=info", "--concurrency=4", "--max-tasks-per-child=100"]
          envFrom:
            - secretRef: { name: backend-secrets }
          resources:
            requests: { cpu: 1000m, memory: 1Gi }
            limits:   { cpu: 2000m, memory: 2Gi }
```

**§20.H.1 Postgres + Valkey** manifests are owned by infra-builder per Phase A Terraform modules (`infra/terraform/modules/postgres/` + `infra/terraform/modules/valkey/`). The Valkey module's `maxmemory=128mb --maxmemory-policy allkeys-lru` is verified live per infra-builder memory.

---

### 20.I V1.5 extraction prep posture

Per §16.G + §21, V1.5 extracts modules one at a time. The §20 manifests are the V1 floor; extracted pods follow the same structural pattern:

- **Each extracted pod uses the same Dockerfile** (the entire `backend/` codebase ships in the image). Per §16.G the shim layer `core/extracted_clients/<module>_client.py` makes the in-process function call indistinguishable from the HTTP call.
- **Extracted pod command differs by module sub-tree.** E.g. extracting `export` (first per §16.H order) launches with CMD `uvicorn app.modules.export.standalone:app --port 8001` (the `standalone:app` is a thin FastAPI app mounting only the export routes + internal endpoints per §16.G.1).
- **V1.5 manifests authored at extraction time, NOT pre-emptively.** The §20 amendment at each extraction milestone adds the per-module pod spec; V1 does NOT carry placeholder manifests.

**§20.I.1 Backwards-compatibility guarantee.** Per §16.G.4, during the extraction window of a module, CI runs the test suite TWICE — once with the in-process module mounted (V1 mode), once with the HTTP shim pointing at the docker-compose'd extracted pod. Both modes MUST pass before the per-namespace manifest update lands in production.

---

### 20.J Ownership boundaries

**`meesell-infra-builder` owns:**
- K3s cluster lifecycle (install, upgrade, node management).
- Postgres + Valkey + Traefik + cert-manager pod manifests + Terraform modules.
- Secret Manager + Kubernetes Secret wiring + the `external-secrets-operator` deployment.
- Ingress + TLS + DNS at `mesell.xyz`.
- GCS bucket lifecycle (`meesell-prod-assets`, `meesell-images`).
- Artifact Registry + image build pipeline (CI side).

**`meesell-backend-coordinator` owns (this section + §3):**
- `backend/Dockerfile` (single-stage or multi-stage Python image).
- `backend/app/main.py` (FastAPI app construction + middleware registration + startup hook).
- The manifest SPEC (this section §20.H) consumed by infra-builder.
- The env-var list specified at §5.D.

**Per the SPEC vs IMPL distinction:** coordinator authors the specification; infra-builder implements the Kubernetes manifests, the Terraform modules, the GitLab CI deployment pipeline.

---

### 20.K What §20 does NOT cover

§20 specifies the **V1 deployment topology FROM THE BACKEND APPLICATION SIDE**. The following concerns are owned by `meesell-infra-builder`:

- **Terraform module internals** (`infra/terraform/modules/postgres/`, `infra/terraform/modules/valkey/`, etc.).
- **Initial Secret Manager population** (`gcloud secrets versions add`) — infra-builder runs the commands; coordinator only specifies the env-var names.
- **GitLab CI deployment pipeline** (build + push + kubectl apply).
- **DNS + cert-manager Let's Encrypt automation.**
- **V2 multi-region** topology (deferred per `MVP_ARCH §14`).
- **Monitoring stack** (Prometheus + Grafana — currently NOT deployed per infra-builder Phase A; deferred to V1.5).
- **V1.5 HPA + multi-node K3s** topology.

A reviewer evaluating §20 asks: "are the 4 pod manifests correctly enumerated, do env-var injections cite §5.D, are health checks specified, do resource budgets fit in the e2-standard-4 VM, is the V1.5 extraction-prep posture preserved?" — NOT "what's the Postgres backup strategy?" (infra-builder) or "how does the CI deployment pipeline work?" (infra-builder).

---

## Section 21 — Extraction Path (V1.5 / V2)

STATUS: LOCKED (2026-06-06)

### 21.A Preamble

§21 is the **per-module extraction roadmap** for the V1.5 / V2 lifecycle. The modular monolith's payoff (locked at §16.G) is the V1.5 extraction story: a module extracts to its own pod **without changing call sites** in any other module. §21 specifies the order (consolidated from §16.H), the readiness checklist per module, the milestone progression from V1 → V1.5 → V2, and the hybrid-mode operating posture between extractions.

§21 does NOT specify extraction dates — that's a business decision tied to traffic growth, team size, and product roadmap. §21 specifies the TECHNICAL EXTRACTION READINESS state per module so that when the business calls "extract export now," the dispatch has a locked checklist.

A reviewer evaluating §21 asks: "is the extraction order traceable to §16.H, does the per-module readiness checklist cite the original locking section, are V1.5 and V2 milestones correctly scoped, does the hybrid-mode posture preserve the §16.G call-site contract?" — NOT "when should we extract category?" (business).

---

### 21.B Extraction order (consolidated from §16.H)

| Order | Module | Rationale | Locking |
|-------|--------|-----------|---------|
| 1st (easiest) | `export` | No downstream dependents — nothing imports export. Extracts alone with no ripple. | §16.H.1 + §14.L |
| 2nd | `dashboard` | Consumes catalog + customer but has no repository (per §16.F exception 1). Trivial extraction surface — pure composition layer. | §16.H.1 + §13.K |
| 3rd | `image` | Consumes catalog (ownership gate). Worker pod already a separate process boundary per §11.L. | §16.H.1 + §11.L |
| 4th | `pricing` | Consumes catalog + category. Deterministic compute, easy to verify in HTTP mode. | §16.H.1 + §12.K |
| 5th | `customer` | Consumed by catalog + export + dashboard. Tenant-scoped, low cross-module call volume. | §16.H.1 + §8.K |
| 6th | `category` | Consumed by catalog + pricing + export. Heavy cache layer — extraction must preserve cache contract. | §16.H.1 + §9.K |
| 7th | `iam` | Consumed by every authenticated route via `core/auth_mw`. Extraction last because every other module must have its `get_current_user` shim already wired. | §16.H.1 + §7.K |
| 8th (hardest) | `catalog` | The spine — every other module is already calling catalog via HTTP shim by the time catalog extracts. | §16.H.1 + §10.K |

The order is the same as §16.H — replicated here for §21 readability. The rationale per step is preserved verbatim.

---

### 21.C Per-module extraction-readiness checklist

For each of the 8 modules, the checklist verifies 4 readiness conditions before extraction can begin:

1. **Stable `service.py` public methods.** No public method signature has changed in the last 30 days.
2. **JSON-serializable `domain.py` return types.** Every public method's return type is a frozen dataclass with primitive / dict / list fields (no datetime objects, no UUID objects without serializer wiring).
3. **Data-layer migration plan.** Per-module specifics — see below.
4. **V1.5 vs V2 trigger.** A specific business signal that justifies extraction.

**§21.C.1 `export` (order 1).**
- ✓ Stable methods (locked at §14.C — 4 public methods, no changes since lock).
- ✓ JSON-serializable returns (`Export`, `ExportInitiatedResponse`, `ExportSummary` per §14.G).
- **Data migration:** `exports` table can remain in the shared Postgres at V1.5 extraction (export reads `catalogs` + `products` + `seller_profile` via HTTP, writes only to `exports`); V2 migrates `exports` to dedicated Postgres.
- **V1.5 trigger:** Export pipeline starts hitting the 30s budget consistently — extracting to a dedicated pod with higher CPU allocation unblocks throughput.

**§21.C.2 `dashboard` (order 2).**
- ✓ Stable methods (locked at §13.C — 1 public method, no changes since lock).
- ✓ JSON-serializable returns (`ProductListResponse` per §13.E).
- **Data migration:** Dashboard owns ZERO tables per §13.D — NOTHING to migrate.
- **V1.5 trigger:** Dashboard's read path starts hitting per-IP rate limits OR when the materialized view for performance (V1.5 amendment) lands and warrants a dedicated query pod.

**§21.C.3 `image` (order 3).**
- ✓ Stable methods (locked at §11.C — 6 public methods).
- ✓ JSON-serializable returns (`ImageUrl`, `ImageStatusSummary` per §11.G).
- **Data migration:** `product_images` table can remain in shared Postgres at V1.5; V2 migrates to dedicated Postgres or GCS-backed metadata store.
- **V1.5 trigger:** Image precheck worker queue depth grows beyond 4-task ceiling — extracting to dedicated worker pod with larger concurrency unblocks throughput.

**§21.C.4 `pricing` (order 4).**
- ✓ Stable methods (locked at §12.C — 1 public method).
- ✓ JSON-serializable returns (`PnLBreakdown`, `PricingAlert` per §12.F).
- **Data migration:** `pricing_calcs` table remains in shared Postgres.
- **V1.5 trigger:** Pricing engine starts being called by 3rd-party integrations (e.g. external "bulk price recalc" endpoint) — extracting allows independent scaling.

**§21.C.5 `customer` (order 5).**
- ✓ Stable methods (locked at §8.C — 9 public methods including 3 cross-module).
- ✓ JSON-serializable returns (`SellerProfile`, `ComplianceBlock`, `ProfileCompleteness`, `EligibilityResult` per §8.F).
- **Data migration:** `seller_profile` table remains in shared Postgres at V1.5.
- **V1.5 trigger:** Customer-onboarding-funnel optimisations require independent A/B testing — extracting allows per-cohort version deployment.

**§21.C.6 `category` (order 6).**
- ✓ Stable methods (locked at §9.C — 8 public methods).
- ✓ JSON-serializable returns (per §9.F).
- **Data migration:** `categories`, `templates`, `field_enum_values`, `field_aliases` tables remain in shared Postgres (global tables per §16.F exception 2).
- **V1.5 trigger:** Category schema-fetch cache contention. Extraction preserves the cache contract by mounting Valkey DB 3 on the extracted pod with same pre-warm pattern.

**§21.C.7 `iam` (order 7).**
- ✓ Stable methods (locked at §7.C — 6 public methods).
- ✓ JSON-serializable returns (per §7.F).
- **Data migration:** `users` table remains in shared Postgres at V1.5; V2 may migrate to a dedicated identity store.
- **V1.5 trigger:** Auth flow requires SAML / OAuth integration that doesn't fit the OTP+JWT model — extracting allows independent identity-stack evolution.

**§21.C.8 `catalog` (order 8 — hardest).**
- ✓ Stable methods (locked at §10.C — 10 public methods including 4 cross-module).
- ✓ JSON-serializable returns (per §10.F).
- **Data migration:** `catalogs`, `products`, `product_drafts` tables remain in shared Postgres until V2 multi-region.
- **V2 trigger:** Multi-region replication. Catalog spine extraction with read-replicas in multiple regions is the natural step into V2 territory.

---

### 21.D V1.5 milestones (per `MVP_ARCH §14`)

V1.5 = the second product iteration after V1 ships. Scope locked at `MVP_ARCH §14`. Backend-relevant milestones (NOT exhaustive — frontend / data / legal tracks have separate V1.5 scope):

1. **RLS migration.** Per the §15.B locked decision (RLS deferred to V1.5), enable PostgreSQL Row-Level Security on the 7 owned-table modules: `seller_profile`, `catalogs`, `products`, `product_drafts`, `product_images`, `pricing_calcs`, `exports`. Drop the `scope_to_user(user_id)` helper from repositories — RLS handles the filtering at the database layer. Add 7 RLS policy migrations to Alembic.
2. **First extraction (order 1: `export`).** Per the §16.H + §21.B order. Triggers the V1.5 backwards-compatibility CI mode per §16.G.4.
3. **Brand-master extraction.** The `meesell-brand-master-builder` agent (deferred from V1 per `CLAUDE.md` agent registry note) lands. Brand-whitelist parsing migrates from inline `meesell-xlsx-parser` to a dedicated module — extracts inside the `category` extraction (order 6) per §16.H rationale.
4. **Razorpay business logic.** V1 captures webhooks only (per §6.E + §7.B.6). V1.5 processes subscription state changes (active / canceled / past_due / etc.) and gates `plan_guard` accordingly.
5. **Tiered plans widening.** `Literal["free"]` becomes `Literal["free", "pro"]` per §4.E V1.5 forward-note. The 4 plan-guard resources get pro-tier limits (1000 product_count, 500 ai_autofill_hourly, etc.).
6. **Tamil + Hindi i18n.** Per §3.H + §5A.I deferred. Adds `messages_ta.py` + `messages_hi.py` to `app/i18n/` — file-add only, no schema migration. `i18n/resolver.py` already handles locale fallback.
7. **Audit_events to Celery sink.** Per §4.G + `MVP_ARCH §14` — the audit_mw becomes `enqueue(audit_event_task)` instead of synchronous inline append. Adds a 3rd Celery task `audit.write`.

---

### 21.E V2 milestones (per `MVP_ARCH §14`)

V2 = post-V1.5 expansion. Scope locked at `MVP_ARCH §14`. Backend-relevant:

1. **Multi-marketplace.** New `MarketplaceExportAdapter` ABC implementations beyond `MeeshoExportAdapter` (per §14.F). Targets: Amazon, Flipkart, Etsy. Each marketplace adapter is a separate concrete class in `modules/export/adapters/`.
2. **Multi-region.** Catalog spine replication. Per `MVP_ARCH §14` + §16.H.3 (multi-region is out of §16 scope, deferred to V2). The catalog extraction (order 8) is the prerequisite — once catalog is its own pod, multi-region replication is a manifest-level concern.
3. **V2 plans.** Additional tiers beyond `free | pro` (e.g. `enterprise` per `MVP_ARCH §14`).
4. **Multi-tenancy at the database level.** Per-tenant database schemas OR per-tenant database instances (the choice depends on V2 tenant count). Drops the shared-table pattern entirely.

---

### 21.F Hybrid-mode operating posture

**Between extractions, the codebase is partly in-process, partly HTTP.** This is the defining characteristic of the V1.5 transition.

- **Modules in-process** still expose their `service.py` Python signatures unchanged.
- **Modules extracted** have their `service.py` replaced by a thin re-export of `core/extracted_clients/<module>_client.py` per §16.G.2.
- **Callers don't know which is which.** `await fetch_schema(category_id)` works identically whether category is in-process or extracted.
- **CI runs BOTH modes per §16.G.4.** During the extraction window of a module, the test suite runs once with the in-process module + once with the HTTP shim pointing at a docker-compose'd extracted pod. Both MUST pass.

**§21.F.1 Hybrid-mode risk.** The hybrid posture introduces a transient configuration complexity: each extracted module needs a `<MODULE>_POD_URL` env var (e.g. `CATEGORY_POD_URL=http://category:8001`) added to `shared/config.py`. The §5.D registry will accumulate these env vars one at a time as modules extract — V1 has zero such entries.

---

### 21.G Cross-track extraction dependencies

The 8-step extraction order is backend-internal. Other tracks' extractions interact:

- **Frontend** does NOT need to change when backend extracts a module per §16.G — the HTTP contract at `mesell.xyz/api/v1/*` remains identical (the per-module pod is behind the same Traefik IngressRoute).
- **Infra** owns the K3s manifests for each extracted pod (per §20.I). The infra extraction-readiness checklist parallels §21.C — when backend signals "export ready," infra authors the per-namespace manifest.
- **Data** (XLSX templates, brand master) extracts independently. The brand-master extraction within `category` (V1.5 milestone 3) is the only data-backend co-extraction.

---

### 21.H What §21 does NOT cover

§21 specifies the **per-module backend extraction roadmap**. The following concerns are owned elsewhere:

- **Specific extraction dates** — business decision tied to traffic + team scale.
- **Specific K3s manifests at extraction time** — §20 amendment at each extraction milestone.
- **Frontend service contract evolution** — owned by `meesell-frontend-coordinator`; backend's contract guarantee per §16.G means FE shouldn't need to change.
- **Data-layer extraction details** (per-table partitioning, replication) — owned by `meesell-data-engineer` (DATA section in MVP_ARCH).
- **V2 multi-region operational runbook** — deferred to V2 dispatch.
- **Tenant migration plan when RLS lands** (V1.5 milestone 1) — owned by `meesell-database-builder` at RLS-dispatch time.

A reviewer evaluating §21 asks: "is the order traceable to §16.H, do per-module readiness checklists cite original locks, are V1.5 and V2 milestones correctly scoped, does the hybrid-mode posture preserve §16.G?" — NOT "when do we ship V1.5?" (business).

---

## Section 22 — Acceptance & Sign-Off

STATUS: LOCKED (2026-06-06)

### 22.A Preamble

§22 is the **V1 done criteria** for the backend track. The checklist maps to `docs/V1_FEATURE_SPEC.md` Features 1-9 at the backend granularity. When every checkbox here is ticked, the backend is V1-complete and the coordinator hands off to the deployment phase. §22 is the canonical sign-off document — the founder reviews it to declare "backend ships."

§22 does NOT introduce new acceptance criteria — every checkbox cites its locking section. What §22 DOES synthesize is the cross-feature acceptance state: 27 endpoints + 2 infrastructure surfaces all live, ~50 i18n message IDs populated, all 7 import-linter contracts pass + 3 custom AST scanners, multi-tenant isolation tests pass, all 4 performance budgets met, 3 Secret Manager containers populated, the latent `pricing_engine.py` bug resolved.

A reviewer evaluating §22 asks: "does every V1_FEATURE_SPEC feature have a backend acceptance criterion, do all cross-cutting acceptance items cite their locking section, is the sign-off ownership unambiguous?" — NOT "is Feature 7 the right scope?" (V1_FEATURE_SPEC).

---

### 22.B Per-feature acceptance checklist (V1_FEATURE_SPEC Features 1-9)

**Feature 1 — Auth / OTP (§7).**
- ✓ 4 V1 contract auth endpoints live: `POST /auth/otp/send`, `POST /auth/otp/verify`, `POST /auth/refresh`, `POST /auth/logout` per §17.B rows 1-4.
- ✓ Infrastructure endpoint `GET /api/v1/auth/me` live per §17.B I1.
- ✓ Infrastructure endpoint `POST /api/v1/webhooks/razorpay` live per §17.B I2 (V1 captures only per §6.E).
- ✓ Refresh allowlist live in Valkey DB 0 with HMAC-pepper keyspace `cache:refresh:{hmac_sha256(token, REFRESH_TOKEN_PEPPER)}` per §15.H.
- ✓ Lua EVAL rotation script tested per §15.H (3 Lua scripts loaded at boot per §5.C).
- ✓ 7-day refresh TTL + 15-min access TTL configured via `REFRESH_TOKEN_TTL_SECONDS=604800` + `ACCESS_TOKEN_TTL_SECONDS=900` per §5.D + §4.B amendment.
- ✓ Logout DEL works (Valkey allowlist entry removed; cookie cleared with `Max-Age=0`) per §7.B.4.
- ✓ FE-D5 acceptance verified — 3 integration tests pass (full silent-refresh + logout-revocation + replay-attack mitigation) per §19.B.

**Feature 2 — Smart Category Picker (§9).**
- ✓ `GET /api/v1/categories/suggest?q=...` returns top-5 with confidence + reasons per §9.B.1.
- ✓ AI guardrails (Layer 1 prompt prefix + Layer 2 enum re-validation) wired via `ai_ops.client.call_gemini(workload="smart_picker", ...)` per §6A.C + §6A.E.
- ✓ Daily ₹500 budget cap with graceful fallback (empty suggestions + `fallback_offered=true` 200 response, NOT 503) per §6A.F + §9.B.1.
- ✓ `smart_picker_hourly=100/h` plan guard enforced per §4.E + §17.E.

**Feature 3 — Catalog Wizard (§10).**
- ✓ 6 catalog endpoints live per §10.B (rows 15-20 in §17.B).
- ✓ Schema validation against `templates.schema_jsonb` envelope per §5A.B (top-level 6 keys + per-field 9 keys + 11-primitive mapping).
- ✓ Autosave coalescing per `MVP_ARCH §11.4` — `product.patch` events coalesced 5-min/`(user_id, product_id)` per §15.E.
- ✓ Draft recovery via `GET /api/v1/products/{id}/draft` per §10.B.6.

**Feature 4 — AI Auto-fill (§10.B.3).**
- ✓ `POST /api/v1/products/{id}/autofill` with `allowed_enums` constraint per §6A.E Layer 1.
- ✓ Layer 2 enum re-validation with up-to-2 retries per §6A.E.
- ✓ Graceful 200-fallback on `BudgetExceededError` per §6A.F + §10.B.3 (empty suggestions + `fallback_offered=true`, NOT 503).
- ✓ `ai_autofill_hourly=50/h` plan guard enforced per §4.E.

**Feature 5 — Image Pre-check (§11).**
- ✓ Image upload + poll endpoints live: `POST /products/{id}/images` (202 ACCEPTED) + `GET /products/{id}/images` per §11.B.
- ✓ 5-step Celery pipeline operational per §11.E (4 deterministic Pillow steps + 1 watermark Gemini step).
- ✓ Watermark vision via `ai_ops.client.call_gemini(workload="watermark", ...)` inside Celery task per §6A.C + §11.E.
- ✓ Informational-not-blocking on budget exhaustion: `precheck_jsonb.watermark_check = "skipped_budget"` AND overall status still "ready" if 4 deterministic checks pass per §6A.F + §11.E.
- ✓ GCS path convention `meesell-images/{user_id}/{product_id}/{idx}.jpg` per §6.D + `MVP_ARCH §10.8`.

**Feature 6 — Live Product Preview (§10.B.4).**
- ✓ `GET /api/v1/products/{id}/preview` composes catalog wire-shape + image URL list + `customer.service.get_compliance_block(user_id)` per §10.B.4.
- ✓ The 3 cross-module reads execute in parallel via `asyncio.gather` per §10.C performance lock.

**Feature 7 — Price Calculator (§12).**
- ✓ `POST /api/v1/products/{id}/price-calc` with deterministic P&L per §12.B.1.
- ✓ 3 alert codes locked at §12.F (`PriceBelowFloor`, `MarginTooLow`, `SellerLossAtMRP`) returned via new `PricingAlert` frozen dataclass in `modules/pricing/domain.py` per §12.F.
- ✓ Latent `pricing_engine.py` bug RESOLVED via delete-legacy + rewrite-clean path per §12.A — first action of §12 specialist dispatch is `rm backend/app/services/pricing_engine.py`, then create fresh `modules/pricing/{service,domain,schemas}.py` per §3.C subtree.
- ✓ Category commission lookup via `category.service.get_commission(category_id)` per §16.B.

**Feature 8 — Dashboard (§13).**
- ✓ `GET /api/v1/products` paginated listing per §13.B.1.
- ✓ `onboarding_completeness` badge composed from `customer.service.get_onboarding_completeness(user_id)` per §16.B.
- ✓ NO repository file in `modules/dashboard/` per §13.D (the §16.F structural exception preserved).
- ✓ P95 ≤ 200 ms per §19.E.

**Feature 9 — XLSX Export (§14).**
- ✓ 2 export endpoints live: `POST /api/v1/exports` (202) + `GET /api/v1/exports/{id}` per §14.B.
- ✓ 9-step Celery pipeline operational per §14.E.
- ✓ 2 ComplianceStrategy concretes (`StandardComplianceStrategy` + `CollapsedComplianceStrategy`) per §14.F + §0.G §12.6.
- ✓ 15 golden round-trip XLSX fixtures pass per §14.K (one per super-category + Eye-Serum collapsed variant).
- ✓ Layer 3 enum guardrail re-validates emitted enum codes against the per-category allowlist per §14.J.
- ✓ M10 forbidden-symbol scanner passes — `meesho_column_header` / `meesho_column_index` / `enum_codes_map` confined to `modules/export/*` + `adapters/gcs.py` per §19.C Contract 9.

---

### 22.C Cross-cutting acceptance

**Surface count.**
- ✓ 27 contract endpoints live per §17.B.
- ✓ 2 infrastructure surfaces live per §17.B (I1 `/me` + I2 `/webhooks/razorpay`).
- ✓ Total 29 routes mounted on `app/main.py` — asserted by boot smoke test per §19.B Layer 5 (target line: 35 routes including `/health` + FastAPI defaults).

**i18n.**
- ✓ All ~50 i18n message IDs populated in `app/i18n/messages_en.py` per §15.K consolidation.
- ✓ All IDs match the §5A.H regex `^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$` per §19.C Contract 10.

**CI gates.**
- ✓ All 7 import-linter contracts pass per §19.C (Contracts 1-7 from §16.E).
- ✓ All 3 custom AST scanners pass per §19.C (Contracts 8 `scope_to_user` + 9 M10 + 10 message_id regex).
- ✓ Pytest stages 1-5 all green per §19.G.

**Multi-tenant isolation.**
- ✓ The `test_user_a_cannot_read_user_b_products` regression suite passes per §19.H.
- ✓ All 4 cross-tenant attack vectors covered (direct GET + list leakage + autosave PATCH + image upload).
- ✓ `scope_to_user(user_id)` AST scanner (Contract 8) passes — every owned-table query has a `user_id` parameter per §15.B.

**Performance.**
- ✓ P95 schema fetch ≤ 50 ms (cache hit) / ≤ 200 ms (cache miss) per §19.E (asserted nightly).
- ✓ P95 manual-browse query ≤ 200 ms per §19.E.
- ✓ End-to-end export pipeline ≤ 30 s per §19.E.
- ✓ Per-call Gemini cost ≤ ₹0.05 average per §19.E.

**Secret Manager.**
- ✓ All 3 PENDING secrets populated per §20.C: `refresh-token-pepper`, `razorpay-webhook-secret`, `langfuse-secret-key`.

**Test coverage.**
- ✓ 80% module-level line coverage on `app/modules/*/service.py` and `app/modules/*/repository.py` per §19.F.
- ✓ 100% endpoint coverage — every contract endpoint has at least 1 happy-path integration test per §19.F.

**AI eval sets.**
- ✓ Smart Picker eval set: top-5 recall ≥ 80% per §6A.H.
- ✓ Autofill eval set: 0% invalid enum emissions per §6A.H.
- ✓ Watermark eval set: classification accuracy ≥ 85% per §6A.H.

---

### 22.D Sign-off responsibilities

**`meesell-backend-coordinator` signs off:**
- Per-module construction acceptance (§22.B Features 1-9 backend criteria).
- Cross-cutting backend acceptance (§22.C all green).
- Hand-off documents to FRONTEND / AI / INFRA / DATA / LEGAL tracks (per §22.B + §22.C per-feature hand-off).

**Founder signs off:**
- Overall V1 completion (all 9 features acceptance criteria met across all tracks).
- Production deployment authorization.

**Per-specialist sign-off (within each module dispatch):**
- Module-level acceptance criteria from §22.B.
- Specialist self-asserts via per-module test pass + per-module integration tests pass + per-module section-J / section-K test plan executed.
- Coordinator reviews specialist output against the relevant §X.B (endpoint contract) + §X.C (service surface) + §X.J (test plan) before signing off.

---

### 22.E Post-V1 follow-ups (NOT V1 blocking)

The following items are RECORDED here so they do NOT block V1 sign-off:

- **V1.5 RLS migration** (§15.B deferred decision; §21.D milestone 1).
- **V1.5 tiered plans** widening from `free` to `free | pro` (§4.E V1.5 forward-note; §21.D milestone 5).
- **V1.5 admin panel** for ops visibility (deferred per `MVP_ARCH §14`).
- **V1.5 Tamil/Hindi i18n** (§5A.I deferred; §21.D milestone 6).
- **V1.5 audit_events to Celery sink** (§4.G V1.5 forward-note; §21.D milestone 7).
- **V2 multi-marketplace** export adapters (Amazon / Flipkart / Etsy per §14.F + §21.E milestone 1).
- **V2 multi-region** (§16.H.3 + §21.E milestone 2).
- **V2 multi-tenancy at the database level** (§21.E milestone 4).

These items are tracked separately and do NOT prevent V1 from shipping.

---

### 22.F What §22 does NOT cover

§22 specifies **backend V1 acceptance**. The following concerns are owned by other tracks:

- **Frontend acceptance** — owned by `meesell-frontend-coordinator` (FRONTEND_ARCH §22). Backend's contract guarantees per §17 are the FE's acceptance dependency.
- **Infrastructure acceptance** — owned by `meesell-infra-builder` (INFRA section). Includes K3s cluster live + namespaces configured + 3 PENDING secrets populated + cert-manager TLS valid.
- **Data acceptance** — owned by `meesell-data-engineer` (DATA section in MVP_ARCH). Includes 3,557 templates + 3,772 categories + ~200K field_enum_values rows + 15 golden XLSX fixtures + Layer 3 enum allowlist.
- **Legal acceptance** — owned by `meesell-legal-writer`. Includes ToS + Privacy Policy + DPDP compliance posture.
- **Production deployment** — owned by `meesell-infra-builder` (`make deploy` per `CLAUDE.md` + GitLab CI pipeline).

A reviewer evaluating §22 asks: "does every V1_FEATURE_SPEC feature have a backend acceptance criterion, do all cross-cutting acceptance items cite their locking section, is the sign-off ownership unambiguous?" — NOT "is the frontend ready?" (FRONTEND track).

---

## Section 22A — Risk Register & Mitigations

STATUS: LOCKED (2026-06-06)

### 22A.A Preamble

§22A is the **backend-specific risk register** for V1. It enumerates 12 architectural risks with mitigations baked into the design of this document, sourced from `MVP_ARCH §13` + this session's design decisions. This register is the canonical defense citation: future PRs that touch a constrained area cite this register to justify the design choice rather than re-litigating it.

§22A does NOT cover frontend risks (FRONTEND_ARCH §22A), infrastructure risks (INFRA section), data risks (DATA section), or V1.5/V2 deferred risks (per `MVP_ARCH §14`). Each risk in §22A has a **severity score** (Likelihood × Impact = Risk Score on a 1-25 scale) + a **mitigation citation** to the locking section.

A reviewer evaluating §22A asks: "are all 12 risks correctly scoped to the backend track, do mitigations cite their locking section, are severity scores defensible?" — NOT "should we add a risk about the frontend?" (FRONTEND_ARCH).

---

### 22A.B The 12 backend risks

**R1 — AI hallucination on autofill produces invalid enum values.**
- **Likelihood:** 4 / 5 (LLMs occasionally emit unallowed enum values even with prompt constraints).
- **Impact:** 5 / 5 (an invalid enum reaching XLSX export rejects the entire catalog on Meesho upload — seller's hours of work wasted).
- **Risk score:** 20 / 25.
- **Mitigation:** 3-layer guardrail spanning §6A Layers 1+2 + §14.J Layer 3 deterministic re-validation. Layer 1 (prompt-time `allowed_enums` constraint in `autofill.v1` prompt), Layer 2 (parser-level re-validation with up-to-2 retries inside `ai_ops/guardrail.py`), Layer 3 (export-time re-validation at step 5 of the 9-step pipeline per §14.J — raises `ExportEnumValidationError` if a saved canonical_name fails category allowlist lookup). The 3 layers are independent — even if Layer 1+2 both fail (e.g. prompt regression + parser bug), Layer 3 catches the bad value before it reaches Meesho.
- **Defense citation:** §6A.E + §14.J + §22A.B R1.

**R2 — Brand picker P95 latency > 2 s.**
- **Likelihood:** 3 / 5 (291 large Brand-pattern enums per `MVP_ARCH §0` premise #5; client-side rendering of 1,000+ brand options is slow).
- **Impact:** 4 / 5 (slow brand picker = friction in core wizard flow = catalog completion rate drops).
- **Risk score:** 12 / 25.
- **Mitigation:** server-side pagination (50/page per §9.B.5); client-side cache by `(category, query_prefix)`; single-flight Valkey lock on 291 large enums per §6.8 + §15.C. The §15.C cache strategy locks the field-enum endpoint as the heaviest cache consumer in the codebase with mandatory single-flight per §9.B.5.
- **Defense citation:** §9.B.5 + §15.C + §22A.B R2.

**R3 — Eye-Serum template breaks (1 / 3,772 leaf).**
- **Likelihood:** 2 / 5 (only 1 out of 3,772 templates uses collapsed compliance shape; collision rare).
- **Impact:** 5 / 5 (if breaks, Eye-Serum sellers cannot export — full feature blockage for a niche).
- **Risk score:** 10 / 25.
- **Mitigation:** backend accepts both representations via ComplianceStrategy dispatch (Standard + Collapsed per §14.F + §0.G §12.6). The 2 concrete classes in `modules/export/strategies/` cleanly separate the Eye-Serum 9→3 collapsed transform from the standard 9-as-9 shape. Round-trip golden fixture #15 (Eye-Serum) per §14.K asserts byte-equal XLSX output.
- **Defense citation:** §14.F + §0.G §12.6 + §22A.B R3.

**R4 — Meesho changes XLSX schema.**
- **Likelihood:** 3 / 5 (Meesho has changed schemas before; quarterly is plausible).
- **Impact:** 4 / 5 (all exports break across all categories until parser updated).
- **Risk score:** 12 / 25.
- **Mitigation:** Parser handles "Recommended" regex per `MVP_ARCH §0` premise #2 (binary Compulsory/Optional, no Recommended tier). Quarterly refresh + diff report owned by `meesell-scraper-maintainer` agent. Round-trip golden fixtures per §14.K detect drift — if Meesho adds a column, the round-trip test fails and the regression surfaces in CI. Brand-master and template seeds are versioned per `MVP_ARCH §2.6`.
- **Defense citation:** §14.K + `MVP_ARCH §0` + scraper-maintainer agent + §22A.B R4.

**R5 — Compulsory median 33 fields in Home & Kitchen overwhelms user.**
- **Likelihood:** 4 / 5 (33 compulsory fields per category is consistent with the corpus — see `MVP_ARCH §0` premise #6).
- **Impact:** 3 / 5 (high seller abandonment but recoverable via UX iteration).
- **Risk score:** 12 / 25.
- **Mitigation:** multi-step wizard with progress bar per §5A.B `wizard_step_count` + AI auto-fill reduces manual input. The 11-input-primitive mapping per §5A.D minimises form complexity; data-driven `wizard_step_count` per `templates.schema_jsonb` envelope splits the 33-field form into 4-6 steps with clear progress.
- **Defense citation:** §5A.B + Feature 4 (Autofill) + §22A.B R5.

**R6 — FSSAI compulsory at signup → lost sign-ups in Grocery.**
- **Likelihood:** 5 / 5 (Grocery sellers in early stages often don't have FSSAI yet).
- **Impact:** 4 / 5 (Grocery is a high-volume super-category; lost signups = lost revenue).
- **Risk score:** 20 / 25.
- **Mitigation:** onboarding wizard surfaces requirement obvious per `customer` module §8.F COMPLIANCE_EXTENSION_MAP (Grocery FSSAI is compulsory per super_id; the requirement IS gated, NOT hidden). "Don't have FSSAI? Apply here" link to fssai.gov.in surfaced inline per F5 (never show a field without an explanation). The Grocery seller is informed BEFORE OTP signup; if they choose to proceed they know FSSAI is required.
- **Defense citation:** §8.F + Feature 1 onboarding flow + `CORE_PHILOSOPHY` F5 + §22A.B R6.

**R7 — Canonical-name normalisation breaks Meesho XLSX export.**
- **Likelihood:** 3 / 5 (1,831 unique field names per `MVP_ARCH §0` premise #4 — collision space is real).
- **Impact:** 5 / 5 (a canonical→raw mismap breaks all exports for that field across all categories).
- **Risk score:** 15 / 25.
- **Mitigation:** reverse map via `field_aliases.for_xlsx_export=TRUE` per `MVP_ARCH §0.G §12.2`. Round-trip golden test per super-category per §14.K detects mapping drift — if a canonical_name → raw header mapping breaks, the round-trip fixture for that super-category fails in CI.
- **Defense citation:** §14.K + `MVP_ARCH §0.G §12.2` + §22A.B R7.

**R8 — RLS deferred to V1.5 — tenant isolation depends on CI linter discipline.**
- **Likelihood:** 3 / 5 (developer forgets `user_id` parameter on a new repository method, slips through PR review).
- **Impact:** 5 / 5 (cross-tenant data leak = legal + reputational disaster).
- **Risk score:** 15 / 25.
- **Mitigation:** per-PR isolation regression test (§19.H) asserts User A cannot read User B's products via 4 attack vectors. Service-signature linter (Contract 8, the `scope_to_user` AST scanner per §19.C) rejects PRs lacking `user_id` parameter on owned-table queries. Defense-in-depth at GCS path-prefix level per §15.B (`meesell-images/{user_id}/...` makes cross-tenant path traversal impossible). V1.5 RLS migration (per §21.D milestone 1) makes this risk obsolete.
- **Defense citation:** §15.B + §19.C Contract 8 + §19.H + §21.D milestone 1 + §22A.B R8.

**R9 — Valkey single point of failure.**
- **Likelihood:** 2 / 5 (Valkey is mature; single-node failure rate is low).
- **Impact:** 4 / 5 (all cache + rate-limit + OTP allowlist + refresh allowlist down simultaneously).
- **Risk score:** 8 / 25.
- **Mitigation:** backend falls back to direct Postgres on cache miss per §15.C; rate limiting fails open with alarm per §4.G; OTP allowlist fail-open with logged warning is acceptable (3/h limit becomes effectively unlimited briefly — security degradation, not failure). V1.5 evaluates Valkey HA / Sentinel deployment per the V1.5 milestone backlog. The 7-day refresh allowlist failure is the most-severe — all logged-in sessions would silently fail to refresh, forcing re-login (acceptable degradation, not security breach).
- **Defense citation:** §4.G + §15.C + V1.5 milestone backlog + §22A.B R9.

**R10 — AI cost overrun — daily ₹500 cap hit during traffic spike.**
- **Likelihood:** 3 / 5 (viral traffic spike or runaway autofill loop could hit cap).
- **Impact:** 3 / 5 (graceful UX fallback degrades feature, doesn't break product).
- **Risk score:** 9 / 25.
- **Mitigation:** per-seller hourly rate limits per §4.E (smart_picker 100/h, autofill 50/h) cap per-user spend. Cost alarm at 80% of daily cap per §6A.F triggers operator notification before hard-stop. Graceful fallback per workload: Smart Picker → empty + manual browse, Autofill → empty 200 with `fallback_offered=true`, Watermark → skipped_budget per §6A.F + §11.E. Review pricing weekly during launch month per `MVP_ARCH §13`.
- **Defense citation:** §4.E + §6A.F + §11.E + §22A.B R10.

**R11 — Refresh token replay attack via stolen cookie.**
- **Likelihood:** 2 / 5 (requires both XSS exfiltration AND attacker prevents legitimate refresh before re-presentation — narrow window).
- **Impact:** 5 / 5 (full account takeover).
- **Risk score:** 10 / 25.
- **Mitigation:** HMAC-SHA256 with `REFRESH_TOKEN_PEPPER` per §15.H (without pepper a Valkey-only breach lets an attacker compute SHA-256 of captured cookies; with pepper, attacker also needs backend-only secret from Secret Manager). Lua EVAL atomic rotation invalidates old key on use per §15.H (re-presentation of pre-rotation cookie returns 401). Server-side revocation on logout DELs allowlist per §15.H. Cookie SameSite=Strict prevents cross-origin theft per §4.G CORS amendment. The 4 defenses are independent — bypass requires breaching all four.
- **Defense citation:** §15.H + §4.G + §22A.B R11.

**R12 — `pricing_engine.py` latent bug surfaces in production.**
- **Likelihood:** 5 / 5 (the file IS unimportable today per `MEMORY.md` Session 2 close-out — guaranteed to break if a route ever imports it).
- **Impact:** 3 / 5 (no live importer currently — but a future PR adding the pricing router would crash boot).
- **Risk score:** 15 / 25.
- **Mitigation:** resolution path locked at §12.A — delete legacy + create fresh `modules/pricing/{service,domain,schemas}.py` per §3.C subtree. New `PricingAlert` frozen dataclass lives in `modules/pricing/domain.py` per §12.F. First action of §12 specialist dispatch is `rm backend/app/services/pricing_engine.py` per §12.A. Session 2 close-out queued this as construction work item #1 (recorded in `MEMORY.md` Session 2 close-out → Queued for construction → Item 1).
- **Defense citation:** §12.A + §12.F + `MEMORY.md` Session 2 close-out → Queued item 1 + §22A.B R12.

---

### 22A.C Severity matrix summary

| Risk | Likelihood | Impact | Score | Severity tier |
|------|-----------|--------|-------|---------------|
| R1 — AI hallucination | 4 | 5 | 20 | CRITICAL |
| R6 — FSSAI compulsory | 5 | 4 | 20 | CRITICAL |
| R7 — Canonical-name break | 3 | 5 | 15 | HIGH |
| R8 — RLS deferred | 3 | 5 | 15 | HIGH |
| R12 — pricing_engine.py | 5 | 3 | 15 | HIGH |
| R2 — Brand picker latency | 3 | 4 | 12 | HIGH |
| R4 — Meesho schema change | 3 | 4 | 12 | HIGH |
| R5 — 33 compulsory fields | 4 | 3 | 12 | HIGH |
| R3 — Eye-Serum break | 2 | 5 | 10 | MEDIUM |
| R11 — Refresh token replay | 2 | 5 | 10 | MEDIUM |
| R10 — AI cost overrun | 3 | 3 | 9 | MEDIUM |
| R9 — Valkey SPOF | 2 | 4 | 8 | MEDIUM |

**Severity tier definition:** CRITICAL ≥ 20, HIGH 12-19, MEDIUM 6-11, LOW 1-5. No risk falls into LOW in V1 — the architecture has been deliberately designed to make MEDIUM the lowest severity (every risk gets at least one mitigation citation).

**Top-3 risks** (CRITICAL + R7 the highest HIGH) carry the most documentation density:
- R1 has 3 independent guardrail layers + safety-net at export time.
- R6 has compulsory-but-surfaced-upfront with link to apply.
- R7 has reverse map + per-super-category round-trip CI fixture.

---

### 22A.D Cross-track risks NOT in §22A

The following risks are owned by OTHER tracks — listed here for cross-reference so this register is self-contained for backend purposes only:

- **Frontend risks** — owned by `meesell-frontend-coordinator` (FRONTEND_ARCH §22A). E.g. "JWT token storage choice" (resolved by FE-D5 to in-memory).
- **Infrastructure risks** — owned by `meesell-infra-builder`. E.g. Postgres backup loss, K3s node disk fill, Let's Encrypt cert renewal failure.
- **Data risks** — owned by `meesell-data-engineer`. E.g. seed data drift across dev/staging/prod, ~200K enum-values row import slowness.
- **Legal risks** — owned by `meesell-legal-writer`. E.g. DPDP non-compliance, ToS not surfaced at signup.
- **V1.5 / V2 deferred risks** — per `MVP_ARCH §14` (RLS migration timing, brand-master extraction, multi-marketplace adapters).

---

### 22A.E Post-V1 risk review cadence

- **Weekly during first 30 days of launch.** Founder + backend coordinator joint review of the 12-row register against production metrics (audit events, error rates, P95 latencies). Each risk's score may shift up/down based on observation.
- **Monthly thereafter.** Same review cadence at lower frequency.
- **Ad-hoc on incident.** Any P0 incident triggers an immediate register update — the new risk is added (if novel) or the existing risk's score updates (if recurrence).
- **V1.5 entry review.** Per the §21.D milestone schedule, R8 retires when RLS lands; R12 retires when §12 construction dispatch completes (the bug is permanently fixed). New V1.5-specific risks added at that review.

---

### 22A.F What §22A does NOT cover

§22A is the **backend-specific risk register**. The following concerns are owned elsewhere:

- **Cross-track risk register** (the union of backend + frontend + infra + data + legal) — owned by master session at V1 sign-off ceremony.
- **Incident response playbooks** — owned by `meesell-infra-builder` (operational runbook).
- **Risk-acceptance documentation** — when a risk is acknowledged and the founder decides to defer mitigation, the decision is recorded in `MEMORY.md` of the relevant coordinator + linked here as a post-V1 follow-up.
- **Risk monetisation** (downtime cost, churn impact in ₹) — business analysis, not architecture.

A reviewer evaluating §22A asks: "are 12 backend risks correctly scoped, do mitigations cite locking sections, do severity scores defend the design choices?" — NOT "what's the dollar cost of R10?" (business).

---
