# Feature Plan — Auth: Phone OTP Login + JWT

**Feature slug:** `auth-otp`
**Session:** `mesell-auth-otp-planning-session-1`
**Date authored:** 2026-06-10
**Status:** PLAN READY — awaiting founder review
**Output of session:** This document. No production code was written.

**Drives:** `meesell-backend-coordinator` · `meesell-frontend-coordinator` · `meesell-infra-builder`
**Prerequisite for:** every other V1 feature (every endpoint except `/auth/otp/*` is JWT-protected)

---

## Decisions

Founder answers recorded verbatim from `mesell-auth-otp-planning-session-1` on 2026-06-10.

### D1 — Scope confirmation

**Answer:** Locked as-is — FE-D5 + §7 contract is the exact build target. No changes.

The feature matches `V1_FEATURE_SPEC.md §F1` + FE-D5 amendment block exactly:
- Access JWT held in-memory by the frontend (Angular signal) — **NOT localStorage**
- Refresh token as `HttpOnly; Secure; SameSite=Strict` cookie at `Path=/api/v1/auth; Domain=.mesell.xyz`
- Lua-script atomic rotation on Valkey DB 0 allowlist (`EVAL` primary, `EVALSHA` production, `EVAL` fallback on `NOSCRIPT`)
- HMAC-SHA256 with `REFRESH_TOKEN_PEPPER` key shape — NOT bare SHA-256 (Valkey-breach hardening)
- `ACCESS_TOKEN_TTL_SECONDS`: dev=30s / staging=60s / prod=900s (15 min) — env-driven per `BACKEND_ARCHITECTURE.md §5.D`
- `REFRESH_TOKEN_TTL_SECONDS`: dev=120s / staging=300s / prod=604800s (7 days) — env-driven per §5.D
- 2 new endpoints per FE-D5: `POST /api/v1/auth/refresh` + `POST /api/v1/auth/logout`
- Cookie `Path=/api/v1/auth` (NOT `Path=/auth` — browser path-matching requires the `/api/v1/auth` prefix)
- `secrets.compare_digest()` for allowlist lookup — NEVER `==` (timing-attack mitigation)
- `withCredentials: true` ONLY on `/api/v1/auth/*` XHR calls — all other API calls `withCredentials: false`

No scope flexes. SignupComponent is included (same backend OTP flow, separate UI page).

### D2 — Feature flag posture

**Answer:** No flag at all — auth lands unconditionally.

Auth is prerequisite zero. A feature flag that disables auth would disable the entire platform. Skip the feature flag; auth code lands directly on develop the moment all three group PRs (`feature/auth-otp/backend`, `feature/auth-otp/frontend`, `feature/auth-otp/infra`) merge to `feature/auth-otp` and the integration PR merges to develop.

`FEATURE_AUTH_OTP_ENABLED` is NOT created. No route-level `404` guard. No frontend `featureFlagGuard`.

### D3 — Priority ordering

**Answer:** Auth first, strict sequential — no other feature branch opens until `feature/auth-otp` merges to `develop`.

No parallel UI stub work for sibling features while auth-otp is in flight. Every other feature branch (`feature/smart-picker`, `feature/catalog-form`, etc.) is gated behind auth-otp's merge to develop. The founder opens the next feature branch only after confirming `develop` carries working auth.

### D4 — Agent lineup (confirmed 2026-06-10)

**Answer:** 3 leads + 7 specialists selected by founder.

| Track | Lead | Specialists |
|-------|------|-------------|
| Backend | `meesell-backend-coordinator` | `meesell-database-builder`, `meesell-services-builder`, `meesell-auth-builder`, `meesell-api-routes-builder` |
| Frontend | `meesell-frontend-coordinator` | `meesell-angular-service-builder`, `meesell-angular-component-builder`, `meesell-angular-ui-styler` |
| Infra | `meesell-infra-builder` (standalone) | — |

**Addition vs original plan:** `meesell-angular-ui-styler` added by founder — handles Tailwind layout, responsive breakpoints, and mobile-first styling for the 3 auth components as a separate pass after component-builder completes. AI track and Data track remain empty (iam has no AI call sites).

---

## Agent lineup

| Lead | Specialists dispatched | What each specialist builds |
|---|---|---|
| `meesell-backend-coordinator` | `meesell-database-builder` | `shared/models/user.py` ORM model + Alembic migration (`iam_users`) |
| | `meesell-services-builder` | `adapters/msg91.py` MSG91 adapter per §6.C |
| | `meesell-auth-builder` (primary) | `modules/iam/service.py` · `domain.py` · `repository.py` · `exceptions.py` · `lua/rotate_refresh.lua` · amends `core/auth.py` + `config.py` |
| | `meesell-api-routes-builder` | `modules/iam/router.py` · `schemas.py` · amends `main.py` |
| `meesell-frontend-coordinator` | `meesell-angular-service-builder` | `core/services/auth.service.ts` · `auth.interceptor.ts` (MODIFY) · `refresh.interceptor.ts` (NEW) · `auth.guard.ts` · amends `app.routes.ts` + `app.config.ts` |
| | `meesell-angular-component-builder` | `features/auth/login/` · `features/auth/signup/` · `features/auth/otp-verify/` (3 standalone components + 1 spec) |
| | `meesell-angular-ui-styler` | `features/auth/login/login.component.scss` · `features/auth/signup/signup.component.scss` · `features/auth/otp-verify/otp-verify.component.scss` — Tailwind mobile-first layout, spacing, responsive, a11y polish |
| `meesell-infra-builder` (standalone) | — | K8s deployment env-var additions (ACCESS/REFRESH TTLs + CORS); verify all 4 secrets are wired; `docs/runbooks/auth-secret-rotation.md` |

**AI track:** NO work (auth has no AI call sites — `iam` is the all-`✗` module per `BACKEND_ARCHITECTURE.md §2.D` matrix).
**Data track:** NO work.

### Dispatch order (critical path)

```
PHASE A (parallel — no deps):
  meesell-database-builder    → users model + migration
  meesell-services-builder    → adapters/msg91.py
  meesell-infra-builder       → env vars + secret wiring + runbook

PHASE B (after A complete):
  meesell-auth-builder        → iam/service.py, domain.py, exceptions.py, lua/, core/auth.py, config.py
                                (needs User model shape from database-builder; needs msg91 adapter interface from services-builder)

PHASE C (after B complete):
  meesell-api-routes-builder  → iam/router.py, schemas.py, main.py
                                (needs domain.py + exceptions.py + service.py interfaces from auth-builder)

PHASE D (after C complete, or parallel with C):
  meesell-angular-service-builder  → AuthService + interceptors + guard + routes
  meesell-angular-component-builder → Login/Signup/OtpVerify components
                                       (after service-builder so AuthService interface is stable)

PHASE E (after component-builder complete):
  meesell-angular-ui-styler        → Tailwind styling for all 3 auth components
                                       (components must exist before ui-styler can reference selectors + HTML structure)
```

---

## Branch setup

> **When to create:** After PR #3 (`feature/auth-otp/planning`) merges to `develop` and this feature is `LOCKED` in the tracker. Do NOT open coding branches while this plan is still `IN REVIEW`. Per D3: no coding branch opens until auth-otp is LOCKED.

### Branches to create (all cut from `develop`)

| Branch | Cut from | Purpose | Who commits here |
|--------|----------|---------|-----------------|
| `feature/auth-otp` | `develop` | Integration branch — sub-branches merge into here; final PR to `develop` | Only merge commits from sub-branches |
| `feature/auth-otp/backend` | `feature/auth-otp` | All backend specialist work | `meesell-database-builder`, `meesell-services-builder`, `meesell-auth-builder`, `meesell-api-routes-builder` |
| `feature/auth-otp/frontend` | `feature/auth-otp` | All frontend specialist work | `meesell-angular-service-builder`, `meesell-angular-component-builder`, `meesell-angular-ui-styler` |
| `feature/auth-otp/infra` | `feature/auth-otp` | All infra work | `meesell-infra-builder` |

### Creation commands (run by founder after PR #3 merges)

```bash
# Ensure develop is current
git checkout develop && git pull origin develop

# Create integration branch
git checkout -b feature/auth-otp
git push -u origin feature/auth-otp

# Create 3 group branches from the integration branch
git checkout -b feature/auth-otp/backend feature/auth-otp
git push -u origin feature/auth-otp/backend

git checkout -b feature/auth-otp/frontend feature/auth-otp
git push -u origin feature/auth-otp/frontend

git checkout -b feature/auth-otp/infra feature/auth-otp
git push -u origin feature/auth-otp/infra

# Return to integration branch
git checkout feature/auth-otp
```

### PR flow (coding stage)

```
feature/auth-otp/backend  ──┐
feature/auth-otp/frontend ──┤──► feature/auth-otp ──► develop
feature/auth-otp/infra    ──┘
```

- Each group branch opens a PR to `feature/auth-otp` (NOT directly to `develop`)
- `feature/auth-otp/backend` PR reviewed and approved by `meesell-backend-coordinator`
- `feature/auth-otp/frontend` PR reviewed and approved by `meesell-frontend-coordinator`
- `feature/auth-otp/infra` PR self-reviewed by `meesell-infra-builder`, then founder gate
- Integration PR (`feature/auth-otp` → `develop`) opened only after all 3 group PRs are merged; founder does final review

### PR templates

| PR | Template file |
|----|--------------|
| `feature/auth-otp/backend` → `feature/auth-otp` | `.github/PULL_REQUEST_TEMPLATE/backend.md` |
| `feature/auth-otp/frontend` → `feature/auth-otp` | `.github/PULL_REQUEST_TEMPLATE/frontend.md` |
| `feature/auth-otp/infra` → `feature/auth-otp` | `.github/PULL_REQUEST_TEMPLATE/infra.md` |
| `feature/auth-otp` → `develop` | `.github/PULL_REQUEST_TEMPLATE/feature.md` |

---

## Sprint plan

> **Purpose:** Execution roadmap for coding-stage dispatch. Read this before dispatching any agent.
> **Based on:** Actual codebase audit (2026-06-10) — backend is ~95% complete; frontend is ~30% complete (UI scaffolded, zero HTTP wiring).
> **Gate to start:** PR #3 merged to `develop` → tracker = `LOCKED` → 4 coding branches created.

### Current state audit

| Track | Component | Status | What exists | What's missing |
|-------|-----------|--------|-------------|----------------|
| Backend | `modules/iam/service.py` | ✅ COMPLETE | All 6 methods implemented with FE-D5 contracts | — |
| Backend | `modules/iam/domain.py` | ✅ COMPLETE | 8 frozen dataclasses | — |
| Backend | `modules/iam/exceptions.py` | ✅ COMPLETE | 8 exception subclasses | — |
| Backend | `modules/iam/router.py` | ✅ COMPLETE | 6 endpoints, cookie constants, rate limiting | — |
| Backend | `core/auth.py` | ✅ COMPLETE | JWT issuing, HMAC pepper, Lua `REFRESH_ROTATE_LUA`, EVALSHA/EVAL fallback | — |
| Backend | `shared/models/user.py` | ✅ COMPLETE | `User` ORM model | Alembic migration needs verification |
| Backend | `adapters/msg91.py` | ✅ COMPLETE | MSG91 adapter | IP whitelist needs verification |
| Backend | `modules/iam/schemas.py` | ⚠️ VERIFY | May exist (router imports it) | Needs pytest suite |
| Frontend | `core/services/auth.service.ts` | ⚠️ STUB | Signal state, `setSession`, `logout`, `getToken` | `sendOtp()`, `verifyOtp()`, `logout()`, `getProfile()` HTTP calls missing |
| Frontend | `core/interceptors/auth.interceptor.ts` | ❌ MISSING | Directory does not exist | Full interceptor file needed |
| Frontend | `core/interceptors/refresh.interceptor.ts` | ❌ MISSING | Directory does not exist | Full interceptor file needed |
| Frontend | `core/guards/auth.guard.ts` | ⚠️ STUB | Reads `isAuthenticated()` computed | Must read `token()` signal directly |
| Frontend | `features/auth/login/login.component.ts` | ⚠️ STUB | Full UI + reactive form | `onSubmit()` uses `setTimeout` mock — no HTTP call |
| Frontend | `features/auth/signup/signup.component.ts` | ⚠️ STUB | Full UI + reactive form | `onSubmit()` uses `setTimeout` mock — no HTTP call |
| Frontend | `features/auth/otp-verify/otp-verify.component.ts` | ⚠️ STUB | UI, countdown timer, OTP input | Phone not read from query params; `'mock-token'` hardcoded |
| Frontend | SCSS files (3) | ❌ MISSING | Not created | `login.component.scss`, `signup.component.scss`, `otp-verify.component.scss` |
| Infra | K8s env vars + secrets | ✅ COMPLETE | All 4 secrets LIVE in Secret Manager | K8s manifest env-var additions needed |
| Infra | `auth-secret-rotation.md` runbook | ❌ MISSING | Not created | New file needed |

### Sprint 0 — Unlock (½ day)

**Gate:** PR #3 reviewed and merged to `develop`. Precedes all coding dispatch.

| # | Task | Owner | Exit criterion |
|---|------|-------|---------------|
| S0.1 | Founder reviews and approves PR #3 (`feature/auth-otp/planning` → `develop`) | Founder | PR merged to `develop` |
| S0.2 | Update `feature_planning_master.md` row: `auth-otp` → `LOCKED` | Founder / Director | Tracker updated |
| S0.3 | Create 4 coding branches per Branch setup commands | Founder | `feature/auth-otp`, `/backend`, `/frontend`, `/infra` all pushed to origin |
| S0.4 | Update `docs/status/feature_board_backend.md` and `feature_board_frontend.md` — auth-otp row = `IN PROGRESS` | Backend coord + Frontend coord | Status boards updated on respective branches |

### Sprint 1 — Backend verification + infra (Days 1–3)

**Dispatch:** Phase A (parallel): `meesell-database-builder` + `meesell-services-builder` + `meesell-infra-builder`
**Followed by:** Phase B: `meesell-auth-builder` → Phase C: `meesell-api-routes-builder`

| # | Task | Agent | Phase | What gets done |
|---|------|-------|-------|---------------|
| S1.1 | Verify Alembic migration exists and runs clean; confirm `User` model columns match `service.py` assumptions | `meesell-database-builder` | A | Migration `iam_users` verified; `alembic upgrade head` passes |
| S1.2 | Add env vars to K8s manifests (dev + staging namespaces); verify all 4 secrets wired; write `auth-secret-rotation.md` runbook | `meesell-infra-builder` | A | 3 infra surfaces done; secret check complete |
| S1.3 | Verify `modules/iam/schemas.py` exists; all Pydantic v2 request/response shapes match `domain.py` dataclasses; add any missing schemas | `meesell-api-routes-builder` | C | `schemas.py` complete; `router.py` imports clean |
| S1.4 | Write pytest suite: `tests/unit/iam/test_service.py` + `test_router.py` + `tests/integration/test_auth_otp_integration.py` | `meesell-auth-builder` (unit) + `meesell-api-routes-builder` (integration) | B + C | ≥ 80% iam path coverage; all 6 service methods tested |
| S1.5 | Verify MSG91 IP whitelist allows dev VM IP (`122.164.85.51`); real OTP send in dev namespace | `meesell-infra-builder` | A | Smoke: `POST /auth/otp/send` with real phone returns `200 OK` in dev |

**Sprint 1 exit gate:**
- [ ] `alembic upgrade head` runs clean from empty DB
- [ ] `pytest tests/unit/iam/` — all green
- [ ] `pytest tests/integration/test_auth_otp_integration.py` — all green (requires dev K8s running)
- [ ] `POST /auth/otp/send` smoke → real OTP received on phone
- [ ] `feature/auth-otp/backend` PR and `feature/auth-otp/infra` PR open and ready for review

### Sprint 2 — Frontend HTTP wiring (Days 4–9)

**Dispatch:** Phase D then Phase E — service-builder first, component-builder after, ui-styler last.

#### S2.A — Service layer (`meesell-angular-service-builder`, Days 4–6)

| # | Task | What gets built |
|---|------|----------------|
| S2.1 | `auth.service.ts` HTTP methods | `sendOtp(phone)`, `verifyOtp(phone, otp)`, `logout()`, `getProfile()` — all returning `Observable<...>` |
| S2.2 | Create `core/interceptors/` directory + `auth.interceptor.ts` | JWT Bearer interceptor; `withCredentials: true` ONLY on URLs containing `/api/v1/auth/` |
| S2.3 | `refresh.interceptor.ts` | Silent 401 handler; `BehaviorSubject` refresh deduplication (one in-flight refresh, all other 401 callers queue); retry original request on success; redirect to `/login` on failure |
| S2.4 | `auth.guard.ts` | Read `AuthService.token()` signal directly (not `isAuthenticated()` computed) |
| S2.5 | `app.routes.ts` | Add `/login`, `/signup`, `/otp-verify` as public routes with `auth-layout`; route comment block per Documentation deliverable #6 |
| S2.6 | `app.config.ts` | Register both interceptors: `provideHttpClient(withInterceptors([authInterceptor, refreshInterceptor]))` — auth first, refresh second |

#### S2.B — Component wiring (`meesell-angular-component-builder`, Days 7–8)

| # | Task | What gets built |
|---|------|----------------|
| S2.7 | `login.component.ts` | Replace `setTimeout` mock with `AuthService.sendOtp()` call; on success navigate to `/otp-verify?phone=<encoded>` |
| S2.8 | `otp-verify.component.ts` | Read `phone` from `ActivatedRoute.queryParams`; replace `setTimeout` mock with `AuthService.verifyOtp()` call; `AuthService.setSession()` on success; navigate to `/dashboard` |
| S2.9 | `signup.component.ts` | Replace `setTimeout` mock with `AuthService.sendOtp()` call; navigate to `/otp-verify?phone=<encoded>&mode=signup` |
| S2.10 | Error states | All 3 components surface inline errors from `IamService` exception types: `phone_invalid`, `otp_expired`, `otp_invalid`, `rate_limited` |

#### S2.C — Styling pass (`meesell-angular-ui-styler`, Day 9)

| # | Task | What gets built |
|---|------|----------------|
| S2.11 | 3 SCSS files | `login.component.scss`, `signup.component.scss`, `otp-verify.component.scss` — Tailwind mobile-first layout, responsive breakpoints, WCAG AA contrast, Tirupur seller mobile target |

**Sprint 2 exit gate:**
- [ ] `ng build` — zero errors, zero `@ts-ignore`
- [ ] `auth.interceptor.ts` and `refresh.interceptor.ts` exist in `core/interceptors/`
- [ ] `auth.guard.ts` reads `token()` signal (not `isAuthenticated()`)
- [ ] Full OTP flow works end-to-end in `ng serve` against dev API — no `setTimeout` mocks remain
- [ ] `phone` read from query params in `otp-verify.component.ts`
- [ ] `feature/auth-otp/frontend` PR open and ready for review

### Sprint 3 — Integration + acceptance gate (Days 10–12)

| # | Task | Owner | Exit criterion |
|---|------|-------|---------------|
| S3.1 | Real end-to-end OTP flow in dev: send OTP → receive SMS → enter OTP → receive JWT → access protected route | Founder + backend lead | Full flow works with real MSG91 SMS |
| S3.2 | Verify refresh token rotation: login → wait for access TTL (30s in dev) → make authenticated request → confirm silent refresh fires once | Founder | No visible session interruption; `POST /auth/refresh` called exactly once |
| S3.3 | Verify logout: `POST /auth/logout` → refresh cookie deleted → subsequent `POST /auth/refresh` returns 401 | Founder | Session fully terminated |
| S3.4 | CI gate 1: `ng build` clean | CI | ✅ green |
| S3.5 | CI gate 2: `pytest` full suite ≥ 80% coverage on `modules/iam/` | CI | ✅ green |
| S3.6 | CI gate 3: `ruff check backend/` clean | CI | ✅ green |
| S3.7 | CI gate 4: `ng lint` clean | CI | ✅ green |
| S3.8 | `feature/auth-otp/backend` PR approved by `meesell-backend-coordinator` | Backend coord | PR ✅ approved |
| S3.9 | `feature/auth-otp/frontend` PR approved by `meesell-frontend-coordinator` | Frontend coord | PR ✅ approved |
| S3.10 | `feature/auth-otp/infra` PR approved by founder | Founder | PR ✅ approved |
| S3.11 | All 3 group PRs merged to `feature/auth-otp` integration branch | Founder | Integration branch holds all work |
| S3.12 | Integration PR (`feature/auth-otp` → `develop`) opened; founder final review | Founder | Review done |
| S3.13 | Integration PR merged; `develop` carries working auth | Founder | `feature/auth-otp` → `develop` ✅ |

**Post-merge stamps (after S3.13):**
- `meesell-backend-coordinator` stamps `V1_FEATURE_SPEC.md §F1` — "implemented YYYY-MM-DD PR#N"
- `meesell-backend-coordinator` adds `BACKEND_ARCHITECTURE.md §7` sentinel comment

### Sprint timeline

```
Day 0:    PR #3 merged → LOCKED → 4 coding branches created
          │
Days 1–3: [BACKEND Phase A — parallel]
            meesell-database-builder  → users model + migration verification
            meesell-services-builder  → msg91 adapter (verify / complete gaps)
            meesell-infra-builder     → K8s env vars + secrets + runbook
          [BACKEND Phase B] meesell-auth-builder      → pytest unit suite
          [BACKEND Phase C] meesell-api-routes-builder → schemas + integration tests
          │
Days 4–6: [FRONTEND Phase D-1] meesell-angular-service-builder
            → auth.service.ts HTTP methods
            → auth.interceptor.ts + refresh.interceptor.ts (NEW)
            → auth.guard.ts fix + app.routes.ts + app.config.ts
          │
Days 7–8: [FRONTEND Phase D-2] meesell-angular-component-builder
            → wire login/signup/otp-verify to real HTTP (remove setTimeout mocks)
          │
Day 9:    [FRONTEND Phase E] meesell-angular-ui-styler
            → 3 SCSS files (mobile-first, WCAG AA)
          │
Days 10–12: Integration test + acceptance gate + group PRs → feature/auth-otp → develop
```

### Risk-adjusted schedule notes

| Risk | Buffer | Contingency |
|------|--------|-------------|
| MSG91 IP whitelist blocked in dev | +0.5 day | Use MSG91 test-sender credentials (no IP restriction) for dev namespace while founder updates whitelist |
| `refresh.interceptor.ts` BehaviorSubject dedup complexity | +1 day | Service-builder reads `BACKEND_ARCHITECTURE.md §4.B` BehaviorSubject pattern before starting; dedup is the hardest piece of this sprint |
| `ng build` breaks after interceptor registration order change | +0.5 day | Interceptor order in `app.config.ts` must be `[authInterceptor, refreshInterceptor]` — auth first, refresh second |
| `dpdp_consented_at` NOT NULL constraint gap (webhook capture) | Deferred | Webhook capture is log-only in V1; `user_id` NOT NULL gap acknowledged; no sprint scope impact |

---

## Code surfaces

### Backend

| # | File | Status | Owner |
|---|------|--------|-------|
| 1 | `backend/app/modules/iam/__init__.py` | NEW | `meesell-auth-builder` |
| 2 | `backend/app/modules/iam/service.py` | NEW | `meesell-auth-builder` |
| 3 | `backend/app/modules/iam/repository.py` | NEW | `meesell-auth-builder` |
| 4 | `backend/app/modules/iam/domain.py` | NEW | `meesell-auth-builder` |
| 5 | `backend/app/modules/iam/exceptions.py` | NEW | `meesell-auth-builder` |
| 6 | `backend/app/modules/iam/lua/rotate_refresh.lua` | NEW | `meesell-auth-builder` |
| 7 | `backend/app/modules/iam/router.py` | NEW | `meesell-api-routes-builder` |
| 8 | `backend/app/modules/iam/schemas.py` | NEW | `meesell-api-routes-builder` |
| 9 | `backend/app/adapters/msg91.py` | NEW | `meesell-services-builder` |
| 10 | `backend/app/shared/models/user.py` | NEW | `meesell-database-builder` |
| 11 | `backend/alembic/versions/<rev>_iam_users.py` | NEW | `meesell-database-builder` |
| 12 | `backend/app/core/auth.py` | MODIFY | `meesell-auth-builder` |
| 13 | `backend/app/config.py` | MODIFY | `meesell-auth-builder` |
| 14 | `backend/app/main.py` | MODIFY | `meesell-api-routes-builder` |
| 15 | `backend/tests/unit/iam/test_service.py` | NEW | `meesell-auth-builder` |
| 16 | `backend/tests/unit/iam/test_router.py` | NEW | `meesell-api-routes-builder` |
| 17 | `backend/tests/integration/test_auth_otp_integration.py` | NEW | `meesell-api-routes-builder` |

**Notes on `core/auth.py` (MODIFY scope):**
- Remove `JWT_EXPIRY_DAYS` references; replace with `settings.ACCESS_TOKEN_TTL_SECONDS`
- Add `SCRIPT LOAD` of `rotate_refresh.lua` at process startup; cache SHA1 digest on `IamService` singleton
- `get_current_user` signature, `CurrentUser` shape, claim decode path — UNCHANGED

**Notes on `config.py` (MODIFY scope):**
- Add: `ACCESS_TOKEN_TTL_SECONDS: int = 900`
- Add: `REFRESH_TOKEN_TTL_SECONDS: int = 604800`
- Add: `REFRESH_TOKEN_PEPPER: str` (Secret Manager ref `refresh-token-pepper`)
- Add: `RAZORPAY_WEBHOOK_SECRET: str` (Secret Manager ref `razorpay-webhook-secret`)
- Add: `CORS_ALLOWED_ORIGINS: list[str]`
- Add: `CORS_ALLOW_CREDENTIALS: bool = True`
- Remove: `JWT_EXPIRY_DAYS` (deprecated per §4.B amendment)

### Frontend

| # | File | Status | Owner |
|---|------|--------|-------|
| 1 | `frontend/src/app/features/auth/login/login.component.ts` | NEW | `meesell-angular-component-builder` |
| 2 | `frontend/src/app/features/auth/login/login.component.html` | NEW | `meesell-angular-component-builder` |
| 3 | `frontend/src/app/features/auth/login/login.component.spec.ts` | NEW | `meesell-angular-component-builder` |
| 4 | `frontend/src/app/features/auth/signup/signup.component.ts` | NEW | `meesell-angular-component-builder` |
| 5 | `frontend/src/app/features/auth/signup/signup.component.html` | NEW | `meesell-angular-component-builder` |
| 6 | `frontend/src/app/features/auth/otp-verify/otp-verify.component.ts` | NEW | `meesell-angular-component-builder` |
| 7 | `frontend/src/app/features/auth/otp-verify/otp-verify.component.html` | NEW | `meesell-angular-component-builder` |
| 8 | `frontend/src/app/core/services/auth.service.ts` | MODIFY | `meesell-angular-service-builder` |
| 9 | `frontend/src/app/core/interceptors/auth.interceptor.ts` | MODIFY | `meesell-angular-service-builder` |
| 10 | `frontend/src/app/core/interceptors/refresh.interceptor.ts` | NEW | `meesell-angular-service-builder` |
| 11 | `frontend/src/app/core/guards/auth.guard.ts` | MODIFY | `meesell-angular-service-builder` |
| 12 | `frontend/src/app/app.routes.ts` | MODIFY | `meesell-angular-service-builder` |
| 13 | `frontend/src/app/app.config.ts` | MODIFY | `meesell-angular-service-builder` |
| 14 | `frontend/src/app/core/services/auth.service.spec.ts` | NEW | `meesell-angular-service-builder` |
| 15 | `frontend/src/app/features/auth/login/login.component.scss` | NEW | `meesell-angular-ui-styler` |
| 16 | `frontend/src/app/features/auth/signup/signup.component.scss` | NEW | `meesell-angular-ui-styler` |
| 17 | `frontend/src/app/features/auth/otp-verify/otp-verify.component.scss` | NEW | `meesell-angular-ui-styler` |

**Notes on `auth.interceptor.ts` (MODIFY):**
Rename conceptually to JWT Bearer interceptor (file name `auth.interceptor.ts` retained — matches Wave 2B scaffold). Reads `AuthService.token()` signal; if non-null, clones request with `Authorization: Bearer <token>`. Sets `withCredentials: true` ONLY on requests whose URL contains `/api/v1/auth/` (enables cookie send on refresh/logout). All other requests: `withCredentials: false`.

**Notes on `refresh.interceptor.ts` (NEW):**
Silent 401 handler. Catches HTTP 401 on non-auth routes, calls `POST /api/v1/auth/refresh` (cookie auto-sent), on success stores new access JWT in `AuthService._token` signal, retries original request. On refresh failure: calls `AuthService.logout()`, redirects to `/login`. Implements request-queue + in-flight dedupe to prevent a refresh storm under concurrent 401s.

**Notes on `auth.guard.ts` (MODIFY):**
Reads `AuthService.token()` signal (`inject(AuthService).token()`). If signal is null: `return router.parseUrl('/login')`. No async — signal is synchronous.

**Notes on `app.routes.ts` (MODIFY):**
Three new public routes (no `authGuard`):
- `/login` → `LoginComponent` (lazy-loaded via `loadComponent`, `auth-layout` as parent)
- `/signup` → `SignupComponent` (lazy-loaded, `auth-layout`)
- `/otp-verify` → `OtpVerifyComponent` (lazy-loaded, `auth-layout`)
All authenticated routes (shell outlet) already guarded by `authGuard` from existing scaffold.

### AI / Data

NONE — no changes in `ai_ops/`, `data/`, or `scripts/`.

### Infra

| # | File / resource | Status | Owner |
|---|-----------------|--------|-------|
| 1 | K8s deployment config for `dev` namespace — add `ACCESS_TOKEN_TTL_SECONDS=30`, `REFRESH_TOKEN_TTL_SECONDS=120`, `CORS_ALLOWED_ORIGINS`, `REFRESH_TOKEN_PEPPER` ref, `RAZORPAY_WEBHOOK_SECRET` ref | MODIFY | `meesell-infra-builder` |
| 2 | K8s deployment config for `staging` namespace — `ACCESS_TOKEN_TTL_SECONDS=60`, `REFRESH_TOKEN_TTL_SECONDS=300` | MODIFY | `meesell-infra-builder` |
| 3 | `docs/runbooks/auth-secret-rotation.md` | NEW | `meesell-infra-builder` |

**Secrets status (confirmed from `meesell-infra-builder` MEMORY.md as of 2026-06-09):**
- `refresh-token-pepper` ✅ VERSION 1 LIVE
- `razorpay-webhook-secret` ✅ VERSION 1 LIVE
- `msg91-auth-key` ✅ VERSION 1 LIVE (⚠️ MSG91 IP whitelist last updated for 122.164.85.51 — verify OTP calls work in dev before marking done)
- `jwt-secret` ✅ VERSION 1 LIVE

Infra builder reads `docs/INFRASTRUCTURE_PLAYBOOK.md` first to locate the exact K8s manifest that references these secrets (live state differs from the CLAUDE.md `k8s/` tree snapshot).

### Docs

| # | File | Action |
|---|------|--------|
| 1 | `docs/V1_FEATURE_SPEC.md §F1` | Stamp "implemented YYYY-MM-DD PR#N" on FE-D5 acceptance criteria — done by backend coordinator AFTER feature/auth-otp merges to develop |
| 2 | `docs/BACKEND_ARCHITECTURE.md §7` | Add sentinel comment referencing the merge commit that proves §7 is LOCKED-on-disk — done by backend coordinator AFTER feature/auth-otp merges to develop |

---

## Documentation deliverables

These must exist alongside the merged code. Each is an acceptance gate item.

| # | Deliverable | Owner | When |
|---|-------------|-------|------|
| 1 | **OpenAPI entries** for `POST /otp/send`, `POST /otp/verify`, `POST /refresh`, `POST /logout`, `GET /me` — auto-generated from Pydantic schemas in `iam/schemas.py`; reviewed in the backend group PR | `meesell-api-routes-builder` | In PR `feature/auth-otp/backend` |
| 2 | **AuthService inline docstring** describing in-memory signal + RefreshInterceptor flow + `withCredentials` scope | `meesell-angular-service-builder` | In PR `feature/auth-otp/frontend` |
| 3 | **`auth-secret-rotation.md` runbook** — how to rotate `REFRESH_TOKEN_PEPPER` without invalidating live sessions (uses Lua script's key-versioning capability per `BACKEND_ARCHITECTURE.md §4.B`) | `meesell-infra-builder` | In PR `feature/auth-otp/infra` |
| 4 | **`V1_FEATURE_SPEC.md §F1` implementation stamp** — "implemented YYYY-MM-DD PR#N" appended to the FE-D5 acceptance criteria block | `meesell-backend-coordinator` | After `feature/auth-otp` → `develop` merges |
| 5 | **`BACKEND_ARCHITECTURE.md §7` sentinel** — one-line commit reference proving §7 code is on-disk | `meesell-backend-coordinator` | After `feature/auth-otp` → `develop` merges |
| 6 | **`app.routes.ts` comment block** — one-line comment per route documenting `public` vs `guarded` status and which layout is used | `meesell-angular-service-builder` | In PR `feature/auth-otp/frontend` |

---

## Dispatch templates

### Template A — `meesell-database-builder`

**Dispatched by:** `meesell-backend-coordinator`
**Phase:** A (first, independent)
**Branch:** `feature/auth-otp/backend` (database-builder commits here)

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-auth-otp-backend-session-1
Lead: meesell-backend-coordinator

## Your mission
Create the `users` SQLAlchemy ORM model and the Alembic migration that creates the `users` table.
This is the data foundation for the iam module. Do NOT write any route handlers, service logic, or JWT code.

## Mandatory reads (in this order)
1. docs/BACKEND_ARCHITECTURE.md §0.D (database baseline — 13 tables, head f31c75438e61)
2. docs/MVP_ARCHITECTURE.md §2.1 (users table DDL — authoritative column spec)
3. docs/BACKEND_ARCHITECTURE.md §3 (file structure — shared/models/ location)
4. docs/BACKEND_ARCHITECTURE.md §5 (shared/ layer — config + session factory)
5. .claude/agent-memory/meesell-database-builder/MEMORY.md

## Acceptance criteria
- [ ] `backend/app/shared/models/user.py` created with `User` SQLAlchemy ORM model:
  - `id`: UUID PK, `server_default=func.gen_random_uuid()`
  - `phone`: `VARCHAR(15) NOT NULL UNIQUE` (E.164 format, validated at service layer)
  - `email`: `VARCHAR(255) NULL`
  - `plan`: `VARCHAR(20) NOT NULL DEFAULT 'free'`
  - `created_at`: `TIMESTAMPTZ NOT NULL DEFAULT now()`
  - `last_login_at`: `TIMESTAMPTZ NULL`
  - `__tablename__ = "users"`
- [ ] Alembic migration at `backend/alembic/versions/<rev>_iam_users.py`:
  - `upgrade()`: CREATE TABLE users with all 6 columns + UNIQUE constraint on phone
  - `downgrade()`: DROP TABLE users
  - `down_revision` chains from current head `f31c75438e61`
  - Migration tested locally: `alembic upgrade head` succeeds; `alembic downgrade -1` succeeds
- [ ] `backend/app/shared/models/__init__.py` exports `User`
- [ ] No other files modified

## Hard constraints
- Do NOT write any route handlers, schemas, service logic, or JWT code
- Do NOT add columns beyond the 6 in MVP_ARCH §2.1 (no `name`, no `verified_at`, no extra cols)
- `phone` column is VARCHAR(15) — E.164 format; regex validation lives in iam schemas, NOT in the ORM model
- `plan` column default is `'free'` string — NOT an enum type (enum lives in Python, not Postgres, per BACKEND_ARCHITECTURE.md §0.D style)
- TIMESTAMPTZ on all timestamps — NOT TIMESTAMP (timezone-aware is the invariant across all 13 tables)
- UUID PK via `server_default=func.gen_random_uuid()` — NOT `default=uuid4()` in Python (server-side generation is the locked pattern per §0.D)
- `alembic.ini` and `alembic/env.py` — READ-ONLY; do NOT modify migration setup

## Files you MAY touch
- `backend/app/shared/models/user.py` (NEW)
- `backend/app/shared/models/__init__.py` (MODIFY — add User export)
- `backend/alembic/versions/<rev>_iam_users.py` (NEW)

## Files you must NOT touch
- Any file under `backend/app/modules/`
- `backend/app/core/auth.py`
- `backend/app/config.py`
- `backend/app/main.py`
- Any file under `backend/app/adapters/`
- Any test files
- Any frontend or infra files

## Final report format
```
REPORT: meesell-database-builder
Session: mesell-auth-otp-backend-session-1
Status: COMPLETE | BLOCKED | PARTIAL

Files created:
- backend/app/shared/models/user.py
- backend/alembic/versions/<actual_rev>_iam_users.py (down_revision: f31c75438e61)

Files modified:
- backend/app/shared/models/__init__.py

Migration test results:
- alembic upgrade head: PASS | FAIL (paste output)
- alembic downgrade -1: PASS | FAIL (paste output)

Memory update: DONE (.claude/agent-memory/meesell-database-builder/auth_otp_feature.md written + committed) | SKIPPED (reason: <why>)

Blockers / notes:
<none | specific issue>
```
```

---

### Template B — `meesell-services-builder`

**Dispatched by:** `meesell-backend-coordinator`
**Phase:** A (parallel with database-builder)
**Branch:** `feature/auth-otp/backend`

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-auth-otp-backend-session-1
Lead: meesell-backend-coordinator

## Your mission
Create the MSG91 SMS adapter at `backend/app/adapters/msg91.py` per BACKEND_ARCHITECTURE.md §6.C.
This adapter is called by the iam module to send OTP codes. Do NOT write iam service logic — just the adapter.

## Mandatory reads (in this order)
1. docs/BACKEND_ARCHITECTURE.md §6.C (MSG91 adapter spec — async, Msg91Response dataclass, send_otp signature)
2. docs/BACKEND_ARCHITECTURE.md §6 (adapters/ layer rules — all async, transport retry only, no business logic)
3. docs/BACKEND_ARCHITECTURE.md §5.D (config.py — MSG91_AUTH_KEY + MSG91_TEMPLATE_ID env vars)
4. .claude/agent-memory/meesell-services-builder/MEMORY.md

## Acceptance criteria
- [ ] `backend/app/adapters/msg91.py` created with:
  - `Msg91Response` dataclass: `success: bool`, `request_id: Optional[str]`, `error: Optional[str]`
  - `MSG91Adapter` class with `async def send_otp(self, phone: str, otp: str, template_id: str) -> Msg91Response`
  - Uses `settings.MSG91_AUTH_KEY` from `shared/config.settings` — NO `os.getenv()` direct reads (§6 locked rule)
  - 1-retry exponential backoff on transport failure per §6.C
  - Returns `Msg91Response(success=False, error=...)` on failure — does NOT raise (this is the documented exception to the raise-on-failure pattern per §6.G)
  - HTTP client: `httpx.AsyncClient` (async, not `requests`)
  - Endpoint: MSG91 OTP send API v5 (`https://control.msg91.com/api/v5/otp`)
- [ ] `backend/app/adapters/__init__.py` exports `MSG91Adapter`
- [ ] No other files modified

## Hard constraints
- Do NOT call `os.getenv()` — all settings come from `shared/config.settings` (§6.G locked rule; CI linter enforces this)
- `send_otp` is async — no sync wrappers
- Transport retry: maximum 1 retry on connection error or 5xx, then return `Msg91Response(success=False)` — do NOT raise
- Do NOT implement OTP generation, rate limiting, or Valkey storage — those are in iam/service.py (auth-builder)
- Do NOT implement `send_bulk_otp` or any method beyond `send_otp` — V1 scope only

## Files you MAY touch
- `backend/app/adapters/msg91.py` (NEW)
- `backend/app/adapters/__init__.py` (MODIFY — add MSG91Adapter export)

## Files you must NOT touch
- Any file under `backend/app/modules/`
- `backend/app/core/auth.py`
- `backend/app/config.py`
- `backend/app/main.py`
- Any other adapter file (`gcs.py`, `gemini.py`, etc.)
- Any test files
- Any frontend or infra files

## Final report format
```
REPORT: meesell-services-builder
Session: mesell-auth-otp-backend-session-1
Status: COMPLETE | BLOCKED | PARTIAL

Files created:
- backend/app/adapters/msg91.py

Files modified:
- backend/app/adapters/__init__.py

send_otp signature implemented:
async def send_otp(self, phone: str, otp: str, template_id: str) -> Msg91Response

Memory update: DONE (.claude/agent-memory/meesell-services-builder/auth_otp_feature.md written + committed) | SKIPPED (reason: <why>)

Blockers / notes:
<none | specific issue>
```
```

---

### Template C — `meesell-auth-builder`

**Dispatched by:** `meesell-backend-coordinator`
**Phase:** B (after database-builder + services-builder complete)
**Branch:** `feature/auth-otp/backend`

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-auth-otp-backend-session-1
Lead: meesell-backend-coordinator

## Your mission
Build the iam module's core: service layer (verify_otp_and_issue_tokens, rotate_refresh_token, revoke_refresh_token, send_otp_for_login, get_profile, capture_razorpay_webhook), repository layer, domain types, exception hierarchy, Lua rotation script, and amend core/auth.py + config.py for FE-D5.
This is the cryptographic and session-management heart of the auth feature.

## Mandatory reads (in this order)
1. docs/BACKEND_ARCHITECTURE.md §4.B (FE-D5 amendment — full text; HMAC pepper, Lua script, cookie attrs, EVALSHA pattern)
2. docs/BACKEND_ARCHITECTURE.md §4.G (FE-D5 CORS amendment — CORS_ALLOW_CREDENTIALS, CORS_ALLOWED_ORIGINS, withCredentials scope)
3. docs/BACKEND_ARCHITECTURE.md §7 (iam module spec — §7.A preamble, §7.B endpoint contracts, §7.C service layer, §7.D repository, §7.F domain types, §7.G exceptions, §7.H adapter usage)
4. docs/BACKEND_ARCHITECTURE.md §5.D (config.py env-var registry — ACCESS_TOKEN_TTL_SECONDS, REFRESH_TOKEN_TTL_SECONDS, REFRESH_TOKEN_PEPPER)
5. docs/BACKEND_ARCHITECTURE.md §5.C (Valkey DB routing — DB 0 for OTP + refresh allowlist; SCRIPT LOAD pattern)
6. docs/V1_FEATURE_SPEC.md §F1 (FE-D5 acceptance criteria)
7. .claude/agent-memory/meesell-auth-builder/MEMORY.md

## Acceptance criteria
- [ ] `backend/app/modules/iam/__init__.py` created (empty or re-exports)
- [ ] `backend/app/modules/iam/domain.py` created:
  - `OtpRecord`: fields `otp: str`, `expires_at: float`, `attempts: int = 0`
  - `RefreshAllowlistEntry`: fields `user_id: str`, `issued_at: int`, `ip: str`
- [ ] `backend/app/modules/iam/exceptions.py` created with 8 subclasses of `MeesellError`:
  - `IamError` (base), `InvalidPhoneFormatError`, `OtpInvalidError`, `OtpAttemptsExceededError`, `OtpExpiredError`, `Msg91UnavailableError`, `RefreshInvalidError`, `WebhookSignatureInvalidError`
- [ ] `backend/app/modules/iam/lua/rotate_refresh.lua` created — VERBATIM from §7.B.3:
  ```lua
  if redis.call('GET', KEYS[1]) then
    redis.call('DEL', KEYS[1])
    redis.call('SET', KEYS[2], ARGV[1], 'EX', ARGV[2])
    return 1
  else
    return 0
  end
  ```
- [ ] `backend/app/modules/iam/repository.py` created with locked methods (all async, SQLAlchemy 2.0 typed):
  - `get_user_by_phone`, `get_user_by_id`, `upsert_user_on_login`, `update_last_login`
- [ ] `backend/app/modules/iam/service.py` created — `IamService` class with:
  - `send_otp_for_login(phone)`: generate 6-digit OTP via `secrets.choice("0123456789", 6)`; store in Valkey DB 0 key `otp:{phone}` as JSON `OtpRecord` with TTL 5 min; call `msg91_adapter.send_otp`; raise `Msg91UnavailableError` if `success=False`
  - `verify_otp_and_issue_tokens(phone, otp, client_ip)`: fetch `OtpRecord` from Valkey DB 0; validate OTP + expiry + attempts; upsert user; generate access JWT (HS256 `{sub, exp, plan, iat}`); generate refresh token (`secrets.token_urlsafe(48)`); compute `refresh_key = "cache:refresh:" + hmac.new(REFRESH_TOKEN_PEPPER.encode(), token.encode(), hashlib.sha256).hexdigest()`; store `RefreshAllowlistEntry` JSON in Valkey DB 0 with `EX REFRESH_TOKEN_TTL_SECONDS`; emit `auth.login.success` / `auth.login.failed` audit events via direct ORM write (documented exception per §7.B.2)
  - `rotate_refresh_token(refresh_cookie, client_ip)`: compute `old_key`; invoke Lua script via `EVALSHA` (fallback `EVAL`); if script returns 0 → raise `RefreshInvalidError`; generate new tokens; emit `auth.token.refreshed` / `auth.token.refresh_failed` audit
  - `revoke_refresh_token(refresh_cookie, user_id)`: DEL allowlist entry; emit `auth.logout` audit
  - `get_profile(user_id)`: read `users` row via `iam.repository.get_user_by_id`
  - `capture_razorpay_webhook(payload, signature)`: verify via `razorpay_adapter.verify_webhook_signature`; emit `razorpay.webhook.captured`
  - `SCRIPT LOAD` of `rotate_refresh.lua` at service init; cache digest on instance
- [ ] `backend/app/core/auth.py` amended:
  - Remove `JWT_EXPIRY_DAYS` references; use `settings.ACCESS_TOKEN_TTL_SECONDS`
  - `get_current_user` dep signature UNCHANGED; `CurrentUser(user_id, plan)` shape UNCHANGED
- [ ] `backend/app/config.py` amended:
  - Add: `ACCESS_TOKEN_TTL_SECONDS: int = 900`
  - Add: `REFRESH_TOKEN_TTL_SECONDS: int = 604800`
  - Add: `REFRESH_TOKEN_PEPPER: str` (Secret Manager ref)
  - Add: `RAZORPAY_WEBHOOK_SECRET: str` (Secret Manager ref)
  - Add: `CORS_ALLOWED_ORIGINS: list[str]`
  - Add: `CORS_ALLOW_CREDENTIALS: bool = True`
  - Remove: `JWT_EXPIRY_DAYS` field

## Hard constraints
- Lua script: VERBATIM from §7.B.3 — do NOT use MULTI/EXEC pipeline (Lua is the locked primitive per §4.B counter-proposal #1)
- HMAC key: `hmac.new(settings.REFRESH_TOKEN_PEPPER.encode(), token.encode(), hashlib.sha256).hexdigest()` — NOT `hashlib.sha256(token).hexdigest()`
- Allowlist lookup: `secrets.compare_digest(computed_key, stored_key)` — NEVER `==` (timing-attack mitigation)
- Cookie `Path=/api/v1/auth` — NOT `Path=/auth` (browser path-matching requires the full `/api/v1/auth` prefix; `Path=/auth` would miss all browser cookie sends)
- Access JWT: `{sub: str(user_id), exp: now + settings.ACCESS_TOKEN_TTL_SECONDS, plan: user.plan, iat: now}` — claim shape locked per §4.B + MVP_ARCH §11.7
- Refresh token: `secrets.token_urlsafe(48)` — NOT a JWT; NOT `uuid4()`
- OTP: 6-digit numeric only; `secrets.choice` NOT `random.randint` (cryptographically secure)
- `iam` is a LEAF module: service.py calls NO other module's service.py (only adapters + core + shared)
- SCRIPT LOAD at service init, EVALSHA on every rotation call, EVAL fallback on NOSCRIPT
- No `os.getenv()` — all settings from `shared/config.settings`

## Files you MAY touch
- `backend/app/modules/iam/__init__.py` (NEW)
- `backend/app/modules/iam/service.py` (NEW)
- `backend/app/modules/iam/repository.py` (NEW)
- `backend/app/modules/iam/domain.py` (NEW)
- `backend/app/modules/iam/exceptions.py` (NEW)
- `backend/app/modules/iam/lua/rotate_refresh.lua` (NEW)
- `backend/app/core/auth.py` (MODIFY — TTL + EVALSHA wiring only)
- `backend/app/config.py` (MODIFY — add FE-D5 env vars, remove JWT_EXPIRY_DAYS)
- `backend/tests/unit/iam/test_service.py` (NEW)

## Files you must NOT touch
- `backend/app/modules/iam/router.py` (owned by api-routes-builder)
- `backend/app/modules/iam/schemas.py` (owned by api-routes-builder)
- `backend/app/main.py` (owned by api-routes-builder)
- `backend/app/adapters/msg91.py` (owned by services-builder — READ, don't modify)
- `backend/app/shared/models/user.py` (owned by database-builder — READ, don't modify)
- Any frontend or infra files

## Final report format
```
REPORT: meesell-auth-builder
Session: mesell-auth-otp-backend-session-1
Status: COMPLETE | BLOCKED | PARTIAL

Files created:
- backend/app/modules/iam/__init__.py
- backend/app/modules/iam/service.py
- backend/app/modules/iam/repository.py
- backend/app/modules/iam/domain.py
- backend/app/modules/iam/exceptions.py
- backend/app/modules/iam/lua/rotate_refresh.lua
- backend/tests/unit/iam/test_service.py

Files modified:
- backend/app/core/auth.py (JWT_EXPIRY_DAYS removed; ACCESS_TOKEN_TTL_SECONDS wired; EVALSHA setup)
- backend/app/config.py (6 fields added, 1 removed)

Lua script SHA1 digest (from SCRIPT LOAD output):
<sha1>

config.py changes summary:
- Added: ACCESS_TOKEN_TTL_SECONDS, REFRESH_TOKEN_TTL_SECONDS, REFRESH_TOKEN_PEPPER, RAZORPAY_WEBHOOK_SECRET, CORS_ALLOWED_ORIGINS, CORS_ALLOW_CREDENTIALS
- Removed: JWT_EXPIRY_DAYS

Unit test results:
pytest tests/unit/iam/test_service.py -v: PASS | FAIL (paste summary)

Memory update: DONE (.claude/agent-memory/meesell-auth-builder/auth_otp_feature.md written + committed) | SKIPPED (reason: <why>)

Blockers / notes:
<none | specific issue>
```
```

---

### Template D — `meesell-api-routes-builder`

**Dispatched by:** `meesell-backend-coordinator`
**Phase:** C (after auth-builder completes)
**Branch:** `feature/auth-otp/backend`

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-auth-otp-backend-session-1
Lead: meesell-backend-coordinator

## Your mission
Create the iam module router (6 endpoints), Pydantic schemas, and wire the iam router into main.py.

## Mandatory reads (in this order)
1. docs/BACKEND_ARCHITECTURE.md §7.B (all 6 endpoint contracts — §7.B.1 through §7.B.6)
2. docs/BACKEND_ARCHITECTURE.md §7.E (schemas — OtpSendRequest, OtpVerifyRequest, TokenResponse, etc.)
3. docs/BACKEND_ARCHITECTURE.md §5A (presentation layer contract — response envelope + validation_message_id)
4. docs/BACKEND_ARCHITECTURE.md §4.B (FE-D5 — cookie Set-Cookie header format, rate limits per endpoint)
5. docs/BACKEND_ARCHITECTURE.md §4.G (CORS — withCredentials context for auth routes)
6. .claude/agent-memory/meesell-api-routes-builder/MEMORY.md

## Acceptance criteria
- [ ] `backend/app/modules/iam/schemas.py` created with Pydantic v2 models:
  - `OtpSendRequest`: `phone: str` (regex `^\+91[6-9]\d{9}$`)
  - `OtpVerifyRequest`: `phone: str`, `otp: str` (len 6, digits only)
  - `TokenResponse`: `access_token: str`, `token_type: str = "bearer"`, `expires_in: int`
  - `UserProfileResponse`: `id: UUID`, `phone: str`, `email: Optional[str]`, `plan: str`, `created_at: datetime`
  - `MessageResponse`: `message: str`
- [ ] `backend/app/modules/iam/router.py` created with `APIRouter(prefix="/api/v1/auth", tags=["auth"])`:
  - `POST /otp/send` → `iam.service.send_otp_for_login` (rate: 3/h/phone; no JWT required)
  - `POST /otp/verify` → `iam.service.verify_otp_and_issue_tokens` (rate: 10/h/phone; sets `Set-Cookie` header with refresh token)
  - `POST /refresh` → `iam.service.rotate_refresh_token` (rate: 60/h/user; cookie-only auth; no JWT required)
  - `POST /logout` → `iam.service.revoke_refresh_token` (JWT optional — accepts both; clears cookie via `Max-Age=0`)
  - `GET /me` → `iam.service.get_profile` (JWT required via `Depends(get_current_user)`)
  - `POST /webhooks/razorpay` → `iam.service.capture_razorpay_webhook` (Razorpay signature auth only)
- [ ] Cookie Set-Cookie format on `/otp/verify` response:
  `refresh_token=<token>; Domain=.mesell.xyz; Path=/api/v1/auth; HttpOnly; Secure; SameSite=Strict; Max-Age=<REFRESH_TOKEN_TTL_SECONDS>`
- [ ] Cookie clear on `/logout` response:
  `refresh_token=; Domain=.mesell.xyz; Path=/api/v1/auth; HttpOnly; Secure; SameSite=Strict; Max-Age=0`
- [ ] `backend/app/main.py` amended:
  - Import `iam_router` from `app.modules.iam.router`
  - Mount on app: `app.include_router(iam_router)`
  - Remove old `auth_router` mount if still present from scaffold
- [ ] `backend/tests/unit/iam/test_router.py` created (httpx AsyncClient tests for at least happy-path of each endpoint)
- [ ] `backend/tests/integration/test_auth_otp_integration.py` created (full OTP send → verify → refresh → logout flow; mocks MSG91 adapter)

## Hard constraints
- Cookie `Path=/api/v1/auth` — NOT `Path=/auth`
- `Set-Cookie` header for `/logout` uses `Max-Age=0` to clear — NOT `expires=<past-date>`
- `/refresh` does NOT require `Authorization: Bearer` header — refresh cookie IS the credential
- `/logout` accepts both (with or without valid access JWT) — idempotent
- Rate-limit decorators per §4.G/§4.H for each route (cite exact limits: 3/h/phone for send, 10/h/phone for verify, 60/h/user for refresh)
- All response models use the §5A presentation envelope shape
- OpenAPI summary/description on each endpoint (these become the auto-generated API docs)

## Files you MAY touch
- `backend/app/modules/iam/router.py` (NEW)
- `backend/app/modules/iam/schemas.py` (NEW)
- `backend/app/main.py` (MODIFY — mount iam_router, remove old auth_router)
- `backend/tests/unit/iam/test_router.py` (NEW)
- `backend/tests/integration/test_auth_otp_integration.py` (NEW)

## Files you must NOT touch
- `backend/app/modules/iam/service.py` (owned by auth-builder — READ, don't modify)
- `backend/app/modules/iam/domain.py` (owned by auth-builder — READ)
- `backend/app/modules/iam/exceptions.py` (owned by auth-builder — READ)
- `backend/app/core/auth.py`
- `backend/app/config.py`
- `backend/app/adapters/`
- `backend/app/shared/models/`
- Any frontend or infra files

## Final report format
```
REPORT: meesell-api-routes-builder
Session: mesell-auth-otp-backend-session-1
Status: COMPLETE | BLOCKED | PARTIAL

Files created:
- backend/app/modules/iam/router.py (6 endpoints)
- backend/app/modules/iam/schemas.py (N Pydantic models)
- backend/tests/unit/iam/test_router.py
- backend/tests/integration/test_auth_otp_integration.py

Files modified:
- backend/app/main.py (iam_router mounted; old auth_router removed: yes/no)

Endpoint list:
- POST /api/v1/auth/otp/send
- POST /api/v1/auth/otp/verify
- POST /api/v1/auth/refresh
- POST /api/v1/auth/logout
- GET /api/v1/auth/me
- POST /api/v1/webhooks/razorpay

Unit test results: PASS | FAIL (paste summary)
Integration test results: PASS | FAIL (paste summary)
OpenAPI review: confirmed auto-generated from schemas

Memory update: DONE (.claude/agent-memory/meesell-api-routes-builder/auth_otp_feature.md written + committed) | SKIPPED (reason: <why>)

Blockers / notes:
<none | specific issue>
```
```

---

### Template E — `meesell-angular-service-builder`

**Dispatched by:** `meesell-frontend-coordinator`
**Phase:** D (after backend group PR merges to feature/auth-otp, or in parallel if working against API spec)
**Branch:** `feature/auth-otp/frontend`

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-auth-otp-frontend-session-1
Lead: meesell-frontend-coordinator

## Your mission
Implement the Angular auth service layer: AuthService (signal-based in-memory access token), auth.interceptor.ts (JWT Bearer), refresh.interceptor.ts (silent 401 handler), auth.guard.ts (route guard), and wire the 3 public auth routes in app.routes.ts + app.config.ts.

## Mandatory reads (in this order)
1. docs/FRONTEND_ARCHITECTURE.md (full — AuthService location in core/, interceptor conventions, auth-layout, app.routes.ts structure)
2. docs/BACKEND_ARCHITECTURE.md §4.B FE-D5 amendment (split-token contract — in-memory signal, refresh cookie, withCredentials scope)
3. docs/BACKEND_ARCHITECTURE.md §4.G amendment (CORS — ONLY /api/v1/auth/* gets withCredentials:true)
4. docs/V1_FEATURE_SPEC.md §F1 FE-D5 acceptance criteria
5. docs/plans/module_federation/MASTER_PLAN.md §4.2 (auth is the LAST federated remote; login/signup/otp-verify live in shell for V1 — DO NOT add federation boilerplate)
6. .claude/agent-memory/meesell-angular-service-builder/MEMORY.md

## Acceptance criteria
- [ ] `frontend/src/app/core/services/auth.service.ts` implemented:
  - `private readonly _token = signal<string | null>(null)` (in-memory; never localStorage/sessionStorage)
  - `readonly token = this._token.asReadonly()` (public read-only signal)
  - `sendOtp(phone: string): Observable<void>` → POST /api/v1/auth/otp/send
  - `verifyOtp(phone: string, otp: string): Observable<void>` → POST /api/v1/auth/otp/verify; on success: stores returned `access_token` in `_token` signal
  - `logout(): Observable<void>` → POST /api/v1/auth/logout (withCredentials: true); on complete: `_token.set(null)`, redirect to /login
  - `getProfile(): Observable<UserProfile>` → GET /api/v1/auth/me
  - Inline docstring: "Access token is held in-memory via Angular signal. Never stored in localStorage or sessionStorage. Refresh token is an HttpOnly cookie owned by the backend. Silent refresh is handled by RefreshInterceptor."
- [ ] `frontend/src/app/core/interceptors/auth.interceptor.ts` modified:
  - Reads `inject(AuthService).token()` signal
  - If token is non-null: clones request with `Authorization: Bearer <token>` header
  - Sets `withCredentials: true` ONLY if `req.url.includes('/api/v1/auth/')` — all other calls: false
- [ ] `frontend/src/app/core/interceptors/refresh.interceptor.ts` created:
  - Catches `HttpErrorResponse` with `status === 401` on non-auth-route requests
  - Calls POST /api/v1/auth/refresh (withCredentials: true, no body — cookie is auto-sent)
  - On refresh success: `AuthService._token.set(newAccessToken)`; retries original request
  - On refresh failure: calls `AuthService.logout()`; redirects to /login
  - Uses BehaviorSubject + switchMap to deduplicate concurrent 401s (refresh storm prevention)
- [ ] `frontend/src/app/core/guards/auth.guard.ts` modified:
  - `export const authGuard: CanActivateFn = () => { const t = inject(AuthService).token(); return t ? true : inject(Router).parseUrl('/login'); }`
  - Synchronous — no async, no HTTP call (signal is sync)
- [ ] `frontend/src/app/app.routes.ts` modified:
  - Three public routes added (NOT guarded by authGuard):
    ```typescript
    { path: 'login', loadComponent: () => import('./features/auth/login/login.component').then(m => m.LoginComponent) }
    { path: 'signup', loadComponent: () => import('./features/auth/signup/signup.component').then(m => m.SignupComponent) }
    { path: 'otp-verify', loadComponent: () => import('./features/auth/otp-verify/otp-verify.component').then(m => m.OtpVerifyComponent) }
    ```
  - Existing shell route continues to be guarded by authGuard
  - Comment block on each auth route: `// PUBLIC — uses auth-layout; no authGuard`
- [ ] `frontend/src/app/app.config.ts` modified:
  - Add `refreshInterceptor` to `withInterceptors([..., refreshInterceptor])`
- [ ] `frontend/src/app/core/services/auth.service.spec.ts` created — at minimum: token signal starts null; verifyOtp success sets signal; logout clears signal and redirects

## Hard constraints
- Access token MUST be held in `signal<string | null>` — NEVER `localStorage.setItem`, NEVER `sessionStorage`, NEVER a class property (must be a signal for reactivity)
- `withCredentials: true` ONLY on URLs containing `/api/v1/auth/` — NOT globally (leaks unrelated cookies if applied globally)
- RefreshInterceptor MUST NOT intercept 401s on auth routes themselves (to prevent infinite refresh loop on /otp/send 401, /otp/verify 401)
- Refresh storm prevention: use BehaviorSubject or similar to ensure only ONE concurrent /auth/refresh call is in-flight regardless of how many 401s arrive simultaneously
- `auth.guard.ts` is synchronous — signal is synchronous; no `tap`, no HTTP call inside the guard
- No NgModules — all components/services are standalone
- OnPush change detection strategy on all components
- No direct PrimeNG imports in `core/` or `features/` — only `@mee/ui` wrappers

## Files you MAY touch
- `frontend/src/app/core/services/auth.service.ts` (MODIFY)
- `frontend/src/app/core/interceptors/auth.interceptor.ts` (MODIFY)
- `frontend/src/app/core/interceptors/refresh.interceptor.ts` (NEW)
- `frontend/src/app/core/guards/auth.guard.ts` (MODIFY)
- `frontend/src/app/app.routes.ts` (MODIFY — auth routes only)
- `frontend/src/app/app.config.ts` (MODIFY — register refreshInterceptor)
- `frontend/src/app/core/services/auth.service.spec.ts` (NEW)

## Files you must NOT touch
- `frontend/src/app/features/auth/` (owned by angular-component-builder — provide interface only)
- `frontend/src/app/ui/` (Layer 2 — unchanged)
- `frontend/src/app/layouts/` (Layer 3 — unchanged; auth-layout already scaffolded in Wave 2B)
- `frontend/src/app/design-system/` (Layer 1 — unchanged)
- Any backend or infra files

## Final report format
```
REPORT: meesell-angular-service-builder
Session: mesell-auth-otp-frontend-session-1
Status: COMPLETE | BLOCKED | PARTIAL

Files created:
- frontend/src/app/core/interceptors/refresh.interceptor.ts
- frontend/src/app/core/services/auth.service.spec.ts

Files modified:
- frontend/src/app/core/services/auth.service.ts
- frontend/src/app/core/interceptors/auth.interceptor.ts
- frontend/src/app/core/guards/auth.guard.ts
- frontend/src/app/app.routes.ts
- frontend/src/app/app.config.ts

AuthService public interface:
- token: Signal<string | null>
- sendOtp(phone): Observable<void>
- verifyOtp(phone, otp): Observable<void>
- logout(): Observable<void>
- getProfile(): Observable<UserProfile>

Auth spec results:
ng test -- --include='**/auth.service.spec.ts' : PASS | FAIL (paste summary)

Build check: pnpm build succeeded in <Xs> (target < 90s)

Memory update: DONE (.claude/agent-memory/meesell-angular-service-builder/auth_otp_feature.md written + committed) | SKIPPED (reason: <why>)

Blockers / notes:
<none | specific issue>
```
```

---

### Template F — `meesell-angular-component-builder`

**Dispatched by:** `meesell-frontend-coordinator`
**Phase:** D (after angular-service-builder completes — components inject AuthService)
**Branch:** `feature/auth-otp/frontend`

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-auth-otp-frontend-session-1
Lead: meesell-frontend-coordinator

## Your mission
Build the 3 auth page components: LoginComponent, SignupComponent, OtpVerifyComponent.
Each uses the auth-layout, reactive forms, and injects AuthService.

## Mandatory reads (in this order)
1. docs/FRONTEND_ARCHITECTURE.md (Layer 2 mee-* UI kit; Layer 3 auth-layout; Layer 4 features structure; non-negotiable rules)
2. docs/FRONTEND_ARCHITECTURE.md — MeeAuthLayoutComponent spec (centered card layout, already scaffolded in Wave 2B)
3. docs/V1_FEATURE_SPEC.md §F1 (auth user journey: phone → OTP → JWT)
4. docs/BACKEND_ARCHITECTURE.md §7.E (schemas — OtpSendRequest, OtpVerifyRequest, TokenResponse — these are the exact API shapes)
5. .claude/agent-memory/meesell-angular-component-builder/MEMORY.md

## Acceptance criteria
- [ ] `frontend/src/app/features/auth/login/login.component.ts` created:
  - Standalone, OnPush
  - Reactive form: `phone: FormControl` with validators (required, pattern `^\+91[6-9]\d{9}$`)
  - Injects `AuthService`, `Router`
  - `onSubmit()`: calls `authService.sendOtp(phone)`; on success: navigate to `/otp-verify?phone=<phone>`
  - Uses `mee-input` (with `prefix="+91"`), `mee-button` — NO direct PrimeNG imports
  - Loading signal (`loading = signal(false)`) for button disabled/loading state
  - Error display for invalid phone format using `mee-input` error prop
- [ ] `frontend/src/app/features/auth/signup/signup.component.ts` created:
  - Same phone OTP flow as login (same backend endpoints — backend upserts user on verify)
  - Form: `phone: FormControl`, `email?: FormControl` (optional)
  - Link to `/login` for existing users
- [ ] `frontend/src/app/features/auth/otp-verify/otp-verify.component.ts` created:
  - Reads `phone` from route query param on init
  - `mee-otp-input` (length=6) for OTP entry
  - `onVerify(otp)`: calls `authService.verifyOtp(phone, otp)`; on success: navigate to `/dashboard`
  - Resend OTP link: enabled after 30 s (countdown signal); calls `authService.sendOtp(phone)` on click
  - Rate-limit error (429): display "Too many attempts. Try again in X minutes."
  - Expired OTP error (401 with specific message): display "OTP expired. Request a new one."
- [ ] `frontend/src/app/features/auth/login/login.component.spec.ts` created:
  - At minimum: form renders; invalid phone shows error; submit calls authService.sendOtp
- [ ] All components:
  - `standalone: true`
  - `changeDetection: ChangeDetectionStrategy.OnPush`
  - Use `MeeAuthLayoutComponent` (or its selector) as the wrapping layout (per auth-layout being Layer 3)
  - Mobile-first responsive: designed at 360px
  - NO direct PrimeNG imports — all UI via `@mee/ui` barrel

## Hard constraints
- Components inject `AuthService` — they do NOT hold any token locally
- NO localStorage, NO sessionStorage in component code
- Reactive Forms only — no template-driven forms
- `mee-otp-input` wraps `<p-inputOtp>` — use `mee-otp-input` selector, NOT `p-inputOtp` directly
- `mee-input` wraps `<p-inputText>` — use `mee-input`, NOT `p-inputText` directly
- OtpVerifyComponent: phone MUST come from route query params — NEVER hard-coded, NEVER from localStorage

## Files you MAY touch
- `frontend/src/app/features/auth/login/login.component.ts` (NEW)
- `frontend/src/app/features/auth/login/login.component.html` (NEW)
- `frontend/src/app/features/auth/login/login.component.spec.ts` (NEW)
- `frontend/src/app/features/auth/signup/signup.component.ts` (NEW)
- `frontend/src/app/features/auth/signup/signup.component.html` (NEW)
- `frontend/src/app/features/auth/otp-verify/otp-verify.component.ts` (NEW)
- `frontend/src/app/features/auth/otp-verify/otp-verify.component.html` (NEW)

## Files you must NOT touch
- `frontend/src/app/core/services/auth.service.ts` (owned by service-builder — READ only)
- `frontend/src/app/core/interceptors/` (owned by service-builder)
- `frontend/src/app/core/guards/` (owned by service-builder)
- `frontend/src/app/app.routes.ts` (owned by service-builder)
- `frontend/src/app/ui/` (Layer 2 — read-only)
- `frontend/src/app/layouts/` (Layer 3 — read-only; DO NOT modify auth-layout)
- Any backend or infra files

## Final report format
```
REPORT: meesell-angular-component-builder
Session: mesell-auth-otp-frontend-session-1
Status: COMPLETE | BLOCKED | PARTIAL

Files created:
- frontend/src/app/features/auth/login/login.component.ts
- frontend/src/app/features/auth/login/login.component.html
- frontend/src/app/features/auth/login/login.component.spec.ts
- frontend/src/app/features/auth/signup/signup.component.ts
- frontend/src/app/features/auth/signup/signup.component.html
- frontend/src/app/features/auth/otp-verify/otp-verify.component.ts
- frontend/src/app/features/auth/otp-verify/otp-verify.component.html

Component summary:
- LoginComponent: phone form, sendOtp(), navigate to /otp-verify
- SignupComponent: phone + optional email form, sendOtp(), navigate to /otp-verify
- OtpVerifyComponent: OTP input, verifyOtp(), 30s resend countdown, error states

UI primitives used: mee-input, mee-otp-input, mee-button (all from @mee/ui)
Layout: MeeAuthLayoutComponent wrapping all 3 components

Component spec results:
ng test -- --include='**/login.component.spec.ts' : PASS | FAIL

Build check: pnpm build succeeded in <Xs> (target < 90s)

Screenshots attached:
- LoginComponent at 360px: yes/no
- LoginComponent at 1280px: yes/no

Memory update: DONE (.claude/agent-memory/meesell-angular-component-builder/auth_otp_feature.md written + committed) | SKIPPED (reason: <why>)

Blockers / notes:
<none | specific issue>
```
```

---

### Template G — `meesell-infra-builder`

**Dispatched by:** Founder (infra-builder is standalone — dispatched directly by founder, not by a lead)
**Phase:** A (can proceed in parallel with backend/frontend)
**Branch:** `feature/auth-otp/infra`

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-auth-otp-infra-session-1
Lead: meesell-infra-builder (standalone)

## Your mission
Wire the auth-otp env vars (ACCESS_TOKEN_TTL_SECONDS, REFRESH_TOKEN_TTL_SECONDS, CORS config) into the dev and staging K8s deployment configs; verify all 4 required secrets are referenced correctly; author the REFRESH_TOKEN_PEPPER rotation runbook.

## Mandatory reads (in this order)
1. docs/INFRASTRUCTURE_PLAYBOOK.md (full — live state is SSOT; do NOT blindly apply CLAUDE.md k8s/ tree)
2. docs/BACKEND_ARCHITECTURE.md §5.D (env-var registry — exact names and values for dev/staging/prod)
3. docs/BACKEND_ARCHITECTURE.md §4.B amendment (REFRESH_TOKEN_PEPPER purpose; rotation implications)
4. docs/BACKEND_ARCHITECTURE.md §4.G amendment (CORS_ALLOWED_ORIGINS, CORS_ALLOW_CREDENTIALS)
5. .claude/agent-memory/meesell-infra-builder/MEMORY.md

## Context: secrets status (from infra MEMORY.md)
- `refresh-token-pepper` ✅ VERSION 1 LIVE
- `razorpay-webhook-secret` ✅ VERSION 1 LIVE (2026-06-09)
- `msg91-auth-key` ✅ VERSION 1 LIVE
- `jwt-secret` ✅ VERSION 1 LIVE
- `langfuse-secret-key` NOT YET — do NOT touch this; it belongs to §6A dispatch

## Acceptance criteria
- [ ] K8s deployment config for `dev` namespace updated with:
  - `ACCESS_TOKEN_TTL_SECONDS=30` (env literal)
  - `REFRESH_TOKEN_TTL_SECONDS=120` (env literal)
  - `CORS_ALLOWED_ORIGINS=["https://dev.mesell.xyz"]` (or literal list per live ingress)
  - `CORS_ALLOW_CREDENTIALS=true`
  - `REFRESH_TOKEN_PEPPER` env ref → Secret Manager `refresh-token-pepper`
  - `RAZORPAY_WEBHOOK_SECRET` env ref → Secret Manager `razorpay-webhook-secret`
- [ ] K8s deployment config for `staging` namespace updated with:
  - `ACCESS_TOKEN_TTL_SECONDS=60`
  - `REFRESH_TOKEN_TTL_SECONDS=300`
  - `CORS_ALLOWED_ORIGINS=["https://staging.mesell.xyz"]` (or staging origin per live ingress)
  - Same REFRESH_TOKEN_PEPPER + RAZORPAY_WEBHOOK_SECRET refs
- [ ] `kubectl apply --dry-run=server -f <manifest>` ran clean for both namespaces
- [ ] `docs/runbooks/auth-secret-rotation.md` created documenting:
  - How to rotate REFRESH_TOKEN_PEPPER without invalidating live sessions
  - Key versioning: old sessions continue to work until their allowlist entry expires naturally (REFRESH_TOKEN_TTL_SECONDS max)
  - Step-by-step: (1) create new version in Secret Manager; (2) roll out deployment to pick up new env var; (3) old allowlist entries expire within REFRESH_TOKEN_TTL_SECONDS; (4) no forced logout of active users
  - Emergency revocation (all sessions): `FLUSHDB` on Valkey DB 0 OTP key pattern OR mass DEL of `cache:refresh:*` keys — documents the blast radius (all users logged out)
- [ ] No changes to secrets themselves — secrets are LIVE; only K8s manifest refs are updated
- [ ] `docs/status/feature_board_infra.md` row for `auth-otp` updated to `IN REVIEW` before pushing

## Hard constraints
- Read `docs/INFRASTRUCTURE_PLAYBOOK.md` FIRST — live state differs from the CLAUDE.md k8s/ snapshot; the playbook is SSOT
- Do NOT use `ACCESS_TOKEN_TTL_SECONDS=60s` format — use integer seconds (`60`), not string (`"60s"`)
- Do NOT touch `langfuse-secret-key` — that is §6A scope
- Do NOT touch any backend, frontend, or docs/plans/ files
- `kubectl apply --dry-run=server` is MANDATORY before any live apply
- Cost impact: these are env var additions — monthly cost delta is ₹0. State it explicitly in the PR body

## Files you MAY touch (consult INFRASTRUCTURE_PLAYBOOK.md for actual paths)
- K8s deployment manifest for `dev` namespace API pod (MODIFY)
- K8s deployment manifest for `staging` namespace API pod (MODIFY)
- `docs/runbooks/auth-secret-rotation.md` (NEW)
- `docs/status/feature_board_infra.md` (MODIFY — status update)

## Files you must NOT touch
- `k8s/postgres.yaml`, `k8s/valkey.yaml`, `k8s/ingress.yaml` — DOCUMENTATION-ONLY manifests per infra memory
- Any terraform files (secrets already live — no Terraform needed for this feature)
- Any backend or frontend files
- Any docs/plans/ files

## Final report format
```
REPORT: meesell-infra-builder
Session: mesell-auth-otp-infra-session-1
Status: COMPLETE | BLOCKED | PARTIAL

Files modified:
- <actual k8s dev manifest path> (ACCESS_TOKEN_TTL_SECONDS=30 + REFRESH_TOKEN_TTL_SECONDS=120 + CORS + secret refs)
- <actual k8s staging manifest path> (ACCESS_TOKEN_TTL_SECONDS=60 + REFRESH_TOKEN_TTL_SECONDS=300 + CORS + secret refs)
- docs/status/feature_board_infra.md (auth-otp → IN REVIEW)

Files created:
- docs/runbooks/auth-secret-rotation.md

Dry-run results:
kubectl apply --dry-run=server -f <dev manifest>: CLEAN | ERROR
kubectl apply --dry-run=server -f <staging manifest>: CLEAN | ERROR

Secrets verified live:
- refresh-token-pepper: ✅ VERSION 1 LIVE
- razorpay-webhook-secret: ✅ VERSION 1 LIVE
- msg91-auth-key: ✅ VERSION 1 LIVE
- jwt-secret: ✅ VERSION 1 LIVE

MSG91 IP whitelist note: <confirmed working | needs update for 122.164.85.51>

Cost impact: ₹0/month (env var additions only)

Memory update: DONE (.claude/agent-memory/meesell-infra-builder/auth_otp_feature.md written + committed) | SKIPPED (reason: <why>)

Blockers / notes:
<none | specific issue>
```
```

---

### Template H — `meesell-angular-ui-styler`

**Dispatched by:** `meesell-frontend-coordinator`
**Phase:** E (after angular-component-builder complete — components must exist before styling)
**Branch:** `feature/auth-otp/frontend`

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-auth-otp-frontend-session-1
Lead: meesell-frontend-coordinator

## Your mission
Apply Tailwind CSS mobile-first styling to the 3 auth page components (Login, Signup, OtpVerify).
The components are already built by angular-component-builder — your job is STYLING ONLY.
Do NOT modify TypeScript logic, template structure, or reactive form setup.

## Mandatory reads (in this order)
1. docs/FRONTEND_ARCHITECTURE.md (Layer 1 design tokens; Layer 2 mee-* component palette; Tailwind 4 config; non-negotiable UI rules)
2. docs/V1_FEATURE_SPEC.md §F1 (auth user journey — understand the screens before styling them)
3. frontend/src/app/features/auth/ (READ the existing component .html files before writing any SCSS — understand the HTML structure you are styling)
4. .claude/agent-memory/meesell-angular-ui-styler/MEMORY.md

## Acceptance criteria
- [ ] `frontend/src/app/features/auth/login/login.component.scss` created:
  - Centered card layout (max-width 400px on tablet+; full-width on mobile 360px)
  - Phone input row with "+91" prefix clearly visible
  - Submit button full-width, proper spacing
  - Error state visually distinct (uses design token for error colour — NOT hard-coded hex)
- [ ] `frontend/src/app/features/auth/signup/signup.component.scss` created:
  - Mirrors login card layout
  - Optional email field visually de-emphasised vs phone field
  - "Already have an account?" link correctly spaced at bottom
- [ ] `frontend/src/app/features/auth/otp-verify/otp-verify.component.scss` created:
  - OTP digit boxes evenly spaced, readable on 360px
  - Countdown timer text de-emphasised (smaller, muted colour)
  - Resend link visually disabled (greyed) until countdown reaches 0
  - Error states (rate-limit, expired) use alert colour from design tokens
- [ ] All 3 components:
  - Mobile-first: designed at 360px, tested at 768px and 1280px
  - NO hard-coded hex colours — use Tailwind design tokens or CSS custom properties from Layer 1
  - WCAG AA contrast on all text and interactive elements
  - Tailwind classes preferred over custom SCSS; custom SCSS only for structural overrides Tailwind cannot express
- [ ] `pnpm build` clean after styling changes (< 90s)
- [ ] Screenshots at 360px + 1280px for all 3 components included in PR body

## Hard constraints
- Styling ONLY — do NOT modify `.component.ts`, `.component.html`, or `.component.spec.ts` files
- No direct PrimeNG CSS overrides (e.g., no `.p-inputtext { ... }`) — override only via `mee-*` wrapper selectors or Tailwind utilities on the host element
- No `!important` in SCSS — if specificity is a problem, fix the selector chain, don't override it
- `MeeAuthLayoutComponent` provides the outer card shell — do NOT duplicate card styling in component SCSS (it lives in the layout layer)
- All spacing via Tailwind scale (4, 8, 12, 16, 24, 32 px) — NOT arbitrary values like `p-[13px]`
- OnPush components: avoid CSS that relies on DOM state not reflected in template bindings

## Files you MAY touch
- `frontend/src/app/features/auth/login/login.component.scss` (NEW)
- `frontend/src/app/features/auth/signup/signup.component.scss` (NEW)
- `frontend/src/app/features/auth/otp-verify/otp-verify.component.scss` (NEW)

## Files you must NOT touch
- `frontend/src/app/features/auth/**/*.ts` (owned by angular-component-builder)
- `frontend/src/app/features/auth/**/*.html` (owned by angular-component-builder)
- `frontend/src/app/features/auth/**/*.spec.ts` (owned by angular-component-builder)
- `frontend/src/app/core/` (owned by angular-service-builder)
- `frontend/src/app/ui/` (Layer 2 — read-only)
- `frontend/src/app/layouts/` (Layer 3 — read-only)
- `frontend/src/app/design-system/` (Layer 1 — read-only)
- Any backend or infra files

## Final report format
```
REPORT: meesell-angular-ui-styler
Session: mesell-auth-otp-frontend-session-1
Status: COMPLETE | BLOCKED | PARTIAL

Files created:
- frontend/src/app/features/auth/login/login.component.scss
- frontend/src/app/features/auth/signup/signup.component.scss
- frontend/src/app/features/auth/otp-verify/otp-verify.component.scss

Design decisions:
- Card layout approach: <describe>
- Colour tokens used: <list design token names>
- Custom SCSS (non-Tailwind): <describe any, or NONE>

Responsive: designed at 360px | tested at 768px | tested at 1280px

Build check: pnpm build succeeded in <Xs> (target < 90s)

Screenshots:
- Login 360px: attached
- Login 1280px: attached
- Signup 360px: attached
- OtpVerify 360px: attached

WCAG AA contrast: confirmed | issues found: <list>

Memory update: DONE (.claude/agent-memory/meesell-angular-ui-styler/auth_otp_feature.md written + committed) | SKIPPED (reason: <why>)

Blockers / notes:
<none | specific issue>
```
```

---

## Review + iteration protocol

### Backend group PR (`feature/auth-otp/backend` → `feature/auth-otp`)

**Reviewer:** `meesell-backend-coordinator`
**Template:** `.github/PULL_REQUEST_TEMPLATE/backend.md`

**What the backend lead checks before approving:**

| # | Check | Pass | Fail → re-dispatch |
|---|-------|------|--------------------|
| 1 | Lua script verbatim from §7.B.3: `if redis.call('GET', KEYS[1]) then ... DEL/SET ... return 1 end` | exact match | Lua uses MULTI/EXEC pipeline — re-dispatch auth-builder with §4.B counter-proposal #1 quoted |
| 2 | `EVALSHA` primary, `EVAL` fallback on `NOSCRIPT`, `SCRIPT LOAD` once at startup | present | Missing EVALSHA path — re-dispatch auth-builder citing §5.C |
| 3 | Allowlist lookup via `secrets.compare_digest()` — NOT `==` | present | `==` comparison — re-dispatch auth-builder citing §4.B timing-attack note |
| 4 | HMAC key shape: `hmac.new(REFRESH_TOKEN_PEPPER.encode(), token.encode(), hashlib.sha256).hexdigest()` | exact | Bare `sha256(token)` — re-dispatch auth-builder citing §4.B HMAC counter-proposal |
| 5 | Cookie `Path=/api/v1/auth` | exact | `Path=/auth` — re-dispatch api-routes-builder citing §4.B cookie path counter-proposal |
| 6 | `ACCESS_TOKEN_TTL_SECONDS` used in JWT exp — `JWT_EXPIRY_DAYS` removed from config.py | confirmed | `JWT_EXPIRY_DAYS` still present — re-dispatch auth-builder citing §4.B deprecation |
| 7 | `CORS_ALLOW_CREDENTIALS=true` on `/api/v1/auth/*` paths; `CORS_ALLOWED_ORIGINS` is explicit list NEVER `["*"]` | confirmed | Wildcard CORS — re-dispatch auth-builder with §4.G quoted |
| 8 | `/logout` clears cookie with `Max-Age=0` | confirmed | Expired-date clear — re-dispatch api-routes-builder |
| 9 | Alembic migration: upgrade + downgrade tested locally | evidence in PR | Missing — return PR to database-builder |
| 10 | Integration test covers OTP send → verify → refresh → logout chain | present | Missing chain — return PR to api-routes-builder |
| 11 | No `os.getenv()` in `adapters/msg91.py` | confirmed | Present — re-dispatch services-builder citing §6.G CI linter rule |

**Re-dispatch preamble template (use when any check above fails):**

```
PREVIOUS RUN FAILED — {check description}

[Paste original Template X here]

## Correction for this re-dispatch
The previous session failed check #{N}: {specific failure}.

Fix required: {exact fix per the check above}.

Read: docs/BACKEND_ARCHITECTURE.md {specific section and paragraph}.

This is iteration {M} of 3. If the fix is not applied by session-3, escalate to founder.
```

**Maximum iterations:** 3 per specialist. After 3 failed iterations: freeze the branch, open a blocker row on `docs/status/feature_board_backend.md`, escalate to founder.

---

### Frontend group PR (`feature/auth-otp/frontend` → `feature/auth-otp`)

**Reviewer:** `meesell-frontend-coordinator`
**Template:** `.github/PULL_REQUEST_TEMPLATE/frontend.md`

**What the frontend lead checks before approving:**

| # | Check | Pass | Fail → re-dispatch |
|---|-------|------|--------------------|
| 1 | `auth.service.ts`: `_token = signal<string \| null>(null)` — NOT localStorage/sessionStorage | confirmed | Any `localStorage.setItem` — re-dispatch service-builder with FE-D5 §4.B quoted |
| 2 | `withCredentials: true` ONLY on URLs containing `/api/v1/auth/` in auth.interceptor.ts | scoped correctly | Applied globally — re-dispatch service-builder citing §4.G "ONLY for /api/v1/auth/* calls" |
| 3 | `refresh.interceptor.ts`: refresh storm prevention — single in-flight /auth/refresh regardless of concurrent 401s | present (BehaviorSubject or equivalent) | Missing dedup — re-dispatch service-builder |
| 4 | `auth.guard.ts` is synchronous (signal read only, no async) | confirmed | Guard makes HTTP call or returns Observable — re-dispatch service-builder |
| 5 | No direct PrimeNG imports in `features/auth/` or `core/` | confirmed (ESLint clean) | `import { ... } from 'primeng/...'` found — re-dispatch component-builder with FRONTEND_ARCHITECTURE.md Layer 2 boundary quoted |
| 6 | All 3 components: `standalone: true`, `changeDetection: ChangeDetectionStrategy.OnPush` | confirmed | Missing either — re-dispatch component-builder |
| 7 | `pnpm build` < 90s (CLAUDE.md Decision 12) | < 90s | ≥ 90s — stop, escalate to founder (build budget exceeded) |
| 8 | Screenshots at 360px and 1280px attached for Login, Signup, OtpVerify | present | Missing — return to component-builder |
| 9 | OtpVerify reads phone from route query params — NOT from localStorage | confirmed | localStorage read — re-dispatch component-builder |
| 10 | Refresh interceptor does NOT intercept 401s from `/api/v1/auth/` routes | confirmed | Infinite refresh loop risk — re-dispatch service-builder |
| 11 | No hard-coded hex colours in `*.component.scss` — design tokens / Tailwind only | confirmed | Hard-coded hex found — re-dispatch ui-styler citing FRONTEND_ARCHITECTURE.md Layer 1 |
| 12 | No direct PrimeNG CSS class overrides in component SCSS (e.g. `.p-inputtext`) | confirmed | Override found — re-dispatch ui-styler; fix via mee-* host selector |
| 13 | All 3 components legible at 360px (screenshots in PR body) | present | Missing screenshots — return PR to ui-styler |
| 14 | `pnpm build` clean after SCSS additions | < 90s | Build broke or ≥ 90s — stop, investigate before re-dispatch |

**Re-dispatch preamble template (frontend):**

```
PREVIOUS RUN FAILED — {check description}

[Paste original Template E, F, or H here — whichever specialist failed]

## Correction for this re-dispatch
Previous session failed check #{N}: {specific failure}.
Fix: {exact fix}.
Read: {specific doc + section}.
Iteration {M} of 3.
```

**Maximum iterations:** 3 per specialist.

---

### Infra group PR (`feature/auth-otp/infra` → `feature/auth-otp`)

**Reviewer:** `meesell-infra-builder` (self-review, then founder gate)
**Template:** `.github/PULL_REQUEST_TEMPLATE/infra.md`

**What infra lead checks before self-approving:**

| # | Check | Pass | Fail → re-do |
|---|-------|------|--------------------|
| 1 | `kubectl apply --dry-run=server` clean for BOTH namespaces | both clean | Any error — fix before PR |
| 2 | `ACCESS_TOKEN_TTL_SECONDS=30` in dev, `=60` in staging (NOT `=60s` string) | integer | String format — fix manifest |
| 3 | `REFRESH_TOKEN_TTL_SECONDS=120` in dev, `=300` in staging | confirmed | Wrong values — re-check §5.D |
| 4 | All 4 secrets referenced by Secret Manager name (not hard-coded values) | SM refs | Hard-coded value — fix immediately |
| 5 | `auth-secret-rotation.md` describes versioning path AND emergency FLUSHDB path | both present | Missing either — complete runbook |
| 6 | Cost impact stated in PR body as ₹0 | stated | Missing — add to PR body |

---

## Acceptance gate

This feature is "done" (ready for `feature/auth-otp` → `develop` PR) when ALL of the following are true:

### All group PRs merged to `feature/auth-otp`
- [ ] `feature/auth-otp/backend` → `feature/auth-otp` merged (backend coordinator approved)
- [ ] `feature/auth-otp/frontend` → `feature/auth-otp` merged (frontend coordinator approved)
- [ ] `feature/auth-otp/infra` → `feature/auth-otp` merged (infra lead self-approved)

### CI gates green on `feature/auth-otp`
- [ ] gate-1 unit: all unit tests pass (backend unit/iam/ + frontend auth.service.spec.ts + login.component.spec.ts)
- [ ] gate-2 smoke: API health check + /auth/otp/send returns expected 200/422/429
- [ ] gate-3 lint: ruff (backend) + ng lint (frontend) both clean; no `os.getenv()` in adapters/
- [ ] gate-4 integration: `test_auth_otp_integration.py` passes (full OTP → verify → refresh → logout chain)
- [ ] gate-5 golden_roundtrip: N/A (no XLSX touched — gate-5 skipped for this feature)

### Manual acceptance criteria from `V1_FEATURE_SPEC.md §F1`
- [ ] User receives OTP within 10s of submit (tested in dev namespace with real MSG91 call)
- [ ] Wrong OTP rejected with 401; correct OTP returns access JWT + sets refresh cookie
- [ ] OTP expires after 5 min; resend allowed after 30s (frontend countdown)
- [ ] Access JWT TTL: 30s (dev), 60s (staging), 900s (prod) — verified via JWT decode
- [ ] Refresh token TTL: 120s (dev), 300s (staging) — verified via allowlist expiry
- [ ] Rate limit: 3 OTP requests per phone per hour → 4th returns 429
- [ ] `/auth/refresh` silently rotates: old cookie rejected (401) after rotation
- [ ] `/auth/logout` clears cookie and revokes allowlist entry; subsequent /auth/refresh with old cookie → 401
- [ ] Frontend: token() signal is null after page reload (in-memory only — no persistence)

### Documentation deliverables present
- [ ] OpenAPI docs for 5 iam endpoints rendered from Pydantic schemas
- [ ] `AuthService` has inline docstring describing split-token contract
- [ ] `docs/runbooks/auth-secret-rotation.md` exists and covers both versioning and emergency paths
- [ ] `app.routes.ts` has comment block on each auth route

### Founder gate
- [ ] All CI gates green on `feature/auth-otp`
- [ ] Founder reviews and approves `feature/auth-otp` → `develop` PR
- [ ] After merge to develop: backend coordinator stamps `V1_FEATURE_SPEC.md §F1` and `BACKEND_ARCHITECTURE.md §7`

---

## Memory management

Agents are stateless across sessions — the only continuity they have is their `MEMORY.md`. Without explicit memory updates after each specialist session, re-dispatches (retries, review-requested revisions, future cross-feature references) are blind to what was already built.

### Protocol — mandatory for every dispatch in this feature

Every dispatch template in this plan ends with a **Memory update** block. The agent MUST:

1. Create (or update) `.claude/agent-memory/{agent-name}/auth_otp_feature.md` — the feature memory file for this agent
2. Add a one-line pointer to it in their `MEMORY.md` index under `## auth-otp`
3. Commit both the code AND the memory file on the same branch (memory and code stay in sync)
4. Include `Memory update: DONE | SKIPPED (reason)` in the final report sent back to the lead

If the agent cannot write to memory (e.g., a blocker prevented code completion), they still write a memory entry recording the blocker and their partial state.

### Pre-dispatch memory seeding

The 3 **lead agents** are seeded with auth-otp awareness before the first dispatch (done by this planning session — see files created below). Specialist agents write their own memory when they complete their session; they do not need pre-seeding because they receive a full dispatch template with all context.

**Lead memory files created by this planning session:**
- `.claude/agent-memory/meesell-backend-coordinator/auth_otp_feature.md` ✅
- `.claude/agent-memory/meesell-frontend-coordinator/auth_otp_feature.md` ✅
- `.claude/agent-memory/meesell-infra-builder/auth_otp_feature.md` ✅

### Per-agent memory spec

What each agent MUST record in `auth_otp_feature.md` when they complete their session:

| Agent | What to record |
|-------|----------------|
| `meesell-backend-coordinator` | Which specialists were dispatched, which phase, PR# of feature/auth-otp/backend, blockers if any, feature_board_backend.md status |
| `meesell-frontend-coordinator` | Which specialists were dispatched, which phase, PR# of feature/auth-otp/frontend, blockers if any, feature_board_frontend.md status |
| `meesell-infra-builder` | Files written (exact paths), dry-run result, PR# of feature/auth-otp/infra, MSG91 IP whitelist confirmed/blocked |
| `meesell-database-builder` | `User` model column names + types, Alembic revision ID, current head after `alembic upgrade head`, `shared/models/__init__.py` export confirmed |
| `meesell-services-builder` | `Msg91Adapter` public method signatures (`send_otp`, `verify_otp` or equivalent), env var name used (`MSG91_AUTH_KEY`), async HTTP client used (httpx/aiohttp) |
| `meesell-auth-builder` | `IamService` public method signatures (6 methods), Lua SHA1 digest stored on instance (so the next session knows the `SCRIPT LOAD` pattern is in place), HMAC key format confirmed, cookie `Path` and `Domain` values used |
| `meesell-api-routes-builder` | 6 endpoint paths + HTTP verbs, Pydantic schema class names, how `iam_router` is mounted in `main.py` (prefix, tags), integration test file path |
| `meesell-angular-service-builder` | `AuthService` public API (signal name, method signatures), interceptor registration order in `app.config.ts`, route paths added to `app.routes.ts` |
| `meesell-angular-component-builder` | Component selectors, reactive form control names for each component, navigation targets, `mee-*` primitives used |
| `meesell-angular-ui-styler` | Tailwind design tokens used, any custom SCSS decisions, WCAG AA contrast confirmed, responsive breakpoints tested |

### Memory file template (use this structure for `auth_otp_feature.md`)

```markdown
---
name: auth-otp-feature
description: auth-otp Feature 1 — what this agent built, files it owns, contracts it implemented
metadata:
  type: project
---

Feature: auth-otp (Feature 1 of 9)
Branch: feature/auth-otp/{backend|frontend|infra}
Session: mesell-auth-otp-{group}-session-{N}
Date: YYYY-MM-DD
Status: COMPLETE | PARTIAL | BLOCKED

## What I built
<list of files created/modified with one-line description of what each does>

## Key contracts I implemented
<critical decisions, method signatures, config values — anything the next specialist needs to know>

## What the next agent in the chain needs from my output
<specific outputs: model shape, interface signatures, mounted paths, etc.>

## PR
feature/auth-otp/{backend|frontend|infra} PR #<N> — <status: open|merged|blocked>

## Blockers
<none | specific blocker with context>
```

---

## Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | **MSG91 IP whitelist mismatch in dev** | Medium — infra MEMORY.md notes the founder IP rotated to 122.164.85.51 on 2026-06-05 and the whitelist may not have been updated | High — `/auth/otp/send` returns `Msg91UnavailableError` in dev, blocking the integration test chain | Infra builder verifies MSG91 whitelist as part of Template G. Backend lead's smoke gate requires a real OTP send before marking gate-2 green. Fallback: use MSG91 test-sender credentials (no IP whitelist) for dev namespace only |
| 2 | **Lua script `EVALSHA` → `NOSCRIPT` after Valkey restart** | Low — Valkey restarts are rare in dev namespace; staging Valkey is more stable | Medium — rotation returns `NOSCRIPT`, causing `RefreshInvalidError` until `EVAL` fallback kicks in. If only `EVALSHA` is implemented (no fallback), every session breaks after a Valkey restart | Auth-builder template explicitly requires BOTH `EVALSHA` primary AND `EVAL` fallback. Review checklist item #2 verifies the fallback path is present |
| 3 | **Refresh storm under network flap in frontend** | Medium — mobile users on 4G in India (Tirupur seller audience) may experience intermittent connectivity | High — if 20 concurrent API calls all get 401 and all independently trigger `/auth/refresh`, the backend gets 20 refresh calls; the Lua script handles concurrency atomically (race loser gets `nil` → 401), but the frontend sees 20 failed retries | Frontend review checklist item #3 requires BehaviorSubject (or equivalent) refresh deduplication. Only ONE `/auth/refresh` call is in-flight at a time; other 401 callers wait on the same Observable |
| 4 | **Cookie domain mismatch in dev vs staging** | Medium — dev may use `localhost` or `dev.mesell.xyz`; `Domain=.mesell.xyz` cookie will NOT be sent from a `localhost`-loaded page to `localhost`-served API | High — local dev with `docker-compose.dev.yml` won't work with the `Domain=.mesell.xyz` cookie setting | Two mitigations: (1) dev K8s namespace uses `dev.mesell.xyz` subdomain (not localhost) per infra playbook; (2) local `docker-compose.dev.yml` dev should set `REFRESH_COOKIE_DOMAIN=localhost` with no `Domain` attribute. Auth-builder template notes this in hard constraints (cookie Domain is env-driven) |
| 5 | **REFRESH_TOKEN_PEPPER rotation breaks all live sessions** | Low in V1 (no prod traffic yet) | High in V1.5+ — rotating the pepper invalidates ALL existing HMAC keys in the Valkey allowlist simultaneously, forcing every active user to re-login | The `auth-secret-rotation.md` runbook documents the versioned rotation path (old pepper version accepted for a grace period = REFRESH_TOKEN_TTL_SECONDS). Auth-builder implements version-tag in the `cache:refresh:` key prefix to support dual-pepper reads during rotation window. Runbook is a gate item — plan not complete without it |

---

## Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-06-10 | mesell-auth-otp-planning-session-1 | Initial FEATURE_PLAN.md authored. Decisions D1/D2/D3 recorded. All 7 specialist dispatch templates drafted. |
| 0.2 | 2026-06-10 | mesell-auth-otp-planning-session-1 | D4 recorded (agent lineup confirmed by founder). meesell-angular-ui-styler added — Phase E, 3 SCSS surfaces, Template H, 4 frontend review checks. |
| 0.3 | 2026-06-10 | mesell-auth-otp-planning-session-1 | Branch setup section added — 4 coding branches documented, creation commands, PR flow, PR templates. |
| 0.4 | 2026-06-10 | mesell-auth-otp-planning-session-1 | Memory management section added — protocol, per-agent spec table, memory file template. Memory update line added to all 8 dispatch template report formats. Lead agent memories pre-seeded (backend-coordinator, frontend-coordinator, infra-builder). |
| 0.5 | 2026-06-10 | mesell-auth-otp-planning-session-1 | Sprint plan added — 3-sprint execution roadmap (Sprint 0 unlock + Sprint 1 backend/infra + Sprint 2 frontend HTTP wiring + Sprint 3 integration). Current state audit table included (backend ~95%, frontend ~30%). |
