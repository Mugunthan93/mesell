# STATUS — FEATURE CROSS-CUTTING (PLATFORM SESSION)

**Owner:** Cross-Cutting Sub-Session (session-as-role)
**Master:** `meesell-frontend-coordinator` session
**Bootstrap prompt:** `docs/SESSION_PROMPTS_FEATURE_CROSS_CUTTING.md` (paired with `docs/SESSION_PROMPTS_FEATURE_BASE.md`)
**Code root:** `frontend/src/app/core/` + `frontend/src/app/shared/` + cross-cutting wiring files (`app.config.ts`, `app.routes.ts`, `app.component.*`, `styles.scss`, `tailwind.config.js`, `ngsw-config.json`, `environments/`)
**Routes owned:** NONE directly — owns the cross-cutting layer every route consumes
**MF-remote target (Phase 2):** This is the **MF SHELL HOST** in Phase 2 — the host that exposes core/ + shared/ to all feature remotes. Not a remote itself.
**Special discipline rule (founder ruling 2026-06-06):** Any change to core/ or shared/ requires verification against ALL routes. Every feature sub-session consumes from here; breaking changes cascade to all 11 feature folders simultaneously.
**Created:** 2026-06-06 by frontend coordinator per FE-D12 amended grouping
**Last update:** 2026-06-06 (initial skeleton — cross-cutting sub-session not yet bootstrapped)

**Status:** Session not yet started — initialize via BASE + CROSS_CUTTING prompts.

## Current Phase

_pending — MAINTENANCE-mode session (most of core/ + shared/ already implemented by service-builder dispatch 2026-06-05)_

## Done

_(via service-builder 2026-06-05 — NOT this sub-session, but the work landed in this session's scope; you maintain + extend from here)_
- AuthService implementation (in-memory accessToken signal, bootstrap, setAccess, scheduleRefresh, logout, clear, computed userId/plan/isAuthenticated)
- 4 interceptors (Jwt → Locale → Refresh → Error) in canonical order
- ApiClient with retryOn503 opt-in
- ApiError with traceId support
- AuthGuard + PlanGuard (PlanGuard wired-but-inert for V1)
- ErrorService + NetworkService
- 9 cross-feature models in core/models/
- InjectionTokens (API_BASE_URL, ENV_CONFIG, ACCESS_TOKEN_SIGNAL)
- All shared pipes (inrCurrency, localeLabel, relativeTime)
- All shared directives ([meeAutosave], [meeClickOutside])
- All shared enums
- 6 shared component stubs (mee-empty-state, mee-status-badge, mee-loading-spinner, mee-confirm-dialog, mee-offline-banner, mee-navbar) — bodies pending; cross-cutting session implements them
- app.config.ts wired (interceptors + router + transloco + service worker + InjectionTokens)
- app.routes.ts with all 12 routes lazy
- ngsw-config.json + tsconfig path aliases + tailwind.config.js + Dockerfile + nginx.conf
- 77 tests passing
- Initial bundle: 111.76 KB gzip (vs §19 budget 180 KB; 37% headroom)

## In Progress

_(none yet — bootstrap pending)_

## Blockers

- Cross-cutting sub-session not yet bootstrapped (founder action)
- ComplianceStepComponent landing in shared/components/compliance-step/ (coordinate with onboarding session — likely implement-then-relocate pattern)
- Tailwind config + styles.scss wiring to design system tokens (blocks on design system completion)
- §22A risk 11 REFRESH_TOKEN_PEPPER pre-deploy gate (infra-builder action; cross-cutting session monitors)

## Next

1. Founder bootstrap
2. Sub-session implements the 6 shared component BODIES (currently stubs from service-builder)
3. Coordinate ComplianceStepComponent landing with onboarding session
4. When design system completes: wire tailwind.config.js + styles.scss to design tokens
5. Maintain core/ + shared/ across feature sub-session requests (with special discipline check on every change)

## Hand-offs

_(none yet)_

## Updates Log

=== UPDATE: 2026-06-06 SKELETON ===
STATUS file created per FE-D12 amended grouping. Cross-cutting
sub-session awaits founder bootstrap. Note: this is MAINTENANCE mode
— service-builder dispatch 2026-06-05 already produced ~90% of
core/ + shared/. Sub-session's job is to implement remaining shared
component bodies + maintain platform layer + enforce special
discipline rule across consumer sessions.

Per FE-D13, this is the MF SHELL HOST in Phase 2.
=========

## Questions for master

_Sub-session appends here; master answers inline below the question._

**Q1 [2026-06-06, open]** ComplianceStepComponent pattern: (a) onboarding
implements inline then hands off to me for relocation to shared/, or (b)
onboarding writes spec + I implement directly in shared/ from the start?
**Recommendation: (a)** — faster, onboarding gets a working component first.

**Q2 [2026-06-06, open]** Shared component bodies (6 stubs): dispatch
component-builder NOW (pre-emptive) or wait for first sibling consumer to
bootstrap and request? **Recommendation: WAIT** — consumer-driven keeps
contracts honest and avoids premature lock-in on template details.

**Q3 [2026-06-06, open]** §22A risk 11 (REFRESH_TOKEN_PEPPER) tracking:
STATUS hand-off only, or escalate to infra-builder formally as a blocker
entry in STATUS_INFRA.md? **Recommendation: STATUS hand-off only** — it's
a pre-deploy gate, not blocking frontend dev work.

**Q4 [2026-06-06, open]** Two minor §4 amendments surfaced by disk audit:
(a) §4.H: ACCESS_TOKEN_SIGNAL InjectionToken added by service-builder but
not in §4.H enumeration — it lives in auth/auth-tokens.ts (not tokens/).
(b) §4.I: service-builder added a 10th model `catalog.model.ts` (mirrors
catalogs table per DATABASE_ARCH; cross-feature — dashboard + catalog
sessions both consume it) but §4.I says "9 cross-feature models". Count is
off by 1. Recommend: formal AMENDMENT blocks for both §4.H + §4.I — keeps
the locked doc authoritative. Alternatively defer to coordinator cleanup
pass before component-builder dispatches (component-builder needs accurate
§4.I to type feature API responses).

## Questions for sibling sessions

_Sub-session appends here. Master may relay if sibling hasn't bootstrapped._

**→ onboarding [2026-06-06, open]** When you bootstrap, please confirm
pattern (a) or (b) for ComplianceStepComponent landing in shared/. Until
you decide, I hold the slot open at shared/components/compliance-step/.

**→ dashboard [2026-06-06, open]** When designing SideMenuComponent, list
the @shared/* imports you expect (route labels, mee-status-badge, etc.) so
I can verify they're in scope and no consumer collision exists.

**→ catalog [2026-06-06, open]** Your 11 form primitives live inside
catalog-form/primitives/ NOT shared/. If a primitive is needed cross-feature
during implementation, surface to me + request promotion per §3.G rule of 2+.
Do NOT import directly across feature folders.

**→ auth [2026-06-06, open]** mee-navbar consumes AuthService.isAuthenticated
computed signal for the sign-out button. If you rename that computed during
LoginComponent implementation, flag me BEFORE merging — it cascades to all
route shells via the app.component (special discipline matrix).

=== UPDATE: 2026-06-06 CROSS-CUTTING SUB-SESSION BOOTSTRAPPED ===
Cross-cutting (platform) sub-session opened by founder per FE-D12 +
FE-D13 + SESSION_PROMPTS_FEATURE_BASE.md +
SESSION_PROMPTS_FEATURE_CROSS_CUTTING.md.

Identity: I am the cross-cutting sub-session — the future MF SHELL HOST
per FE-D13. I own core/ + shared/ + the cross-cutting wiring files
(app.config.ts, app.routes.ts, app.component.*, styles.scss,
tailwind.config.js, ngsw-config.json, environments/).

SPECIAL DISCIPLINE RULE acknowledged (founder ruling 2026-06-06): any
change I propose to core/ or shared/ requires verification against ALL
routes because every feature sub-session consumes from here. Breaking
changes cascade to all 11 feature folders. Before any AuthService API
signature change, ApiClient method change, ApiError shape change, enum
value change, InjectionToken change, or shared component add/remove,
I verify against all 5 sibling STATUS files + grep features/ for usage,
then surface in my Q&A section with a proposed deprecation path.

Mandatory reads complete (9+ files):
  1. docs/status/STATUS_FEATURE_CROSS_CUTTING.md (this file — prior skeleton)
  2. docs/SESSION_PROMPTS_FEATURE_BASE.md (universal protocol)
  3. docs/FRONTEND_ARCHITECTURE.md §0 (premises + FE-D1–FE-D13)
       §1 (topology + interceptor chain + FE-D5/D6)
       §2.B (which features consume which core/shared)
       §3.C–F (canonical tree + path aliases I own)
       §4 (core/ — my binding contract; LOCKED)
       §5 (shared/ inventory — my scope; LOCKED)
       §5A (design system framework LOCKED; values PARTIAL pending FE-D9 designer)
       §16 (cross-cutting walkthroughs)
       §17 (service-component comm rules I ENFORCE)
       §19 (test strategy + perf budget I track)
       §22A risk 11 (REFRESH_TOKEN_PEPPER pre-deploy gate I monitor)
       §23 (route inventory cross-reference)
  4. docs/MVP_ARCHITECTURE.md §6 (HTTP caching / ngsw-config match)
       + §10 (audit log / error interceptor posture)
  5. docs/BACKEND_ARCHITECTURE.md §0 + §4 + §7 (auth contract reciprocity;
       FE-D5 + Lua EVAL + HMAC-pepper + cookie Path=/api/v1/auth)
  6. docs/CORE_PHILOSOPHY.md ALL (M1/M3/M7/M9 + F1/F5 — my enforcement pts)
  7. docs/status/STATUS_FRONTEND.md (master state through service-builder
       2026-06-05 + sub-session split 2026-06-06; FE-D9 visual identity gap)
  8. docs/status/STATUS_DESIGN_SYSTEM.md (Phase 1 Round 1 curated; founder
       picking Phase 1 refs 2026-06-06)
  9. All 5 sibling STATUS files:
       - STATUS_FEATURE_AUTH.md      (skeleton; not bootstrapped)
       - STATUS_FEATURE_ONBOARDING.md (skeleton; not bootstrapped — will need ComplianceStepComponent)
       - STATUS_FEATURE_PROFILE.md   (skeleton; blocker: ComplianceStepComponent landing)
       - STATUS_FEATURE_DASHBOARD.md (skeleton; owns SideMenuComponent left-nav)
       - STATUS_FEATURE_CATALOG.md   (skeleton; MEGA-SESSION, 6 folders, 11 primitives)

STATE OF MY SCOPE (as-of service-builder dispatch 2026-06-05):

  core/ — FULLY IMPLEMENTED per §4 + FE-D5 + FE-D6:
    auth/: auth.service.ts (in-memory accessToken signal; no localStorage;
           bootstrap, setAccess, scheduleRefresh, logout, clear,
           computed userId/plan/isAuthenticated)
           auth.guard.ts (active) + plan.guard.ts (wired-but-inert V1)
           jwt-payload.model.ts + auth-tokens.ts
    interceptors/ (ORDER LOAD-BEARING: Jwt → Locale → Refresh → Error):
           jwt.interceptor.ts, locale.interceptor.ts,
           refresh.interceptor.ts, error.interceptor.ts
    api/:   api-client.service.ts (typed wrapper + retryOn503 opt-in
            3-try exp-backoff 1s/2s/4s; default false)
            api-error.ts (with traceId)
    models/ (9 typed contracts): locale-map, paginated-response,
           ai-suggestion, field-schema, product, category,
           pricing-calc, export-record, seller-profile
    services/: error.service.ts (4 surface methods), network.service.ts
           (navigator.onLine signal), telemetry.service.ts (V1.5 stub)
    tokens/: api-base-url.token.ts, env-config.token.ts,
           env-config.model.ts, auth-tokens.ts (ACCESS_TOKEN_SIGNAL —
           added by service-builder; not yet in §4.H enumeration —
           see PENDING AMENDMENT below)

  shared/ pipes + directives + enums — FULLY IMPLEMENTED:
    pipes:      inr-currency.pipe (₹ Indian format), locale-label.pipe,
                relative-time.pipe
    directives: [meeAutosave] (300ms debounce → PATCH), [meeClickOutside]
    enums:      product-status, plan-tier, image-precheck-result,
                primitive-kind (11 types), step-id (13 IDs + STEP_ORDER)

  shared/ component BODIES — PENDING (6 stubs from service-builder):
    mee-empty-state, mee-status-badge, mee-loading-spinner,
    mee-confirm-dialog, mee-offline-banner, mee-navbar

  WIRING FILES — IN PLACE:
    app.config.ts (interceptors in §4.B order + router + transloco +
                   service worker + InjectionTokens)
    app.routes.ts (12 routes lazy via loadComponent/loadChildren per §23)
    app.component.* (root + navbar + router-outlet + offline banner)
    styles.scss (design-system imports + Tailwind directives +
                 snackbar panel classes)
    tailwind.config.js (CSS custom property refs → design-system tokens;
                        values land from design-system sub-session)
    ngsw-config.json (assetGroups prefetch/lazy + 4 dataGroups per §16)
    tsconfig.json path aliases (@core, @shared, @features,
                                @design-system, @env)
    environment.ts + environment.prod.ts
    Dockerfile (Node 20 → nginx:1.27-alpine per §20.C;
                dist path = dist/frontend/browser — amended from §20.C
                original which said `dist`)
    nginx.conf (SPA fallback + immutable cache + gzip per §20.D)

  TEST / BUNDLE STATE:
    77/77 vitest tests passing
    Initial bundle: 111.76 KB gzip vs §19 budget 180 KB (37% headroom)
    FE-D5 verified: 2 tests assert no localStorage.setItem() in auth flows
    Note: app.component.spec.ts excluded (styleUrl requires
          @analogjs/vite-plugin-angular — deferred to component-builder)

OUTSTANDING MAINTENANCE QUEUE:

  1. SHARED COMPONENT BODIES (6 stubs → implementation)
     Priority: LOW-MEDIUM. Deferred until first feature consumer
     bootstraps — consumer-driven keeps contracts honest.
     Dispatch plan: meesell-angular-component-builder scoped to
       shared/components/<name>/ ONLY — NOT feature folders.
     Pre-condition: @analogjs/vite-plugin-angular must be installed
       before component spec tests can resolve styleUrl.
     Note: mee-navbar consumes AuthService (isAuthenticated signal)
       + RouterLink. Touch only via approved PR through me.

  2. ComplianceStepComponent → shared/components/compliance-step/
     Coordinate with onboarding sub-session when it bootstraps.
     Both onboarding + profile consume it (rule of §3.G ≥2 features → shared).
     Preferred pattern: (a) onboarding implements inline, then hands
       off to me for file relocation + minor refactor → FASTER.
     Fallback pattern: (b) onboarding writes spec; I implement
       directly in shared/ → more coordination overhead.
     Status: PENDING onboarding sub-session bootstrap decision.
     See "Questions for sibling sessions" → onboarding below.

  3. tailwind.config.js + styles.scss wiring to design system tokens
     BLOCKED on design system sub-session Phase 1–4 completion.
     Current state: CSS custom property references in place; values
       land when design-system sub-session composes final 13 files.
     Design system status: Phase 1 Round 1 curated; founder picking
       2026-06-06. Phase 4 compose output gates this item.
     On unblock: targeted dispatch to integrate _tokens.scss +
       _theme.scss compose output; verify tailwind.config.js extends
       correctly; check bundle delta before reporting.

  4. §22A risk 11 — REFRESH_TOKEN_PEPPER pre-deploy gate
     Owner: infra-builder (Secret Manager population in K3s).
     Frontend impact: zero code; integration test only.
     Gate condition: AuthService refresh integration test MUST pass
       against backend (with pepper in place) before staging ships.
     Tracking: STATUS hand-off entry below. Escalate to master
       if infra-builder doesn't confirm within 2 sprint cycles.

  5. Pending documentation amendments (minor; surface to master):
     - §4.H: ACCESS_TOKEN_SIGNAL InjectionToken not enumerated
       (auth-tokens.ts added by service-builder; minor omission only)
     - §20.C: dist path correction → dist/frontend/browser (already
       in Dockerfile; doc-level fix only)
     - §19 / vitest setup: zoneless Angular + JIT + @analogjs pattern
       documented in STATUS_FRONTEND.md; not yet in FRONTEND_ARCH §19

  6. Special discipline matrix — ACTIVE for every change:

     CONTRACT               AFFECTED SUB-SESSIONS (all 5)
     ────────────────────── ─────────────────────────────────────────
     AuthService API        auth, onboarding, profile, dashboard
                              (logout), catalog (guard) = ALL 5
     ApiClient methods      ALL 5 (every *-api.service.ts injects it)
     ApiError shape         ALL 5 (every error-handling path)
     mee-navbar             auth (shell), dashboard, onboarding entry
     mee-offline-banner     ALL (rendered in app.component.html)
     mee-loading-spinner    ALL (used as interim loading state)
     mee-confirm-dialog     dashboard, catalog (destructive confirms)
     mee-status-badge       dashboard, catalog
     mee-empty-state        dashboard, catalog
     Enum values (per enum) grep features/ to determine consumers
     InjectionTokens        ACCESS_TOKEN_SIGNAL → auth.guard +
                              interceptors + AuthService (internal only;
                              no feature direct consumer expected)
     ────────────────────── ─────────────────────────────────────────

     Verification protocol for any breaking change:
     (a) check all 5 sibling STATUS files for in-progress usage
     (b) grep frontend/src/app/features/ for the symbol
     (c) surface in my "Questions for master" + Q&A + propose
         deprecation path (add new → mark old @deprecated → schedule
         removal once consumers migrate)
     (d) if all sibling sessions are still skeleton/not-bootstrapped:
         safe to proceed + leave "consumed by" comment in file

INITIAL DISPATCH POSTURE: NONE immediately.
  This is a MAINTENANCE-mode session. Service-builder produced ~90%
  of my scope. I act on:
  - Sibling sub-session requests for new shared components/pipes/directives
  - Design system Phase 4 completion → token wire-in
  - Backend contract refinements (§4 / §5 impacts)
  - Special discipline checks per the matrix above

QUESTIONS FOR MASTER:
  1. Pattern preference for ComplianceStepComponent: (a) onboarding
     implements inline then hands off to me, or (b) onboarding writes
     spec, I implement directly in shared/? I recommend (a).
  2. Shared component bodies (6 stubs): dispatch component-builder NOW
     (pre-emptive) or wait for first sibling consumer to bootstrap
     and request? I recommend WAIT — consumer-driven keeps contracts
     honest and avoids premature lock-in.
  3. §22A risk 11 tracking posture: STATUS hand-off only, or escalate
     to infra-builder formally via a blocker entry in STATUS_INFRA.md?
     Recommend STATUS hand-off only (it's pre-deploy, not blocking dev).
  4. Minor §4.H amendment for ACCESS_TOKEN_SIGNAL: surface as a
     coordinator AMENDMENT block in FRONTEND_ARCHITECTURE.md, or
     treat as chain-of-custody in STATUS_FRONTEND.md only?
     Recommend formal AMENDMENT block for completeness.

QUESTIONS FOR SIBLING SESSIONS:
  → onboarding: please confirm pattern (a) or (b) for
    ComplianceStepComponent landing in shared/ when you bootstrap.
    Until then I hold the slot open at shared/components/compliance-step/.
  → dashboard: when you design SideMenuComponent, list the @shared/*
    imports you expect (e.g., mee-status-badge, route labels) so
    I can pre-verify they're scoped correctly and not already
    promised to another consumer path.
  → catalog (mega-session): your 11 form primitives live inside
    catalog-form/primitives/ NOT shared/. If during implementation
    a primitive is needed cross-feature (e.g., images/ wants FilePicker),
    surface to me + request promotion to shared/ per §3.G rule of 2+.
    Do NOT import directly across feature folders.
  → auth: mee-navbar consumes AuthService.isAuthenticated signal for
    the sign-out button. If you change the computed property name
    during LoginComponent implementation, flag me BEFORE merging
    (special discipline matrix — navbar cascades to all route shells).

HAND-OFFS:
  → To master: bootstrap complete + maintenance queue established.
    No immediate master action required.
  → To onboarding (deferred until onboarding bootstraps):
    ComplianceStepComponent landing pattern decision.
  → To infra-builder (tracked via STATUS): REFRESH_TOKEN_PEPPER must
    land in dev + staging + prod Secret Manager namespaces before
    staging deploy (§22A risk 11 pre-deploy gate).

Done: cross-cutting sub-session bootstrapped; mandatory reads
  complete; current state of core/ + shared/ catalogued;
  outstanding maintenance queue established; special discipline
  matrix locked; consumer impact table populated; sibling STATUS
  files surveyed (all 5 skeleton / not bootstrapped as of 2026-06-06).

In Progress: monitoring sibling STATUS files for first bootstrap that
  triggers a maintenance action.

Blockers (carried forward):
  - 6 shared component bodies (stubs; LOW urgency; consumer-driven)
  - ComplianceStepComponent landing (coordinated with onboarding)
  - tailwind.config.js + styles.scss wiring (BLOCKED on design system
    Phase 1–4 completion)
  - §22A risk 11 REFRESH_TOKEN_PEPPER (infra-builder deliverable; tracked)
=========
