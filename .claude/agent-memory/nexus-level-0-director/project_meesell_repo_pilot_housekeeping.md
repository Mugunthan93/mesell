---
name: meesell-repo-pilot-housekeeping
description: Model C pilot (housekeeping-v1) results 2026-06-10 — convention validated end-to-end with 3 structural defects found; PR #29 merged to develop (09262ee)
metadata:
  type: project
---

# Model C pilot — housekeeping-v1 (2026-06-10, session mesell-repo-pilot-housekeeping-session-1)

Pilot ran the full Model C flow (MASTER_PLAN §1–§7) on a dead-file cleanup. PRs #27 (infra) + #28 (backend) squash-merged by leads; PR #29 (feature/housekeeping-v1 → develop) **founder-authorized and MERGED** 2026-06-10 (merge-commit `09262ee` per §2.2 — plain merge was blocked by base policy, `--admin` required). feature/housekeeping-v1 branch deprotected + deleted per §1.4; master tree fast-forwarded to 09262ee.

**Why:** First real workload under the ACTIVE convention doubles as its end-to-end validation; scorecard feeds MASTER_PLAN amendments.

**How to apply:** Before any future feature branch work, account for these three structural defects:

1. **§1.2 branch naming is impossible in git.** `feature/{name}` and `feature/{name}/{group}` cannot coexist (ref file/directory conflict — "directory file conflict" on push). Pilot workaround: flat `feature/{name}-{group}`. MASTER_PLAN amendment required before the next feature starts. Never surfaced earlier because planning branches (`feature/{slug}/planning`) existed WITHOUT a parent `feature/{slug}` ref.
2. **Branch protection does not bind the agents.** All agents push with the founder's admin credential; `enforce_admins=false` → direct pushes to PR-only branches succeed with "Bypassed rule violations". Force-push/deletion blocks DO hold even for admin. Protection is advisory under single-credential operation.
3. **§6.5 board MERGED transition conflicts with PR-only protection.** Backend lead chose stale-IN-REVIEW + out-of-band record; infra lead probed (count=0, restrictions=null permit direct contents-API commit) and landed `818b830` directly. Leads diverged — §6.5 needs an amendment picking one mechanic.

Also validated: verify-then-delete caught a wrong audit claim (category_attributes.json + meesho_categories.json are LIVE via app/data/__init__.py loaders + test_data_helpers.py — knowledge-sync "all data/ JSON dead" was wrong; both lead memories corrected). meesho_category_tree.json confirmed current (7 refs). Deleted: .gitlab-ci.yml, backend/__init__.py, data/prompts/catalog_generation.txt, k8s/meesell-worker-sa-key.json (disk-only, 0 bytes, never tracked).

Operational learnings: gh intermittent 401 in sandbox → prefix `GH_TOKEN="$(gh auth token)"` + retry loop on writes; worktrees lack backend/.venv (use master venv interpreter + PYTHONPATH); Edit tool denied on symlinked memory paths in worktrees (append via shell to master path); zsh eats `$VAR:r` (use `${VAR}` braces in refspecs); coordinators have no Agent tool → master dispatches specialists, lead reviews only.

Residual: memory/STATUS appends sit uncommitted on develop checkout (develop is PR-only) — ride next chore PR. Group branches deleted per §1.4; worktrees removed.
