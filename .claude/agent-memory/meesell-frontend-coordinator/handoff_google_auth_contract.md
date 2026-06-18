# Handoff → backend: Google Sign-In contract reconcile

**From:** meesell-frontend-coordinator (Frontend Lead)
**To:** meesell-backend-coordinator
**Date:** 2026-06-18
**Feature:** google-auth (built on `feature/google-auth` worktree, FE committed)
**Design:** docs/plans/google_auth/GOOGLE_AUTH_DESIGN_FRONTEND.md §B + GOOGLE_AUTH_DESIGN_BACKEND.md

## FE built to this contract — backend MUST match

| Item | FE assumption (as-built) |
|---|---|
| Path | `POST /api/v1/auth/google/verify` |
| Request body | `{ "credential": "<google-id-token-jwt>" }` (Content-Type application/json) |
| Response | `VerifyOtpResponse` verbatim: `{ access_token, expires_in, token_type:'bearer' }` |
| Cookie | sets HttpOnly refresh_token, `Path=/api/v1/auth`, same as `/otp/verify` (FE sends `withCredentials:true`) |
| `aud` | backend verifies the ID token `aud` == our `GOOGLE_OAUTH_CLIENT_ID` — FE pins the SAME id in `@mesell/env` (dev + prod placeholders, infra to provision) |
| New-user signal | rides on `GET /auth/me` `onboarding_complete:false`, NOT the verify response (keep verify symmetric with OTP) |

## Phone nullability (OQ-4) — FE DECISION TAKEN
FE made `MeResponse.phone` and `AuthUser.phone` **nullable** (`string | null`) because a
Google-only user has no phone. Backend MUST return `phone: null` (not omit, not synthesise)
for Google users without a phone. If backend instead forces a phone at onboarding, the FE
nullable type is still safe (superset) — no FE rollback needed either way.

## OQ-1 (phone required for Google users?) — STILL OPEN, backend/product call
FE routes new Google users to existing `/onboarding`. Whatever fields onboarding requires is
governed by the onboarding feature + backend. FE will NOT design a phone-capture-with-OTP
sub-step until backend rules are locked.

## Action
Confirm the table above against GOOGLE_AUTH_DESIGN_BACKEND.md. Any drift (path, body key,
response shape, cookie path, aud client id) becomes a runtime 4xx. 48h SLA.

