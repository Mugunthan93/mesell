## Post-merge worktree/branch cleanup (2026-06-21)
Pruned 6 merged-PR worktrees (#329–#334: dev-env-manager, fed-mapping-version, git-workflow, git-workflow-refs, presync-docs-memory, ram-guard-fix) + their 7 local branches + 6 remote branches; `git worktree list` now = master tree (develop) + gauth-live only. NEVER touch develop/main/staging/feature/google-auth/gauth-live. Lessons: (1) verify PR MERGED via `gh pr list --head <b> --state all --json number,state` AND/OR `git branch --merged develop` before any deletion; (2) `ram-guard-fix` had uncommitted scratch in `tools/meesell_env.py` but its branch (`fix/env-manager-ram-guard/infra`) was already merged → `worktree remove --force` safe (only uncommitted experimental edits discarded); (3) all master-tree git ops need `MESELL_ALLOW_MASTER_GIT=1`; (4) prefix gh/git with `GH_TOKEN="$(gh auth token)"` to avoid 401s.

**cloudbuild.yaml extended** (was api+frontend; now api+worker+conditional-frontend):
- Added build-worker + push-worker steps (parallel with api)
- Added precheck-frontend step that writes `/workspace/.frontend-buildable` if `frontend/Dockerfile` exists
- build-frontend + push-frontend both `entrypoint: bash` with the marker-file check — if Wave 2B hasn't produced a Dockerfile yet, they exit 0 quietly
- `images:` block lists only api + worker — frontend OMITTED because Cloud Build FAILS the run if a listed image isn't actually pushed. Comment in file says to add frontend back to `images:` once the Dockerfile lands.
- Timeout bumped 1200s → 1800s
- Default `_REPO`: `meesell-images` → `meesell-prod-images`

**Terraform ci_identity extension (GitHub WIF + meesell-github-ci SA):**
