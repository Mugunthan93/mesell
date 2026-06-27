## Centralize section 4-9 dispatch prompts onto develop (2026-06-15)

**Task:** FAST MODE git consolidation. Copy the 6 `SECTION_DISPATCH_PROMPT.md` files (sections 4-9) from their integration branches onto develop, WITHOUT merging the integration branches. Sections 2 & 3 were already on develop at cf1d4a4.

**Outcome:** PR #233 (`docs/centralize-dispatch-prompts` → develop) merged. Merge SHA `6e1f9ed`. All 6 copied: ai-autofill, image-precheck, live-preview, price-calculator, tracking-dashboard, xlsx-export (1838 insertions). All 5 CI gates green; deploy/build/nightly correctly skipped (docs-only, non-main push). Master tree FF cf1d4a4..6e1f9ed. All 8 section integration worktrees/branches untouched (verified at original SHAs).

**Pattern (copy-doc-without-merging-branch):**
- `git show origin/feature/section-N/integration:<path> > <path>` in a worktree branched off origin/develop. Pulls a single file out of a branch's tree without checking it out or merging. The dest feature dirs already existed on develop, so no mkdir needed.
- Verify sources first with `git cat-file -e origin/feature/section-N/integration:<path>` before copying (brief said STOP+report if any missing — all 6 present).

**git PATH gotcha (NEW — important):**
- `git` is at `/usr/bin/git` (system) AND `/opt/homebrew/bin/git`. Even after `export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"`, a multiline `for ... done` loop intermittently hit `(eval):N: command not found: git` — the eval shell lost resolution mid-loop. FIX: use the ABSOLUTE binary path `/usr/bin/git` (and `/opt/homebrew/bin/gh`) for EVERY invocation. This is more reliable than relying on PATH export across the zsh-eval wrapper. Single explicit commands per line beat a bash for-loop for this.

**Discipline reaffirmed:** waited for all 5 gates to settle green before `gh pr merge --admin`; BLOCKED+MERGEABLE with in-progress required checks is not a fail. FF pull --ff-only with pre-existing unstaged memory edits in working tree still succeeds cleanly (untracked/unstaged changes don't block a FF that doesn't touch those paths). Cleanup: removed temp worktree, deleted local+remote `docs/centralize-dispatch-prompts`, pruned. Never touched main/staging or any feature/section-* branch.

---
