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

1. Authenticate: `gcloud auth application-default login`
2. Make sure billing is enabled on the project.
3. `cp terraform.tfvars.example terraform.tfvars` and fill in real values (`project_id`, `domain`, `ssh_public_key`, the `*_api_key` secrets).
4. `terraform init`
5. `terraform plan`
6. `terraform apply`

`terraform output next_steps` prints the full post-apply checklist (NS records, image push, SSH, migration).

## Day-2

- **Rotate a secret:** edit `terraform.tfvars`, `terraform apply`. A new Secret Manager version is created automatically; pods on the next pod restart will pull it via `scripts/secrets-from-gcp.sh` (re-render `k8s/secrets.yaml`, then `kubectl apply -f k8s/secrets.yaml`).
- **Resize the VM:** change `vm_machine_type`, `terraform apply` — GCE will stop and restart the VM. The boot disk (and K3s state on it) survives.
- **Destroy:** set `bucket_force_destroy = true` first if you want `terraform destroy` to remove the bucket along with its objects. Otherwise destroy will refuse to delete a non-empty bucket — by design.

## Drift-prone things to watch

- `manage_dns = true` creates a Cloud DNS zone. **You must point your registrar's NS records at the values in `terraform output dns_name_servers`** before ACME can issue a Let's Encrypt cert (cert-manager uses HTTP-01 over the same hostname). Until DNS propagates, the ingress will serve a self-signed cert.
- `ssh_source_cidrs` defaults to `["0.0.0.0/0"]` for convenience. **Narrow it for production.**
- The VM's boot disk has K3s state, container images, and the Postgres PVC. **It is not in a managed instance group and there is no replica.** Backups run nightly into the GCS bucket (`backup-cronjob.yaml`); restore is manual.
