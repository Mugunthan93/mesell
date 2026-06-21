---
name: razorpay-integration-merged
description: Razorpay Subscriptions (Waves 1-5) MERGED to develop 2026-06-20 via PR #323 (merge commit 8b5dce2). Code complete + on develop. Go-live deploy items remain (founder/deploy-time).
metadata:
  type: project
---

Razorpay Subscriptions integration is **MERGED to develop** (2026-06-20, merge commit `8b5dce2`, PR #323). develop tip = `8b5dce2`. All 5 waves verified present on develop (W1 db `dd08a50`, W2 adapter/webhook `4aea65d`, W3 entitlement/routes `692345b`, W4 reconcile beat `cc68ae6`, W5 billing FE `475dc59`) plus the alembic merge migration `e9415bdcae20` (single head: down_revision tuple `('d4e5f6a7b8c9','f8fa7a36383f')`).

**Why merged via a long CI-green grind, not instantly:** founder said "merge it once green" but the PR was BLOCKED by a *gated/cascading* CI where every downstream gate had been short-circuited by an early failure. Fixing each gate revealed the next. The chain of fixes (all legit, all Razorpay-introduced or merge artifacts):
1. **CI Gate 1 unit** — `ModuleNotFoundError: pkg_resources`: the new `razorpay==1.4.2` SDK imports pkg_resources at import time; setuptools isn't bundled in py3.12 CI → cascaded to ALL test modules via the app import chain. Fix: `setuptools>=70,<81` in `backend/requirements.txt` (`4091d24`). **The `<81` bound is load-bearing — setuptools 81 removes pkg_resources.**
2. **FE Gate lint (strict)** — FE-2 scanner tripped on a *comment* literally containing `pi pi-wallet` in `sidebar.nav-groups.ts`. Fix: reword comment (`65cf6c6`).
3. **CI Gate 2 smoke** — 5 inventory tripwire-guards hardcoded the route/task list; Razorpay legitimately added 4 `/api/v1/billing/*` routes (→ 34 routes total, was 30) + `app.modules.iam.tasks` celery module. Fix: bump the guards (`65aeb96`). Billing confirmed correctly V1-modular wired (flag-gated `FEATURE_BILLING_ENABLED`).
4. **CI Gate 4 integration (a)** — alembic MULTI-HEAD (billing `f8fa7a36383f` vs develop's pricing `d4e5f6a7b8c9`, both branched from google `c2d3e4f5a6b7`). Fix: merge migration `e9415bdcae20` (`669fdc2`).
5. **CI Gate 4 integration (b)** — 2 Wave-3 billing tests were env-dependent (asserted a sentinel key_id + plan-IDs that CI's minimal env doesn't set; settings is an import-time singleton so the file's `os.environ.setdefault` was too late). Fix: autouse fixture monkeypatching `settings.RAZORPAY_KEY_ID` + 5 `RAZORPAY_PLAN_ID_*` on the live singleton — covers all 22 billing tests (`424d007`). Route/service were CORRECT, not patched.
- Gate 3 (lint 10 contracts) and Gate 5 (golden_roundtrip) passed first time once unblocked.

**How to apply / lessons:**
- This gated CI hides downstream failures behind upstream ones — when fixing one gate, expect the next to surface; budget for several push→watch cycles. Required contexts (branch protection on develop): Gate 1-5 + FE lint + 8 frontend builds.
- Dev-DB guard from [[pytest-wipes-dev-db]] held the entire session — every DB-touching dispatch used a disposable TEST DB (e.g. meesell_rzpw2_test, meesell_alembic_merge_test); dev `meesell` verified still 3,772 categories after.
- gh credential helper can't read the keyring in the non-interactive shell → push/fetch via `git ... "https://x-access-token:$(gh auth token)@github.com/Mugunthan93/mesell.git"`.
- Merged with a **merge commit** (not squash) to preserve wave history; develop allows all 3 methods.

**STILL OUTSTANDING — go-live deploy items (founder/deploy-time, NOT code; full runbook `docs/runbooks/razorpay-golive.md`):**
1. 🔴 Create the 5 Razorpay dashboard Plan objects (test→live) and set `RAZORPAY_PLAN_ID_*` + the 3 secrets per namespace (Secret Manager → K8s).
2. 🔴 Deploy the Celery **beat** process — dedicated single-replica Deployment (`worker.yaml` runs 2 replicas, so `worker -B` would double-fire); manifest in the runbook.
3. 🔴 Register the Razorpay webhook (11 events) → `RAZORPAY_WEBHOOK_SECRET`.
4. 🔴 Full-fleet rebuild of all 7 remotes from one `libs/core` commit (W3 widened `@mesell/core` entitlement → federation singleton/logout bug if skipped — see master memory `finding-federation-auth-singleton-not-shared`).
5. 🟡 CSP additions for Razorpay hosts already in `frontend/docker/csp-policy.env` (`63b84a9`) — activate via frontend image rebuild/pod restart.

Non-blocking: V1.5 `--mee-color-warning-subtle` token; cosmetic `EntitlementLitlement` typo in `billing-poll.util.ts`; billing i18n namespacing pass. Integration worktrees under `/tmp/mesell-wt/` can be pruned.

**DEV-MOCK for local manual testing (MERGED to develop 2026-06-20, PR #325, merge `0203f2a`):** flag-gated dev-only Razorpay mock (`RAZORPAY_DEV_MOCK=true` in backend/.env; force-disabled when APP_ENV=production via `razorpay_mock_active` property). Subscribe creates a fake `sub_mock_*` sub then replays a synthetic webhook through the REAL `_route_webhook_in_session`→`_grant_plan_for_sub` path; FE `plans.component` skips the Razorpay modal when `checkout.mock` and polls → card flips to active. No account/keys/tunnel needed. `adapters/razorpay_mock.py`, `tests/test_billing_mock_mode.py` (7 tests). mfe-billing (:4207) was also wired into the static-dev tooling (build/serve/start-all/route-check) — it had been missing. **To test:** RAZORPAY_DEV_MOCK=true → /mesell:dev → login OTP `000000` → Plans → Subscribe → Pro active.
✅ **CI gap FIXED (PR #326, merged to develop 2026-06-20):** added mfe-billing to ci.yml frontend matrix (outputs `mfe_billing` + paths-filter `frontend/apps/mfe-billing/**` + matrix include `unit/project: mfe-billing`) → `Frontend: mfe-billing` build job; then added that context to develop's required branch-protection checks (now 15 required: 5 CI gates + FE-lint + detect + 8 frontend units incl. mfe-billing). mfe-billing is now built+gated like every other remote.
