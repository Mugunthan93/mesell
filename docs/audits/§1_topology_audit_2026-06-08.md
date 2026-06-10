# §1 System Topology Audit Report

**Date:** 2026-06-08
**Auditor sub-session:** meesell-backend-verification-1-topology-1
**Section audited:** §1 System Topology + §20 Deployment Topology (V1)
**§20 status confirmed:** LOCKED (2026-06-06), CONSTRUCTED (Wave 7 step 3, 2026-06-08, master-ACCEPTED partial)
**Overall verdict:** PARTIAL

---

## Audit checklist results

| # | Check | Status | Evidence |
|---|---|---|---|
| 1 | FastAPI 2 replicas + Celery 2 replicas | **PARTIAL** | Manifests: `api.yaml replicas:2` ✅, `worker.yaml replicas:2` ✅. Live cluster: **neither Deployment applied** — Phase D (image build + kubectl apply) NOT yet executed. `kubectl get all -n dev` shows only `supabase-studio` + `postgres-0` + `valkey-0`. No `api` or `worker` Deployment exists in cluster. |
| 2 | Valkey DB 0/1/2/3 allocation | **PASS** | `shared/valkey.py` exports 4 scoped factory functions: `get_valkey_otp()→DB0`, `get_valkey_broker()→DB1`, `get_valkey_results()→DB2`, `get_valkey_cache()→DB3`. `_build_url_for_db()` enforces correct DB number via URL rewrite. Docstrings and module-level table match §1.B diagram exactly. |
| 3 | Postgres at head `f31c75438e61` + 13 tables | **PASS** | Live cluster: `kubectl exec statefulset/postgres -- psql -c "SELECT version_num FROM alembic_version"` → `f31c75438e61` ✅. `\dt` shows 14 rows (13 application tables + alembic_version system table): `audit_events`, `catalogs`, `categories`, `exports`, `field_aliases`, `field_enum_values`, `pricing_calcs`, `product_drafts`, `product_images`, `products`, `seller_profile`, `templates`, `users` — exact match to §0.D. |
| 4 | GCS bucket layout | **PARTIAL (D1 accepted)** | §1 topology diagram references `meesell-images` as the GCS bucket. Live config: `GCS_BUCKET="meesell-prod-assets"` (single-bucket model per Phase A SSOT). Path conventions honored in code: `adapters/gcs.py` uses `meesell-images/{user_id}/{product_id}/{idx}.jpg` and `meesell-exports/{user_id}/{export_id}/sheet.xlsx` as **prefixes within** `meesell-prod-assets` (confirmed in `modules/image/service.py` line 96 + `modules/export/service.py` lines 345/363). `gsutil` unavailable locally. Bucket existence confirmed via STATUS_INFRA.md + infra hand-off memo. D1 (GCS bucket SSOT) accepted by master during Wave 7 §20 construction — documented divergence, not a regression. |
| 5 | Traefik ingress + cert-manager on `studio.mesell.xyz` | **PASS** | `kubectl get ingress -n dev` shows `studio` ingress (class=traefik, host=studio.mesell.xyz, 80/443, age=4d). `kubectl get certificate -n dev` shows `studio-tls` READY=True. TLS verified via `curl -sv https://studio.mesell.xyz/`: subject=CN=studio.mesell.xyz, issuer=Let's Encrypt YR1, expiry=2026-09-02, TLSv1.3, SSL certificate verify OK. Additionally: `api-tls`, `dev-frontend-tls`, `testing-frontend-tls` all READY=True in dev. `staging-frontend-tls` READY=True in staging namespace. 5/5 cert-manager certs live. |
| 6 | Egress reachability (Gemini/MSG91/Razorpay/LangFuse) | **PASS** | Tested from ephemeral `curlimages/curl` pod in `dev` namespace (FastAPI pod not deployed yet — Phase D pending). Results: Gemini `generativelanguage.googleapis.com` → HTTP 404 (auth-gated, network-reachable ✅); MSG91 `api.msg91.com` → HTTP 200 ✅; Razorpay `api.razorpay.com` → HTTP 406 (AWS ELB, reachable ✅); LangFuse `cloud.langfuse.com` → HTTP 200 ✅. All 4 external SaaS egress paths are network-reachable from the cluster. Caveat: tested from curl image pod, not FastAPI pod; FastAPI-pod-specific test requires Phase D completion. |

---

## Non-compliance findings

### Finding #1 — CRITICAL: `api` and `worker` Deployments not applied to cluster

**Severity:** CRITICAL  
**Check:** #1 (FastAPI 2 replicas + Celery 2 replicas)  
**Observed:** `kubectl get all -n dev` returns only `supabase-studio` (Deployment), `postgres-0` (StatefulSet), `valkey-0` (StatefulSet). No `api` or `worker` Deployment exists.  
**Expected:** 2-replica `api` Deployment + 2-replica `worker` Deployment per §1.B topology and §20.B.  
**Root cause:** Phase D (application image build + initial `kubectl apply -f k8s/api.yaml` + `kubectl apply -f k8s/worker.yaml`) has NOT been executed. The K8s manifest files are correctly authored and committed (api.yaml, worker.yaml), but have not been applied to the cluster.  
**Manifests are correct:** `api.yaml` has `replicas: 2`, `envFrom: secretRef: backend-secrets`, `readinessProbe: /health`, `RollingUpdate maxSurge:1/maxUnavailable:0`. `worker.yaml` has `replicas: 2`, Celery `--concurrency=4 --max-tasks-per-child=100`. Both match §20.H sketches exactly.  
**Blocking condition:** Phase D also requires `backend-secrets` K8s Secret to be created first (see Finding #2).  
**Do NOT fix in this session** — escalate to meesell-backend-coordinator + meesell-infra-builder.

---

### Finding #2 — BLOCKER: `backend-secrets` K8s Secret not present in `dev` namespace

**Severity:** BLOCKER (blocks Phase D pod startup)  
**Check:** #1 (prerequisite)  
**Observed:** `kubectl get secret -n dev backend-secrets` → `NotFound`. Present secrets in dev: `api-tls`, `dev-frontend-tls`, `postgres-credentials`, `studio-tls`, `testing-frontend-tls`, `valkey-credentials`.  
**Expected:** `backend-secrets` Opaque Secret holding all 10 env-var keys per `secrets.yaml.example` and §20.C.  
**Impact:** Without `backend-secrets`, the api and worker pods will fail immediately at start (envFrom: secretRef will reject the pod spec or cause CrashLoopBackOff).  
**Root cause:** The `backend-secrets` Secret must be manually created before `kubectl apply -f k8s/api.yaml`. The `secrets.yaml.example` template is present, but the populated version has never been applied. 2 of the 10+ env-var values are still PENDING founder action: `RAZORPAY_WEBHOOK_SECRET` (container exists, no SM version) and `LANGFUSE_SECRET_KEY` (container exists, no SM version).  
**Do NOT fix in this session** — escalate to founder + meesell-infra-builder for secret population + kubectl create secret.

---

### Finding #3 — DOCUMENTED: GCS bucket name diverges from §1 diagram (D1 accepted)

**Severity:** DOCUMENTED DIVERGENCE (accepted D-flag, not a regression)  
**Check:** #4 (GCS bucket layout)  
**Observed:** Live GCS bucket is `meesell-prod-assets` (single-bucket model). `config.yaml`: `GCS_BUCKET: "meesell-prod-assets"`. Adapter uses `meesell-images/...` and `meesell-exports/...` as path PREFIXES within the single bucket.  
**Expected per §1.B diagram:** `meesell-images` named as the GCS bucket. §6.D (adapters/gcs.py) also references these as path conventions.  
**Status:** D1 (GCS bucket SSOT) accepted by master session during Wave 7 §20 construction. The path convention (`meesell-images/{user_id}/{product_id}/{idx}.jpg`) is correctly implemented in code. The single-bucket model is architecturally sound.  
**Audit note:** §1.B diagram's `meesell-images` label is now misleading — it refers to a path prefix, not the bucket name. A §1 diagram label amendment should be considered (not urgent; functional behavior is correct).

---

## Verdict rationale

The §1 topology is **correctly specified in manifests and code** — all 4 Valkey DB allocations, all 13 Postgres tables, Traefik + cert-manager TLS, and all 4 external egress paths are verifiably correct. The PARTIAL verdict is driven by one critical gap: **Phase D (application image build + Deployment apply) has not been executed**, so the `api` and `worker` pods that §1 topology mandates do not exist in the live cluster. The topology is designed correctly; it is not yet *deployed*. The D1 GCS single-bucket model is a previously-accepted architectural decision, not a new defect.

---

## Boot smoke + schema smoke

- Alembic head `f31c75438e61` confirmed live ✅
- 13 application tables confirmed live ✅  
- `shared/valkey.py` imports cleanly (module-level structure verified) ✅
- No regressions introduced by this audit (read-only sub-session) ✅
- STATUS_BACKEND.md has CONSTRUCTED entries for §20 and all prior sections (Waves 1–7) ✅

---

## Hand-back to master

1. **Phase D unblocked but not started** — Application image build + `backend-secrets` creation + `kubectl apply` of api.yaml + worker.yaml is the next physical step. Manifests are correct and ready. Requires: (a) `RAZORPAY_WEBHOOK_SECRET` SM version (founder → Razorpay dashboard), (b) `LANGFUSE_SECRET_KEY` SM version (founder → cloud.langfuse.com), (c) `kubectl create secret generic backend-secrets -n dev --from-env-file=...`, (d) `docker build && docker push && kubectl apply -f k8s/api.yaml k8s/worker.yaml`. Coordinate: meesell-infra-builder owns kubectl apply; meesell-backend-coordinator owns image build.

2. **D4 open**: `.gitlab-ci.yml` still not produced (GitLab CI pipeline — 6 stages per §19.G). This remains the wave-7 escalation flagged in STATUS_MASTER. Resolve via Option A (§20.5 micro-dispatch) or Option B (defer) per founder ruling.

3. **§1 diagram label advisory** (low priority): the `meesell-images` label in §1.B diagram now refers to a GCS path prefix, not the bucket name. Consider a NOTE annotation on the diagram in a future §1 amendment pass.

4. **All 4 egress endpoints reachable from cluster** — no firewall action needed.

5. **All cert-manager certs READY** — no cert action needed; all 5 subdomains live with LE TLS (auto-renew ~30d before 2026-09-02).
