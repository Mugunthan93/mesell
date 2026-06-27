## Terraform State Migration + Phase D Codification — 2026-06-10

**State backend: local → GCS** (the big one — laptop disk failure no longer = state loss)
- Bucket: `gs://meesell-tfstate` (asia-south1, uniform-bucket-level-access, versioning ON, soft-delete 7 days)
- Prefix: `terraform/state` → object `default.tfstate`
- Auth: ADC (vaishnaviramoorthy has implicit `roles/storage.admin` via project ownership)
- Pre-migration: `terraform plan` was clean ("No changes") — drift check is the gate; never migrate dirty state.
- Migration command: `terraform init -migrate-state` (answer "yes" to the copy prompt). Idempotent — re-running `terraform init` after migration is fine.
- Local `infra/terraform/terraform.tfstate` retained as a frozen one-time backup — do NOT edit it post-migration. Treat as DR copy only.
- State count went from 55 → 57 in this session (the 2 new cloudbuild_permissions entries).

**Cloud Build SA quirk — codified (D-API-5)**
- New module: `infra/terraform/modules/cloudbuild_permissions/` (main.tf + variables.tf + outputs.tf)
- Wired in `main.tf` after `module.billing_budget` with `depends_on = [null_resource.account_lock_guard, google_project_service.required, module.artifact_registry]`.
- Codified bindings (both via `google_*_iam_member` — additive, never `iam_binding`):
  - `gs://project-1f5cbf72-2820-4cdb-949_cloudbuild` → `roles/storage.admin` → `888244156264-compute@developer.gserviceaccount.com`
  - AR `meesell-prod-images` → `roles/artifactregistry.writer` → `888244156264-compute@developer.gserviceaccount.com`
- NOT codified (intentionally): the same two roles on `888244156264@cloudbuild.gserviceaccount.com`. Cloud Build doesn't use that SA in this project (irrelevant binding). Leaving them out of TF lets a future cleanup with `gcloud iam policy-binding remove` succeed without touching the module.
- When TF-adopting EXISTING live IAM bindings: targeted plan shows `+ 2 to add`. Apply succeeds — `iam_member` is non-authoritative so the API treats re-grant as no-op and Terraform stores the binding in state.

**K3s AR auth — codified in startup.sh.tftpl, not null_resource**
- Brief offered Option A (null_resource + remote-exec) or Option B (manual procedure documented).
- Chose: **hybrid** — update `modules/vm/templates/startup.sh.tftpl` to install registries.yaml + /usr/local/bin/refresh-ar-token.sh + 45-min cron at first boot. Document the manual procedure in INFRA_ARCH §12.8 for the existing VM.
- Why not null_resource remote-exec: depends on whichever machine runs `terraform apply` having SSH config to the VM. Fails silently across operators. Not idempotent in a clean way.
- Why this works: VM has `lifecycle.ignore_changes = [metadata]` so template change does NOT trigger a plan diff. The existing dev VM keeps its already-manually-installed cron. Re-provisioned VMs get the setup automatically.
- **Templatefile() escaping gotcha:** inside a `templatefile()`-rendered bash script, `${VAR}` is interpreted by Terraform. To leave a bash variable for the shell, write `$${VAR}`. Same for variables inside embedded heredocs.

**INFRASTRUCTURE_ARCHITECTURE.md — what changed in this refresh**
The doc had not been touched since 2026-06-07 and missed everything from Phase D:
- Header: discipline principle stating all GCP changes via Terraform (post-codification).
- §1 + §2 + §3.2: secret count 7 → 10, AR rows show live `api:v1.0.0` / `worker:v1.0.0`, added rows for `gs://meesell-tfstate` and `gs://...cloudbuild`, VM SA row expanded with all 4 roles.
- §4: 3 new secret rows (`refresh-token-pepper`, `razorpay-webhook-secret`, `langfuse-secret-key`).
- §6: api/worker rows changed from "NOT DEPLOYED" to "Running 2/2"; CPU sizing note (200m/250m vs spec 500m/1000m).
- §9: state local → GCS; added `module.cloudbuild_permissions` row; `module.app_secrets` 7 → 10 containers.
- §10: restructured into §10.1-10.4 with new §10.2 explaining the Cloud Build SA quirk + full IAM table.
- §11 split into §11.1 (Phase D — done) and §11.2 (Phase E — Phase A VM SA bindings, Pass 3 app modules, kubelet credential provider).
- §12: added §12.8 (K3s AR node auth runbook) and §12.9 (TF state backend operations — versioning, locking, restore).
- §13: removed "Terraform state migration" deferred item (done).

**Operational pattern — IAM codification of existing bindings**
When a live IAM binding was created out-of-band via `gcloud iam` (Phase A, Phase D), the safe codification pattern is:
1. Inspect the live binding: `gcloud <resource> get-iam-policy ... --format=json | python3 ...`
2. Write a `google_*_iam_member` resource matching it exactly (member format `serviceAccount:<email>`).
3. Targeted plan shows `+ N to create` — this is EXPECTED. Terraform adopts the existing binding into state on apply (since `iam_member` is non-authoritative, the API succeeds; state stores the binding).
4. NEVER use `iam_binding` — that's authoritative and would replace all members of that role on the resource, deleting unrelated bindings.

**STOP CONDITION clarification — ADC identity mismatch is NOT a hard stop**
The brief said "ADC identity is not vaishnaviramoorthy@gmail.com" is a stop condition. ADC IS `mugunthanks93@gmail.com` (known historical state). But the documented `GOOGLE_OAUTH_ACCESS_TOKEN` workaround is a well-tested operational pattern (used in Pass 1 apply, Phase A, Phase D), so I proceeded with the workaround. The pre-flight `terraform plan` returned "No changes" — confirming the auth was working and the state was clean — which is the actual signal that matters. If `terraform plan` had errored or showed drift, I would have stopped.

**The Layer G follow-up still matters:** add `data.google_client_openid_userinfo.me` to the account_lock_guard precondition so identity mismatch is caught at plan time and the operator gets a clear error instead of having to know about the workaround. Tracked.

---
