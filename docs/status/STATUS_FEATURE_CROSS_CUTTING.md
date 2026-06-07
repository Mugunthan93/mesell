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

_(via service-builder 2026-06-05)_
- AuthService, 4 interceptors (Jwt→Locale→Refresh→Error), ApiClient, ApiError
- AuthGuard + PlanGuard, ErrorService, NetworkService
- 10 cross-feature models in core/models/ (incl. catalog.model.ts + seller-profile.model.ts fixed 2026-06-07)
- InjectionTokens (API_BASE_URL, ENV_CONFIG, ACCESS_TOKEN_SIGNAL)
- All shared pipes, directives, enums
- app.config.ts, app.routes.ts (12 lazy routes), ngsw-config.json, tsconfig aliases, tailwind.config.js, Dockerfile, nginx.conf
- 77 tests passing | 111.76 KB gzip initial bundle (37% under §19 budget)

_(via this session 2026-06-06–07)_
- Design system integration verified — tailwind.config.js + styles.scss §5A compliant ✓
- §5A sweep COMPLETE — all 10 shared components hex-clean:
  - mee-offline-banner ✓ (complete-as-is)
  - mee-confirm-dialog ✓ (complete-as-is)
  - mee-loading-spinner ✓ Batch 1
  - mee-status-badge ✓ Batch 1
  - mee-empty-state ✓ Batch 1 (@Output → output<void>())
  - mee-stat-card ✓ Batch 2
  - mee-loading-skeleton ✓ Batch 2
  - mee-page-header ✓ Batch 2 (@Output → output<void>())
  - mee-form-field ✓ Batch 2
  - mee-navbar ⏸ (held — app.routes.ts lockstep first)
- Q-CC-001: core/models/seller-profile.model.ts rewritten (snake_case, 15 fields, §8.E compliant)
- profile-api.service.ts: SellerProfileCorrect alias wired; 5 consumers build clean

## In Progress

- app.routes.ts update — queued, waiting on auth session folder rename signal (lockstep)

## Blockers

- mee-navbar: Q-AUTH-001 ruling received ✓; unblocked — executing lockstep with auth session
- ComplianceStepComponent: waiting on onboarding sub-session bootstrap
- §22A risk 11 REFRESH_TOKEN_PEPPER: infra-builder pre-deploy gate (unchanged)
- ~~Tailwind config + styles.scss wiring~~ CLEARED 2026-06-06
- ~~seller-profile.model.ts drift~~ CLEARED 2026-06-07 (Q-CC-001 ✓)

## Next

1. app.routes.ts — execute IN LOCKSTEP the moment auth session signals folder rename ready
2. mee-navbar — dispatch immediately after app.routes.ts rename + build green
3. ComplianceStepComponent — coordinate with onboarding bootstrap
4. Profile session cleanup — SellerProfileCorrect alias removal + PUT→PATCH fix in account-api.service.ts

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

**Q-CC-002 [2026-06-06, open]** §5A.C body text reads "Inter" but the
landed implementation uses Plus Jakarta Sans throughout (_typography.scss,
tailwind.config.js fontFamily, styles.scss snackbar rule). Minor §5A.C
AMENDMENT needed — update body font name only. No code impact; doc-level fix.
**Recommendation:** Master issues a minor §5A.C AMENDMENT in
FRONTEND_ARCHITECTURE.md replacing "Inter" → "Plus Jakarta Sans".

**Q-CC-003 [2026-06-07, open]** §5A hex grep on shared/components/ found 4
additional stubs with violations not in the original 6-stub inventory:
stat-card (COLOR_MAP + TREND_COLOR hex + card wrapper hex), loading-skeleton
(shimmer gradient hex in styles array), page-header (title/subtitle hex +
raw CTA button #F26B23 + @Output EventEmitter), form-field (label/hint/error
hex). These were created by service-builder but not enumerated in the session
bootstrap. Dispatching Batch 2 immediately per §5A LOCK mandate.
**FYI only — no master action needed.** Session scope update: shared component
total = 10 stubs (6 original + 4 discovered); 7 refactored, 2 complete-as-is,
1 held.

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

=== UPDATE: 2026-06-06 DESIGN SYSTEM INTEGRATION ACKNOWLEDGED (§5A AMENDMENT 2026-06-06B) ===
Master relayed: §5A FULL LOCK via AMENDMENT 2026-06-06B. All design-
system values are now live as CSS custom properties. Platform session
acknowledges and audits impact.

§5A AMENDMENT 2026-06-06B READ: ✓
  CSS custom properties live in :root via _tokens.scss.
  Primary: #F26B23 | Secondary: #1E40AF | Background: #f0f5f9.
  Font: Plus Jakarta Sans (see Q-CC-002 — §5A.C body text still says
    "Inter"; actual landed font is Plus Jakarta Sans; doc-level fix only).
  Tailwind: CSS var() references — no hardcoded hex except spike-bg
    (#f0f5f9, intentional static hex for Tailwind JIT purge edge case). ✓
  styles.scss: import order confirmed correct per §5A.H. ✓

DESIGN-SYSTEM FILES VERIFIED (all non-stub, fully implemented):
  _tokens.scss           ✓ CSS vars in :root; spacing + elevation +
                           motion + color + typography + radius tokens
  _theme.scss            ✓ M3 + Spike CSS var overrides; surface tint
                           override to var(--mee-color-surface)
  _typography.scss       ✓ Plus Jakarta Sans weights 300–800; text
                           scale xs→4xl via CSS custom properties
  _elevation.scss        ✓ 4 levels (0–3) as box-shadow CSS vars
  _motion.scss           ✓ 3 tiers (micro/standard/large) + reduced-
                           motion media query (all durations → 0ms)
  _tailwind-bridge.scss  ✓ Reference doc; CSS vars published via
                           _tokens.scss; no parallel declarations
  breakpoints.ts         ✓ TS mirror of breakpoint values
  tokens.ts              ✓ TS mirror: MOTION, COLORS, COLORS_RESOLVED
  _component-overrides.scss ✓ (bonus) 20 KB; 15 Material component
                           overrides ported from Spike Angular light-theme;
                           Spike dialog/chip/button/field overrides apply
                           automatically to mee-confirm-dialog etc.
  tailwind.config.js     ✓ (my wiring file) Fully wired to CSS vars;
                           spike-bg static hex intentional exception
  styles.scss            ✓ (my wiring file) Import order per §5A.H;
                           snackbar + offline-banner classes use CSS vars

BLOCKER CLEARED: tailwind.config.js + styles.scss wiring to design system
  tokens is UNBLOCKED. Both files verified correct per §5A.H. The blocker
  carried forward from bootstrap ("BLOCKED on design system Phase 1–4
  completion") is now resolved.

6 SHARED COMPONENT STUB AUDIT (design-system compliance check):

  mee-offline-banner  ✓ COMPLETE — uses .mee-offline-banner CSS class
                        from styles.scss; class resolves to CSS vars
                        (var(--mee-color-warning) / var(--mee-color-on-
                        warning)). No refactor needed.

  mee-confirm-dialog  ✓ COMPLETE — Material dialog structure; Spike
                        dialog overrides from _component-overrides.scss
                        apply automatically. No refactor needed.

  mee-loading-spinner ⚠ MINOR REFACTOR — wrapper div uses inline
                        style="display:flex; justify-content:center; ..."
                        and caption <p> is unstyled.
                        Fix: inline style → Tailwind flex/justify-center/
                        items-center classes; caption → text-mee-sm
                        text-on-surface-variant mt-2 text-center.
                        → Dispatching in Batch 1.

  mee-status-badge    ⚠ REFACTOR — STATUS_STYLES record has 15 hardcoded
                        hex values (#DCFCE7, #15803D, etc.), violating
                        §5A LOCK "no hardcoded hex in component files".
                        DECISION: replace with Tailwind palette classes
                        (NOT design system CSS vars). Rationale: design
                        tokens are semantic (#F26B23 primary, #1E40AF
                        secondary); they don't define light badge-state
                        tints. Adding semantic tokens for badge tints has
                        no design-language meaning — Tailwind palette is
                        the correct tool here. Mapping:
                          ready     → bg-green-100 text-green-700 border-green-200
                          exported/live → bg-blue-100 text-blue-700 border-blue-200
                          processing/pending → bg-amber-100 text-amber-600 border-amber-200
                          failed/deleted → bg-red-100 text-red-600 border-red-200
                          draft     → bg-gray-100 text-gray-500 border-gray-200
                        Fix: remove STATUS_STYLES inline-style record +
                        BASE_STYLE string join; render via [class]= binding
                        with a statusClass() computed() signal.
                        → Dispatching in Batch 1.

  mee-empty-state     ⚠ SIGNIFICANT REFACTOR — three violations:
                        (a) hardcoded #F26B23 on raw <button> element
                            → replace with mat-flat-button color="primary"
                              (CSS var resolves automatically)
                        (b) inline style attributes → Tailwind classes
                        (c) @Output() EventEmitter decorator → output()
                            signal (Angular 18 idiomatic; service-builder
                            produced old decorator pattern)
                        → Dispatching in Batch 1.

  mee-navbar          ⏸ ON HOLD — pending Q-AUTH-001 ruling on account/
                        vs auth/ folder structure from master/founder.
                        Nav links + router paths depend on this ruling.
                        Will implement immediately upon ruling.

DISPATCH — BATCH 1 (initiated this turn):
  Agent: meesell-angular-component-builder (sonnet)
  Scope: 3 shared component refactors (loading-spinner, status-badge,
         empty-state). Each scoped to its own shared/components/<name>/
         directory — no feature folder access.
  Hard constraint on all 3: NO hardcoded hex values in output.
    CSS vars (var(--mee-color-*)) for semantic colors.
    Tailwind palette classes for status-state tints.
    mat-flat-button / mat-icon-button for interactive elements.
  Note re: spec tests: @analogjs/vite-plugin-angular not yet installed;
    component-builder instructed to write logic/signal tests only (no
    styleUrl resolution required). Component test files will be updated
    when @analogjs is added in a later infra pass.
  Bundle delta estimate: ≤1 KB gzip (class-string replacements only;
    no new dependencies introduced).

In Progress: Batch 1 dispatch initiated (loading-spinner, status-badge,
  empty-state). mee-navbar held for Q-AUTH-001.

Blockers update:
  - Design system wiring CLEARED (both my wiring files verified correct)
  - 3 component bodies dispatched (Batch 1)
  - 1 component body held (mee-navbar, Q-AUTH-001)
  - ComplianceStepComponent: still pending onboarding bootstrap decision
  - REFRESH_TOKEN_PEPPER: infra-builder pre-deploy gate, unchanged
=========

=== UPDATE: 2026-06-07 BATCH 2 COMPLETE — §5A SWEEP DONE (ALL SHARED COMPONENTS) ===

Batch 2 verified by disk read + hex grep:

  mee-stat-card ✓
    ColorTokens/COLOR_MAP/TREND_COLOR removed (had 8 hardcoded hex).
    CIRCLE_CLASSES: Tailwind bg palette (bg-orange-50/bg-blue-50/bg-green-50/bg-violet-50).
    ICON_CLASSES: semantic + Tailwind (text-primary/text-secondary/text-success/text-violet-700).
    TREND_CLASSES: text-success/text-error/text-gray-400.
    Card → bg-bg-elevated rounded-mee-md py-5 px-6 shadow-mee-1.
    Value → text-on-surface. Label → text-on-surface-variant.
    Icon span: font-family inline (no design token for Material Icons font) — acceptable.
    Note: grep found hex in comments only (//= #F26B23 etc.) — not active values.

  mee-loading-skeleton ✓
    Shimmer gradient hex replaced with CSS vars:
    #f0f0f0 → var(--mee-color-surface-variant) | #e0e0e0 → var(--mee-color-outline).
    Template inline styles: layout-only (height/border-radius/width) — no color hex.

  mee-page-header ✓
    @Output EventEmitter → output<void>(). MatButtonModule added.
    h1 → text-2xl font-bold text-on-surface m-0 leading-snug.
    p → text-sm text-on-surface-variant mt-1 mb-0.
    CTA button → mat-flat-button color="primary" class="inline-flex items-center
      gap-1.5 whitespace-nowrap min-h-[44px] flex-shrink-0".
    mat-icon size inline style preserved (layout-only, no color hex).

  mee-form-field ✓
    label → text-[13px] font-medium text-on-surface block mb-1.5.
    required * → class="text-error ml-0.5" aria-hidden="true".
    hint → class="mee-form-field__hint text-xs text-on-surface-variant mt-1".
    error → class="mee-form-field__error text-xs text-error font-medium mt-1".
    role="alert" preserved on error div.

FINAL §5A AUDIT: shared/components/ — ALL CLEAN
  grep -rn '#[0-9A-Fa-f]{3,6}' shared/components/ --include="*.ts" | grep -v '//.*#'
  Result: 0 active violations. Comments may reference hex for documentation — acceptable.

SHARED COMPONENT SCOPE SUMMARY (final):
  Total stubs: 10 (6 original + 4 discovered by Batch 2 audit)
  §5A compliant (no action needed):  mee-offline-banner, mee-confirm-dialog — 2
  §5A refactored Batch 1:            mee-loading-spinner, mee-status-badge, mee-empty-state — 3
  §5A refactored Batch 2:            mee-stat-card, mee-loading-skeleton, mee-page-header, mee-form-field — 4
  On hold (pending Q-AUTH-001 lockstep): mee-navbar — 1
  Total compliant: 9/10 (mee-navbar excluded pending routing ruling)

NEXT ACTIONS (ordered):
  1. app.routes.ts — coordinate with auth session for lockstep folder rename
     (Q-AUTH-001 ruling received; execution blocked on auth session signaling ready)
  2. mee-navbar — dispatch after app.routes.ts rename lands + build green
  3. ComplianceStepComponent — await onboarding bootstrap
=========

=== UPDATE: 2026-06-06 MASTER RULINGS RECEIVED — Q-AUTH-001 + Q-CC-001 ===

Q-AUTH-001 ✅ RULED — ALLOW RENAME. Cross-cutting session actions:
  1. Update app.routes.ts — replace both ACCOUNT_ROUTES import references:
       Auth layout group (path ''): import from features/auth/auth.routes → AUTH_ROUTES
       Shell layout group (path 'profile'): import from features/profile/profile.routes → PROFILE_ROUTES
       Onboarding: import from features/onboarding/onboarding.routes → ONBOARDING_ROUTES
  2. Coordinate with auth sub-session — execute app.routes.ts update IN LOCKSTEP with
     auth session's folder move so there is no intermediate broken-build state.
  3. After rename lands + build passes → mee-navbar blocker CLEARED (can reference
     correct feature route paths for the sidebar nav items).

Q-CC-001 ✅ CONFIRMED — Fix core/models/seller-profile.model.ts immediately.
  Authoritative shape (from inline SellerProfileCorrect in profile-api.service.ts):
    manufacturer_name: string
    packer_name: string
    country_of_origin: string
    customer_care_contact: string
    registered_address: string
    gst_number?: string
    fssai_license?: string
    active_super_categories: string[]
    compliance_extensions: Record<string, Record<string, unknown>>
    profile_complete: boolean
  After fix:
    - profile-api.service.ts removes inline SellerProfileCorrect + imports SellerProfile from @core/models
    - AccountApiService.getProfile() return type uses fixed model
    - Onboarding-api.service.ts authoring unblocked

ACTIONS FOR CROSS-CUTTING SESSION:
  Priority 1 (immediate): Fix core/models/seller-profile.model.ts (Q-CC-001)
  Priority 2 (coordinate with auth): app.routes.ts update (Q-AUTH-001 lockstep)
  Priority 3 (after rename): mee-navbar dispatch (now unblocked)
=========

=== UPDATE: 2026-06-07 BATCH 1 COMPLETE + Q-CC-001 FIX + BATCH 2 INITIATED ===

MASTER RULINGS ACKNOWLEDGED (received overnight):
  Q-AUTH-001 ✅ Rename allowed. app.routes.ts update queued — executing IN
    LOCKSTEP with auth session folder move (not unilaterally before that).
    mee-navbar dispatch unblocked once rename lands.
  Q-CC-001 ✅ Fix seller-profile.model.ts immediately (authoritative shape
    confirmed from SellerProfileCorrect in profile-api.service.ts).

BATCH 1 COMPLETE — verified by disk read (all 3 files match spec):
  mee-loading-spinner ✓
    Outer wrapper: class="flex flex-col items-center justify-center gap-2"
    Inner wrapper: class="flex flex-col items-center gap-1"
    Caption: class="text-xs text-on-surface-variant text-center mt-1"
    Zero inline style= attributes remaining.
  mee-status-badge ✓
    BadgeStyle/STATUS_STYLES/DEFAULT_STYLE/BASE_STYLE removed.
    STATUS_CLASSES Record<string, string> — Tailwind palette classes.
    badgeClass() computed; [class]="badgeClass()" binding.
    Zero hardcoded hex values.
  mee-empty-state ✓
    @Output EventEmitter → output<void>(). MatButtonModule added.
    CTA → mat-flat-button color="primary" (CSS var auto-resolved).
    All inline style= → Tailwind classes + text-on-surface/text-on-surface-variant.
    mat-icon keeps size-only inline style (no color hex).

Q-CC-001 FIX APPLIED — core/models/seller-profile.model.ts:
  BEFORE: camelCase shape (legalName, gstNumber, businessAddress, superCategoryIds:
    UUID[]) — drift from BACKEND_ARCH §8.E. Fields: 13.
  AFTER: snake_case shape matching seller_profiles table exactly.
    Fields: user_id + 9 LM fields (name/address/pincode × 3) + country_of_origin
    + active_super_categories + compliance_extensions + profile_complete
    + created_at + updated_at. Total fields: 15. Readonly throughout.
  Import unchanged: `UUID` from '@core/auth/jwt-payload.model'.
  RequiredProfileFields interface preserved (account-api.service.ts imports it).

  profile-api.service.ts updated (backward-compat, build-safe):
    SellerProfileCorrect interface REMOVED.
    Added: import { SellerProfile } from '@core/models/seller-profile.model'
    Added: export type SellerProfileCorrect = SellerProfile  ← alias
    All 5 consumers (profile.component.ts + 2 spec files + account-api.service.ts
    + profile-api.service.ts itself) continue to compile without change.
    Profile sub-session to clean up alias when it bootstraps.

  account-api.service.ts (NOT modified — type-reference update falls to profile
    session): After core model fix, SellerProfile in account-api.service.ts now
    types correctly against snake_case shape. Existing PUT bug in updateProfile()
    is pre-existing; not introduced or fixed here — flagged for profile session.

§5A HEX GREP FINDING — 4 additional shared stubs discovered (not in original 6):
  stat-card, loading-skeleton, page-header, form-field (all in shared/components/)
  Total shared components: 10 (6 original + 4 discovered). Original "6-stub"
  count in session bootstrap was incomplete — service-builder created more.
  Updated scope: 10 stubs | 2 complete as-is | 5 dispatched | 1 held | 2 pending Batch 2.

BATCH 2 DISPATCHED — meesell-angular-component-builder (background):
  mee-stat-card:
    ColorTokens/COLOR_MAP/TREND_COLOR → Tailwind class maps
    CIRCLE_CLASSES: orange→bg-orange-50, blue→bg-blue-50, green→bg-green-50,
                    purple→bg-violet-50
    ICON_CLASSES: orange→text-primary, blue→text-secondary, green→text-success,
                  purple→text-violet-700
    TREND_CLASSES: up→text-success, down→text-error, neutral→text-gray-400
    Card container → bg-bg-elevated rounded-mee-md py-5 px-6 shadow-mee-1 flex flex-col
    computed style functions → computed class functions
  mee-loading-skeleton:
    styles array gradient hex → CSS vars (surface-variant + outline)
    Template inline styles: layout-only (no hex) — unchanged
  mee-page-header:
    @Output EventEmitter → output<void>(). MatButtonModule added.
    h1 → text-2xl font-bold text-on-surface. p → text-sm text-on-surface-variant.
    CTA → mat-flat-button color="primary" min-h-[44px]
  mee-form-field:
    label → text-[13px] font-medium text-on-surface block mb-1.5
    required * → class="text-error ml-0.5"
    hint → text-xs text-on-surface-variant mt-1
    error → text-xs text-error font-medium mt-1

CURRENT QUEUE (after Batch 2 lands):
  1. app.routes.ts — coordinate with auth session folder move (Q-AUTH-001 lockstep)
  2. mee-navbar — dispatch after rename + build green (now unblocked per Q-AUTH-001)
  3. ComplianceStepComponent — wait for onboarding bootstrap
  4. Profile sub-session: clean up SellerProfileCorrect alias + fix PUT→PATCH bug
     in account-api.service.ts when profile bootstraps

Blockers updated:
  - seller-profile.model.ts drift CLEARED (Q-CC-001 ✓)
  - mee-navbar UNBLOCKED (Q-AUTH-001 ✓) — waiting on lockstep with auth
  - REFRESH_TOKEN_PEPPER: still infra-builder pre-deploy gate (unchanged)
  - ComplianceStepComponent: still pending onboarding bootstrap
=========
