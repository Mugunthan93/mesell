## Session mesell-ci-mfe-billing-infra-session-1 — 2026-06-20 — add mfe-billing remote to CI frontend matrix

**Task (additive-only CI YAML):** the mfe-billing remote (merged develop PRs #323/#325) was missing from CI's frontend build/change-detection, so no `Frontend: mfe-billing` check existed. Added it mirroring siblings EXACTLY. Worktree `/tmp/mesell-wt/ci-mfe-billing`, branch `chore/ci-mfe-billing` off develop@0203f2a. Commit `344b7b3` (NOT pushed/PR'd — Director handles git).

**The 3-spot recipe (ci.yml documents it itself: "Adding a remote = ONE include entry below + ONE filter block above"; +outputs key):**
1. `frontend-changes.outputs:` block (~L532) — `mfe_billing: ${{ steps.filter.outputs.mfe_billing }}` after `mfe_auth`.
2. `filters:` block inside the `filter` step `with.filters` YAML string (~L576) — `mfe_billing:\n  - 'frontend/apps/mfe-billing/**'` after `mfe_auth`.
3. `frontend-build.strategy.matrix.include:` (~L630) — `- unit: mfe-billing / project: mfe-billing / run: ${{ ...outputs.mfe_billing == 'true' || ...libs == 'true' }}` after `mfe-auth`.

**NAMING CONVENTION (load-bearing, easy to get wrong):** filter/output KEYS use UNDERSCORE (`mfe_billing`); matrix `unit`/`project` use HYPHEN (`mfe-billing`). The `run` expression references the underscore output. `project:` must equal the angular.json project name (verified `"mfe-billing"` at angular.json L670, serve port :4207). Check name = `Frontend: ${{ matrix.unit }}` → `Frontend: mfe-billing`.

**Verify recipe (no workflow run):** `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` for parse, THEN parse structurally — the filters live as a YAML STRING in `steps[id=filter].with.filters`, so re-`yaml.safe_load` that string to confirm the filter key. Don't trust a flat grep on `${{` (shell-escaping ate my first grep). Matrix units after this change: shell + 7 remotes (pricing/export/onboarding/dashboard/catalog/auth/billing) = 8 legs.

**Doc sync (DEVOPS_ARCHITECTURE.md §9.2 sole-writer):** it ENUMERATES the matrix → must update or it rots. Changed: added `mfe_billing` filter-table row; "7 legs / all 6 remotes" → "8 legs / all 7 remotes". The §intro "10 jobs" count is UNCHANGED (a matrix leg is not a new job).

**Branch-protection follow-up (Director's note, for a later session):** after this merges to develop, add `Frontend: mfe-billing` to develop's required status-check contexts. Current required frontend contexts were 7 units + detect (per 2026-06-12 branch-protection memory) — this makes it 8 units + detect. Same NEVER-add rule holds: no Build/Deploy (main-only) or Nightly (schedule-only).
