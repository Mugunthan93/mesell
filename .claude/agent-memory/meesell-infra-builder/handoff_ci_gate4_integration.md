# Handoff — CI Gate 4 (integration) RED — backend test-harness, not infra

**From:** meesell-infra-builder
**To:** meesell-backend-coordinator
**Opened:** 2026-06-11 (mesell-ci-activation-session-1, re-fire #3)
**Run:** 27323036548 (push to main `a5cb4420`, PR #89 develop→main merge). Gates 1/2/3 GREEN; Gate 4 RED; Gate 5/Build/Deploy SKIPPED (sequential `needs:`).
**Result line:** `21 failed, 23 passed, 647 deselected, 151 errors in 62.50s`

## Context — the prior barriers are CLOSED
- Collection (`ModuleNotFoundError: app`) CLOSED by PR #73/#74/#75 (`pythonpath=.`).
- §5.D env-guard CLOSED by PR #76 (17 dummies).
- Marker-application exit-5 (`0 selected`) CLOSED by PR #85 (`34d8b47`) — 823 tests now §19.D-tagged. **Gates 1 (unit), 2 (smoke), 3 (lint) now PASS.** This is the marker request — RESOLVED.
- The next barrier is Gate 4 integration, below. This is the FIRST time the suite executes against live service containers.

## Diagnosis — ALL backend test-harness owned. The infra ci.yml Gate 4 service+env block is CORRECT.
ci.yml (origin/main) Gate 4 provides: Postgres `meesell:password@...:5433/meesell_test` (mapped 5433:5432) and Valkey on 6381:6379, with env `TEST_DATABASE_URL`/`DATABASE_URL`=...5433/meesell_test and `VALKEY_URL`/`TEST_VALKEY_URL`=redis://localhost:6381/0. All consistent.

The failures come from `backend/tests/conftest.py` (on develop `34d8b47`) NOT honoring those env vars in the live/dev fixtures:

1. **Postgres auth/db mismatch → `asyncpg InvalidPasswordError` (test_database.py, 6 fails).**
   conftest L56-58: `_DEV_DATABASE_URL` defaults to `postgresql+asyncpg://meesell:j3w%2F...@localhost:5433/meesell` (URL-encoded **K3s-dev cluster password**, db `meesell`). It only overrides from `DEV_DATABASE_URL` (which CI does NOT set), NOT from `TEST_DATABASE_URL`. The `db`/dev fixtures (L309, L328) use `_DEV_DATABASE_URL` → wrong password + wrong db (`meesell` vs `meesell_test`) → auth fail against the CI postgres on 5433.

2. **Redis on 6379 → `redis.ConnectionError [Errno 111]` (many: plan_guard, iam logout, category suggest).**
   conftest L183 + L398: live-Redis fixtures default to `CORE_TEST_VALKEY_URL` = `redis://localhost:6379`. CI maps Valkey to **6381** and sets `VALKEY_URL`/`TEST_VALKEY_URL` (6381) but NOT `CORE_TEST_VALKEY_URL` → fixtures hit 6379 → refused.

3. **`operator class "gin_trgm_ops" does not exist` + `relation "categories" does not exist`.**
   Integration test DB setup does not `CREATE EXTENSION pg_trgm` and does not apply migrations/seed the schema before the trigram/category tests run. (The trgm failure aborts the txn → cascading "categories does not exist".)

4. **`got Future attached to a different loop` (test_core_auth_rotation.py, 3), `assert 2 == 1` (audit coalesce), `assert 200 == 429` (rate-limit mw, 2).**
   Backend async-fixture loop-scope + assertion logic.

## NOT the known suspect
This is NOT the `test_config.py` importing `app.config` (moved to `app.shared.config`) suspect from prior memory. Gates 1-3 collected and passed cleanly; this is integration-bucket runtime failures, not a collection/import error.

## Fix is BACKEND-owned (two viable shapes — backend-coordinator's call)
- **(A) conftest honors the test env vars** (preferred): make `_DEV_DATABASE_URL` fall back to `TEST_DATABASE_URL`, and `CORE_TEST_VALKEY_URL` fall back to `TEST_VALKEY_URL`/`VALKEY_URL`. Plus add `CREATE EXTENSION IF NOT EXISTS pg_trgm` + run migrations/seed in the integration DB setup fixture. Plus fix the loop-scope + the 3 assertion bugs.
- **(B) CI also exports `DEV_DATABASE_URL` + `CORE_TEST_VALKEY_URL`** — papers over (1)+(2) only, and STILL fails on the password/db (CI postgres is `password`/`meesell_test`, the baked dev DSN wants the cluster password + db `meesell`). Brittle; does NOT fix (3) or (4). I do NOT recommend a CI-only patch; the conftest gap is the real bug.

**I (infra) am NOT changing ci.yml or backend/ — the ci.yml service block is provably correct.** If backend decides the cleanest fix touches ci.yml env (option B partial), open an inter-lead request back to me with the exact var names and I'll add them — but the password/db/extension/loop bugs (1 password-half, 3, 4) cannot be fixed from ci.yml.
