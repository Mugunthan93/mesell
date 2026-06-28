## SSOT Architecture Document Published — 2026-06-05

**File:** `docs/INFRASTRUCTURE_ARCHITECTURE.md`
This is now the canonical reference for live infrastructure. When asked "what's the state of X" check this file FIRST before re-deriving from `gcloud` / `kubectl` / `terraform state`. The file is updated whenever live infra changes — anyone who modifies live state owns the corresponding doc update.

**Structure (13 sections):** Overview, Architecture Diagram (ASCII), GCP Resources, Secret Manager (7), Kubernetes Cluster (K3s v1.35.5), Workloads (per ns), Networking + Ingress (5 hosts), In-Cluster Service Discovery (DNS map), Terraform Module Map (14 modules), CI/CD (WIF wired, pipeline pending), Pending (Phase D), Operational Runbooks (5), Deferred.

**Implications for future tasks:**
- When state of a live resource is being asked, link to the relevant section of `INFRASTRUCTURE_ARCHITECTURE.md` instead of re-discovering via `gcloud`. Faster + consistent.
- `STATUS_INFRA.md` remains the rolling journal (per-session updates); SSOT is the steady-state truth.
- Update the SSOT immediately after every live infra change; otherwise the document rots and the agent loses trust in it.
