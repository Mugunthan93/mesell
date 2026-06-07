# STATUS — FEATURE AUTH

**Owner:** Auth Sub-Session (session-as-role)
**Master:** `meesell-frontend-coordinator` session
**Bootstrap prompt:** `docs/SESSION_PROMPTS_FEATURE_AUTH.md` (paired with `docs/SESSION_PROMPTS_FEATURE_BASE.md`)
**Code root:** `frontend/src/app/features/auth/` + `frontend/src/app/features/landing/`
**Routes owned:** `/`, `/signup`, `/login`
**MF-remote target (Phase 2):** auth-mfe per FE-D13
**Created:** 2026-06-06 by frontend coordinator per FE-D12 amended grouping
**Last update:** 2026-06-07 (Dispatch 3 complete — session V1-COMPLETE pending cross-cutting)

**Status:** V1-COMPLETE — all 3 component dispatches done. Awaiting cross-cutting app.routes.ts coordination.

## Current Phase

HANDOFF — All component dispatches complete. Cross-cutting session must update
app.routes.ts (replace ACCOUNT_ROUTES auth layout with AUTH_ROUTES from features/auth/auth.routes.ts).

## Done

- Bootstrap reads complete (2026-06-06)
- Design system integration acknowledged (§5A FULL LOCK 2026-06-06B)
- Q-AUTH-001/002/003 all RULED (2026-06-07 via master)
- **Dispatch 1: LandingComponent — COMPLETE** (2026-06-06)
    6/6 tests ✓ · 1.31 KB gzip · zero build errors
- **Dispatch 2: auth/ scaffold — COMPLETE** (2026-06-07)
    14/14 tests ✓ · SignupComponent + LoginComponent + PhoneInputComponent
    + auth-api.service.ts (corrected contracts) + auth.routes.ts
    · signup chunk 963 B gzip · login chunk 883 B gzip · zero build errors
- **Dispatch 3: OtpVerifyComponent body — COMPLETE** (2026-06-07)
    6/6 tests ✓ · 196-line component · 60s timer · 3-attempt guard
    · ng-otp-input (NgOtpInputModule v1.9.3) · Q-AUTH-003 redirect wired
    · zero build errors · 2 new en.json keys (auth.otp_invalid, auth.otp_attempts_exceeded)

## In Progress

_(none — all dispatches complete)_

## Blockers

- **CROSS-CUTTING REQUIRED**: app.routes.ts update — cross-cutting session must:
  - Replace the ACCOUNT_ROUTES lazy load (for the auth layout) with AUTH_ROUTES
    from `@features/auth/auth.routes`
  - Verify signup and login routes resolve to features/auth/ components
  - This is the final lockstep to make the auth feature navigable

## Next

_(none — session V1-complete; cross-cutting owns the remaining blocker)_

## Hand-offs

**TO CROSS-CUTTING SESSION** (2026-06-07):
  - features/auth/auth.routes.ts — routes for /signup + /login with lazy
    loadComponent + AuthApiService in providers[]
  - features/auth/components/otp-verify/otp-verify.component.ts — IMPLEMENTED
    (was stub when Dispatch 2 landed; now full body per Dispatch 3)
  - app.routes.ts currently loads: ACCOUNT_ROUTES for auth layout
  - app.routes.ts must load: AUTH_ROUTES from features/auth/auth.routes for
    the `/signup` + `/login` lazy routes
  - Verify: `ng build` exits 0 after app.routes.ts update

## Updates Log

=== UPDATE: 2026-06-06 AUTH SUB-SESSION BOOTSTRAP ===
Phase: Bootstrap — 8 mandatory reads complete; architectural state assessed.

BINDING CONTRACT: FRONTEND_ARCHITECTURE.md §7 (Feature: account, post-merger
2026-06-05B). §7 remains authoritative for this sub-session despite the
2026-06-06A un-merge doc amendment (§7 content: endpoint contracts, UX details,
deferred-to-core list, component inventory — all valid). Session scope is:
  - features/landing/ + features/auth/ (routes /, /signup, /login)
  - AuthApiService wrapping POST /api/v1/auth/otp/send + POST /api/v1/auth/otp/verify
  Per FE-D12 amended 2026-06-06A (§2.B + §3.C.4).

DESIGN SYSTEM STATE: PARTIAL LOCK
  STATUS_DESIGN_SYSTEM.md confirms Phase 1 Round 1 curation complete (38 refs
  across 5 categories). No picks ratified. §5A values are PLACEHOLDER.
  All components in this session use CSS custom property references only
  (var(--color-primary), var(--color-surface), etc.) — NO hardcoded hex values.
  FLAG: visual re-verification pass required after design system sub-session
  completes Phase 4 compose and master flips §5A → FULL LOCK.

SERVICE-BUILDER HAND-OFFS (from 2026-06-05 dispatch — confirmed COMPLETE):
  ✓ core/auth/auth.service.ts — FULLY IMPLEMENTED
      AuthService.setAccess({ access_token, expires_in }) → writes in-memory
      signal per FE-D5 (no localStorage). scheduleRefresh() auto-wired.
      OtpVerifyComponent consumes this after successful verify.
  ✓ features/account/account-api.service.ts — STUB (method signatures present;
      bodies stubbed; OTP send + verify are this session's implementation target)
  ✓ All 4 interceptors wired in app.config.ts — cross-cutting session NOT
      needed before auth component dispatch.

STRUCTURAL GAPS (action required — see Q-AUTH-001 to Q-AUTH-003):

  GAP 1 — Folder mismatch:
    Session prompt assumes features/auth/ (per 2026-06-06A doc amendment).
    Actual scaffold: features/account/ (service-builder created 2026-06-05
    under the pre-amendment 9-folder structure). No features/auth/ exists.
    LandingComponent in features/landing/ is UNAFFECTED (correct folder).
    Auth component dispatch blocked pending Q-AUTH-001 ruling.

  GAP 2 — AccountApiService contract mismatches vs backend §7.B (3 issues):
    (a) OtpVerifyRequest stub has { requestId, otp } — backend expects { phone, otp }
    (b) OtpVerifyResponse stub has profileComplete: boolean — NOT in backend spec
    (c) OtpSendResponse stub has 'message' field — NOT in backend spec
    These will be corrected when auth service file is implemented/renamed.

  GAP 3 — Resend timer ambiguity: §7 says 30s; session prompt says 60s.
    Awaiting Q-AUTH-002 ruling. Not blocking LandingComponent.

  GAP 4 — profileComplete post-verify redirect: backend verify response has no
    profile_complete. See Q-AUTH-003. Proceeding with GET /seller-profile call
    as default until master rules.

i18n POSTURE (M9 structural):
  ALL user-facing strings in templates use Transloco t() calls. Keys:
    landing.hero.title, landing.cta.signup, landing.cta.login
    auth.phone.label, auth.phone.placeholder, auth.otp.title
    auth.otp.resend, auth.otp.error.invalid, auth.otp.error.limit
  en.json will be populated by component-builder dispatch. ta.json + hi.json
  stubs remain empty for V1.5.

VALIDATION MESSAGE KEYS (M3 — plain language, never backend codes):
  validation.phone.invalid_format → "Please enter a valid 10-digit mobile number."
  auth.otp_invalid → "That code doesn't match. Try again."
  auth.otp_attempts_exceeded → "Too many attempts. Request a new code."
  plan.limit_exceeded (429) → "Too many requests. Try again in X minutes."
    (X extracted from response headers / Retry-After where available)

COMPONENT-BUILDER MEMORY: Empty baseline (no prior sessions). Dispatches
  will build up memory for future rounds.

FIRST DISPATCH: LandingComponent body — READY
  landing/ folder is correct. Stub at
  features/landing/landing/landing.component.ts exists. No folder-rename
  dependency. Will surface first dispatch spec to founder immediately
  after this bootstrap.

BACKEND DEPLOYED STATUS: Not yet verified (not blocking — component-builder
  dispatches scaffold against MSW mocks per §19; integration tested on deploy).

In progress: LandingComponent dispatch spec pending founder authorisation.
Blockers:
  - Q-AUTH-001 (folder rename decision) — BLOCKS auth component dispatches
  - Q-AUTH-002 (resend timer) — BLOCKS OtpVerifyComponent implementation
  - Q-AUTH-003 (profileComplete) — BLOCKS OtpVerifyComponent routing logic
  (None of the above block LandingComponent)
=========

=== UPDATE: 2026-06-06 DESIGN SYSTEM INTEGRATION ACKNOWLEDGED ===
Phase: §5A FULL LOCK confirmed; dispatching LandingComponent with real tokens.

CONFIRMED READS (per master notification 2026-06-06B):
  ✓ FRONTEND_ARCHITECTURE.md §5A AMENDMENT 2026-06-06B — FULL LOCK confirmed.
  ✓ design-system/_tokens.scss  — CSS custom props live; primary #F26B23 / secondary
                                   #1E40AF / bg #f0f5f9 / surface #ffffff / on-surface
                                   #2a3547; radius 7/16/18/full; motion 100/200/300ms.
  ✓ design-system/_theme.scss   — Material M3 + Spike light-theme overrides wired.
  ✓ design-system/_typography.scss — Plus Jakarta Sans (300–800) loaded globally.
  ✓ design-system/_elevation.scss / _motion.scss — 4 levels / 3 tiers.
  ✓ design-system/_component-overrides.scss — Spike 15-component visual language;
                                               Material components inherit automatically.
  ✓ design-system/breakpoints.ts / tokens.ts — TS mirrors confirmed.
  ✓ tailwind.config.js — bg-primary / text-on-primary / bg-bg / bg-surface /
                          text-on-surface / rounded-mee-* / shadow-mee-* / text-mee-*
                          / duration-standard wired to CSS custom properties.
  ✓ styles.scss — import order: tokens → theme → overrides → bridge → typography
                  → elevation → motion → Tailwind — correct.
  ✓ STATUS_FRONTEND.md — DESIGN SYSTEM INTEGRATION COMPLETE block read.

IMPACT:
  No in-flight dispatches to re-trigger (session was awaiting authorisation).
  LandingComponent dispatching NOW with real tokens — no re-work needed.
  Future auth component dispatches (signup, login, OTP) will use same token
  reference (blocked on Q-AUTH-001/002/003, not on design system).

TOKEN CHEATSHEET FOR THIS SESSION'S DISPATCHES:
  Colors (Tailwind): bg-primary, text-on-primary, bg-bg, bg-surface,
    text-on-surface, text-on-surface-variant, bg-surface-variant, text-primary,
    text-secondary, text-error, text-success, text-warning
  Border radius:     rounded-mee-sm, rounded-mee-md, rounded-mee-lg, rounded-mee-full
  Shadows:           shadow-mee-1, shadow-mee-2, shadow-mee-3
  Type scale:        text-mee-xs/sm/base/lg/xl/2xl/3xl/4xl
  Motion:            transition duration-standard duration-micro ease-mee
  Material CTAs:     color="primary" → orange; color="accent" → blue
  Icons:             Material Symbols Outlined (interim) — mat-icon or
                     <span class="material-symbols-outlined">
  Font:              Plus Jakarta Sans loaded globally; no component-level config.
  CSS vars directly: var(--mee-color-primary), var(--mee-color-surface) etc.
                     (for component SCSS not expressible via Tailwind)

OPEN Qs: none triggered by design system integration.

In progress: Dispatch 1 — LandingComponent (meesell-angular-component-builder)
Blockers (unchanged):
  - Q-AUTH-001 (folder rename) — BLOCKS auth components; NOT landing
  - Q-AUTH-002 (resend timer) — BLOCKS OtpVerify
  - Q-AUTH-003 (profileComplete) — BLOCKS OtpVerify routing
=========

=== UPDATE: 2026-06-06 DISPATCH 1 COMPLETE — LandingComponent ===
Phase: CONSTRUCTION — Dispatch 1 done; waiting for Q answers to start Dispatch 2.

DISPATCH RESULT: meesell-angular-component-builder — LandingComponent ✓ ACCEPTED

Files produced:
  ✓ features/landing/landing/landing.component.ts (120 lines)
      Standalone, OnPush, host class "mee-landing"
      Imports: RouterLink, MatButtonModule, TranslocoModule
      Sections: sticky navbar (brand + Log in link + Sign up button) /
                hero (headline + sub + CTA) / 3-card value props / footer
      All strings via Transloco pipe (consistent with codebase pattern)
      Zero hardcoded hex values; all tokens via Tailwind utilities
      WCAG: aria-label on CTAs, aria-hidden on decorative icons,
            aria-labelledby on hero, nav role labelled, min 44×44 touch targets
  ✓ features/landing/landing/landing.component.spec.ts (137 lines)
      Vitest + Angular TestBed (zoneless + JIT) + TranslocoTestingModule
      6/6 tests passing:
        renders brand name "MeeSell" in navbar
        renders hero headline from transloco
        Sign up element with routerLink="/signup"
        Log in link with routerLink="/login"
        3 value prop article cards
        footer copyright text
  ✓ i18n/en.json — 6 keys appended (landing.value.{catalog,quality,pricing}.{title,body})

Build verification (coordinator-run):
  ng build --configuration=production: ✓ ZERO errors, ~4.4s
  Landing chunk: 3.68 KB raw / 1.31 KB gzip (budget: 80 KB; 98% headroom)

Full vitest run (coordinator-run):
  168 tests total — 161 passed / 7 failed
  7 failures are PRE-EXISTING, OUT OF SESSION SCOPE:
    export/export/export.component.spec.ts — 7 tests (catalog sub-session owns)
    layouts/shell/shell.component.spec.ts — 1 suite (cross-cutting session owns)
  Landing suite: 6/6 ✓ — no regressions introduced by this dispatch

Agent deviations accepted:
  (a) Transloco pipe used (| transloco) instead of *transloco="let t" structural
      directive — matches codebase pattern established by service-builder +
      DashboardComponent. Pipe is correct.
  (b) CommonModule omitted — correct; no *ngIf/*ngFor needed (pure Angular 18
      native control flow; static template needs neither).

TOKEN USAGE CONFIRMED (no violations):
  bg-bg, bg-bg-elevated, bg-surface, bg-surface-variant — ✓
  text-on-surface, text-on-surface-variant, text-primary — ✓
  shadow-mee-1, rounded-mee-md, rounded-mee-full — ✓
  text-mee-xl, text-mee-3xl, text-mee-4xl, text-mee-lg, text-mee-sm — ✓
  duration-standard — ✓
  Material Symbols Outlined (inventory_2, task_alt, trending_up) — ✓
  color="primary" on MatButton (resolves to #F26B23 via Spike) — ✓

NEXT DISPATCH GATE: Q-AUTH-001/002/003 answers from master.
  While waiting: no parallel work available in this session scope.
  LandingComponent is the only unblocked component. Done.
=========

=== UPDATE: 2026-06-06 SKELETON ===
STATUS file created by master per FE-D12 amended grouping. Bootstrap
prompt authored at docs/SESSION_PROMPTS_FEATURE_AUTH.md (paired with
BASE). Auth sub-session awaits founder bootstrap.
=========

## Questions for master

**Q-AUTH-001 (2026-06-06) — Folder rename: account/ → auth/ + onboarding/ + profile/**
The 2026-06-06A amendment updated §2.B + §3.C.4 + §23 to un-merge account/
into auth/ + onboarding/ + profile/. The service-builder scaffold (2026-06-05)
created features/account/ (old structure). No auth/ folder exists in code.
LandingComponent can proceed (landing/ is correct). For /signup + /login
components, I need either:
(a) This session owns the rename of account/signup/ → auth/signup/ +
    account/login/ → auth/login/ + account/components/otp-verify/ →
    auth/components/otp-verify/ + split account.routes.ts into auth.routes.ts
    + the update to app.routes.ts (app.routes.ts is cross-cutting scope)
(b) Cross-cutting session owns the structural rename + routes split; auth
    sub-session waits and then builds component bodies
Recommend (a) — rename is a mechanical code move; naming it "cross-cutting"
adds sequencing risk. But app.routes.ts edits are cross-cutting scope. Needs
founder ruling.

**Q-AUTH-002 (2026-06-06) — Resend timer: 30s (§7) vs 60s (session prompt)**
§7 Feature: account says "30-second resend timer". Session bootstrap prompt
says "60-second resend timer". Backend iam §7.B.1 has 5-minute OTP TTL + 3/h
rate limit with no explicit per-send resend window at the API layer. Which is
the correct value? Will implement whichever master confirms.

**Q-AUTH-003 (2026-06-06) — profileComplete in OTP verify response**
Backend §7.B.2 VerifyOtpResponse = { access_token, expires_in, token_type }
only. No profile_complete field. The service-builder's AccountApiService stub
added profileComplete: boolean to the response interface (incorrect per locked
backend spec). Post-verify redirect to /onboarding vs /dashboard requires
knowing profile completeness. How should OtpVerifyComponent determine this?
Options:
(a) Immediate GET /seller-profile after verify — adds RTT but uses existing
    endpoint
(b) Backend adds profile_complete to VerifyOtpResponse — backend amendment needed
(c) Keep profileComplete in the stub and accept the backend will add it
Will implement per master ruling. Proceeding with option (a) until answered.

## Questions for sibling sessions

_(sub-session appends here; sibling reads own STATUS first)_

=== UPDATE: 2026-06-06 MASTER RULINGS RECEIVED ===

Q-AUTH-001 ✅ RULED — ALLOW RENAME. Auth sub-session executes:
  - Create features/auth/ with auth.routes.ts + auth-api.service.ts (sendOtp + verifyOtp only)
  - Move login/ + signup/ + otp-verify/component → auth/
  - Discard account.routes.ts + AccountApiService methods not auth-related
  - Cross-cutting session owns app.routes.ts update (coordinate lockstep)
  - Gate: ng build + vitest pass before auth component dispatches continue

Q-AUTH-002 ✅ RULED — 60s resend timer confirmed.
  §7 "30s" superseded. OtpVerifyComponent: 60-second countdown.

Q-AUTH-003 ✅ RULED — Option A: GET /seller-profile post-verify.
  OtpVerifyComponent flow after successful verify:
    1. AccountApiService.verifyOtp() stores token in AuthService (already wired)
    2. Call GET /seller-profile
    3. profile_complete: true → navigate('/dashboard')
    4. profile_complete: false OR 404 → navigate('/onboarding')
  Remove incorrect profileComplete: boolean from OtpVerifyResponse interface.

Blockers cleared: Q-AUTH-001 + Q-AUTH-002 + Q-AUTH-003 all resolved.
Auth sub-session may now proceed with rename dispatch + component dispatches.
=========

=== UPDATE: 2026-06-07 DISPATCH 3 COMPLETE — OtpVerifyComponent body ===
Phase: HANDOFF — session V1-COMPLETE.

DISPATCH RESULT: meesell-angular-component-builder — OtpVerifyComponent ✓ ACCEPTED

Files produced:
  ✓ features/auth/components/otp-verify/otp-verify.component.ts (196 lines)
      Standalone, OnPush, host class "mee-otp-verify"
      Imports: NgOtpInputModule, MatButtonModule, MatProgressSpinnerModule,
               TranslocoModule
      @Inputs: phone (E.164), requestId (MSG91 correlation ID)
      Signals: otpValue, verifying, resending, timeLeft (60→0), attempts (0→3), errorMsg
      Computed: displayPhone() — strips +91 prefix for display
      Countdown: interval(1000) + take(60) + takeUntilDestroyed — restartable on resend
      OTP input: NgOtpInputModule; (onInputChange) → auto-submit at 6 chars
      Verify flow:
        → AuthApiService.verifyOtp({ phone, otp }) [setAccess wired via tap]
        → ApiClient.get<SellerProfile>('/seller-profile') [Q-AUTH-003 Option A]
        → profile_complete: true → /dashboard | false/404 → /onboarding
      Error handling (M3 — plain language, never backend codes):
        3rd wrong attempt → auth.otp_attempts_exceeded (inline errorMsg)
        429 → account.otp.rate_limit via ErrorService snackbar
        400/422 → auth.otp_invalid (inline errorMsg) + attempts++
      Resend: shows when timeLeft===0 && attempts<3; calls sendOtp + restarts timer
      WCAG: role="group" on OTP input, aria-live="assertive" on error, aria-live="polite"
            on subtitle, aria-label on verify button, min 44×44 touch targets
      Zero hardcoded hex values; all tokens via Tailwind utilities or CSS var()

  ✓ features/auth/components/otp-verify/otp-verify.component.spec.ts (143 lines)
      Vitest + Angular TestBed (zoneless + JIT) + TranslocoTestingModule
      6/6 tests passing:
        renders the OTP title from transloco
        renders sent-to subtitle with phone stripped of +91
        renders the ng-otp-input element
        verify button is disabled initially when otpValue is empty
        shows resend countdown "Resend in 60s" on initial render
        renders error message in role="alert" element when errorMsg is set

  ✓ i18n/en.json — 2 keys appended:
      "auth.otp_invalid": "That code doesn't match. Try again."
      "auth.otp_attempts_exceeded": "Too many attempts. Request a new code."

Build verification (sub-session-run):
  ng build --configuration=production: ✓ ZERO errors; warnings are pre-existing NG8102/NG8107
  OtpVerify chunk: NOT separately chunked (rendered inline in signup/login chunks)

Full vitest run (sub-session-run):
  254 tests total — 238 passed / 16 failed
  16 failures are ALL PRE-EXISTING (no regressions from Dispatch 3):
    export/export.component.spec.ts — 7 tests (catalog sub-session owns)
    dashboard/dashboard.component.spec.ts — 6 tests (styleUrl vitest jsdom known issue)
    layouts/shell/shell.component.spec.ts — 1 suite
    images/image-slot/image-slot.component.spec.ts — 1 test
    images/precheck-report/precheck-report.component.spec.ts — 2 tests
  OtpVerify suite: 6/6 ✓ — no regressions introduced

Agent deviation accepted:
  (a) NgOtpInputModule in imports[] (not NgOtpInputComponent) — ng-otp-input v1.9.3
      is NgModule-based; not standalone-ready. NgOtpInputComponent retained as
      @ViewChild type annotation only. Runtime behavior identical.

SESSION STATUS: V1-COMPLETE
  All 3 dispatches done. Routes /  /signup  /login  component implementations complete.
  Pending: cross-cutting session updates app.routes.ts to register AUTH_ROUTES
           (see Hand-offs section above).
=========
