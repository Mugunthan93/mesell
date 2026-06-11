# Feature Board — Backend Lead

**Lead agent:** `meesell-backend-coordinator`
**Domain:** backend
**Last updated:** 2026-06-11 (CI Gate-4 integration fix PASS 2 MERGED — PR #107 squash `df93208` → develop; module-conftest loop-scope (24 fixtures) + customer_client env/provision-aware + 4 test_seeded_* skip-guard (BE-SEED-1). Merge-gate verified the field_enum_values-gate deviation as SOUND (pollution-robust prod-seed signal; no fixture writes field_enum_values — confirmed) and ACCEPTED it as honoring spec intent. BEFORE 63f/111p/4s/35e → AFTER 35f/135p/8s/14e (+24p/−28f/−21e). PASS 3 now IN FLIGHT (`fix/ci-gate4-integration-pass3`, session `mesell-ci-gate4-fix-session-3`) targeting true exit-0 modulo 4 is_leaf reds: savepoint per-test isolation + route-client loop hygiene + seed-skip extension. — mesell-ci-gate4-fix-session-3)
**This file is the single domain-level status surface for the lead.**

---

## Active features

| Feature | Group branch | Status | Current session | Last touched | Blocking | Notes |
|---|---|---|---|---|---|---|
| microservices-export | feature/microservices-export/backend | IN PROGRESS | mesell-microservices-backend-session-1 | 2026-06-10 22:55 IST | none | Sub-Plan A (SUB_PLAN_01) authored DRAFT; awaiting founder ratification of A1 (ai_ops) + A2 (middleware). Step 4 extraction execution is POST-V1. |
| ci-gate4-integration (pass 3) | fix/ci-gate4-integration-pass3 (standalone CI hotfix → develop, no group parent) | IN PROGRESS | mesell-ci-gate4-fix-session-3 | 2026-06-11 12:30 IST | none | Pass-3 closes the pass-2 out-of-fence residue (true exit-0 target modulo 4 is_leaf). Spec `spec_ci_gate4_fix_pass3.md` authored (full text in coordinator session output; memory-dir write blocked by isolation guard this turn). Fence (now INCLUDES tests/conftest.py — pass-1's file): (A) loop_scope on 3 route-client fixtures (customer_client/export_client/unauth_client) + port export_client's 3 unfixed env/provision defects (its twin customer_client got them in pass 2); (B) db_session connection+txn+rollback rewrite + route-client single-connection `join_transaction_mode="create_savepoint"` outer-rollback isolation (THE hardest piece — handler commit() → SAVEPOINT, teardown rolls back the FK-pollution) + audit_mw savepoint binding; (C) extend BE-SEED-1 skip (field_enum_values gate) to 4 category-seed + test_is_advanced_flag. is_leaf 4 reds STAY (BE-CAT-ISLEAF-1). Specialist: services-builder (THIRD round, deepest context). |

## Recently merged (last 14 days)

| Feature | Merged to | Date | PR | Notes |
|---|---|---|---|---|
| ci-gate4-integration (pass 2) | develop | 2026-06-11 | [#107](https://github.com/Mugunthan93/mesell/pull/107) (squash `df93208`) | **CI hotfix merge-gate PASS.** Standalone fix (`fix/ci-gate4-integration-pass2` → develop, no group parent — D1 N/A). 7 files: 4 module conftests (catalog/image/pricing/customer — 24 async db-fixtures got `loop_scope="function"`; grep-sweep zero bare fixtures; category/dashboard/export confirmed 0 async fixtures = no 5th defect) + `test_customer_routes.py` (customer_client 3 fixes: DB→`_DEV_DATABASE_URL`, Valkey→`_valkey_base()`, drop_all/create_all provision-aware setup+teardown; singleton-patch intact) + `test_database.py` (4 `test_seeded_*` runtime-skip on absent prod seed, BE-SEED-1) + `STATUS_BACKEND.md` (append-only session block). **DEVIATION RULING — ACCEPTED:** seed-skip gate keys on `COUNT(field_enum_values)==0` NOT the spec's `COUNT(categories)==0`. Coordinator VERIFIED the pollution argument at the gate: the only `db`-fixture FieldEnumValue writer (`test_crud_field_enum_value`) uses `flush()`+`delete()` and `db_session` rolls back → never persists; category conftest "intentionally adds nothing"; NO fixture commits field_enum_values (49 259-row enum seed is DATABASE-track only). So `field_enum_values==0` is pollution-robust while committing route fixtures defeat the literal `categories` gate. Honors spec INTENT; the literal gate would have re-surfaced the AssertionError → deviation is the CORRECT call. Provision-aware safety confirmed: gate `bool(os.environ.get("TEST_DATABASE_URL"))` → no TEST_* = drop_all/create_all unchanged byte-for-byte. BEFORE 63f/111p/4s/35e → AFTER 35f/135p/8s/14e (+24p/−28f/−21e); catalog service_unit 14→0, pricing 12→0, catalog integration 8→0. NOT exit-0 — residue (26 BaseHTTPMiddleware loop + 14 IntegrityError pollution + 5 category-seed + 4 is_leaf) all pre-existing, zero regressions, dispositioned to pass 3. §19.D preserved; ci.yml + pytest.ini + app code untouched; §17 stays 28. |
| ci-gate4-integration (pass 1) | develop | 2026-06-11 | [#104](https://github.com/Mugunthan93/mesell/pull/104) (squash `0b70219`) | **CI hotfix merge-gate PASS (12/12 §10 checklist).** Standalone fix. Single file `backend/tests/conftest.py` (+223/−18). Env precedence (TEST_DATABASE_URL/TEST_VALKEY_URL honored), /0/0 strip guard (`_valkey_base()`+`_strip_valkey_db_suffix()`), session-scoped autouse `_provision_test_schema` (DROP SCHEMA + pg_trgm + `alembic upgrade head`, gated on TEST_DATABASE_URL — SAFE: a no-TEST_* laptop run cannot DROP the live dev DB), db_engine provision-aware + NullPool + loop_scope. BEFORE 9f/38p/148e → AFTER 63f/111p/4s/35e (+73 passing/−113 errors). Residue dispositioned to pass 2. §19.D preserved; ci.yml + pytest.ini untouched; §17 stays 28. |
| ci-gate1-pytest-collection | develop | 2026-06-11 | [#74](https://github.com/Mugunthan93/mesell/pull/74) (squash bb09aea) | **CI hotfix merge-gate PASS 8/8.** Additive `pythonpath = .` in `backend/pytest.ini` fixes Gate-1 `ModuleNotFoundError: No module named 'app'`. **FLAG (infra-owned):** 5 dummy env vars missing from ci.yml (GCS_BUCKET, GCS_PROJECT_ID, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, CORS_ALLOWED_ORIGINS) → infra inter-lead OPEN. **DUPLICATE-MERGE REPAIR (PR #75):** a parallel session merged the identical fix as PR #73 (`1e95b2a`) → duplicate `pythonpath` key broke config-load → repaired to a single key in PR #75 + §19.D note. |
| smart-picker (backend group) | feature/smart-picker/integration | 2026-06-11 | [#72](https://github.com/Mugunthan93/mesell/pull/72) (squash ba94543) | **Backend group merge-gate PASS.** Smart Category Picker (V1 Feature 2) backend slice: `§9` VERIFY (zero drift) + `FEATURE_SMART_PICKER_ENABLED` flag guard + unit 9/9 + smoke 5/5 + ruff clean + token-free `ai_eval` (recall=100%). `_GLOBAL_TABLES` drift ACCEPTED as doc-vs-code; follow-up chore queued. |
| dual-pepper-rotation (integration→develop) | develop | 2026-06-11 | #66 (merge 50cdcef) | **Founder-gated merge MERGED.** R5 pre-V1.5-prod gate CLEARED. Version-tagged Valkey DB 0 allowlist key prefix + dual-pepper read fallback; additive config `REFRESH_TOKEN_PEPPER_PREVIOUS`/`REFRESH_TOKEN_PEPPER_VERSION`. |
| auth-otp (integration→develop) | develop | 2026-06-11 | #46 (merge cad0a9a) | **Founder-gated merge MERGED.** auth-otp (V1 Feature 1, FE-D5 split-token) fully on develop. |
| auth-otp (backend group) | feature/auth-otp/integration | 2026-06-11 | #44 (squash af6a619) | Backend group merge-gate. iam backend 100% built/contract-correct. Subsumed into develop via #46. |

## Inter-lead requests open

| To lead | About feature | Request | Opened | Status |
|---|---|---|---|---|
| meesell-infra-builder | ci-gate1-pytest-collection | Add 5 missing dummy env vars to the **Gate-1 (unit) env block** in `.github/workflows/ci.yml` (and the same set to Gate-2 smoke / Gate-3 lint / Gate-4 / Gate-5 / nightly env blocks where they run app code): `GCS_BUCKET`, `GCS_PROJECT_ID`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `CORS_ALLOWED_ORIGINS`. The app's §5.D startup guard (`app.shared.config`) fails-fast on these; PR #74 fixed the `import app` path so collection now REACHES that guard, but the guard still aborts CI until these dummies exist. Memo: `.claude/agent-memory/meesell-backend-coordinator/memo_ci_gate1_closed.md`. | 2026-06-11 | OPEN |
| meesell-infra-builder | ci-gate4-integration | Gate-4 (integration) harness fix progress: **pass 1 MERGED** (#104), **pass 2 MERGED** (#107 squash `df93208` — module-conftest loop-scope + customer_client + seeded-skip). **Pass 3 IN FLIGHT** (`fix/ci-gate4-integration-pass3`, session `mesell-ci-gate4-fix-session-3` — savepoint per-test isolation + route-client loop hygiene + seed-skip extension). ETA: ONE more specialist round, then Gate 4 re-fires on the next develop→main pipeline and should reach the 4-is_leaf floor (BE-CAT-ISLEAF-1, separate ticket). NO ci.yml change requested from any pass (skip-guard + savepoint isolation deliberately avoid a CI seed step). Still tied to the Gate-1 env-var request above (5 missing dummies gate the full pipeline). Memo: `.claude/agent-memory/meesell-backend-coordinator/handoff_ci_gate4_integration.md` (infra-owned, returned). | 2026-06-11 | OPEN |
| meesell-infra-builder | dual-pepper-rotation | Add `REFRESH_TOKEN_PEPPER_PREVIOUS` and `REFRESH_TOKEN_PEPPER_VERSION` to `k8s/secrets.yaml.example` + GCP Secret Manager onboarding notes. | 2026-06-11 | RESOLVED 2026-06-11 — landed PR #69 |

---

## Status vocabulary

| Status | Meaning |
|---|---|
| `PENDING` | Feature is on the lead's backlog; no branch exists yet. |
| `IN PROGRESS` | A `feature/{name}/backend` branch exists; specialist is actively committing. |
| `IN REVIEW` | A PR is open against `feature/{name}`; awaiting lead approval. |
| `MERGED` | The backend group's PR has merged to `feature/{name}` — the group is done for this feature. |
| `BLOCKED` | Work stopped pending an inter-lead request, infra change, or founder decision. |

A feature row stays on the Active features table until that group's PR merges to `feature/{name}`; then it moves to "Recently merged" for 14 days before being removed.

## Acceptance gate

Every `feature/{name}/backend` → `feature/{name}` PR must use `.github/PULL_REQUEST_TEMPLATE/backend.md` and pass the approval criteria in `.claude/agents/meesell-backend-coordinator.md` § "Merge gate". The lead (this agent) is the sole approver for this PR class per MASTER_PLAN.md D1.
