# Google Sign-In — FRONTEND Wave Plan (execution)

**Status:** IN PROGRESS
**Author:** meesell-frontend-coordinator (Frontend Lead), executing directly (opus)
**Worktree:** /private/tmp/mesell-wt/google-auth (branch feature/google-auth, off develop)
**Date:** 2026-06-18
**Design doc:** docs/plans/google_auth/GOOGLE_AUTH_DESIGN_FRONTEND.md (master tree)

## Founder-ratified decisions implemented to
- Dual identity: phone OR Google. Google button on BOTH /login and /signup.
- GIS ID-token flow. Backend contract: `POST /api/v1/auth/google/verify` body `{credential}` → `VerifyOtpResponse` + HttpOnly refresh cookie.
- Build directly to this contract (backend built in parallel to it).

## Waves

### FE-W1 — GoogleIdentityService + env client id
- `libs/core/services/google-identity.service.ts` — lazy GSI script inject, initialize, renderButton, zoneless-safe callback marshalling.
- `libs/core/types/google-gsi.d.ts` — minimal ambient `window.google.accounts.id` typing.
- `@mesell/env`: add `googleOauthClientId` to interface + dev + prod files.

### FE-W2 — AuthApiService.googleVerify + nullable phone
- `AuthApiService.googleVerify(credential): Observable<VerifyOtpResponse>` POST withCredentials.
- `MeResponse.phone` + `AuthUser.phone` → nullable (Google-only users have no phone).

### FE-W3 — AuthService.completeLogin shared success tail
- `completeLogin(resp): Observable<{route:string[]}>` — token set → /me → setSession(3-arg, auto scheduleRefresh) → onboarding-gate routing.
- Refactor otp-verify onSubmit tail to reuse it (symmetry).

### FE-W4 — Google button on login + signup
- "or" divider, GIS-rendered button, googleLoading state, error matrix via mee-alert-banner, mobile + a11y.

### FE-W5 — Specs
- AuthApiService.googleVerify, AuthService.completeLogin, GoogleIdentityService, login/signup Google path.

## Validation
- ng test (libs/core + mfe-auth), lint changed files, type-check mfe-auth + libs/core build.

## Open issues for integration
- Backend contract must match §B (path/body/response/cookie/aud client id). [RECONCILE-BE]
- Phone nullability (OQ-4) — implemented FE-side as nullable.
- CSP add-only + OAuth client provisioning → infra (post-merge memo).

