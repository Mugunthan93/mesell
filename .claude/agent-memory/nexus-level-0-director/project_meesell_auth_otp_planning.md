---
name: meesell-auth-otp-planning
description: auth-otp Feature 1 planning session — FEATURE_PLAN.md complete (1561 lines), committed to feature/auth-otp/planning, awaiting master consolidation
metadata:
  type: project
---

Feature: auth-otp (Feature 1 of 9 — prerequisite zero)
Session: mesell-auth-otp-planning-session-1
Date: 2026-06-10
Status: PLAN READY — held for master consolidation

## What was produced

- `docs/plans/features/auth-otp/FEATURE_PLAN.md` — 1561 lines, v0.5
  - Committed as `c1a41e9` on branch `feature/auth-otp/planning`
  - Pushed to `origin/feature/auth-otp/planning`
  - Note: committed BEFORE the parallel-sessions COORDINATION INTERRUPT arrived; do NOT open PR — master handles consolidation

## Decisions locked (D1–D4)

- **D1**: Scope confirmed — FE-D5 + §7 contract is the exact build target
- **D2**: No feature flag — auth lands unconditionally on develop
- **D3**: Auth first, strict sequential — no other feature branch opens until auth-otp merges to develop
- **D4**: 3 leads + 7 specialists — `meesell-backend-coordinator` (4 specialists), `meesell-frontend-coordinator` (3 specialists, including ui-styler added by founder), `meesell-infra-builder` (standalone)

## Key contracts in the plan

- FE-D5 split-token: access JWT in Angular signal (never localStorage), refresh token as HttpOnly cookie at Path=/api/v1/auth
- Lua-atomic rotation: EVALSHA primary + EVAL fallback on NOSCRIPT
- HMAC-SHA256 pepper key — NOT bare SHA-256
- TTLs: dev=30s/120s, staging=60s/300s, prod=900s/604800s (env-driven)
- `secrets.compare_digest()` for allowlist lookup — NEVER `==`
- `withCredentials: true` ONLY on `/api/v1/auth/` XHR calls

## Implementation status at planning close (audited 2026-06-10)

- Backend: ~95% complete (all 6 service methods, full domain/exceptions/router/core/auth.py)
- Frontend: ~30% (UI scaffolded; zero HTTP wiring; both interceptors missing; phone not read from query params)
- Infra: ~60% (4 secrets LIVE; K8s env-var additions + runbook still needed)

## Pre-seeded lead memories

- `.claude/agent-memory/meesell-backend-coordinator/auth_otp_feature.md` ✅
- `.claude/agent-memory/meesell-frontend-coordinator/auth_otp_feature.md` ✅
- `.claude/agent-memory/meesell-infra-builder/auth_otp_feature.md` ✅

## Branch state

- `feature/auth-otp/planning` — 6 commits; pushed to origin
- Per COORDINATION INTERRUPT: no PR opened; master consolidation handles it
- `feature/auth-otp`, `feature/auth-otp/backend`, `feature/auth-otp/frontend`, `feature/auth-otp/infra` — NOT YET CREATED (documented in FEATURE_PLAN.md §Branch setup; founder creates them after PR #3/planning merges to develop)
