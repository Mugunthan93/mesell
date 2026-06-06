# STATUS — FEATURE AUTH

**Owner:** Auth Sub-Session (session-as-role)
**Master:** `meesell-frontend-coordinator` session
**Bootstrap prompt:** `docs/SESSION_PROMPTS_FEATURE_AUTH.md` (paired with `docs/SESSION_PROMPTS_FEATURE_BASE.md`)
**Code root:** `frontend/src/app/features/auth/` + `frontend/src/app/features/landing/`
**Routes owned:** `/`, `/signup`, `/login`
**MF-remote target (Phase 2):** auth-mfe per FE-D13
**Created:** 2026-06-06 by frontend coordinator per FE-D12 amended grouping
**Last update:** 2026-06-06 (initial skeleton — auth sub-session not yet bootstrapped)

**Status:** Session not yet started — initialize by opening a new Claude Code window and pasting bootstrap prompts (BASE + AUTH).

## Current Phase

BOOTSTRAP COMPLETE — 8 mandatory reads done; structural gaps identified;
Q-AUTH-001/002/003 surfaced to master; LandingComponent dispatch ready.

## Done

- Bootstrap reads complete (2026-06-06)
- STATUS update written with architectural state, gaps, i18n posture, validation
  message key mapping
- Q-AUTH-001/002/003 raised for master

## In Progress

- Awaiting founder authorisation for LandingComponent dispatch
- Awaiting master answers on Q-AUTH-001 (folder rename), Q-AUTH-002 (timer),
  Q-AUTH-003 (profileComplete)

## Blockers

- Q-AUTH-001: features/account/ exists; features/auth/ does not — BLOCKS
  auth component dispatches (signup, login, OTP). LandingComponent unaffected.
- Q-AUTH-002: resend timer (30s §7 vs 60s session prompt) — BLOCKS OtpVerify.
- Q-AUTH-003: profileComplete not in backend verify response — BLOCKS redirect
  routing logic in OtpVerify.

## Next

1. Founder authorises LandingComponent dispatch → dispatch meesell-angular-component-builder
2. Founder answers Q-AUTH-001/002/003 (or defers to master session)
3. After folder resolution: dispatch SignupComponent + LoginComponent stubs
4. After Q-AUTH-002/003 answers: dispatch OtpVerifyComponent + PhoneInputComponent

## Hand-offs

_(none yet)_

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
