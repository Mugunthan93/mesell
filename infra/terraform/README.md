# MeeSell Infra — Terraform

Production infrastructure for MeeSell. Managed by Terraform.
Scope: GCP-layer resources only (Pass 1) + Kubernetes workloads (Pass 2, not yet scaffolded).

**R&D workspace is out of scope.** The directory `mesell/terraform/` is a live R&D flat workspace
managing `meesell-vm` (sandbox). Do NOT modify it from here. All production work is in this directory.
Full rationale: `docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §1` and `§2`.

---

## Purpose and Scope

Pass 1 (this workspace) provisions the following GCP resources:

| Module | Resource | Description |
|---|---|---|
| `apis` | `google_project_service` | Enable 9 required GCP APIs |
| `ci_identity` | SA + WIF pool + provider + IAM | GitLab CI keyless auth via Workload Identity |
| `artifact_registry` | `google_artifact_registry_repository` | Production Docker image registry |
| `asset_bucket` | `google_storage_bucket` | Production GCS asset bucket |
| `app_secrets` | `google_secret_manager_secret` | Secret containers (values populated manually) |
| `vm` | `google_compute_instance` | K3s host VM (e2-standard-2, asia-south1-a) |
| `firewall` | `google_compute_firewall` | HTTP/HTTPS open + K3s API locked to founder IP |
| `billing_budget` | `google_billing_budget` | Spending alerts at 50%, 75%, 90% |

Pass 2 (future) adds Kubernetes workloads (namespaces, Postgres, Valkey, Traefik, cert-manager, Ingress).
See `docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §11` for the full bootstrap sequence.

---

## Account Lock

Six security layers prevent accidental apply to a wrong account or project.
Full rationale: `docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §19`.

| Layer | Mechanism | Where |
|---|---|---|
| A | Hardcoded project ID + billing account in `providers.tf` and `modules/billing_budget/main.tf` | Code review required to change |
| B | `data.google_project.current` reads actual authenticated project at plan time | `main.tf` |
| C | `null_resource.account_lock_guard` preconditions fail plan if project or billing drifts | `main.tf` |
| D | Makefile.tf sets `CLOUDSDK_CORE_ACCOUNT` and `CLOUDSDK_CORE_PROJECT` env vars | `Makefile.tf` |
| E | `tf-preflight.sh` checks gcloud auth + billing + ADC + terraform version before any apply | `scripts/tf-preflight.sh` |
| F | `google_billing_budget` with `prevent_destroy = true` prevents silent cost overrun | `modules/billing_budget/main.tf` |

**Locked constants (do not change without founder review):**

```
GCP account:   vaishnaviramoorthy@gmail.com
Project ID:    project-1f5cbf72-2820-4cdb-949
Billing acct:  01620D-6785AB-0E4698
Region:        asia-south1
Zone:          asia-south1-a
```

---

## Bootstrap — Pre-Terraform Steps (run once)

```bash
# 1. Set up Application Default Credentials as the locked account.
gcloud auth application-default login --account=vaishnaviramoorthy@gmail.com

# 2. Make the preflight script executable.
chmod +x scripts/tf-preflight.sh

# 3. Verify all checks pass before proceeding.
scripts/tf-preflight.sh
```

---

## Pass 1 — GCP-Layer Provisioning

```bash
cd /path/to/mesell    # workspace root (where Makefile.tf lives)

# 1. Initialise Terraform (downloads providers, sets up local backend).
make -f Makefile.tf tf-init

# 2. Discover your current public IP for the K3s API firewall rule.
export FOUNDER_IP=$(curl -4 ifconfig.me)
echo "FOUNDER_IP = $FOUNDER_IP"    # confirm it looks like a real IPv4

# 3. Generate the plan for Pass 1.
FOUNDER_IP=$FOUNDER_IP make -f Makefile.tf tf-plan-pass1

# 4. Review the plan output carefully. Confirm:
#    - project = project-1f5cbf72-2820-4cdb-949
#    - No unexpected destroys
#    - K3s API firewall source_ranges = ["<your IP>/32"] (NOT 0.0.0.0/0)

# 5. Apply (requires confirmation prompt).
FOUNDER_IP=$FOUNDER_IP make -f Makefile.tf tf-apply-pass1
```

After apply completes:
- Retrieve the VM's external IP from `terraform output vm_external_ip`.
- Follow the playbook from `docs/INFRASTRUCTURE_PLAYBOOK.md §3` to SSH in and verify K3s.
- Populate secret values: see `modules/app_secrets/main.tf` for the `gcloud secrets versions add` command.

---

## Pass 2 — Kubernetes Workloads (placeholder)

Pass 2 modules are not yet scaffolded. See `docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §11` for the planned sequence.

```bash
# After K3s is running and kubeconfig is retrieved:
make -f Makefile.tf tf-plan-pass2   # prints "Pass 2 not yet scaffolded" and exits
make -f Makefile.tf tf-apply-pass2  # same
```

---

## Common Operations

```bash
# Format all .tf files.
make -f Makefile.tf tf-fmt

# Dry-run a destroy to see what would be deleted (does not apply).
FOUNDER_IP=$(curl -4 ifconfig.me) make -f Makefile.tf tf-destroy-check

# Re-run plan with a different environment (staging example).
FOUNDER_IP=$(curl -4 ifconfig.me) cd infra/terraform && \
  terraform plan -var-file=environments/staging.tfvars -var="founder_ip=$FOUNDER_IP"
```

---

## Troubleshooting

**Account lock violation at `terraform plan`**
```
ACCOUNT LOCK VIOLATION: provider authenticated to project 'X', expected 'project-1f5cbf72-...'
```
Fix: `gcloud auth application-default login --account=vaishnaviramoorthy@gmail.com` and re-run via `make -f Makefile.tf`.

**ADC file missing**
```
WARN: ~/.config/gcloud/application_default_credentials.json not found
```
Fix: run the `gcloud auth application-default login` command shown in the preflight output.

**API not enabled**
```
Error: googleapi: Error 403: ... has not been used in project
```
Fix: the `google_project_service.required` resource enables all required APIs. Ensure `module.apis` was targeted first in Pass 1 (`-target=google_project_service.required`). If you skipped it, run: `cd infra/terraform && terraform apply -target=google_project_service.required -var-file=environments/dev.tfvars -var="founder_ip=<ip>"`.

**Founder IP changed (K3s API unreachable after a network change)**
```
# Firewall rule blocks your new IP. Update and re-apply:
export FOUNDER_IP=$(curl -4 ifconfig.me)
FOUNDER_IP=$FOUNDER_IP make -f Makefile.tf tf-plan-pass1   # shows firewall update
FOUNDER_IP=$FOUNDER_IP make -f Makefile.tf tf-apply-pass1
```

**`curl -4 ifconfig.me` returns nothing or times out**
```
# ifconfig.me without -4 returns IPv6 on dual-stack networks, which the
# firewall module's IPv4-only validation rejects. The -4 flag forces IPv4.
# If -4 also fails (rare — network preference or firewall blocks IPv4 outbound):
export FOUNDER_IP=$(curl -s api4.ipify.org)
echo "FOUNDER_IP = $FOUNDER_IP"   # must be a dotted-quad, e.g. 203.0.113.42
```

---

## What the Playbook Still Owns

Day-to-day operator procedures (SSH access, K3s health checks, backup, secret rotation,
incident response) are imperative bash procedures in `docs/INFRASTRUCTURE_PLAYBOOK.md §13`.
Terraform manages desired state; the playbook manages operational procedures. See
`docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §13` for the explicit boundary between the two.
