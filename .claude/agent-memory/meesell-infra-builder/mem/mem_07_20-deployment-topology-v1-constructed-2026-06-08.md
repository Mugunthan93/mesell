## §20 Deployment Topology V1 CONSTRUCTED — 2026-06-08

**Outcome:** All 10 k8s manifests updated to §20 spec (9 changed; `k8s/frontend.yaml` already correct). Full `kubectl apply --dry-run=client -f k8s/` PASSES with 0 errors. NOT applied to cluster (construction/documentation phase; §22 acceptance is next gate).

**Secret Manager population (Pass 2):**
| Secret ID | Status |
|---|---|
| `refresh-token-pepper` | ✅ VERSION 1 LIVE — `openssl rand -hex 32` (64 bytes, no newline). Local backup `~/.meesell-secrets/refresh-token-pepper` (chmod 600). |
| `razorpay-webhook-secret` | ⚠️ SM container created, ZERO versions — FOUNDER ESCALATION (Razorpay dashboard → Webhooks → signing secret). Blocks §7 (iam). |
| `langfuse-secret-key` | ⚠️ SM container created, ZERO versions — FOUNDER ESCALATION (LangFuse cloud account at cloud.langfuse.com). Blocks §6A (ai_ops). Also need LANGFUSE_PUBLIC_KEY into k8s/config.yaml. |

Exact populate commands live in `k8s/secrets.yaml.example` comments.

**K8s Secret name migration:** app containers (api, worker, backup-cronjob) now reference `backend-secrets` (was `meesell-secrets`). `meesell-secrets` kept only as legacy alias note. Namespace fixed `meesell`→`dev` on postgres/valkey/backup.

**CRITICAL reconciliation — datastores are TF-managed StatefulSets, NOT Deployments:**
- Live `postgres-0` and `valkey-0` are **StatefulSets** owned by Terraform (`module.postgres_dev`, `module.valkey_dev`).
- They read dedicated secrets `postgres-credentials` / `valkey-credentials` via `valueFrom: secretKeyRef` — NOT `backend-secrets`, NOT `envFrom`. This is the Day-1 bootstrap pattern (playbook §5.1/§6.1) preserved by TF.
- The §20 sketch proposed a Deployment + `envFrom backend-secrets` for postgres — this CONTRADICTS live state. **Live state is SSOT (playbook §0).** So `k8s/postgres.yaml`, `k8s/valkey.yaml`, `k8s/ingress.yaml` are now DOCUMENTATION-ONLY with prominent "DO NOT APPLY" headers, mirroring live.
- Rule for §20.C "envFrom: secretRef: backend-secrets": applies to APPLICATION containers (api, worker, backup) only — not bootstrap datastore StatefulSets.
- Live verified specs: postgres `postgres:16`, req 200m/500Mi lim 1/1Gi; valkey `valkey/valkey:8`, req 100m/200Mi lim 500m/512Mi, args maxmemory 128mb allkeys-lru. Left at live values (D-flags D2/D3), did NOT bump to §20.G targets because TF owns them.

**D-flags recorded:**
- D1: GCS single bucket `meesell-prod-assets` (spec §20 said `meesell-images`; live SSOT is single bucket per Phase A). Accepted. Paths: images `{user_id}/{product_id}/{idx}.jpg`, exports `exports/{user_id}/{export_id}.xlsx`, backups `backups/`.
- D2: postgres TF StatefulSet + postgres-credentials (not Deployment + backend-secrets). Doc-only manifest.
- D3: valkey TF StatefulSet, resources left at live (not §20.G 200m/500m CPU); stale yaml maxmemory 512mb corrected to 128mb in doc.

**V0-rot carry-forward bug:** `backend/tests/test_config.py` imports `app.shared.config` but references `app.config` (`importlib.reload(app.config)`, `app.config.settings`) — config module moved to `app/shared/config.py`; `app/config.py` no longer exists. 5 tests FAIL. NOT infra scope — carry-forward for a backend specialist. `tests/test_celery_*.py` (12) all PASS.

**Operational learnings (this session):**
- `gcloud` lives at `/opt/homebrew/bin/gcloud`, `kubectl` at `/usr/local/bin/kubectl` — NOT on the default non-login Bash PATH. Always `export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"` at the top of every Bash call (cwd + env reset between calls).
- No `gcp-mesell` SSH alias. `~/.ssh/config` only has `gcp-nexus` → `35.244.22.79` (a DIFFERENT VM, not the mesell VM `35.234.223.66`). Tunnel restore must use `kubectl port-forward svc/postgres 5433:5432 -n dev`, NOT an SSH alias. Background log at `/tmp/meesell-pf-postgres.log`.
- `psql` is NOT installed on the laptop. For DB queries use `kubectl exec postgres-0 -n dev -- psql -U meesell -d meesell -c "..."` instead of a local psql over the tunnel.
- Founder IP rotated again → `122.164.87.94` (was 122.164.85.51). Firewall NOT touched this session (kubectl already worked). If kubectl times out next session, apply the TF firewall IP-rotate procedure (above).
- Pool budget verified: postgres `max_connections=100`, baseline ~6 conns; 2 API×15 + 2 worker×15 = 60 < 100. OK.

---
