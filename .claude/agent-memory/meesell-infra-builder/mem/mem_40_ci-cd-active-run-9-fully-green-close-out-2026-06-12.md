## CI/CD ACTIVE — run-9 fully green — close-out — 2026-06-12

**THE CI/CD PIPELINE IS LIVE.** Run 9 (`27366269839`, merge SHA `62713935`, PR #132) is the **FIRST FULLY GREEN end-to-end pipeline** in project history: 5 backend gates + 8 frontend legs + Cloud Build + IAP deploy (token refresh → k3s restart → readyz → applies → settle wait → alembic migrate → image roll → rollout status → in-pipeline health check) + external `https://api.mesell.xyz/health` → 200. After this, "what's the CI/CD state" = ACTIVE; the long red-march is over.

**The 6-rung deploy-bug ladder (memorize the SHAPE — each rung is a distinct failure class, all now codified):**
1. **act-as on the compute SA** (PR #113) — `meesell-github-ci` needed `roles/iam.serviceAccountUser` ON `888244156264-compute@…` (Cloud Build's runner SA). `cloudbuild.builds.editor` lets you SUBMIT; act-as lets the build RUN as the compute SA.
2. **compute.viewer** (PR #116) — instance-scoped `instanceAdmin.v1` ≠ project-level `compute.projects.get`/`zones.get`. `gcloud compute ssh --tunnel-through-iap` resolves the target via project/zone reads BEFORE the tunnel → needs project-wide read (`compute.viewer`).
3. **AR pull auth** (PR #119) — K3s-outside-GKE pulls via `registries.yaml` metadata-server token (45-min cron + `systemctl restart k3s` to reload containerd; NO hot-reload). SA-key alt (#121) DEAD by org policy `iam.disableServiceAccountKeyCreation`; its puller SA + repo IAM member TF-destroyed.
4. **shallow-clone FETCH_HEAD** (PR #123, sibling) — VM clone has no `origin/main` ref → `git fetch origin main` + reset to FETCH_HEAD, never `git reset --hard origin/main`.
5. **unescaped `$(seq)`** (PR #127) — every `$` in `gcloud compute ssh --command="…"` must be `\$`-escaped unless runner-side (`${{ }}`) is intended; command substitutions are the worst offenders. Substitution-free `until`+counter loop removes the class.
6. **exec-on-terminating-pod settle wait** (PR #131) — `kubectl apply` is NOT inert ("X configured" = a rollout fired); on kill-before-surge the old pod terminates FIRST, so a following `kubectl exec deploy/<name>` races a dying pod → SIGKILL exit 137. Insert `rollout status` between apply and exec.

**Branch protection — APPLIED 2026-06-12, FOUNDER-RULED develop ONLY.** 13 required contexts (5 gates + frontend `detect` + 7 frontend units) + strict (up-to-date) + 1 review. **`main` deliberately has NO required checks** (founder ruling) — do NOT add them; it is intentional. NEVER add Build/Deploy (main-/push-only → would deadlock PRs) or Nightly/ai_eval (schedule-only) to any required-context set. When re-confirming exact context strings, list them from a real green run — the frontend matrix is 7 units (auth/catalog/dashboard/export/onboarding/pricing + shell) + detect, NOT the old 3-context list.

**Still pending (FOUNDER, non-blocking):** `GEMINI_API_KEY_CI` GitHub secret (quota-capped key from aistudio.google.com/apikey; consumed ONLY by nightly `ai_eval`). Does not affect the activated push/PR pipeline.

**V1.5 follow-ups (already in memory; reconfirmed):** migration-runs-in-OLD-image smell (proper fix = short-lived Job running `alembic upgrade head` on the NEW image, gated before `set image`); BE-SEED-1; legacy `github-pool`/`meesell-ci` WIF+SA orphan cleanup.

**Process lesson (durable):** NEVER chain a branch-delete unconditionally after a PR merge — gate on `merged == true`. The PR #124 incident (a delete fired on a non-merged path) was recovered via #126. Any "merge then delete branch" automation must read the merge result first.

**Close-out mechanics:** docs + 2 memory files only (board + STATUS_INFRA + this MEMORY + ONE authorized scribe-entry to the director's `project_meesell_ci_activation.md` — explicit master-session exception to memory-ownership rule 4). Branch `docs/ci-activation-close-out` off origin/develop. NOTE: develop now carries 13 required checks — the close-out PR itself must pass the gates before it can merge (expected; reported, not merged by me). Cost ₹0/month; zero cluster/TF/secret/ci.yml mutations.

---
