# UI Design-System Decoupling — Phase 5 (Seal & DAG contracts — capstone)

**Status:** BUILT + PR OPEN + **branch protection WIRED**. 2026-06-17.
**PR:** #271 `feat/ui-ds-phase5 → develop`. Commit `303baec`. Worktree `/tmp/mesell-wt/ui-ds-phase5` off develop @ `8994735` (P1–P4 all merged).

## What shipped (config + finalize only — no app code)
- **ci.yml**: FE-gate step `--strict=fe2,fe3` → **`--strict`** (all 5 fail CI on any violation). Job stays NON-`needs` of build/deploy (required-check gates merge, not the build DAG); Node-only.
- **fe5_public_barrels_only.mjs**: `PHASE0_ALLOWED_DEEP_PREFIXES = []` (emptied). 0 deep `@mesell/*/subpath` imports exist in apps → the SP0 lean-bundle allowance was never used → seal finalized to "barrel roots only, no exceptions." Scanner logic byte-identical otherwise.
- **fe1/fe4/run-all**: doc-comment finalize (no logic). **README**: all 5 strict + gate required.

## Branch protection — DONE (founder-authorized, out-of-band)
Added **`FE Gate: lint (5 contracts)`** to develop's required status checks via `gh api` (additive POST to `/branches/develop/protection/required_status_checks/contexts` → preserved the existing 13, now 14). It is NOT a file in the PR.
- **Key safety reasoning:** the FE Gate has the SAME `if: frontend-changes` condition as the 7 frontend checks ALREADY required (`Frontend: shell`, `Frontend: mfe-*`). Precedent proven → backend-only PRs skip it cleanly (no wedge); the context was already green on develop (#265/#267). Safe to add pre-Phase-5-merge.
- **gh api recipe (for future required-check adds):** `echo '["<context>"]' | gh api -X POST repos/Mugunthan93/mesell/branches/develop/protection/required_status_checks/contexts --input -` (additive, preserves existing).

## The 5 contracts — all blocking now
FE-1 (PrimeNG seal) **P5** · FE-2 (icon seal) P1 · FE-3 (chrome shell-only) P4 · FE-4 (lib DAG) **P5** · FE-5 (barrel-roots-only) **P5**. Any regression of any boundary now blocks merge.

## Merge mechanics learned this session (CARRY FORWARD)
- **Squash-merge + stacked PR divergence:** #265 was squash-merged → develop got a NEW squash SHA, so feat/ui-ds-phase4 still carried the original phase3 commits as duplicate ancestors. FIX: `git rebase --onto origin/develop <old-phase3-tip> feat/ui-ds-phase4` → replays only phase4 commits onto develop. Clean (libs/layout untouched by other PRs). Force-push-with-lease, then retarget PR base → develop.
- **Retarget doesn't trigger CI:** changing a PR base fires `pull_request: edited`, NOT in the default `[opened, synchronize, reopened]` types, AND the workflow only runs for PRs based on main/develop. After retarget, **close+reopen** the PR (fires `reopened`) to trigger CI. (Or push a commit.)
- The FE Gate runs `--strict` now; it's fast (~9s) and required — every frontend PR is gated by it.

## Roadmap (remaining)
- **Phase 6**: per-MFE adoption sweep — migrate each MFE (auth/catalog/dashboard/export/onboarding/pricing) to MEE_LAYOUT page primitives + ui-kit aggregators + mee-icon semantic names; remove any ad-hoc imports. Per-MFE parallel PRs. Now that FE-1/4/5 are strict+required, adoption regressions are caught immediately.
- **Phase 7**: swap-proof — add a 2nd theme preset (toggle one file) + an icon-set swap (edit MEE_ICONS only); document the swap procedure (plan appendix §8). Proves the DoD.
- Discipline: one phase = fresh worktree off develop (symlink node_modules from a sibling worktree to skip pnpm install) = one branch = one PR; founder merges; NEVER git in master tree.
