## Session mesell-infra-microservices-infra-session-1 (S4 ratification package) — 2026-06-10

**Posture: ratification PACKAGE, not self-approval.** Like S5/MF, the founder rules on `docs/plans/infra/microservices_infra_plan.md` (stays DRAFT). I packaged the 3 open decisions + consistency check into the S4 session doc and returned to founder. ZERO cluster/TF/manifest mutations — Steps 3/4/5 of the dispatch (VM resize, PgBouncer, IngressRoute) are EXECUTION, deferred to post-V1 + founder ruling.

**The 3 decisions (recommendations):**
1. **VM `e2-standard-4`** (forced — `e2-standard-2` infeasible). Evidence: DRAFT §6.3 ≈2450–3400m CPU requests vs 2000m allocatable; GATE4 headroom ~350m free on current node (scheduler gates on REQUESTS not usage — live usage only 190m). MASTER_PLAN Rev 1.0 records the same "≥ e2-standard-4 (~₹2.5–6k/mo)". ~₹2,600/mo NEW spend = **>₹500/mo founder cost gate**.
2. **Gateway = Traefik path-prefix IngressRoute** — concurs with LOCKED MASTER_PLAN §2.C. Use FULL `/api/v1/<resource>/*` paths (MASTER_PLAN), not DRAFT's abbreviated `/auth/`.
3. **DB pools = B+C then A** — right-size pools + `max_connections=200` first (unblocks low-pool early extractions), PgBouncer transaction-pool mandatory before traffic cutover. Naive 8-svc = 360 conns; even right-sized = 133 > 100.

**Consistency check (DRAFT vs LOCKED MASTER_PLAN v1.1) — no blocking contradictions, 4 deltas:**
- **#1 must-fix:** DRAFT §6.1 recommends "(A) e2-standard-2 for V1 dev" — CONTRADICTS its own §6.3 math + R-MS-2 (Certain/High) + the LOCKED MASTER_PLAN. Stale line.
- **#2 should-fix:** gateway prefix shape — DRAFT `/auth/` vs MASTER_PLAN full `/api/v1/auth/`. MASTER_PLAN authoritative (matches 28 wired routes).
- **#3 note:** service naming — DRAFT `svc-auth…svc-billing` (invents `svc-billing`/`svc-quality`); MASTER_PLAN uses real backend modules `iam/customer/category/catalog/image/pricing/dashboard/export` (Razorpay-webhook lives in iam; plan_guard is core/, not a service). MASTER_PLAN authoritative — maps to `backend/app/modules/<module>/` + the LOCKED A–H extraction order.
- **#4 note:** namespace single-`dev`-per-env — consistent, no change.

**Option-C federation cross-check — KEY FINDING: the two migrations are CPU-orthogonal.** Per my GATE4_CONFIRMATION.md (C-RES-2), the 6 MF remotes ship as static GCS+Cloud-CDN bundles OUTSIDE K3s (0 in-cluster CPU); only the shell stays in-cluster (~0-net-CPU swap for retiring `frontend` Deployment). So the frontend migration consumes NONE of the dev node CPU headroom the MS topology needs → MS sizing (Decision 1) is computed on backend pods alone and is UNAFFECTED. Favorable: `e2-standard-4` sized purely for 8 backend svcs + infra, no frontend contention. No MS-math revision needed.

**Mechanics that worked:**
- Worktree `/tmp/mesell-wt/s4-infra-ms` on `chore/s4-infra-ms-prep` from `origin/develop` (tip a391671). PR **#35** → develop, **merged (merge commit) SHA `101308d798e82fb392619b8337bb21644141e5d5`** = develop tip. Commit `e927294`.
- **`gh pr merge --delete-branch` post-merge hook FAILS in a worktree** with `fatal: 'develop' is already used by worktree at <master tree>` — the auto `git checkout develop` can't run because develop is checked out in the master tree. **The remote merge STILL succeeds** (verified merged=true via `gh api .../pulls/35`). Cleanup the deleted-branch + worktree manually afterward: `git push origin --delete <branch>` + `git worktree remove --force` + `git branch -D`. Don't trust the merge command's exit/stderr — verify merged state via REST.
- `GH_TOKEN="$(gh auth token)"` prefix needed again for gh API under sandbox (401 otherwise). Single-file staged set verified via `git diff --cached --name-status` before commit.
- Surface discipline held: wrote ONLY `docs/plans/sessions/S4_INFRA_MICROSERVICES.md`. Did NOT touch `docs/plans/infra/` (DRAFT untouched), `docs/plans/module_federation/` (sibling S3), or `docs/plans/microservices_migration/` (sibling S2) — read-only cross-ref only.

---
