## Session mesell-puller-state-reconcile-infra-session-1 — 2026-06-11 — image-puller orphans DESTROYED per founder ruling (PR #121 CLOSED)

**Founder ruling 2026-06-11:** PR #121 is CLOSED. The metadata-token `registries.yaml` mechanism (mechanism B, live since Phase D, key-free, org-policy-clean) WON over the SA-key imagePullSecret approach (mechanism A). Org policy `constraints/iam.disableServiceAccountKeyCreation` blocks SA keys anyway, so A was never viable. The 2 reader-SA resources applied in session-7 (`module.artifact_registry`) became orphaned state — the code on develop never defined them (PR #121 never merged), so develop's state held 2 resources the code doesn't.

**Action taken — targeted destroy, via Terraform NOT `gcloud delete`:** reconciled via `terraform apply` of a targeted destroy plan (the Terraform-managed path — Playbook §0 forbids `gcloud delete` w/o founder approval; this WAS founder-approved-in-prompt AND went through TF, not gcloud).
- Worktree on origin/develop base (#120 merge `75f30ea`); develop's `artifact_registry/main.tf` has NO puller resources → targeted plan naturally showed them as deletions.
- `.terraform` symlink-to-master-cache trick again (disk 5.4Gi free / 69%): `ln -s <master>/infra/terraform/.terraform .terraform`, run plan/apply, `rm -f` the symlink at cleanup; master cache untouched.
- `GOOGLE_OAUTH_ACCESS_TOKEN="$(gcloud auth print-access-token --account=vaishnaviramoorthy@gmail.com)"` prefix + `-target=module.artifact_registry -var-file=environments/dev.tfvars` + postgres/valkey password `-var`s. ADC active acct was `vaishnaviramoorthy@gmail.com` (correct).

**PLAN GATE (the safety bar) — PASSED exactly:** `0 to add, 0 to change, 2 to destroy`. Machine-verified via `terraform show -json <plan> | python3` that the change set was EXACTLY:
- `module.artifact_registry.google_artifact_registry_repository_iam_member.image_puller_reader` → delete
- `module.artifact_registry.google_service_account.meesell_image_puller` → delete
- The AR repo itself (`google_artifact_registry_repository.meesell_prod_images`) was NOT in the change set (preserved). The `module.cloudbuild_permissions` compute-SA writer member (a DIFFERENT module) untouched by the `-target`.
- **LESSON re-confirmed:** machine-readable `terraform show -json .tfplan | python3` parsing of `resource_changes[].change.actions` is the trustworthy gate for "exactly these N resources, exactly this verb" — better than eyeballing colored CLI output. Use it whenever the gate is "destroy EXACTLY X and nothing else."

**VERIFY (post-apply, all PASS):**
1. `gcloud iam service-accounts list --filter="email:meesell-image-puller" --format="value(email)"` → EMPTY (SA gone).
2. `gcloud artifacts repositories get-iam-policy meesell-prod-images` → NO `meesell-image-puller` member in any binding. Remaining `roles/artifactregistry.reader` member = `888244156264-compute@...` (the Phase A VM-SA binding that powers mechanism B pulls — correct, intact).
3. Re-plan `-target=module.artifact_registry` → "No changes" (idempotent, state clean).

**Net live state now:** `module.artifact_registry` = AR repo + (cloudbuild_permissions writer member, separate module). The reader-SA + repo-reader-member session-7 added are GONE. AR pull auth for K3s remains 100% on mechanism B (registries.yaml metadata token). No cluster mutations. No secret/key material printed or created. Cost ₹0 (a destroy; the SA was free anyway). No stale GCS lock this session.

**Process note:** no repo code commit needed (develop's code already correct — never had these resources). Only repo commit was THIS memory append, on branch `chore/infra-memory-puller-destroyed` → PR to develop (NOT merged — founder gate). Board: 3 active rows (ci-activation/auth-otp/mfe-cutover) all IN REVIEW, last-touched 2026-06-11 — session-start + session-end sweep found ZERO rows stale 7+ days. No new feature row added (state-reconcile chore, not a feature branch). NOTE: this worktree's `.claude/agent-memory/MEMORY.md` is a tracked copy (709 lines) BEHIND the master-tree working copy (918 lines, holds sessions 5-7 appends that shipped via their own now-closed/other PR branches); the append here is self-contained and additive so the divergence is harmless for this single-section commit.

---
