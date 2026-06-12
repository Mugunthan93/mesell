# Runbook — PgBouncer cutover + Postgres max_connections=200 (MS-0 / D5 step 1)

**Owner:** `meesell-infra-builder`
**Scope:** DEV namespace only. ₹0 new spend. Current hardware (`e2-standard-2`).
**Source of truth:** `docs/plans/infra/microservices_infra_plan.md` §3.3 (MS-DB-3 + MS-DB-4),
`docs/plans/microservices_migration/MASTER_PLAN.md` D5.
**Status:** AUTHORED + validated, NOT applied. Application is founder-gated (see PR
`[FOUNDER GATE — DO NOT MERGE] MS-0`).

This runbook covers two coupled changes:
1. **Postgres `max_connections` 100 → 200** (TF-managed StatefulSet, `module.postgres_dev`).
2. **PgBouncer** in transaction-pool mode (`k8s/pgbouncer.yaml` + `pgbouncer-userlist` Secret).

PgBouncer is the **D5 prerequisite** — it MUST be live and validated before ANY service
cutover flip points its `DATABASE_URL` at `pgbouncer:6432`. The DATABASE_URL flip itself is
a **separate founder-gated step** (§ "Cutover step 3" below) and is NOT performed by MS-0.

---

## 0. Pre-flight

```bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
export KUBECONFIG=~/.kube/meesell-dev.yaml
gcloud auth list   # confirm vaishnaviramoorthy@gmail.com is active (*)
gcloud config get-value project   # project-1f5cbf72-2820-4cdb-949
kubectl get nodes  # meesell-dev-master Ready  (K3s API reachable = founder IP in firewall /32)
kubectl -n dev exec postgres-0 -- psql -U meesell -d meesell -tAc "SHOW max_connections;"  # expect 100 (pre)
```

Snapshot before the destructive-ish step (StatefulSet update restarts postgres-0):
```bash
gcloud compute instances list > /tmp/meesell-pre-ms0-state.txt
kubectl -n dev get statefulset postgres -o yaml > /tmp/meesell-pre-ms0-postgres-sts.yaml
```

---

## 1. Apply order (exact)

### Step 1 — Postgres max_connections=200 (TF)

This is an **in-place StatefulSet update** → it triggers a rolling restart of `postgres-0`
(brief DB downtime, seconds; PVC is `prevent_destroy`, data is safe).

```bash
export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token --account=vaishnaviramoorthy@gmail.com)
cd infra/terraform   # (or use -chdir)
terraform plan -target=module.postgres_dev \
  -var-file=environments/dev.tfvars \
  -var "postgres_password=$(cat ~/.meesell-secrets/dev-postgres-password)" \
  -var "valkey_password=$(cat ~/.meesell-secrets/dev-valkey-password)" \
  -out=.tflogs/ms0-postgres.tfplan
# EXPECT: Plan: 0 to add, 1 to change, 0 to destroy
#   ~ container.args += ["-c","max_connections=200"]
#   ~ resources.limits.memory  "1Gi" -> "1536Mi"
terraform apply .tflogs/ms0-postgres.tfplan
```

Wait for the pod to come back, then VERIFY:
```bash
kubectl -n dev rollout status statefulset/postgres --timeout=120s
kubectl -n dev exec postgres-0 -- pg_isready -U meesell -d meesell   # accepting connections
kubectl -n dev exec postgres-0 -- psql -U meesell -d meesell -tAc "SHOW max_connections;"  # EXPECT 200
```

### Step 2 — PgBouncer manifests

**[MANDATORY GATE — playbook §15 step 3]** server-side dry-run first:
```bash
# 2a. Populate the userlist Secret (procedure in k8s/pgbouncer-userlist.secret.yaml.example).
#     The md5 hash is computed from the LIVE postgres password; never committed.
PGPW="$(kubectl -n dev get secret postgres-credentials -o jsonpath='{.data.password}' | base64 -d)"
HASH="md5$(printf '%s%s' "$PGPW" "meesell" | md5sum | cut -d' ' -f1)"
printf '"meesell" "%s"\n' "$HASH" > /tmp/userlist.txt
kubectl -n dev create secret generic pgbouncer-userlist \
  --from-file=userlist.txt=/tmp/userlist.txt --dry-run=client -o yaml | kubectl apply -f -
shred -u /tmp/userlist.txt 2>/dev/null || rm -f /tmp/userlist.txt

# 2b. MANDATORY server dry-run on the workload manifests.
kubectl -n dev apply --dry-run=server -f k8s/pgbouncer.yaml   # must be clean
# (validated clean during authoring on 2026-06-12; re-run before apply)

# 2c. Apply.
kubectl -n dev apply -f k8s/pgbouncer.yaml
kubectl -n dev rollout status deployment/pgbouncer --timeout=120s
```

VERIFY PgBouncer is pooling against Postgres:
```bash
kubectl -n dev get pods -l app=pgbouncer    # 1/1 Running
# SHOW POOLS via the pgbouncer admin DB (auth as meesell over 127.0.0.1:6432):
kubectl -n dev exec deploy/pgbouncer -- \
  psql "postgresql://meesell:$PGPW@127.0.0.1:6432/pgbouncer" -c "SHOW POOLS;"
# EXPECT a row for database `meesell`, pool_mode `transaction`, cl_active/sv_idle columns.
unset PGPW HASH
```

Smoke (proves a real query flows app → pgbouncer → postgres):
```bash
kubectl -n dev exec deploy/pgbouncer -- \
  psql "postgresql://meesell:$(kubectl -n dev get secret postgres-credentials -o jsonpath='{.data.password}' | base64 -d)@127.0.0.1:6432/meesell" \
  -c "SELECT 1;"   # EXPECT: 1 row, value 1
```

### Step 3 — DATABASE_URL flip (FOUNDER-GATED — NOT part of MS-0)

The monolith / each extracted service flips its `DATABASE_URL` host:port from
`postgres.dev.svc.cluster.local:5432` to `pgbouncer.dev.svc.cluster.local:6432`. This is a
per-service founder-gated cutover, NOT done here. **Prerequisite for the flip:** the backend
asyncpg/SQLAlchemy compatibility changes (R-MS-8 — see
`.claude/agent-memory/meesell-infra-builder/handoff_d5_pgbouncer_backend.md` and the backend
inter-lead request) MUST be merged first. Transaction-pool mode breaks prepared statements
that span transactions; without the backend changes the flip causes runtime errors.

When the founder authorizes a flip:
```bash
# backend-secrets carries DATABASE_URL; update host:port 5432 -> pgbouncer:6432.
# (compose with urllib.parse.quote on the password — base64 passwords contain +/@, see MEMORY)
# Then rolling-restart the consumer Deployment so it re-reads the Secret.
kubectl -n dev rollout restart deployment/api deployment/worker
```

---

## 2. Verification queries (reference)

| What | Command |
|---|---|
| Postgres ceiling | `kubectl -n dev exec postgres-0 -- psql -U meesell -d meesell -tAc "SHOW max_connections;"` → `200` |
| Postgres live conns | `kubectl -n dev exec postgres-0 -- psql -U meesell -d meesell -tAc "SELECT count(*) FROM pg_stat_activity;"` |
| PgBouncer pools | `... psql ".../pgbouncer" -c "SHOW POOLS;"` |
| PgBouncer clients | `... psql ".../pgbouncer" -c "SHOW CLIENTS;"` |
| End-to-end | `... psql ".../meesell" -c "SELECT 1;"` via :6432 |

---

## 3. Rollback

### Rollback PgBouncer (Step 2)
PgBouncer is additive — nothing routes through it until the founder-gated DATABASE_URL flip.
So removing it is safe as long as no service has flipped:
```bash
kubectl -n dev delete -f k8s/pgbouncer.yaml
kubectl -n dev delete secret pgbouncer-userlist
```
If a service HAD flipped to :6432, first point its `DATABASE_URL` back at
`postgres.dev.svc.cluster.local:5432` and `rollout restart` it, THEN delete pgbouncer.

### Rollback max_connections (Step 1) — playbook §5 (Postgres) discipline
```bash
# Revert the TF module change (git revert the MS-0 merge commit on the branch), then:
export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token --account=vaishnaviramoorthy@gmail.com)
terraform -chdir=infra/terraform plan -target=module.postgres_dev \
  -var-file=environments/dev.tfvars \
  -var "postgres_password=$(cat ~/.meesell-secrets/dev-postgres-password)" \
  -var "valkey_password=$(cat ~/.meesell-secrets/dev-valkey-password)" \
  -out=.tflogs/ms0-rollback.tfplan
# EXPECT: args -> removed, memory limit 1536Mi -> 1Gi. Plan: 0 add, 1 change, 0 destroy.
terraform apply .tflogs/ms0-rollback.tfplan
kubectl -n dev rollout status statefulset/postgres --timeout=120s
kubectl -n dev exec postgres-0 -- psql -U meesell -d meesell -tAc "SHOW max_connections;"  # back to 100
```
**Note:** lowering `max_connections` while > the new ceiling are open would refuse the change
at boot. At dev baseline (~10 conns) this is never an issue. Postgres restarts on the change.

### If postgres-0 won't come back (either direction)
Playbook §12.1 (Pod won't start) + §12.4 (DB connection refused). The PVC is
`prevent_destroy`; data is intact. `kubectl -n dev describe pod postgres-0` + check the
`-c max_connections=N` arg didn't exceed what the pod's `shared_buffers` / memory allows
(1.5Gi limit is sized for 200 conns; do not raise N further without re-sizing memory).

---

## 4. Cost

₹0/month. No new VM, no new disk, no new billable GCP resource. PgBouncer is one tiny pod
(25m CPU req / 32Mi mem req) on the existing node; the postgres memory LIMIT rose but the
REQUEST is unchanged (no new reservation, no scheduler pressure). The e2-standard-2 node has
ample memory headroom (live: 44% of 8GB requested). CPU — the binding constraint — is
untouched (postgres CPU unchanged; pgbouncer adds 25m request against ~350m free).
