## CI activation run-4 fix — act-as on compute SA — 2026-06-11

**Blocker:** `gcloud builds submit` (the build job in `.github/workflows/ci.yml`) failed for `meesell-github-ci` with `iam.serviceAccounts.actAs denied`. GitHub Actions run **27331720017** (run-4).

**Root cause:** Cloud Build in THIS project runs builds AS the Compute Engine default SA (`888244156264-compute@developer.gserviceaccount.com`) — the same quirk codified in `module.cloudbuild_permissions` (Phase D memory). To *submit* a build that runs as that SA, the submitting identity must hold `roles/iam.serviceAccountUser` (act-as) ON the compute SA. The legacy/manual CI SA `meesell-ci@...` had this grant out-of-band; the TF-managed `meesell-github-ci` SA never did. That gap was the run-4 blocker.

**Fix (codified, founder-ruled "Terraform-codified"):** added `google_service_account_iam_member.github_ci_act_as_compute` to `modules/ci_identity/main.tf` — `roles/iam.serviceAccountUser`, member `meesell-github-ci@...`, on `service_account_id = projects/.../serviceAccounts/888244156264-compute@developer.gserviceaccount.com` (compute SA hardcoded, matching sibling `cloudbuild_permissions/main.tf` style — not a var).

**Plan/apply:** `-target=module.ci_identity` plan = exactly `1 to add, 0 to change, 0 to destroy`. The benign billing-budget in-place change does NOT appear under this target (different module). Applied clean. Verified `get-iam-policy` on compute SA now lists BOTH `meesell-ci@` (legacy) and `meesell-github-ci@` (new) under `roles/iam.serviceAccountUser`.

**Stale-lock gotcha:** my prior halted run (killed by the bg-session write guard mid-plan) left an orphaned GCS state lock (`gs://meesell-tfstate/terraform/state/default.tflock`, Operation=Plan, ~7h old, same operator `root@Mugunthans-MacBook-Air.local`). Since the operation was a PLAN (never an apply) and clearly mine, `terraform force-unlock -force <lock-id>` was safe. RULE: a Plan-operation orphan lock from your own machine is safe to force-unlock; an Apply-operation lock needs investigation first.

**tfvars drift note:** root `variables.tf` now uses `founder_ip_ranges` (required, in `environments/dev.tfvars`), NOT the old per-session `founder_ip` /32 var. `postgres_password` / `valkey_password` now `default = null` (optional). For a `-target=module.ci_identity` plan they're not strictly needed, but passing them from `~/.meesell-secrets/dev-{postgres,valkey}-password` is harmless and keeps the command copy-paste-safe.

**Branch:** `ci/act-as-compute-fix`; worktree `.claude/worktrees/agent-a73bb701f6e9884f2`. PR to develop (do-not-merge — founder gate).

---
