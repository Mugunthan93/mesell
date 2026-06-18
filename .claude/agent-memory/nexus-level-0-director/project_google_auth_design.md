---
name: google-auth-design
description: Google sign-in BUILT on feature/google-auth worktree (2026-06-18); flag-gated OFF, not pushed/no PR; awaiting integration + infra
metadata:
  type: project
---

Google sign-in for MeeSell auth module: DESIGN/PLAN phase complete on 2026-06-18, status **HELD — not building**.

**Design docs (authored, no code):**
- `docs/plans/google_auth/GOOGLE_AUTH_DESIGN_BACKEND.md` (meesell-backend-coordinator)
- `docs/plans/google_auth/GOOGLE_AUTH_DESIGN_FRONTEND.md` (meesell-frontend-coordinator)

**Founder decisions locked (2026-06-18):**
1. Identity model = **dual identity** (phone OR Google). `iam.users.phone` → nullable; `email` → unique; new `google_sub` (unique) + `auth_provider`; CHECK `phone IS NOT NULL OR google_sub IS NOT NULL`. Identities inline on users (normalized table deferred to V1.5).
2. OAuth flow = **Google Identity Services (ID-token)**, reusing the FE-D5 split-token machinery.
3. Account-linking = **auto-link on verified email** (email_verified==true + exact email match; 409 on google_sub mismatch). Match order: google_sub → verified email (link) → new Google-only user (phone NULL).
4. Contract: `POST /api/v1/auth/google/verify` body `{credential}` → `VerifyOtpResponse` shape + same refresh cookie. FE `AuthService.completeLogin()` shared tail; `MeResponse.phone`/`AuthUser.phone` become nullable.

**BUILT 2026-06-18.** Founder said "execute" → treated as ratification of the Decision #5 amendment. Built in parallel (BE + FE coordinators) in worktree `/private/tmp/mesell-wt/google-auth`, branch `feature/google-auth` (off develop 86dfb86). 8 commits, 53 files (+3735/−71). **SPLIT backend-first (founder 2026-06-18):** PR #294 CLOSED/superseded → **PR #295 backend-first** (feat/google-auth-backend, 5 BE commits + §7.3 amendment, MERGE FIRST) + **PR #296 frontend** (feat/google-auth-frontend, 3 FE commits, MERGE AFTER #295). Both base develop, OPEN, awaiting founder gate. Decision #5 amendment RATIFIED in locked BACKEND_ARCHITECTURE.md §7.3/§17 (commit 5eda708). Scratch worktrees: /private/tmp/mesell-wt/{ga-backend,ga-frontend} (+ original google-auth) — prune after merge. Endpoint flag-gated `FEATURE_GOOGLE_AUTH_ENABLED` default OFF (route not mounted → §17 stays 28 until flipped).

Contract (FE↔BE reconciled): `POST /api/v1/auth/google/verify` {credential} → VerifyOtpResponse + refresh cookie; new-user signal via /me onboarding_complete; phone nullable both sides. Migration `c2d3e4f5a6b7` in both alembic chains (svc down_rev b1c2d3e4f5a6; monolith down_rev b7c2e1a9d3f4).

**OUTSTANDING before this is live (integration step):**
1. ✅ DONE — `BACKEND_ARCHITECTURE.md` §7.3 amendment ratified (commit 5eda708, in PR #295).
2. Merge ORDER: #295 (backend) FIRST, then #296 (frontend). FE specs WRITTEN but UNEXECUTED — sandbox had no esbuild/network; CI must run `ng test` on #296.
3. Infra: provision 2 GCP OAuth Web clients (dev/prod) on the SHELL origin, set GOOGLE_OAUTH_CLIENT_ID per namespace, flip FEATURE_GOOGLE_AUTH_ENABLED (dev first), add GIS to CSP.
4. Pre-existing (NOT this feature): 3 svc-iam parity test reds (dev-otp-bypass + cookie-domain drift); FE spec-ahead-of-component drift in mfe-onboarding/profile/shell/ui-kit.

**How to apply:** Next is integration — push feature/google-auth + open PR → develop (founder gates). Do NOT enable the flag in any namespace until infra provisions the OAuth client id.
