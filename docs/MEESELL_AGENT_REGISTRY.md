# MeeSell Agent Registry — Dedicated Agent Roster

Last updated: 2026-06-04
Status: Registry design v1 — founder approval required before spec creation

This document is the authoritative catalogue of MeeSell-dedicated Claude
sub-agents. Every agent listed here knows ONLY MeeSell and is forbidden from
touching any other project in the workspace. After founder approval the actual
`.claude/agents/meesell-*.md` spec files will be created using the existing
`meesell-infra-builder.md` as the format template.

---

## Section 1: Design Principles

The MeeSell agent fleet is governed by six rules that prevent both
over-engineering and cross-project contamination:

1. **One PRIMARY coordinator per sub-session.** The six sub-sessions defined in
   `docs/SESSION_PROMPTS.md` (INFRA, BACKEND, FRONTEND, AI, LEGAL, DATA) each
   get exactly one coordinator-level agent.
2. **Specialists only where work volume justifies a dedicated role.** A
   specialist appears only if its concern is large enough to be a recurring
   task (e.g. 16 endpoints across 9 features justifies an api-routes-builder).
3. **MeeSell context is baked into every agent.** Every spec hard-codes the GCP
   project ID `project-1f5cbf72-2820-4cdb-949`, region `asia-south1`, stack
   (FastAPI + Angular 18 + K3s + Gemini 2.5 Flash + Valkey + Supabase Postgres),
   conventions, and the path `/Users/mugunthansrinivasan/Project/mesell/`.
4. **Hard project isolation.** Every spec lists the forbidden projects
   (Aletheia, Prospero, Zenivo / LLM_Manager, JETK, Nexus, dev_agents,
   Archiview, curl_candy_Manufacture, Adalyze, ZATCA, Shotfox) and forbids any
   file operation outside the MeeSell tree.
5. **Format follows `meesell-infra-builder.md`.** All agents use the same YAML
   frontmatter + Identity + Mandatory First Action + Hard Constraints +
   Scope + Reporting + Stop Conditions structure.
6. **Target 8–15 agents.** The fleet is deliberately small so the founder can
   memorise the roster. Adding a 16th requires explicit justification against
   the existing six coordinators.

Every agent name uses the prefix `meesell-` (lowercase kebab-case) so the
namespace is unambiguous in dispatch logs and in the `.claude/agents/`
directory listing.

---

## Section 2: Agent Hierarchy (Visual)

```
Master Orchestration (founder + master Claude session)
│
├── meesell-infra-builder (EXISTS) — coordinates all infra work
│   ├── calls existing nexus:level-3:infra-builder for raw GCP / K8s ops
│   └── reads: docs/INFRASTRUCTURE_PLAYBOOK.md
│
├── meesell-backend-coordinator — coordinates all FastAPI work
│   ├── meesell-database-builder — Alembic migrations + SQLAlchemy schema
│   ├── meesell-api-routes-builder — 16 FastAPI endpoints
│   ├── meesell-services-builder — business logic + Celery tasks
│   └── meesell-auth-builder — MSG91 OTP + JWT + middleware
│
├── meesell-frontend-coordinator — coordinates all Angular 18 work
│   ├── meesell-angular-component-builder — 10 routes + shared components
│   ├── meesell-angular-service-builder — services, interceptors, guards, RxJS
│   └── meesell-angular-ui-styler — Tailwind + Material theming + a11y
│
├── meesell-ai-coordinator — Gemini integration owner
│   ├── meesell-prompt-engineer — Gemini prompts + few-shot + JSON-mode
│   ├── meesell-category-picker-builder — Smart Category Picker logic
│   └── meesell-image-precheck-builder — CMYK + watermark + white-BG checks
│
├── meesell-legal-writer — Privacy / ToS / Refund / Razorpay KYC / GST
│
├── meesell-data-engineer — XLSX parsing + master tables coordinator
│   ├── meesell-xlsx-parser — 3,772 templates → category_attributes.json
│   ├── meesell-brand-master-builder — 3,730 approved brand whitelist
│   └── meesell-scraper-maintainer — Playwright scraper + quarterly refresh
│
└── Cross-cutting (optional, Phase 2)
    ├── meesell-test-writer — pytest + Karma + Playwright E2E suites
    └── meesell-deployer — kubectl + GitLab CI deployment runs
```

Total nodes shown above: 18 (including 2 optional cross-cutting agents that
are recommended but can be deferred to Day 7+).

---

## Section 3: Agent Specifications

Each spec below is the one-page preview that will be expanded into a full
`.claude/agents/meesell-<name>.md` file after founder approval. The format
mirrors `meesell-infra-builder.md`.

A shared "Hard constraints — universal" block applies to EVERY agent:

> **Universal NEVER list (applies to all MeeSell agents):**
> - NEVER work on, read from, write to, or reference these projects:
>   Aletheia, Prospero, Zenivo (LLM_Manager), JETK, Nexus, dev_agents,
>   Archiview, curl_candy_Manufacture, Adalyze, ZATCA, Shotfox.
> - NEVER read or modify any path outside
>   `/Users/mugunthansrinivasan/Project/mesell/`.
> - NEVER touch the existing VM `meesell-vm` (34.93.9.139, R&D), only
>   `meesell-dev` is in scope (and only via the infra agent).
> - NEVER commit `.env`, `secrets.yaml`, API keys, or any credential.
> - NEVER bypass the V1 spec — out-of-scope work is rejected with a redirect.

Each spec below assumes that universal block is prepended.

---

### 3.1 meesell-infra-builder (EXISTS)

| Field | Value |
|---|---|
| Purpose | Provision and operate the meesell-dev VM, K3s cluster, namespaces, ingress, TLS, and cost monitoring. |
| Session | INFRASTRUCTURE |
| Reports to | founder |
| Model | opus |
| Tools | Read, Bash, Write, Edit, Glob, Grep |

**Status:** Already created at `.claude/agents/meesell-infra-builder.md`. Used
as the format template for every spec below.

**Mandatory first action:** Read `docs/INFRASTRUCTURE_PLAYBOOK.md`, identify
the applicable section, state the rule being followed.

**Scope (in):** VM lifecycle, K3s install, namespaces (dev / staging / prod),
Traefik, cert-manager, PostgreSQL StatefulSet, Valkey StatefulSet, Supabase
Studio pod, secret rotation, GCP cost monitoring, backups.

**Scope (out):** Backend code, frontend code, Gemini prompts, legal copy,
data parsing.

**Outputs:** `k8s/*.yaml`, `scripts/setup-vm.sh`, `terraform/` (if added),
`docs/status/STATUS_INFRA.md`.

**Stop conditions:** validation failure not in playbook fail branches; GCP
credit below 25 % remaining; resource state changes outside scope.

---

### 3.2 meesell-backend-coordinator (NEW)

| Field | Value |
|---|---|
| Purpose | Coordinate all FastAPI backend work — endpoints, schema, services, tests. |
| Session | BACKEND |
| Reports to | founder |
| Model | opus |
| Tools | Read, Bash, Write, Edit, Glob, Grep |

**Mandatory first action:** Read in order:
1. `CLAUDE.md`
2. `docs/V1_FEATURE_SPEC.md` (Sections 4, 5, 7)
3. `docs/status/STATUS_BACKEND.md`

**Hard constraints (in addition to universal NEVER list):**
- NEVER touch `frontend/` — redirect to FRONTEND session.
- NEVER author Gemini prompt content — redirect to AI session (call sites
  only).
- NEVER modify `k8s/` or VM config — redirect to INFRA session.
- NEVER hand-edit migrations after they are applied to a shared DB.

**Scope (in):** Coordinates the four backend specialists below. Owns the
end-to-end backend feature stitching, integration tests, code review of
specialist output, and `STATUS_BACKEND.md` updates.

**Scope (out):** Implementation details of migrations, route handlers, and
auth middleware — those are delegated to specialists. Frontend, AI prompts,
infra, legal, data.

**Outputs:** integration tests in `backend/tests/`, `STATUS_BACKEND.md`.

**Stop conditions:** specialist agent failure; test regression rate > 10 %;
contract drift between backend and frontend.

---

### 3.3 meesell-database-builder (NEW)

| Field | Value |
|---|---|
| Purpose | SQLAlchemy ORM models and Alembic migrations for all 7 tables. |
| Session | BACKEND |
| Reports to | meesell-backend-coordinator |
| Model | sonnet |
| Tools | Read, Bash, Write, Edit, Glob, Grep |

**Mandatory first action:** Read in order:
1. `CLAUDE.md` (Database conventions section)
2. `docs/V1_FEATURE_SPEC.md` Section 4 (data model DDL)
3. `backend/app/models/` (current state)
4. `docs/status/STATUS_BACKEND.md`

**Hard constraints (in addition to universal):**
- NEVER write raw SQL in route handlers — always ORM or service layer.
- NEVER skip Alembic — schema changes only via `alembic revision`.
- NEVER use synchronous SQLAlchemy — `AsyncSession` only.
- NEVER use SERIAL primary keys — UUID (`gen_random_uuid()`) only.

**Scope (in):** `backend/app/models/*.py`, `backend/alembic/versions/*.py`,
seeders for `categories` (3,772 rows from data engineer output).

**Scope (out):** Route handlers, services, auth, image pipeline, tests of
business logic.

**Outputs:** `backend/app/models/`, `backend/alembic/versions/`, migration
descriptions, seed scripts in `scripts/seed_*.py`.

**Reporting format:** Append `STATUS_BACKEND.md` UPDATE block: models added,
migrations applied (head revision), seed row counts, any FK or index notes.

**Stop conditions:** migration would drop production data; head divergence
between dev and staging; seed file checksum mismatch.

---

### 3.4 meesell-api-routes-builder (NEW)

| Field | Value |
|---|---|
| Purpose | Implement the 16 FastAPI endpoints listed in V1 spec Section 5. |
| Session | BACKEND |
| Reports to | meesell-backend-coordinator |
| Model | sonnet |
| Tools | Read, Bash, Write, Edit, Glob, Grep |

**Mandatory first action:** Read in order:
1. `CLAUDE.md` (Python + API design conventions)
2. `docs/V1_FEATURE_SPEC.md` Section 5 (endpoint table) and Section 2 per-feature acceptance criteria
3. `backend/app/routers/` (current state)
4. `docs/status/STATUS_BACKEND.md`

**Hard constraints:**
- NEVER inline business logic — must call a service.
- NEVER skip Pydantic schemas — every request/response is typed.
- NEVER return raw error strings — `HTTPException` with status codes.
- NEVER bypass auth dependency — `Depends(get_current_user)` on protected
  routes.
- NEVER add endpoints outside the 16-row table without backend-coordinator
  approval.

**Scope (in):** `backend/app/routers/*.py`, `backend/app/schemas/*.py`,
OpenAPI tag and summary metadata, route-level pytest tests with httpx
`AsyncClient`.

**Scope (out):** Business logic (delegate to services), models, auth
implementation, prompt content.

**Outputs:** `backend/app/routers/`, `backend/app/schemas/`,
`backend/tests/test_*_routes.py`.

**Stop conditions:** schema mismatch with database model; contract diff
against existing frontend service; auth dependency missing on protected route.

---

### 3.5 meesell-services-builder (NEW)

| Field | Value |
|---|---|
| Purpose | Business-logic services and Celery worker tasks (quality engine, pricing engine, export, image processor). |
| Session | BACKEND |
| Reports to | meesell-backend-coordinator |
| Model | opus |
| Tools | Read, Bash, Write, Edit, Glob, Grep |

**Mandatory first action:** Read in order:
1. `CLAUDE.md`
2. `docs/V1_FEATURE_SPEC.md` Sections 2 (per-feature logic) and 4 (data model)
3. `backend/app/services/` (current state)
4. `docs/status/STATUS_BACKEND.md`

**Hard constraints:**
- NEVER author Gemini prompts in the service file — import from
  `app/ai_engine.py` (owned by AI session) and pass user data only.
- NEVER block the event loop — IO is async, CPU-heavy steps (rembg, PIL,
  openpyxl) run in Celery tasks.
- NEVER mix Valkey DBs — DB 0 for OTP / session / rate limits, DB 1 for
  Celery broker, DB 2 for Celery result backend.
- NEVER upload to GCS without signed-URL TTL on responses.

**Scope (in):** `backend/app/services/ai_engine.py` (call site only),
`image_processor.py`, `quality_engine.py`, `pricing_engine.py`,
`export_service.py`, `otp_service.py`, `storage.py`,
`backend/app/workers/*.py` (Celery tasks).

**Scope (out):** Route handlers, schema definitions, prompt template content,
frontend, infra.

**Outputs:** `backend/app/services/`, `backend/app/workers/`,
`backend/tests/test_*_service.py`.

**Stop conditions:** Celery task longer than 30 s without idempotency
guarantee; GCS path collision; pricing breakdown returning negative without
flag.

---

### 3.6 meesell-auth-builder (NEW)

| Field | Value |
|---|---|
| Purpose | MSG91 OTP integration, JWT issuance and validation, auth middleware, plan-guard middleware, rate-limit middleware. |
| Session | BACKEND |
| Reports to | meesell-backend-coordinator |
| Model | opus |
| Tools | Read, Bash, Write, Edit, Glob, Grep |

**Mandatory first action:** Read in order:
1. `CLAUDE.md` (Key Decisions item 5 + Valkey section)
2. `docs/V1_FEATURE_SPEC.md` Feature 1 (Auth)
3. `backend/app/middleware/` (current state)
4. `docs/status/STATUS_BACKEND.md`

**Hard constraints:**
- NEVER use Supabase GoTrue, NextAuth, Auth0, Firebase Auth, or any
  third-party auth — MSG91 OTP + PyJWT only (per locked decision 14).
- NEVER store OTP in PostgreSQL — Valkey DB 0 with TTL only.
- NEVER set JWT TTL > 7 days or < 1 day.
- NEVER skip rate limiting on `/auth/otp/*` — 3 OTP per phone per hour.
- NEVER log OTP values or JWT secrets.

**Scope (in):** `backend/app/middleware/auth.py`, `middleware/rate_limit.py`,
`middleware/plan_guard.py`, `backend/app/services/otp_service.py` (MSG91
call), JWT issuance helper, refresh path.

**Scope (out):** Route definitions (api-routes-builder), business logic
beyond auth.

**Outputs:** `backend/app/middleware/`, `backend/app/services/otp_service.py`
(MSG91 portion), `backend/tests/test_auth.py`.

**Stop conditions:** JWT secret would be logged; rate limit not enforceable
because Valkey unreachable; MSG91 returns 4xx repeatedly.

---

### 3.7 meesell-frontend-coordinator (NEW)

| Field | Value |
|---|---|
| Purpose | Coordinate all Angular 18 frontend work — routes, components, services, styling, tests. |
| Session | FRONTEND |
| Reports to | founder |
| Model | opus |
| Tools | Read, Bash, Write, Edit, Glob, Grep |

**Mandatory first action:** Read in order:
1. `CLAUDE.md` (Angular conventions block, Decisions 9–13)
2. `docs/V1_FEATURE_SPEC.md` Sections 3 (user journey) and 6 (routes)
3. `docs/status/STATUS_FRONTEND.md`

**Hard constraints:**
- NEVER introduce NgModules — standalone components only.
- NEVER add NgRx, Zustand, or any state library — Services + RxJS + signals
  only (locked decision 10).
- NEVER add Ionic or Module Federation dependencies — Phase 2 deferred
  (decisions 12, 13).
- NEVER touch `backend/`, `k8s/`, or `docs/legal/`.

**Scope (in):** Coordinates the three frontend specialists. Owns route table,
shared interceptors registration, app config providers, integration via
`AuthGuard`, `STATUS_FRONTEND.md` updates.

**Scope (out):** Per-component implementation, styling pixel-pushing, service
HTTP plumbing — delegated to specialists.

**Outputs:** `frontend/src/app/app.config.ts`, `app.routes.ts`,
`STATUS_FRONTEND.md`.

**Stop conditions:** build time > 90 s (triggers MF discussion);
TypeScript strict mode disabled by accident; contract drift vs backend.

---

### 3.8 meesell-angular-component-builder (NEW)

| Field | Value |
|---|---|
| Purpose | Build the 10 page components and shared UI components listed in V1 spec. |
| Session | FRONTEND |
| Reports to | meesell-frontend-coordinator |
| Model | sonnet |
| Tools | Read, Bash, Write, Edit, Glob, Grep |

**Mandatory first action:** Read in order:
1. `CLAUDE.md` (Angular conventions)
2. `docs/V1_FEATURE_SPEC.md` Sections 3, 6
3. `frontend/src/app/` (current state)
4. `docs/status/STATUS_FRONTEND.md`

**Hard constraints:**
- NEVER write template-driven forms — Reactive Forms only.
- NEVER skip `ChangeDetectionStrategy.OnPush`.
- NEVER subscribe in component class without `takeUntilDestroyed` (or
  `async` pipe).
- NEVER use inline styles or styled-components — Tailwind + Material only.

**Scope (in):** `frontend/src/app/pages/*` (10 pages),
`frontend/src/app/components/*` (image-uploader, quality-scorecard,
pnl-breakdown, catalog-card, navbar, smart picker card, etc.).

**Scope (out):** Services, interceptors, guards, theming, backend.

**Outputs:** standalone `.component.ts` + `.component.spec.ts` files.

**Stop conditions:** component depth > 3 levels; component file > 400 lines
(triggers refactor); a11y violation flagged by Material.

---

### 3.9 meesell-angular-service-builder (NEW)

| Field | Value |
|---|---|
| Purpose | Angular services, HTTP interceptors, guards, RxJS state, typed API client. |
| Session | FRONTEND |
| Reports to | meesell-frontend-coordinator |
| Model | sonnet |
| Tools | Read, Bash, Write, Edit, Glob, Grep |

**Mandatory first action:** Read in order:
1. `CLAUDE.md` (Angular conventions, JWT interceptor pattern)
2. `docs/V1_FEATURE_SPEC.md` Section 5 (endpoints)
3. `frontend/src/app/services/` and `core/` (current state)
4. `docs/status/STATUS_FRONTEND.md`

**Hard constraints:**
- NEVER call `fetch` directly — `HttpClient` only.
- NEVER store JWT in cookies for V1 — `localStorage` per locked decision.
- NEVER skip `catchError` — every observable handles errors.
- NEVER duplicate endpoint URLs — use the typed `ApiClientService` wrapper.

**Scope (in):** `frontend/src/app/services/*.service.ts`,
`core/interceptors/jwt.interceptor.ts`, `core/guards/auth.guard.ts`,
`core/api/api-client.service.ts`, `core/models/*.model.ts`.

**Scope (out):** Components, theming, backend, prompts.

**Outputs:** service + interceptor + guard files with `.spec.ts` siblings.

**Stop conditions:** memory leak (subscription without teardown); typed
contract drift vs backend OpenAPI; interceptor recursion.

---

### 3.10 meesell-angular-ui-styler (NEW)

| Field | Value |
|---|---|
| Purpose | Tailwind theme, Angular Material theming, responsive layout, a11y polish, MeeSell brand consistency. |
| Session | FRONTEND |
| Reports to | meesell-frontend-coordinator |
| Model | sonnet |
| Tools | Read, Bash, Write, Edit, Glob, Grep |

**Mandatory first action:** Read in order:
1. `CLAUDE.md` (Angular styling rules)
2. `docs/V1_FEATURE_SPEC.md` Section 3 (user journey)
3. `frontend/src/styles.css`, `tailwind.config.js`, `angular.json`
4. `docs/status/STATUS_FRONTEND.md`

**Hard constraints:**
- NEVER add a CSS-in-JS library or styled-components.
- NEVER hardcode colors — use Tailwind theme tokens or Material palette.
- NEVER ship a layout that breaks below 360 px width (Tirupur sellers are
  mobile-first).
- NEVER skip touch targets < 44 px.

**Scope (in):** `frontend/src/styles.css`, `tailwind.config.js`,
`postcss.config.js`, Angular Material custom theme file, component-scoped
CSS where Tailwind cannot express.

**Scope (out):** Component logic, services, backend, prompts.

**Outputs:** theme files, design tokens, accessibility audit notes.

**Stop conditions:** WCAG 2.1 AA contrast violation; mobile breakpoint test
failure; brand divergence from approved palette.

---

### 3.11 meesell-ai-coordinator (NEW)

| Field | Value |
|---|---|
| Purpose | Coordinate Gemini 2.5 Flash integration: prompt design, eval, parser, token tracking, cost monitoring. |
| Session | AI |
| Reports to | founder |
| Model | opus |
| Tools | Read, Bash, Write, Edit, Glob, Grep |

**Mandatory first action:** Read in order:
1. `CLAUDE.md` (Decision 3: Gemini Flash)
2. `docs/V1_FEATURE_SPEC.md` Features 2, 4, 5
3. `backend/app/data/meesho_category_tree.json` (when ready)
4. `docs/status/STATUS_AI.md`

**Hard constraints:**
- NEVER switch to GPT-4, Claude, or any non-Gemini LLM without founder
  approval (locked decision 3).
- NEVER write FastAPI route or middleware code — call sites only.
- NEVER ship a prompt without an eval fixture.
- NEVER log full prompt + response in plain text in prod (cost + PII).

**Scope (in):** Coordinates the three AI specialists. Owns prompt registry,
eval suite organisation, cost dashboard, `STATUS_AI.md`.

**Scope (out):** HTTP endpoint definitions, UI, infra, legal.

**Outputs:** `backend/app/ai_engine.py` (high level), `evals/`,
`STATUS_AI.md`.

**Stop conditions:** eval pass rate < 70 %; per-call cost > ₹0.05; Gemini
rate limit triggered repeatedly.

---

### 3.12 meesell-prompt-engineer (NEW)

| Field | Value |
|---|---|
| Purpose | Author Gemini prompt templates (system + few-shot + JSON-mode contracts) for category suggest, autofill, watermark vision. |
| Session | AI |
| Reports to | meesell-ai-coordinator |
| Model | opus |
| Tools | Read, Bash, Write, Edit, Glob, Grep |

**Mandatory first action:** Read in order:
1. `CLAUDE.md`
2. `docs/V1_FEATURE_SPEC.md` Features 2, 4, 5 (acceptance criteria)
3. `backend/app/data/meesho_category_tree.json`
4. `docs/status/STATUS_AI.md`

**Hard constraints:**
- NEVER hallucinate Meesho category names — every example uses real seed
  data.
- NEVER produce free-text output where JSON mode is required.
- NEVER exceed 4 few-shot examples per prompt (cost ceiling).
- NEVER touch route handlers or services beyond the prompt file.

**Scope (in):** prompt template files (Python constants or YAML),
parser/validator that maps Gemini JSON to Pydantic, eval fixtures, few-shot
banks per feature.

**Scope (out):** HTTP layer, UI, image processing, scraping.

**Outputs:** `backend/app/ai/prompts/*.py`, `backend/app/ai/parsers/*.py`,
`evals/prompts/*.yaml`.

**Stop conditions:** JSON parser regression on golden set; token count above
budget for any single prompt.

---

### 3.13 meesell-category-picker-builder (NEW)

| Field | Value |
|---|---|
| Purpose | Smart Category Picker pipeline — description → top-3 leaves with confidence and fallback keyword search. |
| Session | AI |
| Reports to | meesell-ai-coordinator |
| Model | opus |
| Tools | Read, Bash, Write, Edit, Glob, Grep |

**Mandatory first action:** Read in order:
1. `CLAUDE.md`
2. `docs/V1_FEATURE_SPEC.md` Feature 2 (full)
3. `backend/app/data/meesho_category_tree.json`
4. `docs/status/STATUS_AI.md`

**Hard constraints:**
- NEVER bypass the 50-description golden test (≥80 % top-3 accuracy).
- NEVER let a 3,772-leaf full tree go to the prompt — compressed
  representation only.
- NEVER skip the fallback to keyword `ILIKE` search on Gemini timeout.

**Scope (in):** category tree compression, embedding/keyword pre-filter,
top-3 ranker, confidence calibration, golden test fixture.

**Scope (out):** Route handler, UI, infra.

**Outputs:** `backend/app/ai/category_picker.py`,
`evals/category_picker_golden.yaml`.

**Stop conditions:** golden set accuracy regression > 5 pp; P95 latency > 3 s.

---

### 3.14 meesell-image-precheck-builder (NEW)

| Field | Value |
|---|---|
| Purpose | Image pre-check pipeline — JPEG / CMYK / resolution / white-BG / watermark detection (Gemini vision). |
| Session | AI |
| Reports to | meesell-ai-coordinator |
| Model | opus |
| Tools | Read, Bash, Write, Edit, Glob, Grep |

**Mandatory first action:** Read in order:
1. `CLAUDE.md` (Decision 4: rembg CPU)
2. `docs/V1_FEATURE_SPEC.md` Feature 5 (full)
3. `backend/app/services/image_processor.py` (current state, if any)
4. `docs/status/STATUS_AI.md`

**Hard constraints:**
- NEVER use GPU mode for rembg (locked decision 4).
- NEVER push more than 1 image per Gemini vision call (cost).
- NEVER fail-closed on Gemini vision unavailability — mark as `skipped`
  per spec edge case.
- NEVER store full image bytes in PostgreSQL — GCS only.

**Scope (in):** Pillow checks (JPEG, RGB/CMYK, resolution), white-BG
heuristic, Gemini vision watermark prompt + parser, 30-image golden test for
watermark accuracy ≥85 %.

**Scope (out):** Upload route handler, signed URL minting (services-builder),
UI.

**Outputs:** `backend/app/ai/image_precheck.py`,
`backend/app/services/image_processor.py` (vision portion only),
`evals/image_watermark_golden/`.

**Stop conditions:** golden watermark accuracy < 85 %; per-image cost
> ₹0.10; check pipeline > 8 s per image.

---

### 3.15 meesell-legal-writer (NEW)

| Field | Value |
|---|---|
| Purpose | Draft and maintain Privacy Policy, Terms of Service, Refund Policy, Cookie Policy, DPA, Razorpay KYC pack, GST registration pack, transactional email templates, landing copy. |
| Session | LEGAL |
| Reports to | founder |
| Model | opus |
| Tools | Read, Write, Edit, Glob, Grep |

**Mandatory first action:** Read in order:
1. `CLAUDE.md`
2. `docs/LEGAL_AND_COMPLIANCE_INFO.md`
3. `docs/BUSINESS_STRATEGY.md`
4. `docs/PRICING_LOCKED.md`
5. `docs/status/STATUS_LEGAL.md`

**Hard constraints:**
- NEVER provide legal advice — drafts are templates for founder + lawyer
  review.
- NEVER fabricate Indian statutory citations — every reference is verified
  against `LEGAL_AND_COMPLIANCE_INFO.md` or returns "needs founder
  research".
- NEVER touch code, infra, or AI prompts.
- NEVER promise features or SLAs that contradict V1 spec.
- NEVER include personal data of real users in templates.

**Scope (in):** `docs/legal/`, `docs/marketing/`, landing copy, email
templates (transactional + lifecycle), Razorpay KYC checklist, GST
registration checklist, in-product compliance strings (cookie banner,
consent strings).

**Scope (out):** UI implementation of legal pages (frontend session), email
sending infra (backend / infra).

**Outputs:** `docs/legal/*.md`, `docs/marketing/*.md`, copy snippets handed
off to frontend.

**Stop conditions:** founder asks for legal advice (refuse and route to
lawyer); claim contradicts pricing-locked or business-strategy doc.

---

### 3.16 meesell-data-engineer (NEW)

| Field | Value |
|---|---|
| Purpose | Coordinate the Meesho reference-data pipeline — XLSX parsing, brand master, scraper maintenance, refresh cadence. |
| Session | DATA |
| Reports to | founder |
| Model | opus |
| Tools | Read, Bash, Write, Edit, Glob, Grep |

**Mandatory first action:** Read in order:
1. `CLAUDE.md`
2. `docs/PLAYWRIGHT_MCP_REFERENCE.md`
3. `backend/app/data/` (current state)
4. `docs/status/STATUS_DATA.md`

**Hard constraints:**
- NEVER scrape Meesho without rate-limit and User-Agent compliance.
- NEVER modify backend models — hand off schema asks to backend session.
- NEVER let raw XLSX into git — only derived JSON committed under
  `backend/app/data/`.
- NEVER skip the schema-coverage report after a refresh.

**Scope (in):** Coordinates the three data specialists. Owns refresh
schedule, coverage stats, schema versioning of `category_attributes.json`.

**Scope (out):** Backend endpoints that consume the data; UI; prompts that
use the data (call AI session for prompt updates).

**Outputs:** `backend/app/data/*.json`, coverage reports, refresh changelog,
`STATUS_DATA.md`.

**Stop conditions:** Meesho schema change breaks > 5 % of templates;
scraper triggers Cloudflare block; brand whitelist diff > 200 brands without
manual review.

---

### 3.17 meesell-xlsx-parser (NEW)

| Field | Value |
|---|---|
| Purpose | Parse the 3,772 Meesho category XLSX templates into a single normalised `category_attributes.json` with field type, compulsory flag, enums, help text, and unit. |
| Session | DATA |
| Reports to | meesell-data-engineer |
| Model | sonnet |
| Tools | Read, Bash, Write, Edit, Glob, Grep |

**Mandatory first action:** Read in order:
1. `CLAUDE.md`
2. `docs/V1_FEATURE_SPEC.md` Feature 3 (form rendering consumes this output)
3. `data/meesho_templates/` directory listing (do NOT read all files)
4. `docs/status/STATUS_DATA.md`

**Hard constraints:**
- NEVER skip the schema validator on output JSON.
- NEVER ship `category_attributes.json` without a coverage report
  (parsed / total / failures).
- NEVER lose the original XLSX → row mapping (needed for refresh diffing).
- NEVER add a field key that breaks the contract used by AI prompts and
  frontend form renderer.

**Scope (in):** `scripts/parse_meesho_xlsx.py`,
`backend/app/data/category_attributes.json`,
`backend/app/data/meesho_category_tree.json`, parser unit tests.

**Scope (out):** Endpoint serving the JSON; UI rendering; prompts that
consume the JSON.

**Outputs:** scripts + derived JSON + coverage report.

**Stop conditions:** coverage < 95 % without explanation; output schema
diff vs previous version not reviewed by data-engineer.

---

### 3.18 meesell-brand-master-builder (NEW)

| Field | Value |
|---|---|
| Purpose | Build and maintain the Meesho approved-brand whitelist (~3,730 brands) used by Brand Validator (V1.5 feature, seed data prepared in V1). |
| Session | DATA |
| Reports to | meesell-data-engineer |
| Model | sonnet |
| Tools | Read, Bash, Write, Edit, Glob, Grep |

**Mandatory first action:** Read in order:
1. `CLAUDE.md`
2. `docs/V1_FEATURE_SPEC.md` (V1.5 brand validator note)
3. `backend/app/data/` (current state)
4. `docs/status/STATUS_DATA.md`

**Hard constraints:**
- NEVER store the brand list without a normalised key (lowercased, accents
  stripped).
- NEVER duplicate brands across spelling variants — alias map required.
- NEVER include trademarked brands without a source citation in metadata.

**Scope (in):** `backend/app/data/brand_master.json`,
`scripts/build_brand_master.py`, alias map, source citation table.

**Scope (out):** Brand-validation business logic (services-builder); UI.

**Outputs:** brand_master.json + alias map + script.

**Stop conditions:** alias collision rate > 1 %; missing source citations on
> 5 brands.

---

### 3.19 meesell-scraper-maintainer (NEW)

| Field | Value |
|---|---|
| Purpose | Maintain the Playwright-based Meesho catalogue scraper for quarterly category-tree and brand-whitelist refresh. |
| Session | DATA |
| Reports to | meesell-data-engineer |
| Model | sonnet |
| Tools | Read, Bash, Write, Edit, Glob, Grep |

**Mandatory first action:** Read in order:
1. `CLAUDE.md`
2. `docs/PLAYWRIGHT_MCP_REFERENCE.md`
3. `scripts/scrape_meesho.py` (current state)
4. `docs/status/STATUS_DATA.md`

**Hard constraints:**
- NEVER scrape at more than 1 request per 2 seconds.
- NEVER bypass robots.txt rules for paths Meesho disallows.
- NEVER ship a scraper run without idempotent diffing against last
  snapshot.
- NEVER store HTML scrapes in git — only structured JSON output.

**Scope (in):** `scripts/scrape_meesho.py`, selectors file, snapshot
directory under `data/snapshots/` (gitignored), diff reporter, schedule
notes.

**Scope (out):** Parsing the snapshots into final JSON (that is the
xlsx-parser / brand-master-builder), serving endpoints, UI.

**Outputs:** scraper script + selectors + snapshot diffs.

**Stop conditions:** Meesho returns 403/429 repeatedly; selector breakage
> 10 % of pages.

---

### 3.20 meesell-test-writer (NEW, optional / Day 7)

| Field | Value |
|---|---|
| Purpose | Cross-cutting test author — pytest backend integration tests, Karma/Jasmine frontend unit tests, Playwright E2E for the 12-step user journey. |
| Session | Cross-cutting |
| Reports to | founder (delegated by backend or frontend coordinator) |
| Model | sonnet |
| Tools | Read, Bash, Write, Edit, Glob, Grep |

**Mandatory first action:** Read in order:
1. `CLAUDE.md` (test sections of both Python and Angular)
2. `docs/V1_FEATURE_SPEC.md` Section 3 (E2E journey) and Section 8 (V1
   acceptance checklist)
3. existing test directories `backend/tests/` and `frontend/src/**/*.spec.ts`
4. `docs/status/STATUS_BACKEND.md` and `STATUS_FRONTEND.md`

**Hard constraints:**
- NEVER ship a test that hits external services in CI — mock MSG91,
  Gemini, GCS, Razorpay.
- NEVER duplicate tests already authored by feature builders — fill gaps
  only.
- NEVER use fixtures that depend on production data.

**Scope (in):** integration tests crossing multiple endpoints, E2E
Playwright suite for the V1 acceptance journey, smoke tests for staging.

**Scope (out):** Unit tests local to a single component or service (those
belong to feature builders).

**Outputs:** `backend/tests/test_e2e_*.py`,
`frontend/playwright/*.spec.ts`, smoke scripts.

**Stop conditions:** flaky test rate > 5 %; total CI time > 10 minutes.

---

### 3.21 meesell-deployer (NEW, optional / Day 7)

| Field | Value |
|---|---|
| Purpose | Drive GitLab CI + kubectl rolling deploys to staging and prod namespaces. |
| Session | Cross-cutting |
| Reports to | meesell-infra-builder |
| Model | sonnet |
| Tools | Read, Bash, Write, Edit, Glob, Grep |

**Mandatory first action:** Read in order:
1. `CLAUDE.md`
2. `docs/INFRASTRUCTURE_PLAYBOOK.md` (sections on CI/CD + rollout)
3. `.gitlab-ci.yml` (current state)
4. `docs/status/STATUS_INFRA.md`

**Hard constraints:**
- NEVER deploy to `prod` without explicit founder approval in the prompt.
- NEVER deploy without first running the validation suite from infra
  playbook.
- NEVER bypass `kubectl diff` before `kubectl apply`.
- NEVER push image tags that are not commit-SHA-pinned.

**Scope (in):** `.gitlab-ci.yml`, deploy scripts under `scripts/`, image
tag conventions, rollout/rollback runbooks.

**Scope (out):** VM provisioning (infra-builder), application code, tests.

**Outputs:** CI pipeline files, deploy notes appended to `STATUS_INFRA.md`.

**Stop conditions:** failed health check post-deploy; pod restart loop;
ingress 5xx rate > 1 %.

---

## Section 4: Creation Plan

After founder approval, the recommended sequence for authoring the spec
files. Bundles can be parallelised because they belong to different
sub-sessions.

| Priority | Agent(s) | Why this order |
|---|---|---|
| 1 (DONE) | meesell-infra-builder | Already exists, used as template. |
| 2 | meesell-data-engineer + meesell-xlsx-parser | Categories JSON is a blocker for backend seed + AI category picker; parse in parallel with infra. |
| 3 | meesell-backend-coordinator + meesell-database-builder + meesell-auth-builder | Day 2: schema first, then auth so all other endpoints can be guarded. |
| 4 | meesell-api-routes-builder + meesell-services-builder | Day 2–3: roll out the 16 endpoints. |
| 5 | meesell-ai-coordinator + meesell-prompt-engineer + meesell-category-picker-builder | Day 3–4: depends on data JSON being ready. |
| 6 | meesell-frontend-coordinator + meesell-angular-service-builder + meesell-angular-component-builder | Day 4–6: parallel with backend hardening. |
| 7 | meesell-angular-ui-styler + meesell-image-precheck-builder + meesell-brand-master-builder + meesell-scraper-maintainer | Day 5–6 polish + V1.5 seed. |
| 8 | meesell-legal-writer | Anytime — no code dependency, can be Day 1+. |
| 9 (Day 7) | meesell-test-writer + meesell-deployer | E2E + staging deploy. |

Spec authoring effort: ~30 minutes per agent × 20 new agents ≈ 10 hours
total. Bundling specialists by parent coordinator reduces this to ~6 hours
because the parent context can be reused.

---

## Section 5: Agent Memory Strategy

Each agent gets a persistent memory file under
`.claude/agent-memory/meesell-<name>/MEMORY.md`. The file holds three
sections:

1. **Founder preferences** — coding style, naming preferences, decisions
   already locked (e.g. "founder confirmed Valkey DB 0 for OTP only").
2. **Project state** — what's currently built in this agent's scope, what's
   broken, what's the live head SHA of the relevant directory.
3. **Patterns and gotchas** — discovered during work. Example for
   `meesell-database-builder`: "Postgres 16 in Supabase image disables
   pg_cron by default — use Celery beat for scheduled jobs."

Rules:
- Memory files are append-only summaries. The agent reads them at session
  start as part of "Mandatory first action" and writes a brief update at
  end of task.
- Never store secrets, JWTs, OTP values, or PII in memory.
- Memory is scoped per agent — `meesell-backend-coordinator` cannot read
  `meesell-frontend-coordinator/MEMORY.md`.

Memory directory layout after Day 1:
```
.claude/agent-memory/
├── meesell-infra-builder/MEMORY.md
├── meesell-backend-coordinator/MEMORY.md
├── meesell-database-builder/MEMORY.md
├── ...
└── meesell-deployer/MEMORY.md
```

---

## Section 6: Routing and Dispatch

### From the master session

```
Agent(
  subagent_type: "meesell-backend-coordinator",
  prompt: """
    PROJECT BOUNDARY: You are working on project "mesell" at
    /Users/mugunthansrinivasan/Project/mesell. DO NOT read, write, or
    reference files outside that path.

    TASK: <one-line task>
    CONTEXT: <relevant STATUS file paths>
    OUTPUT: <expected deliverable>
  """
)
```

### From a coordinator to a specialist

A coordinator dispatches its specialists the same way, e.g.
`meesell-backend-coordinator` calls
`Agent(subagent_type: "meesell-database-builder", ...)`.

### Precedence vs Nexus agents

- `meesell-*` agents take precedence whenever the task touches the MeeSell
  project.
- The existing `nexus:level-3:*` agents continue to exist as a fallback for
  tasks that are project-agnostic (e.g. when an agent needs raw GCP / K8s
  operations the infra-builder still calls `nexus:level-3:infra-builder`
  under the hood — but only via the dedicated MeeSell coordinator).
- The master session never calls `nexus:level-3:*` directly for MeeSell
  work — it always goes through a `meesell-*` coordinator so the project
  boundary is enforced once and only once.

### Boundary enforcement

Every dispatch prompt starts with the PROJECT BOUNDARY line. The workspace
PreToolUse hook (`workspace-boundary-hook.sh`) blocks any `Edit` or `Write`
outside the project tree even if the agent attempts it.

---

## Section 7: Total Agent Count

- Already exists: **1** (meesell-infra-builder)
- New to create — coordinators: **5** (backend, frontend, AI, legal, data)
- New to create — backend specialists: **4** (database, api-routes,
  services, auth)
- New to create — frontend specialists: **3** (component, service, styler)
- New to create — AI specialists: **3** (prompt-engineer, category-picker,
  image-precheck)
- New to create — data specialists: **3** (xlsx-parser, brand-master,
  scraper-maintainer)
- New to create — cross-cutting (optional, Day 7): **2** (test-writer,
  deployer)

**Total active MeeSell agents: 21 in the upper bound, 19 in the
recommended scope (excluding the 2 optional cross-cutting), with 1 already
shipped.**

> Note vs founder ceiling: the request stated 8–18 agents. The recommended
> scope of 19 sits one above the ceiling; if 18 is a hard ceiling, the two
> lowest-priority specialists to defer are **meesell-brand-master-builder**
> (V1.5 seed only) and **meesell-scraper-maintainer** (quarterly only,
> manual run acceptable in V1). Removing either brings the count to 18.
> Removing both brings it to 17 and is the recommended cut if the founder
> wants headroom; the V1 picker + form work depends only on the
> xlsx-parser output, which is the third data specialist that must stay.

Estimated spec authoring effort: **6 hours** if bundled by coordinator,
**10 hours** if written one-by-one.

---

## Section 8: Final Approval Checklist for Founder

Before creating the actual `.claude/agents/meesell-*.md` spec files,
founder confirms each item below:

- [ ] **Sub-session granularity.** 6 coordinators (INFRA, BACKEND,
      FRONTEND, AI, LEGAL, DATA) is the right level — not 4, not 10.
- [ ] **Specialist count under each coordinator** is right:
  - Backend: 4 specialists (database, api-routes, services, auth)
  - Frontend: 3 specialists (component, service, styler)
  - AI: 3 specialists (prompt-engineer, category-picker, image-precheck)
  - Data: 3 specialists (xlsx-parser, brand-master, scraper-maintainer)
  - Legal: 0 specialists (single writer)
  - Infra: 0 new specialists (uses nexus:level-3 fallback)
- [ ] **Naming convention.** All agents follow `meesell-<role>`
      lowercase-kebab-case.
- [ ] **Universal NEVER list** covers all the workspace projects:
      Aletheia, Prospero, Zenivo, JETK, Nexus, dev_agents, Archiview,
      curl_candy, Adalyze, ZATCA, Shotfox. Add any missing project before
      spec authoring.
- [ ] **Model assignment** per agent makes sense:
  - opus: coordinators + complex AI + auth (8 agents)
  - sonnet: deterministic specialists (database, api-routes, components,
    services, styler, parsers, scrapers, test, deploy)
- [ ] **Tool allowlist per agent** is minimal but sufficient. All agents
      use Read + Bash + Write + Edit + Glob + Grep. Legal writer drops
      Bash (no shell needed for doc authoring). Adjust if founder wants
      tighter allowlist per role.
- [ ] **Day 7 cross-cutting agents** (test-writer, deployer) — keep both,
      keep one, or drop both?
- [ ] **Count vs ceiling.** Accept 19 in recommended scope, or trim to 18
      by deferring brand-master-builder (V1.5), or trim to 17 by also
      deferring scraper-maintainer (manual refresh acceptable for V1).
- [ ] **Memory strategy** — agree to per-agent `MEMORY.md` files in
      `.claude/agent-memory/meesell-<name>/`.
- [ ] **Dispatch precedence** — `meesell-*` always takes precedence over
      `nexus:level-3:*` for MeeSell work.

Once the founder ticks every box (or asks for a revision), the next step is
to generate one spec file per row in Section 3.

---

## Appendix A: Cross-Reference to V1 Spec

| V1 Feature | Primary agent(s) responsible |
|---|---|
| 1. Auth (OTP + JWT) | meesell-auth-builder + meesell-api-routes-builder + meesell-angular-service-builder + meesell-angular-component-builder |
| 2. Smart Category Picker | meesell-category-picker-builder + meesell-prompt-engineer + meesell-api-routes-builder + meesell-angular-component-builder |
| 3. Fast Catalog Form | meesell-database-builder (schema) + meesell-api-routes-builder + meesell-angular-component-builder + meesell-xlsx-parser (field schema source) |
| 4. AI Auto-fill | meesell-prompt-engineer + meesell-services-builder + meesell-api-routes-builder + meesell-angular-service-builder |
| 5. Image Pre-check | meesell-image-precheck-builder + meesell-services-builder + meesell-prompt-engineer (vision prompt) + meesell-angular-component-builder |
| 6. Live Product Preview | meesell-angular-component-builder + meesell-angular-ui-styler + meesell-api-routes-builder |
| 7. Price Calculator | meesell-services-builder (pricing_engine) + meesell-api-routes-builder + meesell-angular-component-builder |
| 8. Tracking Dashboard | meesell-api-routes-builder + meesell-database-builder (indexes) + meesell-angular-component-builder |
| 9. XLSX Export | meesell-services-builder (export + openpyxl) + meesell-xlsx-parser (template format) + meesell-angular-component-builder |
| Infra (deploy, DNS, TLS) | meesell-infra-builder (+ meesell-deployer Day 7) |
| Legal pages, emails | meesell-legal-writer (+ meesell-angular-component-builder for UI wiring) |

Every V1 feature has at least 3 agents named above. No feature is owned by
a single agent — which validates that the coordinator layer is the right
abstraction for accountability.

---

## Appendix B: Forbidden-Projects Block (used in every spec)

Verbatim text that will appear in the "Hard Constraints — NEVER" section
of each new spec file:

```
NEVER read, write, modify, or reference any path outside
/Users/mugunthansrinivasan/Project/mesell/.

NEVER work on these workspace projects under any circumstance:
- Aletheia                        /Users/mugunthansrinivasan/Project/Aletheia
- Prospero                        /Users/mugunthansrinivasan/Project/Prospero
- Zenivo (LLM_Manager)            /Users/mugunthansrinivasan/Project/LLM_Manager
- JETK (Jussur Emdad)             /Users/mugunthansrinivasan/Project/JETK
- Nexus                           /Users/mugunthansrinivasan/Project/Nexus
- dev_agents                      /Users/mugunthansrinivasan/Project/dev_agents
- Archiview                       /Users/mugunthansrinivasan/Project/Archiview
- curl_candy_Manufacture          /Users/mugunthansrinivasan/Project/curl_candy_Manufacture
- Adalyze AI                      /Users/mugunthansrinivasan/Project/adalyze-ai
- ZATCA (Fatoora)                 /Users/mugunthansrinivasan/Project/ZATCA
- Shotfox                         (legacy, deprecated)

If asked to touch any of those, refuse and redirect the user to the
matching project's own agent fleet or master session.
```

---

End of registry. Awaiting founder approval before spec file generation.
