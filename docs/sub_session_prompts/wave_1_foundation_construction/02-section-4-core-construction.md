# Sub-Session Prompt: §4 `core/` — Cross-Cutting Foundation
# Wave 1 of 10 — CONSTRUCTION
# Specialist agents: meesell-services-builder + meesell-auth-builder
# Renames session to: meesell-backend-construction-4-core-1

---

## How to use this file

1. Open a NEW Claude Code session (separate from the master session).
2. Verify you are in the MeeSell project root: `cd /Users/mugunthansrinivasan/Project/mesell/`
3. Copy the entire "Sub-Session Prompt" block below (between the START / END markers).
4. Paste it as your FIRST message in the new session.
5. The sub-session will load context, confirm baseline, and report "Ready to begin §4 construction". WAIT for master's "go" before dispatching specialists.

---

## ⬇ START SUB-SESSION PROMPT — COPY EVERYTHING BELOW THIS LINE ⬇

You are the meesell-services-builder + meesell-auth-builder agents operating in a dedicated construction sub-session for MeeSell §4 (`core/` — Cross-Cutting Foundation).

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: SUB-SESSION (construction). The master session is the parent Claude window that authored `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md`. You execute; master reviews and orchestrates.
- Project: MeeSell (and ONLY MeeSell). Project root: /Users/mugunthansrinivasan/Project/mesell/
- Section under construction: §4 `core/` — Cross-Cutting Foundation (middleware chain + auth dep + tenancy helpers + cache helper + plan_guard + structured errors)
- Specialist agents: meesell-services-builder (owns tenancy.py + cache.py + plan_guard.py + errors.py + most middleware), meesell-auth-builder (owns auth.py `get_current_user` + middleware/auth_mw.py per the FE-D5 ratification at §4.B)
- Attempt: #1
- Sub-session naming: rename via `/rename meesell-backend-construction-4-core-1`.

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

You are working ONLY on the MeeSell project. DO NOT read, write, or reference any file outside `/Users/mugunthansrinivasan/Project/mesell/`. Never touch Aletheia, Prospero, LLM_Manager/Zenivo, JETK, Nexus framework, dev_agents, Archiview, curl_candy_Manufacture, or ZATCA. If you find yourself looking at a path that does not start with `/Users/mugunthansrinivasan/Project/mesell/`, STOP and report to master.

═══════════════════════════════════════════════════════════════
REQUIRED READING (read in this exact order)
═══════════════════════════════════════════════════════════════

1. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §4 (your construction contract — A through J subsections, especially §4.B JWT contract incl. FE-D5 amendment, §4.C tenancy, §4.D cache, §4.E plan_guard 4 V1 resources, §4.F errors, §4.G middleware subtree, §4.H middleware ordering rationale).

2. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §0 (Architectural Premises incl. FE-D5 amendment), §1 (System Topology), §3 (File Structure — esp. §3.D `core/` subtree), §5 (`shared/` — already CONSTRUCTED in Wave 1 step 1; consume `get_db`, `get_valkey_*` factories, `Settings`).

3. `/Users/mugunthansrinivasan/Project/mesell/docs/MVP_ARCHITECTURE.md` §10.4 (multi-tenancy) and §11 (audit log — esp. §11.3 audit-after-write ordering). Cited; not amended.

4. `/Users/mugunthansrinivasan/Project/mesell/CLAUDE.md` (project conventions; Decision 14 FE-D5 amendment about access-JWT-in-memory + refresh-token in HttpOnly cookie + HMAC-pepper allowlist).

5. `.claude/agents/meesell-services-builder.md` and `.claude/agents/meesell-auth-builder.md` (your own specs).

6. `.claude/agent-memory/meesell-services-builder/MEMORY.md` and `.claude/agent-memory/meesell-auth-builder/MEMORY.md` (your prior session memory).

7. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_BACKEND.md` (current state — confirm §5 shared CONSTRUCTED).

8. `/Users/mugunthansrinivasan/Project/mesell/backend/app/` — confirm §5 CONSTRUCTED baseline (Wave 1 step 1 complete; `shared/` package exists; 13 ORM models import from `app.shared.models`).

═══════════════════════════════════════════════════════════════
CONSTRUCTION SCOPE
═══════════════════════════════════════════════════════════════

You build EXACTLY the files specified by §4 of `BACKEND_ARCHITECTURE.md`. The locked file list per §3.D:

```
backend/app/core/
├── __init__.py
├── auth.py              # get_current_user FastAPI dep; JWT decode/validate per §4.B (owner: meesell-auth-builder)
├── tenancy.py           # user_id injection + scope_to_user helper per §4.C (owner: meesell-services-builder)
├── cache.py             # Valkey DB 3 read-through helper with version-tagged keys per §4.D
├── plan_guard.py        # plan claim → 4 V1 feature budget enforcement per §4.E
├── errors.py            # structured error handlers + validation_message_id resolution (calls i18n/, even though i18n/ not yet built — declare the call point as a deferred wire)
└── middleware/
    ├── __init__.py
    ├── request_id.py    # X-Request-ID injection + propagation
    ├── auth_mw.py       # decode access JWT + attach user to request.state (owner: meesell-auth-builder)
    ├── tenancy_mw.py    # inject user_id into request context per §4.C
    ├── rate_limit_mw.py # Valkey DB 0 sliding-window per MVP_ARCH §10.7
    ├── plan_guard_mw.py # plan enforcement (consumes core/plan_guard.py)
    └── audit_mw.py      # audit_events post-commit write (per §2.10 cross-cutting exception, after-route placement per §3.D + §4.H)
```

Also: `backend/app/main.py` — register all 7 middleware in the locked order per §3.D + §4.H: `CORS → request_id → auth_mw → tenancy_mw → rate_limit_mw → plan_guard_mw → (route handler) → audit_mw`. CORS configured per §4.G with `Access-Control-Allow-Credentials: true` on `/api/v1/auth/*` and `Access-Control-Allow-Origin` explicit (NEVER `*`).

Construction protocol:

1. **Tests first** for every public surface. Test classes:
   - `test_auth_get_current_user.py` — JWT happy path, expired token (401 `auth.token_expired`), missing token (401 `auth.token_missing`), unknown user (401 `auth.user_not_found`).
   - `test_tenancy_scope_to_user.py` — `scope_to_user(query, user_id)` injects WHERE clause.
   - `test_cache_versioned_keys.py` — version-tagged key construction; cache miss → repository call → cache set; cache hit → no repository call; pre-warm path; ETag round-trip.
   - `test_plan_guard.py` — 4 V1 resources enforced per §4.E (the 3 plan-gated + autosave coalescing per `MVP_ARCH §11.4`).
   - `test_errors.py` — `validation_message_id` envelope shape; HTTP status mapping per exception class.
   - `test_middleware_ordering.py` — boot-time assertion that the 7 middleware are registered in the §4.H canonical order.
   - `test_audit_mw_post_commit.py` — audit_events row only written on 2xx (no row on 4xx / 5xx).

2. **Implementation second**. Build to the locked signatures per §4.B (`get_current_user(token: str = Depends(oauth2_scheme)) -> User`), §4.C (`scope_to_user(stmt, user_id)`), §4.D (`get_or_set_cache(key, fetch_fn, ttl, version)`), §4.E (`@requires_plan_capacity(resource, key_fn)`).

3. **Acceptance verification** at the end:
   - All unit tests pass.
   - Integration tests pass against real Postgres + Valkey via dev tunnel.
   - Linter clean (`ruff check`).
   - Boot smoke test continues to pass (`pytest backend/tests/test_app_boot_integration.py`); route count assertion may need increment.
   - DB schema smoke test continues to pass (`pytest backend/tests/test_database.py`).

═══════════════════════════════════════════════════════════════
HARD RULES — WHAT YOU MAY NOT DO
═══════════════════════════════════════════════════════════════

- DO NOT amend any LOCKED section of `BACKEND_ARCHITECTURE.md`. If ambiguous, STOP and escalate.
- DO NOT change the locked function signatures from §4.B / §4.C / §4.D / §4.E / §4.F.
- DO NOT introduce new cross-module call sites. `core/` is consumed by every domain module but does NOT import any domain module's service/repo.
- DO NOT import `adapters.gemini` directly. `core/` does not consume `ai_ops/` either — this is foundation glue.
- DO NOT touch `STATUS_MASTER.md` (master owns).
- DO NOT touch any project outside MeeSell.
- DO NOT dispatch agents outside the `meesell-*` fleet.
- DO NOT continue past a test failure — fix the implementation OR escalate to master.

═══════════════════════════════════════════════════════════════
SPECIALIST DISPATCH PERMISSION
═══════════════════════════════════════════════════════════════

You ARE permitted to dispatch:
- `meesell-services-builder` — owns `tenancy.py`, `cache.py`, `plan_guard.py`, `errors.py`, and the 5 services-owned middleware files (`request_id.py`, `tenancy_mw.py`, `rate_limit_mw.py`, `plan_guard_mw.py`, `audit_mw.py`).
- `meesell-auth-builder` — owns `auth.py` (`get_current_user`) and `middleware/auth_mw.py` (decode JWT + attach to request.state) per §4.B FE-D5 amendment.

You ARE NOT permitted to dispatch:
- `meesell-backend-coordinator` (master owns).
- Any non-`meesell-*` agent.
- Specialists for OTHER sections (`meesell-api-routes-builder` is for per-module routers; `meesell-database-builder` belongs to §5 + Alembic migrations).

═══════════════════════════════════════════════════════════════
PENDING SECRETS & LATENT BUGS (PER §4)
═══════════════════════════════════════════════════════════════

None — no Secret Manager containers need population during this dispatch. `REFRESH_TOKEN_PEPPER` is consumed by `auth.py` + `middleware/auth_mw.py` but populated by §20 deployment construction. The pepper is read via `Settings.REFRESH_TOKEN_PEPPER` (already locked at §5.D); your job is to consume the setting, not provision the secret.

None — no latent bugs to resolve during this dispatch.

═══════════════════════════════════════════════════════════════
ACCEPTANCE CRITERIA (you MUST meet ALL before reporting done)
═══════════════════════════════════════════════════════════════

Per §4 test plan (consolidated across §4.B/C/D/E/F):

1. `core/auth.py` — `get_current_user` decodes access JWT with claims `{sub, exp, plan}` per §4.B; 3 documented error paths (token_missing, token_expired, user_not_found) raise typed exceptions with `validation_message_id` set; HMAC-pepper allowlist refresh path correct per FE-D5.
2. `core/tenancy.py` — `scope_to_user(stmt, user_id)` returns a SQLAlchemy 2.0 Select with the `user_id` WHERE predicate; 3-layer defense documented (this is layer 1; `assert_product_ownership` is layer 2 in §10; GCS path prefix is layer 3 in §11).
3. `core/cache.py` — version-tagged keys (`CACHE_VERSION="v1"` from §5.D); read-through pattern; ETag support; single-flight via Valkey SETNX per `MVP_ARCH §6.7`.
4. `core/plan_guard.py` — 4 V1 resources enforced (the 3 plan-gated endpoints per §17.E + autosave coalescing per `MVP_ARCH §11.4`); fail-fast BEFORE any DB write.
5. `core/errors.py` — every exception has a `validation_message_id` field; resolver call point declared (will be wired to `i18n/resolver.py` in §5A); HTTP status mapping per `MVP_ARCH §10` envelope shape.
6. Middleware ordering — `app/main.py` registers in §4.H canonical order: `CORS → request_id → auth_mw → tenancy_mw → rate_limit_mw → plan_guard_mw → (route) → audit_mw`. `audit_mw` is the only middleware that runs AFTER the route per §4.H.
7. CORS — `Access-Control-Allow-Credentials: true` on `/api/v1/auth/*`; `Access-Control-Allow-Origin` explicit from `Settings.CORS_ALLOWED_ORIGINS` (NEVER `*`).

Plus the universal acceptance criteria:

1. All files listed in §3.D subtree exist and compile.
2. Section-specific tests pass.
3. Import-linter contracts pass for files touched (manual grep substitute until §19 lands).
4. `ruff check` clean.
5. `pytest backend/tests/test_app_boot_integration.py` PASS.
6. `pytest backend/tests/test_database.py` PASS.
7. Memory files updated.
8. STATUS_BACKEND.md UPDATE block appended.

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

When acceptance is met:

1. Update both specialists' memory files with construction outcome.

2. Append UPDATE block to `docs/status/STATUS_BACKEND.md`:
   ```
   === UPDATE: <YYYY-MM-DD> — §4 core/ CONSTRUCTED ===

   Files created: <list>
   Tests added: <list with counts>
   Decisions made: <list of non-obvious choices>
   Hand-offs: §5A i18n (consumes core/errors.py resolver call point) + §7 iam (consumes core/auth.get_current_user + auth_mw) + every later module (consumes tenancy/cache/plan_guard/errors)
   Acceptance: PASS / FAIL with reason
   =========
   ```

3. Report back to master (under 400 words): files created, tests added, acceptance status, decisions, hand-offs. "Construction complete. Standing by for master review and next dispatch."

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS (STOP AND REPORT TO MASTER)
═══════════════════════════════════════════════════════════════

- Locked contract ambiguous (e.g. `plan_guard` resource set unclear past the 4 named in §4.E).
- §5 dependency missing or broken (e.g. `get_db` not yet importable).
- Test failure requiring locked-signature change.
- Cross-module call not in the §2.D matrix.
- On-disk baseline differs from §5 CONSTRUCTED state.

Escalation format same as standard.

═══════════════════════════════════════════════════════════════
END OF SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. `/rename meesell-backend-construction-4-core-1`
2. Read the REQUIRED READING list.
3. Confirm §5 CONSTRUCTED baseline (`shared/` exists; 42/42 + 7/7 tests pass).
4. Report "Context loaded. Ready to begin §4 construction." to master.

WAIT for master's "go" before writing any code or dispatching specialists.

## ⬆ END SUB-SESSION PROMPT — COPY EVERYTHING ABOVE THIS LINE ⬆

---

## Master session reference (NOT part of the paste)

- **Wave:** 1 of 10
- **Sequential dependency:** §5 shared MUST be CONSTRUCTED first (core consumes `get_db`, `get_valkey_*` factories, `Settings`).
- **Parallel-safe?:** No — Wave 1 is sequential.
- **Expected duration estimate:** ~6-8 hours (auth dep + 6 middleware + plan_guard + cache layer).
- **Acceptance verification by master:** (1) inspect middleware registration order in `app/main.py` against §4.H; (2) `pytest backend/tests/test_app_boot_integration.py` PASS; (3) `pytest backend/tests/test_database.py` PASS; (4) grep `validation_message_id` in `core/errors.py` confirms field exists; (5) confirm STATUS_BACKEND.md carries `=== UPDATE: ... §4 core/ CONSTRUCTED ===`.
