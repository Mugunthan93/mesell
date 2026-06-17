# SPEC — CI Gate-4 (integration) test-harness fix

**Authored:** 2026-06-11 by `meesell-backend-coordinator`
**Rule 7 three-step:** STEP 1 of 3 (SPEC ONLY). STEP 2 = specialist executes. STEP 3 = coordinator reviews PR at merge gate.
**Source failure:** CI run `27323036548` (push to main `a5cb4420`, PR #89 develop→main), Gate 4 (integration) RED: `21 failed, 23 passed, 647 deselected, 151 errors in 62.50s`. Gates 1/2/3 GREEN; 5/Build/Deploy SKIPPED (sequential `needs:`).
**Infra handoff:** `.claude/agent-memory/meesell-infra-builder/handoff_ci_gate4_integration.md` (read-only, infra-owned).
**Session token:** `mesell-ci-gate4-fix-session-1`
**Predecessor:** `spec_ci_gate1_fix.md` (Gates 1/2/3 now GREEN — that fix is the precondition this builds on).

---

## 0. Feature/specialist mapping (operating procedure step 2)

This is NOT a single V1 feature. It is a cross-cutting test-harness fix for the whole backend integration bucket. The failures span three module surfaces — iam (auth rotation, logout, rate-limit, replay), category (pg_trgm + `categories` relation), core (audit coalesce, plan_guard) — plus `test_database.py`. The fix target is the test harness (`backend/tests/conftest.py`, `backend/tests/integration/conftest.py`) + CI schema provisioning, NOT app code.

**Named specialist:** `meesell-services-builder` (opus). Justification in §8.

---

## 1. Verified root causes (coordinator-confirmed against the actual code)

Infra's diagnosis is directionally correct on all four classes. Verified sharpenings below — each cites the exact conftest line/file.

### 1.A — Class 1: Postgres password/db mismatch (asyncpg InvalidPasswordError, test_database.py)
VERIFIED. `conftest.py` L56-59 hardcodes `_DEV_DATABASE_URL` to the URL-encoded K3s-dev cluster password on `localhost:5433/meesell`, overridable ONLY by `DEV_DATABASE_URL`. `dev_engine` (L309) + `db` (L328) bind to it. CI sets `TEST_DATABASE_URL` (meesell:password@5433/meesell_test) but NOT `DEV_DATABASE_URL` → wrong password AND wrong db → 6 fails.
ASYMMETRY TO PRESERVE: the top-of-file `DATABASE_URL` at L14-17 ALREADY honors `TEST_DATABASE_URL`. So `db_engine`/`client`/`db_session` (read `os.environ["DATABASE_URL"]`) are already CI-correct. The bug is confined to the `_DEV_DATABASE_URL` fixtures. Do NOT disturb L14-17.

### 1.B — Class 2: Valkey port 6379 (redis.ConnectionError, many)
VERIFIED. Two live-Redis fixtures default to 6379 via `CORE_TEST_VALKEY_URL`: `use_live_valkey` (L183) + `valkey` §19.D (L398). CI maps Valkey 6381 and sets `VALKEY_URL`/`TEST_VALKEY_URL` (6381) but NOT `CORE_TEST_VALKEY_URL` → both hit 6379 → refused.
NOTE: `test_core_auth_rotation.py` has its OWN local `valkey` fixture (L48) reading `VALKEY_URL` (6381 in CI) — its connection is fine; its failure is Class 4 (loop). Do NOT rewrite that fixture's URL resolution.

### 1.C — Class 3: schema + extension absent (gin_trgm_ops / relation "categories" does not exist)
VERIFIED + sharpened. The CI `meesell_test` db is created EMPTY by postgres:16-alpine. Gate-4 runs `pytest -m "integration"` directly — NO `alembic upgrade head`, NO schema provisioning (confirmed: Gate-4 job = checkout → setup-python → pip install → pytest only).
Two consumers, two paths:
1. `tests/integration/conftest.py` `iam_client` (+ all `tests/integration/`) does NOT override get_db; routes resolve against `settings.DATABASE_URL` = CI meesell_test. Expects the FULL schema incl. pg_trgm GIN indexes (migration a1b2c3d4e5f6). The integration conftest docstring states it AVOIDS create_all precisely because create_all cannot build the GIN indexes → this path REQUIRES `alembic upgrade head`.
2. Top-level `db_engine` (L70-78) does drop_all+create_all against DATABASE_URL — builds ORM tables but NOT the pg_trgm migration → no extension, no GIN indexes. `create_all` DOES build `categories` (ORM model), so "relation categories does not exist" is the iam_client/integration path (never provisions), NOT db_engine.
SEED CHECK: baseline 935e55b4852c creates `categories` EMPTY (zero INSERTs — verified). Failing tests INSERT their own Category rows (test_database.py L142/252/951; integration flows self-seed). NO seeder required — schema + extension only. Do NOT author a seed step.

### 1.D — Class 4: event-loop + genuine assertions
- `got Future attached to a different loop` (test_core_auth_rotation.py ×3): local `valkey` fixture (L34) is loop_scope=function and tests are @pytest.mark.asyncio(loop_scope=function). Likely residual = module-level Lua SHA cache / redis client bound to a prior loop interacting with session-default loop. EXPECTED to mostly evaporate once Class 2 (6381) lands. Triage AFTER connection fixes.
- `assert 2 == 1` (test_core_audit_mw.py, audit coalesce): 5-min window state bleed via shared Valkey keys — likely resolved by per-test FLUSHDB once fixtures connect (currently never connect → never flush). Re-evaluate after Class 2.
- `assert 200 == 429` (test_core_rate_limit_mw.py ×2): KEY INSIGHT — rate-limit mw FAILS OPEN on Valkey unreachable (verified: test_valkey_unreachable_fails_open asserts 200 on outage). use_live_valkey hits 6379 (refused) → check fails open → 200 where test expects 429. DOWNSTREAM of Class 2, not independent logic. Self-resolves once Valkey reachable on 6381.

TRIAGE DOCTRINE (locked): Classes 1+2+3 are connection/provisioning — fix FIRST, re-run, THEN assess Class-4 residue. 151 errors strongly implies fixture-SETUP errors (cascades), not assertion failures. Do NOT pre-emptively rewrite test logic before connection fixes prove which Class-4 items survive.

---

## 2. The fix — decisions the spec locks

### 2.1 — Env-var unification (Class 1 + 2)
CANONICAL PRECEDENCE (LOCKED):
- DB (`_DEV_DATABASE_URL` fixtures): `TEST_DATABASE_URL` > `DEV_DATABASE_URL` > hardcoded K3s-dev local default. CI wins; local dev preserved when TEST_* absent (falls through to DEV_DATABASE_URL then baked dev DSN — current laptop behavior byte-for-byte).
- Valkey (`use_live_valkey` L183 + `valkey` L398): `TEST_VALKEY_URL` > `VALKEY_URL` > `CORE_TEST_VALKEY_URL` > default `redis://localhost:6379`.
  CAUTION /N SUFFIX: both fixtures APPEND `/0`, `/3` to `base`. CI `TEST_VALKEY_URL` = `redis://localhost:6381/0` ALREADY carries `/0`. Appending → `redis://localhost:6381/0/0` (INVALID). The specialist MUST strip any trailing `/<db>` from the resolved base before re-appending the per-DB index (parse to scheme://host:port, then append `/{db_index}`). Verify against `redis://localhost:6381/0` (CI) AND `redis://localhost:6379` (bare). HIGHEST-RISK edit — call it out in the PR.
LOCAL-DEV GATE: with NO TEST_* env, both resolutions MUST reproduce today's behavior exactly. State explicitly in PR.

### 2.2 — Schema provisioning in CI (Class 3)
DECISION (LOCKED): Option (a) — a session-scoped autouse async fixture provisions `meesell_test` via `alembic upgrade head`. Rationale: matches §19.D real-DB policy; `alembic upgrade head` is the ONLY path that builds pg_trgm + GIN indexes that create_all cannot (integration conftest docstring confirms). Avoids cross-lane ci.yml churn.
SHAPE (specialist designs exact code; spec fixes the contract): place a session-scoped autouse async fixture in `backend/tests/conftest.py` (so both top-level + integration suites inherit), gated on `os.environ.get("TEST_DATABASE_URL")` being present (CI sets it; laptop dev-tunnel runs do not), that:
  1. `CREATE EXTENSION IF NOT EXISTS pg_trgm` against TEST_DATABASE_URL (defensive ordering).
  2. `alembic upgrade head` programmatically (alembic.config.Config + command.upgrade pointed at backend/alembic.ini with sqlalchemy.url overridden to TEST_DATABASE_URL) → full chain 935e55b4852c → a1b2c3d4e5f6 → f31c75438e61.
  3. (optional) teardown drop/downgrade — SKIP if it adds risk for an ephemeral CI db.
GUARD: this fixture MUST NOT run alembic against the live K3s dev DB. When TEST_DATABASE_URL absent → no-op (dev DB already has schema via real chain). State the guard.
db_engine (L70-78): leave drop_all/create_all as-is. IF a category-trigram test on the db_engine path still hits gin_trgm_ops, add `CREATE EXTENSION IF NOT EXISTS pg_trgm` before create_all there (extension presence stops the hard error; tests needing the GIN index belong on the alembic path). Decide at execution; document.

#### 2.2.A — Escalation valve
If programmatic alembic-in-conftest proves infeasible (env.py assumptions, async-vs-sync engine friction), FALLBACK = inter-lead request to infra to add ONE ci.yml step (`cd backend && alembic upgrade head` with DATABASE_URL → meesell_test) BEFORE pytest. Open via memo + a row on OUR board; do NOT edit ci.yml directly. Prefer (a); document why if (a) blocked.

### 2.3 — Event-loop fixes (Class 4 loop)
Diagnose the 3 test_core_auth_rotation.py loop errors AFTER §2.1/§2.2 (may evaporate). If they survive: local valkey fixture (L34) is already loop_scope=function; residual is likely the module-level Lua SHA cache (_reset_lua_cache_for_tests resets it but a cached redis client/SHA may bind to a prior loop) OR lazy from_url attachment across session/function loop boundary. FIX SHAPE: ensure the rotation fixture's redis client is created AND first-awaited inside the function loop (the await client.ping() at L56 already does this — confirm no module-level singleton client is reused). If rotate_refresh_token caches a SHA against a dead-loop client, the reset must drop that cached client. Mirror the use_live_valkey "fresh client per call in current loop" doctrine (conftest L145-167). Do NOT change `asyncio_default_fixture_loop_scope=session` in pytest.ini (§19.D-adjacent; db/db_engine session fixtures depend on it). Per-fixture loop_scope discipline, not a global flip.

### 2.4 — Genuine test-logic residue (Class 4 assertions)
After connection+schema fixes, re-run and triage SURVIVORS only:
- assert 200 == 429 (rate-limit ×2): expected to self-resolve (fail-open was the symptom). If survives WITH Valkey reachable → counter state bleed; ensure use_live_valkey pre-flush (L243-250 FLUSHDB) runs against the correct 6381 DB. Per-test unique IP already isolates. Do NOT weaken the assertion.
- assert 2 == 1 (audit coalesce): expected to self-resolve via working FLUSHDB. If survives → coalesce key not flushed; verify it lives in a flushed DB (DB 0). Fix flush coverage, NOT the assertion.
- GENUINE APP BUG CARVE-OUT (§6): if a survivor reveals a real app defect (not harness gap) — audit genuinely double-counts, rate-limit genuinely off-by-one — STOP, do NOT edit app code, FLAG in PR body under "App bug suspected — needs separate review" with failing test + evidence. Coordinator triages separate-ticket disposition at merge gate. Do NOT bury an app fix in this harness PR.

---

## 3. Verification gate (specialist MUST pass BEFORE the PR)
Target: `cd backend && pytest -m "integration" -v` exits 0 with the CI env shape.
CI ENV SHAPE (mirror Gate-4): TEST_DATABASE_URL=postgresql+asyncpg://meesell:password@localhost:5433/meesell_test ; TEST_VALKEY_URL=redis://localhost:6381/0 ; DATABASE_URL=(same as TEST_DATABASE_URL) ; VALKEY_URL=redis://localhost:6381/0 ; APP_ENV=development ; JWT_SECRET=ci-dummy-jwt-secret + the other 9 ci-dummy-* secrets from the Gate-4 env block.

REPRO SUBSTRATE — DOCKER DAEMON IS NOT RUNNING (verified this session: `docker info` fails; binary 28.4.0 present). Two-tier:
1. PREFERRED (if specialist can start the daemon): docker run -d --rm --name mc-pg -e POSTGRES_USER=meesell -e POSTGRES_PASSWORD=password -e POSTGRES_DB=meesell_test -p 5433:5432 postgres:16-alpine ; docker run -d --rm --name mc-vk -p 6381:6379 valkey/valkey:8-alpine. Identical images to CI. Tear down after (docker rm -f mc-pg mc-vk).
2. FALLBACK (daemon cannot start): use the founder's K3s dev port-forward (Postgres 5433) but CREATE a scratch `meesell_test` db on it for the run (CREATE DATABASE meesell_test; point TEST_DATABASE_URL at it with the DEV password). Valkey: if dev port-forward is 6380 not 6381, set TEST_VALKEY_URL/VALKEY_URL to the actual forwarded port for the LOCAL run only — the conftest code must HONOR env generically; the local repro port may differ as long as the env-var-precedence path is exercised. STATE the substitution + its limitation HONESTLY in PR Test-evidence (image-parity is the only delta vs CI).

PR EVIDENCE:
1. Before/after `pytest -m "integration" -v` summary line (was 21 failed/23 passed/151 errors; target 0 failed/0 errors, or 0 failed + a flagged §6 app-bug xfail/skip).
2. Proof the /0/0 double-suffix bug is absent (print resolved otp-client Valkey URL under TEST_VALKEY_URL=redis://localhost:6381/0).
3. Proof alembic upgrade head ran against meesell_test (\dx shows pg_trgm; \d categories shows GIN indexes).
4. Local-dev no-regression note: TEST_* unset → DB = K3s dev DSN, provision fixture no-op (assert by inspection; do NOT mutate the live dev DB to prove it).

CI DOES NOT RUN ON develop PRs (ci.yml triggers on push/PR to main only). The PR's pipeline will NOT exercise Gate 4 — LOCAL repro IS the gate. True CI confirmation = next develop→main PR (founder's gate). Make this explicit in the PR body.

---

## 4. Execution order (locked)
1. Connection/provisioning first: §2.1 (DB+Valkey precedence incl. /0/0 guard) + §2.2 (alembic-upgrade session fixture + extension) — the bulk of 151 errors.
2. Re-run `pytest -m "integration"` with CI env. Capture new summary.
3. Loop fixes (§2.3) for surviving Future-attached-to-different-loop.
4. Re-run. Triage assertion residue (§2.4).
5. Genuine app bugs (§6): flag, do not fix inline.
6. 1-2 iterations expected. Do NOT open PR until green (or green-modulo-a-flagged-app-bug).

---

## 5. Files the specialist MAY touch
- backend/tests/conftest.py — primary (env precedence L14-18/L56-59/L183/L398, new alembic-provision session fixture, loop hygiene).
- backend/tests/integration/conftest.py — only if the integration path needs the provision fixture wired (should inherit; touch only if necessary).
- backend/tests/test_core_auth_rotation.py — ONLY fixture/loop hygiene if §2.3 residue requires; NOT the assertions.
- A tiny URL-normalization helper (new private fn in conftest, or inline) for the /0/0 guard.

---

## 6. Scope fence — MUST NOT touch
- .github/workflows/ci.yml — infra-owned, provably correct. Touch only via §2.2.A inter-lead request if option (a) blocked.
- Production app code (backend/app/**) — UNLESS a test reveals a genuine app bug → FLAG (§2.4 carve-out), do NOT fix in this PR.
- frontend/, k8s/, terraform/, VM/infra config.
- backend/pytest.ini markers/asyncio_mode/asyncio_default_fixture_loop_scope/addopts — §19.D-locked. Do NOT flip session loop-scope (§2.3). (§2.1 fixes are in conftest.py.)
- nightly/slow/perf/ai_eval/golden_roundtrip markers + their tests — untouched. integration bucket only.
- §19.D 6-fixture real-vs-mock contract — preserved (db+valkey real; adapters mocked; no SQLite/fakeredis).
- Alembic migration files — do NOT hand-edit any applied migration. The fix RUNS the chain, does not modify it.
- Do NOT add a category/catalog SEEDER — tests self-seed (§1.C).

---

## 7. BACKEND_ARCHITECTURE.md lock check
No amendment required. §19.D governs the test CONTRACT (markers, real-vs-mock, strict flags) — all preserved. Honoring CI env + provisioning via the real alembic chain + per-function-loop hygiene are IMPLEMENTATIONS of the §19.D "real DB + Valkey via dev tunnel" policy, not deviations. Do NOT edit §19.D. (Same posture as the gate-1 §1.A additive ruling.)

---

## 8. Named specialist — meesell-services-builder (opus)
Async fixture engineering + event-loop hygiene + programmatic alembic invocation + multi-class failure triage across 2 iterations — materially heavier than the gate-1 config-only 2-line change (correctly sonnet routes-builder). Loop-attachment reasoning, the /0/0 URL guard, the alembic-in-conftest async/sync-engine seam, and the harness-gap-vs-app-bug judgment (§6) need opus reasoning. services-builder owns the deepest async+harness surface. Not auth-builder (not OTP/JWT/mw logic — it's the harness exercising them). Not database-builder (no ORM/migration AUTHORING — RUNS the existing chain).

---

## 9. Branch + PR shape
- Base: origin/develop (re-fetch; tip was e4c77de this session).
- Branch: fix/ci-gate4-integration.
- Worktree (master tree dirty with agent-memory edits — isolate):
  git -C /Users/mugunthansrinivasan/Project/mesell fetch origin
  git -C /Users/mugunthansrinivasan/Project/mesell worktree add /tmp/mesell-wt/ci-gate4-fix -b fix/ci-gate4-integration origin/develop
  (Confirm /tmp/mesell-wt/ci-gate4-fix free.)
- Commit message:
  fix(ci): make integration fixtures honor CI test env + provision meesell_test schema

  CI Gate 4 (integration) RED on run 27323036548 (21 failed, 23 passed, 151
  errors). Four classes: (1) _DEV_DATABASE_URL ignored TEST_DATABASE_URL ->
  asyncpg auth fail; (2) live-Redis fixtures defaulted to 6379, CI maps 6381;
  (3) meesell_test created empty (no alembic upgrade) -> pg_trgm/categories
  missing; (4) loop-scope + assertion cascades off (1)-(3). Fix: env-var
  precedence (TEST_* > DEV_*/VALKEY_* > local default, with /N suffix guard),
  session-scoped alembic-upgrade-head provision fixture (gated on
  TEST_DATABASE_URL so laptop dev DB is untouched), per-function-loop hygiene.
  Section 19.D real-DB contract preserved; ci.yml untouched.

  Session: mesell-ci-gate4-fix-session-1
- PR: fix/ci-gate4-integration -> develop. Standalone CI hotfix (no feature/{name}/backend parent) so the D1 group-gate does not apply; develop->main remains the founder's gate.
- PR body fills .github/PULL_REQUEST_TEMPLATE/backend.md completely. N/A sections (Alembic — N/A, RUNS the chain, adds no migration; endpoint inventory — N/A, §17 stays 28; OpenAPI — N/A; contract — N/A no FE/AI memo): write the explicit N/A sentence, NEVER a placeholder. Paste §3 verification into Test evidence. Add "App bug suspected" heading ONLY if §6 triggered.

---

## 10. Merge-gate review checklist (coordinator, STEP 3)
- [ ] Diff confined to backend/tests/conftest.py (+ optionally tests/integration/conftest.py, test_core_auth_rotation.py fixture-only). NO backend/app/** change. NO ci.yml change.
- [ ] Env-var precedence correct for BOTH DB and Valkey; /0/0 double-suffix demonstrably absent (evidence).
- [ ] Local-dev no-regression: TEST_* absent -> DB = K3s dev DSN, provision fixture no-op. Stated + reasoned.
- [ ] Schema provisioning runs the FULL alembic chain (pg_trgm + GIN present), gated on TEST_DATABASE_URL so live dev DB is never mutated by a laptop run.
- [ ] No category/catalog seeder added (tests self-seed).
- [ ] §19.D real-vs-mock preserved (db+valkey real; adapters mocked; no SQLite/fakeredis). pytest.ini markers/asyncio/loop-scope untouched.
- [ ] pytest -m integration evidence: before (21 failed/151 errors) -> after (0 failed/0 errors, or 0 failed + a flagged §6 app-bug xfail/skip). Repro substrate + limitation stated honestly (docker down -> fallback acceptable IF env-precedence + alembic-provision + loop fixes all exercised).
- [ ] Any §6 app-bug flag SURFACED (not buried) — coordinator decides separate-ticket.
- [ ] PR template fully filled; zero <> placeholders; N/A explicit.
- [ ] Commit footer = Session: mesell-ci-gate4-fix-session-1. Branch from origin/develop; PR -> develop.
- [ ] §2.D matrix + §16 import-linter untouched. §17 stays 28. No FE/AI/data memo (no contract/schema/prompt change).
- [ ] CI does NOT run on develop PRs — LOCAL repro is the gate. Next develop->main PR is where Gate 4 truly re-greens (founder's gate). If that main PR shows Gate 4 still RED, no silent block — re-open with new failure pasted.
- [ ] After merge: squash-merge; notify infra (close/return handoff_ci_gate4_integration via memo); update feature_board_backend.md -> MERGED + move to Recently merged; STATUS_BACKEND.md UPDATE block.
