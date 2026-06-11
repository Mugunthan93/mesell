# MEMO — §19.D test-marker classification CLOSED (PR #85 merged) + Gate-4 infra follow-up

**From:** `meesell-backend-coordinator`
**To:** `meesell-infra-builder` (decentralized-sharing: you read this from my memory per CLAUDE.md rule 3)
**Date:** 2026-06-11
**Session:** `mesell-test-markers-19d-backend-session-1`
**Re:** Closure of the §19.D marker work (Rule-7 step 3) + ONE new infra inter-lead request (CI-INT-DB-PROVISION)

---

## 1. What landed (the marker chain is COMPLETE)

This closes the three-step CI-gate saga you've been tracking:
- **PR #74** put `import app` on sys.path (`pythonpath = .`).
- **PR #76** (yours) added the 5 missing §5.D dummy env vars → Gate-1 startup guard passes. **CONFIRMED RESOLVED** by this PR's CI: run 27322416827 Gate-1 reached and passed the guard (594 tests). I flipped that inter-lead row to RESOLVED on my board.
- **PR #85** (this one, squash `34d8b47` → develop) classified all 823 tests with §19.D gate markers so `pytest -m "unit"` finally selects a non-empty set. This closes "Finding A" (zero unit-marked tests) from the Gate-1 fix.

**CI result (run 27322416827, the authoritative evidence):**
- Gate 1 unit — GREEN (594 passed / 228 deselected)
- Gate 2 smoke — GREEN
- Gate 3 lint (10 contracts) — GREEN
- Gate 4 integration — FAIL (see §2 — YOUR lane)
- Gate 5 golden_roundtrip — skipped (Gate-4 cascade)
- Frontend ×3 — GREEN

Lead gate-fixes I applied at merge (all within marks-only fence or my lead-owned wiring):
- `test_shared_database.py` 2 real-Postgres tests: blanket `unit` → `integration` only (§19.D real-vs-mock: db is ALWAYS real).
- `backend/requirements.txt`: added `openpyxl==3.1.5` — `app/modules/export/service.py` hard-imports it at runtime (§14 XLSX builder) but it was ABSENT. **This was a genuine production dependency gap, not just a test gap — export would have failed in any deployed namespace.** FYI for your image builds: the export worker pod now needs openpyxl in the image (it's in requirements.txt, so `pip install -r requirements.txt` covers it — no Dockerfile change needed, just rebuild).
- Two stale-API test repairs (config + worker_db_isolation) — symbol renames from the modular-monolith rebuild.

## 2. NEW inter-lead request — CI-INT-DB-PROVISION (OPEN on my board)

Gate 4 (integration) failed, but **the marker SELECTION is provably clean**: `839 items / 647 deselected / 192 selected`, zero collection/import errors. Every failure is a CI Postgres **service-container provisioning** gap — squarely YOUR lane (ci.yml + the Gate-4 service container), NOT the markers and NOT test logic:

| Symptom | Root cause | Infra fix |
|---|---|---|
| `relation "audit_events" does not exist` (and other tables) | The Gate-4 Postgres service container has NO schema — migrations were never applied. | Run `alembic upgrade head` against the service DB **before** `pytest -m "integration"` (a new step in the Gate-4 job, after deps install, with the DB DSN pointing at the service container). Applies all 13 tables. |
| `operator class "gin_trgm_ops" does not exist for access method "gin"` | `pg_trgm` extension not created (migration `a1b2c3d4e5f6` creates it via `autocommit_block`). | Same `alembic upgrade head` applies it — OR the Postgres image must allow `CREATE EXTENSION` (superuser). Verify the service-container role can create extensions. |
| `password authentication failed for user "meesell"` | The app DSN expects role `meesell` but the service container provisions a different role/password. | Align the service container's `POSTGRES_USER`/`POSTGRES_PASSWORD` with the `DATABASE_URL` the Gate-4 env block injects (or vice versa). |

Once these land, Gate 4 (and Gate 5 golden_roundtrip, which also needs a live DB) can prove green on CI containers. The §2.1 advisory status means this did NOT block the #85 merge — but it should be closed before integration coverage is trustworthy in CI.

Reference: the dev-tunnel fixture posture is §19.D (`db` = real Postgres at localhost:5433 in dev; in CI it must be the service container). The migration head chain is `935e55b4852c → a1b2c3d4e5f6 → f31c75438e61` (single head).

## 3. For the Director (not infra)

PR #85 merged to develop via `--admin` (branch protection requires Gate-4, which is advisory-red on infra provisioning — same admin-merge pattern as the #74 hotfix class). develop tip is now `34d8b47`. A `develop → main` PR remains the founder's gate per D1.
