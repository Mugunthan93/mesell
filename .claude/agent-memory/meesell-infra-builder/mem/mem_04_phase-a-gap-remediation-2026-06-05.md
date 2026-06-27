## Phase A Gap Remediation — 2026-06-05

### VM SA IAM bindings (production service account `888244156264-compute@developer.gserviceaccount.com`)
| Resource | Role | Phase | Verified |
|---|---|---|---|
| `meesell-prod-images` (Artifact Registry, asia-south1) | `roles/artifactregistry.reader` | A1 | yes (get-iam-policy) |
| `gs://meesell-prod-assets` (GCS) | `roles/storage.objectAdmin` | A2 | yes — alongside CI SA `meesell-prod-ci@…` |

These bindings let workloads on the VM (K8s pods using the VM SA) pull container images and read/write app assets without separate SA impersonation.

### Valkey maxmemory configured (A3)
- Module: `infra/terraform/modules/valkey/main.tf`
- Container args now include `--maxmemory 128mb --maxmemory-policy allkeys-lru`
- Live verification: `valkey-cli config get maxmemory → 134217728`, `maxmemory-policy → allkeys-lru`
- Pod rolled cleanly (no restart loops)
- TF module name is `module.valkey_dev` (not `module.valkey`). Important for `-target` flags. Same pattern for postgres → `module.postgres_dev`. Sample plan target:
  ```
  terraform -chdir=infra/terraform plan -target=module.valkey_dev ...
  ```

### dev.tfvars expanded (A5)
- `app_secret_ids` list now 7 entries — added `msg91-template-id`, `audit-pii-salt`
- TF apply for `module.app_secrets` NOT executed in Phase A (per spec). Future targeted plan will show "2 to add" — safe.

### Founder IP rotation procedure (operational pattern — observed 2026-06-05)
- Symptom: `kubectl` from laptop fails with `dial tcp 35.234.223.66:6443: i/o timeout`
- Cause: founder ISP rotated public IP (122.164.85.200 → 122.164.85.51). Firewall rule `meesell-dev-k3s-api` only allows the old IP.
- Fix (Terraform-managed, do NOT use `gcloud compute firewall-rules update`):
  ```bash
  TOKEN=$(gcloud auth print-access-token --account=vaishnaviramoorthy@gmail.com)
  export GOOGLE_OAUTH_ACCESS_TOKEN=$TOKEN
  KUBECONFIG=~/.kube/meesell-dev.yaml \
    terraform -chdir=infra/terraform plan \
      -target=module.firewall \
      -var-file=environments/dev.tfvars \
      -var "postgres_password=$(cat ~/.meesell-secrets/dev-postgres-password)" \
      -var "valkey_password=$(cat ~/.meesell-secrets/dev-valkey-password)" \
      -var "founder_ip=$(curl -4 -s ifconfig.me)" \
      -out=.tflogs/firewall-ip-rotate.tfplan
  terraform -chdir=infra/terraform apply .tflogs/firewall-ip-rotate.tfplan
  ```
- Source range MUST stay /32 — never 0.0.0.0/0 (Playbook §2.3).
- After apply, validate: `kubectl get nodes` should return `meesell-dev-master Ready`.
- Side note: MSG91 keeps its own IP whitelist (122.164.85.200 currently). If OTP send fails for the founder during testing, refresh MSG91 whitelist to current IP.

### TF gotcha — silent "No changes"
- If a targeted plan returns "No changes" but you know live state differs, the `-target` address is wrong. TF does NOT warn that the target matched zero resources.
- Recovery: `terraform -chdir=infra/terraform state list | grep <pattern>` to find the actual module path.
- Lesson: prefer `terraform state list` first when in doubt, especially after long sessions where module naming may have evolved.

---
