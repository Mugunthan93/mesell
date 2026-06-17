# terraform/ — MeeSell GCP infrastructure

Provisions the full hosting footprint on a single GCP project:

| Resource | Purpose |
|---|---|
| `google_compute_instance.vm` | Ubuntu 24.04 VM running K3s. e2-standard-2 by default. |
| `google_compute_address.static` | Permanent external IP. |
| `google_compute_firewall.allow_http_https` + `allow_ssh` | Inbound rules (80/443 open; 22 limited to `ssh_source_cidrs`). |
| `google_service_account.workload` | Attached to the VM; backend, workers, and the backup CronJob inherit it via the metadata server. |
| `google_storage_bucket.assets` | Bucket for `originals/`, `processed/`, `exports/`, and Postgres `backups/`. Uniform access + public access blocked + versioned. |
| `google_artifact_registry_repository.images` | Docker repo for `api` and `frontend` images. |
| `google_secret_manager_secret.*` | One secret per value: `JWT_SECRET`, `POSTGRES_PASSWORD` (auto-generated), plus `GEMINI_API_KEY`, `MSG91_*`, `RAZORPAY_*` (operator-supplied). |
| `google_dns_managed_zone` + `google_dns_record_set` | Cloud DNS zone with `@`, `www`, `api` records pointing at the static IP. Skippable via `manage_dns = false`. |

## What it does *not* do

- Build or push container images. That's `make build && make deploy` from your workstation (or a GitHub Actions job).
- Install K3s. That's `scripts/setup-vm.sh`, executed by an operator over SSH after `terraform apply`.
- Apply Alembic migrations. Once the API pods are Ready: `kubectl -n meesell exec deploy/api -- alembic upgrade head`.

The split is deliberate: Terraform owns immutable infrastructure; `setup-vm.sh` owns the cluster bootstrap; the app deploy is `kubectl set image`.

## One-time setup

This stack runs under the **`vaishnaviramoorthy@gmail.com`** account (the one
with the free GCP credit).

1. **Switch gcloud to the Vaishnavi account.** From your laptop:
   ```bash
   gcloud auth login vaishnaviramoorthy@gmail.com
   gcloud auth application-default login            # browser flow; sign in as vaishnavi
   gcloud config set account vaishnaviramoorthy@gmail.com
   gcloud projects list                             # pick the project linked
                                                     # to the free-credit billing account
   gcloud config set project <PROJECT_ID>
   gcloud auth application-default set-quota-project <PROJECT_ID>
   ```
   Tip: use `gcloud config configurations create meesell-vaishnavi` to keep this
   profile separate from `mugunthanks93@gmail.com`.

2. **Confirm billing.** Free credit binds to the *billing account*, not the
   project. Verify with:
   ```bash
   gcloud billing projects describe <PROJECT_ID>     # billingEnabled should be true
   ```
   If billing is not linked, link a billing account that still has trial credit:
   ```bash
   gcloud billing accounts list
   gcloud billing projects link <PROJECT_ID> --billing-account=<BILLING_ACCOUNT_ID>
   ```

3. `cp terraform.tfvars.example terraform.tfvars` and fill in real values
   (`project_id`, `domain`, `ssh_public_key`, the `*_api_key` secrets).
4. `terraform init`
5. `terraform plan`     ← review carefully; look for `+ create` on the expected resources
6. `terraform apply`

`terraform output next_steps` prints the full post-apply checklist (NS records, image push, SSH, migration).

### Sanity-check Terraform is using the right identity

Before `terraform apply`, confirm:

```bash
gcloud auth application-default print-access-token --quiet >/dev/null \
  && gcloud config list account --format='value(core.account)'
# Expected output: vaishnaviramoorthy@gmail.com
```

If the printed account is `mugunthanks93@gmail.com`, re-run step 1 — Terraform
will otherwise provision resources in the wrong account.

## Day-2

- **Rotate a secret:** edit `terraform.tfvars`, `terraform apply`. A new Secret Manager version is created automatically. (NOTE 2026-06-12: the legacy `scripts/secrets-from-gcp.sh` materialiser was deleted — it used the dead `meesell-`-prefixed SM IDs and the legacy `meesell` namespace, neither of which the live path uses. The live path is the un-prefixed `app_secrets` module → k8s Secret `backend-secrets` in `dev` ns, populated via `gcloud secrets versions add`. See `docs/INFRASTRUCTURE_ARCHITECTURE.md`.)
- **Resize the VM:** change `vm_machine_type`, `terraform apply` — GCE will stop and restart the VM. The boot disk (and K3s state on it) survives.
- **Destroy:** set `bucket_force_destroy = true` first if you want `terraform destroy` to remove the bucket along with its objects. Otherwise destroy will refuse to delete a non-empty bucket — by design.

## Drift-prone things to watch

- `manage_dns = true` creates a Cloud DNS zone. **You must point your registrar's NS records at the values in `terraform output dns_name_servers`** before ACME can issue a Let's Encrypt cert (cert-manager uses HTTP-01 over the same hostname). Until DNS propagates, the ingress will serve a self-signed cert.
- `ssh_source_cidrs` defaults to `["0.0.0.0/0"]` for convenience. **Narrow it for production.**
- The VM's boot disk has K3s state, container images, and the Postgres PVC. **It is not in a managed instance group and there is no replica.** Backups run nightly into the GCS bucket (`backup-cronjob.yaml`); restore is manual.
