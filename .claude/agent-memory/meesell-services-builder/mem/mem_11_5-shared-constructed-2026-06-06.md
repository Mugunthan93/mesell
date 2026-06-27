## §5 shared CONSTRUCTED (2026-06-06)

### Scope
Joint dispatch with `meesell-database-builder` against `BACKEND_ARCHITECTURE.md` §5 (`shared/` Foundation Layer).

### What I did (services-builder side — §5.B / §5.C / §5.D)

#### shared/database.py (§5.B)
- `engine` configured per locked verbatim signature: `pool_size=settings.DB_POOL_SIZE`, `max_overflow=settings.DB_MAX_OVERFLOW`, `pool_pre_ping=True`, `pool_recycle=settings.DB_POOL_RECYCLE` (default 1800s), `echo=settings.DB_ECHO`.
- `AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)` — `expire_on_commit=False` locked.
- `get_db()` FastAPI dependency with commit-on-yield + rollback-on-exception + always-close. Verified by 2 test cases that patch AsyncSessionLocal and assert commit/rollback/close call ordering.
- `make_worker_session()` peer helper — NullPool engine constructed per call + disposed on exit. Verified by 2 tests (NullPool type check + live worker query).
- `Base = DeclarativeBase` defined here; re-exported by `shared/models/base.py`.

#### shared/valkey.py (§5.C)
- 4 factories: `get_valkey_otp()` (DB 0), `get_valkey_broker()` (DB 1), `get_valkey_results()` (DB 2), `get_valkey_cache()` (DB 3).
- `redis.asyncio` library (Valkey 8 protocol-compatible).
- Lazy module-level singletons — `_otp_client`, `_broker_client`, `_results_client`, `_cache_client`. One `from_url(...)` per factory per process; reused across calls. Verified by 4 parametrised tests + same-instance reuse test.
- DB selection is structural — `_build_url_for_db(base, db)` rewrites the URL's `path` component to `/{db}` so the URL the client sees IS the verification.
- Lua script helpers: `load_lua_script(client, source) -> sha1_digest` (single SCRIPT LOAD at startup) + `eval_lua_script(client, digest, source, keys, args)` — prefers EVALSHA, falls back to EVAL on `NoScriptError`. Verified by happy-path + NOSCRIPT-fallback tests.
- `aclose_all()` shutdown helper — closes only-initialised clients; safe when some/all are None.

#### shared/config.py (§5.D)
- 11 grouped env-var tables present per §5.D inline registry: Database (5), Valkey (1), JWT/Auth (6 — including FE-D5 fields ACCESS_TOKEN_TTL_SECONDS/REFRESH_TOKEN_TTL_SECONDS/REFRESH_TOKEN_PEPPER + DEPRECATED JWT_EXPIRY_DAYS), MSG91 (2), Razorpay (3), Gemini (2), GCS (3), LangFuse (3), AI Ops (2), Cache (1 CACHE_VERSION="v1"), Audit (1 AUDIT_PII_SALT), Rate limits (1), CORS (2 — CORS_ALLOWED_ORIGINS Annotated[list[str], NoDecode], CORS_ALLOW_CREDENTIALS=True), App (1 APP_ENV Literal["development","staging","production"]).
- `model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")`.
- `_parse_cors_origins` field validator (mode="before") accepts comma-separated string OR JSON array OR list — using `NoDecode` annotation so pydantic-settings does NOT pre-decode the env value as JSON.
- `_forbid_cors_wildcard` model validator — SystemExits if `"*" in CORS_ALLOWED_ORIGINS` per §4.G amendment.
- `_require_non_empty` model validator (mode="after") — SystemExits if any `REQUIRED_FIELDS` entry is empty/unset, with the offending field name in the error message. 17 required fields total.
- Module-level singleton `settings = _load_settings()` — `_load_settings` wraps construction so pydantic ValidationError → SystemExit.

### Decisions made (FLAGGED — not in locked architecture)

1. **pydantic-settings upgrade 2.4.0 → ≥2.5.** Reason: `NoDecode` annotation only available in 2.5+. Required to accept comma-separated env strings for `list[str]` fields without breaking pydantic's pre-validator JSON decode. `requirements.txt` updated to `pydantic-settings>=2.5,<3`. **MASTER REVIEW NEEDED** if this conflicts with infra-builder's pinned dependency set.

2. **`.env` populated with dev placeholders for 5 newly-required fields** (`REFRESH_TOKEN_PEPPER`, `RAZORPAY_WEBHOOK_SECRET`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`, `AUDIT_PII_SALT`). Real Secret Manager values are populated by infra-builder during §7 iam dispatch (per STATUS_BACKEND L2 latent). Dev `.env` placeholders carry `dev-…-replace-in-prod` suffix to make the audit trail obvious.

3. **`.env.example` rewritten** to document the V1 contract per §5.D — every required + optional field present, grouped to match the 11 §5.D tables.

4. **`CORS_ORIGINS` env var renamed to `CORS_ALLOWED_ORIGINS`** (was the legacy `app/config.py` field name; §5.D locks the new name). Comma-separated parsing preserved. `app/main.py` updated to read `settings.CORS_ALLOWED_ORIGINS` + `settings.CORS_ALLOW_CREDENTIALS`.

5. **`app/middleware/auth.py` unused-import cleanup** (`from sqlalchemy import select` removed; ruff F401). Pre-existing tech debt — fixed because ruff acceptance gate required it.

### Tests added
- `tests/test_shared_database.py` — 8 cases: Base inheritance, engine pool config, expire_on_commit=False, get_db yield/commit/rollback/close lifecycle, make_worker_session NullPool + live query.
- `tests/test_shared_valkey.py` — 8 cases: 4 DB-pinned factories parametrised, lazy singleton, distinct-client isolation, Lua SCRIPT LOAD, EVALSHA happy path, EVAL fallback on NOSCRIPT, aclose_all tolerance for uninitialised clients.
- `tests/test_shared_config.py` — 30 cases: REQUIRED_FIELDS registry match (17 fields), every Settings field declared, JWT_EXPIRY_DAYS deprecation, FE-D5 default locks, CACHE_VERSION default, full-env happy path, 17 parametrised SystemExit-on-empty cases, CORS wildcard rejection, comma-separated CORS parse, JSON-array CORS parse, module singleton smoke, canonical 13-model import path.

Total new tests: **46**. Combined with the 49 baseline tests → **95/95 PASS** against live dev Postgres.

### Hand-offs queued
- §4 `core/` (next Wave 1) — consumes `shared/database.py:get_db`, `shared/database.py:make_worker_session`, `shared/valkey.py:get_valkey_otp`/`get_valkey_cache`, `shared/config.py:settings`.
- §6A `ai_ops/client.py` — consumes `shared/config.py:settings` for `GEMINI_API_KEY`, `LANGFUSE_*`, `AI_DAILY_BUDGET_INR`, `AI_BUDGET_ALARM_THRESHOLD`.
- §15.H + §7 `iam` — consumes `shared/valkey.py:load_lua_script` + `eval_lua_script` for the refresh-token allowlist Lua (script body lives in `core/auth.py` per §4.B FE-D5 amendment).
- `meesell-infra-builder` — populates 3 deferred Secret Manager values during §7 iam dispatch (`refresh-token-pepper`, `razorpay-webhook-secret`) and §6A ai_ops dispatch (`langfuse-secret-key`).

---
