## Summary
One sentence: what does this PR do and why.

## Linked feature / spec
- Feature slug: `<image-precheck>`
- V1_FEATURE_SPEC.md section: `<§F5>`
- INFRASTRUCTURE_PLAYBOOK.md / k8s manifest reference: `<§X>`

## What changed
- File-level bullet list. Use `<path/to/file>` formatting.
- One bullet per concern, not per file.

## Test evidence
- Unit test results (paste manifest validation / `kubectl --dry-run` output).
- Smoke results (paste smoke deploy log against `dev`).
- Lint results (`terraform fmt -check`, `kubectl apply --dry-run` summary).
- Screenshot / log paste for any visual or runtime change.

## Reviewer reminder

**Reviewer rule (locked 2026-06-10):**
- For `feature/{name}/{group}` → `feature/{name}` PRs: the lead agent for this group is the reviewer.
- For `feature/{name}` → `develop` PRs: the founder is the reviewer.

## Session
- Session name: `mesell-<feature>-infra-session-<N>`
- Branch name: `feature/<feature>/infra`
- Lead: `meesell-infra-builder` (the one who will approve this PR)

## Checklist
- [ ] Branch is `feature/{name}/infra` and is rebased on `feature/{name}` tip
- [ ] CI gates 1+2+3 green (unit, smoke, lint)
- [ ] `feature_board.md` updated to IN REVIEW
- [ ] Agent memory updated with session learnings

---

## Infra-specific evidence

### Terraform plan
- [ ] `terraform plan` run against the affected state file
- Plan output (paste relevant excerpt):
  ```
  Plan: X to add, Y to change, Z to destroy.
  ```
- [ ] No `destroy` actions on production-tier resources without explicit founder sign-off in PR body

### K3s manifest
- [ ] Manifest under `k8s/` touched
- [ ] `kubectl apply --dry-run=server -f <file>` ran clean
- [ ] Namespace target verified (`dev` / `staging`)

### Secrets / IAM
- [ ] Secret Manager refs added / removed listed
- [ ] IAM binding changes listed with principal + role
- [ ] No JSON keys committed
- [ ] Workload Identity Federation paths confirmed

### Deployment evidence
- [ ] Smoke deploy to `dev` succeeded: `<pod status paste>`
- [ ] Rollback procedure documented if change is high-blast-radius

### Cost impact
- New monthly cost estimate: ₹`<XX>` (call out if > ₹500/month)

### CI gates relevant to this PR
- gate-3 lint (manifest validation) · deploy-dev (auto-fires post-merge)

---

## Acceptance gate (Step 1: feature/{name}/{group} → feature/{name})

- [ ] Branch name follows `feature/{name}/{group}` convention
- [ ] Branch rebased on current `feature/{name}` tip (no merge commits)
- [ ] CI gates 1+2+3 green (unit, smoke, lint) — gates 4+5 advisory at Step 1
- [ ] Group's PR template (this file) filled completely
- [ ] `docs/status/feature_board_<group>.md` row status = IN REVIEW
- [ ] Specialist's agent memory updated with session-close entry
- [ ] Acceptance criteria from `docs/V1_FEATURE_SPEC.md` met for this group's slice
