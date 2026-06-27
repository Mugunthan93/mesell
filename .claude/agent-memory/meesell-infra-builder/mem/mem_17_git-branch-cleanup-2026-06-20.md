## Git branch cleanup (2026-06-20)

Safe branch-cleanup chore done on master tree (override `MESELL_ALLOW_MASTER_GIT=1`). Counts: local 219→32, remote 79→28. Deleted: 46 truly-merged (`git branch -d` after `--merged develop`), 109 squash-merged (matched against `gh pr list --state merged ... -q '.[].headRefName'`, force `-D` since squash leaves them "unmerged" to git), 24 `worktree-agent-*`, 8 named scratch (`pr252-merge`/`regate-rewind`/`__cf_integration`/etc), 51 remote (merged-PR head or contained in origin/develop).

Gotchas:
- `git push origin --delete <b1> <b2> ...` BATCH form is unreliable here — output looked like it echoed names but did NOT delete (remote count unchanged). Single-branch deletes in a loop work cleanly. Always re-`fetch --prune` + re-count to VERIFY remote deletes; never trust the push stdout (it gets truncated by `tail`).
- 5 `feature/*/integration` remote branches are PROTECTED by a GitHub branch-protection rule (`GH006: Cannot delete this branch`). Can't delete via git push — needs founder to delete via GitHub UI or relax the rule. Left for founder review.
- 19 remote + 30 local branches KEPT because unmerged + not contained in develop (section-4..9/integration, microservices-catalog/category/iam component branches, pricing-fe-rework, bootsmoke, b03-debounce, topbar-icon-drift). Conservative rule: when ahead-of-develop AND not in merged-PR list → KEEP.
