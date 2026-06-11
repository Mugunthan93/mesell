# Feature Board — Infra Lead

**Lead agent:** `meesell-infra-builder`
**Domain:** infra
**Last updated:** 2026-06-11 (ci-activation re-fire #3 run 27323036548 — Gates 1-3 GREEN via PR #85 markers; Gate 4 integration RED = backend test-harness; build/deploy still unproven)
**This file is the single domain-level status surface for the lead.**

---

## Active features

| Feature | Group branch | Status | Current session | Last touched | Blocking | Notes |
|---|---|---|---|---|---|---|
| ci-activation | (no branch — CI-config / GitHub-settings ops) | BLOCKED | — | 2026-06-11 | backend — Gate 4 (integration) RED: backend test-harness (conftest) ignores CI TEST_DATABASE_URL/TEST_VALKEY_URL for its live/dev fixtures + missing pg_trgm/seed + async-loop/assert bugs; see inter-lead request + handoff_ci_gate4_integration.md | **Re-fire #3 (FOUNDER-AUTHORIZED develop→main to first-exercise build/deploy which are `github.ref==refs/heads/main`-guarded).** PR #89 (develop `34d8b47`→main `218aa83`) MERGE-COMMIT `a5cb4420` (develop preserved). Push run **27323036548** (main `a5cb4420`) = FAILURE, but BIGGEST progress yet: **Gate 1 unit ✅ · Gate 2 smoke ✅ · Gate 3 lint ✅** (PR #85 `34d8b47` §19.D markers on 823 tests RESOLVED the exit-5 deselect-to-zero barrier) · **Gate 4 integration ❌** · Gate 5/Build/Deploy ⏭skipped(sequential needs:) · Frontend 3/3 ✅ · nightly+ai_eval ⏭skipped. Gate-4 line `21 failed, 23 passed, 647 deselected, 151 errors`: ALL backend test-harness — the infra ci.yml Gate-4 service block is PROVABLY CORRECT (PG `meesell:password@:5433/meesell_test`, Valkey 6381, env matches). conftest (`34d8b47`) bypasses it: (1) `_DEV_DATABASE_URL` L56-58 = baked K3s-dev pw on 5433 db `meesell`, only `DEV_DATABASE_URL`-overridable (CI doesn't set) → `asyncpg InvalidPasswordError`; (2) live-Redis fixtures L183/398 default `CORE_TEST_VALKEY_URL=localhost:6379` (CI uses 6381) → `redis.ConnectionError`; (3) no `CREATE EXTENSION pg_trgm` + no migrations/seed → `gin_trgm_ops`/`categories does not exist`; (4) loop-scope + `assert 2==1`/`assert 200==429` bugs. NOT the `test_config.py`/`app.config` suspect (collection is green). I did NOT modify ci.yml or backend/. WIF + Cloud Build + IAP deploy STILL UNPROVEN (Gate-4 cascade skips build/deploy). Branch-protection contexts still DEFERRED until green (founder-gated). GEMINI_API_KEY_CI still founder-pending (nightly-only). Cost ₹0. |
| auth-otp | feature/auth-otp/infra | IN REVIEW | — | 2026-06-11 | — | FE-D5 env-var wiring (dev=30/120; staging overlay=60/300) + auth-secret-rotation runbook. Base=feature/auth-otp/integration. |

## Recently merged (last 14 days)

| Feature | Merged to | Date | PR | Notes |
|---|---|---|---|---|
| dual-pepper-secret-refs | develop | 2026-06-11 | #69 (squash) | R5 inter-lead (from backend PR #65/#66) RESOLVED. Added REFRESH_TOKEN_PEPPER_PREVIOUS+VERSION to k8s/secrets.yaml.example + SM onboarding note in INFRASTRUCTURE_ARCHITECTURE.md §4 (NOT new SM secrets — PREVIOUS=prior pepper SM version kept ENABLED during grace window per runbook §2; VERSION=operator int). Docs/example only, no cluster/SM ops. Cost ₹0. |
| mf-ci-c-ci-1 | develop | 2026-06-11 | #50 (squash 86e67c8) | C-CI-1 DISCHARGED-pending-activation: ci.yml frontend paths-filter matrix (shell + mfe-pricing pilot, libs fan-out) REPLACING single-frontend conditional; cloudbuild shell-image + INERT GCS remote publish (`_REMOTES_BUCKET`). Config+docs only. Cost ₹0. |
| auth-otp | feature/auth-otp/integration | 2026-06-11 | #45 (squash d2b734e) | FE-D5 env wiring (dev=30/120; staging overlay=60/300) + auth-secret-rotation runbook. Founder-flags F1 (APP_ENV), F2 (single-pepper backend follow-up), F3 (dry-run-server at deploy). Cost ₹0. |
| gate4-confirmation | develop | 2026-06-10 | #33 (merge f30d61f) | MF §9 Gate 4 hosting confirmation — VERDICT CONFIRMED-WITH-CONDITIONS (6 conditions feed Sub-plan 7) |
| housekeeping-v1 | feature/housekeeping-v1 | 2026-06-10 | #27 (squash 6096244) | dead GitLab CI removal + SA key disk hygiene |

## Inter-lead requests open

| To lead | About feature | Request | Opened | Status |
|---|---|---|---|---|
| frontend-coordinator (incoming) | mf-workspace-foundation | MF CI prep C-CI-1 (handoff_mf_ci_prep.md) — replace single-frontend CI with paths-filter matrix before SP1 | 2026-06-10 | RESOLVED via PR #50 (merged develop) — frontend lead marks CLOSED on its own board |
| backend-coordinator | ci-activation | First main pipeline RED — Gate 1 `pytest -m unit` fails at COLLECTION: `from app.shared.database import` → `ModuleNotFoundError: No module named 'app'`. CI runs `pytest` in `working-directory: backend` with no PYTHONPATH and no installable pkg (`pytest.ini` §19.D LOCKED has no `pythonpath`; no pyproject/setup.py). Fix is backend-owned: add `pythonpath = .` to pytest.ini (founder OK — §19.D locked) OR add pyproject/setup.py + `pip install -e .`. See handoff_ci_gate1_collection.md. | 2026-06-11 | RESOLVED — backend pythonpath fix (#73/#74) closed collection; infra PR #76 (0f44d72) closed the resulting §5.D env-guard gap. Both sides done. |
| backend-coordinator | ci-activation | §19.D gate markers (`unit`/`smoke`/`integration`/`golden_roundtrip`/`slow`/`perf`/`ai_eval`) are REGISTERED in pytest.ini but applied to ZERO of 823 tests (0 files match `pytest.mark.<m>` for all 7; no `pytest_collection_modifyitems` hook). `pytest -m "unit"` selects 0 → exit 5 → RED. SYSTEMIC across all marker-gated gates + nightly; fixing only `unit` just moves red to Gate-2. Fix backend-owned: tag the suite per §19.D bucket (explicit `@pytest.mark` OR conftest auto-marking hook), complete across all buckets so each gate selects >0. First seen on PR #78 run 27320321536; RE-CONFIRMED on the develop trigger path — push run 27320468096 RED at Gate-1 exit-5. See handoff_ci_gate_markers.md. | 2026-06-11 | RESOLVED via PR #85 (`34d8b47`, merged develop) — 823 tests now §19.D-tagged; run 27323036548 Gates 1-3 GREEN. Backend marks CLOSED on its own board. |
| backend-coordinator | ci-activation | Gate 4 (integration) RED on run 27323036548 — `21 failed, 23 passed, 151 errors`. Backend test-harness (`backend/tests/conftest.py`) does not honor the CI-provided `TEST_DATABASE_URL`/`TEST_VALKEY_URL` for its live/dev fixtures: `_DEV_DATABASE_URL` (L56-58) hardcodes the K3s-dev cluster password on 5433/db `meesell` (only `DEV_DATABASE_URL`-overridable) → `asyncpg InvalidPasswordError`; live-Redis fixtures (L183/398) default `CORE_TEST_VALKEY_URL=localhost:6379` (CI maps Valkey to 6381) → `redis.ConnectionError`; integration DB setup lacks `CREATE EXTENSION pg_trgm` + migrations/seed → `gin_trgm_ops`/`categories does not exist`; plus async loop-scope + `assert 2==1`/`assert 200==429` logic bugs. The infra ci.yml Gate-4 service+env block is CORRECT (verified) — fix is backend (conftest honors TEST_* + pg_trgm + seed + loop/assert fixes). See handoff_ci_gate4_integration.md. | 2026-06-11 | OPEN |

---

## Status vocabulary

| Status | Meaning |
|---|---|
| `PENDING` | Feature is on the lead's backlog; no branch exists yet. |
| `IN PROGRESS` | A `feature/{name}/infra` branch exists; lead is actively committing. |
| `IN REVIEW` | A PR is open against `feature/{name}`; awaiting lead self-review approval. |
| `MERGED` | The infra group's PR has merged to `feature/{name}` — the group is done for this feature. |
| `BLOCKED` | Work stopped pending an inter-lead request, infra change, or founder decision. |

A feature row stays on the Active features table until the infra group's PR merges to `feature/{name}`; then it moves to "Recently merged" for 14 days before being removed.

---

## Acceptance gate

Group-PR approval criteria live in the infra PR template at `.github/PULL_REQUEST_TEMPLATE/infra.md`. The lead approves a `feature/{name}/infra` → `feature/{name}` PR only when the template is filled completely — including the `terraform plan` output (`Plan: X to add, Y to change, Z to destroy`), `kubectl apply --dry-run=server` clean output, secret refs documented with no JSON keys, Workload Identity Federation paths confirmed, smoke deploy to `dev` succeeded (`kubectl get pods -n dev` Ready), cost impact estimate recorded (with explicit founder sign-off for any change > ₹500/month) — plus CI gate-3 (lint — manifest validation) green and the rollback procedure for the resource type documented per `docs/INFRASTRUCTURE_PLAYBOOK.md`.
