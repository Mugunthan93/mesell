# Feature Board — Infra Lead

**Lead agent:** `meesell-infra-builder`
**Domain:** infra
**Last updated:** 2026-06-11 (dual-pepper-secret-refs — R5 inter-lead resolved PR #69; ci-activation BLOCKED on backend Gate-1 collection fix)
**This file is the single domain-level status surface for the lead.**

---

## Active features

| Feature | Group branch | Status | Current session | Last touched | Blocking | Notes |
|---|---|---|---|---|---|---|
| ci-activation | (no branch — TF/GitHub-settings ops) | BLOCKED | — | 2026-06-11 | backend — Gate 1 unit collection error (ModuleNotFoundError: app) blocks pipeline; see inter-lead request to backend-coordinator | PR #64 MERGED (merge commit 0ea1988, develop→main, develop preserved). First main pipeline run 27318816408 = FAILURE: Gate 1 unit failed at pytest COLLECTION (conftest `from app.shared.database import` → ModuleNotFoundError: No module named 'app'; no PYTHONPATH/installable pkg). Gates 2-5+build+deploy SKIPPED (sequential needs). 3 frontend jobs GREEN; nightly correctly skipped. WIF/build/deploy unproven (never ran). Fix = BACKEND scope (pytest sys.path / packaging). Check contexts captured in STATUS_INFRA; branch-protection still DEFERRED until green. GEMINI_API_KEY_CI still founder-pending (nightly-only). |
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
| backend-coordinator | ci-activation | First main pipeline RED — Gate 1 `pytest -m unit` fails at COLLECTION: `from app.shared.database import` → `ModuleNotFoundError: No module named 'app'`. CI runs `pytest` in `working-directory: backend` with no PYTHONPATH and no installable pkg (`pytest.ini` §19.D LOCKED has no `pythonpath`; no pyproject/setup.py). Fix is backend-owned: add `pythonpath = .` to pytest.ini (founder OK — §19.D locked) OR add pyproject/setup.py + `pip install -e .`. See handoff_ci_gate1_collection.md. | 2026-06-11 | OPEN |

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
