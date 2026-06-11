# SPEC — CI Gate-4 (integration) test-harness fix — PASS 2

**Authored:** 2026-06-11 by `meesell-backend-coordinator`
**Rule 7 three-step:** STEP 1 of 3 (SPEC ONLY). STEP 2 = specialist executes. STEP 3 = coordinator reviews PR at merge gate.
**Predecessor:** `spec_ci_gate4_fix.md` (pass 1) — PR #104 MERGED to develop 2026-06-11 (squash SHA `0b70219576`). Pass 1 fixed the 3-file fence (conftest env precedence + /0/0 guard + alembic-provision + db_engine loop hygiene). Pass-1 result: `9f/38p/148e → 63f/111p/4s/35e` (+73 passing, −113 errors). The residue below is everything pass-1 correctly STOPPED on as OUT OF FENCE.
**Session token:** `mesell-ci-gate4-fix-session-2`
**Named specialist:** `meesell-services-builder` (opus) — continuity with pass 1.
**Branch:** `fix/ci-gate4-integration-pass2` from `origin/develop` (tip post-merge `0b70219576`).

## 1. Verified residue map (coordinator-confirmed against the live tree)
- Defect-bearing module conftests (async fixtures consuming db/db_session, no loop_scope): catalog (6/8), image (8/9), pricing (9/11), customer (1 — the `db(db_session)` alias). CLEAN (untouched): category (0), dashboard (0), export (db-deps are fake_* mocks with db=None, not fixtures).
- Each defect conftest redefines `@pytest_asyncio.fixture async def db(db_session): yield db_session`. Top-level db_session now carries loop_scope=function (pass 1), but the module alias + downstream (user/other_user/beauty_category/…) default to session loop (pytest.ini asyncio_default_fixture_loop_scope=session, §19.D-LOCKED) → "got Future attached to a different loop" + "another operation is in progress".
- test_customer_routes.py::customer_client (L67-209) THREE defects: (1) L114 Valkey hardcoded 6379 ignoring TEST_VALKEY_URL/VALKEY_URL (6381) → /otp/verify 429 ×9; (2) L102-105 DB default localhost:5432 wrong port (CI 5433); (3) L107-109/204-205 own drop_all/create_all vs the alembic-provisioned meesell_test → destroys GIN indexes + DROP-vs-open-txn contention pass 1 solved for db_engine.
- test_database.py::test_seeded_* (L1148-1191, 4 tests) bind dev_engine → meesell_test in CI; schema present, DATA empty (baseline zero INSERTs). Assert prod seed (≥321 Grocery cats, exactly-1 collapsed template, MAX value_count 4481, ≥1 field_alias.for_xlsx_export) → AssertionError.
- Category.is_leaf AttributeError ×4 (test_multi_tenant_isolation.py + test_category_schema_p95.py) — model has leaf_name not is_leaf. GENUINE app/test mismatch → carved to BE-CAT-ISLEAF-1, OUT of pass-2 scope.
- FK IntegrityError ×5 (pricing-persistence + iam) — suspected loop/seed cascade. Re-triage after 2.1+2.2.

## 2. Fix decisions (LOCKED)
### 2.1 Module-conftest loop-scope — files: catalog/image/pricing/customer conftest.py. Add loop_scope="function" to EVERY @pytest_asyncio.fixture depending (transitively) on db/db_session, starting with the `db` alias. DO NOT touch category/dashboard/export. Post-edit grep MUST show zero bare @pytest_asyncio.fixture in the 4 files (unless provably loop-agnostic). Sibling sweep: grep all tests/modules/*/conftest.py for fixtures lacking loop_scope; if a 5th defect surfaces, fix + PR-note.
### 2.2 customer_client (test_customer_routes.py, the fixture only): (1) reuse conftest _valkey_base() (import `from tests.conftest import _valkey_base`, or replicate _strip_valkey_db_suffix+_valkey_base verbatim — state which); (2) use `from tests.conftest import _DEV_DATABASE_URL` for the DB url (kills the 5432 default); (3) make drop_all/create_all provision-aware: `provisioned = bool(os.environ.get("TEST_DATABASE_URL"))`, skip setup+teardown drop_all when provisioned (mirror pass-1 db_engine). Leave the audit_mw/_cache_client singleton-patch logic INTACT.
### 2.3 Seeded-data tests — DECIDED: option (ii) runtime pytest.skip() guard. In each of the 4 test_seeded_* bodies, COUNT(categories); if 0 → pytest.skip("… tracked: BE-SEED-1 …"). NO seeder (49k enums blow ~3min budget; §19.D locks the seed-tables to DATABASE track). NO new marker (pytest.ini §19.D-LOCKED, --strict-markers). Skip gates on the data precondition — assertions NOT weakened.
### 2.4 FK re-triage after 2.1+2.2: cascade→note-resolved; harness gap in-fence→fix; genuine app cascade→FLAG (do not fix inline).
### 2.5 Category.is_leaf — OUT of scope; carved to BE-CAT-ISLEAF-1; 4 known-reds remain after pass 2.

## 3. Verification gate
Target: `cd backend && pytest -m integration -v` with CI env → exit 0 OR non-zero with ONLY {4 BE-SEED-1 skips} ∪ {4 BE-CAT-ISLEAF-1 known-reds} ∪ {any §2.4-flagged app bug}. NO loop-attach errors, NO customer_client 429, NO empty-seed AssertionError surfacing as failure.
CI env shape = pass-1 shape (TEST_DATABASE_URL meesell:password@localhost:5433/meesell_test; TEST_VALKEY_URL redis://localhost:6381/0; DATABASE_URL/VALKEY_URL same; APP_ENV=development; ci-dummy-* secrets incl. the 5 REQUIRED_FIELDS).
Repro substrate = pass-1 two-tier (docker images, else Homebrew PG16+Valkey on 5433/6381, backend/.venv Py3.11 + pytest 8.3.0/asyncio 0.24.0; state parity deltas honestly).
PR evidence: before (63f/111p/4s/35e) → after (enumerated skip+known-red set, 0 errors); post-edit grep proof; customer_client resolved-URL proof; local-dev no-regression by inspection.
CI does NOT run on develop PRs — local repro is the gate; next develop→main is the true re-green (founder's gate).

## 4. Execution order: 2.1 → 2.2 → re-run → 2.3 → 2.4 → re-run → enumerate residual.

## 5. Files MAY touch (LOCKED fence): tests/modules/{catalog,image,pricing,customer}/conftest.py; test_customer_routes.py (customer_client only); test_database.py (4 test_seeded_* only); + optional 5th conftest with PR note.

## 6. MUST NOT touch: backend/tests/conftest.py (pass-1 owns); ci.yml; pytest.ini (§19.D — no new marker, no loop-scope flip); backend/app/** (is_leaf is BE-CAT-ISLEAF-1); alembic versions; category/dashboard/export conftests; tests/integration/conftest.py (unless §2.4 proves a defect, PR-note); customer_client singleton-patch logic.

## 7. BACKEND_ARCHITECTURE.md lock check: no amendment. §2.1/§2.2/§2.3 are §19.D implementations; §2.3 skip deliberately avoids a pytest.ini marker change to keep §19.D's locked marker set intact.

## 8. Branch + PR: fix/ci-gate4-integration-pass2 from origin/develop (0b70219); worktree /tmp/mesell-wt/ci-gate4-fix-pass2; PR → develop (standalone CI hotfix, D1 N/A); template fully filled, N/A explicit, no placeholders; commit footer `Session: mesell-ci-gate4-fix-session-2`.

## 9. Merge-gate checklist (STEP 3): diff confined to §5 fence; §2.1 loop_scope + grep proof; §2.2 env-helper reuse + /0/0 absent + provision-aware drop_all + singletons intact; §2.3 BE-SEED-1 skip-guards, no seeder/marker, assertions intact; §2.4 survivors triaged/flagged; §2.5 is_leaf untouched + 4 known-reds enumerated; before/after evidence + substrate honesty; §19.D + §2.D + §16 preserved, §17 stays 28, no FE/AI/data memo; template filled; footer correct; CI-not-on-develop note; after merge squash + delete branch + clean worktree + board MERGED + STATUS block + notify infra.
