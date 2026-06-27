## Local dev-stack rebuild — preflight gates (lesson, 2026-06-18)

Dispatched to rebuild static `mfe-catalog` :4205 after "PR #278 (My Live Listings) merged to develop". STOPPED at Step 1 — premise false + tree dirty. ZERO mutations.

**Two preflight gates that MUST both pass before any build/serve in the master tree:**
1. **The PR is actually ON origin/develop.** Do NOT trust the dispatch claim. Verify: `git fetch origin develop` then `git log origin/develop --oneline | grep <feature>`. PR #278 (`5a866ad`, branch `feat/my-live-listings`) was only an OPEN PR (`refs/pull/278/head` present in `git ls-remote`, but origin/develop tip = `028096d` #277). GOTCHA: `git cat-file -t 5a866ad` returns "commit" because PR refs get fetched into the local object store — that does NOT mean it's merged. Check `git log origin/develop`, never `cat-file`.
2. **The master tree is clean enough for `--ff-only`.** This repo has `pull.rebase=true` set locally, so `git pull --ff-only` STILL errors `cannot pull with rebase: unstaged changes` (exit 128) when the tree is dirty. The master-tree safety contract permits ONLY `git pull --ff-only origin develop` (no stash/commit/reset) — so a dirty tree is an unclearable block from my side. The modifying session must clean its own tree.

**What I did right:** stopped, made zero mutations, did NOT kill the existing :4205 server (pid 2529 stale build left serving), did NOT force, recorded the STOP in STATUS_INFRA.md.

**Scope note:** this ops rebuild (build → serve gitignored dist/ on a local port) is the deploy-boundary serving role, distinct from the 2026-06-08 DECLINED "scaffold frontend" dev task. Building/serving a built artifact = OK as a local ops task when founder-directed; running `ng new`/installing app deps as a feature-dev step = still NOT mine.

---
