# Sub-Session Prompt: §20 Deployment Topology V1
# Wave 7 of 10 — CONSTRUCTION
# Specialist agent: meesell-infra-builder
# Renames session to: meesell-backend-construction-20-deployment-1

---

## How to use this file

1. Open a NEW Claude Code session.
2. `cd /Users/mugunthansrinivasan/Project/mesell/`
3. Copy block below between START / END markers.
4. Paste as first message. Wait for "Ready to begin §20 construction" then master's "go".

---

## ⬇ START SUB-SESSION PROMPT — COPY EVERYTHING BELOW THIS LINE ⬇

You are the meesell-infra-builder agent operating in a dedicated construction sub-session for MeeSell §20 (Deployment Topology V1).

§20 is the **only construction section that touches `k8s/`**. ALL 3 pending Secret Manager containers (`refresh-token-pepper`, `razorpay-webhook-secret`, `langfuse-secret-key`) get POPULATED during this dispatch.

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: SUB-SESSION (construction). Master = parent Claude window owning BACKEND_ARCHITECTURE.md.
- Project: MeeSell only. Root: `/Users/mugunthansrinivasan/Project/mesell/`
- Section under construction: §20 Deployment Topology V1 — K3s YAML manifests + env-var injection + Secret Manager wiring + ingress + CORS
- Specialist agent: meesell-infra-builder (solo per §20 lock — INFRA track only touches `k8s/`, `terraform/`, VM config)
- Attempt: #1
- Sub-session naming: `/rename meesell-backend-construction-20-deployment-1`

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

MeeSell only. Stop and report if outside `/Users/mugunthansrinivasan/Project/mesell/`.

═══════════════════════════════════════════════════════════════
REQUIRED READING (in order)
═══════════════════════════════════════════════════════════════

1. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §20 — A through K (esp. §20.B pod inventory V1 = 4 pod types: FastAPI 2 replicas + Celery 2 replicas + PostgreSQL + Valkey; §20.C env-var injection via `envFrom: secretRef:`; §20.D ingress + TLS + CORS — Traefik + cert-manager on `studio.mesell.xyz`; §20.E health checks; §20.F scaling posture; §20.G per-pod resource requests/limits sketch; §20.H K3s manifest sketches application side; §20.I V1.5 extraction prep posture; §20.J ownership boundaries).

2. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §1.B (topology), §4.G (CORS — Allow-Credentials true on /api/v1/auth/*; never-`*` Allow-Origin), §5.D (env vars catalog — all 11 grouped tables), §6A.F (LangFuse — `langfuse-secret-key` Secret Manager ref).

3. `/Users/mugunthansrinivasan/Project/mesell/docs/MVP_ARCHITECTURE.md` §10 (deployment), §10.8 (GCS bucket layout `meesell-images/` + `meesell-exports/`).

4. `/Users/mugunthansrinivasan/Project/mesell/CLAUDE.md` (Architecture section; namespace mapping `dev`/`staging`/`prod`).

5. `.claude/agents/meesell-infra-builder.md` (own spec).

6. `.claude/agent-memory/meesell-infra-builder/MEMORY.md` (prior session memory — GCP project ID, VM IPs, K3s state).

7. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_BACKEND.md` (confirm Wave 1-7 §18 + §19 CONSTRUCTED).

8. `/Users/mugunthansrinivasan/Project/mesell/k8s/` current state — confirm baseline manifests from CLAUDE.md project structure (`namespace.yaml`, `secrets.yaml.example`, `config.yaml`, `postgres.yaml`, `valkey.yaml`, `api.yaml`, `worker.yaml`, `frontend.yaml`, `ingress.yaml`, `backup-cronjob.yaml`).

═══════════════════════════════════════════════════════════════
CONSTRUCTION SCOPE
═══════════════════════════════════════════════════════════════

Files to author/modify in `k8s/`:

```
k8s/
├── namespace.yaml               # 3 namespaces: dev, staging, prod
├── secrets.yaml.example         # template (NEVER commit actual secrets.yaml)
├── config.yaml                  # ConfigMap with non-secret env vars per §5.D 11 tables
├── postgres.yaml                # PostgreSQL 16 self-hosted (trimmed Supabase image)
├── valkey.yaml                  # Valkey 8 single instance; 4 logical DBs (0/1/2/3)
├── api.yaml                     # FastAPI Deployment 2 replicas + Service; envFrom: secretRef
├── worker.yaml                  # Celery Worker Deployment 2 replicas; same image different CMD
├── frontend.yaml                # Angular static (Phase 1 V1)
├── ingress.yaml                 # Traefik + cert-manager on studio.mesell.xyz; CORS per §4.G
└── backup-cronjob.yaml          # Daily Postgres backup to GCS
```

Plus: provision GCP Secret Manager containers:
- `refresh-token-pepper` (populated this dispatch — random 64-byte token via `openssl rand -hex 32`)
- `razorpay-webhook-secret` (populated this dispatch — Razorpay webhook secret from dashboard)
- `langfuse-secret-key` (populated this dispatch — LangFuse cloud account key)

Plus: GCS buckets:
- `meesell-images` (region asia-south1; lifecycle rules per `MVP_ARCH §10.8`)
- `meesell-exports` (same)

Locked invariants per §20:
- FastAPI 2 replicas per §20.B.
- Celery 2 replicas per §20.B.
- 3 namespaces: `dev`, `staging`, `prod`.
- Valkey DB allocation: DB 0 sessions/OTP/rate limits/refresh allowlist; DB 1 Celery broker; DB 2 Celery result backend; DB 3 cache.
- Postgres at alembic head `f31c75438e61` with 13 tables.
- GCS buckets: `meesell-images/{user_id}/{product_id}/{idx}.jpg` and `meesell-exports/{user_id}/{export_id}.xlsx`.
- Ingress on `studio.mesell.xyz` with Traefik + cert-manager (TLS auto-renewal).
- CORS per §4.G: `Allow-Credentials: true` on `/api/v1/auth/*`; `Allow-Origin` explicit (NEVER `*`); cookie `Domain=.mesell.xyz`.
- Per-pod resource requests/limits per §20.G sketch.
- Health checks per §20.E (readiness + liveness on `/health`).
- Secret injection via `envFrom: secretRef:` pattern per §20.C (NOT inline `valueFrom: secretKeyRef:` for individual fields).
- Egress: Gemini API + MSG91 API + Razorpay API + LangFuse API reachable from FastAPI pod.

Construction protocol:

1. **Tests first**:
   - K3s manifest validity: `kubectl apply --dry-run=client -f k8s/` succeeds.
   - Settings boot test: pod starts and loads all required env vars from secretRef (no SystemExit).
   - Health check responds 200 OK on `/health` after pod start.
   - Ingress TLS cert renewal verified (cert-manager).
   - CORS preflight on `/api/v1/auth/otp/send` returns expected headers (Allow-Credentials, Allow-Origin explicit).
   - Secret Manager population: all 3 secrets exist + accessible by the pod's service account.

2. **Implementation** per §20.H K3s manifest sketches.

3. **Acceptance**: smoke deploy to `dev` namespace; verify all 4 pod types come up healthy; verify route `GET /health` returns 200 through ingress; verify boot smoke test against the deployed instance.

═══════════════════════════════════════════════════════════════
HARD RULES
═══════════════════════════════════════════════════════════════

- DO NOT commit `secrets.yaml` (only `secrets.yaml.example` template; actual values via Secret Manager).
- DO NOT set CORS `Allow-Origin: *` (locked at §4.G).
- DO NOT use inline `valueFrom: secretKeyRef:` for individual secret fields — use `envFrom: secretRef:` per §20.C.
- DO NOT change Valkey DB allocation (DB 0/1/2/3 locked).
- DO NOT change FastAPI replicas to 1 (locked at 2 per §20.B).
- DO NOT change Celery replicas to 1 (locked at 2 per §20.B).
- DO NOT add a 4th pod type in V1 (4 only: FastAPI, Celery, Postgres, Valkey).
- DO NOT enable GoTrue / Realtime / Storage subsystems on the trimmed Supabase image (Decision 15 lock).
- DO NOT touch `STATUS_MASTER.md`.
- DO NOT touch any project outside MeeSell.
- DO NOT dispatch non-`meesell-*` agents.

═══════════════════════════════════════════════════════════════
SPECIALIST DISPATCH PERMISSION
═══════════════════════════════════════════════════════════════

You ARE permitted: `meesell-infra-builder` (solo per §20 lock — INFRA track is the only track touching `k8s/`).

You ARE NOT permitted: any other dispatch.

═══════════════════════════════════════════════════════════════
PENDING SECRETS & LATENT BUGS (PER §20)
═══════════════════════════════════════════════════════════════

**ALL 3 PENDING SECRETS POPULATED DURING THIS DISPATCH:**

1. `refresh-token-pepper` — provision via `openssl rand -hex 32` (64-character hex string). Store in GCP Secret Manager. Reference from K3s manifests via `envFrom: secretRef:` per §20.C. Consumed by `iam/service.py` (§7) for HMAC allowlist key construction.

2. `razorpay-webhook-secret` — copy from Razorpay dashboard (Webhooks settings). Store in GCP Secret Manager. Same injection pattern. Consumed by `iam/service.py` for `POST /webhooks/razorpay` HMAC signature verify.

3. `langfuse-secret-key` — copy from LangFuse cloud account (Settings). Store in GCP Secret Manager. Same injection pattern. Consumed by `ai_ops/client.py` for trace egress.

After population, verify FastAPI + Celery pods successfully consume all 3 via boot smoke test against `dev` namespace.

None — no latent bugs to resolve in §20.

═══════════════════════════════════════════════════════════════
ACCEPTANCE CRITERIA
═══════════════════════════════════════════════════════════════

1. `k8s/` manifests for all 10 files updated/authored per CLAUDE.md project structure + §20.H sketches.
2. `kubectl apply --dry-run=client -f k8s/` succeeds.
3. All 3 secrets populated in GCP Secret Manager + accessible.
4. GCS buckets `meesell-images` + `meesell-exports` provisioned in asia-south1 with lifecycle rules.
5. Traefik ingress on `studio.mesell.xyz` with TLS via cert-manager.
6. CORS per §4.G: `Allow-Credentials: true` on `/api/v1/auth/*`; explicit `Allow-Origin`; cookie `Domain=.mesell.xyz`.
7. FastAPI 2 replicas + Celery 2 replicas deployed to `dev` namespace; all healthy.
8. `GET /health` returns 200 through ingress.
9. Boot smoke test PASS against deployed `dev` instance.
10. Postgres connection pool budget: 2 FastAPI × (10+5) + 2 Celery × similar < 100 (verified via `pg_stat_activity` query).

Plus universal: ruff clean (no application code changes expected; YAML lint clean); STATUS_BACKEND.md UPDATE block.

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

1. Update `.claude/agent-memory/meesell-infra-builder/MEMORY.md` with deployment outcome + the 3 populated secret container names + GCS bucket names + ingress hostname.
2. Append to `docs/status/STATUS_BACKEND.md`:
   ```
   === UPDATE: <YYYY-MM-DD> — §20 deployment CONSTRUCTED ===
   Files modified: k8s/{10 manifest files}
   Secrets populated: refresh-token-pepper, razorpay-webhook-secret, langfuse-secret-key (all in GCP Secret Manager)
   GCS buckets: meesell-images, meesell-exports (asia-south1)
   Ingress: studio.mesell.xyz (Traefik + cert-manager)
   Tests added: deployment smoke + CORS preflight + TLS cert + pod health
   Decisions made: <list>
   Hand-offs: §22 acceptance (the final wave consumes the deployed state to run the V1 GO/NO-GO checklist)
   Acceptance: PASS/FAIL
   =========
   ```
3. Report back to master under 400 words.

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS
═══════════════════════════════════════════════════════════════

- GCP Secret Manager API not enabled on project (escalate — needs gcloud command).
- Razorpay webhook secret not available (escalate — coordinate with founder for dashboard access).
- LangFuse cloud account not yet created (escalate — V1.5 vs V1 ruling).
- K3s cluster resource exhaustion on dev VM (escalate — request VM upgrade).
- TLS cert issuance failure on studio.mesell.xyz (escalate — DNS misconfiguration).

═══════════════════════════════════════════════════════════════
END OF SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. `/rename meesell-backend-construction-20-deployment-1`
2. Read REQUIRED READING.
3. Confirm Wave 1-7 §18 + §19 CONSTRUCTED.
4. Report "Context loaded. Ready to begin §20 construction." to master.

WAIT for master's "go".

## ⬆ END SUB-SESSION PROMPT — COPY EVERYTHING ABOVE THIS LINE ⬆

---

## Master session reference (NOT part of the paste)

- **Wave:** 7 of 10
- **Sequential dependency:** Wave 1-7 §18 + §19 CONSTRUCTED.
- **Parallel-safe?:** No — Wave 7 sequential. §20 is the LAST construction sub-session before audits begin.
- **Expected duration estimate:** ~8-12 hours (10 manifest files + 3 secret provisions + GCS buckets + ingress + deployment smoke).
- **Acceptance verification by master:** (1) `gcloud secrets list --project=project-1f5cbf72-2820-4cdb-949` shows all 3 secret containers; (2) `kubectl get pods -n dev` shows FastAPI + Celery + Postgres + Valkey all Running; (3) `curl https://studio.mesell.xyz/health` returns 200; (4) `gsutil ls -b gs://meesell-images gs://meesell-exports` shows both buckets; (5) STATUS_BACKEND.md UPDATE block present. AFTER §20 PASSES, master proceeds to Wave 8 verification audits.
