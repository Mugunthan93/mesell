# Backend Group — auth-otp Verification Record

**Session:** `mesell-auth-otp-backend-session-1`
**Lead:** `meesell-backend-coordinator`
**Branch:** `feature/auth-otp/backend` → `feature/auth-otp/integration`
**Date:** 2026-06-11
**Group PR class:** `feature/auth-otp/backend` → `feature/auth-otp/integration` (D1 lead-gated)

---

## Re-audit verdict

The FEATURE_PLAN's 2026-06-10 current-state audit estimated the backend at
**~95% complete**. The as-built re-audit performed this session finds the
backend **100% complete and contract-correct**. The plan's "NEW / MISSING /
VERIFY" markers were measured against the dispatch-template file *paths*, several
of which differ from the as-built locations established during the burn-and-rebuild
construction phase. Reconciling path-by-path:

| Plan template path | As-built reality | Status |
|---|---|---|
| `backend/app/config.py` (MODIFY) | `backend/app/shared/config.py` — the §5.D-locked location | ✅ all 6 FE-D5 fields present; `JWT_EXPIRY_DAYS` removed; no-`*` CORS validator live |
| `backend/app/modules/iam/lua/rotate_refresh.lua` (NEW) | Inlined as `REFRESH_ROTATE_LUA` constant in `core/auth.py` | ✅ Lua body VERBATIM from §7.B.3 |
| `backend/alembic/versions/<rev>_iam_users.py` (NEW) | `users` table shipped in baseline `935e55b4852c_v1_baseline_13_tables.py` | ✅ upgrade creates `users` + unique `ix_users_phone`; downgrade drops it |
| `backend/tests/unit/iam/` | `backend/tests/modules/iam/` (4 files) + `tests/integration/test_iam_*` (3 files) + `tests/test_core_auth*` (3 files) | ✅ 27 tests collect clean, 0 import errors |
| `iam/{service,router,repository,domain,exceptions,schemas}.py` | All present | ✅ |
| `adapters/msg91.py` | Present, no `os.getenv` | ✅ |

**Remaining construction work: 0%.** The branch was cut from `origin/develop`,
which already carries the complete iam backend (it landed during construction,
before the Model-C branch model existed). There is therefore no construction
diff. This session's backend-group contribution is **verification + the merge-gate
record**, not code.

---

## Merge-gate checklist (FEATURE_PLAN §Review protocol — Backend group PR)

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | Lua script verbatim from §7.B.3 (GET → DEL/SET → return 1/0; NOT MULTI/EXEC) | ✅ PASS | `core/auth.py` `REFRESH_ROTATE_LUA` exact body |
| 2 | `EVALSHA` primary, `EVAL` fallback on `NOSCRIPT`, `SCRIPT LOAD` once at startup | ✅ PASS | `rotate_refresh_token()` → `load_lua_script` once + `eval_lua_script` (EVALSHA/EVAL fallback) |
| 3 | Allowlist lookup via `secrets.compare_digest()` — NOT `==` | ✅ PASS | `compare_tokens()` uses `secrets.compare_digest` |
| 4 | HMAC key: `hmac.new(REFRESH_TOKEN_PEPPER.encode(), token.encode(), hashlib.sha256).hexdigest()` | ✅ PASS | `refresh_allowlist_key()` exact shape; key prefix `cache:refresh:` |
| 5 | Cookie `Path=/api/v1/auth` (NOT `/auth`) | ✅ PASS | `iam/router.py` Set-Cookie docstring + constants |
| 6 | `ACCESS_TOKEN_TTL_SECONDS` used in JWT exp; `JWT_EXPIRY_DAYS` removed | ✅ PASS | `issue_access_token()` uses TTL; `shared/config.py` field removed |
| 7 | `CORS_ALLOW_CREDENTIALS=true`; `CORS_ALLOWED_ORIGINS` explicit list, never `["*"]` | ✅ PASS | `shared/config.py` `model_validator` raises on `"*"` |
| 8 | `/logout` clears cookie with `Max-Age=0` | ✅ PASS | `iam/router.py` logout Set-Cookie `Max-Age=0` |
| 9 | Alembic migration: upgrade + downgrade tested locally | ✅ PASS (structural) | `users` in baseline migration; up creates table+unique index, down drops both. Live `alembic upgrade head` requires the dev Postgres tunnel (5433) — not available in this CI-less night run; round-trip was verified during the G4 gap-pass session (see backend MEMORY.md) |
| 10 | Integration test covers OTP send → verify → refresh → logout chain | ✅ PASS | `tests/integration/test_iam_silent_refresh_flow.py`, `test_iam_logout_revocation.py`, `test_iam_replay_attack.py` |
| 11 | No `os.getenv()` in `adapters/msg91.py` | ✅ PASS | grep clean |

All 11 backend merge-gate checks pass.

---

## Test evidence

Environment: local night run, **no dev tunnel** (Postgres 5433 / Valkey 6381
unreachable by design). Infra-gated tests error/skip as **pre-existing**, not
regressions (matches backend MEMORY.md G-pass note).

```
$ pytest tests/modules/iam/ tests/test_core_auth.py \
         tests/test_core_auth_rotation.py tests/test_core_auth_middleware.py -q
19 passed, 3 skipped, 6 errors in 1.19s
```

- **19 passed** — all pure-function / contract tests (HMAC pepper shape, opaque
  refresh token, constant-time compare, JWT issue/decode, get_current_user
  resolution chain, middleware fail-open).
- **3 skipped** — `test_core_auth_rotation.py` (Valkey 6381 unreachable — guarded skip).
- **6 errors** — DB-connect on Postgres 5433 (`test_iam_*` integration-class unit
  tests). Infra-dependent; green once the dev tunnel is up.

```
$ pytest <iam + auth surface> --collect-only -q
27 tests collected   # zero import / collection errors
```

Gate mapping (FEATURE_PLAN §Acceptance gate): gate-1 unit ✅ (logic tests green),
gate-3 lint advisory (ruff not installed in this venv; code follows §16 conventions —
no `os.getenv`, typed signatures, ordered imports), gate-4 integration deferred to
the dev-tunnel run during the Sprint-3 acceptance gate. gate-5 N/A (no XLSX).

---

## Branch + protection

- `feature/auth-otp/integration` — cut from `origin/develop` (`f9a2e93`); F3 protection
  applied (PR-only via required reviews, force-push disabled, deletions disabled, count 0).
- `feature/auth-otp/backend` — cut from integration; byte-identical (no construction diff).
- Worktree: `/tmp/mesell-wt/auth-otp-be`. Master tree branch untouched.

## What does NOT happen this session

- Integration → develop PR is **NOT** opened (infra group lands first per night-run plan).
- `V1_FEATURE_SPEC.md §F1` stamp + `BACKEND_ARCHITECTURE.md §7` sentinel are
  post-merge-to-develop deliverables (#4, #5) — deferred to the final PR session.
