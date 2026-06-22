# Onboarding Testing Session 1 — Handoff (2026-06-22)
Session: mesell-onboarding-testing-session-1

## Shipped to develop (via integration 2147d5b, merge-commit; absorbed develop #406 refreshForced)
The integration→develop merge was PR #422 (merge-commit, `--no-ff`), landing on develop as
merge-commit **`98cc02a`** (parents: develop `4f055ec` + integration `2147d5b`). `origin/develop`
`4f055ec` was an **ancestor** of the integration tip because develop's #406 refreshForced was
absorbed INTO `feature/qa-onboarding/integration` first (`2147d5b`), so `git merge-tree` reported
**0 conflicts** and no `--admin` was needed (all 15 required checks green).

Full onboarding QA wave (FE+BE) + 3 product-bug fixes:
- Wave A backend pytest (PR #391): iam 7/7 + customer 5/5 happy+error; 15 new cases
- Wave B frontend specs + onboarding persist fix (fix #399, tests #407): suite 60→1 failures; auth-storm sentinel reconciled to #406 refreshForced
- Wave C Playwright E2E two-phase (PR #411): 11 pass / 3 fixme; OB-E2E-03 persist+resume regression guard
- Profile reshape → Legal-Metrology compliance editor (PR #416)
- Pincode-required FE (#416) + pincode 422-not-500 BE service guard (#419)

## Bugs fixed
1. Onboarding onSubmit was a setTimeout mock → never persisted seller profile (data-loss). Now patchProfile→refreshUser→navigate; unit + E2E guards.
2. Profile onSubmit had the same setTimeout placeholder (edited a display-name with NO backend). Reshaped into a real compliance editor (getProfile/patchProfile, saved-in-place, no navigate, no refreshUser).
3. Empty manufacturer/packer pincode → 500 NotNullViolation. FE: pincode now required; BE: 422-not-500 service guard (fires only when existing is None; partial PATCH unaffected; zero new i18n keys via the .missing generic fallback); revert-checked.

## Carried follow-ups (logged on boards — none blocking)
- BE-CUSTOMER-INSERT-500-1 (P2): same latent INSERT-path 500 for the other 5 NOT-NULL profile fields (manufacturer_name/address, packer_name/address, country_of_origin)
- OB-FE-18: shell "Onboarding" sidebar nav not implemented in product (E2E gap)
- empty-state spec flawed 'inventory' assertion (pre-existing develop-identical red) → ui-kit/composites cleanup
- load-remote.spec flaky federation-fallback-timeout (pre-existing develop-identical) → infra
- mfe-export route-productId placeholder (Wave-1 carry, blocks export-download)
- pnpm-lock.yaml / @playwright/test@1.52.0 boot-smoke false-RED → infra
- **PR #417 (QA-journal docs) NOT YET LANDED:** it was held to avoid interleaving the journal
  conflicts. After #422 merged, #417 now CONFLICTS against develop on 2 QA-coordinator-owned files
  (`docs/status/feature_board_qa.md`, `.claude/agent-memory/meesell-qa-coordinator/coverage_gaps.md`)
  because #422 brought the canonical QA-journal content into develop. Resolution is the
  qa-coordinator's (sole-writer) — rebase #417 onto develop `98cc02a` and reconcile against the
  landed journal content. #417 left OPEN.

## Process notes
- Every change ran the HYBRID flow (coordinator spec → builder → independent merge-gate; gates re-ran tests, revert-checked the BE guard).
- develop advanced 13 commits during the wave; #406 refreshForced was absorbed into integration and the Wave-B auth-storm spec reconciled to it (single-flight storm guard preserved).
- .claude/agent-memory worktree write-protection blocked in-agent memory appends throughout; learnings captured in board/STATUS files + PR bodies; deferred-scribe owed.
- All branches RETAINED (no deletes).
