# Memory — meesell-services-builder

## Agent Identity
Business-logic specialist for MeeSell. Owns service layer (ai_engine call site, image_processor, quality_engine, pricing_engine, export_service, otp_service MSG91 portion, storage) + Celery workers. Decentralized memory ecosystem.

---

## D4 §20.5 CI YAML CONSTRUCTED (2026-06-09, .gitlab-ci.yml)

### Scope
Micro-dispatch `meesell-services-builder` solo. D4 founder-approved Option A: produce `.gitlab-ci.yml` ONLY (the previously-missing CI YAML §20 sub-session never produced). Zero `backend/app/` changes; zero architecture-doc edits (§5.0). On branch `claude/meesell-project-setup-Tl7DS`, no commit (master handles git).

### What I did
Created `/Users/mugunthansrinivasan/Project/mesell/.gitlab-ci.yml` (283 LOC). 6 stages sequential per §19.G, gated via `needs:` chain (unit→smoke→lint→integration→golden_roundtrip):
- **unit** `cd backend && pytest -m "unit"` — dummy env, no services.
- **smoke** `cd backend && pytest -m "smoke"` — boot+schema, `needs:[unit]`.
- **lint** (§16.E HARD RULE, separate build-failing stage, `needs:[smoke]`) — 4 commands, ALL from `backend/`: `lint-imports --config tests/lint/import_rules.toml` (Contracts 1-7) + `python tests/lint/check_scope_to_user.py` (8) + `python tests/lint/check_no_meesho_symbols_outside_export.py` (9) + `python tests/lint/check_message_id_regex.py` (10).
- **integration** `cd backend && pytest -m "integration"` `needs:[lint]` — services `postgres:16` (alias postgres) + `valkey/valkey:8` (alias valkey); `DATABASE_URL=postgresql+asyncpg://meesell:meesell@postgres:5432/meesell_test`, `VALKEY_URL=redis://valkey:6379`.
- **golden_roundtrip** `pytest -m "golden_roundtrip"` `needs:[integration]` — same services.
- **nightly** schedule-only — 2 jobs both `needs:[golden_roundtrip]`: `nightly_slow_perf` (`pytest -m "slow or perf"`, `PYTEST_RUN_SLOW=1`) + `nightly_ai_eval` (`pytest -m "ai_eval"`, `RUN_AI_EVAL=1`, `GEMINI_API_KEY=$GEMINI_API_KEY`).

### Locked patterns / decisions (reusable)
- **Schedule gating idiom:** stages 1-5 use `rules: [{if: schedule → never}, {when: on_success}]`; nightly uses `rules: [{if: schedule → on_success}, {when: never}]`. This keeps MR pipelines off nightly AND keeps nightly from re-running PR-only gates. `$CI_PIPELINE_SOURCE == "schedule"` is the discriminator.
- **All pytest + lint run from `backend/`** via `cd backend && ...` — pytest.ini, import_rules.toml, and the 3 AST scanners all resolve paths relative to backend/.
- **lint-imports invocation is `--config tests/lint/import_rules.toml`** — the TOML uses `[tool.importlinter]` namespace (§19 D-flag); `import-linter>=2.0,<3` already in requirements.txt.
- **base image `python:3.12-slim`**; pip cache `.cache/pip` keyed on `backend/requirements.txt` files-hash so a lock change busts it.
- **YAML anchors:** `.install_deps` (`before_script: pip install -r backend/requirements.txt`) + `.dummy_env` (CI-safe placeholder SECRET_KEY/MSG91_*/REFRESH_TOKEN_PEPPER/RAZORPAY_WEBHOOK_SECRET) merged into jobs via `<<: *anchor`. Real values via `$VAR` CI/CD variables on integration+. NO hard-coded secrets.
- **Dummy-env jobs (unit/smoke/lint)** need no Postgres/Valkey — app Pydantic Settings only require values present/well-formed to import modules.
- Verified: `python3 -c "import yaml; yaml.safe_load(...)"` → YAML VALID + structural asserts (6 stages, anchor merges, needs chain, services, 4 lint commands, schedule gating) all pass.

### Hand-off
- **meesell-infra-builder**: register GitLab nightly schedule (Settings→CI/CD→Pipeline schedules, e.g. cron `0 18 * * *`) so nightly jobs fire; populate 5 protected/masked CI/CD variables (`SECRET_KEY`, `MSG91_API_KEY`/`MSG91_SENDER_ID`/`MSG91_ROUTE`, `REFRESH_TOKEN_PEPPER`, `RAZORPAY_WEBHOOK_SECRET`, `GEMINI_API_KEY`). L2 Secret Manager names align.
- D4 escalation CLOSED.

---

## §19 CI gates CONSTRUCTED (2026-06-08, Wave 7 step 2)

### Scope
Sub-session `meesell-backend-construction-19-tests-1`. Solo dispatch acting as both meesell-services-builder (primary — AST scanners + perf tests + pytest fixtures + CI integration) AND meesell-database-builder (per-test transaction `db` fixture posture review + multi-tenant isolation regression). Wave 7 step 2 per founder's sequential plan.

### What I did
- **7 import-linter contracts** (`backend/tests/lint/import_rules.toml`, 1247 LOC): expressed §16.E's 7 logical contracts as **27 per-source sub-contracts** because import-linter v2's `forbidden` contract structurally rejects pairs that share descendants (e.g. `source=app.modules.iam` + `forbidden=app.modules.iam.repository`). Per-source expansion: Contract 1 → 8 sub-contracts (one per domain module excluding own repository); Contract 4 → 8 (own schemas); Contract 7 → 8 (own router + tasks); Contracts 2, 3, 5 stay single. Intra-module self-import allowlist (`__init__.py` router re-exports + intra-module router→service / service→repository / service→tasks / service→schemas chains) added via `ignore_imports` + `unmatched_ignore_imports_alerting = "none"` so cross-module enforcement stays sharp while legitimate intra-module loads pass. Final result: **27 kept / 0 broken** against live codebase.

- **Contract 8 — `scope_to_user` AST scanner** (`tests/lint/check_scope_to_user.py`, 244 LOC): walks every public method in `app/modules/{customer,catalog,image,pricing,export}/repository.py` and asserts `user_id` is in the signature. Allowlist via `SCANNED_MODULES` constant (excludes `iam` (users IS the principal per §15.B special-case), `category` (global tables per §16.F.2), `dashboard` (no repository per §16.F.1)). `KNOWN_DEVIATIONS` frozenset documents `app.modules.pricing.repository.insert_calc` as the one pre-existing exception (tenancy upstream via `catalog.assert_product_ownership` per the function's own docstring).

- **Contract 9 — M10 forbidden-symbol AST scanner** (`tests/lint/check_no_meesho_symbols_outside_export.py`, 242 LOC): walks `app/**/*.py` (excluding `app/modules/export/**` + `app/adapters/gcs.py` per §14.J + §15.F) checking 4 AST node kinds — `ast.Name`, `ast.Attribute`, `ast.keyword`, `ast.arg` — for the 3 forbidden symbols (`meesho_column_header` / `meesho_column_index` / `enum_codes_map`). Docstring string literals NOT walked per L_export_M10_AST_scanner spec line. `KNOWN_DOCSTRING_HITS` frozenset documents 6 pre-existing string-literal mentions (3 in `app/shared/models/template.py` JSON-shape docstring + 3 in `app/modules/export/{schemas,__init__}.py` docstrings) for forward-compat documentation.

- **Contract 10 — i18n message_id regex scanner** (`tests/lint/check_message_id_regex.py`, 152 LOC): loads `app.i18n.messages_en.VALIDATION_MESSAGES` at runtime and asserts every key matches §5A.H regex `^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$`. Reports 55 keys all PASS against current registry. The existing `tests/test_messages_en_id_regex.py` continues to provide belt-and-braces parametrised coverage.

- **4 pytest wrappers** (`tests/lint/test_*.py`, 73-171 LOC each): `test_import_contracts.py` runs `lint-imports` via subprocess with venv-binary auto-discovery (resolves `lint-imports` via `shutil.which` then `sys.prefix/{bin,Scripts}/lint-imports`); the other 3 wrappers invoke their scanners in-process and include counter-example tests (synthetic temp directories with a violating `repository.py` / `service.py`).

- **6 §19.D pytest fixtures** appended to `backend/tests/conftest.py` (existing 343 LOC → 621 LOC): `valkey` (real per-test connection to all 4 logical DBs (0/1/2/3) via dev tunnel, FLUSHDB on teardown, returns `dict[name, Redis]`), `mock_ai_ops_client` (AsyncMock for `call_gemini` patched on source + 4 consumers), `mock_msg91_adapter` (AsyncMock for `send_otp` patched on source + iam consumers), `mock_gcs_adapter` (in-memory `dict[str, bytes]` backing the 4 GCS async surfaces, patched on source + 4 image/export consumers), `mock_razorpay_adapter` (MagicMock for `verify_webhook_signature`). The pre-existing `db` fixture already implements the §19.D per-test transaction + ROLLBACK pattern — preserved unchanged.

- **4 performance test files** (`tests/perf/`, 74-152 LOC each + 152 LOC conftest with `assert_p95_within_budget` / `assert_value_within_budget` helpers): `test_category_schema_p95.py` (cache hit ≤ 50 ms / miss ≤ 200 ms), `test_category_browse_p95.py` (≤ 200 ms), `test_export_pipeline.py` (≤ 30 s), `test_ai_cost_average.py` (≤ ₹0.05 over 7-day audit_events rolling window). All marked `@pytest.mark.slow + @pytest.mark.perf`. **Suite-wide skip via `pytest_collection_modifyitems` hook** in `tests/perf/conftest.py` — gates BEFORE fixture instantiation (the `db` fixture connects at fixture setup), so fast-lane PR runs skip the suite cleanly without DB-connect errors.

- **Multi-tenant isolation regression** (`tests/integration/test_multi_tenant_isolation.py`, 278 LOC): 4 attack vectors per §19.H + §15.B as separate test methods inside `TestMultiTenantIsolation`. Direct ORM INSERT to build User A / User B (bypassing OTP per §19.D fixture posture); `app.core.auth.issue_access_token` mints the User B JWT; the 4 vectors exercise GET preview / list / PATCH autosave / POST image-upload as User B against User A's product. Asserts 404 (preferred) or 403 (acceptable) — both are no-leak outcomes per §15.B 3-layer defense.

- **`backend/pytest.ini` markers** + addopts per §19.D: 7 markers registered (`unit`, `integration`, `golden_roundtrip`, `ai_eval`, `slow`, `smoke`, `perf`); `--strict-markers --strict-config -ra` added. `asyncio_default_fixture_loop_scope = session` preserved (load-bearing for the `dev_engine` pattern). `testpaths = tests` preserved.

- **`backend/requirements.txt`** appended `import-linter>=2.0,<3`.

### Decisions made (FLAGGED — for master review at hand-off)

1. **TOML namespace fork from §16.E sketch.** §16.E uses bare `[importlinter]` for clarity; the runtime import-linter package requires `[tool.importlinter]` (per `importlinter.adapters.user_options.TomlFileUserOptionReader` line 90). Implementation uses runtime-required namespace; semantic count of "7 import-linter contracts" preserved via per-source expansion. **No architecture-doc edit per §5.0 — documented inline in the TOML header comment.**

2. **Per-source expansion of Contracts 1, 4, 7.** import-linter v2's `forbidden` contract rejects source/forbidden pairs that share descendants. Expanded as: Contract 1 → 8 sub-contracts (one per source module); Contract 4 → 8; Contract 7 → 8. **Semantic count remains "7 logical contracts" per §19.C.** Documented inline. Suggest §19.C amendment NOTE for future readers ("Contracts 1/4/7 implemented as N=8 per-source sub-contracts each — see import_rules.toml header").

3. **`KNOWN_DEVIATIONS` allowlist for Contract 8.** `pricing.repository.insert_calc` lacks `user_id` because the `pricing_calcs` table FKs on `product_id`, and the tenancy gate is enforced upstream at `catalog.assert_product_ownership` per the function's own docstring (lines 8-11). Added to the scanner's allowlist with inline citation. **NO modification to §12 LOCKED CONSTRUCTED code per §5.0 + §18-precedent ("don't touch other sub-sessions' LOCKED code unless necessary").** Suggest V1.5 ticket: widen `insert_calc` signature to accept `user_id: UUID` for defence-in-depth.

4. **L_iam_1 NOT addressed in §19.** The latent says `core/auth.py` raises 2-segment IDs (e.g. `auth.token_missing`) but i18n + §5A.H regex require 3-segment. Contract 10 scans `app.i18n.messages_en.VALIDATION_MESSAGES` keys (all 55 PASS), NOT the runtime ID strings raised by exceptions. The 2-segment exception IDs WILL produce missing-key resolver fallbacks at runtime per §5A.I (which logs WARNING and returns the verbatim ID — a degraded UX but not a crash). **Out of §19 scope per the construction prompt's "DO NOT amend per-module test plans" rule + §5.0.** Already in latent backlog as L_iam_1.

5. **L_iam_2 V0-rot cleanup PARTIAL.** `tests/test_config.py` (5 failures) + `tests/test_worker_db_isolation.py` (3 V0-rot failures referencing `app.database`, `async_session_maker`, `app.services.image_processor`) NOT remediated in this sub-session — tunnel was down for the duration so failure causes can't be confirmed. **Recommend §20 sub-session pick up V0-rot cleanup once §20 deployment dispatch goes out.**

6. **Tunnel down during sub-session.** `nc -zv localhost 5433` returned `Connection refused` throughout the session — autossh process exists (PID 82990 → `gcp-nexus` alias) but the forwarding was not active. Boot smoke (`test_app_boot_integration`) + schema smoke (`test_database`) + new multi-tenant regression COULD NOT be exercised. Lint suite (18 PASS), perf suite (5 skip), 92 non-DB tests verified. **Master must re-run boot+schema+multi-tenant after tunnel restoration to close §19 acceptance.**

### Tests added (in this sub-session)
- **18 pytest tests under `tests/lint/`**: 1 import-linter wrapper (2 sub-asserts) + 4 scope_to_user wrapper + 6 M10 forbidden-symbol wrapper + 6 message_id regex wrapper — ALL PASS in 0.31s.
- **5 perf tests under `tests/perf/`**: ALL SKIP cleanly per `PYTEST_RUN_SLOW=1` gate. `PYTEST_RUN_SLOW=1` invocation will exercise the 4 budgets — requires tunnel + V1.5 export-pipeline seed harness for the 30s budget test.
- **4 multi-tenant integration tests under `tests/integration/`**: collected cleanly; will exercise the 4 §15.B attack vectors once tunnel is restored.

### Acceptance status

| # | Criterion | Status |
|---|---|---|
| 1 | 7 import-linter contracts in `tests/lint/import_rules.toml` matching §16.E | ✅ 27 kept / 0 broken |
| 2 | 3 custom AST scanners (Contracts 8, 9, 10) + counter-example tests | ✅ all 3 scan PASS; counter-examples flag synthetic violations |
| 3 | 4 perf test files in `tests/perf/` with locked budgets per §19.E | ✅ 4 files, skip cleanly under PR gate |
| 4 | `tests/conftest.py` with 6 locked fixtures per §19.D | ✅ all 6 in place (`db` pre-existed, 5 new appended) |
| 5 | `pytest.ini` markers per §19.D + `perf` | ✅ 7 markers + addopts |
| 6 | `test_multi_tenant_isolation.py` 4 attack vectors | ✅ written, awaiting tunnel for run |
| 7 | All 10 CI contracts PASS against current codebase | ✅ Contracts 1-10 all PASS (Contracts 1-7: 27 sub-contracts kept; Contracts 8-10: scanners exit 0) |
| 8 | Coverage targets met (80% line / 100% branch on critical paths) | ⏸ DEFERRED — coverage harness requires tunnel for integration tests |
| 9 | ~88 test classes per §19.B inventory all PASS | ⏸ DEFERRED — DB-dependent tests cannot run without tunnel |
| 10 | Universal: ruff clean | ✅ (3 auto-fixed) |

### Hand-offs queued
- **§20 deployment sub-session**: pick up L_iam_2 V0-rot cleanup (5 `test_config.py` failures + 3 `test_worker_db_isolation.py` failures); wire the CI YAML to invoke the 4 `pytest -m` stages per §19.G; populate the 3 PENDING Secret Manager secrets (`refresh-token-pepper`, `razorpay-webhook-secret`, `langfuse-secret-key`).
- **meesell-infra-builder**: restore the dev tunnel (autossh) so master can verify §19 acceptance criteria #8 + #9.
- **V1.5 tickets queued** (D-flags for master ratification): (a) §19.C amendment NOTE on per-source expansion of Contracts 1/4/7; (b) widen `pricing.repository.insert_calc` signature to accept `user_id: UUID` (defence-in-depth); (c) L_iam_1 resolution — migrate `core/auth.py` exception IDs from 2-segment to 3-segment per §5A.H.

---

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

## Session: 2026-06-05 — Final Gap Purge (workers + leftover tests) COMPLETE

### Task summary
Coordinator gap-pass mini-task: api-routes-builder had purged 9 routers + 6 schemas + 4 services + 3 tests
but 2 worker files and 2 router-tests survived outside their boundary. My job: delete the dead remnants,
audit the rest of workers/ + tests/, then declare backend CONSTRUCTION-READY.

### Files DELETED (10 total)

Workers (3):
- backend/app/workers/generation_tasks.py — imported deleted app.models.sku.SKU
- backend/app/workers/image_tasks.py — imported deleted app.services.image_processor
- backend/app/workers/scrape_tasks.py — imported deleted app.services.meesho_scraper

Tests (7):
- backend/tests/test_routers_exports.py — tested deleted exports router
- backend/tests/test_routers_images.py — tested deleted images router
- backend/tests/test_scraper.py — imported deleted app.schemas.scrape + app.services.meesho_scraper
- backend/tests/test_image_processor.py — imported deleted app.services.image_processor
- backend/tests/test_catalog.py — used deleted /api/v1/catalogs + legacy /api/v1/auth/send-otp URLs
- backend/tests/test_schemas.py — imported deleted schemas (catalog, sku, pricing)
- backend/tests/test_pricing.py — imported pricing_engine (transitively broken) + hit deleted /api/v1/pricing/calculate

### Files MODIFIED (1)
- backend/app/workers/celery_app.py:
  - include=[] (was [image_tasks, generation_tasks, scrape_tasks])
  - added task_reject_on_worker_lost=True per services-builder ALWAYS rules
  - removed task_routes={images, generation, scraping} for deleted queues
  - kept core conf: task_serializer, task_track_started, task_acks_late, worker_prefetch_multiplier=1

### Workers KEPT: none
All 3 V0 worker task modules were dead. Only celery_app.py survives (modified). Construction phase will
re-populate include[] when image-precheck / export tasks land.

### Acceptance checks — all 5 evaluated
1. `from app.main import app; len(app.routes)` → 9 — PASS
2. `from app.workers.celery_app import celery_app` → imports clean, include=[] — PASS
3. `grep "from app.models.sku|from app.models.image|_load_owned_sku|_load_owned_catalog"` over backend/app + backend/tests → 0 matches — PASS
4. `pytest test_app_boot_integration test_database test_auth -v`:
   - test_app_boot_integration.py: 7/7 PASS
   - test_database.py: 40 errors + 6 fails — ALL Postgres `localhost:5433` connection refused (pre-existing infra gap, not regression)
   - test_auth.py: 4 errors — same Postgres connection issue
   No import errors, no collection errors, no URL regressions. PASS (infrastructure caveat).
5. `git status` shows 10 deletes + 1 modify within scope, full delta recorded in STATUS file. PASS.

### Residual blocker found (NOT this pass — for construction)
**backend/app/services/pricing_engine.py line 23**: `from app.schemas.pricing import PricingAlert`
The pricing.py schema was deleted by api-routes-builder. pricing_engine.py is therefore unimportable.
This was OUT of my purge scope (it is a "kept" service the prior agent declared clean, but it has a
transitive broken import on a deleted schema). Construction phase fix options:
- Option A: re-author backend/app/schemas/pricing.py with PricingAlert (V1 form).
- Option B: refactor pricing_engine to use a plain `@dataclass` or `TypedDict` for the alert.
Recommendation: Option A — schemas/pricing.py is going to be re-authored anyway for the V1 pricing router.

### V1 service inventory after this pass

| Service | State |
|---|---|
| backend/app/services/ai_engine.py | LIVE — clean imports (app.config, app.data) |
| backend/app/services/otp_service.py | LIVE — clean imports (httpx, redis, app.config) |
| backend/app/services/storage.py | LIVE — clean imports (app.config) |
| backend/app/services/pricing_engine.py | **BROKEN IMPORT** — needs app.schemas.pricing.PricingAlert |
| backend/app/services/image_processor.py | TO BUILD (construction) |
| backend/app/services/quality_engine.py | TO BUILD (construction) |
| backend/app/services/export_service.py | TO BUILD (construction) |
| backend/app/workers/celery_app.py | LIVE — modified, include=[] |
| backend/app/workers/image_tasks.py | TO BUILD (V1 image precheck) |
| backend/app/workers/generation_tasks.py | TO BUILD (V1 XLSX + ZIP export gen) |

### Cross-agent notes I picked up

From **meesell-database-builder MEMORY**:
- Head revision: `f31c75438e61` (parent `a1b2c3d4e5f6` → `935e55b4852c`)
- 13 V1 tables live; seed counts: field_aliases=67, templates=3566, categories=3772, field_enum_values=49259
- Already shipped: pg_trgm + 3 GIN trgm indexes on categories (path, leaf_name, super_name)
- Already shipped: idx_product_drafts_saved_at (B-tree)
- New `app/i18n/` package owns versioned constants for schema_jsonb shape (STEP_ASSIGNMENT, primitive_classifier).
  Services that produce schema_jsonb output MUST import from app.i18n.

From **meesell-api-routes-builder MEMORY**:
- Only auth router exists right now. App.routes has 9 (4 starlette builtins + 3 auth APIRoute + 1 health APIRoute + 1 Mount).
- Auth URL prefix locked: /api/v1/auth/{otp/send, otp/verify, me}.
- Python venv: backend/.venv/bin/python (3.11, not 3.12 as CLAUDE.md states).
- PYTHONPATH=/Users/mugunthansrinivasan/Project/mesell/backend required for pytest.

### Construction-phase next-steps prefix (for self next session)

1. **First fix on construction start**: backend/app/services/pricing_engine.py PricingAlert import.
   Either re-create schemas/pricing.py (likely api-routes-builder will when it ships POST /products/{id}/pricing)
   or refactor pricing_engine to dataclass. Coordinate with api-routes-builder.
2. **Worker task modules**: image_tasks.py + generation_tasks.py rewrite against V1 13-table schema.
   - image_tasks: process_image(product_image_id) — rembg + PIL + GCS + product_images.precheck_jsonb update.
   - generation_tasks: generate_export(export_id) — openpyxl XLSX + image ZIP per export row.
3. **Celery includes**: when worker modules land, update celery_app.py include=[] to register them.
   Pattern: include=["app.workers.image_tasks", "app.workers.generation_tasks"].
4. **task_routes**: add {images, generation} queues back to celery_app.py when tasks ship.
5. **GCS path scheme** (not yet locked): TBD but proposed `{bucket}/{user_id}/products/{product_id}/images/{order_idx}.jpg`
   for processed; `{bucket}/{user_id}/products/{product_id}/originals/{order_idx}.{ext}` for raw.
   Signed-URL TTL: 1h default per agent spec.

### Backend declared CONSTRUCTION-READY by this pass
Pending founder approval of the construction-phase dispatch plan. Coordinator review next.

---

---

## §4 core/ services slice CONSTRUCTED (2026-06-06)

### Scope
Joint dispatch with `meesell-auth-builder` against `BACKEND_ARCHITECTURE.md` §4 (`core/`).
Owned: errors, tenancy, cache, plan_guard + 6 middleware (request_id, tenancy_mw,
rate_limit_mw, plan_guard_mw, audit_mw) + `app/main.py` wiring.
Auth-builder owns `core/auth.py` + `core/middleware/auth_mw.py` — both were shipped
in time for me to wire `app/main.py`.

### Files created
- `backend/app/core/__init__.py` — package doc only.
- `backend/app/core/errors.py` (255 LOC) — `MeesellError` root + `register_error_handlers`
  registering 5 handlers (MeesellError, RequestValidationError, PydanticValidationError,
  HTTPException, Exception). Locked envelope `{detail, code, validation_message_id, request_id}`.
  Deferred-wire i18n resolver: `_resolve_message_id` tries `app.i18n.resolver` then falls back
  to `fallback or mid`.
- `backend/app/core/tenancy.py` (130 LOC) — `TenantViolationError`, `assert_owned`,
  `scope_to_user` using SQLAlchemy `query.column_descriptions[0]['entity']` reflection.
- `backend/app/core/cache.py` (160 LOC) — `get_or_set` (versioned `meesell:v{cv}:{key}`,
  single-flight via SET NX EX with 10s lock + 50ms poll up to 5s), `etag_for` (quoted SHA-256
  per RFC 7232), `prewarm_top_categories` (V1 no-op stub).
- `backend/app/core/plan_guard.py` (200 LOC) — `PlanLimitExceededError` (status 402),
  `V1_LIMITS_FREE` table, `enforce_plan_limit` with sliding-window (Valkey DB 0 sorted-set)
  + total-cap (SELECT COUNT(*) FROM products) branches.
- `backend/app/core/middleware/__init__.py` — package doc only.
- `backend/app/core/middleware/request_id.py` (60 LOC) — UUID gen + `X-Request-ID` echo.
- `backend/app/core/middleware/tenancy_mw.py` (35 LOC) — pure-copy `user.user_id` → `state.user_id`.
- `backend/app/core/middleware/rate_limit_mw.py` (230 LOC) — per-IP DDoS + per-route via
  `@rate_limit(scope, limit, window)` decorator attaching `__rate_limit__` tuple to the
  handler. Manual route resolution via `app.router.routes[r].matches(scope)` because
  `BaseHTTPMiddleware` runs BEFORE Starlette populates `request.scope["route"]`. Returns
  JSONResponse 429 inline (does NOT raise — see decision below). Fail-open with WARNING
  on `RedisError`/`ConnectionError`/`OSError`.
- `backend/app/core/middleware/plan_guard_mw.py` (30 LOC) — V1 no-op pass-through.
- `backend/app/core/middleware/audit_mw.py` (290 LOC) — post-2xx commit `audit_events`
  write via `AsyncSessionLocal()`. `@audit_event(event_type)` decorator; coalesce regex
  `/api/v1/products/{uuid}/(draft|autosave)` with Valkey DB 0 `SET NX EX 300` marker.
  PII scrubber hashes `phone` (SHA-256 + AUDIT_PII_SALT), strips `fssai_no`/`FSSAI_no`/
  `gst_no`/`GST_no`. Drop-on-failure: every exception caught + WARNING-logged.
- `backend/app/main.py` — re-authored to register 7 middleware deepest-first (Audit →
  PlanGuard → RateLimit → TenancyContext → AuthContext → RequestId → CORS) +
  `register_error_handlers(app)` + `prewarm_top_categories()` inside `lifespan` startup
  (try/except so startup never blocks on prewarm failure). Health endpoint preserved.

### Tests added (39 new, all PASS)
- `tests/test_core_errors.py` — 6 tests: envelope shape, MeesellError handler returns
  locked envelope, RequestValidationError → 422 with `validation.<field>.<constraint>`,
  HTTPException → `http.<status>`, generic Exception → `server.internal_error` with NO
  traceback leakage, deferred-wire fallback returns `mid` or `fallback`.
- `tests/test_core_tenancy.py` — 4 tests: assert_owned OK, mismatch → 403, None → 403,
  scope_to_user adds WHERE clause + unknown column raises ValueError.
- `tests/test_core_cache.py` — 5 tests: versioned key format, miss-then-hit dedupes,
  single-flight (10 concurrent → fetch called exactly 1), ETag quoted SHA-256, prewarm stub.
- `tests/test_core_plan_guard.py` — 9 tests: parametrised sliding-window over the 3 hourly
  resources, batched `requested` arg, recovery after key purge, product_count under-limit OK,
  at-limit raise, missing-db kwarg raises ValueError, unknown resource raises.
- `tests/test_core_middleware_ordering.py` — 4 tests: count==7, runtime order matches §4.H,
  audit innermost, CORS outermost. Reads `app.user_middleware` from the real `app.main.app`.
- `tests/test_core_audit_mw.py` — 7 tests: PII scrubber unit (phone hashed, FSSAI/GST stripped),
  2xx authenticated writes 1 row, 4xx writes 0 rows, 5xx writes 0 rows, anonymous writes 0
  rows, autosave coalesce (2 hits → 1 row), non-autosave (2 hits → 2 rows). Mocks
  `AsyncSessionLocal` to capture row inserts without Postgres.
- `tests/test_core_rate_limit_mw.py` — 3 tests: per-IP triggers 429 with locked envelope,
  per-route decorator triggers 429, Valkey unreachable fails OPEN + WARNING logged.

Plus `tests/conftest.py` extended with `use_live_valkey` fixture (loop_scope="function")
that re-points `shared.valkey._otp_client`/`_cache_client` at the locally-running Redis on
6379 — the conftest default 6381 is a tunnel that's not normally running on the laptop.

### Decisions FLAGGED (not in locked architecture)

1. **`RateLimitMiddleware` returns `JSONResponse` inline, not `raise RateLimitExceededError`.**
   Reason: `BaseHTTPMiddleware.dispatch` raises pass OUTSIDE Starlette's exception handler
   middleware in the dispatch stack, so registered handlers for `MeesellError` are bypassed.
   The inline JSONResponse builds the same locked envelope `{detail, code, validation_message_id, request_id}`
   manually. The `RateLimitExceededError` class is still exposed for service-layer use.
   Trade-off acknowledged; documented in module docstring.

2. **`plan_guard.enforce_plan_limit(product_count, ...)` REQUIRES `db: AsyncSession` kwarg.**
   Picked SELECT COUNT(*) over a Valkey-counter sync-up because the latter is a second
   source-of-truth with extra failure modes. `core/` takes the AsyncSession DB import via a
   LOCAL import (inside the function body) to avoid top-level `app.shared.models` import in
   `core/`. Documented in module docstring + tests cover the missing-kwarg ValueError path.

3. **Per-route rate-limit metadata lookup uses manual `app.router.routes[r].matches(scope)`.**
   `BaseHTTPMiddleware` runs BEFORE Starlette's router populates `request.scope["route"]`,
   so the documented `request.scope.get("route")` approach in §4.H is incomplete for this
   middleware position. Walks `app.routes` and picks the FULL match. Uses
   `starlette.routing.Match.FULL` enum. The fallback path also checks `request.scope["route"]`
   first so an inner middleware re-dispatch still works.

4. **`errors.py` registers BOTH `RequestValidationError` AND `PydanticValidationError`.**
   FastAPI body-validation raises the former; service-layer `Model.model_validate(...)`
   raises the latter. The §4.F spec mentions "pydantic.ValidationError" only — handler
   added for both to cover both call sites with the same envelope. Documented in module.

5. **`use_live_valkey` fixture added to `tests/conftest.py`** — pivots the singletons at
   localhost:6379 because conftest default port 6381 expects an SSH tunnel that is not
   running. Override via env `CORE_TEST_VALKEY_URL`. Loop-scope=function to dodge the
   asyncpg/asyncio cross-loop Future attachment that pytest-asyncio 0.24 induces under
   `asyncio_default_fixture_loop_scope=session`.

### Acceptance gate result
- `python -c "from app.main import app"` → imports clean; 9 routes; 7 user middleware in
  exactly the §4.H runtime order.
- `ruff check app/core/ app/main.py tests/test_core_*.py` → ALL CHECKS PASSED.
- Core test suite: 39/39 PASS.
- Baseline regression (`test_app_boot_integration.py` + `test_database.py`): 49/49 PASS.
- Shared infra (`test_shared_*`): 46/46 PASS.
- Grand total this dispatch: 134/134 PASS.

### Auth-builder coordination
`core/auth.py` (19.6 KB) and `core/middleware/auth_mw.py` (5.5 KB) were both already on
disk when I wired `app/main.py`. The import `from app.core.middleware.auth_mw import AuthContextMiddleware`
resolved cleanly — class name confirmed by inspecting auth_mw `__all__`. No blocker raised.

### Hand-offs queued
- §5A `i18n/resolver.py` — `_resolve_message_id` in `core/errors.py` is already wired with
  a lazy import. When resolver lands, no code change is required in `errors.py`.
- §7 `iam` — consumes `RateLimitMiddleware`'s `@rate_limit` decorator + `audit_event`
  decorator on auth endpoints; consumes `PlanLimitExceededError` for the upcoming
  subscription gates; consumes `enforce_plan_limit` from service layer at every
  create-product call site.
- §9 `category` — replaces `prewarm_top_categories` stub with the real seed-list +
  fetch fn. Signature `prewarm_top_categories(n: int = 100) -> None` is locked.
- `meesell-api-routes-builder` — every authenticated route can now use
  `@rate_limit(...)`, `@audit_event(...)`, and rely on `request.state.{user_id, request_id}`
  being populated by the chain. Error responses follow the locked envelope automatically.

---

## Memory index
| Entry | Type | Summary |
|---|---|---|
| Session 2026-06-05 final purge | project | 10 files deleted (3 workers + 7 tests), 1 modified (celery_app.py); backend declared construction-ready |
| pricing_engine import blocker | reference | services/pricing_engine.py line 23 imports deleted app.schemas.pricing.PricingAlert; fix in construction |
| celery_app.py include pattern | reference | include=[] when task modules absent; re-populate with ["app.workers.image_tasks", ...] when V1 tasks ship |
| task_reject_on_worker_lost | reference | Added to celery conf per services-builder ALWAYS rule |
| V1 head revision (DB) | reference | f31c75438e61 (chain: 935e55b4852c → a1b2c3d4e5f6 → f31c75438e61) |
| §4 core/ services slice 2026-06-06 | project | 11 files + 7 test files (39 tests) — errors, tenancy, cache, plan_guard, 5 middleware + app/main wiring |
| Rate-limit JSONResponse-inline decision | reference | BaseHTTPMiddleware raises bypass FastAPI exception handlers — middleware MUST return Response, not raise |
| Plan guard product_count needs db kwarg | reference | enforce_plan_limit(resource="product_count", db=AsyncSession) — local import of Product model to avoid core/→domain imports |
| Per-route rate-limit via decorator + manual route match | reference | @rate_limit(scope,limit,window) attaches __rate_limit__; mw walks app.router.routes[r].matches(scope) — request.scope["route"] is None at BaseHTTPMiddleware entry |
| use_live_valkey fixture | reference | tests/conftest.py loop_scope="function" — points singletons at localhost:6379, flushes scratch DBs around test |
| Middleware registration deepest-first | reference | Starlette stores users[0]=outermost; register Audit FIRST then PlanGuard → RateLimit → Tenancy → Auth → RequestId → CORS to achieve §4.H runtime order |
| i18n resolver deferred wire | reference | errors._resolve_message_id() lazy-imports app.i18n.resolver; falls back to mid or fallback; no code change needed when §5A lands |
| auth URL pattern (routes) | reference | /api/v1/auth/otp/send, /otp/verify, /me — locked by api-routes-builder |
| Python venv path | reference | backend/.venv/bin/python (3.11); PYTHONPATH=backend/ for pytest |
| app/i18n/ pattern (DB) | reference | versioned schema_jsonb constants; services producing schema_jsonb MUST import here |

---

## §4 cross-test pollution fix (2026-06-06 follow-up)

### Symptom
After `test_database.py`'s seeded-data tests ran (session-scoped `dev_engine`),
the next test that called `get_valkey_otp()`/`get_valkey_cache()` raised
`RuntimeError: Task got Future attached to a different loop`. 10 tests in
test_core_cache/plan_guard/rate_limit_mw affected when the full suite ran.

### Root cause
The old `use_live_valkey` fixture pivoted module-level singletons in
`app.shared.valkey._otp_client`/`_cache_client`. Those clients had connection
pools bound to whatever loop ran the fixture setup. When pytest-asyncio's
session-loop-scoped fixture (`dev_engine`) forced its loop into scope, the
singleton's pool was bound to that loop. Function-scoped tests that ran
later in a different loop hit the cross-loop Future error.

### Fix (tests/conftest.py)
Replaced singleton-pivot with **monkeypatch of `get_valkey_otp` /
`get_valkey_cache`** in (a) `app.shared.valkey`, (b) every consumer module
in `app.core.*` that did `from app.shared.valkey import ...` at module load
(`cache`, `plan_guard`, `middleware.rate_limit_mw`, `middleware.audit_mw`),
and (c) the test modules `test_core_cache` + `test_core_plan_guard` (pytest
loads tests as TOP-LEVEL modules, not `tests.test_core_*`, when there is no
`tests/__init__.py`). Each patched factory returns a FRESH Redis client
built inside the CURRENT loop on every call. All clients are tracked in a
local list and `aclose`d in teardown before the loop dies. The fixture also
defensively nukes any pre-existing `_otp_client` / `_cache_client` singletons
at entry — no shared state survives.

### Why per-call fresh client (not singleton pivot)
- `redis.asyncio` Connection pools attach to whatever loop is running on first
  await on a connection. Singletons built in a session loop are unusable in a
  function loop.
- monkeypatch teardown is automatic — zero leak risk; no need to restore.

### Acceptance after fix
- Reproducer `pytest tests/test_database.py tests/test_core_cache.py::test_versioned_key_format` → 43 PASS (was 42 PASS + 1 cross-loop error).
- Full §4 suite `pytest tests/test_app_boot_integration.py tests/test_database.py tests/test_core_*.py tests/test_shared_*.py` → **149 PASS, 3 skip, 0 fail**.
- `ruff check app/core/ app/main.py tests/conftest.py tests/test_core_*.py` → All checks passed (also cleaned pre-existing `import uuid` unused-import from conftest).

### Files touched
- `backend/tests/conftest.py` — fixture body rewritten lines ~119–230 (was 119–162); pre-existing `import uuid` removed line 7.
- **NO** consumer file changes — every consumer already calls through `app.shared.valkey.<name>` via `from app.shared.valkey import …` at module load; the monkeypatch of those captured names covers the call sites.

### Pattern locked for future tests
When introducing a new core/middleware module that calls `get_valkey_*`,
append its import path to the consumer-patch tuple in
`use_live_valkey` (currently 4 entries). When introducing a new test
module that imports `get_valkey_*` by name at module load, append it to
the test-module-patch tuple (currently 2 entries).

---

## §5A i18n CONSTRUCTED (2026-06-06)

### Scope
Solo sub-session `meesell-backend-construction-5A-i18n-1`. Built the
Presentation Layer Contract + i18n package per `BACKEND_ARCHITECTURE.md`
§5A. Six files created/extended under `backend/app/i18n/` + 4 unit-test
modules + `core/errors.py` resolver wire.

### Files created (5)
- `backend/app/i18n/messages_en.py` (NEW) — `VALIDATION_MESSAGES: dict[str, str]`
  with **54 IDs** covering iam (8) + auth-dep (3) + customer (6) + category (4)
  + catalog (8) + image (5) + pricing (5) + dashboard (1) + export (7) + core
  cross-cutting (3: tenancy/plan_guard/server) + validation.body.malformed_json.
- `backend/app/i18n/resolver.py` (NEW) — `resolve(message_id, locale="en") -> str`
  per §5A.I. Locked fallback chain: locale → en → verbatim ID. Logs
  `i18n.resolver.missing_key` at WARNING when verbatim returned (§6A/§19
  observability hook).
- `backend/app/i18n/schema_contract.py` (NEW) — TypedDicts `SchemaEnvelope`
  (§5A.B 7-key) + `FieldSpec` (§5A.C 9-key). Locked enum sets:
  `DATA_TYPE_VALUES` (8) + `PRIMITIVE_VALUES` (11) + `COMPLIANCE_SHAPE_VALUES`
  (2) + `ENUM_RESOLVER_VALUES` (3). Frozensets `ENVELOPE_KEYS` + `FIELD_SHAPE_KEYS`
  drive the conformance tests.
- `backend/app/i18n/advanced_canonical.py` (NEW) — `ADVANCED_CANONICAL_NAMES =
  frozenset({"group_id"})` exactly 1 element per §5A.F + sub-session 2 G1.
- `backend/app/i18n/__init__.py` (REWRITTEN) — module docstring now
  documents the three concerns the package owns: seed-rule modules,
  presentation contract, locale-aware message resolution.

### Files modified (1)
- `backend/app/core/errors.py` — replaced deferred-wire `_resolve_message_id`
  with direct call to `app.i18n.resolver.resolve(mid, locale="en")`.
  Locale hard-coded to `"en"` per V1 (§5A.I item 4); V1.5 will plumb
  `request.state.locale` from an Accept-Language middleware. Existing
  fallback-to-prose semantic preserved when resolver returns verbatim ID.

### Tests added (4 modules, 140 tests)
- `tests/test_messages_en_id_regex.py` — 6 test classes including
  parametrised `pytest.mark.parametrize("message_id", sorted(VALIDATION_MESSAGES.keys()))`
  regex match per §5A.H `^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){2}$` + segment
  count + no-hyphen + no-uppercase + non-empty values.
- `tests/test_resolver_fallback.py` — 7 tests: en locale hit, default
  locale = en, non-en fallback to en, unknown id → verbatim, unknown id
  non-en locale → verbatim, missing-key WARNING log assertion, entirely
  unregistered locale code → en.
- `tests/test_schema_jsonb_envelope_keys.py` — 8 tests against reference
  envelope: exactly-7-keys, parametrised key presence, types
  (list/int/str), total_count invariant, compliance_shape ∈ locked set,
  wizard_step_count ∈ [3, 8].
- `tests/test_per_field_shape_keys.py` — 14 test classes mostly
  parametrised across 6 reference fields covering all 6 data_type
  primitives + advanced + non-advanced: 9-key subset coverage,
  data_type ∈ 8 locked, primitive ∈ 11 locked, enum_resolver invariant
  (REQUIRED for dropdown, null otherwise), marker binary, canonical_name
  regex, help_text non-empty, validation_message_ids list[str],
  is_advanced allowlist enforcement, cardinality locks for each enum
  set (8/11/2/3) plus ADVANCED_CANONICAL_NAMES cardinality=1.

### Decisions FLAGGED (not in locked architecture)

D1 — **`server.internal_error` and `http.{N}` IDs stay 2-segment** despite
the §5A.H regex requiring 3-segment registry keys. Resolution: these are
DYNAMIC envelope `validation_message_id` values built at runtime in
`core/errors.py` for fall-through handlers (generic Exception, HTTPException);
they are NOT registry keys. §5A.H line 1688 says the CI Contract 10 regex
scans the **registry** (`i18n/messages_en.py`), not dynamic envelope values.
Registry has `server.internal.error` (3-segment) as the canonical entry;
the envelope-emitted ID `server.internal_error` falls through the resolver
to verbatim, then errors.py uses the supplied fallback. Tests
`test_register_error_handlers_generic_exception` + `test_register_error_handlers_http_exception`
preserved as-is — they assert on the envelope's literal `validation_message_id`
field which is independent of the registry key spelling.

D2 — **The 8 §7.G iam message IDs spec'd as 2-segment** (`auth.otp_invalid`,
`auth.refresh_invalid`, etc.) were normalised to 3-segment in the
registry (`auth.otp.invalid`, `auth.refresh.invalid`, etc.) to conform
to §5A.H. Same pattern for customer/catalog/image/export domain IDs that
the spec lists in 2-segment shorthand (e.g. `customer.profile_not_found`
→ `customer.profile.not_found`; `export.not_found` → `export.not.found`).
Spec text at §7.G/§8/§14.J uses 2-segment shorthand inline; §5A.H regex
is the authoritative lock. ESCALATION NEEDED if master prefers updating
§5A.H to permit 2-segment instead.

D3 — **Spec mentions 6-key envelope; spec example shows 7 keys.** The
construction prompt summary said "6-key envelope" but §5A.B example
envelope (lines 1533-1542) shows 7: fields, compulsory_count,
optional_count, total_count, wizard_step_count, main_sheet_label,
compliance_shape. Honoured the spec example (7). The prompt was a
summary, not a lock amendment.

D4 — **Spec key name is `validation_message_ids` (plural)**, not
`validation_message_id` (singular) the prompt summary used. Spec §5A.C
line 1587 locks `list[str]` plural. Honoured spec.

### Hand-offs queued
- §6 adapters + §6A ai_ops — NO direct consumption; resolver only fires
  on error envelope path.
- §7 iam (`meesell-auth-builder`) — every `IamError` subclass raises with
  `validation_message_id` set to one of the 8+3 IDs registered:
  `validation.phone.invalid_format`, `validation.otp.invalid_format`,
  `validation.webhook.malformed_payload`, `auth.otp.invalid`,
  `auth.otp.attempts_exceeded`, `auth.msg91.unavailable`,
  `auth.refresh.invalid`, `auth.webhook.signature_invalid`,
  `auth.token.missing`, `auth.token.expired`, `auth.user.not_found`.
  `core/errors.py` resolves to English via `resolve()`.
- §8/§9/§10/§11/§12/§13/§14 module construction — exceptions.py file
  per module raises with the IDs registered here. ID set is forward-compat:
  modules MAY add per-field dynamic IDs at services-builder dispatch time;
  the registry growth pattern is documented in §5A.J.
- §19 CI Contract 10 — `test_messages_en_id_regex.py` IS the CI gate.
- `schema_contract.py` — consumed by §9 (`category.service.fetch_schema`
  return-type hint should be `SchemaEnvelope`), §10 (`catalog.service.patch_product`
  validator dispatches on `data_type`/`enum_resolver`/`is_advanced`),
  §14 (`export.tasks._select_strategy` dispatches on `compliance_shape`).
- `ADVANCED_CANONICAL_NAMES` — consumed at seed time by
  `scripts/build_template_schemas.py` (already locked at line 84 per
  database-builder memory) and at validation time by §10 catalog
  schema-driven validator (rejects new is_advanced=True canonical_name
  not in the allowlist).

### Test counts
- New tests this dispatch: **140 PASS** (90 messages_en_id_regex
  parametrised + 7 resolver_fallback + 8 schema_envelope + 35 per_field_shape).
- Updated tests: `test_core_errors.py::test_i18n_resolver_wired` (was
  `test_i18n_resolver_deferred_wire`) — 6/6 PASS.
- Full Wave 1 regression suite: **268/268 PASS** (boot 7 + database 42 +
  shared 46 + core 39 + 4 new modules 140 + assorted = 268).
- Ruff: clean on all 7 touched files.

### Memory index additions
| Entry | Type | Summary |
|---|---|---|
| §5A i18n landed | project | 5 i18n package files + 1 errors wire + 4 test modules; 140 new tests; 268 regression PASS |
| i18n.resolver fallback chain locked | reference | locale → en → verbatim with WARNING log on verbatim tier; observability key = i18n.resolver.missing_key |
| 3-segment regex normalisation | reference | spec §7.G/§8/§14.J 2-segment IDs renormalised to 3-segment registry keys; §5A.H regex is the authoritative lock |
| ADVANCED_CANONICAL_NAMES locked at 1 element | reference | frozenset({"group_id"}) exactly per §5A.F + sub-session 2 G1; widening requires §5A amendment |
| SchemaEnvelope + FieldSpec TypedDicts | reference | doc-in-code §5A.B (7 keys) + §5A.C (9 keys); imported by tests, optional import for downstream module type hints |
| DATA_TYPE_VALUES (8) / PRIMITIVE_VALUES (11) / COMPLIANCE_SHAPE_VALUES (2) / ENUM_RESOLVER_VALUES (3) | reference | locked frozensets at app.i18n.schema_contract module level |

---

## §6 adapters CONSTRUCTED (2026-06-06)

### Scope
Solo sub-session `meesell-backend-construction-6-adapters-1`. Built the 5
vendor adapters per `BACKEND_ARCHITECTURE.md` §6.B–§6.G under
`backend/app/adapters/`. Zero touches outside §6 scope.

### Files created (6)
- `backend/app/adapters/__init__.py` — `AdapterError(MeesellError)` root +
  5 typed subclasses (`GeminiAdapterError`, `Msg91AdapterError`,
  `GcsAdapterError`, `RazorpayAdapterError`, `LangfuseAdapterError`).
  Default `status_code=502` + `validation_message_id=<vendor>.unavailable`.
- `backend/app/adapters/gemini.py` (~230 LOC) — async `generate_text` +
  `generate_vision`; `GeminiResponse` dataclass (text/in_tok/out_tok/
  finish_reason/raw); 3-retry exponential 1s/4s/16s on conn/5xx/429;
  `_call_sdk` is the single SDK touch point + mock target for tests; lazy
  per-model `GenerativeModel` cache; `genai.configure(api_key=...)` runs
  exactly once at first model construction.
- `backend/app/adapters/msg91.py` (~180 LOC) — async `send_otp(phone, otp,
  *, template_id)`; `Msg91Response(success, request_id, message)`; 1
  retry on conn/5xx/429; **LOCKED EXCEPTION: NEVER raises** — returns
  `success=False` on any failure (transport, vendor failure, unexpected).
  Phone `+` stripped (vendor requirement). OTP NEVER logged.
- `backend/app/adapters/gcs.py` (~200 LOC) — async `upload_bytes`,
  `download_bytes`, `generate_signed_url(ttl_seconds=3600 default,
  method="GET"|"PUT")`, `delete`; sync SDK wrapped in `asyncio.to_thread`;
  ADC creds; raises `GcsAdapterError(502)` on `_FATAL_SDK_EXC` =
  (NotFound, Forbidden, Unauthorized, BadRequest, GoogleAPICallError);
  signed URLs use `version="v4"`.
- `backend/app/adapters/razorpay.py` (~80 LOC) — **SYNC**
  `verify_webhook_signature(payload, signature, *, secret) -> bool`;
  HMAC-SHA256 + `hmac.compare_digest` constant-time; **LOCKED EXCEPTION:
  NEVER raises, NEVER async**; defensive bool returns on malformed
  payload/signature.
- `backend/app/adapters/langfuse.py` (~190 LOC) — async `trace` +
  `score`; **LOCKED: NEVER raises (drop-on-failure with WARNING)**;
  missing creds → no-op + 1-time WARNING via `_creds_warned` latch; httpx
  direct POST to `{LANGFUSE_HOST}/api/public/ingestion` with batch
  envelope `{batch: [{id, timestamp, type: "trace-create"|"score-create",
  body: {...}}]}`.

### Tests added (5 modules, 73 tests, all PASS)
- `tests/test_gemini_adapter.py` (17 tests) — exception hierarchy
  inheritance; happy path; max_output_tokens / response_mime_type
  propagation; generate_vision image bytes propagation; 503/429/
  ConnectionError transient retry then succeed; retry exhaustion → raise;
  non-retryable Unauthenticated / InvalidArgument → raise immediately;
  exception chained via `__cause__`; defensive `_envelope` on
  missing usage_metadata / missing text; no `from app.modules` imports;
  no `os.getenv`.
- `tests/test_msg91_adapter.py` (13 tests) — happy 2xx + `type=success`;
  4xx → success=False (no raise); 5xx → 1 retry then success=False;
  429 → 1 retry; success after one transient 5xx; connection error →
  success=False; timeout → success=False; phone `+` stripped; template_id
  override; defensive RuntimeError → success=False; no `os.getenv`;
  source-grep confirms OTP not interpolated into log format strings.
- `tests/test_gcs_adapter.py` (16 tests) — exception class inheritance;
  upload_bytes happy + image path + export path conventions; Forbidden /
  GoogleAPICallError → GcsAdapterError; download_bytes happy + NotFound
  → raise; signed URL default TTL=3600s (locked §10.8); custom TTL; PUT
  method; SDK error → raise; delete happy + NotFound → raise; bucket
  override; no `os.getenv`; no domain imports.
- `tests/test_razorpay_adapter.py` (14 tests) — `iscoroutinefunction`
  False (LOCKED sync); source-grep first line `def` not `async def`;
  RazorpayAdapterError class defined for V1.5; valid HMAC → True;
  invalid → False (no raise); wrong secret → False; uses settings when
  secret arg omitted; empty/None signature → False; non-bytes payload →
  False (defensive); bytearray accepted; constant-time `compare_digest`
  used; no `os.getenv`; razorpay SDK NOT imported in V1.
- `tests/test_langfuse_adapter.py` (13 tests) — LangfuseAdapterError
  defined for V1.5; trace + score POST to `/api/public/ingestion` with
  correct type discriminators; 5xx/ConnectError/Timeout/RuntimeError →
  drop-on-failure + WARNING log; missing creds → 0 network calls + 1
  WARNING per session (latch verified); UUID generated when trace_id
  omitted; user_id UUID serialised to str; no `os.getenv`; no domain
  imports.

### Acceptance gate result
- Ruff: ALL CHECKS PASSED on all 11 touched files (4 unused-import F401
  fixes applied during gate: `asyncio` in test_gcs/test_gemini,
  `timedelta` in test_gcs, `pytest` in test_razorpay).
- `python -c "from app.main import app; <import all 5 adapter modules>"`:
  imports clean, routes=9 unchanged.
- `pytest test_app_boot_integration test_shared_* test_core_* test_messages_en_id_regex test_resolver_fallback test_schema_jsonb_envelope_keys test_per_field_shape_keys`:
  216/216 PASS.
- `pytest test_<5 adapters>_adapter.py`: **73/73 PASS in 5.69s**.
- `pytest test_database.py` (live dev Postgres via SSH tunnel): **42/42 PASS in 153s**.
- Grand total this dispatch: **331/331 PASS**.

### Decisions FLAGGED (not in locked architecture)

D1 — **LangFuse implementation = httpx direct POST, NO new SDK dependency.**
`requirements.txt` has no `langfuse` package and I chose NOT to add one in
this dispatch. Rationale: (a) `httpx` is already pinned; (b) fire-and-
forget semantics make the SDK's batching value moot for V1 volume; (c)
SDK reintroduction is a single-file change in V1.5 if needed. FLAGGED in
the `adapters/langfuse.py` module docstring under "Decision flag D1".
ESCALATE to master if the SDK is preferred — the swap is trivial.

D2 — **`adapters/__init__.py` re-exports both `AdapterError` and the 5
typed subclasses** — `app.adapters import GeminiAdapterError` works
without touching the per-vendor module. The §19 CI linter can then test
the inheritance chain at the package import surface.

D3 — **`_reset_for_testing()` helper added to each adapter** (except
razorpay — no state). Pattern: clears the module-level singleton client
and `_init_lock`. Required because `asyncio.Lock()` is bound to the
loop that first awaits it; pytest-asyncio session loop-scope plus the
function-scope fixture pattern would otherwise hit "Future attached to
a different loop" on subsequent test runs. Test fixtures call this in
both setup and teardown.

D4 — **Gemini retry constants live in module-level `_RETRY_DELAYS_S =
(1.0, 4.0, 16.0)`** — exposed for monkeypatch overrides (tests zero it
to keep wall time low). The 4 attempts = 1 initial + 3 retries per §6.B
"3-retry exponential backoff" reading; the loop iterates
`range(len(_RETRY_DELAYS_S) + 1)`.

D5 — **`razorpay.verify_webhook_signature` source-grep test added.**
`test_verify_webhook_signature_signature_is_def_not_async_def` reads
the function's source first line and asserts it starts with `def ` and
NOT `async def `. Defensive against accidental rewrites.

### Hand-offs queued
- **§6A `ai_ops/client.py`** — sole consumer of `adapters/gemini.py` per
  §3.G boundary rule. Will call `gemini.generate_text(...)` /
  `gemini.generate_vision(...)` wrapped by cost tracker + 3-layer
  guardrail + LangFuse trace + budget cap.
- **§6A `ai_ops/client.py`** — sole consumer of `adapters/langfuse.py`.
  Wraps every Gemini call with `langfuse.trace(...)` after the call
  returns (success or failure).
- **§7 `iam.service.send_otp_for_login`** — consumes
  `adapters/msg91.send_otp(phone, otp)` after rate-limit gate per
  `MVP_ARCH §10.7`. Surfaces 503 to seller when `Msg91Response.success
  is False` (the adapter never raises — caller is the 5xx gateway).
- **§7 `iam.router.razorpay_webhook`** — consumes
  `adapters.razorpay.verify_webhook_signature(payload, signature)`;
  responds 401 when False. SYNC call (no await).
- **§11 `image.service.upload_image`** + **§11 `image.tasks.process_image`**
  — consume `adapters/gcs.upload_bytes`, `gcs.download_bytes`,
  `gcs.generate_signed_url`. Path convention enforced at service layer:
  `meesell-images/{user_id}/{product_id}/{idx}.jpg`.
- **§14 `export.service.build_xlsx`** + **§14 `export.tasks.generate_export`**
  — consume `adapters/gcs.upload_bytes` (XLSX + ZIP),
  `gcs.download_bytes` (image gather), `gcs.generate_signed_url`
  (download URL on poll). Path: `meesell-exports/{user_id}/{export_id}/
  {sheet.xlsx|images.zip}`.

### Pending Secret Manager values still queued (NOT a blocker)
- `razorpay-webhook-secret` — populated by `meesell-infra-builder`
  during §7 iam dispatch (per STATUS_BACKEND L2 latent).
- `langfuse-secret-key` — populated by `meesell-infra-builder` during
  §6A ai_ops dispatch (per STATUS_BACKEND L2 latent).
Both are consumed by the adapters from `settings.*` — the adapters do
not pre-validate; missing values surface as MSG91/Razorpay/LangFuse
runtime failures that the adapter's locked failure mode already covers
(msg91 → success=False; razorpay → False; langfuse → drop-on-failure).

### Memory index additions
| Entry | Type | Summary |
|---|---|---|
| §6 adapters CONSTRUCTED | project | 5 adapter files + 1 `__init__.py` + 5 test modules (73 tests); 331 regression PASS |
| AdapterError(MeesellError) root | reference | `app.adapters.AdapterError` + 5 vendor subclasses; default status=502, code=`<vendor>.unavailable` |
| Gemini retry triple | reference | `_RETRY_DELAYS_S=(1.0,4.0,16.0)` — 1 initial + 3 retries on conn/5xx/429; non-retryable raises immediately |
| msg91 NEVER raises | reference | locked exception #1 to §6.G — returns `Msg91Response(success=False, ...)` on transport / vendor failure |
| razorpay sync + bool | reference | locked exceptions #2 + #3 — `verify_webhook_signature` is `def` (not `async def`) + returns bool (never raises) |
| langfuse drop-on-failure | reference | locked exception #4 to §6.G — `trace`/`score` always return None; failures logged WARNING; missing creds = no-op + 1 WARNING (latched) |
| GCS path convention | reference | `meesell-images/{user_id}/{product_id}/{idx}.jpg` + `meesell-exports/{user_id}/{export_id}/{sheet.xlsx\|images.zip}` per §6.D + MVP_ARCH §10.8 |
| GCS signed URL TTL=3600 | reference | locked default per `settings.GCS_SIGNED_URL_TTL_SECONDS = 3600` (MVP_ARCH §10.8) |
| Lazy singleton + asyncio.Lock + `_reset_for_testing` | reference | Required pattern for every async-stateful adapter to survive pytest-asyncio function-loop tests across module loads |
| LangFuse httpx-direct (no SDK) | reference | D1 decision — POST to `{LANGFUSE_HOST}/api/public/ingestion` with batch envelope; trace-create + score-create types |
| Boundary rule: gemini consumed only by ai_ops | reference | §3.G + §16.D — §19 import-linter rejects `from app.adapters.gemini` under `app/modules/` |

---

## §6A ai_ops CONSTRUCTED (2026-06-06)

### Scope
Solo sub-session `meesell-backend-construction-6A-aiops-1`. Built the
AI Operations Layer per `BACKEND_ARCHITECTURE.md` §6A under
`backend/app/ai_ops/` — the SOLE import surface domain modules use for
Smart Picker / Auto-fill / Watermark AI work. Authored both the
infrastructure (services-builder track) and the V1 baseline prompt
templates (prompt-engineer track did NOT need a separate dispatch —
content drafted inline, refinement deferred to §19 golden-eval tuning).

### Files created (10 source + 6 test modules)

Source (10):
- `backend/app/ai_ops/__init__.py` — re-exports `AICallContext`,
  `AIResponse`, `BudgetExceededError`, `call_gemini`, `EvalReport`,
  `FixtureResult`, `run_eval`.
- `backend/app/ai_ops/cost_tracker.py` (~220 LOC) — module-level
  `RATE_INPUT_PER_1K=0.0078` + `RATE_OUTPUT_PER_1K=0.031` constants
  (env override via `getattr(settings, ..., default)` per §6A.D
  footnote); `compute_cost_inr` pure formula; `record()` direct
  ORM write to `audit_events` + per-user-hourly Valkey counter +
  delegates reservation release to `budget_cap.release_reservation`;
  `Workload = Literal["smart_picker", "autofill", "watermark"]` locked
  type re-export; Asia/Kolkata day-boundary helpers
  `_today_kolkata_str` / `_hour_kolkata_str`.
- `backend/app/ai_ops/budget_cap.py` (~280 LOC) — `BudgetExceededError`
  subclass (status 503, code `ai_ops.budget_exhausted`,
  validation_message_id `ai_ops.budget.exhausted`); `BudgetStatus`
  frozen dataclass; `check_and_reserve` atomic Lua via
  `redis.eval(_RESERVE_LUA)`; `release_reservation` atomic Lua via
  `_RELEASE_LUA` (idempotent on missing); `get_budget_status` reads
  committed+pending; 80% alarm log fires inside `check_and_reserve`;
  per-workload default token estimates locked.
- `backend/app/ai_ops/guardrail.py` (~210 LOC) — `_LAYER1_PREFIX`
  dict locked at module level (one prefix per workload); enum-block
  appended to autofill prefix when allowed_enums supplied;
  `parse_and_validate` dispatches to per-workload shape validators
  (smart_picker / autofill enum / watermark); returns None on
  failure → signals retry; `build_retry_prompt` constructs the
  stricter follow-up prompt.
- `backend/app/ai_ops/prompt_registry.py` (~140 LOC) — `resolve()`
  dynamic-imports `app.ai_ops.prompts.<name>_v<n>`; `render()`
  literal `{{var}}` substitution (no Jinja2 dep in V1);
  `PromptResolutionError` on malformed prompt_id /
  workload-mismatch / missing module attrs.
- `backend/app/ai_ops/client.py` (~290 LOC) — `AICallContext` +
  `AIResponse` frozen dataclasses with the locked §6A.C 5-field
  shape; `call_gemini()` 9-step internal flow with per-workload
  graceful fallback for BudgetExceededError, adapter-failure, and
  Layer 2 retry exhaustion; arg-validation guard for
  watermark-image_bytes / non-watermark-no-image-bytes mismatch;
  trace_id propagation through LangFuse.
- `backend/app/ai_ops/eval.py` (~160 LOC) — `EvalReport` +
  `FixtureResult` frozen dataclasses; `_TARGET_METRICS` locked at
  smart_picker=0.80 / autofill=1.00 / watermark=0.85;
  `run_eval(workload)` loads `tests/eval/<workload>/fixtures.json`,
  returns 0/0+failed when missing (V1 baseline — fixtures land in
  §19); per-fixture dispatch is a stub returning passed=False with
  explicit "wired in §19" error string; CLI entry at
  `python -m app.ai_ops.eval --workload <name>`.
- `backend/app/ai_ops/prompts/__init__.py` — package docstring documenting
  the 4 required module-level constants (TEMPLATE, VERSION, WORKLOAD,
  RENDERED_BY).
- `backend/app/ai_ops/prompts/smart_picker_v1.py` — V1 baseline draft
  with `{{description}}` + `{{compressed_tree}}` substitution
  placeholders; emits 5-suggestions JSON contract.
- `backend/app/ai_ops/prompts/autofill_v1.py` — V1 baseline draft
  with `{{product_spec}}` + `{{schema}}` placeholders; emits
  `{"fields": {...}}` JSON contract.
- `backend/app/ai_ops/prompts/watermark_v1.py` — V1 baseline draft;
  vision-rendered; emits `{"has_watermark": bool, "confidence": float}`
  JSON contract.

Files modified (1):
- `backend/app/i18n/messages_en.py` — added one cross-cutting ID
  `ai_ops.budget.exhausted` consumed by `BudgetExceededError`
  envelope. Conforms to §5A.H 3-segment regex.

### Tests added (6 modules, 80 tests, all PASS)
- `tests/test_ai_ops_cost_tracker.py` (15 tests) — rate constants;
  compute_cost_inr (4 cases incl. ₹0.05 envelope); record audit row
  shape; release_reservation wired when reservation_id supplied; no
  release when None; audit failure does NOT raise; user hourly
  counter bumped; get_daily_spend / get_user_hourly_spend.
- `tests/test_ai_ops_guardrail.py` (22 tests) — Layer 1 per-workload
  prefix; autofill enum-block appended only when supplied;
  Layer 2 smart_picker (7 invariants: JSON / list rejected / missing
  fields / confidence range / reasons type); Layer 2 autofill (5: enum
  match / enum violation / free-text / missing / value-type);
  Layer 2 watermark (3 invariants); build_retry_prompt.
- `tests/test_ai_ops_prompt_registry.py` (11 tests) — 3 active V1
  versions resolve; workload-mismatch / malformed / unknown raise
  PromptResolutionError; render substitution + missing-placeholder
  left-as-is + non-str stringify.
- `tests/test_ai_ops_budget_cap.py` (14 tests) —
  BudgetExceededError envelope shape (4 invariants); happy
  reserve below cap; default estimate when 0 tokens; hard-stop raise;
  80% alarm log; release missing reservation noop; release
  pending+committed accounting; get_budget_status (empty / 80% /
  100%); race protection (2 concurrent near cap, at most 1 success).
- `tests/test_ai_ops_client.py` (10 tests) — frozen dataclasses;
  9-step flow in order (mock-verified); budget fallback for each
  of 3 workloads with correct envelope shape; Layer 2 retry-then-
  succeed with `layer2_retries=1`; Layer 2 all-3-invalid fallback
  with `reason="guardrail"`; caller-arg guard rails (watermark
  needs bytes, non-watermark rejects bytes).
- `tests/test_ai_ops_eval.py` (8 tests) — frozen dataclass shape;
  3 golden targets locked (0.80 / 1.00 / 0.85); 3-workloads-only
  registry; missing fixtures → passed=False 0/0; 3-fixture file
  → 3 results.

### Acceptance gate result
- Ruff: ALL CHECKS PASSED on all 11 new source files + 6 new test
  files + 1 modified i18n file.
- `python -c "from app.main import app; import app.ai_ops"`:
  imports clean, **routes=9 unchanged**, **Base.metadata.tables=13 unchanged**.
- Workload Literal: `Literal['smart_picker', 'autofill', 'watermark']`
  — exactly 3, locked.
- `pytest test_ai_ops_*`: **80/80 PASS in 0.66 s**.
- `pytest test_app_boot_integration test_shared_* test_core_*
  test_messages_en_id_regex test_resolver_fallback
  test_schema_jsonb_envelope_keys test_per_field_shape_keys
  test_<5 adapters>_adapter test_ai_ops_*`:
  **395 PASS, 3 skip (pre-existing Valkey tunnel)**.
- `pytest test_database.py` (live dev Postgres via SSH tunnel):
  **42/42 PASS in 85 s**.
- Grand total: **437 PASS, 3 skip** across the §0/§4/§5/§5A/§6/§6A
  surface.

### Decisions FLAGGED (not in locked architecture)

D1 — **Cost rates configurable via `getattr(settings, "AI_RATE_*",
MODULE_CONSTANT)`** rather than adding `AI_RATE_INPUT_PER_1K` /
`AI_RATE_OUTPUT_PER_1K` fields to the §5.D Settings table now. §6A.D
says "configurable via env if rates change"; adding Settings fields is
a future amendment. The `getattr` pattern lets a future infra-builder
add the env var without changing this module's code. ESCALATE if
master prefers explicit Settings fields shipped now.

D2 — **Reservation pattern uses 2 Valkey counters** (`committed` +
`pending`) instead of 1. The 100% hard-stop check is against
`committed + pending`; release moves pending → committed. Lua script
serialises both counter reads + writes atomically in Valkey's
single-threaded executor. This is the §6A.F "reservation pattern"
made concrete — the spec mandates race-safety but did not specify the
counter layout.

D3 — **Reservation safety-net TTL = 300 s** (5 min). Worst-case
Gemini call = adapter 3-retry (1+4+16 s) × 2 Layer-2 retries +
network ≈ 100 s; 300 s leaves a 3× safety margin. If a worker crashes
mid-call, the pending counter self-heals in ≤5 min.

D4 — **Audit row uses `event_type="ai.call"`** (7 chars, fits the
40-char column lock). Metadata jsonb shape:
`{workload, input_tokens, output_tokens, cost_inr}`. Diff_jsonb is
NULL because there's no before/after delta for an AI call.

D5 — **AIResponse stays exactly 5 fields per §6A.C** — no
`fallback_offered` field added. Instead, the workload-specific
`parsed` dict carries `"fallback_offered": True` (smart_picker /
autofill) or `"watermark_check": "skipped_budget"` / `"skipped_guardrail"`
(watermark). Domain modules branch on the parsed-dict key rather than
a top-level flag. Keeps the locked shape intact.

D6 — **prompt-engineer track NOT dispatched in this sub-session.**
Authored V1 baseline prompt templates inline (storage layout is locked
here; content is a draft). Per dispatch prompt's "if the prompt-engineer
escalates, route via meesell-ai-coordinator memory" — this avoids a
coordinator-of-coordinator depth penalty. Refinement deferred to §19
golden-eval tuning where prompt-engineer iterates against the 3 fixture
sets. FLAGGED in prompt-engineer MEMORY for awareness.

D7 — **Per-workload graceful fallback intercepts `BudgetExceededError`
inside `client.py`** (not at the consumer module). Per dispatch prompt
acceptance criterion #7 + locked rule "DO NOT raise BudgetExceededError
from smart_picker/autofill/watermark paths". Spec §6A.F mentions "the
error maps to a graceful fallback at the calling module" — dispatch
prompt amends this to be wrapped inside client.call_gemini so consumers
NEVER see the exception. Documented in client.py module docstring.

D8 — **Spec says autofill graceful fallback returns 503;
dispatch prompt overrides to 200 with `fallback_offered=True`.**
Honoured the dispatch prompt (more recent lock). The `BudgetExceededError`
class still defaults to status=503 for callers who DO surface it (V1.5
direct-paths) but client.py converts to AIResponse with parsed-dict
`fallback_offered=True` for V1.

### Hand-offs queued

- **§7 `iam`** — NO consumption (auth doesn't use AI). But:
  `core/errors.py` already wires `i18n.resolver` — when iam ships,
  the new `ai_ops.budget.exhausted` ID is resolved via the same path.
- **§9 `category.service.suggest_categories`** — consumes
  `ai_ops.client.call_gemini(ctx, "smart_picker.v1", {"description":
  ..., "compressed_tree": ...})`. Returns `AIResponse` whose
  `.parsed["suggestions"]` is the top-5 list; on budget fallback
  `.parsed = {"suggestions": [], "fallback_offered": True}` → category
  module returns HTTP 200 with the empty suggestions + a fallback
  flag in the response payload.
- **§10 `catalog.service.autofill_product`** — consumes
  `ai_ops.client.call_gemini(ctx, "autofill.v1", {"product_spec":...,
  "schema": ...}, allowed_enums={...})`. Returns `AIResponse` whose
  `.parsed["fields"]` is the canonical-field-name → value dict; on
  budget/Layer-2 fallback `.parsed["fallback_offered"] is True` →
  catalog module returns HTTP 200 with empty fields + flag.
- **§11 `image.tasks.precheck_image`** — consumes
  `ai_ops.client.call_gemini(ctx, "watermark.v1", {}, image_bytes=...)`
  in Celery worker context. Returns `AIResponse` whose
  `.parsed["has_watermark"]` is the bool; on budget fallback
  `.parsed["watermark_check"] == "skipped_budget"` → worker writes
  `product_images.precheck_jsonb.watermark_check = "skipped_budget"`
  and overall precheck status STAYS `"ready"`.
- **§14 `export.service`** — NO direct ai_ops consumption. But
  Layer 3 enum re-validation runs there per §6A.E + §14.
- **§19 import-linter Contract 2** — must reject
  `from app.ai_ops.cost_tracker import ...` /
  `from app.ai_ops.guardrail import ...` /
  `from app.ai_ops.budget_cap import ...` from any module under
  `app/modules/`. Only `app.ai_ops.client.call_gemini` (plus the 3
  re-exported types) is the legal domain-import surface.
- **§19 import-linter Contract 1** — must reject
  `from app.adapters.gemini import ...` from any module under
  `app/modules/`. Only `app.ai_ops.*` may import the gemini adapter.
- **§19 tests/eval/{smart_picker,autofill,watermark}/fixtures.json**
  — populated by category-picker-builder / prompt-engineer /
  image-precheck-builder respectively, against the locked target
  metrics (0.80 / 1.00 / 0.85).
- **`meesell-infra-builder`** — populates `langfuse-secret-key` Secret
  Manager value during §20 deployment (per pre-existing §6 adapter
  hand-off note). client.py consumes from `settings.LANGFUSE_SECRET_KEY`;
  langfuse adapter drops with WARNING when unset.
- **`meesell-prompt-engineer`** — refines the 3 V1 baseline prompts
  during §19 golden-eval tuning. Storage layout locked here; templates
  themselves are owned by prompt-engineer going forward.

### Pending Secret Manager values still queued (NOT a blocker)
- `langfuse-secret-key` — adapters.langfuse already handles missing
  creds (drop-on-failure with 1 WARNING per session). ai_ops.client
  consumes via the adapter; no pre-validation at this layer.

### Memory index additions
| Entry | Type | Summary |
|---|---|---|
| §6A ai_ops CONSTRUCTED | project | 10 source files + 6 test modules (80 tests); 437 regression PASS |
| Workload Literal locked at 3 | reference | `Literal["smart_picker", "autofill", "watermark"]` exactly — adding requires 6-file edit by design |
| Cost rate constants | reference | `RATE_INPUT_PER_1K=0.0078` + `RATE_OUTPUT_PER_1K=0.031` at module level; env override via getattr(settings, ...) |
| 9-step call_gemini flow | reference | resolve→reserve→Layer1→render→SDK→record(+release on final)→Layer2→trace→return |
| Per-workload graceful fallback locked | reference | smart_picker/autofill: parsed={"...": [], "fallback_offered": True}; watermark: parsed={"watermark_check": "skipped_budget"} |
| BudgetExceededError envelope | reference | status=503, code="ai_ops.budget_exhausted", validation_message_id="ai_ops.budget.exhausted" — caught inside client.py for V1 |
| Reservation 2-counter pattern | reference | committed + pending Valkey counters; Lua-atomic check-and-reserve; release moves pending→committed; 300s safety-net TTL |
| 3 golden targets | reference | smart_picker 80% / autofill 100% conformance (0% invalid) / watermark 85% — locked per MVP_ARCH §8.5 |
| ai_ops/prompts/ storage layout | reference | one module per `<workload>_v<version>.py` with TEMPLATE/VERSION/WORKLOAD/RENDERED_BY constants; resolve() dynamic-imports |
| Asia/Kolkata day boundary | reference | _today_kolkata_str() uses zoneinfo("Asia/Kolkata"); 25h TTL on daily keys survives midnight reset |


---

## §8 customer service layer CONSTRUCTED (2026-06-07)

### Scope
Solo sub-session `meesell-backend-construction-8-customer-1` — step 1 of 2 (router lands in api-routes-builder step 2). Built the seller-profile service layer + 5 unit tests + 2 integration tests per §8 (LOCKED 2026-06-05) + master rulings (2026-06-07).

### Files created (8)

Source (6):
- `backend/app/modules/customer/__init__.py` — package shell; router NOT mounted in step 1.
- `backend/app/modules/customer/domain.py` — 4 frozen dataclasses (`SellerProfile`, `ComplianceBlock`, `ProfileCompleteness`, `ComplianceExtensionSpec`) + `COMPLIANCE_EXTENSION_MAP` (11 keys, MappingProxyType wrapped, Beauty's 6 super_ids share ONE Spec instance). Also `BASE_FIELD_NAMES` (10) + `BASE_REQUIRED_FIELDS` (7 blocking).
- `backend/app/modules/customer/exceptions.py` — 6 CustomerError subclasses: `ProfileNotFoundError` (404), `InvalidPincodeError` (422), `InvalidSuperCategoryError` (422), `SuperCategoryNotDeclaredError` (404), `ComplianceExtensionMissingFieldsError` (422), `ProfileIncompleteForCategoryError` (422). 3-segment validation_message_ids per §5A.H.
- `backend/app/modules/customer/schemas.py` — SCAFFOLD: 6 Pydantic v2 models (`SellerProfileResponse`, `PatchProfileRequest`, `PatchActiveCategoriesRequest`, `PatchComplianceExtensionRequest`, `RequiredFieldsResponse`, `ComplianceBlockResponse`). `Field(pattern=r"^\d{6}$")` on all 3 pincode fields.
- `backend/app/modules/customer/repository.py` — 4 module-private async methods (`find_by_user_id`, `upsert`, `update_active_categories`, `update_compliance_extension`). Every method body has a direct `scope_to_user(` call (inlined in `upsert` to be a §19 grep anchor).
- `backend/app/modules/customer/service.py` — 9 PUBLIC async methods per §8.C: `get_profile_or_none`, `get_profile`, `upsert_profile`, `set_active_categories`, `set_compliance_extension`, `get_required_fields`, `get_compliance_block`, `get_onboarding_completeness`, `assert_eligible_for_super_id`.

Tests (2 files in modules/customer + 2 files in integration + 1 conftest):
- `backend/tests/modules/customer/conftest.py` — `db` fixture aliases `db_session` (ephemeral 5432 DB) so unit tests don't need the 5433 tunnel.
- 5 unit tests (29 sub-tests pass).
- 2 integration tests (6 sub-tests pass, both use per-test NullPool engine to dodge cross-loop Future issues).

### Tests added
| File | Sub-tests | Notes |
|---|---|---|
| test_profile_upsert_idempotency.py | 2 | First-PATCH-creates-row + user_id stable across upserts. |
| test_pincode_regex_enforcement.py | 13 | Parametrised over 8 invalid + 3 fields + valid + None. |
| test_compliance_extension_validation_per_super_id.py | 8 | 4 sync MAP shape (11 keys, Beauty shared identity, Grocery/Beauty compulsory, optional supers) + 4 async DB. |
| test_onboarding_complete_flag_recomputation.py | 3 | 6-transition lifecycle + missing-base-field + all-optional-supers. |
| test_eye_serum_case.py | 3 | ComplianceBlock has only 9 LM fields; Beauty seller still stores 9 base; Beauty Spec has no compliance_shape attr. |
| test_customer_full_onboarding_flow.py | 1 | Sign up via OTP → PATCH base → PATCH active['26'] → PATCH compliance/26 → required-fields shows completed=True. |
| test_customer_cross_module_eligibility.py | 5 | assert_eligible_for_super_id under all 5 gate combinations. |

Total: **35 customer tests PASS / 35**.
Regression sweep (227 baseline core+iam+i18n+shared): 227/227 PASS, no regressions.

### Decisions FLAGGED

D1 — **`schemas.RequiredFieldsResponse` uses `list[dict[str, Any]]` not `list[FieldSpec]`.** Pydantic v2 on Python 3.11 rejects `typing.TypedDict` (which `app/i18n/schema_contract.FieldSpec` uses); requires `typing_extensions.TypedDict`. Service-layer `_build_field_spec` constructs each dict with the §5A.C 9-key shape; `tests/test_per_field_shape_keys.py` is the schema-conformance gate. Forward-compat: when Python 3.12 is runtime OR i18n switches to `typing_extensions.TypedDict`, the type can be tightened.

D2 — **`db` fixture in tests/modules/customer/conftest.py aliases `db_session` (5432 ephemeral) NOT the iam-style `db` (5433 tunnel).** Customer unit tests don't need seeded categories (repository helpers bypass the categories.super_id validation). Dev tunnel at 5433 is operator-dependent (SSH session required). iam unit tests keep the 5433 dependency because they exercise tunnel-only paths.

D3 — **Unit + integration tests CANNOT run in the same pytest invocation** against the local 5432 DB because `db_engine` teardown calls `Base.metadata.drop_all`, wiping `audit_events` before integration's `iam_client` teardown tries to DELETE. Run them in separate pytest invocations (the standard CI pattern). Both pass on their own.

D4 — **`repository.upsert` inlines its SELECT** (instead of delegating to `find_by_user_id`) so the §19 grep anchor `scope_to_user(` appears at the call site of every repository mutator method body. Same query plan; explicit grep visibility.

D5 — **6 customer-specific validation_message_ids were ALREADY in messages_en.py** from the §5A construction dispatch. The brief said to "append 6 entries" assuming they weren't there; they were. Verified all 6 keys present, conform to §5A.H regex, and have natural English text.

### Key implementation patterns locked

#### COMPLIANCE_EXTENSION_MAP structure
- `dict[str, ComplianceExtensionSpec]` wrapped in `MappingProxyType` (defensive immutability).
- 11 keys: `26` (Grocery, compulsory=True), `13` (Kids, optional), `16` (Electronics, optional), `19/36/37/14/88/34` (Beauty, compulsory=True, **shared instance** for O(1) lookup), `80` (Books, optional), `30` (Home & Kitchen, optional).
- Beauty `super_id` `"19"` is the canonical anchor; 6 keys all map to the SAME Spec instance (`is` identity verified in tests).
- `required_keys` + `optional_keys` are `tuple[str, ...]` (immutable). `compulsory: bool` drives the gate.

#### `onboarding_complete` recompute algorithm
```python
all(_is_field_present(base_state[name]) for name in BLOCKING_BASE_FIELDS)
AND
for super_id in active_super_categories:
    spec = COMPLIANCE_EXTENSION_MAP.get(super_id)
    if spec and spec.compulsory:
        all(_is_field_present(ext.get(super_id, {}).get(k)) for k in spec.required_keys)
```
- `BLOCKING_BASE_FIELDS` = 6 mandatory LM fields + `country_of_origin` (importer trio is OPTIONAL — does not block).
- Recomputed on every PATCH path (B.2 / B.3 / B.4); written into `seller_profile.onboarding_complete`.
- `ProfileCompleteness.base_total_count` is always 10 (`len(BASE_FIELD_NAMES)`) for UI badge math; blocking gate uses 7.

#### Cache pattern (§8.B.5 /required-fields)
- Logical key: `customer.required_fields.{user_id}`; full key: `meesell:v{cv}:customer.required_fields.{user_id}`.
- TTL: 60s (`_REQUIRED_FIELDS_TTL_SECONDS`).
- Invalidated by `_invalidate_required_fields_cache(user_id)` after every PATCH (B.2/B.3/B.4).
- Drop-on-failure: cache delete failures logged at WARNING, never raise.

#### Cache pattern (categories.super_id distinct set)
- Logical key: `customer.super_category_set` (global; not per-user).
- TTL: 3600s, `single_flight=True` to prevent cold-cache stampede.
- Service-side cache via `core.cache.get_or_set` — `_load_super_id_set` is `SELECT DISTINCT super_id FROM categories ORDER BY super_id`.

#### Cross-loop Future avoidance (integration tests)
- DO NOT use `app.shared.database.AsyncSessionLocal` directly in integration tests that span multiple iam_client requests — the module-level engine's pool attaches to whatever loop first awaits it.
- DO use a per-test NullPool engine: `create_async_engine(DATABASE_URL, poolclass=NullPool)` inside the test body, dispose in `finally`.

#### Test ordering (local dev with 5432 only)
- Unit tests use `db_session` (drops + creates tables fresh).
- Integration tests use `iam_client` against `settings.DATABASE_URL` (5432); assume schema already present.
- Run them in SEPARATE pytest invocations to avoid `db_engine` teardown wiping the integration schema.
- For the integration suite, before the first run: `Base.metadata.create_all` + seed a `Grocery` (super_id='26') Category row.

### Hand-offs queued

- **meesell-api-routes-builder (step 2 of 2)** — `backend/app/modules/customer/router.py` with 5 endpoint handlers per §8.B; main.py `include_router(customer_router)`; update `test_app_boot_integration.py` allowed paths + route count from 11 → 16; refine schemas examples/descriptions for OpenAPI. Service signatures use 3rd-positional `db: AsyncSession`; router handlers should `Depends(get_db)` and forward.
- **§9 category** — replaces my `_get_super_id_set` cached read with a richer category-set service if needed; existing key `customer.super_category_set` is the canonical name.
- **§10 catalog** — `catalog.service.create_product` calls `customer.service.assert_eligible_for_super_id(user_id, super_id, db)` BEFORE creating any row. Raises `ProfileIncompleteForCategoryError` (422 `customer.profile.incomplete_for_category`).
- **§13 dashboard** — `dashboard.service` consumes `customer.service.get_onboarding_completeness(user_id, db)` for the completeness badge.
- **§14 export** — `export.service` consumes `customer.service.get_compliance_block(user_id, db)`; the Eye-Serum collapsed-3-column transformation happens at XLSX-write time only (NOT in customer).
- **§19 import-linter** — register the customer module's repository surface as a §16 boundary: `from app.modules.customer.repository import` MUST NOT appear under any other `app/modules/<other>/`.

### Memory index additions
| Entry | Type | Summary |
|---|---|---|
| §8 customer landed | project | 6 source + 5 unit + 2 integration tests; 35 customer tests + 227 regression PASS |
| COMPLIANCE_EXTENSION_MAP 11 keys | reference | Beauty's 6 super_ids share ONE Spec instance (`is` identity); 6 source rules; MappingProxyType wrapped |
| Beauty Spec compulsory=True | reference | Master ruling 4 — license_registration_number/type/expiry_date block onboarding |
| onboarding_complete recompute | reference | 6+1 base fields blocking AND every compulsory super's required_keys present |
| customer cache keys | reference | `customer.required_fields.{user_id}` TTL 60s; `customer.super_category_set` TTL 3600s single_flight |
| repository scope_to_user invariant | reference | every method body has a direct `scope_to_user(` call (upsert inlines its SELECT) |
| customer test split rule | reference | unit + integration cannot share pytest invocation against 5432 (db_engine drops tables); run separately |
| per-test NullPool engine for integration | reference | DO NOT reuse `app.shared.database.AsyncSessionLocal` across `iam_client` requests — cross-loop Future error |
| customer has no adapter egress | reference | Pure CRUD-against-Postgres + cache reads; no Gemini, MSG91, GCS, Razorpay, LangFuse per §8.H |
| FieldSpec TypedDict workaround | reference | Pydantic v2 + py3.11 rejects typing.TypedDict; use list[dict[str, Any]] until py3.12 or typing_extensions migration |


---

## §9 category services slice CONSTRUCTED (2026-06-07)

### Scope
Sub-session `meesell-backend-construction-9-category-1` — services-builder
slice (api-routes-builder runs in parallel for router.py + schemas.py +
main.py mount).  Built repository + service + exceptions + domain for §9
per BACKEND_ARCHITECTURE.md §9 (LOCKED 2026-06-05).

### Files created (4)
- `backend/app/modules/category/exceptions.py` — `CategoryError` base + 4
  subclasses per §9.G (CategoryNotFoundError 404, FieldEnumNotFoundError 404,
  SuggestQueryInvalidError 400, BrowseQueryInvalidError 400).
- `backend/app/modules/category/domain.py` — 2 frozen dataclasses per §9.F
  (CategoryRow, SuperCategoryInfo).
- `backend/app/modules/category/repository.py` — 7 module-private async
  methods per §9.D.  **No `scope_to_user`** (categories/templates/
  field_enum_values are §4.C global data — §19 linter exempts).
- `backend/app/modules/category/service.py` — 8 PUBLIC async methods per
  §9.C.  Returns plain `dict` payloads (NOT Pydantic shapes — schemas.py
  is owned by api-routes-builder dispatched in parallel).

### Files modified (1)
- `backend/app/core/cache.py` — `prewarm_top_categories` rewritten from V1
  stub to real implementation.  Lazy-imports `app.modules.category.service`
  inside the function to avoid the circular core/→modules/ import.  Uses
  `make_worker_session()` (lifespan ctx has no get_db).  Warms
  category_tree GLOBAL key + schema:{id} for top n categories (taken as
  the first n in canonical (super_id, leaf_name) order for V1; replaced
  with traffic-driven ranking in V1.5).  Failure-mode = try/except per
  step, never blocks boot.

### Tests added (5 unit modules + 3 integration modules)

Unit (`tests/modules/category/`):
- `test_trigram_search_uses_gin_index.py` (2 tests) — EXPLAIN ANALYZE
  asserts Bitmap Index Scan on one of the 3 GIN trgm indexes
  (idx_categories_path_trgm / _leaf_name_trgm / _super_name_trgm shipped
  in migration a1b2c3d4e5f6).  P95 over 100 iterations < 200 ms target.
- `test_schema_fetch_envelope_conformance.py` (4 tests) — 5 random
  category_ids each; 7-key envelope, compliance_shape ∈ {standard,
  collapsed}, total = compulsory + optional, fields[] carry the
  5 §5A.C-derived keys (canonical_name, data_type, primitive, marker,
  is_advanced).
- `test_field_enum_returns_labelled_payload.py` (2 tests) — entries
  carry {canonical, meesho, labels.en}; single-flight dedupe verified
  via monkeypatched call-counter.
- `test_suggest_graceful_fallback_on_budget.py` (2 tests) — covers BOTH
  paths: (a) `BudgetExceededError` raised through `call_gemini` →
  200 + empty + fallback_offered=True, (b) `AIResponse.parsed.
  fallback_offered=True` returned → same.
- `test_suggest_layer2_invalid_id_retry.py` (1 test) — AI returns an
  invalid UUID; service's final-pass guardrail rejects + emits empty
  fallback envelope.

Integration (`tests/integration/`):
- `test_category_smart_picker_to_schema_flow.py` — HTTP /suggest (mocked
  call_gemini) → /{id}/schema (200 + 7-key envelope).
- `test_category_browse_to_schema_flow.py` — HTTP /browse → /{id}/schema.
- `test_category_etag_roundtrip.py` — GET /categories ETag → 304 via
  If-None-Match.

All 3 integration tests pytest.skip on 404 from the category router so
they don't fail when api-routes-builder hasn't shipped router.py yet.
They ERROR on the pre-existing test-infra blocker (audit_events relation
missing on ephemeral test DB) — SAME issue as §8 customer integration
tests (memory D3); separate test-infra dispatch.

### Test counts
- Category unit: **15/15 PASS** (4 pre-existing picker_helpers + 11 new) in 28.4 s.
- Core/cache regression: **5/5 PASS** (`test_prewarm_top_categories_stub_no_raise`
  still passes because the rewritten prewarm catches all exceptions and
  returns).
- Boot regression: **7/7 PASS**.
- Combined: **27/27 PASS**.

### Decisions FLAGGED (NEW)

D1 — **Service returns `dict` payloads (NOT Pydantic models).**  `schemas.py`
is owned by api-routes-builder dispatched IN PARALLEL with this slice.
Returning dicts decouples the service tests from the schema author cycle;
the router does `XxxResponse.model_validate(dict)` at the boundary.  No
double-validation cost — the cache layer JSON-roundtrips already.  When
schemas.py lands the service signatures can be widened to return Pydantic
models without breaking callers (the dict shape == the Pydantic model
shape by construction).

D2 — **`repository.fetch_schema_uncached` merges `templates.compliance_shape`
into the §5A.B envelope at read time.**  The seeded `templates.schema_jsonb`
JSONB carries 6 top-level keys (`fields`, `compulsory_count`,
`optional_count`, `total_count`, `wizard_step_count`, `main_sheet_label`);
the 7th key (`compliance_shape`) lives on the dedicated `templates.
compliance_shape` column for indexability.  The repository SELECTs both
in one JOIN and assembles the 7-key envelope per §5A.B spec.

D3 — **The 4 §9.G validation_message_ids in the dispatch prompt are
2-segment shorthand.**  §5A.H regex locks 3-segment.  Used the canonical
3-segment IDs already shipped by §5A construction
(`category.lookup.not_found`, `category.field_enum.not_found`,
`validation.suggest_q.too_short_or_long`,
`validation.browse.invalid_pagination`).  Same precedent as §7 iam
(memory D2) and §8 customer (memory D5).  ESCALATION QUEUED if master
prefers updating §5A.H to permit 2-segment.

D4 — **Integration tests `pytest.skip` on router 404** so they survive
the parallel api-routes-builder dispatch.  Once the router lands, the
skips fall away and the assertions exercise the HTTP surface end-to-end.

D5 — **`get_commission` returns `Decimal('0.00')` when `commission_pct`
IS NULL** (rather than raising).  The 404 path (no row) still raises
`CategoryNotFoundError`; the NULL-commission row is treated as "no
commission rule seeded yet — pricing service may apply a default at the
call site".  Documented in service docstring; pricing-builder will refine
on §12 dispatch.

### Hand-offs queued

- **meesell-api-routes-builder (parallel)** — service surface returns
  dicts.  Router wraps each in `SuggestResponse.model_validate(payload)`
  (etc.).  For GET /categories: compute `etag_for(json.dumps(payload).
  encode())`; set ETag header; on If-None-Match match return 304.  For
  GET /categories/{id}/schema: same ETag pattern.

- **§10 catalog** — `catalog.service.create_product` calls
  `category.service.assert_category_exists(category_id, db)` BEFORE the
  insert.  `catalog.service.validate_product` calls
  `category.service.fetch_schema(category_id, db)` to retrieve the
  §5A.B envelope.  Both raise `CategoryNotFoundError` (404).

- **§12 pricing** — `pricing.service.calculate_price` calls
  `category.service.get_commission(category_id, db)`.  Returns
  `Decimal` (never None; falls back to `Decimal('0.00')` when
  `commission_pct` is NULL).

- **§8 customer (back-edge)** — `customer.service.set_active_categories`
  already uses a customer-private `_get_super_id_set` distinct read.
  When the api-routes dispatch lands, customer can switch to
  `category.service.list_super_categories(db)` for the canonical
  `SuperCategoryInfo` cross-module type.  The legacy cache key
  `customer.super_category_set` and the new `super_category_list` are
  separate by design (cache keyspace already includes the caller name).

- **§19 import-linter** — register the category module's repository
  surface as a §16 boundary: `from app.modules.category.repository
  import` MUST NOT appear under any other `app/modules/<other>/`.
  `from app.adapters.gemini import` MUST NOT appear under
  `app/modules/category/` (already clean — grep verified).

### Memory index additions
| Entry | Type | Summary |
|---|---|---|
| §9 category services slice 2026-06-07 | project | 4 source + 1 cache.py rewrite + 5 unit (15 tests) + 3 integration; 27 regression PASS |
| category global-data carve-out | reference | repository carries NO `scope_to_user` — §4.C exception listed in `core/tenancy._GLOBAL_TABLES` |
| category cache key inventory | reference | smart_picker (900s) / browse (300s) / category_tree (3600s + ETag) / schema:{id} (3600s + ETag) / field_enum:{id}:{name} (3600s, single_flight=True) / super_category_list (3600s) |
| service returns dict not Pydantic (D1) | reference | service surface dict-typed; router wraps in `.model_validate(payload)` — schemas.py owned by api-routes-builder |
| fetch_schema 7-key envelope merge (D2) | reference | repository SELECTs schema_jsonb + compliance_shape column together; merges into §5A.B 7-key envelope |
| ID normalisation D3 (3-segment) | reference | category IDs use `category.lookup.not_found`/`category.field_enum.not_found` registered in i18n; matches §5A.H regex |
| prewarm_top_categories real impl | reference | lazy-imports category.service from inside the fn (avoids circular); uses `make_worker_session()`; warms tree + top n schemas; try/except per step |
| integration test skip-on-404 (D4) | reference | category integration tests skip when router 404s — survives parallel api-routes-builder dispatch |
| get_commission None→Decimal('0.00') (D5) | reference | no-row → CategoryNotFoundError; row + null commission → 0.00 (pricing applies default at call site) |

## §10 catalog — CONSTRUCTED 2026-06-07 (sub-session 1)

| Memory key | type | content |
| ---------- | ---- | ------- |
| §10 catalog service surface (10 methods) | reference | route-internal: create_product / patch_product / autofill_product / get_preview / soft_delete / get_draft; cross-module: assert_product_ownership / get_product_for_export / list_products / get_validation_summary |
| §10 ProductNotFoundError uniform collapse | reference | repository.find_by_id collapses (non-existent | cross-tenant | soft-deleted) → None; service raises ProductNotFoundError uniformly — no leak between cases |
| §10 plan_guard wiring (D5 — service-level) | reference | create_product: plan_guard("product_count", db=db) FIRST → category.assert_category_exists → customer.assert_eligible_for_super_id → catalog select/create → insert; autofill_product: plan_guard("ai_autofill_hourly") |
| §10 schema-driven validation (D3 — 3-segment IDs) | reference | dispatch through schema field's data_type + primitive + enum_resolver; unknown→`validation.fields.unknown_key`; text_short>100→`validation.{canonical}.too_long`; static enum miss→`validation.{canonical}.invalid_enum_value`; category enum via `category.service.get_field_enum`; multi-violation→first drives validation_message_id, rest in `details: list[str]` |
| §10 product_drafts wrapper (D1 — applied) | reference | draft_jsonb = {"fields": <merged>, "autosave_count": N}; saved_at→last_updated; legacy rows coerce to autosave_count=1; repository._unwrap_draft_payload is the canonical reader |
| §10 audit_mw coalesce regex deviation (D2) | reference | `_AUTOSAVE_PATH = ^/api/v1/products/[0-9a-fA-F-]+/(draft|autosave)/?$` does NOT match `PATCH /products/{id}`; audit row writes per PATCH (no coalescing in V1); §4.G amendment queued — NOT a §10 blocker |
| §10 graceful fallback symmetry | reference | autofill_product handles BOTH `BudgetExceededError` raise AND `AIResponse.parsed.fallback_offered=True` AND empty `parsed.fields` — all 3 → `AutofillResponse(suggestions={}, applied={}, fallback_offered=True)` with HTTP 200 |
| §10 ai_suggestions persistence | reference | overwrite (not merge) per call — each Auto-fill replaces ai_suggestions_jsonb with the full payload; history lives in audit_events |
| §10 autofill confidence default (D4) | reference | _DEFAULT_AUTOFILL_CONFIDENCE=0.9 — above the 0.85 auto-apply floor; emission IS the confidence signal (prompt instructs model to omit unsure fields) |
| §10 default catalog name (D5) | reference | `{user_id_last4_hex}-Drafts-{YYYYMMDD-HHMM}` — uses user_id-last-4 instead of phone-last-4 to avoid hot-path DB read; UX layer may rewrite |
| §10 super_id resolution | reference | _resolve_super_id_for_category(category_id) reads `schema["super_id"]` from category.fetch_schema cache; defensive return None skips the eligibility gate |
| §10 cross-module surface stability | reference | assert_product_ownership / get_product_for_export / list_products / get_validation_summary form the V1.5 gRPC interface per §10.K — the 4 RPCs |
| §10 image/pricing forward-compat | reference | get_preview and get_product_for_export defensively try `from app.modules import image` — empty image_urls/refs when §11 not yet present (parallel-dispatch safe) |

## §11 image — CONSTRUCTED 2026-06-07 (sub-session: meesell-backend-construction-11-image-1)

| Memory key | type | content |
| ---------- | ---- | ------- |
| §11 image service surface (6 methods) | reference | route-internal: upload_image / list_images; cross-module: get_image_urls (catalog) / get_image_bytes (export) / write_precheck_result (Celery worker) / summary (dashboard) — all async, all take db kwarg |
| §11 image repository (7 methods + helper) | reference | insert / find_by_product / find_by_id / find_by_slot / update_precheck_result / soft_delete_by_idx / summarize_by_products; _owned_product_ids_subquery helper applies scope_to_user(select(ProductORM.id), user_id) — §19 grep anchor for tables w/o direct user_id column |
| §11 GCS path locked convention | reference | `meesell-images/{user_id}/{product_id}/{idx}.jpg` — grep-anchored in service._gcs_path_for + reproduced in repository docstrings; tested via stub_gcs_upload call inspection |
| §11 product_images missing soft-delete columns (D1) | reference | MVP_ARCH §2.5 DDL + ORM model lack deleted_at + updated_at; repository workarounds: filter status != 'deleted' (not deleted_at IS NULL); find_by_slot returns any row regardless (DB UNIQUE is real gate); update_precheck_result drops updated_at = NOW(); soft_delete_by_idx writes status='deleted' (internal helper only — no DELETE-image endpoint in V1) |
| §11 ImageUrl __str__ shim (D3) | reference | frozen dataclass ImageUrl carries __str__ returning self.signed_url so catalog.service.get_preview defensive `tuple(str(u) for u in urls)` shim works unchanged; future catalog cleanup may use `.signed_url` |
| §11 Celery task is sync (V1) | reference | @shared_task(name="image.precheck", bind=True, max_retries=2, retry_backoff=True); body uses asyncio.run(_run_precheck_pipeline(...)) for async work; UUIDs serialised to str across JSON boundary |
| §11 watermark budget defensive try (D4) | reference | tasks._check_watermark wraps ai_ops.client.call_gemini in try/except BudgetExceededError even though client catches internally — belt-and-suspenders for §11.K int #2 stub_call_gemini_budget_exceeded raising directly |
| §11 5-step pipeline (AI track) | reference | _check_jpeg (Pillow open + format==JPEG) / _check_color_space (mode → RGB|CMYK|Gray) / _check_resolution (≥1500x1500) / _check_white_background (4-corner 5x5 sample, threshold 235/255) / _check_watermark (Gemini Vision); only the 4 deterministic checks gate final_status="ready" — watermark step informational per §11.J + §6A.F |
| §11 image.precheck.completed audit | reference | _emit_precheck_completed_audit writes AuditEvent direct ORM (entity_type="product_image", entity_id=image_id, metadata_jsonb={precheck_jsonb, final_status, emitted_at}); drops on failure with warning log — same pattern as §6A.D cost_tracker._write_audit_row |
| §11 i18n wording fixes (D5) | reference | validation.image.invalid_format "JPEG and PNG" → "JPEG"; validation.image.invalid_idx "1 and 6" → "1 and 4"; 5 IDs themselves unchanged |
| §11 cross-module backward-compat with §10 | reference | catalog.service.get_preview lines 822-833 defensive integration WORKS UNCHANGED because ImageUrl.__str__ returns signed_url; integration test int #3 covers this contract |
| §11 PrecheckResult.to_jsonb shape | reference | dict with 5 keys + watermark_confidence; deterministic_checks_pass property excludes watermark step (informational) — final_status="ready" iff property True |

## §12 pricing — CONSTRUCTED 2026-06-07 (sub-session: meesell-backend-construction-12-pricing-1)

| Memory key | type | content |
| ---------- | ---- | ------- |
| §12 pricing service surface | reference | route-internal: calculate(user_id, product_id, request, *, db) -> PriceCalcResponse; cross-module (OPTIONAL §13): get_last_calc(user_id, product_id, *, db) -> PricingCalc \| None — V1 dashboard does NOT call this per founder ruling §2 (matrix stays at 8 ✓) |
| §12 P&L locked formula | reference | seller_price = input_cost × (1 + target_margin_pct/100); denom = 1 - commission_pct/100 - (gst_pct/100) × (commission_pct/100); mrp = seller_price / denom; commission_amount = mrp × commission_pct/100; gst_amount = commission_amount × gst_pct/100 (GST charged on commission, not full MRP); meesho_price = mrp; profit = seller_price - input_cost; profit_pct = profit / input_cost × 100; ALL quantize ROUND_HALF_EVEN to 2 dp |
| §12-PRICING-D1 commission missing signal | feedback | category.service.get_commission returns Decimal('0.00') (NOT None) for missing-commission case per Wave 3 LOCKED docstring "NEVER None — pricing service fails over to a default". Pricing treats == 0 as missing-signal and raises CommissionMissingError. Safe in V1 because no legitimately 0% Meesho category exists. **Why**: §9 docstring explicit; **How to apply**: V1.5 if a real 0% category ever lands, widen §9 with separate get_commission_or_none surface |
| §12-PRICING-D2 golden formula vs spec | feedback | §12.J test #3 prose says mrp ≈ 151.52 but formula yields 130 / 0.823 ≈ 157.96. Followed formula; documented in unit test docstring. **Why**: locked formula is the contract; prose golden is spec drafting error. **How to apply**: when spec prose and locked formula diverge, formula wins; assert formula-derived value in tests with D-flag annotation |
| §12-PRICING-D3 3 exception classes per §12.G | reference | PricingError base + InvalidPriceInputError (400 / validation.price.invalid_input) + CommissionMissingError (422 / pricing.commission.missing). Master prompt's "5 classes" count was actually the 5 i18n message_id keys (3 alerts are domain dataclass values per §12.F, NOT exceptions) |
| §12-PRICING-D3a 3-segment ID convention | reference | Use pricing.commission.missing (3-segment) NOT pricing.commission_missing (2-segment shorthand in §12.G prose). §5A.H regex locks 3-segment; i18n/messages_en.py ships 3-segment already. Same precedent as §7 iam D3, §8 customer D5, §9 category D3, §10 catalog D3 |
| §12-PRICING-D4 DDL is the law | feedback | pricing_calcs DDL (Wave 1 LOCKED §5.E ORM) has structured columns: mrp/meesho_price/seller_price/commission_pct/gst_pct/margin/margin_pct/created_at — NOT {user_id, input_jsonb, output_jsonb, calculated_at} per §12.B.1 step 8 prose. **Why**: ORM model docstring explicitly designs tenancy via product→catalog→user FK chain (no user_id column on pricing_calcs). **How to apply**: persist structured columns; tenancy via (a) service-layer assert_product_ownership upstream + (b) repository JOIN through products with Product.user_id == user_id as §16 grep-anchor. margin column = computed profit; margin_pct = computed profit_pct |
| §12 alert thresholds (strict inequalities) | reference | LOW_MARGIN: profit_pct < 10 (warning); HIGH_MRP_MULTIPLIER: mrp / input_cost > 3 (warning); THIN_PROFIT: profit < 50 INR (info). All STRICT — at boundary no alert fires. Multiple can fire (e.g., low margin + thin profit) |
| §12 _generate_alerts pure function | reference | accepts PnLBreakdown + input_cost kwarg; returns list[PricingAlert]; no I/O; defensive input_cost > 0 guard for HIGH_MRP_MULTIPLIER (Pydantic gt=0 should prevent but pure helper can be called directly in unit tests) |
| §12 denom positive guard | reference | _compute_pnl guards against denom <= 0 by raising InvalidPriceInputError ("Commission + GST combine to a non-positive denominator") — defensive for V1.5 override surface; V1 commission ∈ [0,100] and gst=18 keep denom ∈ (0.82, 1.0] |
| §12 append-only audit invariant | reference | pricing_calcs is the audit trail. insert_calc is the ONLY mutator; no UPDATE method on repository. Each calculate() call → new row. Test #2 verifies 3 calcs → 3 rows (commits between calcs in integration test because Postgres NOW() is transaction-bound per D5) |
| §12-PRICING-D5 transaction-bound NOW() in tests | reference | Postgres NOW() = transaction_timestamp() — same for all statements in one tx. Test that asserts ordering of multiple INSERTs must commit between calls + sleep(0.01) to get distinct created_at. Production reality: each HTTP request = own tx → distinct NOW() automatically |
| §12 cross-module import allowlist | reference | service.py imports: catalog.service (assert_product_ownership) + category.service (get_commission). NO catalog.repository, NO category.repository, NO adapters.gemini, NO ai_ops.client, NO Razorpay/MSG91/GCS. Pricing is deterministic math per §12.H. shared.models.product is permitted (ORM is cross-module per §16 — only repository is module-private) |
| §12 latent bug §0.E RESOLVED | project | DELETE backend/app/services/pricing_engine.py FIRST per §12.A (verified zero importers via grep before deletion); new modules/pricing/{7 files} replaces it cleanly; new PricingAlert in modules/pricing/domain.py replaces deleted legacy schemas/pricing.PricingAlert; boot-smoke green after rm. L1 latent retired |
| §12 NO Celery tasks | reference | NO tasks.py in pricing subtree (unlike §11 image which has tasks.py for precheck pipeline). Pricing is synchronous — math is sub-millisecond; sellers tweak target_margin_pct interactively |
| §12 V1.5 forward-compat | reference | PriceCalcRequest carries override_commission_pct + override_gst_pct as Optional V1.5+ fields. V1 IGNORES them (service uses category-resolved commission + DEFAULT_GST_PCT=18). V1.5 Pro-tier may honor them — schema doesn't break |
| §12 incidental §11 cleanup | reference | §11 image dispatch left test_app_boot_integration.py out of sync (image router was mounted but allowed_paths/expected_count not updated). Folded the fix into §12: added /api/v1/products/{id}/images to allowed_paths + bumped expected_count 25 → 27 (+1 image +1 pricing). No behavior change to image module |

## §13 dashboard — CONSTRUCTED 2026-06-07 (sub-session: meesell-backend-construction-13-dashboard-1)

| Memory key | type | content |
| ---------- | ---- | ------- |
| §13 dashboard service surface | reference | ONE public method: `list_products_for_dashboard(user_id, query: DashboardQuery, db: AsyncSession) -> DashboardResponse`. ONE private pure function: `_compose_response(*, paginated: PaginatedProductsInternal, completeness: ProfileCompleteness) -> DashboardResponse`. No other public methods — dashboard is a leaf consumer on §2.D matrix (no producer surface) |
| §13 cross-module calls (exactly 2) | reference | catalog.service.list_products(user_id, pagination, db) per §16.B row 6; customer.service.get_onboarding_completeness(user_id, db) per §16.B row 7. NO other module calls (matrix kept at 8 ✓ for V1; V1.5 may elevate to 11 ✓ for image/pricing/export summary() opt-ins) |
| §13 NO repository.py (structural) | reference | dashboard subtree has 5 source files: __init__, router, service, schemas, domain (empty body), exceptions. Absent repository.py is intentional design per §13.D + §3.C deviation. Tenancy enforced upstream at catalog.repository (§10.D) + customer.repository (§8.D) — dashboard never sees raw SQL |
| §13-DASHBOARD-D3 amendment §13.A.1 filter/search → V1.5 | feedback | Founder ruling 2026-06-07 deferred status_filter + search query params to V1.5. ProductListItem.status narrowed from Literal["draft","ready","exported"] to Literal["draft","ready"]. DashboardQuery shrinks from 4 fields to 2. **Why**: catalog.Pagination is locked at (page, limit) only; status_filter+search would require §10 catalog amendment, plus "exported" status would need either exports table JOIN or denormalised is_exported on products. Day-1 sellers (0-5 products in Tirupur) don't need filter/search; V1.5 ships with catalog Pagination extension. **How to apply**: V1 ships `page`+`limit` only; V1.5 lifts §13.A.1, restores 4-field query, restores 3-value status Literal, requires concurrent §10 catalog amendment |
| §13-DASHBOARD-D4 dashboard.domain.Pagination reuses catalog's | feedback | Post-amendment, dashboard's local Pagination would be identical to catalog.domain.Pagination (page, limit only). To avoid duplication, dashboard.service imports catalog.domain.Pagination directly. Permitted by §16 Rule 4 (domain.py is cross-module exchange currency for types in public service signatures). dashboard/domain.py is empty body — kept for §3.C canonical subtree completeness. **Why**: V1 amendment makes the shapes identical; **How to apply**: don't duplicate the dataclass; import the producer's type |
| §13-DASHBOARD-D5 _compose_response purity | reference | Pure function — no I/O, no DB, no await, no clock reads, no randomness. Maps catalog.Product → ProductListItem (renames .id → .product_id) and customer.ProfileCompleteness → ProfileCompletenessSummary (1:1). Tested in isolation via test_response_composition.TestComposeResponsePure (deterministic outputs for given inputs). Separates composition from orchestration so service-level unit tests don't need to mock both consumed services to test the shape |
| §13 stub_consumed_services fixture pattern | reference | Patch the dashboard service module's BOUND imports: `dashboard_service_module.catalog_service.list_products` + `.customer_service.get_onboarding_completeness` via monkeypatch. The aliases are bound at import time (`from app.modules.catalog import service as catalog_service`), so the patch lands on the consumer's namespace and the stubs reach the service. Returns a `configure(items, total, completeness)` callable for per-test shaping. Tracks call args in `state["calls"]` for forward-verification |
| §13 empty inventory → 200 not 404 | reference | First-time seller with zero products → service returns DashboardResponse(products=[], total=0, page, limit, onboarding_completeness=ProfileCompleteness(0,10,0,0, False)). §8 customer.get_onboarding_completeness no-profile branch returns the zero shape (NOT raises). §13.B status code lock — empty inventory is a valid 200, NOT 404 |
| §13 ProductListItem.status narrowing safety | reference | After §13.A.1 amendment, ProductListItem.status = Literal["draft","ready"] matches catalog.domain.Product.status exactly. Pydantic validates the value on construction — if catalog ever emits an unexpected status the response builder will raise pydantic.ValidationError → 500 via §4.F. Acts as a structural guard against future catalog.Product.status widening that forgets to update dashboard |
| §13 integration tests pattern (§12 precedent) | reference | Service-level integration: seed user + seller_profile + products via ORM directly (bypassing §10 catalog.create_product to avoid §8 eligibility setup); invoke dashboard.service.list_products_for_dashboard; assert response shape. HTTP-level coverage delegated to §15 contract suite. Uses db_session + use_live_valkey fixtures. Phone prefix +9155500XXXXX for cleanup convention |
| §13 template parser_version VARCHAR(8) constraint | reference | shared.models.template.Template.parser_version is mapped_column(String(8)) — strict 8 character cap. Test fixtures must use short codes like "dash1.0", NOT "dashboard-integ-1.0". Same constraint applies to ANY integration test that seeds templates directly (precedent for other constructors) |
| §13 sample_products fixture: status passthrough | reference | sample_products fixture builds 3 frozen Product instances with status sequence [ready, draft, draft]. Used by test_response_composition + test_empty_state to verify status_passthrough without mocking the entire catalog service |
| §13 no AI Ops integration | reference | dashboard imports nothing from app.ai_ops, app.adapters, or app.ai_ops.client. Zero vendor egress per §13.H. P95 ≤ 200ms budget per §1.E is structurally honored — no third-party round-trips to absorb the latency. Cache helper NOT participating (high write churn from product PATCH would tank hit rate per §13.I) |

## §14 export — CONSTRUCTED 2026-06-08 (sub-session: meesell-backend-construction-14-export-1)

Heavy-lift slice. Authored 6 source files + 10 unit test modules (33 sub-tests) + 3 integration tests + 15-fixture JSON corpus + fixture runner (17 sub-tests). Celery `include=` populated. All 64 export tests + 8 boot-smoke + 200 Wave 1–5 regression tests PASS. Ruff clean. M10 boundary holds.

| Memory key | type | content |
| ---------- | ---- | ------- |
| §14 export service surface (3 public + 1 cross-module + 10 worker-internal) | reference | public: initiate_export(user_id, product_id, request, db) → ExportInitiatedResponse; get_export(user_id, export_id, db) → ExportResponse. cross-module (V1 unused): summary(user_id, product_ids, db) → dict[UUID, ExportStatusSummary]. worker-internal: _run_export_pipeline + 9 named step helpers (_resolve_schema, _select_strategy, _build_row, _apply_strategy, _translate_enums, _reorder_columns, _restore_aliases, _write_xlsx, _round_trip_validate, _package_images_zip). Router calls accept db positionally — service signatures match router's `await service.initiate_export(user_id=..., db=db)` convention |
| §14 export repository (5 methods) | reference | insert / find_by_id / update_status_ready / update_status_failed / summarize_by_products. All async. All use scope_to_user(user_id) directly on ExportORM (§19 grep anchor). _orm_to_domain helper applies the D1-D4 derivations (initiated_at←created_at; completed_at→None; format derived from zip_gcs_path or pending hint; error_code parsed from error_message prefix; round_trip_validated=True when status='ready') |
| §14-EXPORT-D1 DDL no initiated_at/completed_at/updated_at | feedback | exports DDL ships with only `created_at`. Map: API initiated_at ← DDL created_at; API completed_at = None always. update_status_ready/failed signatures keep completed_at param for forward-compat but DROP it at SQL layer. **Why**: Wave 1 DDL is fixed; protocol §5.0 forbids sub-session migrations. **How to apply**: V1.5 migration adds initiated_at + completed_at columns; remove `del completed_at` lines |
| §14-EXPORT-D2 DDL no format column | feedback | DDL has no format column. Pipeline carries format in Celery payload. API GET derives format from zip_gcs_path (NOT NULL → xlsx_with_images; NULL → xlsx_only). For pending rows, service writes Valkey DB 0 key `export:format:{export_id}` 10-min TTL on insert; API reads for pending-window cosmetic accuracy. **Why**: format MUST round-trip in the API contract but the DDL is fixed. **How to apply**: V1.5 migration adds format column; remove the Valkey hint |
| §14-EXPORT-D3 DDL no error_code column | feedback | DDL has no error_code column. update_status_failed concatenates `f"[{code}] {message}"` into the existing error_message column. API GET parses the bracketed prefix back. 4 codes: enum_validation_failed / compliance_strategy_failed / xlsx_build_failed / round_trip_mismatch (per §14.H). _parse_error_code helper is defensive against malformed prefixes. **Why**: §14.B.2 wire contract requires error_code; DDL doesn't support it. **How to apply**: V1.5 migration adds error_code; update_status_failed switches to writing both columns |
| §14-EXPORT-D4 round_trip_validated implied TRUE | feedback | DDL has no boolean column. Per MVP_ARCH §5.7, status='ready' invariant requires round-trip pass (else pipeline raises RoundTripValidationError → status='failed'). _orm_to_domain returns round_trip_validated=True iff status='ready', None otherwise. **Why**: contract derivation removes a column. **How to apply**: no migration needed for V1.5 unless we want to record the diagnostic from RoundTripResult |
| §14-EXPORT-D5 status='pending' explicit override | reference | DDL status server_default = 'processing' but §14 uses 'pending'. repository.insert() passes status='pending' explicitly to override server_default. Status transitions only pending→ready OR pending→failed; legacy 'processing' never written by this module |
| §14-EXPORT-D6 download_url column vestigial | reference | DDL ships `download_url TEXT` column that §14.B.2 doesn't use (signed URLs generated fresh per response per §6.D). Module leaves it NULL; never reads/writes |
| §14-EXPORT-D7 alias restoration is RUNTIME NO-OP | feedback | §14.C step 7 spec mentions `category.service.fetch_xlsx_aliases(category_id)` but §16.B.1 locks export's category surface at fetch_schema + get_field_enum only. RESOLUTION: meesho_column_header is sourced from schema["fields"][i].meesho_column_header in _build_row directly. Seed pipeline (per MVP_ARCH §3) pre-embeds typo-preserved headers in templates.schema_jsonb.fields[*].meesho_column_header. field_aliases.for_xlsx_export=TRUE is consumed at SEED time only; runtime does NOT query that table. _restore_aliases is retained as explicit no-op so §14.C 9-step contract is structurally honored. **Why**: avoids cross-module surface widening; seed embedding makes runtime restoration redundant. **How to apply**: when V2 marketplaces diverge from seed-embedded headers, _restore_aliases is the insertion point |
| §14-EXPORT-D8 Celery task name + retry locks | reference | @shared_task(name="export.xlsx", bind=True, max_retries=1, retry_backoff=True) per §14.E locked. Master prompt's "export.generate"/max_retries=2 was non-normative drift; §14.E line 5427 governs |
| §14-EXPORT-D9 GCS paths LOCKED | reference | XLSX: `meesell-exports/{user_id}/{export_id}/sheet.xlsx`; ZIP: `meesell-exports/{user_id}/{export_id}/images.zip` per §14.I. NOT `{export_id}.xlsx` (drift). Grep-anchored in service.py + integration test asserts the exact path |
| §14-EXPORT-D10 exception class names LOCKED | reference | ProductNotReadyForExportError (NOT ProductNotReadyError), RoundTripValidationError (NOT RoundTripMismatchError) per §14.H |
| §14-EXPORT-D11 3-segment ID normalisation | feedback | §14.H prose lists 2-segment shorthand (export.not_found, export.product_not_ready, etc.). i18n/messages_en.py already ships canonical 3-segment IDs from §5A construction (export.lookup.not_found, export.product.not_ready, export.front_image.missing, export.enum.validation_failed, export.compliance.strategy_failed, export.xlsx.build_failed, export.round_trip.mismatch). Exception classes wire to the canonical 3-segment IDs. Same precedent as §7 D2, §8 D5, §9 D3, §10 D3, §11 D2, §12 D3a. **Why**: §5A.H regex requires 3-segment; spec prose is shorthand. **How to apply**: every new module's validation_message_id MUST conform to §5A.H regex regardless of how the spec text inlines them |
| §14-EXPORT-D12 MeeshoExportAdapter is V2 seam | feedback | Domain ships MarketplaceExportAdapter ABC + V1 concrete MeeshoExportAdapter, but the V1 pipeline runs through service._run_export_pipeline directly (invoked by Celery task). MeeshoExportAdapter.export raises NotImplementedError in V1 — kept as future-proofing seam for V2 multi-marketplace per §14.L. **Why**: pipeline-as-service-helpers makes per-step unit testing simpler than adapter-method orchestration. **How to apply**: V2 expansion populates the body + shifts Celery dispatch through the adapter |
| §14 Celery enqueue pattern | reference | service.initiate_export calls `export_xlsx_task.delay(str(export.id), str(user_id))` — same pattern as §11 image.service. Avoids importing `app.workers.celery_app` at request time (the celery_app singleton reads `settings.CELERY_BROKER_URL` which is a PRE-EXISTING config gap — env var supplies value to Celery but Settings model doesn't expose the field). Task name binding preserved at @shared_task decorator. **TBD V1.5:** add CELERY_BROKER_URL/CELERY_RESULT_BACKEND to shared/config.py Settings |
| §14 cross-module call sites | reference | service.py imports: catalog.service (assert_product_ownership + get_product_for_export), customer.service (get_compliance_block), category.service (fetch_schema + get_field_enum), image.service (list_images). NO repository imports across module boundaries per §16. NO ai_ops/adapters imports except adapters.gcs (the one egress) |
| §14 Layer 3 hallucination guardrail | reference | _translate_enums looks up each column's canonical value in field_enum_values.enum_entries via category.service.get_field_enum. Unknown canonical → ExportEnumValidationError (500 / export.enum.validation_failed). FieldEnumNotFoundError + CategoryNotFoundError = "not an enum field" pass-through. Empty/None values bypass the lookup (no false enum rejection on optional empty fields). Single point of structural F3 enforcement (philosophy "never send invalid enum to Meesho") — the deterministic safety net under AI Layers 1+2 in §6A.E |
| §14 StandardComplianceStrategy NON-pollution rule | reference | _apply_strategy with StandardComplianceStrategy ONLY replaces existing compliance columns (by canonical_name match); does NOT append compliance canonicals that aren't in the schema. Schema is authoritative column inventory per §5A.B + §14.K fixture 1 (saree schema has 3 fields, NOT 9 LM fields). Strategy itself emits 9 columns (unit-testable via strategy.apply); the merge logic decides which to keep |
| §14 CollapsedComplianceStrategy ", " separator + drop-empties | reference | concatenate (name, address, pincode) with ", " separator; drop empty + whitespace-only entries before join (`if not str(raw).strip(): continue`). All-None triple → empty string (not "None, None, None"). Default headers "Manufacturer Details" / "Packer Details" / "Importer Details" overridable via schema column_header_map. Filters the 9 LM canonicals from row.columns + appends 3 derived columns |
| §14 round-trip validator comparison rules | reference | compares header row (strict) + data row (via str() to tolerate int/float/Decimal round-trip). XLSX coerces "" to None on read → both expected and parsed normalised to "" via `"" if x is None else x`. RoundTripResult.mismatches reports canonical_name strings (seller-friendly); diagnostic carries the prose summary used for the error_message |
| §14 15-fixture runner pattern | reference | tests/integration/golden_round_trip/fixture_NN_<name>.json files + test_golden_fixtures_runner.py iterator. Each fixture: input_snapshot + schema + expected_xlsx_canonical (+ optional enum_payloads). Runner reconstructs XlsxRowSpec from expected_xlsx_canonical + schema headers → _write_xlsx → _round_trip_validate. Parametrised over all 15 fixtures + extra parametrised enum-translation pass for the 2 enum-bearing fixtures (9 + 10). 17 sub-tests total. test_fixture_count_is_exactly_15 locks the matrix size |
| §14 mock-stub conftest pattern | reference | stub_cross_module fixture monkeypatches BOUND imports inside service.py (catalog_service.assert_product_ownership, .get_product_for_export, customer_service.get_compliance_block, category_service.fetch_schema, .get_field_enum, image_service.list_images) — same pattern as §13 dashboard. Returns a `configure(*, snapshot, compliance, schema, enum_payloads, enum_raises, images, ownership_raises)` callable. stub_gcs patches the 3 gcs_adapter methods. stub_celery patches export_xlsx_task.delay (NOT celery_app.send_task) per the D8 enqueue switch |
| §14 worker session pattern | reference | _run_export_pipeline opens its own `async with make_worker_session() as db:` (Celery has no request scope). _persist_failure uses its OWN second worker session so a failure during the main pipeline session doesn't poison the failure-persistence write. Both call await db.commit() explicitly (no get_db autocommit) |
| §14 tests outcome | reference | 10 unit modules (33 sub-tests) + 3 integration (4 sub-tests) + 1 fixture runner (17 sub-tests) + 9 router tests (api-routes-builder parallel) = 63 export tests + 8 boot smoke + 200 Wave 1-5 regression = 271 PASS, 0 fail. Ruff clean on all authored files |
| §14 hand-offs queued | reference | (a) §18 celery_app.py include= already populated for export — partial complete. (b) §19 Contract 9 AST scanner — verify M10 boundary holds (only allowed hits: app/modules/export/ + app/adapters/gcs.py + app/shared/models/template.py docstring example). (c) §18 settings: add CELERY_BROKER_URL/CELERY_RESULT_BACKEND fields to shared/config.py Settings (pre-existing gap; env var supplies celery_app.py value but Settings model doesn't expose). (d) DB migration V1.5: add initiated_at/completed_at/format/error_code/round_trip_validated columns to exports table (D1-D4 unwind); when columns land, remove the `del` statements in repository.py and the Valkey hint in service.py |


---

## §18 Celery wiring CONSTRUCTED (2026-06-08)

### Scope
Sub-session `meesell-backend-construction-18-celery-1`.  Solo dispatch.
§18 = the operational glue layer that lets the 2 V1 Celery tasks
(image.precheck + export.xlsx) run reliably: Valkey wiring, worker
invariants, task registration, worker JWT re-validation.

### Files modified (1)
- `backend/app/workers/celery_app.py` — full rewrite from 40 LOC →
  241 LOC.
  - §18.E: BROKER_URL + RESULT_BACKEND_URL derived from
    `settings.VALKEY_URL` via local `_build_url_for_db` helper
    (mirrors `shared.valkey._build_url_for_db`; equivalence guarded by
    `tests.test_celery_broker_db.test_broker_db_matches_shared_valkey_helper`).
  - §18.B: `include=["app.modules.image.tasks", "app.modules.export.tasks"]`
    — exactly 2 V1 modules, no V0 leftovers.
  - §18.G: `task_reject_on_worker_lost=True` preserved (session 2 G3 lock).
  - §18.F: `task_prerun` signal handler scoped to
    `{image.precheck, export.xlsx}` whitelist.  Re-validates `user_id`
    via SELECT-by-id existence check against `users` table; raises
    `Reject(requeue=False)` on miss.  Fails OPEN on transient DB error.

### Files deleted (1)
- `backend/app/workers/generation_tasks.py` — V0 leftover (catalog.generate
  + sku.regenerate decorators).  Deleted in session 2 final purge,
  accidentally restored, re-deleted here.  workers/ now matches §3.I
  canonical 2-file subtree.

### Files modified (test infra, 2)
- `backend/tests/conftest.py` — removed `CELERY_BROKER_URL` +
  `CELERY_RESULT_BACKEND` env-var defaults (was `/11` + `/12`).  Celery's
  env-var resolution order (`os.environ.get('CELERY_BROKER_URL') or
  self.first(...)`) hijacked the `Celery(broker=...)` constructor arg
  and silently broke the §18.E lock.  Replaced with defensive
  `os.environ.pop()` calls.  No test consumed these values functionally.
- `backend/tests/test_worker_db_isolation.py` — removed test #4
  (`test_generation_tasks_use_make_worker_session`) which referenced the
  deleted module.  RETIRED banner in its place.  Also removed unused
  `import pytest` (ruff F401, pre-existing).

### Tests added (5 modules, 26 sub-tests, all PASS)
- `tests/test_celery_app_include_list.py` (4) — include-list exact match,
  V0-forbidden negative, V1 tasks discoverable at boot via
  `loader.import_default_modules()`, only-2-V1-tasks cardinality.
- `tests/test_celery_broker_db.py` (4) — broker path /1,
  endswith('/1'), redis scheme, equivalence with
  `shared.valkey._build_url_for_db`.
- `tests/test_celery_result_backend_db.py` (4) — result path /2,
  endswith('/2'), redis scheme, broker+result share host:port diff DB.
- `tests/test_task_reject_on_worker_lost.py` (5) —
  `task_reject_on_worker_lost=True`, companion `task_acks_late=True`,
  `worker_prefetch_multiplier=1`, JSON serialisation locked,
  `Asia/Kolkata` timezone.
- `tests/test_worker_user_revalidation.py` (9) — filter discipline
  (non-V1 task no-op), missing-user → `Reject(requeue=False)` for both
  V1 tasks, existing-user passthrough, kwarg extraction, malformed
  user_id rejected, DB-error fail-open, no-user_id no-op, whitelist
  cardinality.

### Decisions FLAGGED (D-flag log — not in locked architecture)
**D1 — VALKEY_URL → broker_url + result_backend derivation (§18.E).**
The §14 hand-off said *"add CELERY_BROKER_URL/CELERY_RESULT_BACKEND
fields to shared/config.py Settings"*; §18 chose VALKEY_URL derivation
per the §18.E explicit lock instead.  Avoids 2 new Settings fields +
matches §5.C factory allocation discipline.  Settings cleanup of the
hand-off-suggested fields NOT REQUIRED.

**D2 — §18.F enforcement layer = task_prerun signal handler, not
in-task call.**
§18.F LOCKED prose specifies `_validate_user_or_abort` lives inside
each `tasks.py`.  The §11.E + §14.E LOCKED CONSTRUCTED tasks.py files
do NOT include the call — adding it would breach §5.0 NON-NEGOTIABLE.
§18 enforces at the worker layer via a Celery `task_prerun` signal
handler scoped to the 2 V1 task names.  Same observable invariant;
LOCKED §11/§14 code untouched.

**D3 — V1 User model has NO `disabled` / `deleted_at` columns.**
§18.F prose mentions both conditions; V1 reduces to SELECT-by-id
existence check.  V1.5 ships soft-delete columns; the prerun handler
extends to `WHERE id=$1 AND disabled=False AND deleted_at IS NULL`
without a §18 amendment.

**D4 — Workers env-var pollution cleanup (conftest.py).**
Tests/conftest.py previously set `CELERY_BROKER_URL=/11` +
`CELERY_RESULT_BACKEND=/12` to avoid accidental GCP worker pickup;
Celery's env-var resolution order hijacked the §18.E lock.  Defensive
`os.environ.pop` replaces the `setdefault` calls.

**D5 — Local `_build_url_for_db` helper duplicates `shared.valkey`
copy.**
Rationale: avoid an import cycle between `workers/` and
`shared/valkey` + Celery wants URL strings not Redis clients.  Two
helpers are equivalence-tested.

**D6 — V1 `_user_exists_sync` fails OPEN on DB transient error.**
Spec §18.F doesn't prescribe behaviour on DB outage; we favour
task-body retry (the standard error path) over hard reject (which
loses an audit trail of WHY).  Tested.

**D7 — Whitelist hard-coded to `{image.precheck, export.xlsx}`.**
Adding a 3rd entry silently expands §18.F enforcement to a task that
hasn't been audited for the `(entity_id, user_id)` positional contract.
Tested.

### Acceptance gate (7 dispatch-brief criteria)
1. include list exactly `[image.tasks, export.tasks]`              — PASS
2. broker /1; result_backend /2                                    — PASS
3. `task_reject_on_worker_lost=True` preserved                     — PASS
4. Worker user re-validation implemented + tested (9 sub-tests)   — PASS
5. image.precheck + export.xlsx discoverable at boot              — PASS
6. Failure mode wiring (deferred to §11.E + §14.E ownership)      — PASS
7. 5 unit-test modules with 5+ sub-tests (delivered 5 mods/26 subs)— PASS

Plus universal: boot smoke PASS (34 routes); ruff clean on all 7
touched files; §18 regression 26/26 PASS; Wave 1-3 cross-cutting
regression 230 PASS + 3 PRE-EXISTING failures (test_worker_db_isolation
test #2 / test #3 / test #5 reference V0 `app/database.py` broken
import + `async_session_maker` legacy name — predate §18).

### Latent bugs CLOSED in this sub-session
**L18.1 — `settings.CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND`
non-existent.**  Settings fields broke celery_app.py boot
(AttributeError at import).  CLOSED by VALKEY_URL derivation per §18.E.
The §14 hand-off entry "§18 settings: add CELERY_BROKER_URL/
CELERY_RESULT_BACKEND fields" is now SUPERSEDED — V1 uses VALKEY_URL
derivation; no Settings fields needed.

**L18.2 — workers/generation_tasks.py V0 leftover.**  Violated §3.I
canonical 2-file subtree.  CLOSED by deletion.

### Hand-offs queued
- **§19 test infrastructure**: V0-rot cleanup backlog includes
  `test_worker_db_isolation.py` 3 PRE-EXISTING failures (V0
  `app/database.py` with broken `from app.config import settings`
  import; legacy `async_session_maker` references vs V1
  `AsyncSessionLocal`; V0 `app/services/image_processor.run_pipeline`).
  Out of §18 scope; not a regression.
- **§20 deployment (Celery worker pod manifests)**: consume the locked
  `BROKER_URL` / `RESULT_BACKEND_URL` string-form invariants — broker
  on `/1`, results on `/2`; single Valkey instance.  Worker pod
  replica count per §18.C (image: 2 pods × concurrency=4 = 8 max) +
  §18.D (export: 2 pods × concurrency=2 = 4 max).  §20 picks whether
  to separate worker pools (4 total worker pods, 2 per queue) OR mix
  (2 pods × concurrency=4 with prefetch=1 for fairness).
- **V1.5 User model migration**: add `disabled BOOL DEFAULT false`,
  `deleted_at TIMESTAMPTZ NULL`.  The §18.F task_prerun handler
  extends to `WHERE id=$1 AND disabled=False AND deleted_at IS NULL`
  without requiring a §18 amendment.
- **API routes builder**: the §14 `service.initiate_export` enqueue
  pattern was `export_xlsx_task.delay(str(export.id), str(user_id))`.
  §18 confirms this is the correct pattern; no settings change needed.

### Memory index additions
| Entry | Type | Summary |
|---|---|---|
| §18 Celery wiring CONSTRUCTED | project | celery_app.py rewritten 40→241 LOC; broker/result derive from VALKEY_URL via local _build_url_for_db; task_prerun signal handler enforces §18.F user re-validation without touching LOCKED §11/§14 tasks.py |
| §18-CELERY-D1 VALKEY_URL derivation | reference | broker = _build_url_for_db(settings.VALKEY_URL, 1); result_backend = _build_url_for_db(settings.VALKEY_URL, 2). NO CELERY_BROKER_URL/CELERY_RESULT_BACKEND Settings fields needed |
| §18-CELERY-D2 task_prerun signal handler | reference | @task_prerun.connect handler in workers/celery_app.py filters to {image.precheck, export.xlsx} whitelist; raises Reject(requeue=False) on missing user. §11/§14 LOCKED tasks.py NOT modified |
| §18-CELERY-D3 User model V1 fields | reference | V1 User has only (id, phone, email, plan, created_at, last_login_at). No disabled/deleted_at — V1.5 adds those + handler extension is forward-compat |
| §18-CELERY-D4 conftest env-var pollution | reference | tests/conftest.py CELERY_BROKER_URL=/11 + CELERY_RESULT_BACKEND=/12 setdefault calls REMOVED (replaced with os.environ.pop). Celery env-var resolution hijacked broker= constructor arg |
| §18-CELERY-D5 _build_url_for_db duplication | reference | Local copy in workers/celery_app.py mirrors shared.valkey copy; avoids import cycle + Celery wants URL strings. Equivalence guarded by test_broker_db_matches_shared_valkey_helper |
| §18-CELERY-D6 fail-open on transient DB error | reference | _user_exists_sync returns True on RuntimeError in _user_exists_async; task body retries via repo layer + Celery autoretry. §18.F observability rule |
| §18-CELERY-D7 whitelist cardinality lock | reference | _TASKS_REQUIRING_USER_REVALIDATION = frozenset({"image.precheck", "export.xlsx"}). Adding a 3rd entry silently expands enforcement; tested |
| Workers §3.I subtree | reference | workers/ MUST contain exactly __init__.py + celery_app.py. generation_tasks.py / image_tasks.py / scrape_tasks.py are all V0 leftovers; deletion is the correct cleanup |
| Celery env-var resolution order | reference | os.environ.get('CELERY_BROKER_URL') wins over Celery(broker=...) constructor arg. Document at celery/app/utils.py:103. Tests/conftest MUST NOT set these env vars or §18.E lock is silently bypassed |
| V0 pre-existing rot (V0 path scan) | reference | app/database.py exists with broken `from app.config import settings` import; legacy app.services.image_processor.run_pipeline still references async_session_maker. test_worker_db_isolation.py test #2/#3/#5 fail because of this. Out of §18 scope; §19 V0 cleanup backlog |
| §18 hand-offs | reference | §20 worker pod manifests consume BROKER_URL/RESULT_BACKEND_URL invariants; V1.5 User migration adds disabled+deleted_at columns (handler is forward-compat); §14 enqueue pattern `export_xlsx_task.delay(str(export.id), str(user_id))` confirmed |

---

## F-15-1 export worker terminal audit rows IMPLEMENTED (2026-06-09)

### Scope
Micro-task. Founder ruled Option A (implement, not V1.5-defer). Touched ONLY
`backend/app/modules/export/tasks.py`. No commit. Branch
`claude/meesell-project-setup-Tl7DS`. BACKEND_ARCHITECTURE.md untouched (§5.0).

### Defect (from §15/§22 audit, MEDIUM)
`export/tasks.py` docstring lines 15-18 CLAIMED audit writes for
`export.completed`/`export.failed` were "embedded in the service-level pipeline"
(`_run_export_pipeline`), but ZERO `AuditEvent(event_type="export.*")` calls
existed anywhere in the export module. False claim → MEDIUM defect F-15-1.

### What I did
- Added imports mirroring image/tasks.py: `from datetime import datetime, timezone`,
  `from sqlalchemy.exc import SQLAlchemyError`,
  `from app.shared.database import AsyncSessionLocal`,
  `from app.shared.models.audit_event import AuditEvent`.
- New async helper `_emit_export_terminal_audit(*, user_id, export_id, event_type,
  error)` — byte-for-byte same pattern as
  `image/tasks.py:_emit_precheck_completed_audit` (own `AsyncSessionLocal()`
  session, `session.add(row)` + `await session.commit()`, drop-on-failure via
  `except (SQLAlchemyError, Exception) as exc: logger.warning(...)`).
- `export.completed` written at terminal SUCCESS (after
  `asyncio.run(_run_export_pipeline(...))` returns, before the return dict).
- `export.failed` written at terminal FAILURE — GATED on
  `self.request.retries >= self.max_retries` so it fires ONCE on the final
  retries-exhausted attempt. Transient first-attempt failures that later succeed
  record only `export.completed`. Written BEFORE `raise self.retry(exc=exc)`.
- Task body is SYNC (`@shared_task`, not async) so the helper is invoked via
  `asyncio.run(_emit_export_terminal_audit(...))` (same as the pipeline call).
- Corrected docstring lines 15-18 to state writes are in the worker task.
- `__all__` now exports `_emit_export_terminal_audit` for unit tests.

### AuditEvent field shape (LOCKED — confirmed from shared/models/audit_event.py)
Constructor kwargs used: `user_id` (UUID, FK RESTRICT), `event_type` (String(40)),
`entity_type` (String(20), nullable), `entity_id` (UUID, nullable), `diff_jsonb`
(JSONB, nullable — None here), `metadata_jsonb` (JSONB, nullable — carries
`export_id`/`emitted_at`/optional `error`). `id` is BIGSERIAL Identity(always)
— do NOT set. `occurred_at` server_default NOW() — do NOT set.
For export terminal events: entity_type="export", entity_id=exports.id.

### Pattern locked (reusable for any worker terminal audit)
Workers have NO request-close hook → audit_mw post-commit path cannot fire →
every Celery terminal event needs a DIRECT `AuditEvent(...)` write in its own
`AsyncSessionLocal()` session, drop-on-failure with WARNING. Canonical reference:
`image/tasks.py:370-409`. The `metadata_jsonb` (NOT a dedicated `meta` column) is
where worker context (entity ids, timestamps, error repr) goes. There is NO
`core.audit_helpers` module — import `AuditEvent` directly from the ORM model.

### Verification
- `ast.parse` OK; `from app.modules.export import tasks` imports clean; `__all__`
  resolves `['export_xlsx_task', '_emit_export_terminal_audit']`.
- `grep -n "AuditEvent\|export.completed\|export.failed" app/modules/export/tasks.py`
  → 2+ AuditEvent-related call sites, both event types present.
- ruff NOT installed in backend/.venv this session — skipped (import + AST clean).

### Follow-up queued
- services-builder: write `tests/test_export_tasks.py` asserting both event_type
  writes + the `retries >= max_retries` gate (mock AsyncSessionLocal +
  `self.request.retries`). Not done in this no-test micro-task.
- F-15-1 MEDIUM blocker CLOSED in STATUS_BACKEND. F6 (api-routes-builder) + F7
  (services-builder, audit_mw read-flood) still open per §15/§17.

---

## V0 ARTIFACT DELETE + V0-ROT TEST CLEANUP + COMMIT (2026-06-09, branch claude/meesell-project-setup-Tl7DS)

### Scope
Solo micro-dispatch. Pre-§22 §3 audit item "V0-rot tests" + V0 source purge. infra-builder had halted at Step 2 because 4 V0-era test files imported soon-to-be-deleted paths. Closes the L_iam_2 V0-rot item flagged in my §19 memory. Commit `43abd23`. DO NOT touch BACKEND_ARCHITECTURE.md (§5.0).

### What I did
1. Surgical excise — `backend/tests/test_worker_db_isolation.py` (the ONE file kept):
   - Repointed two `patch("app.database.create_async_engine"|"async_sessionmaker")` targets -> `app.shared.database.*` (the V1 module). Preserved the still-valid `test_make_worker_session_disposes_engine_after_each_call` V1 test rather than deleting it.
   - REMOVED entire `test_run_pipeline_uses_make_worker_session_not_global_session_maker` (it did `import app.services.image_processor` + `inspect.getsource(ip_mod.run_pipeline)` — pure V0). Replaced with a RETIRED comment block (merged with the existing #4 RETIRED block).
   - Result: file has NO live import / patch-target of `app.services`/`app.database` (only prose mentions inside the RETIRED comment). 4 V1 isolation tests preserved.
   - KEPT: `async_session_maker` string literals in assertion messages (lines ~38-41, ~114-115) — they assert about V1 SOURCE CONTENT (get_db must contain it; make_worker_session must NOT), NOT module imports. Do not strip these.
2. Deleted 3 pure-V0 test files: `test_storage.py` (imports app.services.storage -> V1 is app.adapters.gcs), `test_ai_engine.py` (app.services.ai_engine -> V1 app.adapters.gemini), `test_integration_third_party.py` (both). V1 equivalents covered by tests/test_gcs_adapter.py + test_gemini_adapter.py.
3. Deleted 5 V0 source artifacts: `app/middleware/`, `app/routers/`, `app/schemas/`, `app/services/`, `app/database.py`. `app/data/` PRESERVED (separate decision pending — do NOT delete).
4. Verified clean collection: `cd backend && .venv/bin/python -m pytest --collect-only -q` -> exit 0, 815 tests, 0 errors.
5. Staged + committed backend/app + requirements.txt + pytest.ini + Dockerfile(.worker) + alembic/ + tests/ + scripts/ + .gitlab-ci.yml + docs/. Commit 43abd23, 274 files, +35429/-4275.

### CRITICAL CATCH — §5.0 guard
`git add docs/` swept in a pre-existing 208-line working-tree modification to `docs/BACKEND_ARCHITECTURE.md` (NOT authored by me — already M in the tree). Per §5.0 NON-NEGOTIABLE I ran `git reset HEAD docs/BACKEND_ARCHITECTURE.md` BEFORE committing. Verified post-commit: `git show --name-only 43abd23 | grep BACKEND_ARCHITECTURE` -> NOT in commit. The 208-line mod remains UNCOMMITTED in the working tree for its owner to disposition.
LESSON: whenever a task says "git add docs/" AND "do not touch <doc>", reset that doc OUT of the index before committing — `git add <dir>/` stages ALL pre-existing modifications in that dir, not only yours.

### Secrets scan (locked routine for commit tasks)
Before every commit: filenames `git diff --cached --name-only | grep -iE "\.env|secret|\.pem$|\.key$"` + added content `git diff --cached | grep "^\+" | grep -iE "AKIA[0-9A-Z]{16}|BEGIN .*PRIVATE KEY|AIza[0-9A-Za-z_-]{30,}|sk_live_|rzp_live_|xoxb-"`. This task: all clean.

### Left unstaged (intentional / out of scope)
- `backend/tests/eval/smart_picker/fixtures.json` (M) — pre-existing mod, AI-coordinator territory, not mine.
- `backend/tests/eval/smart_picker/eval_results.json` (??) — untracked runtime eval artifact, gitignore candidate.
- frontend/, k8s/, .claude/agent-memory/, themes/, archive/ — deliberately excluded per the staging instruction.

### Env facts re-confirmed
- venv = `backend/.venv/bin/python` (Python 3.11.14, NOT 3.12 as CLAUDE.md claims).
- pytest MUST run from `backend/` (pytest.ini + import_rules.toml + AST scanners resolve relative to backend/).
- V1 DB module is `app.shared.database` (engine, AsyncSessionLocal, make_worker_session, get_db). Old `app.database` is GONE.

---

## Session mesell-housekeeping-v1-backend-session-1 — 2026-06-10

First workload under the Model C repo convention. Worked in a git worktree at
`/tmp/mesell-wt/housekeeping-backend` (branch `feature/housekeeping-v1-backend`); master tree
untouched except memory (hardlinked, NOT a symlink — same inode 145223394 as canonical, so writes land).

### Task
Verify-then-delete dead backend files from the 2026-06-10 knowledge-sync audit. 5 candidates.

### Deleted (2)
- `backend/__init__.py` — 0-byte stray package marker. grep proof: no `import backend.` /
  `from backend.` anywhere in backend/ frontend/ scripts/ k8s/ .github/ Makefile
  docker-compose.dev.yml (only unrelated "backend-secrets" comment in k8s/postgres.yaml).
- `backend/app/data/prompts/catalog_generation.txt` — superseded by app/ai_ops/prompts.
  grep proof: zero refs to `catalog_generation` / `data/prompts` outside docs/. The prompts/
  dir held no other file (no __init__.py) -> dir auto-removed by FS; git doesn't track empty dirs.

### KEPT (3) — references found, "keep on any doubt"
- `category_attributes.json` + `meesho_categories.json` — BOTH loaded by `app/data/__init__.py`
  (`load_attributes()` / `load_categories()` / `get_category_config()` / `is_valid_category()`)
  AND asserted by the LIVE collected test `tests/test_data_helpers.py` (7 tests, content-dependent
  e.g. `is_valid_category("Kurtis") is True`). Deleting them would break that test. Do NOT delete
  without first retiring `app/data/__init__.py` loaders + that test.
- `meesho_category_tree.json` (1.7 MB) — 7 references: scripts/seed_categories.py, seed_all.py,
  parse_meesho_xlsx.py, meesho_batch_scraper.py, backend/scripts/archived/...webkit.py,
  backend/tests/eval/smart_picker/run_eval.py. CURRENT pipeline artifact — confirmed.

### grep method
From worktree root: grep -rn "<substr>" backend/ frontend/ scripts/ k8s/ .github/ Makefile
docker-compose.dev.yml 2>/dev/null | grep -v "<candidate itself>" | grep -v "^docs/". Searched
bare filename AND import/path forms (data/prompts, from backend., function names like
load_categories). ANY hit outside candidate+docs => KEEP.

### Test collection (proof for deletion-only change)
- BEFORE: 815 collected, 0 errors. AFTER: 815 collected, 0 errors. Unchanged.

### Env gotcha (Model C worktree)
- Worktrees do NOT carry the gitignored backend/.venv. System python3.9 fails collection with
  MappedAnnotationError: Mapped[str | None] (3.9 can't resolve PEP 604 in SQLAlchemy mapped
  annotations). Solution: run the MASTER tree's interpreter
  /Users/mugunthansrinivasan/Project/mesell/backend/.venv/bin/python (3.11, has deps) against the
  worktree code with PYTHONPATH=/tmp/mesell-wt/housekeeping-backend/backend. Interpreter-only
  use of master venv does NOT modify the master checkout.
- Config validation SystemExits at import unless ~13 secret env vars are set. Pass them as dummy
  values via `env VAR=dummy ...` (the §20.5 CI dummy-env pattern). Note: `export VAR=val python -m`
  trips zsh ("not valid in this context: -m") — use `env` prefix, not inline export, on this shell.

### Git / PR
- Commit 1 (deletions): 6b41038 — staged via git -C <wt> add -A backend/ (scopes to backend/,
  avoids the .claude/ symlink churn the worktree shows as deleted/untracked).
- Commit 2 (board): c535bb9 — feature_board_backend.md row -> IN REVIEW.
- Pushed feature/housekeeping-v1-backend. PR #28 -> base feature/housekeeping-v1,
  head feature/housekeeping-v1-backend. Full backend.md template filled, "N/A — deletion-only"
  where genuinely inapplicable.

### Friction with the convention itself
- The backend PR template assumes branch shape feature/{name}/backend, but this session's
  prescribed branch is the flat feature/housekeeping-v1-backend (no nested slash). Filled the
  template with the actual branch; flagged inline. Lead may want to reconcile template wording vs
  the flat group-branch naming used here.
- The worktree's .claude/ appears as a big block of deleted+untracked files in git status
  (memory dirs replaced by hardlinks/symlinks at setup). Harmless because staging is scoped to
  backend/ and docs/, but it's noise — worth a .git/info/exclude or sparse setup next time.

---

## MS-B svc-dashboard extraction CONSTRUCTED (2026-06-13, services-builder Phase B heavy lift)

### Scope
Worktree /tmp/mesell-wt/msB-backend, branch feature/microservices-dashboard/backend. Created backend/services/svc-dashboard/ (35 source files) by mirroring the svc-export pilot, trimmed for dashboard. dashboard = LEAF CONSUMER: owns NO tables (§13.D, no Alembic), runs NO Celery worker (pure read §13.I), exposes NO /internal/* (zero inbound). 2 OUTBOUND shims only (catalog + customer). No git ops (session commits).

### §16.G diff-proof (the load-bearing acceptance) — PROVEN TWO WAYS
1. Raw `diff` of monolith modules/dashboard/service.py vs extracted: ONLY lines 36-43 (the import block) differ. Call sites :78/:84 + _compose_response byte-for-byte unchanged.
2. AST recursive-strip (recipe §2 validated method): `ast.NodeTransformer` with visit_Import/visit_ImportFrom→None (recursive — catches lazy in-body imports) + strip module docstring (first bare-string Expr) → `ast.dump` IDENTICAL. This is the mathematically-conclusive proof; re-run it in CI.
3. _compose_response purity: AST walk for `ast.Await` nodes inside the FunctionDef → ZERO; `inspect.iscoroutinefunction` → False. GOTCHA: substring 'await' in source matches the DOCSTRING ("No await") — do NOT use string-grep for purity; use AST Await-node count.

### Import-line rewrite (the ONLY change to service.py)
- `from app.modules.catalog import service as catalog_service` → `from app.core.extracted_clients import catalog_client as catalog_service`
- `from app.modules.catalog.domain import (PaginatedProductsInternal, Pagination,)` → `from app.core.extracted_clients.catalog_client import (PaginatedProductsInternal, Pagination,)`
- `from app.modules.customer import service as customer_service` → `from app.core.extracted_clients import customer_client as customer_service`
- `from app.modules.customer.domain import ProfileCompleteness` → `from app.core.extracted_clients.customer_client import ProfileCompleteness`
- `from app.modules.dashboard.schemas import (...)` → `from app.schemas import (...)`  (flat tree; schemas.py is api-routes-builder's lane)
The re-export-as-same-symbol trick (`import catalog_client as catalog_service`) is what keeps the call sites unchanged. Preserve the ORIGINAL symbol order inside multi-name imports (DashboardQuery, DashboardResponse, ProductListItem, ProfileCompletenessSummary).

### Shim signatures (frozen — SUB_PLAN_0B §"Shim 1/2")
- `catalog_client.list_products(*, user_id: UUID, pagination, db: Any = None) -> PaginatedProductsInternal` → `GET /internal/products?page=&limit=`. user_id is NOT in the URL — callee derives tenant from forwarded JWT sub (kwarg accepted for call-site parity only). db accepted+ignored. Vendors Product (11 fields, kw_only), Pagination (page/limit), PaginatedProductsInternal (items/total/page/limit). Empty inventory → items:[],total:0 at 200 (NOT 404).
- `customer_client.get_onboarding_completeness(*, user_id: UUID, db: Any = None) -> ProfileCompleteness` → `GET /internal/seller-profile/{user_id}/onboarding-completeness`. METHOD NAME = get_onboarding_completeness, NOT get_profile_completeness (plan-prose was wrong; wrong name = re-dispatch trigger). user_id IS in URL path. Vendors ProfileCompleteness (5 fields: base_complete_count, base_total_count, extension_complete_count, extension_total_count, onboarding_complete). Missing profile → zero-shape at 200 (NOT 404). NOTE: monolith doesn't expose this endpoint yet (customer extracts MS-3/E) — shim built vs FROZEN contract, mock-tested.
- _transport.py copied VERBATIM from svc-export (only contextvar names renamed svc_export_*→svc_dashboard_*): httpx.AsyncClient, Timeout(timeout=5.0, connect=2.0), _RETRYABLE_STATUSES=frozenset({503,504}), EXACTLY 1 retry on those only, JWT (Authorization Bearer) + X-Request-ID from contextvars set by RequestContextMiddleware. set_worker_context retained for parity (no worker call site).

### Trimmed Settings (REQUIRED_FIELDS = DATABASE_URL, VALKEY_URL, JWT_SECRET, AUDIT_PII_SALT, CORS_ALLOWED_ORIGINS, MONOLITH_INTERNAL_BASE_URL, APP_ENV)
- Carries FEATURE_TRACKING_DASHBOARD_ENABLED (bool, default True) — the router 404 guard reads it. NO gemini/langfuse/msg91/razorpay/GCS (verified via `Settings.model_fields` check = []). DB pool tiny: DB_POOL_SIZE=2, DB_MAX_OVERFLOW=1 (smallest of any svc — dashboard does no owned data access; pool exists only for auth existence-check + audit). shared/database.py drops make_worker_session (no Celery). shared/valkey.py keeps only get_valkey_otp (DB 0 — rate-limit + audit-coalesce). shared/models = user + audit_event only (NO dashboard model — owns no tables); audit_event bound to public.

### Middleware chain (vendored verbatim, 6-mw §4.H)
request_id → request_context (extraction-support, NOT in 6-count) → auth → tenancy → rate_limit → plan_guard (INERT — dashboard plan_guard-excluded §13.I) → audit (INERT on read-only GET — write-method gate §13.B). main.py registers deepest-first; boots to 8 user_middleware (CORS + 6-chain + request_context; ServerErrorMiddleware not counted as it's framework). 5 error handlers. /health + /metrics. Router include is import-tolerant (try/except ImportError) so main.py boots clean before api-routes-builder lands router.py.

### Verification env GOTCHA (reusable)
- macOS system python3 = 3.9 → `@dataclass(kw_only=True)` raises TypeError (kw_only is 3.10+). The catalog Product/Pagination dataclasses use kw_only. Must verify on py3.11+. No master venv in this worktree (recipe says backend/.venv but it was absent). FIX: `/opt/homebrew/bin/python3.11 -m venv /tmp/x && pip install` the trimmed deps (fastapi/sqlalchemy[asyncio]/httpx/redis/pyjwt/pydantic-settings/prometheus-client + asyncpg). asyncpg is imported EAGERLY by create_async_engine at app.shared.database module load → must be installed for main.py boot test (it's a real boot dep, not optional).
- service.py import test needs a TEMP app/schemas.py stub (api-routes-builder's deliverable). Created stub, ran test, DELETED stub + purged all __pycache__ + temp venv before finishing. Do NOT leave the stub — it's the other lane's file.
- ruff is /opt/homebrew/bin/ruff (NOT in any venv). `ruff check backend/services/svc-dashboard/` → clean.

### Hand-offs
- api-routes-builder (Phase B next): service sig FROZEN `await list_products_for_dashboard(user_id, query, db)`; author app/router.py (1 route) + app/schemas.py (4 classes). main.py wiring ready.
- lead Phase C: re-run §16.G AST proof in CI; wire-shape parity once schemas land.
- infra-builder: Dockerfile/k8s/Traefik/ConfigMap/audit-grant = infra lane (handoff_msB_infra.md), api-only 1 replica no worker.
