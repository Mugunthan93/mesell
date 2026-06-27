## Branch housekeeping deep-pass — squash-merge "looks ahead" trap (2026-06-20)

Did a deep branch-deletion pass (local 32->5, remote 28->15). KEY LESSON: `git cherry develop <branch>`
showing `+` lines does NOT mean genuine new development. Squash-merges create a develop commit with a
DIFFERENT patch-id than the branch's individual commits, so `git cherry` reports `+` for every branch
commit even though the CONTENT is fully in develop. Likewise `git log develop..<branch>` shows N commits.

THE DECISIVE TEST (use this, not cherry/log counts):
  files=$(git diff develop...<ref> --name-only)
  git diff <ref> develop -- $files --name-only | grep -c .   # 0 == develop already has branch tip content exactly => DELETE
This restricts the compare to the branch's OWN changed files and asks "does develop already match the
branch tip for them?" Zero differing files = squash absorbed = no new dev = DELETE.

Result: ALL 8 microservices-* + ALL section-*/integration + pricing/bootsmoke/smart-picker/ci-fix branches
were squash-absorbed (0 files differ). Two branches (chore/infra-memory-puller-destroyed,
fix/topbar-icon-drift) had 1 differing file each but it was a PURE .md status/memory append describing
ALREADY-COMPLETED work (zero code) — also DELETE. Net: NO non-protected/non-held branch had real unmerged code.

GH006 reality: `*/integration` branches have GitHub branch protection that BLOCKS `git push origin --delete`
("protected branch hook declined"). These 11 must be deleted from the GitHub UI by the founder (or by
relaxing protection). git push cannot remove them. origin/staging is also protected (correctly kept).

HELD branches feat/google-auth-backend + feat/google-auth-frontend are LOCAL-ONLY (never pushed). Per
founder ruling, never auto-push or delete held branches — flag the asymmetry, leave as-is.

Audit file pattern: /tmp/meesell-newdev-audit-<ts>.txt with per-branch evidence (commit count / cherry +/- /
diff stat / decisive-test result). The `for b in $MULTILINE_VAR` shell trap: a multi-line variable in a
POSIX `for` is ONE word — use `while IFS= read -r b; do ... done < file` instead.
