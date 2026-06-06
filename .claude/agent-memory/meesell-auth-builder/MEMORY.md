# Memory — meesell-auth-builder

## Agent Identity
Authentication specialist for MeeSell. Owns MSG91 OTP integration (Valkey side), PyJWT issuance/validation, auth middleware, plan-guard middleware, rate-limit middleware, DPDP consent storage. Decentralized memory ecosystem.

## Initial State
No prior memories. First task will populate this file.

## MEMORY.md
(Index of memory files — populated as agent works)

---

## §4 core/ CONSTRUCTED (2026-06-06)

### Scope
§4.B `core/auth.py` + §4.G `core/middleware/auth_mw.py`. Joint dispatch with `meesell-services-builder` (services-builder owns the Valkey factory + cross-test-pollution fix via `use_live_valkey` fixture; auth-builder owns JWT issuance/decoding, refresh allowlist HMAC, Lua rotation script, and the request-state middleware).

### Files created
- `backend/app/core/auth.py` (405 LOC)
- `backend/app/core/middleware/auth_mw.py` (119 LOC)
- 3 test files:
  - `backend/tests/test_core_auth.py` (9 cases — unit, no Valkey)
  - `backend/tests/test_core_auth_middleware.py` (5 cases — unit, no Valkey)
  - `backend/tests/test_core_auth_rotation.py` (4 cases — 1 sanity + 3 live-Valkey)

### Locked contracts implemented
- **`CurrentUser`** — frozen dataclass `(user_id: UUID, plan: Literal["free"])`. V1 enum locked to `"free"` only; `"pro"` reserved for V1.5.
- **`get_current_user(token, db) -> CurrentUser`** — FastAPI dependency. Uses `OAuth2PasswordBearer(tokenUrl="/api/v1/auth/otp/verify", auto_error=False)`. Decodes access JWT `{sub, exp, plan}` HS256. Hits DB to verify user exists (auth_mw does NOT — fail-open at middleware, fail-closed at the dep).
- **Three error paths**, all subclass `core.errors.MeesellError`:
  - `TokenMissingError` → 401 / `auth.token_missing` (covers both missing AND malformed tokens per §4.B)
  - `TokenExpiredError` → 401 / `auth.token_expired`
  - `UserNotFoundError` → 403 / `auth.user_not_found`
- **`issue_access_token(user_id, plan="free") -> str`** — HS256, lifetime from `settings.ACCESS_TOKEN_TTL_SECONDS`. Claims: `sub`, `exp`, `plan`.
- **`issue_refresh_token() -> str`** — opaque `secrets.token_urlsafe(48)`. NOT a JWT — bearer secret only, validated by Valkey allowlist lookup.
- **`refresh_allowlist_key(token) -> str`** — `f"cache:refresh:{hmac_sha256_hex(token, settings.REFRESH_TOKEN_PEPPER)}"`. **HMAC-with-pepper** per coordinator counter-proposal vs FE memo (FE-D5 wanted plain sha256; coordinator strengthened to HMAC so a Valkey-only breach cannot let an attacker validate cookies without also exfiltrating the pepper from Secret Manager).
- **`compare_tokens(a, b)`** — thin wrapper around `secrets.compare_digest`. Constant-time comparison (timing-attack mitigation on refresh-token validation).
- **`REFRESH_ROTATE_LUA`** script + **`rotate_refresh_token(valkey, old_key, new_key, new_value, ttl_seconds) -> bool`** — Lua atomic check-DEL-SET via EVALSHA→EVAL fallback. Module-level `_refresh_rotate_sha` cached on first call (via `shared.valkey.load_lua_script` + `eval_lua_script`). Per §4.B counter-proposal: **Lua over MULTI/EXEC** because Lua executes server-side atomically with no race window between the existence check and the rotation. Returns `True` if old key existed and was rotated; `False` if old key absent (a `False` return is the canonical replay-attack signal — `routers/auth.py` should treat it as a 401 + alarm).
- **`AuthContextMiddleware(BaseHTTPMiddleware)`** — **position 3 in the chain** (after RequestID + ErrorHandler, before RateLimit). **FAIL-OPEN** — missing/malformed/expired tokens leave `request.state.user = None`. No 401 raised at the middleware layer; raising 401 is `get_current_user`'s job per §4.G separation of concerns. Decodes JWT, builds `CurrentUser` from payload, attaches to `request.state.user`. **Does NOT hit the DB** — keeps the middleware fast for unauthenticated routes; `get_current_user` performs the user-existence check only when a route actually requires auth.

### Decisions flagged
- **`oauth2_scheme.tokenUrl="/api/v1/auth/otp/verify"`** — chose the verify endpoint (where the JWT is actually issued) so the OpenAPI Authorize button points users at the right place for getting a token.
- **Malformed-vs-missing token both raise `TokenMissingError`** (401 / `auth.token_missing`); **expired alone → `TokenExpiredError`** (401 / `auth.token_expired`). Aligns with §4.B which states "missing/malformed → `token_missing`", "expired → `token_expired`".
- **`MeesellError.__init__(code, status_code, validation_message_id, detail)`** signature — auth-exception subclasses pass `detail=` as a keyword argument so they do NOT accidentally overwrite the class-level `code = "auth.token_missing"` etc. Lesson learned during testing: positional arg to `super().__init__` shadows the class attribute.
- **`_reset_lua_cache_for_tests()`** helper — underscored so the rotation-test fixture can clear the module-level Lua SHA between tests. Needed because the EVALSHA→EVAL fallback path can only be exercised after a real `SCRIPT FLUSH` on the Valkey server, and the cached SHA would otherwise short-circuit the fallback.

### Tests + results
- **Unit tests (no Valkey)**: `test_core_auth.py` (9) + `test_core_auth_middleware.py` (5) → **14/14 PASS**.
- **Rotation tests** (live Valkey at `redis://127.0.0.1:6379/15` for the test client; `app.shared.valkey` factories monkeypatched by services-builder's `use_live_valkey` fixture per the cross-test-pollution fix that landed after my dispatch) → **4/4 PASS** when 6379 reachable; 3 skip cleanly when only the DB-0 tunnel port is bound.
- **Baseline regression**: 49/49 PASS (`test_app_boot_integration.py` + `test_database.py`).
- **Master full sweep**: **103 PASS / 3 SKIP / 0 FAIL** in 227 s.

### Hand-offs queued for §7 iam (next dispatch — first domain module)
- `core/auth.py:get_current_user` is **THE** authenticated-user dep for every authenticated route. All `routers/*.py` must inject it via `Depends(get_current_user)`.
- `core/auth.py:issue_access_token` + `issue_refresh_token` + `refresh_allowlist_key` + `rotate_refresh_token` are consumed by `app/routers/auth.py` during §7 rewrite.
- **Legacy `backend/app/middleware/auth.py` MUST be deleted during §7 dispatch.** It currently coexists; the legacy `app/routers/auth.py` still imports `create_token` + `get_current_user` from it. Cannot delete until §7 rewrites the router.
- **Legacy `tests/test_middleware_{auth,plan_guard,rate_limit}.py` MUST be deleted in lock-step** with the legacy middleware files.
- **`JWT_EXPIRY_DAYS` config field is DEPRECATED** per FE-D5; removed during §7 dispatch and replaced with `ACCESS_TOKEN_TTL_SECONDS`. Currently both live in `shared/config.py` so legacy paths continue working until §7.
- **`refresh-token-pepper` Secret Manager value** populated by infra-builder during §7 dispatch.
- **`razorpay-webhook-secret` Secret Manager value** populated by infra-builder during §7 dispatch.

### Cross-agent memory references
- `meesell-services-builder/MEMORY.md` — owns `app/shared/valkey.py` factory + `use_live_valkey` fixture + MSG91 HTTP call signature.
- `meesell-database-builder/MEMORY.md` — `users` table shape (phone E.164, `plan` enum currently `"free"` only).
- `meesell-infra-builder/MEMORY.md` — Secret Manager paths for `JWT_SECRET`, `REFRESH_TOKEN_PEPPER`, `MSG91_AUTH_KEY`.
