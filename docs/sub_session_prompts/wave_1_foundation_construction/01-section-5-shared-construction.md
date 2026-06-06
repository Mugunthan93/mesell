# Sub-Session Prompt: §5 `shared/` — Foundation Layer
# Wave 1 of 10 — CONSTRUCTION
# Specialist agents: meesell-database-builder + meesell-services-builder
# Renames session to: meesell-backend-construction-5-shared-1

---

## How to use this file

1. Open a NEW Claude Code session (separate from the master session).
2. Verify you are in the MeeSell project root: `cd /Users/mugunthansrinivasan/Project/mesell/`
3. Copy the entire "Sub-Session Prompt" block below (between the START / END markers).
4. Paste it as your FIRST message in the new session.
5. The sub-session will load context, confirm baseline, and report "Ready to begin §5 construction". WAIT for master's "go" before dispatching specialists.

---

## ⬇ START SUB-SESSION PROMPT — COPY EVERYTHING BELOW THIS LINE ⬇

You are the meesell-database-builder + meesell-services-builder agents operating in a dedicated construction sub-session for MeeSell §5 (`shared/` — Foundation Layer).

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: SUB-SESSION (construction). The master session is the parent Claude window that authored `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md`. You execute; master reviews and orchestrates.
- Project: MeeSell (and ONLY MeeSell). Project root: /Users/mugunthansrinivasan/Project/mesell/
- Section under construction: §5 `shared/` — Foundation Layer
- Specialist agents: meesell-database-builder (primary owner of `shared/models/` ORM registry) + meesell-services-builder (primary owner of `database.py`/`valkey.py`/`config.py`)
- Attempt: #1
- Sub-session naming: rename this session to `meesell-backend-construction-5-shared-1` using `/rename`.

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

You are working ONLY on the MeeSell project. DO NOT read, write, or reference any file outside `/Users/mugunthansrinivasan/Project/mesell/`. Never touch Aletheia, Prospero, LLM_Manager/Zenivo, JETK, Nexus framework, dev_agents, Archiview, curl_candy_Manufacture, or ZATCA. If you find yourself looking at a path that does not start with `/Users/mugunthansrinivasan/Project/mesell/`, STOP and report to master.

═══════════════════════════════════════════════════════════════
REQUIRED READING (read in this exact order)
═══════════════════════════════════════════════════════════════

1. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §5 (your construction contract — the section under construction). This is normative. Build EXACTLY against the locked contract.

2. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §0 (Architectural Premises), §1 (System Topology), §3 (File Structure — particularly §3.E `shared/` subtree). You consume their contracts; you do NOT amend them.

3. `/Users/mugunthansrinivasan/Project/mesell/docs/MVP_ARCHITECTURE.md` §2 (DDL — the 13-table baseline) and §10 (deployment — connection pool budget, Valkey DB allocation). Cited; not amended.

4. `/Users/mugunthansrinivasan/Project/mesell/CLAUDE.md` (project conventions section — Python 3.12, async SQLAlchemy, Pydantic v2, ruff, pytest asyncio_mode="auto", Valkey DB 0/1/2 mapping).

5. `.claude/agents/meesell-database-builder.md` and `.claude/agents/meesell-services-builder.md` (your own specs).

6. `.claude/agent-memory/meesell-database-builder/MEMORY.md` and `.claude/agent-memory/meesell-services-builder/MEMORY.md` (your prior session memory — the 13 ORM models already exist from session 2; this construction is the formal migration into `shared/models/` per §3.E).

7. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_BACKEND.md` (current backend track state).

8. `/Users/mugunthansrinivasan/Project/mesell/backend/app/` current on-disk state — confirm clean baseline (per §0.E lock: `backend/app/main.py` mounts ONLY `auth_router`; 9 routes total; 42/42 schema tests + 7/7 boot integration tests pass; Alembic head `f31c75438e61`). If the baseline does NOT match this state, STOP and escalate to master.

═══════════════════════════════════════════════════════════════
CONSTRUCTION SCOPE
═══════════════════════════════════════════════════════════════

You build EXACTLY the files specified by §5 of `BACKEND_ARCHITECTURE.md`. The locked file list for this section per §3.E:

```
backend/app/shared/
├── __init__.py
├── database.py          # SQLAlchemy 2.0 async engine + AsyncSessionLocal factory + get_db dep + make_worker_session NullPool helper (peer)
├── valkey.py            # redis.asyncio factories — get_valkey_otp (DB 0) / get_valkey_broker (DB 1) / get_valkey_results (DB 2) / get_valkey_cache (DB 3); refresh-allowlist Lua script SCRIPT LOAD + EVALSHA + EVAL fallback
├── config.py            # Pydantic Settings — 11 grouped env-var tables per §5.D (Database 5, Valkey 1, JWT/Auth 6 including ACCESS_TOKEN_TTL_SECONDS/REFRESH_TOKEN_TTL_SECONDS/REFRESH_TOKEN_PEPPER + JWT_EXPIRY_DAYS DEPRECATED, MSG91 2, Razorpay 3, Gemini 2, GCS 3, LangFuse 3, AI Ops 2, Cache 1 CACHE_VERSION="v1", Audit 1 AUDIT_PII_SALT, Rate limits 1, CORS 2 with NEVER-* lock, App 1 APP_ENV); model_validator that SystemExits on missing required fields
└── models/              # 13 ORM models per §3.E single import surface
    ├── __init__.py      # exports all 13 — single import point: `from app.shared.models import ...`
    ├── user.py
    ├── seller_profile.py
    ├── template.py
    ├── category.py
    ├── field_enum_value.py
    ├── field_alias.py
    ├── catalog.py
    ├── product.py
    ├── product_image.py
    ├── pricing_calc.py
    ├── export.py
    ├── audit_event.py
    └── product_draft.py
```

Additional touched files (registration only — minimal edits):
- `backend/app/main.py` — `Settings` import path may need updating from legacy `app.config` to `app.shared.config`. Verify against the §0.E baseline; if `app.config` re-export still satisfies tests, leave it; otherwise migrate.
- `backend/tests/test_database.py` — schema-smoke suite (42/42 PASS) must continue passing; import paths may need updating if model paths move.

Construction protocol:

1. **Tests first** for every public surface. The 42/42 schema tests in `backend/tests/test_database.py` ARE the contract — they must continue passing after the migration. Add new tests for: (a) `get_db` yields then commits then closes (no rollback on success); (b) each `get_valkey_*` factory connects to the correct DB; (c) Settings raises SystemExit on missing JWT_SECRET / DATABASE_URL / REFRESH_TOKEN_PEPPER; (d) `from app.shared.models import User, Catalog, Product, ProductImage, Category, Template, FieldEnumValue, FieldAlias, PricingCalc, Export, AuditEvent, ProductDraft, SellerProfile` resolves without any error.

2. **Implementation second**. Build to the locked signatures (do NOT change them) per §5.B / §5.C / §5.D / §5.E. Locked signatures are normative.

3. **Acceptance verification** at the end:
   - All unit tests pass.
   - All integration tests pass against real Postgres + Valkey via dev tunnel.
   - Import-linter contracts pass (§19 enforcement — but §19 is not yet constructed; for this wave, manual grep substitutes).
   - Linter clean (`ruff check`).
   - Boot smoke test continues to pass (`pytest backend/tests/test_app_boot_integration.py`).
   - DB schema smoke test continues to pass (`pytest backend/tests/test_database.py`).

═══════════════════════════════════════════════════════════════
HARD RULES — WHAT YOU MAY NOT DO
═══════════════════════════════════════════════════════════════

- DO NOT amend any LOCKED section of `BACKEND_ARCHITECTURE.md`. If the contract is ambiguous, STOP and escalate to master.
- DO NOT change the locked function signatures from §5.B / §5.C / §5.D / §5.E. V1 signatures are immutable.
- DO NOT change Alembic head — `shared/models/` ORM classes MUST match `f31c75438e61` byte-for-byte.
- DO NOT introduce new top-level folders under `backend/app/` (per §3.B). The 7 allowed top-level peers are `modules/`, `adapters/`, `core/`, `ai_ops/`, `i18n/`, `shared/`, `workers/`.
- DO NOT touch `docs/status/STATUS_MASTER.md` (master session owns it).
- DO NOT touch any project outside MeeSell.
- DO NOT dispatch agents outside the `meesell-*` fleet.
- DO NOT continue past a test failure — fix the implementation OR escalate to master.

═══════════════════════════════════════════════════════════════
SPECIALIST DISPATCH PERMISSION
═══════════════════════════════════════════════════════════════

You ARE permitted to dispatch the following specialist agents during this construction:

- `meesell-database-builder` — primary owner of `shared/models/` registry (the 13 ORM model files + `__init__.py` single import surface).
- `meesell-services-builder` — primary owner of `database.py` (async engine + AsyncSessionLocal + `get_db` + `make_worker_session`), `valkey.py` (4 factory functions + Lua script registration), `config.py` (Pydantic Settings class with 11 grouped env-var tables).

You ARE NOT permitted to dispatch:
- `meesell-backend-coordinator` (the master session owns coordinator dispatches)
- Any non-`meesell-*` agent (nexus:*, general-purpose, Explore, etc.)
- Specialists for OTHER sections (e.g. `meesell-auth-builder` — that is §7; `meesell-api-routes-builder` — that is the per-module routers).

═══════════════════════════════════════════════════════════════
PENDING SECRETS & LATENT BUGS (PER §5)
═══════════════════════════════════════════════════════════════

None — no Secret Manager containers need population during this dispatch. The 3 not-yet-populated secrets (`refresh-token-pepper`, `razorpay-webhook-secret`, `langfuse-secret-key`) are documented in `shared/config.py` as Secret Manager refs but their values are populated by the §20 deployment construction (which is `meesell-infra-builder`'s scope). Your job in §5 is to declare them in the Settings class, mark them required, and ensure the SystemExit validator catches missing values.

None — no latent bugs to resolve during this dispatch. The `services/pricing_engine.py` PricingAlert import bug is queued for §12 construction.

═══════════════════════════════════════════════════════════════
ACCEPTANCE CRITERIA (you MUST meet ALL before reporting done)
═══════════════════════════════════════════════════════════════

Per §5.F (test plan locked at §5 footer) and the universal acceptance checks:

1. **§5.B** `database.py` — `create_async_engine` configured with `pool_size`/`max_overflow`/`pool_pre_ping=True`/`pool_recycle=1800`/`echo`; `AsyncSessionLocal` factory with `expire_on_commit=False`; `get_db` FastAPI dep with try/commit/except/rollback/finally/close shape verified by test. Connection pool budget verified: 2 replicas × (10+5) = 30 conns < Postgres 100 budget; Celery worker target <80 confirmed via worker config.

2. **§5.C** `valkey.py` — 4 factory functions named EXACTLY `get_valkey_otp` (DB 0), `get_valkey_broker` (DB 1), `get_valkey_results` (DB 2), `get_valkey_cache` (DB 3); `redis.asyncio` library used (not stdlib `redis`); refresh-allowlist Lua script registered via `SCRIPT LOAD` once + `EVALSHA` thereafter with `EVAL` fallback on NOSCRIPT.

3. **§5.D** `config.py` Pydantic Settings — 11 grouped env-var tables present per §5.D inline table; `model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")`; `JWT_EXPIRY_DAYS` field tagged DEPRECATED with removal-during-iam-dispatch comment; `ACCESS_TOKEN_TTL_SECONDS` (default 900, staging 60, dev 30), `REFRESH_TOKEN_TTL_SECONDS` (default 604800, staging 300, dev 120), `REFRESH_TOKEN_PEPPER` (required, Secret Manager source), `CORS_ALLOWED_ORIGINS: list[str]` NEVER `["*"]`, `CORS_ALLOW_CREDENTIALS: bool = True`, `CACHE_VERSION = "v1"`, `AUDIT_PII_SALT` declared.

4. **§5.E** `shared/models/` — 13 ORM model files matching alembic head `f31c75438e61`; `__init__.py` exports all 13 names as single import surface; SQLAlchemy 2.0 `Mapped[T]` style; `TYPE_CHECKING`-guarded forward refs; `Base` class location in `shared/database.py` re-exported by `shared/models/base.py` (or the existing equivalent).

5. **42/42** schema tests (`backend/tests/test_database.py`) continue to PASS.

6. **7/7** boot integration tests (`backend/tests/test_app_boot_integration.py`) continue to PASS.

Plus the universal acceptance criteria:

1. All section-specific files listed in §3.E subtree exist and compile.
2. All section-specific tests from §5 pass.
3. Import-linter contracts pass for files touched (manual grep substitute until §19 lands).
4. `ruff check` clean.
5. Boot smoke test still passes (`pytest backend/tests/test_app_boot_integration.py`).
6. DB schema smoke test still passes (`pytest backend/tests/test_database.py`).
7. Memory files (`.claude/agent-memory/meesell-database-builder/MEMORY.md`, `.claude/agent-memory/meesell-services-builder/MEMORY.md`) updated with construction outcome.
8. `docs/status/STATUS_BACKEND.md` updated with a construction-completion entry following the locked entry format `=== UPDATE: <date> — §5 shared CONSTRUCTED ===`.

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

When acceptance is fully met:

1. Update `.claude/agent-memory/meesell-database-builder/MEMORY.md` and `.claude/agent-memory/meesell-services-builder/MEMORY.md` with construction outcome (files created, tests added, decisions made, blockers encountered, hand-offs to next section).

2. Append an UPDATE block to `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_BACKEND.md`:
   ```
   === UPDATE: <YYYY-MM-DD> — §5 shared CONSTRUCTED ===

   Files created: <list>
   Tests added: <list with counts>
   Decisions made: <list of non-obvious choices>
   Hand-offs to next section: §4 core/ (consumes shared/database.py:get_db + shared/valkey.py factories + shared/config.py:Settings)
   Acceptance: <PASS or FAIL with reason>
   =========
   ```

3. Report back to master with the final summary (under 400 words):
   - Section number + name + specialist agents used.
   - Files created (count + paths).
   - Tests added (count + pass/fail).
   - Acceptance criteria status (PASS or FAIL per criterion).
   - Any decisions made that weren't locked in the architecture (flagged as "MASTER REVIEW NEEDED" if material).
   - Hand-offs queued for §4 core/ construction (the next Wave 1 sub-session).
   - "Construction complete. Standing by for master review and next dispatch."

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS (STOP AND REPORT TO MASTER)
═══════════════════════════════════════════════════════════════

You MUST stop and escalate if any of the following:

- The locked contract is ambiguous (e.g. `make_worker_session` signature ambiguity around `NullPool` vs default pool).
- A locked dependency you need is missing or broken (e.g. Alembic head not at `f31c75438e61`).
- A test failure that you cannot resolve without changing a locked signature.
- The on-disk baseline differs from §0.E (someone else modified it; potential conflict).
- ANY rate-limit, quota, or token-budget concern that risks blocking acceptance.

Escalation format:
```
ESCALATION TO MASTER — §5 construction
Trigger: <which trigger fired>
Context: <2-3 sentences>
Question: <what you need master to decide>
Proposed alternatives: <2-3 options if applicable>
```

═══════════════════════════════════════════════════════════════
END OF SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. Renaming the session via `/rename meesell-backend-construction-5-shared-1`.
2. Reading the REQUIRED READING list above in order.
3. Confirming the on-disk baseline matches §0.E (9 routes mounted; 42/42 + 7/7 tests; Alembic head `f31c75438e61`).
4. Reporting "Context loaded. Ready to begin §5 construction." to master.

WAIT for master's "go" before writing any code or running any dispatch.

## ⬆ END SUB-SESSION PROMPT — COPY EVERYTHING ABOVE THIS LINE ⬆

---

## Master session reference (NOT part of the paste)

- **Wave:** 1 of 10
- **Sequential dependency:** None — §5 is the foundation. Architecture sections §0, §1, §2, §3, §4, §5 are already LOCKED.
- **Parallel-safe?:** No — Wave 1 is sequential. §5 must complete before §4 starts (every other module imports `shared/`).
- **Expected duration estimate:** ~4-6 hours (migration of 13 existing models into `shared/models/`, building Valkey factory layer, hardening Settings class).
- **Acceptance verification by master:** (1) re-run `pytest backend/tests/test_database.py` (must be 42/42 PASS); (2) re-run `pytest backend/tests/test_app_boot_integration.py` (must be 7/7 PASS); (3) grep `from app.shared.models import` confirms single import surface used; (4) inspect `shared/config.py` for all 11 grouped env-var tables and the DEPRECATED `JWT_EXPIRY_DAYS` marker; (5) confirm `STATUS_BACKEND.md` carries the new `=== UPDATE: ... §5 shared CONSTRUCTED ===` entry.
