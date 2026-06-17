# MeeSell Terraform Workspace — Comprehensive Audit

**Prepared by:** meesell-infra-builder
**Date:** 2026-06-04
**Status:** READ-ONLY audit — no infrastructure was modified
**Scope:** `terraform/` directory (flat workspace, serial 68, last applied 2026-05-31)

---

## 1. Workspace Inventory

### Directory listing (`terraform/`)

```
total 568
drwxr-xr-x  26   832 May 31 15:02  .           (workspace root)
-rw-r--r--   1   212 May 27 22:05  .gitignore
drwxr-xr-x   3    96 May 27 22:13  .terraform/  (provider cache — exists)
-rw-r--r--   1  2336 May 27 22:14  .terraform.lock.hcl
-rw-r--r--   1  5034 May 27 22:05  README.md
-rw-r--r--   1  5603 May 31 15:02  ci.tf
-rw-r--r--   1  1410 May 27 22:05  dns.tf
-rw-r--r--   1  1105 May 27 22:05  iam.tf
-rw-r--r--   1   440 May 27 22:05  locals.tf
-rw-r--r--   1   736 May 31 14:17  main.tf
-rw-r--r--   1   864 May 27 22:05  network.tf
-rw-r--r--   1  3139 May 31 14:17  outputs.tf
-rw-r--r--   1   596 May 27 22:05  registry.tf
-rw-r--r--   1  1513 May 27 22:05  secrets.tf
-rw-r--r--   1   868 May 27 22:05  storage.tf
drwxr-xr-x   3    96 May 27 22:05  templates/
-rw-r--r--   1 90979 May 31 15:02  terraform.tfstate      (local state)
-rw-r--r--   1 89731 May 31 15:02  terraform.tfstate.backup
-rw-r--r--   1   511 May 27 22:13  terraform.tfvars       (gitignored — present on disk)
-rw-r--r--   1  1644 May 27 22:05  terraform.tfvars.example
-rw-r--r--   1 16745 May 27 22:14  tfplan                 (saved plan artifact — stale)
-rw-r--r--   1  4114 May 31 14:17  variables.tf
-rw-r--r--   1   237 May 27 22:05  versions.tf
-rw-r--r--   1  1603 May 27 22:05  vm.tf
templates/
  startup.sh    (cloud-init startup script template — 42 lines)
```

No `modules/` subdirectory exists. This is a flat workspace.

### Per-file summary

| File | Lines | Purpose |
|---|---|---|
| `versions.tf` | 14 | Terraform >= 1.5.0, providers: google ~> 6.10, random ~> 3.6 |
| `main.tf` | 28 | Provider block (google), local for required_services list, `google_project_service.enabled` for_each |
| `variables.tf` | 152 | 21 input variables: project_id, region, zone, name_prefix, labels, vm_*, ssh_*, bucket_*, manage_dns, domain, 5 sensitive app secrets, github_* |
| `outputs.tf` | 81 | 10 outputs: vm_name, vm_external_ip, ssh_command, bucket_name, artifact_registry_url, workload_service_account, secret_ids, dns_name_servers, registry_docker_login_hint, ci_workload_identity_provider, ci_service_account_email, cloud_build_service_account_email, next_steps |
| `locals.tf` | 9 | vm_name, workload_sa_id, bucket_name, registry_id, registry_url, dns_zone_name, ssh_metadata_value |
| `vm.tf` | 57 | `google_compute_instance.vm` with startup_script templatefile, shielded config, static IP attachment |
| `network.tf` | 39 | `google_compute_address.static` (static external IP), `google_compute_firewall.allow_http_https` (80/443), `google_compute_firewall.allow_ssh` (22) |
| `iam.tf` | 29 | `google_service_account.workload`, 3x `google_project_iam_member` for workload SA (AR reader, log writer, metric writer) |
| `ci.tf` | 135 | WIF pool + GitHub OIDC provider, `google_service_account.ci`, 7x IAM bindings for CI pipeline, `google_compute_project_metadata_item.enable_oslogin`, `google_compute_firewall.allow_ssh_iap` |
| `registry.tf` | 26 | `google_artifact_registry_repository.images` (DOCKER, cleanup policies) |
| `secrets.tf` | 52 | `random_password` for JWT_SECRET and POSTGRES_PASSWORD, `google_secret_manager_secret` + `_version` + `_iam_member` for 7 secrets via for_each |
| `storage.tf` | 31 | `google_storage_bucket.assets` (versioned, uniform access, public blocked, 90d archived delete rule), `google_storage_bucket_iam_member.workload_object_admin` |
| `dns.tf` | 41 | `google_dns_managed_zone.primary` (count = manage_dns ? 1 : 0), 3 A records (apex, www, api) — all currently inactive (manage_dns=false) |
| `templates/startup.sh` | 42 | Cloud-init script: installs curl/git/jq/gcloud, writes /etc/meesell.env with project metadata. Does NOT install K3s. |
| `.gitignore` | 15 | Excludes .terraform/, *.tfstate*, terraform.tfvars, *.auto.tfvars — correct |
| `README.md` | 84 | One-time setup guide, post-apply checklist, Day-2 operations |
| `terraform.tfvars` | 8 | Live values: project_id, region, zone, manage_dns=false, domain="", ssh_user=mugunthansrinivasan, ssh_public_key=[ed25519 key], secrets=placeholder |
| `terraform.tfvars.example` | 43 | Template with inline comments |

### .terraform/ provider cache

`.terraform/providers/` directory exists. Cached providers:
- `registry.terraform.io/hashicorp/google` v6.50.0 (constraint: ~> 6.10)
- `registry.terraform.io/hashicorp/random` v3.9.0 (constraint: ~> 3.6)

Terraform CLI version on disk: **1.13.3** (latest is 1.15.5 — minor, not blocking).

---

## 2. Managed Resource Inventory

### `terraform state list` output (57 resource instances across 31 resource entries)

```
data.google_project.this
google_artifact_registry_repository.images
google_artifact_registry_repository_iam_member.ci_ar_writer
google_artifact_registry_repository_iam_member.cloudbuild_ar_writer
google_compute_address.static
google_compute_firewall.allow_http_https
google_compute_firewall.allow_ssh
google_compute_firewall.allow_ssh_iap
google_compute_instance.vm
google_compute_project_metadata_item.enable_oslogin
google_iam_workload_identity_pool.github
google_iam_workload_identity_pool_provider.github
google_project_iam_member.ci_cloudbuild_editor
google_project_iam_member.ci_iap_tunnel
google_project_iam_member.ci_os_login
google_project_iam_member.workload_ar_reader
google_project_iam_member.workload_log_writer
google_project_iam_member.workload_metric_writer
google_project_service.enabled["artifactregistry.googleapis.com"]
google_project_service.enabled["cloudbuild.googleapis.com"]
google_project_service.enabled["compute.googleapis.com"]
google_project_service.enabled["dns.googleapis.com"]
google_project_service.enabled["iam.googleapis.com"]
google_project_service.enabled["iamcredentials.googleapis.com"]
google_project_service.enabled["iap.googleapis.com"]
google_project_service.enabled["secretmanager.googleapis.com"]
google_project_service.enabled["storage.googleapis.com"]
google_secret_manager_secret.secret["GEMINI_API_KEY"]
google_secret_manager_secret.secret["JWT_SECRET"]
google_secret_manager_secret.secret["MSG91_AUTH_KEY"]
google_secret_manager_secret.secret["MSG91_TEMPLATE_ID"]
google_secret_manager_secret.secret["POSTGRES_PASSWORD"]
google_secret_manager_secret.secret["RAZORPAY_KEY_ID"]
google_secret_manager_secret.secret["RAZORPAY_KEY_SECRET"]
google_secret_manager_secret_iam_member.workload_access["GEMINI_API_KEY"]
google_secret_manager_secret_iam_member.workload_access["JWT_SECRET"]
google_secret_manager_secret_iam_member.workload_access["MSG91_AUTH_KEY"]
google_secret_manager_secret_iam_member.workload_access["MSG91_TEMPLATE_ID"]
google_secret_manager_secret_iam_member.workload_access["POSTGRES_PASSWORD"]
google_secret_manager_secret_iam_member.workload_access["RAZORPAY_KEY_ID"]
google_secret_manager_secret_iam_member.workload_access["RAZORPAY_KEY_SECRET"]
google_secret_manager_secret_version.version["GEMINI_API_KEY"]
google_secret_manager_secret_version.version["JWT_SECRET"]
google_secret_manager_secret_version.version["MSG91_AUTH_KEY"]
google_secret_manager_secret_version.version["MSG91_TEMPLATE_ID"]
google_secret_manager_secret_version.version["POSTGRES_PASSWORD"]
google_secret_manager_secret_version.version["RAZORPAY_KEY_ID"]
google_secret_manager_secret_version.version["RAZORPAY_KEY_SECRET"]
google_service_account.ci
google_service_account.workload
google_service_account_iam_member.ci_act_as_cloudbuild
google_service_account_iam_member.ci_act_as_workload
google_service_account_iam_member.ci_wif_binding
google_storage_bucket.assets
google_storage_bucket_iam_member.workload_object_admin
random_password.jwt_secret
random_password.postgres_password
```

**Total: 57 managed resource instances**

### Resources grouped by source file

**main.tf** (9 instances — API enables):
`google_project_service.enabled` for: artifactregistry, cloudbuild, compute, dns, iam, iamcredentials, iap, secretmanager, storage

**vm.tf** (1 instance):
- `google_compute_instance.vm` — name: `meesell-vm`, zone: `asia-south1-a`, machine type: `e2-standard-2` (from variables.tf default), external IP: 34.93.9.139

**network.tf** (3 instances):
- `google_compute_address.static` — name: `meesell-ip`, address: 34.93.9.139 (static external IP)
- `google_compute_firewall.allow_http_https` — name: `meesell-allow-http-https`, rules: tcp:80,443, source: 0.0.0.0/0
- `google_compute_firewall.allow_ssh` — name: `meesell-allow-ssh`, rule: tcp:22, source: var.ssh_source_cidrs (default 0.0.0.0/0)

**iam.tf** (4 instances):
- `google_service_account.workload` — email: `meesell-workload@project-1f5cbf72-2820-4cdb-949.iam.gserviceaccount.com`
- `google_project_iam_member.workload_ar_reader` — roles/artifactregistry.reader
- `google_project_iam_member.workload_log_writer` — roles/logging.logWriter
- `google_project_iam_member.workload_metric_writer` — roles/monitoring.metricWriter

**ci.tf** (12 instances):
- `google_iam_workload_identity_pool.github` — pool id: `github-pool`
- `google_iam_workload_identity_pool_provider.github` — provider id: `github-oidc`, scoped to `Mugunthan93/mesell`
- `google_service_account.ci` — email: `meesell-ci@project-1f5cbf72-2820-4cdb-949.iam.gserviceaccount.com`
- `google_service_account_iam_member.ci_wif_binding` — WIF → CI SA
- `google_artifact_registry_repository_iam_member.ci_ar_writer` — CI SA: roles/artifactregistry.writer
- `google_artifact_registry_repository_iam_member.cloudbuild_ar_writer` — Cloud Build SA: roles/artifactregistry.writer
- `google_project_iam_member.ci_cloudbuild_editor` — CI SA: roles/cloudbuild.builds.editor
- `google_service_account_iam_member.ci_act_as_cloudbuild` — CI SA: serviceAccountUser on compute SA
- `google_project_iam_member.ci_iap_tunnel` — CI SA: roles/iap.tunnelResourceAccessor
- `google_project_iam_member.ci_os_login` — CI SA: roles/compute.osLogin
- `google_compute_project_metadata_item.enable_oslogin` — key: enable-oslogin, value: TRUE
- `google_compute_firewall.allow_ssh_iap` — name: `meesell-allow-ssh-iap`, source: 35.235.240.0/20 (IAP range), port 22
- `google_service_account_iam_member.ci_act_as_workload` — CI SA: serviceAccountUser on workload SA

**registry.tf** (1 instance):
- `google_artifact_registry_repository.images` — id: `meesell-images`, format: DOCKER, location: asia-south1

**secrets.tf** (22 instances):
- `random_password.jwt_secret` — [REDACTED]
- `random_password.postgres_password` — [REDACTED]
- `google_secret_manager_secret.secret` x7 — secret IDs: meesell-gemini-api-key, meesell-jwt-secret, meesell-msg91-auth-key, meesell-msg91-template-id, meesell-postgres-password, meesell-razorpay-key-id, meesell-razorpay-key-secret

> SUPERSEDED 2026-06-12: the applied `app_secrets` module uses un-prefixed secret IDs (`gemini-api-key`, `jwt-secret`, etc.; `secret_id = each.key`); the `meesell-*` prefixed scheme described here was never created. The SM secret `meesell-gemini-api-key` is dead (HTTP 400) and unreferenced by any live path.
- `google_secret_manager_secret_version.version` x7 — version 1 of each, [REDACTED values]
- `google_secret_manager_secret_iam_member.workload_access` x7 — workload SA: roles/secretmanager.secretAccessor on each

**storage.tf** (2 instances):
- `google_storage_bucket.assets` — name: `project-1f5cbf72-2820-4cdb-949-meesell-assets`, location: ASIA-SOUTH1, versioning: enabled, public_access_prevention: enforced
- `google_storage_bucket_iam_member.workload_object_admin` — workload SA: roles/storage.objectAdmin

**dns.tf** (0 active instances — manage_dns=false, all count=0):
- `google_dns_managed_zone.primary`, `google_dns_record_set.apex/www/api` — NOT in state (manage_dns=false)

---

## 3. Outputs and State Metadata

### terraform output (non-sensitive)

```
artifact_registry_url       = "asia-south1-docker.pkg.dev/project-1f5cbf72-2820-4cdb-949/meesell-images"
bucket_name                 = "project-1f5cbf72-2820-4cdb-949-meesell-assets"
ci_service_account_email    = "meesell-ci@project-1f5cbf72-2820-4cdb-949.iam.gserviceaccount.com"
ci_workload_identity_provider = "projects/888244156264/locations/global/workloadIdentityPools/github-pool/providers/github-oidc"
cloud_build_service_account_email = "888244156264-compute@developer.gserviceaccount.com"
dns_name_servers            = []    (manage_dns=false)
registry_docker_login_hint  = "gcloud auth configure-docker asia-south1-docker.pkg.dev"
secret_ids                  = { GEMINI_API_KEY: "meesell-gemini-api-key", ... }
                              # SUPERSEDED 2026-06-12: applied app_secrets module uses un-prefixed IDs
                              # (gemini-api-key etc.); meesell-* prefix never created. meesell-gemini-api-key is dead (HTTP 400).
ssh_command                 = "ssh mugunthansrinivasan@34.93.9.139"
vm_external_ip              = "34.93.9.139"
vm_name                     = "meesell-vm"
workload_service_account    = "meesell-workload@project-1f5cbf72-2820-4cdb-949.iam.gserviceaccount.com"
next_steps                  = [post-apply checklist — K3s not yet installed per script; SSH is the next manual step]
```

### State metadata

| Field | Value |
|---|---|
| State serial | 68 |
| Terraform version (in state) | 1.13.3 |
| Lineage | 91dd948e-cf8e-0c9f-de3b-8ccab2f2c36c |
| Backend type | **local** (no `backend` key in state file — defaults to local) |
| State file last modified | 2026-05-31 15:02:34 |
| State backup last modified | 2026-05-31 15:02:34 |

State file is local (`terraform.tfstate` on disk in `terraform/`). The `.gitignore` excludes `*.tfstate*` correctly — the state is NOT in git. This is the risk the plan doc acknowledges: laptop disk failure = state loss.

---

## 4. Per-File Walkthrough

### `versions.tf`
- **Provider declarations:** `hashicorp/google ~> 6.10`, `hashicorp/random ~> 3.6`
- **Terraform version:** `>= 1.5.0`
- **NOTE vs plan:** Plan calls for `~> 5.30` for google provider. Existing workspace uses `~> 6.10` (locked at 6.50.0). This is a MAJOR version difference — the new plan's provider strategy is incompatible with the existing workspace without a `terraform init -upgrade`.

### `main.tf`
- **Resources:** `google_compute_instance.vm` does not live here; this file owns only the API-enable for_each
- **Variables used:** `var.project_id`
- **No module calls** — flat workspace
- **No lifecycle blocks**

### `variables.tf`
- **21 variables:** project_id, region (default asia-south1), zone (default asia-south1-a), name_prefix (default "meesell"), labels (default app/managed tags), vm_machine_type (default e2-standard-2), vm_disk_size_gb (default **50**), vm_disk_type (default pd-balanced), vm_image (default `ubuntu-os-cloud/ubuntu-2404-lts-amd64`), ssh_user, ssh_public_key (sensitive), ssh_source_cidrs (default **0.0.0.0/0**), bucket_location (ASIA-SOUTH1), bucket_force_destroy (false), manage_dns (true), domain (""), gemini_api_key (sensitive), msg91_auth_key (sensitive), msg91_template_id (sensitive), razorpay_key_id (sensitive), razorpay_key_secret (sensitive), github_repository, github_issuer_uri
- **NOTE:** `vm_disk_size_gb` default is 50GB; playbook specifies 30GB. Provisioned with 50GB per the variable default.
- **NOTE:** `vm_image` is Ubuntu 24.04 (`ubuntu-2404-lts-amd64`); playbook specifies Ubuntu 22.04. The existing VM runs Ubuntu 24.04.
- **No validation blocks** — notably, `ssh_source_cidrs` has no validation enforcing non-0.0.0.0/0 (cf. plan's proposed founder_ip validation).

### `locals.tf`
- **Locals:** vm_name = "meesell-vm", workload_sa_id = "meesell-workload", bucket_name = "${project_id}-meesell-assets", registry_id = "meesell-images", registry_url = "asia-south1-docker.pkg.dev/...", dns_zone_name, ssh_metadata_value
- **No module references**

### `vm.tf`
- **Resources:** `google_compute_instance.vm`
- **Variables used:** `var.vm_machine_type`, `var.zone`, `var.labels`, `var.vm_disk_size_gb`, `var.vm_disk_type`, `var.vm_image`, `var.project_id`, `var.region`, `var.name_prefix`, `var.domain`
- **Module calls:** None
- **startup-script:** Uses `templatefile()` pointing to `templates/startup.sh` — does NOT install K3s (important: startup.sh only installs gcloud CLI and writes /etc/meesell.env). K3s install is left to a separate manual `scripts/setup-vm.sh` step.
- **Lifecycle blocks:** NONE — no `prevent_destroy` on the VM.
- **Depends_on:** static IP, workload SA, GCS bucket, AR repo, Secret Manager versions

### `network.tf`
- **Resources:** `google_compute_address.static`, `google_compute_firewall.allow_http_https`, `google_compute_firewall.allow_ssh`
- **Variables used:** `var.name_prefix`, `var.region`, `var.labels`, `var.ssh_source_cidrs`
- **SECURITY NOTE:** `allow_ssh.source_ranges = var.ssh_source_cidrs` — default `["0.0.0.0/0"]`. In the live tfvars no override is set, meaning SSH port 22 is open to the world on this VM. See Section 10.
- **Lifecycle:** None — no `prevent_destroy`
- **No k3s-api firewall rule** — the plan calls for a scoped tcp:6443 rule; the existing workspace does not have it. K3s API is presumed blocked by default (not exposed) unless K3s was installed and explicitly opened.

### `iam.tf`
- **Resources:** `google_service_account.workload`, 3x `google_project_iam_member` for workload SA
- **Variables used:** `var.project_id`, `var.name_prefix`
- **Lifecycle:** None

### `ci.tf`
- **Resources:** 13 resources covering full GitHub Actions WIF pipeline
- **Variables used:** `var.project_id`, `var.name_prefix`, `var.github_repository`, `var.github_issuer_uri`
- **Lifecycle:** None
- **NOTE:** This is substantially more CI/CD infrastructure than described in the playbook. The playbook says CI/CD is a "sketch — not implemented now." The existing workspace has a fully applied WIF + GitHub OIDC identity plane with 13 managed resources. This was already built and applied.

### `registry.tf`
- **Resources:** `google_artifact_registry_repository.images`
- **Variables used:** `var.project_id`, `var.region`, `var.name_prefix`, `var.labels`
- **Cleanup policies:** keep last 10 versions, delete untagged after 7 days
- **Lifecycle:** None

### `secrets.tf`
- **Resources:** `random_password` x2, `google_secret_manager_secret` x7, `_version` x7, `_iam_member` x7
- **Variables used:** `var.name_prefix`, `var.labels`, `var.project_id`, `var.gemini_api_key`, `var.msg91_auth_key`, `var.msg91_template_id`, `var.razorpay_key_id`, `var.razorpay_key_secret`
- **Lifecycle:** None on the secrets — no `lifecycle.ignore_changes`. This means re-applying after rotating `var.gemini_api_key` etc. creates a new secret version (that is intended). For the auto-generated `random_password` resources, there is similarly no `lifecycle.ignore_changes`, so they can drift.
- **NOTE vs plan:** The plan recommends `kubernetes_secret` with `lifecycle.ignore_changes` for PG/Valkey passwords. The existing workspace uses Google Secret Manager for POSTGRES_PASSWORD (auto-generated by `random_password.postgres_password`), not Kubernetes Secrets. This is a completely different secret management approach.
- **CRITICAL:** The `random_password` results ARE stored in state. The plan acknowledges this risk but proposes `lifecycle.ignore_changes` on Kubernetes Secrets. In the existing workspace there is no such guard on Secret Manager versions.

### `storage.tf`
- **Resources:** `google_storage_bucket.assets`, `google_storage_bucket_iam_member.workload_object_admin`
- **Variables used:** `var.name_prefix`, `var.project_id`, `var.bucket_location`, `var.bucket_force_destroy`, `var.labels`
- **lifecycle_rule (NOT lifecycle block):** 90-day delete for archived objects — this is a bucket lifecycle rule, not a Terraform destroy guard.
- **No `lifecycle { prevent_destroy = true }`** on the bucket.

### `dns.tf`
- **Resources:** `google_dns_managed_zone.primary[0]`, `google_dns_record_set.apex/www/api` — all count=0 (manage_dns=false in tfvars)
- **Variables used:** `var.manage_dns`, `var.domain`, `var.labels`
- **Not in state** — no DNS resources currently provisioned.

---

## 5. Cross-Reference to Playbook Section 14 (Day 1 Acceptance Gates)

| # | Acceptance item | Status | Notes |
|---|---|---|---|
| 1 | `gcloud compute instances list | grep meesell-dev` shows `RUNNING` | PARTIAL | A VM exists but it is named `meesell-vm` (not `meesell-dev`). The playbook target `meesell-dev` does not match the provisioned VM name. |
| 2 | Three firewall rules named `meesell-dev-http/https/k3s-api`; k3s-api scoped to founder IP/32 | PARTIAL | Two rules exist (`meesell-allow-http-https`, `meesell-allow-ssh`). Names do not match playbook names. K3s-api rule (tcp:6443) is absent. SSH is open to 0.0.0.0/0, not founder-IP scoped. |
| 3 | `kubectl get nodes` shows `meesell-dev-master   Ready` | NOT COVERED | K3s is not installed by startup.sh. The node name `meesell-dev-master` is not set anywhere in the existing workspace. |
| 4 | Namespaces `dev` and `staging` with `env` label | NOT COVERED | No Kubernetes provider resources in existing workspace. Namespaces are not managed. |
| 5 | `postgres-0`, `valkey-0`, `supabase-studio-*` all `1/1 Running` in `dev` | NOT COVERED | No Kubernetes StatefulSets or Deployments in existing workspace. |
| 6 | `postgres-0` pg_isready returns `accepting connections` | NOT COVERED | As above — no PG pod managed. |
| 7 | `valkey-0` returns `PONG` | NOT COVERED | As above — no Valkey pod managed. |
| 8 | Supabase Studio port-forward returns HTTP 200/307 | NOT COVERED | As above — no Studio pod managed. |
| 9 | Local `kubectl get nodes` works from founder's laptop | NOT COVERED | Kubeconfig not retrievable — K3s not installed. |
| 10 | Manual backup files in `~/meesell-backups/` | N/A | Operational procedure — not Terraform managed. |
| 11 | `~/.meesell-secrets/` is 700, files are 600 | N/A | Operational procedure — existing workspace uses Secret Manager instead. |
| 12 | `kubectl -n dev get secrets` lists `postgres-credentials` and `valkey-credentials` | NOT COVERED | Kubernetes Secrets not in existing workspace. Secret Manager used instead. |
| 13 | `kubectl -n dev get events | grep -i error` returns nothing | NOT COVERED | No Kubernetes resources managed. |
| 14 | GCP billing budget with 50/75/90% thresholds | NOT COVERED | No `google_billing_budget` resource in existing workspace. |
| 15 | No changes against `meesell-vm`, `shotfox-platform`, `shotfox-mvp1-alpha-dev` | PARTIAL | The existing workspace manages `meesell-vm` — the playbook treats this name as an "other project" VM NOT to be touched. This is a naming collision (see Section 7). |

**Summary: 0 COVERED, 3 PARTIAL, 10 NOT COVERED, 2 N/A** (out of 15 items)

---

## 6. Cross-Reference to Plan Doc Section 6 Resource Mapping

| Plan Section 6 row | Planned TF resource | Existing state status |
|---|---|---|
| 2.2 VM: `google_compute_instance.meesell_dev` | `google_compute_instance.meesell_dev` | NAME MISMATCH — exists as `google_compute_instance.vm` (GCP name: `meesell-vm`) |
| 2.2 Boot disk 30GB Ubuntu 22.04 | boot_disk in instance | NAME MISMATCH — existing is 50GB Ubuntu 24.04 |
| 2.3 `google_compute_firewall.meesell_dev_http` | tcp:80 → 0.0.0.0/0 | NAME MISMATCH — exists as `google_compute_firewall.allow_http_https` (combined 80+443) |
| 2.3 `google_compute_firewall.meesell_dev_https` | tcp:443 → 0.0.0.0/0 | NAME MISMATCH — combined with http in `allow_http_https` |
| 2.3 `google_compute_firewall.meesell_dev_k3s_api` | tcp:6443 → founder_ip/32 | NOT PRESENT — no K3s API firewall rule exists |
| 3.2 K3s startup_script | VM metadata.startup-script | PARTIAL — startup.sh exists but does NOT install K3s (only installs gcloud + writes /etc/meesell.env). K3s is left to manual `scripts/setup-vm.sh`. |
| 4 `kubernetes_namespace.dev` | Kubernetes ns dev | NOT PRESENT |
| 4 `kubernetes_namespace.staging` | Kubernetes ns staging | NOT PRESENT |
| 5.1 `kubernetes_secret.postgres_credentials` | K8s Secret in dev ns | NOT PRESENT — POSTGRES_PASSWORD exists in Secret Manager instead |
| 5.2 `kubernetes_stateful_set.postgres` + Service | PG StatefulSet+PVC | NOT PRESENT |
| 6.1 `kubernetes_secret.valkey_credentials` | K8s Secret in dev ns | NOT PRESENT |
| 6.2 `kubernetes_stateful_set.valkey` + Service | Valkey StatefulSet+PVC | NOT PRESENT |
| 7 `kubernetes_deployment.supabase_studio` + Service | Studio Deployment | NOT PRESENT |
| 8.1 `helm_release.traefik` | Traefik via Helm | NOT PRESENT |
| 8.2 `helm_release.cert_manager` | cert-manager via Helm | NOT PRESENT |
| 8.3 `kubernetes_manifest.cluster_issuer_letsencrypt_prod` | ClusterIssuer | NOT PRESENT |
| 9 `kubernetes_manifest.ingress_studio` | Ingress resource | NOT PRESENT (also domain not set) |
| 13 `google_billing_budget.meesell_dev_budget` | Billing budget | NOT PRESENT |

**Summary: 0 ALREADY IN STATE, 4 NAME MISMATCH, 14 NOT PRESENT**

Additionally, the existing workspace contains resources the plan does NOT describe:
- Artifact Registry (`google_artifact_registry_repository.images`) — not in plan scope
- GitHub Actions WIF pool + OIDC provider (`ci.tf`) — plan only sketches this as future CI/CD
- GCS assets bucket (`google_storage_bucket.assets`) — not in plan scope
- Secret Manager secrets x7 — plan uses Kubernetes Secrets approach instead
- IAP firewall rule (`allow_ssh_iap`) — not in plan scope

---

## 7. Overlaps (Critical)

### The `meesell-vm` naming collision — CRITICAL

The playbook's Section 0 [DANGER] rule states: "NEVER touch `meesell-vm`, `shotfox-platform`, `shotfox-mvp1-alpha-dev` — other projects, out of scope."

The existing `terraform/` workspace manages `google_compute_instance.vm` with GCP resource name `meesell-vm`.

This means: the existing workspace IS the VM the playbook treats as an out-of-scope artifact from another project context. The playbook was written expecting `meesell-dev` to be the new VM to create; the existing workspace already created a VM called `meesell-vm`.

These are either:
(a) The same VM — the playbook naming expectation (`meesell-dev`) diverged from what was actually provisioned (`meesell-vm`), OR
(b) Two separate VMs — `meesell-vm` (Terraform-managed, existing) and `meesell-dev` (the playbook's intended Day 1 target, not yet created)

Evidence strongly supports **(a)**: `terraform output vm_name = "meesell-vm"` and the playbook says "NEVER touch meesell-vm" as context from a prior project session that predates this playbook's authorship. The `local.vm_name = "${var.name_prefix}-vm"` in locals.tf shows the naming convention; the plan intended to change the convention to use `meesell-dev`.

Resolution needed from founder: is `meesell-vm` the intended MeeSell infrastructure VM, or a different project's VM? If it is MeeSell's VM, the playbook's Section 0 danger rule was written to protect OTHER projects' VMs and should be updated to reference `meesell-vm` as the MeeSell VM.

### Per-resource overlap analysis

| Existing resource | GCP/K8s name | Planned resource | Collision type |
|---|---|---|---|
| `google_compute_instance.vm` | `meesell-vm` | `google_compute_instance.meesell_dev` (name: `meesell-dev`) | DUPLICATE — if both are applied, GCP would have two VMs. If the plan re-addresses the existing VM with a new TF name, it requires `terraform state mv`. |
| `google_compute_firewall.allow_http_https` | `meesell-allow-http-https` | `google_compute_firewall.meesell_dev_http` + `_https` (names: `meesell-dev-http`, `meesell-dev-https`) | DUPLICATE — different GCP rule names, effectively same ruleset. |
| `google_compute_firewall.allow_ssh` | `meesell-allow-ssh` | No equivalent in plan (plan has k3s-api only; no explicit SSH rule) | DIFFERENT — existing has SSH; plan does not explicitly create a new SSH rule |
| `google_compute_address.static` | `meesell-ip` | No static IP in plan (plan uses dynamic assignment via access_config) | DIFFERENT — existing has a static IP resource (valuable — this is the address 34.93.9.139 that DNS and the README reference) |
| `random_password.postgres_password` + Secret Manager | `meesell-postgres-password` | `kubernetes_secret.postgres_credentials` with `lifecycle.ignore_changes` | ARCHITECTURAL DIFFERENCE — not a GCP name collision, but two entirely different secret approaches. Both manage the Postgres password. |
| K3s API firewall | (not in existing state) | `google_compute_firewall.meesell_dev_k3s_api` | NOT PRESENT — no collision, purely additive |
| All Kubernetes resources | (not in existing state) | All of modules namespaces/postgres/valkey/supabase_studio/traefik_stack/cert_manager/ingress | NOT PRESENT — no collision, purely additive |
| `google_billing_budget` | (not in existing state) | `google_billing_budget.meesell_dev_budget` | NOT PRESENT — purely additive |

**K3s installed?** No. The `templates/startup.sh` only installs gcloud CLI and writes /etc/meesell.env. It does NOT run the K3s installer script. K3s installation is left to the manual `scripts/setup-vm.sh` step (referenced in the `next_steps` output). There is no evidence K3s was installed — this would have been done manually by the operator after `terraform apply`. Cannot confirm from Terraform state alone.

**PostgreSQL in state?** No Kubernetes PostgreSQL StatefulSet in state. A `meesell-postgres-password` Secret Manager secret exists (auto-generated), but no PG pod is Terraform-managed.

**Valkey in state?** No. Same as PostgreSQL — not in state.

**Billing budget in state?** No.

---

## 8. Gaps

Resources in the new plan that have NO equivalent in existing state:

| Gap | Playbook section | Plan module | Why needed |
|---|---|---|---|
| K3s firewall rule (tcp:6443, founder IP/32) | 2.3 | `module.firewall` | Currently no scoped K3s API access rule. Existing SSH is open to 0.0.0.0/0 which is a risk. |
| Kubernetes namespace `dev` | 4 | `module.namespaces` | Day 1 acceptance item — not Terraform-managed |
| Kubernetes namespace `staging` | 4 | `module.namespaces` | Day 1 acceptance item — not Terraform-managed |
| Kubernetes Secret `postgres-credentials` (in-cluster) | 5.1 | `module.postgres` | App pods reference this k8s secret via secretKeyRef |
| PostgreSQL StatefulSet + Service + PVC | 5.2 | `module.postgres` | Core datastore — not yet deployed |
| Kubernetes Secret `valkey-credentials` (in-cluster) | 6.1 | `module.valkey` | App pods reference this k8s secret |
| Valkey StatefulSet + Service + PVC | 6.2 | `module.valkey` | Cache/queue — not yet deployed |
| Supabase Studio Deployment + Service | 7 | `module.supabase_studio` | DB UI for dev — not yet deployed |
| Traefik Helm release + namespace | 8.1 | `module.traefik_stack` | Ingress controller — not yet deployed |
| cert-manager Helm release + ClusterIssuer | 8.2/8.3 | `module.cert_manager` | TLS — not yet deployed |
| Ingress resources | 9 | `module.ingress` | Blocked on domain purchase |
| GCP billing budget | 13 | `module.billing_budget` | Cost guard — not present (risk) |
| VM renamed to `meesell-dev` (if plan naming is adopted) | 2.2 | `module.vm` | Plan calls for `meesell-dev`; existing is `meesell-vm` |

---

## 9. Structural Differences

| Dimension | Existing workspace | New plan |
|---|---|---|
| Layout | Flat (all .tf files in root) | Modular (`modules/vm/`, `modules/firewall/`, etc.) |
| VM resource name | `google_compute_instance.vm` (GCP name: `meesell-vm`) | `google_compute_instance.meesell_dev` (GCP name: `meesell-dev`) |
| Firewall naming | `meesell-allow-http-https`, `meesell-allow-ssh` (combined) | `meesell-dev-http`, `meesell-dev-https`, `meesell-dev-k3s-api` (separate) |
| Secret management | Google Secret Manager (`google_secret_manager_secret`) + `random_password` | Kubernetes Secrets with `lifecycle.ignore_changes`, `sensitive` var |
| Providers in use | google v6.50.0, random v3.9.0 | Plan proposes google ~> 5.30, kubernetes ~> 2.30, helm ~> 2.13, random ~> 3.6, null ~> 3.2, tls ~> 4.0, time ~> 0.11 |
| Variable convention | `name_prefix` drives all names via locals | Explicit `vm_name`, `founder_ip`, environment-specific tfvars |
| OS image | Ubuntu 24.04 (`ubuntu-2404-lts-amd64`) | Ubuntu 22.04 LTS (`ubuntu-2204-lts`) |
| Disk size | 50GB (variable default) | 30GB (plan default) |
| CI/CD plane | Fully provisioned (WIF + GitHub OIDC + Cloud Build) | Plan sketches GitLab CI, not yet implemented — but existing uses GitHub |
| Static IP | `google_compute_address.static` (34.93.9.139) | Plan's `module.vm` does not mention a static IP resource |
| K3s startup script | Does NOT install K3s (only preps env) | Plan requires cloud-init to run K3s installer |
| Terraform variable patterns | Uses `for_each` over secret map (clean) | Uses for_each in proposed modules |
| `prevent_destroy` | ZERO resources have `prevent_destroy = true` | Plan requires it on VM, both StatefulSets, both PVCs, billing budget |
| Deprecated patterns | `count` on DNS resources — clean `count = var.manage_dns ? 1 : 0` | Plan uses similar `count`/`for_each` — no regression |
| `count` vs `for_each` | `for_each` used for secrets (good); `count` used for DNS zone (acceptable for single conditional) | Plan uses `for_each` for namespaces list — cleaner |

---

## 10. Safety Posture

### `prevent_destroy` audit

**ZERO resources in the existing workspace carry `lifecycle { prevent_destroy = true }`.**

This is a critical safety gap. The following live resources hold state or data and are unprotected:

| Resource | Risk |
|---|---|
| `google_compute_instance.vm` (meesell-vm) | Destroying this VM destroys K3s, all pods, and all PVC data. No `prevent_destroy`. |
| `google_storage_bucket.assets` | Application images, exports, and backups live here. `bucket_force_destroy = false` prevents destroy from deleting objects but does not prevent the TF resource from being removed. No `prevent_destroy` on the bucket resource itself. |
| `random_password.jwt_secret` | Destroying and recreating would generate a new JWT secret, invalidating all existing user sessions. No `prevent_destroy` and no `lifecycle.ignore_changes`. |
| `random_password.postgres_password` | Destroying and recreating would generate a new password that is out of sync with any running PostgreSQL instance. No `prevent_destroy`. |
| `google_secret_manager_secret_version.version["POSTGRES_PASSWORD"]` | Lives in Secret Manager; `terraform destroy` would delete it. No `prevent_destroy`. |

### Open security risks

| Risk | Severity | Detail |
|---|---|---|
| SSH port 22 open to 0.0.0.0/0 | HIGH | `google_compute_firewall.allow_ssh` has `source_ranges = var.ssh_source_cidrs` with default `["0.0.0.0/0"]`. `terraform.tfvars` does not override this. Port 22 on the VM (34.93.9.139) is world-reachable. The plan calls for scoping to founder IP/32. |
| No K3s API firewall scoping | MEDIUM | The plan's required tcp:6443 scoped rule does not exist. If K3s IS installed and the default K3s port is reachable, it would be protected only by TLS client cert validation. |
| Placeholder secrets in Secret Manager | MEDIUM | `terraform.tfvars` shows `gemini_api_key = "placeholder"`, `msg91_auth_key = "placeholder"`, etc. These placeholder values have been written to Secret Manager version 1. Any app reading from Secret Manager will get "placeholder" strings, not real keys. |
| `random_password` in local state (unencrypted) | MEDIUM | `terraform.tfstate` is local (not GCS, not encrypted). It contains the base64-encoded JWT secret and Postgres password in plaintext. The state file is on the founder's laptop. |
| No billing budget | MEDIUM | No `google_billing_budget` resource. If costs spike there is no automated alert. |

---

## 11. Account / Project / Billing Lock Current State

### `project_id` — variable-driven or hardcoded?

`project_id` is a **required input variable** with no default. It is supplied in `terraform.tfvars` as `project-1f5cbf72-2820-4cdb-949`. This is the correct pattern — not hardcoded.

### Billing account referenced?

No `google_billing_budget` resource. No `billing_account_id` variable. The billing account (`01620D-6785AB-0E4698`) is referenced nowhere in the existing workspace. This means:
- No billing lock (budget) is in place.
- The existing workspace cannot be used to manage billing budgets as-is.

### Auth pattern

The existing workspace uses **Application Default Credentials (ADC)**. The `provider "google"` block has no `credentials` argument. Terraform calls authenticate via `gcloud auth application-default login`. The `terraform.tfvars.example` and `README.md` both instruct the operator to `gcloud auth application-default login` as `vaishnaviramoorthy@gmail.com` before applying. No service account JSON key is stored.

The `terraform.tfvars` `ssh_user = "mugunthansrinivasan"` shows the operator is Mugunthan (the founder's laptop), not the Vaishnavi account. This means Terraform was likely applied as `mugunthansrinivasan@gmail.com` via ADC, not as `vaishnaviramoorthy@gmail.com`. This matters for billing: if the project is linked to the Vaishnavi billing account, ADC as the wrong account may have used a different project or different credit pool. This warrants confirmation.

### Plan Section 19 lock layers gap analysis (A through F)

| Layer | Plan intent | Current state |
|---|---|---|
| A: Billing account locked to project | Budget resource ties billing account ID to project | NO budget resource exists. Billing account not referenced in TF. |
| B: Project ID enforced as required variable | `var.project_id` required, no default | DONE — correctly implemented |
| C: Budget with multi-threshold alerts | `google_billing_budget` at 50/75/90% | ABSENT |
| D: ADC identity confirmed pre-apply | README documents the check; no code enforcement | PARTIAL — documented but not enforced in code |
| E: `prevent_destroy` on critical resources | VM, PVCs, budget | ABSENT — zero resources guarded |
| F: State backend isolation (GCS per environment) | GCS bucket with versioning + locking | ABSENT — local state only |

---

## 12. Path A / B / C Recommendation

### Path A — Extend existing flat workspace, revise plan to match

Accept the existing workspace's scope (GCP-layer only: VM, firewall, IAM, GCS, AR, Secret Manager, CI/CD identity) as the "infrastructure plane." Do NOT add Kubernetes resources to this workspace. Separately, create Kubernetes manifests (e.g., `k8s/`) or a second Terraform workspace for Kubernetes layer. Rename resources via `terraform state mv` to align naming where necessary (e.g., the VM can stay named `meesell-vm` and the plan's naming convention is updated to match). Add the missing safety items: `prevent_destroy` on the VM + bucket + random passwords, the billing budget resource, and the K3s API firewall rule.

### Path B — Refactor existing state into the plan's modular structure

Use `terraform state mv` to move all 57 existing resource instances into the modular layout (e.g., `module.vm.google_compute_instance.meesell_dev`). Then extend the modular workspace with Kubernetes modules. This is clean long-term but requires ~30 careful `terraform state mv` commands, each of which must be run correctly or the next `terraform apply` will attempt to destroy and recreate live resources.

### Path C — Keep existing for its scope, scaffold modular plan in a separate directory

Leave `terraform/` unchanged. Create `terraform-k8s/` (or `terraform-runtime/`) for the Kubernetes layer. The GCP resources (VM, networking, IAM, GCS, AR, secrets) remain in `terraform/`. Kubernetes namespaces, StatefulSets, Helm releases, and billing budget go in the new directory. The `terraform-k8s/` workspace reads outputs from `terraform/` via `terraform_remote_state` or by hard-coding the VM IP/endpoint.

### Recommendation: Path A

**Justification:** Path A requires the least state manipulation risk and delivers the fastest path to Day 1 acceptance. The existing workspace already has a working GCP identity, networking, and secrets foundation. The Kubernetes resources (namespaces, StatefulSets, Helm releases) can be added directly to this flat workspace as new files (e.g., `k8s.tf`, `billing.tf`) without any `state mv` operations. The naming mismatch (`meesell-vm` vs `meesell-dev`) can be resolved by either (a) updating the plan naming convention to use `meesell-vm`, or (b) doing a single `terraform state mv google_compute_instance.vm module.vm.google_compute_instance.meesell_dev` once the modular structure is ready. Path B's `state mv` risk is too high for a live VM with data. Path C creates coordination overhead across two state files.

**Safest concrete next action under Path A:**
1. Add `lifecycle { prevent_destroy = true }` to `vm.tf`, `storage.tf`, and `secrets.tf` for the random password resources — this is a code change with no infrastructure impact, zero risk.
2. Add `google_billing_budget` to a new `billing.tf` file — purely additive, no existing resources touched.
3. Add the K3s API firewall rule to `network.tf` — additive.
4. Narrow `ssh_source_cidrs` in `terraform.tfvars` to the founder's current IP.
5. Then add Kubernetes provider + all Kubernetes resources in `k8s.tf` after K3s is confirmed installed.

**Founder approval needed before any action:**
- Confirmation that `meesell-vm` IS the MeeSell project VM (not an out-of-scope VM the playbook forbids touching).
- Confirmation that the billing account `01620D-6785AB-0E4698` should be linked in the new `billing.tf`.
- Confirmation that Terraform was applied as the `vaishnaviramoorthy@gmail.com` account (or acknowledgement that it was applied as Mugunthan's account and this is acceptable).

---

## Appendix: State Resource Count by Category

| Category | Instance count |
|---|---|
| GCP API enables | 9 |
| Compute (VM + static IP) | 2 |
| Firewall rules | 3 |
| IAM service accounts | 2 |
| IAM member bindings | 11 |
| WIF pool + provider | 2 |
| Secret Manager secrets | 7 |
| Secret Manager versions | 7 |
| Secret Manager IAM | 7 |
| Artifact Registry repo | 1 |
| GCS bucket | 1 |
| GCS bucket IAM | 1 |
| Random passwords | 2 |
| OS login metadata | 1 |
| Data sources | 1 |
| **TOTAL** | **57** |
