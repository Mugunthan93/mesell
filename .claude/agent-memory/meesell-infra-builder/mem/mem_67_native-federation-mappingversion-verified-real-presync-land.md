## Native Federation `mappingVersion` verified REAL + presync land (2026-06-21)

**Session:** `mesell-federation-mapping-version-infra-session-1`

**PART A verdict — `features.mappingVersion` IS recognized in the installed stack (PR #332, landed):**
- Installed wrapper `@angular-architects/native-federation@21.2.3` depends on core `@softarc/native-federation ~3.5.1`; resolved core = `3.5.5` (sibling `@softarc/native-federation-node@3.5.5`).
- The live tree's `frontend/node_modules` symlinks pointed into a PRUNED worktree (`/private/tmp/mesell-wt/razorpay-wave5/.../.pnpm`) → dangling, could NOT inspect in-tree. WORKAROUND: `npm pack` the exact versions into `/tmp/nf-inspect`, untar, grep the built JS. This is the authoritative way to verify a library option when node_modules is a dangling pnpm symlink.
- Evidence in core 3.5.5:
  - `src/lib/config/with-native-federation.js` L19 → `mappingVersion: config.features?.mappingVersion ?? false` (default false).
  - `src/lib/core/bundle-exposed-and-mappings.js` L66 (shared) + L115 (sharedMappings) → `version: config.features.mappingVersion ? getMappingVersion(path) : ''`.
  - `getMappingVersion()` reads nearest `package.json` → `json.version ?? ''`.
  - Typed in `federation-config.d.ts` (`mappingVersion?: boolean`).
- Dependency satisfied: `frontend/libs/{core,env,ui-kit,composites}/package.json` ("1.0.0") are already on `origin/develop`, so the flag has a real version to stamp. Landed mappingVersion:true on all 7 configs (shell + 6 remotes).

**LESSON — verify the option in the BUILT lib before landing a config flag.** "Looks like an NF feature" is not enough; NF silently ignores unknown `features` keys (no default merge for them). Always grep the installed package's dist JS + .d.ts. A no-op flag would have been pure noise in 7 files.

**PART B+C presync chore (chore/presync-docs-memory → develop):**
- Copied genuinely-new docs + new nexus/backend memory + 4 SUPERSET MEMORY.md (mine, db-builder, angular-service-builder, nexus director). All 4 supersets were pure-addition (removed=0 vs develop) — safe.
- **DROPPED `docs/sessions/MASTER_SESSION_DISPATCH.md`**: the master-tree copy was STALE (older than develop). Develop's #330 added `docs/GIT_WORKFLOW.md` references; the master-tree copy REMOVES them → would regress #330. Restored to develop in the worktree.
- LESSON: before copying a "presync" file, diff it vs origin/develop. A line-count SHRINK on a doc-only file = red flag for a regression of upstream-reconciled content. Pure-addition supersets are safe; mixed add/remove on already-landed files are NOT.

**Master-tree git hygiene:** only mutation to master-tree git state was the allowed `git checkout --` file-restore of the 7 federation.config.js (after landing them via PR #332). No commits, no staging in the master tree.
