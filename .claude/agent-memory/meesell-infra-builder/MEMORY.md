# Memory — meesell-infra-builder

## Agent Identity
Infrastructure builder for MeeSell. Owns VM lifecycle, K3s cluster, namespaces, Postgres/Valkey/Supabase pods, ingress, TLS, secret management, GCP cost monitoring. Decentralized memory ecosystem.

## Initial State
No prior memories. First task will populate this file.

## MEMORY.md
(Index of memory files — populated as agent works)

## Agent Routing Override — 2026-06-04

**Why:** User-level agent-routing hook in `~/.claude/settings.json` originally allowed only `nexus:*`, `claude-code-guide`, `statusline-setup`. This blocked all 18 meesell-* dispatches.

**Where fixed:**
- `~/.claude/settings.json` (user-level) — regex extended to `^meesell-|^nexus:|^claude-code-guide$|^statusline-setup$`
- `/Users/mugunthansrinivasan/Project/mesell/.claude/settings.json` (project-local) — explicit override

**Backup:** `~/.claude/settings.json.bak.20260604-114224`

**Debug commands:**
```bash
# Verify user-level hook has meesell-
grep -o 'meesell-' ~/.claude/settings.json | head -1
# Should output: meesell-

# Test routing regex
echo "meesell-x" | grep -qE '^meesell-|^nexus:|^claude-code-guide$|^statusline-setup$' && echo ALLOW || echo BLOCK
# Should output: ALLOW
```

**Critical knowledge:**
- Auto Mode classifier BLOCKS agents from modifying these settings files (correct security behavior)
- Must be done manually by founder OR via direct Bash heredoc/Python from master session
- Agent specs at `.claude/agents/meesell-*.md` only loaded into Claude Code at session START
- Sessions active before spec creation cannot dispatch meesell-* until restart
- Fresh sessions automatically load all 18 specs on startup

**Status:** Routing layer fixed. Agent loading requires session restart for active sessions.

---

## Secret Manager Population Status — 2026-06-04

GCP project: `project-1f5cbf72-2820-4cdb-949` (numeric: `888244156264`)
Secret Manager secrets created in Pass 1. Populate via:
`gcloud secrets versions add <secret-id> --project=project-1f5cbf72-2820-4cdb-949 --data-file=- <<< "$VALUE"`
Local backup directory: `~/.meesell-secrets/` (chmod 700, each file chmod 600)

| Secret ID | Status | Notes |
|-----------|--------|-------|
| `msg91-auth-key` | ✅ VERSION 1 LIVE | Service name: DEVOTP. IP whitelisted: 122.164.85.200 (NOTE: founder IP rotated to 122.164.85.51 on 2026-06-05 — MSG91 whitelist may need update if OTP calls fail). Local backup: ~/.meesell-secrets/msg91-auth-key |
| `msg91-template-id` | ✅ VERSION 1 LIVE (2026-06-05) | Sourced from R&D meesell-msg91-template-id (11 chars). Phase A. |
| `gemini-api-key` | ✅ VERSION 1 LIVE | AIzaSyB... (populated 2026-06-04). Local backup: ~/.meesell-secrets/gemini-api-key |
| `jwt-secret` | ✅ VERSION 1 LIVE | Auto-generated 64-byte hex (openssl rand -hex 64). Local backup: ~/.meesell-secrets/jwt-secret |
| `razorpay-key-id` | ✅ VERSION 1 LIVE | TEST key (rzp_test_*). Local backup: ~/.meesell-secrets/razorpay-key-id |
| `razorpay-key-secret` | ✅ VERSION 1 LIVE | TEST secret. Local backup: ~/.meesell-secrets/razorpay-key-secret |
| `audit-pii-salt` | ✅ VERSION 1 LIVE (2026-06-05) | Generated `openssl rand -hex 32` (64 chars). Local backup: ~/.meesell-secrets/audit-pii-salt (chmod 600). Phase A. |

Verify any secret: `gcloud secrets versions access latest --secret=<id> --project=project-1f5cbf72-2820-4cdb-949`

---

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

## SSOT Architecture Document Published — 2026-06-05

**File:** `docs/INFRASTRUCTURE_ARCHITECTURE.md`
This is now the canonical reference for live infrastructure. When asked "what's the state of X" check this file FIRST before re-deriving from `gcloud` / `kubectl` / `terraform state`. The file is updated whenever live infra changes — anyone who modifies live state owns the corresponding doc update.

**Structure (13 sections):** Overview, Architecture Diagram (ASCII), GCP Resources, Secret Manager (7), Kubernetes Cluster (K3s v1.35.5), Workloads (per ns), Networking + Ingress (5 hosts), In-Cluster Service Discovery (DNS map), Terraform Module Map (14 modules), CI/CD (WIF wired, pipeline pending), Pending (Phase D), Operational Runbooks (5), Deferred.

**Implications for future tasks:**
- When state of a live resource is being asked, link to the relevant section of `INFRASTRUCTURE_ARCHITECTURE.md` instead of re-discovering via `gcloud`. Faster + consistent.
- `STATUS_INFRA.md` remains the rolling journal (per-session updates); SSOT is the steady-state truth.
- Update the SSOT immediately after every live infra change; otherwise the document rots and the agent loses trust in it.

## Phase B Verified Live State (snapshot 2026-06-05)

For quick recall without re-querying GCP / K8s:
- 5 LE certs Ready=True on: `studio.mesell.xyz` (issued 2026-06-04), `api.mesell.xyz`, `dev.mesell.xyz`, `testing.mesell.xyz`, `staging.mesell.xyz` (issued 2026-06-05).
- All 7 Secret Manager secrets at version 1, populated. Local backups at `~/.meesell-secrets/`.
- VM SA `888244156264-compute@...` has `artifactregistry.reader` on `meesell-prod-images` and `storage.objectAdmin` on `gs://meesell-prod-assets`.
- Valkey args confirmed live: `--maxmemory 128mb --maxmemory-policy allkeys-lru`. Runtime verified via `valkey-cli config get`.
- TF state: clean (last drift check during PASS2B-COMPLETE / Phase A applies). Local file at `infra/terraform/terraform.tfstate`.
- Outstanding application work: `dev/api`, `dev/worker`, `dev/frontend` Deployments not yet created (Phase D — gated on image builds).
