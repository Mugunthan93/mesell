# Feature Board — Backend Lead

**Lead agent:** `meesell-backend-coordinator`
**Domain:** backend
**Last updated:** 2026-06-11 (smart-picker BACKEND group MERGED to feature/smart-picker/integration — PR #72 squash ba94543; gate PASS; _GLOBAL_TABLES drift ACCEPTED as doc-vs-code + follow-up chore queued — mesell-smart-picker-backend-session-1)
**This file is the single domain-level status surface for the lead.**

---

## Active features

| Feature | Group branch | Status | Current session | Last touched | Blocking | Notes |
|---|---|---|---|---|---|---|
| microservices-export | feature/microservices-export/backend | IN PROGRESS | mesell-microservices-backend-session-1 | 2026-06-10 22:55 IST | none | Sub-Plan A (SUB_PLAN_01) authored DRAFT; awaiting founder ratification of A1 (ai_ops) + A2 (middleware). Step 4 extraction execution is POST-V1. |

## Recently merged (last 14 days)

| Feature | Merged to | Date | PR | Notes |
|---|---|---|---|---|
| smart-picker (backend group) | feature/smart-picker/integration | 2026-06-11 | [#72](https://github.com/Mugunthan93/mesell/pull/72) (squash ba94543) | **Backend group merge-gate PASS.** Smart Category Picker (V1 Feature 2) backend slice: `§9.B.1`/`§9.E`/`§9.G`/`§9.D` VERIFY (zero drift — service/schemas/repository/exceptions untouched) + `FEATURE_SMART_PICKER_ENABLED` 404-when-disabled flag guard (D2) + unit 9/9 + smoke 5/5 + ruff clean + token-free `ai_eval` CI job (run_eval 50/50 recall=100%). Benchmark `test_trigram_p95.py` infra-gated (slow/perf markers → not in blocking gate 4; runs in Nightly w/ live DB; EXPLAIN deferred to live tunnel). **RULING — `_GLOBAL_TABLES` drift:** ACCEPTED as doc-vs-code (zero runtime impact; carve-out honored by convention); follow-up database-builder chore queued to add the sentinel frozenset to `core/tenancy.py` (founder FYI, not a blocker). Merged on top of AI slice #54; rebase/order correct. Founder-gate PR (integration→develop) auto-updated, untouched per D1. |
| dual-pepper-rotation (integration→develop) | develop | 2026-06-11 | #66 (merge 50cdcef) | **Founder-gated merge MERGED.** R5 pre-V1.5-prod gate CLEARED. `feature/dual-pepper-rotation/integration` → `develop`; group PR #65 squash a2e566c. Version-tagged Valkey DB 0 allowlist key prefix (`cache:refresh:v{N}:{hmac}`) + dual-pepper read fallback; additive config `REFRESH_TOKEN_PEPPER_PREVIOUS`/`REFRESH_TOKEN_PEPPER_VERSION`. 8 fakeredis tests; baseline 27 passed / 3 skipped / 6 errors (infra-gated) no regression. Prod pepper rotation per runbook §2 now fully executable once secrets are provisioned at deploy time (infra PR #69). |
| auth-otp (integration→develop) | develop | 2026-06-11 | #46 (merge cad0a9a) | **Founder-gated merge MERGED.** `feature/auth-otp/integration` → `develop` = backend group #44 + infra group #45. auth-otp (V1 Feature 1, FE-D5 split-token) now fully on develop. Backend post-merge sentinels stamped: V1_FEATURE_SPEC.md Feature 1 + BACKEND_ARCHITECTURE.md §7 (this PR). |
| auth-otp (backend group) | feature/auth-otp/integration | 2026-06-11 | #44 (squash af6a619) | Backend group merge-gate. Re-audit: iam backend 100% built/contract-correct (plan said ~95%); no construction diff — iam already on develop. 11/11 §Review checks PASS. Now subsumed into develop via #46 (cad0a9a). |
| housekeeping-v1 | feature/housekeeping-v1 (integration) | 2026-06-10 | #28 | Sweep correction: PILOT_REPORT shows backend group PR squash-merged `6da5b80`; board row was stale at IN REVIEW (F2 conservative path). Moved to MERGED. |

## Inter-lead requests open

| To lead | About feature | Request | Opened | Status |
|---|---|---|---|---|
| meesell-infra-builder | dual-pepper-rotation | Add `REFRESH_TOKEN_PEPPER_PREVIOUS` and `REFRESH_TOKEN_PEPPER_VERSION` to `k8s/secrets.yaml.example` + GCP Secret Manager onboarding notes. Backend code is live (PR #65); infra must provision the new secret refs before the first prod rotation. | 2026-06-11 | RESOLVED 2026-06-11 — k8s/secrets.yaml.example + SM onboarding notes (INFRASTRUCTURE_ARCHITECTURE.md §4) landed PR #69 |

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
