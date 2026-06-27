## project: pr_283_merged (2026-06-18)

PR #283 MERGED to develop.
Merge commit: da588f3a455d812ed18215946b27da6900a20a1a
Merged at: 2026-06-18T09:55:15Z
Merged by: Mugunthan93 (repo owner, admin merge — branch protection bypassed via --admin flag)
PR URL: https://github.com/Mugunthan93/mesell/pull/283

Commits landed on develop:
  - Design token migration (Wave A) — _tokens.css CSS custom property layer
  - Responsive pass — mee-grid cols=4 three-step fix, mee-page <main> to <div> a11y landmark fix
  - mee-multiselect — full CVA, virtual scroll, server search
  - CVA NgControl upgrade (Wave D) — self-inject NgControl pattern on all form primitives
  - Virtual scroll + lazy table (Wave E) — [lazy]/[virtualScroll]/(lazy_load) on mee-table
  - Auth restore — production auth guard/service restored (design-worktree bypass removed)

Operational learnings for future PRs:
  1. gh pr review --approve FAILS when author == reviewer (GitHub API: "Cannot approve your own pull request"). Expected on solo repos. Use --admin merge or have a second GitHub account approve.
  2. gh pr merge --delete-branch FAILS inside a worktree when the target base branch is checked out in another worktree. Error: "fatal: 'develop' is already used by worktree at ...". Workaround: omit --delete-branch, delete remote branch separately after merge.
  3. gh pr merge --admin is idempotent — if PR already merged, exits with warning, not error. Safe to re-run.
