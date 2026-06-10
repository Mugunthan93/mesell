---
name: auth-otp-feature
description: auth-otp Feature 1 — backend coordinator awareness, dispatch plan, specialist chain, branch ownership
metadata:
  type: project
---

Feature: auth-otp (Feature 1 of 9 V1 features)
Status: PLAN READY → IN REVIEW (PR #3 open on feature/auth-otp/planning)
Plan document: docs/plans/features/auth-otp/FEATURE_PLAN.md
Date seeded: 2026-06-10

## Your role in this feature

You are the lead for the backend group. You:
- Own `docs/status/feature_board_backend.md` — update it at session start and session close
- Are the merge gate for `feature/auth-otp/backend` → `feature/auth-otp` PR
- Dispatch 4 backend specialists in phase order (A → B → C)
- Use dispatch templates from FEATURE_PLAN.md — templates are ready to paste

## Branch you own

`feature/auth-otp/backend` (to be created from `feature/auth-otp` after plan is LOCKED)

Do NOT create branches until FEATURE_PLAN.md PR #3 merges to develop and the tracker shows LOCKED.

## Specialist dispatch order (critical path)

```
PHASE A (parallel — dispatch simultaneously):
  meesell-database-builder   → Template A in FEATURE_PLAN.md
  meesell-services-builder   → Template B in FEATURE_PLAN.md

PHASE B (after both Phase A agents report COMPLETE):
  meesell-auth-builder       → Template C in FEATURE_PLAN.md
  (needs User model shape from database-builder + msg91 adapter interface from services-builder)

PHASE C (after auth-builder reports COMPLETE):
  meesell-api-routes-builder → Template D in FEATURE_PLAN.md
  (needs domain.py + exceptions.py + IamService interface from auth-builder)
```

## Key contracts you enforce in PR review

Read FEATURE_PLAN.md "Review + iteration protocol — Backend group PR" for the full 11-check list.
Critical checks:
1. Lua script VERBATIM from §7.B.3 (not MULTI/EXEC)
2. EVALSHA primary + EVAL fallback on NOSCRIPT
3. `secrets.compare_digest()` for allowlist lookup (not ==)
4. HMAC key: `hmac.new(REFRESH_TOKEN_PEPPER.encode(), token.encode(), hashlib.sha256).hexdigest()`
5. Cookie `Path=/api/v1/auth` (not `/auth`)

## What to update when your dispatch session completes

Update this file with:
- Which specialists were dispatched and when
- Phase A COMPLETE date (both database-builder + services-builder done)
- Phase B COMPLETE date (auth-builder done)
- Phase C COMPLETE date (api-routes-builder done)
- PR # for feature/auth-otp/backend → feature/auth-otp
- Blockers if any
