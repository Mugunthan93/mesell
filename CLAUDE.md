# CLAUDE.md — MeeSell Project Context

## MeeSell Agent Ecosystem Rules (NON-NEGOTIABLE)

MeeSell uses a **dedicated agent fleet** of 19 `meesell-*` agents. These rules govern every Claude session, sub-session, and dispatch in this project:

1. **Only `meesell-*` agents handle MeeSell work.** NEVER dispatch `nexus:level-*`, `general-purpose`, `Explore`, `Plan`, or any other non-MeeSell agent for MeeSell tasks. If a task touches MeeSell, only an agent whose name starts with `meesell-` may execute it.
2. **Decentralized memory.** Each agent has its own persistent memory at `.claude/agent-memory/meesell-<role>/MEMORY.md`. Every agent reads its own memory at the start of every task and appends learnings at the end.
3. **Decentralized cross-agent sharing.** Agents share context by **reading each other's memory** (`.claude/agent-memory/meesell-<other-role>/MEMORY.md`), NOT via a centralized truth document. There is no single source of truth — the truth is distributed across agent memories, STATUS files, and the locked docs (`V1_FEATURE_SPEC.md`, `PRICING_LOCKED.md`, `INFRASTRUCTURE_PLAYBOOK.md`, `LEGAL_AND_COMPLIANCE_INFO.md`).
4. **No agent writes to another agent's memory.** Memory directories are owned. If you need info that's not yet recorded in another agent's memory, escalate via the STATUS file blocker mechanism.
5. **Coordinator → specialist hierarchy.** The 5 coordinators (`meesell-backend-coordinator`, `meesell-frontend-coordinator`, `meesell-ai-coordinator`, `meesell-legal-writer`, `meesell-data-engineer`) plus `meesell-infra-builder` dispatch the specialists. The master Claude session dispatches the coordinators.
6. **Out-of-scope work is refused with a redirect.** Every agent has a Scope (IN) and Scope (OUT) section. Out-of-scope asks are refused with a polite "defer to meesell-<other-role>" message.
7. **HYBRID dispatch rule (founder-ruled 2026-06-11).** Dispatched coordinator agents have no Agent tool — they cannot reach their specialists, so the session window must run the hierarchy FOR them:
   - **Code-heavy construction** (feature code, extractions, AI pipeline code, auth/backend changes): THREE-step dispatch — (1) dispatch the coordinator to produce a task SPEC, (2) the session dispatches the named SPECIALIST agent (the sonnet builders) with that spec, (3) dispatch the coordinator again to run the MERGE-GATE REVIEW on the specialist's PR. The review is a real gate — it can reject back to the specialist.
   - **Docs, status flips, rulings landings, chores**: single-agent fast mode — the coordinator/lead executes directly. No ceremony.
   - Standalone agents (`meesell-infra-builder`, `meesell-legal-writer`) have no specialists — they always execute directly.

### The 19-agent roster

| Coordinator / Standalone | Specialists |
|---|---|
| `meesell-section-coordinator` (opus) | — (Tier-1 master; dispatches the frontend + backend discipline coordinators) |
| `meesell-infra-builder` (opus) | — |
| `meesell-backend-coordinator` (opus) | `meesell-database-builder` (sonnet), `meesell-api-routes-builder` (sonnet), `meesell-services-builder` (opus), `meesell-auth-builder` (opus) |
| `meesell-frontend-coordinator` (opus) | `meesell-angular-component-builder` (sonnet), `meesell-angular-service-builder` (sonnet), `meesell-angular-ui-styler` (sonnet) |
| `meesell-ai-coordinator` (opus) | `meesell-prompt-engineer` (opus), `meesell-category-picker-builder` (opus), `meesell-image-precheck-builder` (opus) |
| `meesell-legal-writer` (opus, no Bash) | — |
| `meesell-data-engineer` (opus) | `meesell-xlsx-parser` (sonnet), `meesell-scraper-maintainer` (sonnet) |

**Tier-1:** `meesell-section-coordinator` (opus) masters ONE V1 feature vertical slice — owns its wave plan + the integration→develop PR; dispatches the frontend + backend discipline coordinators beneath it. See SECTION_PARALLEL_MODEL.md / SECTION_DISPATCH_PROTOCOL.md.

**Deferred to V1.5:** `meesell-brand-master-builder` (brand whitelist parsed inline by `meesell-xlsx-parser` for V1). `meesell-test-writer` and `meesell-deployer` are not created at this stage.

See `docs/MEESELL_AGENT_REGISTRY.md` for full agent specs and `.claude/agents/meesell-*.md` for the executable spec files.

---

## Engineering Discipline (NON-NEGOTIABLE)

These rules apply to **every `meesell-*` agent on every task**. They are adapted from Andrej
Karpathy's catalogue of LLM coding failure modes (`multica-ai/andrej-karpathy-skills`, MIT) and
tuned to this fleet. They are behavioural defaults — not a substitute for the enforced PreToolUse
hooks — but agents are expected to follow them by default, and coordinators should enforce them at
the merge-gate review.

1. **Think Before Coding.** Before writing or editing code, state your interpretation of the task in
   one line and flag any ambiguity, then RESOLVE it (read the locked spec / live `/schema` / a peer's
   `MEMORY.md`, or escalate via the STATUS blocker) **before** you build. Guessing on an ambiguous
   spec is how the `size_in_ltrs` 422 shipped — the load-bearing question ("does enum validation read
   the public `/schema` or the internal cache?") was never surfaced. If two interpretations are
   plausible and the choice matters, stop and ask rather than guess.

2. **Surgical Changes.** Touch only the code that directly satisfies the task. Do NOT refactor,
   rename, reformat, or "tidy" unrelated code in the same change, and do NOT edit a shared singleton
   (`@mesell/core`, `@mesell/env`) when only a remote or feature is in scope. If you spot an unrelated
   problem, NOTE it for the coordinator — don't fix it inline. Drive-by edits are how the federation
   singleton / version-drift bugs propagated across remotes. Preserve existing style; smaller diffs
   clear the merge-gate review faster.

3. **Simplicity First.** Build exactly what was asked — no speculative abstractions, no unsolicited
   error handling, no "while I'm here" features, and no new dependency unless the task requires it.
   (The pricing engine is deliberately offline + constant-shipping + 0%-commission; don't add
   generality the spec doesn't ask for.) Extra surface area is extra review burden and extra bug
   surface.

> Karpathy's fourth rule, *Goal-Driven Execution*, is intentionally omitted: the
> coordinator→SPEC→build→merge-gate-review flow already provides the completion gate. If any agent
> runs an automated loop, it MUST set a hard token/iteration budget (the known gap in the original
> ruleset). MeeSell does NOT use the Nexus SDLC pipeline — discipline here is enforced by this fleet's
> own coordinator/merge-gate flow and hooks.

---

## What is MeeSell?

MeeSell is an AI-powered SaaS platform for Meesho marketplace suppliers. It helps sellers create product catalogs, validate listing quality, and optimize pricing — all from one platform at ₹499–1,999/month.

## Architecture

Single-node K3s cluster on GCP (asia-south1). All services run as Kubernetes pods.

```
Client (Angular 18 PWA) → FastAPI API (2 replicas) → PostgreSQL + Valkey
                                              → Celery Workers (2 replicas)
                                              → GCS (file storage)
                                              → Gemini 2.5 Flash (AI)
```

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2, Celery
- **Frontend:** Angular 18, TypeScript, Tailwind CSS, Angular Material, RxJS
- **Phase 2 Micro-frontends:** `@angular-architects/module-federation`
- **Phase 2 Mobile:** Ionic + Capacitor (wraps the Angular app for iOS/Android)
- **API:** REST (OpenAPI auto-generated from FastAPI)
- **Database:** PostgreSQL 16 self-hosted on K3s (via trimmed self-hosted Supabase)
- **Cache/Queue:** Valkey 8 (Redis-compatible, K3s pod)
- **Background jobs:** Celery + Valkey
- **AI Text:** Google Gemini 2.5 Flash API
- **AI Image:** rembg (self-hosted, CPU mode)
- **Storage:** Google Cloud Storage (GCS direct, free 5 GB tier)
- **Auth:** FastAPI + MSG91 OTP + JWT (PyJWT) — NOT GoTrue, NOT Supabase Auth
- **Payments:** Razorpay Subscriptions
- **Infra:** meesell-dev VM + K3s with `dev` / `staging` / `prod` namespaces, Traefik ingress, cert-manager
- **Region:** asia-south1
- **CI/CD:** GitLab CI + kubectl

## Project Structure

```
meesell/
├── CLAUDE.md                    ← You are here
├── TICKETS.md                   ← Sprint tasks (read this for next task)
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, middleware, health check
│   │   ├── config.py            # Pydantic Settings (env vars)
│   │   ├── database.py          # SQLAlchemy async engine + session
│   │   ├── models/              # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── catalog.py
│   │   │   ├── sku.py
│   │   │   ├── image.py
│   │   │   └── export.py
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── catalog.py
│   │   │   ├── sku.py
│   │   │   ├── quality.py
│   │   │   └── pricing.py
│   │   ├── routers/             # API route handlers
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── catalogs.py
│   │   │   ├── skus.py
│   │   │   ├── images.py
│   │   │   ├── quality.py
│   │   │   ├── pricing.py
│   │   │   └── exports.py
│   │   ├── services/            # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── ai_engine.py     # Gemini API calls + prompt management
│   │   │   ├── image_processor.py # rembg + PIL pipeline
│   │   │   ├── quality_engine.py  # QualityGate rules engine
│   │   │   ├── pricing_engine.py  # P&L calculator
│   │   │   ├── export_service.py  # CSV/ZIP generation
│   │   │   ├── otp_service.py     # MSG91 integration
│   │   │   └── storage.py         # GCS upload/download
│   │   ├── workers/             # Celery tasks
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py
│   │   │   ├── image_tasks.py
│   │   │   └── generation_tasks.py
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py          # JWT validation
│   │   │   ├── rate_limit.py    # Valkey sliding window
│   │   │   └── plan_guard.py    # Plan limit enforcement
│   │   └── data/                # Static data files
│   │       ├── meesho_categories.json
│   │       ├── meesho_shipping_slabs.json
│   │       ├── banned_words.json
│   │       └── category_attributes.json
│   ├── alembic/                 # DB migrations
│   │   ├── alembic.ini
│   │   └── versions/
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_catalog.py
│   │   ├── test_quality.py
│   │   └── test_pricing.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── main.ts
│   │   ├── index.html
│   │   ├── styles.css                  # Tailwind directives + Material theming
│   │   ├── app/
│   │   │   ├── app.component.ts        # Root standalone component
│   │   │   ├── app.config.ts           # ApplicationConfig (providers, router)
│   │   │   ├── app.routes.ts           # Route definitions (lazy-loaded)
│   │   │   ├── core/
│   │   │   │   ├── interceptors/
│   │   │   │   │   └── jwt.interceptor.ts   # HttpClient JWT interceptor
│   │   │   │   ├── guards/
│   │   │   │   │   └── auth.guard.ts
│   │   │   │   └── api/
│   │   │   │       └── api-client.service.ts # Typed HttpClient wrapper
│   │   │   ├── services/
│   │   │   │   ├── auth.service.ts          # Auth state (signals + RxJS)
│   │   │   │   ├── catalog.service.ts       # Catalog state + API
│   │   │   │   ├── sku.service.ts
│   │   │   │   ├── quality.service.ts
│   │   │   │   └── pricing.service.ts
│   │   │   ├── pages/
│   │   │   │   ├── onboarding/
│   │   │   │   │   └── onboarding.component.ts
│   │   │   │   ├── dashboard/
│   │   │   │   │   └── dashboard.component.ts
│   │   │   │   ├── catalog-create/
│   │   │   │   │   └── catalog-create.component.ts
│   │   │   │   ├── catalog-preview/
│   │   │   │   │   └── catalog-preview.component.ts
│   │   │   │   ├── quality-check/
│   │   │   │   │   └── quality-check.component.ts
│   │   │   │   ├── price-calculator/
│   │   │   │   │   └── price-calculator.component.ts
│   │   │   │   └── export-page/
│   │   │   │       └── export-page.component.ts
│   │   │   ├── components/
│   │   │   │   ├── image-uploader/
│   │   │   │   │   └── image-uploader.component.ts
│   │   │   │   ├── quality-scorecard/
│   │   │   │   │   └── quality-scorecard.component.ts
│   │   │   │   ├── pnl-breakdown/
│   │   │   │   │   └── pnl-breakdown.component.ts
│   │   │   │   ├── catalog-card/
│   │   │   │   │   └── catalog-card.component.ts
│   │   │   │   └── navbar/
│   │   │   │       └── navbar.component.ts
│   │   │   └── utils/
│   │   │       └── formatters.ts
│   ├── public/
│   │   └── manifest.webmanifest
│   ├── angular.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── tsconfig.json
│   └── package.json
├── k8s/
│   ├── namespace.yaml
│   ├── secrets.yaml.example
│   ├── config.yaml
│   ├── postgres.yaml
│   ├── valkey.yaml
│   ├── api.yaml
│   ├── worker.yaml
│   ├── frontend.yaml
│   ├── ingress.yaml
│   └── backup-cronjob.yaml
├── scripts/
│   └── setup-vm.sh
├── docker-compose.dev.yml       # Local dev (no K3s needed)
├── Makefile
└── .gitignore
```

## Coding Conventions

### Python (Backend)

- **Python 3.12**, type hints on all function signatures
- **Async everything**: use `async def` for all route handlers and service methods
- **SQLAlchemy async**: use `AsyncSession`, never synchronous queries
- **Pydantic v2** for all request/response schemas
- **Error handling**: raise `HTTPException` with appropriate status codes, never return raw error strings
- **Naming**: snake_case for functions/variables, PascalCase for classes, UPPER_CASE for constants
- **Imports**: stdlib → third-party → local, separated by blank lines
- **No print()**: use `logging.getLogger(__name__)` everywhere
- **Docstrings**: required on all service functions, optional on simple route handlers
- **Tests**: pytest + httpx AsyncClient for API tests

```python
# Example pattern for a router
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.catalog import CatalogCreate, CatalogResponse
from app.services.catalog_service import CatalogService
from app.middleware.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/v1/catalogs", tags=["catalogs"])

@router.post("/", response_model=CatalogResponse, status_code=status.HTTP_201_CREATED)
async def create_catalog(
    data: CatalogCreate,
    user: User = Depends(get_current_user),
    service: CatalogService = Depends(),
) -> CatalogResponse:
    return await service.create(user_id=user.id, data=data)
```

```python
# Example pattern for a service
import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.catalog import Catalog
from app.schemas.catalog import CatalogCreate

logger = logging.getLogger(__name__)

class CatalogService:
    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.db = db

    async def create(self, user_id: UUID, data: CatalogCreate) -> Catalog:
        """Create a new catalog for the user."""
        catalog = Catalog(user_id=user_id, name=data.name, status="draft")
        self.db.add(catalog)
        await self.db.commit()
        await self.db.refresh(catalog)
        logger.info(f"Catalog created: {catalog.id} for user {user_id}")
        return catalog
```

### Angular (Frontend)

- **Angular 18** with **standalone components** (default — no NgModules)
- **TypeScript strict mode**, type every input/output and service method
- **File naming**: kebab-case (e.g., `catalog-card.component.ts`, `auth.service.ts`, `jwt.interceptor.ts`)
- **Class naming**: PascalCase with suffix (`DashboardComponent`, `AuthService`, `JwtInterceptor`)
- **State management**: Angular **services + RxJS** (`BehaviorSubject` / `Observable`) for shared state; **signals** for component-local reactive state and computed values
- **HTTP**: `HttpClient` only, with a global **JWT interceptor** registered via `provideHttpClient(withInterceptors([...]))`
- **Styling**: **Tailwind CSS** utility classes + **Angular Material** components (no inline styles, no styled-components)
- **Routing**: `provideRouter` with **lazy-loaded** standalone route components (`loadComponent`)
- **Forms**: Reactive Forms (`FormBuilder`, `FormGroup`) — avoid template-driven forms
- **Change detection**: prefer `ChangeDetectionStrategy.OnPush` on all components
- **Loading states**: show Material spinner or skeleton for all async operations; use `async` pipe to subscribe in templates
- **Error handling**: `catchError` in services, surface user-facing errors via `MatSnackBar`
- **Tests**: **Karma + Jasmine** (Angular CLI default) or **Jest** — one `.spec.ts` per component/service

```typescript
// Example pattern for a page component (standalone, OnPush, signals + async pipe)
import { ChangeDetectionStrategy, Component, OnInit, signal, inject } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatProgressSpinnerModule } from "@angular/material/progress-spinner";
import { AuthService } from "../../services/auth.service";
import { CatalogService } from "../../services/catalog.service";
import { CatalogCardComponent } from "../../components/catalog-card/catalog-card.component";
import { Catalog } from "../../core/models/catalog.model";

@Component({
  selector: "app-dashboard",
  standalone: true,
  imports: [CommonModule, MatProgressSpinnerModule, CatalogCardComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="max-w-5xl mx-auto p-4">
      <h1 class="text-2xl font-bold mb-4">Dashboard</h1>
      @if (loading()) {
        <mat-spinner diameter="32"></mat-spinner>
      } @else {
        @for (c of catalogs(); track c.id) {
          <app-catalog-card [catalog]="c"></app-catalog-card>
        }
      }
    </div>
  `,
})
export class DashboardComponent implements OnInit {
  private readonly auth = inject(AuthService);
  private readonly catalogApi = inject(CatalogService);

  readonly catalogs = signal<Catalog[]>([]);
  readonly loading = signal(true);

  ngOnInit(): void {
    this.catalogApi.list().subscribe({
      next: (res) => {
        this.catalogs.set(res.catalogs);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }
}
```

```typescript
// Example pattern for a JWT interceptor
import { HttpInterceptorFn } from "@angular/common/http";
import { inject } from "@angular/core";
import { AuthService } from "../../services/auth.service";

export const jwtInterceptor: HttpInterceptorFn = (req, next) => {
  const token = inject(AuthService).token();
  if (!token) return next(req);
  return next(req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }));
};
```

### Phase 2: Module Federation (Micro-frontends)

When the app grows past MVP, the Angular shell will be split into independently deployable
remotes using **`@angular-architects/module-federation`**.

- **Shell** (host): routing, auth, navbar, shared services
- **Remotes** (planned): `catalog-mfe`, `quality-mfe`, `pricing-mfe`, `export-mfe`
- Each remote is a standalone Angular 18 app exposing its root route via Webpack 5 Module Federation
- Shared singletons: `@angular/core`, `@angular/common`, `@angular/router`, `rxjs`, `AuthService`
- Bootstrap with `loadRemoteModule(...)` in the shell's lazy routes — no rebuild of the shell needed when a remote ships
- Do **not** introduce Module Federation until at least 2 teams are touching the frontend or build times exceed 90s

### Phase 2: Ionic + Capacitor (Mobile)

The same Angular codebase is wrapped with **Ionic + Capacitor** for iOS/Android in Phase 2.

- Ionic components (`ion-content`, `ion-list`, `ion-button`) replace Material on mobile routes
- Capacitor plugins for camera (image upload), file system (CSV export), push notifications
- Single codebase: web (Angular Material) and mobile (Ionic) share services, models, and interceptors
- Do **not** add Ionic dependencies before Phase 2 — keep MVP frontend pure web

### Valkey (Cache/Queue)

- **Connection URL**: `redis://valkey:6379/{db}` (Valkey uses Redis protocol)
- **DB 0**: Sessions, OTP, rate limits
- **DB 1**: Celery broker
- **DB 2**: Celery result backend
- **Key naming**: `{namespace}:{entity}:{id}` (e.g., `otp:+919876543210`, `ratelimit:user123:generate:60`)
- **TTL**: always set TTL on temporary keys, never store without expiry
- **Library**: `redis.asyncio` (works with Valkey unchanged)

### Database

- **UUIDs** for all primary keys (gen_random_uuid())
- **TIMESTAMPTZ** for all timestamps (timezone-aware)
- **JSONB** for flexible structured data (ai_attributes, quality_checks)
- **Indexes**: on all foreign keys + frequently queried columns
- **Migrations**: Alembic, one migration per feature-group change, descriptive message
- **No raw SQL in routes**: always go through SQLAlchemy ORM or service layer

### API Design

- **Prefix**: `/api/v1/` for all endpoints
- **Auth**: JWT Bearer token in Authorization header
- **Pagination**: `?page=1&limit=20` with response `{ data: [...], total: N, page: N }`
- **Errors**: `{ "detail": "Human-readable message" }` with appropriate HTTP status
- **File uploads**: multipart/form-data, max 10MB per image
- **Background jobs**: return `{ "job_id": "...", "status": "processing" }`, poll via GET

### Git

> **Canonical git workflow: see `docs/GIT_WORKFLOW.md`.** That file is the single source of truth for branching, worktrees, and the merge flow. The summary below is a pointer — if anything here ever disagrees with `docs/GIT_WORKFLOW.md`, the workflow doc wins.

- **Branch naming**: `feature/{slug}/{group}`, where `group ∈ {backend, frontend, ai, data, infra}`. Each group gets its own branch, its own git worktree, and its own localhost env. (The legacy `ticket/{number}-desc` naming is RETIRED.)
- **Worktrees, not the master tree**: every group works in its own worktree. NEVER run git in the master tree (`MESELL_ALLOW_MASTER_GIT=1` override is for safe recovery only).
- **Two-step merge flow**:
  1. `feature/{slug}/{group}` --**squash**--> `feature/{slug}/integration` — the Director/coordinator merges this step.
  2. `feature/{slug}/integration` --**merge-commit**--> `develop` — the **FOUNDER** merges this step.
  3. Promotion onward: `develop` → staging → main (tagged).
- **No auto-delete of branches** (manual prune after merge); **no age-based stale rule**. (The legacy "one ticket per PR, squash merge to main" single-step flow is RETIRED.)
- **Commit messages**: conventional commits (`feat:`, `fix:`, `chore:`, etc.); reference the feature slug, not a ticket number.
- **Never commit**: .env, secrets.yaml, __pycache__, node_modules, .venv

## Key Decisions (Do Not Change)

1. **Valkey, not Redis** — open-source Redis fork, same protocol, no license issues
2. **GCS, not S3** — we're on GCP, same cloud as Gemini API
3. **Gemini 2.5 Flash, not GPT-4** — 10x cheaper, sufficient quality for catalog text
4. **rembg on CPU, not GPU** — 3-5s/image is acceptable for MVP, no GPU cost
5. **Dual-identity login: phone OTP OR Google Sign-In** — Indian sellers prefer phone, no password friction; Google Sign-In is an additive identity provider for the Android/Google-account cohort (removes SMS cost + delivery friction). **AMENDMENT 2026-06-18 — google-auth ratification:** the original "phone OTP login, not email" decision is widened to a DUAL-IDENTITY model. A user may exist with phone only (every existing row), Google only (`email` + Google `sub`, `phone = NULL`), or both. `iam.users.phone` becomes nullable-unique; `email` gains a nullable-UNIQUE linking constraint; a new nullable-UNIQUE `google_sub` column and an `auth_provider` audit column are added; a table-level CHECK guarantees `phone IS NOT NULL OR google_sub IS NOT NULL`. Account-linking is AUTO-LINK on a Google-`email_verified` match: `google_sub` match → login; else verified-`email` match → link `google_sub` onto the existing user; else create a Google-only user; a 409 is returned if the email belongs to a different `google_sub`. The phone-OTP path is unchanged. (End amendment.)
6. **K3s, not docker-compose in prod** — production-grade orchestration, easy to scale horizontally
7. **Meesho CSV export, not API upload** — Meesho has no open API for small third parties
8. **FastAPI, not Django** — async-first, better for AI/ML pipeline integration
9. **Angular 18, not React** — opinionated framework, built-in DI / Router / HttpClient / Forms, TypeScript-first, easier handoff to enterprise / agency engineers; standalone components remove the historical NgModule boilerplate
10. **Angular Services + RxJS (and signals), not NgRx/Zustand/Redux** — minimal boilerplate for MVP scope; revisit NgRx only if state complexity demands it
11. **Tailwind + Angular Material, not Material alone** — Material for accessible primitives (forms, dialogs, snackbars), Tailwind for layout and one-off styling
12. **Module Federation deferred to Phase 2** — single Angular app is faster to ship; split only when team size or build time forces it
13. **Ionic + Capacitor deferred to Phase 2** — MVP is web-only PWA; mobile wrap happens after product-market fit
14. **MSG91 OTP + JWT (PyJWT), not GoTrue / Supabase Auth** — full control over OTP flow, no external auth dependency, JWT issued by our own FastAPI. **AMENDMENT 2026-06-05 — FE-D5 ratification:** access JWT held in-memory by the frontend; refresh token in HttpOnly+Secure+SameSite=Strict cookie owned by backend with server-side revocation via Valkey allowlist (HMAC-with-pepper keyspace) on logout — no tokens in localStorage. (End amendment.)
15. **Trimmed self-hosted Supabase for PostgreSQL only** — use Supabase's hardened Postgres image on K3s; do NOT enable GoTrue, Realtime, or Storage subsystems

> **AMENDMENT 2026-06-18 — google-auth endpoint-inventory bump (BACKEND_ARCHITECTURE.md §7.3 / §17).** The dual-identity decision (#5 amendment) adds exactly one new endpoint, `POST /api/v1/auth/google/verify`, to the `iam` module. The locked iam endpoint count rises **6 → 7**; the locked §17 mounted-endpoint inventory rises **28 → 29**. The new route is feature-flag gated (`FEATURE_GOOGLE_AUTH_ENABLED`, default `False`): it is NOT mounted when the flag is off, so the OpenAPI surface and §17 count remain at 28 until the flag is enabled per namespace (dev → staging; prod deferred to V1.5). Reverse this amendment by deleting the route + the flag-gated mount and restoring the 6/28 counts. (End amendment.)

## Environment Variables

See `backend/.env.example` for full list. Key ones:
- `DATABASE_URL` — PostgreSQL async connection string
- `VALKEY_URL` — Valkey connection (redis:// protocol)
- `GEMINI_API_KEY` — Google Gemini API key
- `GCS_BUCKET` — GCS bucket name for images/exports
- `MSG91_AUTH_KEY` — SMS OTP provider
- `JWT_SECRET` — JWT signing secret
- `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` — Payment gateway

## Commands

```bash
# Local development
make dev              # Start docker-compose.dev.yml (API + Valkey + PostgreSQL)
make migrate          # Run Alembic migrations
make test             # Run pytest
make lint             # Run ruff linter

# Frontend (Angular CLI)
cd frontend && npm install           # Install dependencies
cd frontend && ng serve              # Dev server on :4200 (live reload)
cd frontend && ng build              # Production build to dist/
cd frontend && ng test               # Karma + Jasmine unit tests
cd frontend && ng lint               # Angular ESLint
cd frontend && ng generate component components/my-thing --standalone
cd frontend && ng generate service services/my-service

# Production (on GCP VM)
make deploy           # Build, push, kubectl rolling update
```

## What to Read Before Starting

1. This file (CLAUDE.md) — you're here
2. `TICKETS.md` — find your assigned ticket, read it fully
3. The relevant service/router files referenced in the ticket
4. `backend/.env.example` for required environment variables
