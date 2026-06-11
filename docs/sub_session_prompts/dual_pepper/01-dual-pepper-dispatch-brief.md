# Dual-Pepper Rotation — Session Dispatch Brief

**Session name:** `mesell-dual-pepper-session-1`
**Date authored:** 2026-06-11 (master session, founder-approved parallel lane)
**Status:** READY — clears the R5 backlog item early (board row `dual-pepper-rotation`, pre-V1.5-prod gate)

---

## What this session is

You are a dedicated sub-session to implement **dual-pepper grace-window rotation** for refresh tokens. Today `REFRESH_TOKEN_PEPPER` is single and unversioned — rotating it instantly invalidates every live session (prod rotation would be incident-only). This task makes pepper rotation a safe, planned operation.

Dispatch `meesell-backend-coordinator`, which dispatches `meesell-auth-builder` (the board-assigned owner). **Only `meesell-*` agents may execute MeeSell work.**

## Required reading (in order)

1. `CLAUDE.md` (project root)
2. `docs/runbooks/auth-secret-rotation.md` — **§2 is the spec** (R5 dual-pepper version-tagged grace window)
3. `docs/status/feature_board_backend.md` — the `dual-pepper-rotation` PENDING row (scope + key-prefix design)
4. `docs/plans/features/auth-otp/FEATURE_PLAN.md` §7.B + `BACKEND_VERIFICATION.md` — the as-built auth internals
5. `.claude/agent-memory/meesell-backend-coordinator/MEMORY.md` + `auth_otp_feature.md` — **critical path corrections**: config lives at `backend/app/shared/config.py` (NOT `app/config.py`); the rotation Lua is inlined as `REFRESH_ROTATE_LUA` in `backend/app/core/auth.py`; iam tests live at `tests/modules/iam/` + `tests/test_core_auth*.py`
6. `docs/plans/repo_management/MASTER_PLAN.md` — Model C conventions

## Scope (per runbook §2 + the board row)

1. **Version-tagged allowlist keys**: `cache:refresh:{version}:{hmac}` (today: `cache:refresh:{hmac}`, see `refresh_allowlist_key` in `core/auth.py`)
2. **Dual-pepper read path**: during a grace window, validation tries the CURRENT pepper first, falls back to PREVIOUS; writes always use CURRENT
3. **Config** (in `shared/config.py`): `REFRESH_TOKEN_PEPPER_PREVIOUS` (optional, empty = no grace window) + `REFRESH_TOKEN_PEPPER_VERSION` (or equivalent per §2 — the runbook wording wins)
4. **Lua compatibility**: the `REFRESH_ROTATE_LUA` rotation script must keep working against versioned keys
5. **Migration/compat**: existing unversioned keys must either be honored during one grace window or the design must document the one-time cutover (short dev/staging TTLs make this cheap — runbook §1)
6. **Tests**: unit tests for key derivation + dual-read fallback + rotation flow; honor the no-tunnel reality (19-passed/3-skipped/6-errors is the known no-tunnel baseline — your NEW tests must be pure-function/fakeredis-style so they pass without infra)
7. **Runbook update**: flip §2 from "NOT yet implemented" to as-built, with the exact env-var rotation procedure
8. `backend/.env.example`: add the new vars with comments

## OUT of scope

- k8s secret manifests / GCP Secret Manager entries (that's infra — open an inter-lead request on the board for the new secret refs; do NOT edit k8s/)
- Frontend (no contract change — token shape is untouched)
- Any other auth behavior (TTLs, cookie flags, Lua rotation semantics)

## Git conventions (Model C)

- ALL branch work in worktrees under `/tmp/mesell-wt/dp-*` — NEVER switch the master tree's branch.
- `feature/dual-pepper-rotation/integration` from develop (F3 protection: PR-only, count 0, no force-push/deletions) + group branch `feature/dual-pepper-rotation/backend`.
- Group → integration: lead-gate as PR comment + squash `--admin`; delete remote refs via `gh api -X DELETE` (the `--delete-branch` worktree gotcha).
- Integration → develop: **FOUNDER-ONLY** gate — open `[FOUNDER GATE — DO NOT MERGE]` with evidence, leave open.
- Explicit-path staging. Board flips per §6.5/F2 (PENDING → IN PROGRESS → IN REVIEW → MERGED).

## Parallel-lane discipline

Frontend Wave 1 (SP02/SP03), AI, Legal, and CI-activation sessions may be running. You own `backend/app/core/auth.py`, `backend/app/shared/config.py` (additive fields), iam tests, the runbook §2 flip, `.env.example`, and backend status surfaces. Touch NOTHING else. Status/board pushes: pull --rebase first, push immediately, retry on rejection.

## Session end

Update `STATUS_BACKEND.md` + `feature_board_backend.md` + coordinator memory (auth_otp_feature.md gets the new contract). Report: PRs, the founder-gate PR number, test evidence, the inter-lead secret request, and the updated rotation procedure summary.
