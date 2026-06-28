## Three founder rulings landed — 2026-06-11 (mesell-land-infra-rulings-infra-session-1)

PR #48 SQUASH-MERGED to develop. Squash SHA `32b350f`. Worktree `/tmp/mesell-wt/land-infra-rulings` on `chore/land-infra-rulings` from `origin/develop` (0b147e8). Master tree never switched branch. ₹0/month.

**Rulings landed (all additive/corrective, 4 files, all infra-owned):**
1. **F1 RESOLVED — APP_ENV**: `k8s/config.yaml` dev ConfigMap (`namespace: dev`) `APP_ENV "production" -> "development"`. Founder ruled prod was wrong for dev. Did NOT touch staging overlay or prod. The prior auth-otp session (PR #45) carried F1 as a *flag*; this session is the *resolution*.
2. **Deploy gate**: `INFRASTRUCTURE_PLAYBOOK.md` §15 "Safe deployment template" step 3 elevated to `[MANDATORY GATE]` — `kubectl apply --dry-run=server` is mandatory at EVERY deploy, hard precondition for the real apply. Founder ruling in-prompt = the §7.3 playbook-amendment approval (this is HOW the playbook gets amended — never unilaterally).
3. **MSG91 precondition**: added "Dev OTP smoke preconditions" subsection to `STATUS_INFRA.md` next-steps (founder whitelists dev server IP in MSG91 before first dev OTP send).

**KEY GOTCHA — `docs/runbooks/auth-secret-rotation.md` + `k8s/overlays/staging/` are NOT on `develop`.** They were created by the auth-otp session but merged to `feature/auth-otp/integration` (PR #45), and that integration→develop PR (#46) had NOT merged when this task ran. So in a worktree from `origin/develop` these files DO NOT EXIST. Any task that says "edit the runbook / staging overlay" must first check whether it's actually on `develop` vs still on a feature/integration branch. The STATUS_INFRA auth-otp SESSION-END entry listing those files as "merged" means merged to *integration*, not develop. This is why Task 3's "ONLY IF runbook smoke section exists" condition failed → fell through to STATUS_INFRA next-steps (the documented fallback). Self-folds into the runbook when #46 (or its successor) lands on develop.

**Process gotcha — `gh pr merge --squash --admin --delete-branch` from a worktree fails the branch-delete step** with `fatal: 'develop' is already used by worktree`. The MERGE itself succeeds (verify via `gh pr view <n> --json state,mergeCommit`); only the local `gh` cleanup (which tries to checkout develop) fails. Fix: delete the remote branch via API instead — `gh api -X DELETE repos/<owner>/<repo>/git/refs/heads/<branch>` — then `git worktree remove --force` + `git branch -D` from the master tree. Do NOT rely on `--delete-branch` when merging from a worktree whose base branch is checked out elsewhere.

**Offline validation pattern when cluster unreachable (F3 deferral):** `kubectl --dry-run=client` STILL contacts the cluster for API discovery (openapi / api group list) → fails with 6443 connection refused when the cluster is down. It is NOT a true offline validator. The authoritative offline check for a manifest value change is `python3 -c "yaml.safe_load_all(...)"` asserting kind/namespace/the-changed-key. Server-side dry-run is genuinely deferred to deploy time per F3 — and ruling #2 above now codifies that deferral as a mandatory-but-deferrable gate.

---
