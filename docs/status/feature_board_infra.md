# Feature Board — Infra Lead

**Lead agent:** `meesell-infra-builder`
**Domain:** infra
**Last updated:** 2026-06-11 (ci-activation RE-FIRED — PR #78 merge `218aa83` develop→main; push run 27320321536 RED: Gate-1 marker deselect-to-zero exit5; BLOCKED on backend test-tagging)
**This file is the single domain-level status surface for the lead.**

---

## Active features

| Feature | Group branch | Status | Current session | Last touched | Blocking | Notes |
|---|---|---|---|---|---|---|
| ci-activation | (no branch — TF/GitHub-settings ops) | BLOCKED | — | 2026-06-11 | backend — §19.D gate markers applied to ZERO of 823 tests; every marker-gated gate deselects-to-zero (exit 5); see inter-lead request + handoff_ci_gate_markers.md | RE-FIRED on founder authorization: PR #78 (develop→main) MERGED merge-commit `218aa83d9af2396f02a9a53da291d5a9092e4415` (develop preserved `2662e5b`). Push run **27320321536** = FAILURE. PROGRESS: Gate-1 collection fix (pythonpath=.) + §5.D env-guard (PR #76) both WORKED — 823 items collected cleanly, config guard passed. NEW failure: `pytest -m "unit"` selects 0/823 → exit 5 (`collected 823 / 823 deselected / 0 selected`). Root cause: NO test carries `@pytest.mark.unit` (0 files for all 7 §19.D markers; no `pytest_collection_modifyitems` hook). SYSTEMIC — gates 2(smoke)/4(integration)/5(golden_roundtrip) + nightly(slow/perf/ai_eval) will hit the same exit-5. Gates 2-5+build+deploy SKIPPED (sequential needs). 3 frontend jobs GREEN; nightly skipped. WIF + Cloud Build + IAP deploy STILL UNPROVEN (sequential-blocked on BOTH fires). Branch-protection still DEFERRED until a green run. GEMINI_API_KEY_CI still founder-pending (nightly-only). Cost ₹0. |
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
| backend-coordinator | ci-activation | Re-fire run 27320321536 RED — §19.D gate markers (`unit`/`smoke`/`integration`/`golden_roundtrip`/`slow`/`perf`/`ai_eval`) are REGISTERED in pytest.ini but applied to ZERO of 823 tests (0 files match `pytest.mark.<m>` for all 7; no `pytest_collection_modifyitems` hook). `pytest -m "unit"` selects 0 → exit 5 → RED. SYSTEMIC across all marker-gated gates + nightly. Fix backend-owned: tag the suite per §19.D bucket (explicit `@pytest.mark` OR conftest auto-marking hook), complete across all buckets so each gate selects >0. See handoff_ci_gate_markers.md. | 2026-06-11 | OPEN |

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
