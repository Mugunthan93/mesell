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

---

## §7 iam CONSTRUCTED (2026-06-06)

### Scope
Full §7 iam module per BACKEND_ARCHITECTURE.md §7.A–§7.L (LOCKED 2026-06-05).  Solo dispatch.

### Files created (8 source + 4 unit + 3 integration + 2 helpers)
- `backend/app/modules/__init__.py` (new domain-modules root)
- `backend/app/modules/iam/__init__.py` (router re-export)
- `backend/app/modules/iam/exceptions.py` — 8 classes: `IamError` base + 7 leaves
  (`InvalidPhoneFormatError`, `InvalidOtpFormatError`, `MalformedWebhookPayloadError`,
  `OtpInvalidError`, `OtpAttemptsExceededError`, `RefreshInvalidError`,
  `WebhookSignatureInvalidError`, `Msg91UnavailableError`).
- `backend/app/modules/iam/domain.py` — 8 frozen dataclasses per §7.F
  (`OtpRecord`, `RefreshAllowlistEntry`, `SendOtpResult`, `VerifyOtpResult`,
  `RotateRefreshResult`, `RevokeResult`, `UserProfile`, `WebhookCaptureResult`).
- `backend/app/modules/iam/schemas.py` — 7 Pydantic v2 models per §7.E.
- `backend/app/modules/iam/repository.py` — 4 async methods per §7.D (private to module).
- `backend/app/modules/iam/service.py` — 6 async PUBLIC methods per §7.C.
- `backend/app/modules/iam/router.py` — 6 endpoint handlers per §7.B.
- `backend/tests/modules/iam/test_iam_refresh_allowlist_write.py` (§7.J unit 1).
- `backend/tests/modules/iam/test_iam_refresh_validation.py` (§7.J unit 2 — 4 cases).
- `backend/tests/modules/iam/test_iam_logout_idempotency.py` (§7.J unit 3 — 2 cases).
- `backend/tests/modules/iam/test_iam_constant_time_compare.py` (§7.J unit 4 — AST regression guard).
- `backend/tests/integration/conftest.py` — `iam_client` fixture + phone-prefix cleanup helper.
- `backend/tests/integration/_cookie_helpers.py` — `extract_refresh_cookie` (httpx drops `.mesell.xyz` cookies).
- `backend/tests/integration/test_iam_silent_refresh_flow.py` (§7.J integ 1).
- `backend/tests/integration/test_iam_logout_revocation.py` (§7.J integ 2).
- `backend/tests/integration/test_iam_replay_attack.py` (§7.J integ 3).

### Files modified
- `backend/app/main.py` — swap `from app.routers import auth as auth_router` → `from app.modules.iam import iam_router`; mount `iam_router`.
- `backend/app/shared/config.py` — DROP `JWT_EXPIRY_DAYS` field per FE-D5 amendment (§4.B).
- `backend/tests/conftest.py` — add `app.modules.iam.router` to `use_live_valkey` consumer-patch list; rewrite `auth_client` fixture against FE-D5 contract (6-digit OTP + `access_token` + `/me` for user_id).
- `backend/tests/test_app_boot_integration.py` — bump expected route count 8 → 11; add 4 new allowed paths.
- `backend/tests/test_shared_config.py` — invert `JWT_EXPIRY_DAYS` assertion (now asserts removal).
- `backend/tests/test_integration_third_party.py` — drop legacy MSG91/OTPService section (covered by `tests/test_msg91_adapter.py` + new iam tests).

### Files DELETED (legacy supersede)
- `backend/app/routers/auth.py`
- `backend/app/services/otp_service.py`
- `backend/app/schemas/auth.py`
- `backend/app/middleware/{auth,rate_limit,plan_guard}.py`
- `backend/tests/{test_auth,test_otp_service,test_middleware_auth,test_middleware_plan_guard,test_middleware_rate_limit}.py`

### Locked invariants implemented (per §7.B–§7.G)
- 6 endpoints mounted: `POST /api/v1/auth/{otp/send,otp/verify,refresh,logout}`,
  `GET /api/v1/auth/me`, `POST /api/v1/webhooks/razorpay`.  Boot-smoke route count = **11** (4 FastAPI builtins + 6 iam + 1 health).
- Access JWT shape `{sub, exp, plan}` HS256 — consumed from `core/auth.issue_access_token`; no `refresh_token` claim.
- Refresh token: opaque `secrets.token_urlsafe(48)`; HttpOnly + Secure + SameSite=Strict cookie; `Path=/api/v1/auth`; `Domain=.mesell.xyz`.
- Refresh allowlist keyspace: `cache:refresh:{hmac_sha256(token, REFRESH_TOKEN_PEPPER)}` — HMAC-with-pepper per §4.B FE-D5 amendment.
- Rotation: server-side Lua script via EVALSHA → EVAL fallback (consumed from `core/auth.rotate_refresh_token`).  No MULTI/EXEC.
- `secrets.compare_digest` for all token comparisons.  AST guard `test_iam_constant_time_compare.py` regression-locks both `app/modules/iam/service.py` and `app/core/auth.py`.
- 6-digit OTP, SHA-256 hashed at rest in Valkey DB 0 under `otp:{phone}` (TTL 300 s); 3-strikes lockout → `OtpAttemptsExceededError` + key DEL.
- Single-use OTP — `DEL otp:{phone}` after successful verify.
- Rate-limit decorators applied: `otp_send` 3/3600, `otp_verify` 10/3600, `auth_refresh` 60/3600.  `/me` + `/webhooks/razorpay` per-IP fallback only.  `/logout` no decorator.
- Direct-ORM audit writes via **SAVEPOINT** on the route's `db` session for `auth.login.success`, `auth.token.refreshed`, `auth.token.refresh_failed`, `auth.logout` — drop-on-failure preserved.  CRITICAL: previously used `AsyncSessionLocal()` (separate session) which FK-failed against the in-flight user upsert; SAVEPOINT pattern fixes this AND keeps audit failures from poisoning the business txn.

### Decisions flagged (deviations from §7 prose — master notified pre-construction)

**D1 — DPDP capture is a no-op.**  `users` table has no `dpdp_consented_at` column (absent from `shared/models/user.py`, `MVP_ARCH §2.1`, and every Alembic migration).  The §7.D `upsert_user_on_login(capture_dpdp: bool)` signature is preserved but the column-write is logged + skipped.  Resolution: `meesell-database-builder` adds the column in a V1.5 migration, OR scope-reduce DPDP capture to V1.5.  Logged via `INFO ... dpdp_consent.skipped_no_column ...`.

**D2 — Rate-limit decorator does not support `key="phone"`.**  §7.B prose specifies per-phone (otp_send/verify) and per-refresh-cookie-user-id (refresh) keying.  Wave 1 decorator `rate_limit(scope, limit: int, window: int)` only supports per-user-or-per-IP via FastAPI middleware introspection.  Effective semantics: anonymous routes (otp_send/verify/refresh) are per-IP, NOT per-phone.  Per-phone keying is a §V1.5 enhancement to the decorator API; tracked.

**D3 — 3-segment validation_message_id form.**  §7.G prose uses 2-segment IDs (`auth.otp_invalid`); `i18n/messages_en.py` registry + §5A.H CI regex (`^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){2}$`) require 3 segments.  IamError subclasses use the registry's 3-segment form (`auth.otp.invalid` etc.).  `core/auth.py`'s own exceptions still use 2-segment — separate §4 hygiene, flagged not fixed.

**D4 — Razorpay webhook audit row is a LOG, not an INSERT.**  `audit_events.user_id` is NOT NULL per §11.2 DDL; the webhook has no user_id.  V1 path: signature-verify + JSON-parse + LOG via service logger; return 200.  No audit row written.  §V1.5 resolution: either NULL-allow on `audit_events.user_id` or a separate `webhook_events` table.  `capture_razorpay_webhook` returns `WebhookCaptureResult(audit_event_id=0)` as the placeholder.

**D5 — Integration tests bypass `db_engine` rebuild.**  Conftest's `client` fixture rebuilds the full schema via `Base.metadata.create_all`, which requires the `pg_trgm` extension (live on the K3s dev tunnel Postgres at 5433; absent on the bare dev Postgres at 5432).  Integration tests use a dedicated `iam_client` fixture against `settings.DATABASE_URL` (no rebuild) with audit_events + users phone-prefix cleanup in teardown.  Phone-prefix convention: `+9155500XXXXX`.

### Tests + results
- **iam unit (10)**: `test_iam_constant_time_compare.py` (3 cases) + `test_iam_logout_idempotency.py` (2) + `test_iam_refresh_allowlist_write.py` (1) + `test_iam_refresh_validation.py` (4) → **10/10 PASS** in 11.5 s.
- **iam integration (3)**: silent_refresh, logout_revocation, replay_attack → **3/3 PASS** in 28.7 s.
- **Boot smoke**: `test_app_boot_integration.py` 7/7 PASS — route count = 11 confirmed.
- **Baseline regression** (378 tests): **378 PASS / 9 FAIL** — all 9 failures pre-existing (5 in `test_config.py` referencing the deleted `app/config.py`, 4 in `test_worker_db_isolation.py` referencing the deleted `generation_tasks`).  NONE caused by §7.
- **Ruff**: clean on all touched files.

### Hand-offs queued for next dispatch (§8 customer)
- `core/auth.get_current_user` is the canonical authenticated-user dep — all `modules/*/router.py` consume it via `Depends`.
- `app/modules/iam/service.{verify_otp_and_issue_tokens, rotate_refresh_token, revoke_refresh_token, get_profile, capture_razorpay_webhook, send_otp_for_login}` — locked PUBLIC surface; `iam` is leaf per §2.D so NO module calls these except via `core/auth`.
- `iam_client` integration test fixture pattern in `tests/integration/conftest.py` is reusable for §8–§14 module integration tests.
- `extract_refresh_cookie` helper in `tests/integration/_cookie_helpers.py` is reusable for any test asserting on the FE-D5 cookie surface.
- `_write_audit_direct(db=..., ...)` SAVEPOINT pattern in `app/modules/iam/service.py` — the canonical recipe for any service-level direct-ORM audit write that needs the route session's in-flight FK visibility.
- DEPRECATED `JWT_EXPIRY_DAYS` is gone — any cross-module code that still references it fails fast at import; `test_shared_config.py::test_jwt_expiry_days_field_removed_by_iam_dispatch` regression-locks the removal.

### Pending secrets (Secret Manager — populate at §20 deployment)
- `refresh-token-pepper` — used in dev with `test-pepper-do-not-use`; production-grade pepper required before staging deploy.
- `razorpay-webhook-secret` — used in dev with `test-webhook-secret`; real Razorpay test-mode secret required before any webhook receive.

### Latents documented (not §7-scope; for future dispatches)
- L_iam_1: `auth.token_missing` / `auth.token_expired` / `auth.user_not_found` in `core/auth.py` use 2-segment IDs; messages_en.py has 3-segment.  Resolver falls back to `exc.detail` (still human-readable) but the i18n payload is wrong.  §4 cleanup.
- L_iam_2: 9 baseline test failures (`test_config.py` × 5, `test_worker_db_isolation.py` × 4) reference deleted legacy modules.  §5 / §G3 cleanup ownership.
- L_iam_3: `tests/test_otp_service.py` was deleted; reaffirms `tests/test_msg91_adapter.py` as the canonical MSG91 transport test.
