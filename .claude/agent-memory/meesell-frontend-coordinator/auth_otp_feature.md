---
name: auth-otp-feature
description: auth-otp Feature 1 — frontend coordinator awareness, dispatch plan, specialist chain, branch ownership
metadata:
  type: project
---

Feature: auth-otp (Feature 1 of 9 V1 features)
Status: PLAN READY → IN REVIEW (PR #3 open on feature/auth-otp/planning)
Plan document: docs/plans/features/auth-otp/FEATURE_PLAN.md
Date seeded: 2026-06-10

## Your role in this feature

You are the lead for the frontend group. You:
- Own `docs/status/feature_board_frontend.md` — update it at session start and session close
- Are the merge gate for `feature/auth-otp/frontend` → `feature/auth-otp` PR
- Dispatch 3 frontend specialists in phase order (D → D → E)
- Use dispatch templates from FEATURE_PLAN.md — templates are ready to paste

## Branch you own

`feature/auth-otp/frontend` (to be created from `feature/auth-otp` after plan is LOCKED)

Do NOT create branches until FEATURE_PLAN.md PR #3 merges to develop and the tracker shows LOCKED.

## Specialist dispatch order

```
PHASE D (dispatch service-builder first, then component-builder after service-builder reports COMPLETE):
  meesell-angular-service-builder   → Template E in FEATURE_PLAN.md
  (AuthService signal, RefreshInterceptor, auth.interceptor.ts MODIFY, authGuard, app.routes.ts)

  meesell-angular-component-builder → Template F in FEATURE_PLAN.md
  (Login, Signup, OtpVerify components — after service-builder so AuthService interface is stable)

PHASE E (after component-builder reports COMPLETE):
  meesell-angular-ui-styler         → Template H in FEATURE_PLAN.md
  (Tailwind styling for 3 auth components — after components exist)
```

**Note:** Phase D can begin in parallel with backend Phase C (api-routes-builder), but service-builder
must complete before component-builder starts. Coordinate timing with backend-coordinator.

## Key contracts you enforce in PR review

Read FEATURE_PLAN.md "Review + iteration protocol — Frontend group PR" for the full 14-check list.
Critical checks:
1. `_token = signal<string | null>(null)` — never localStorage/sessionStorage
2. `withCredentials: true` ONLY on `/api/v1/auth/` URLs (not globally)
3. RefreshInterceptor has BehaviorSubject dedup (refresh storm prevention)
4. `authGuard` is synchronous (signal read only, no HTTP call)
5. No direct PrimeNG imports in features/auth/ or core/
6. `pnpm build` < 90s (Decision 12)
7. No hard-coded hex in *.component.scss (ui-styler check)

## Architecture context (FE-D5 split-token contract)

- Access JWT: held in `signal<string | null>(null)` in AuthService — NEVER in localStorage
- Refresh token: HttpOnly cookie owned by backend — browser sends it automatically on `/api/v1/auth/*`
- `withCredentials: true` ONLY on auth route XHR calls — NOT globally
- Auth pages (Login, Signup, OtpVerify) live in shell app for V1 — NOT in mfe-auth (mfe-auth is the LAST to federate per module federation master plan §4.2)
- All components: standalone: true, ChangeDetectionStrategy.OnPush
- No NgModules anywhere in frontend

## What to update when your dispatch session completes

Update this file with:
- Which specialists were dispatched and when
- Phase D service-builder COMPLETE date
- Phase D component-builder COMPLETE date
- Phase E ui-styler COMPLETE date
- PR # for feature/auth-otp/frontend → feature/auth-otp
- Blockers if any
