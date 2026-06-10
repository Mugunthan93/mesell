# Session Dispatch: Infra — Microservices
**Session name:** `mesell-infra-microservices-infra-session-1`
**Project:** `/Users/mugunthansrinivasan/Project/mesell`
**Status:** BLOCKED — requires Session 1 complete; can run parallel with Session 2

---

## Prerequisite
Session 1 (repo-management) must be COMPLETE.
Session 2 (microservices) Sub-Plan A should be in progress or complete —
infra session can run in parallel with Session 2 on non-overlapping work.

---

## Mission
Review and ratify the Infra Microservices Plan. Lock the VM sizing, gateway
routing, and DB isolation decisions. Execute the infrastructure preparation
that unblocks the first microservice extraction.

---

## Read first (in this order)
1. `docs/plans/infra/microservices_infra_plan.md` — the plan to ratify
2. `docs/INFRASTRUCTURE_ARCHITECTURE.md` — current live state
3. `docs/DEVOPS_ARCHITECTURE.md` — current CI/CD pipeline
4. `k8s/` — all current manifests
5. `.claude/agent-memory/meesell-infra-builder/MEMORY.md`

---

## Open decisions — get founder answer in this session

1. **Dev VM resize: e2-standard-2 → e2-standard-4**
   - 8 microservices cannot fit in 2 vCPU. Non-negotiable for migration.
   - Cost: ~₹3,500/month vs ~₹1,750/month
   - Confirm to proceed OR select `e2-standard-4` vs `e2-standard-8`

2. **MS-GW-1: API gateway routing strategy**
   - Option A: Path-prefix routing (`api.mesell.xyz/catalog/`, `/iam/`, etc.)
     — 1 TLS cert, 1 Traefik IngressRoute, no DNS changes
   - Option B: Host-based subdomain routing (`catalog.mesell.xyz`, `iam.mesell.xyz`)
     — separate TLS cert per service, DNS changes required
   - Recommendation: Option A — less cert-manager churn, no DNS sprawl for dev

3. **MS-DB-1: Connection pool approach**
   - Current: max_connections=100, 2 services × 15 pool = 60 (safe)
   - After migration: 8 services × 15 pool = 120 (OVER limit)
   - Option A: PgBouncer transaction-pool (recommended)
   - Option B: Reduce per-service pool to 10 → 80 total (tight but fits)
   - Option C: Raise max_connections to 200 (Postgres tuning)
   - Recommendation: Option A (PgBouncer) — scales beyond V1.5 without re-tuning

---

## What to produce

### Step 1 — Ratify the plan
- Change STATUS in `docs/plans/infra/microservices_infra_plan.md` → APPROVED
- Record the 3 decisions

### Step 2 — Create the feature branch
- Create `feature/microservices-infra-prep/infra` from `develop`

### Step 3 — Execute MS-ENV-1: Dev VM resize
Dispatch `meesell-infra-builder` to:
- Terraform plan for `e2-standard-4` upgrade to `meesell-dev`
- Get founder approval on the plan output
- Apply and verify K8s nodes healthy post-resize

### Step 4 — Execute MS-DB-1: PgBouncer
Dispatch `meesell-infra-builder` to:
- Add PgBouncer deployment to K8s (`k8s/pgbouncer.yaml`)
- Configure transaction-pool mode, pool size per service
- Wire Terraform module
- Smoke test: existing api pods connect through PgBouncer without error

### Step 5 — Execute MS-K8S-1: Gateway IngressRoute template
Dispatch `meesell-infra-builder` to:
- Create Traefik IngressRoute template for path-prefix gateway
- Test with current single api service (no regression)
- Document per-service IngressRoute pattern for sub-plan execution

### Step 6 — Commit + PR
Commit on `feature/microservices-infra-prep/infra`
Open PR to `feature/microservices-infra-prep`
Update `docs/status/feature_board_infra.md`
Update `docs/INFRASTRUCTURE_ARCHITECTURE.md` with all changes

---

## Acceptance gate — session is DONE when
- [ ] MASTER_PLAN.md status = APPROVED
- [ ] Dev VM resized to e2-standard-4, K8s nodes healthy
- [ ] PgBouncer running, existing services connect through it
- [ ] Gateway IngressRoute template committed and tested
- [ ] INFRASTRUCTURE_ARCHITECTURE.md updated
- [ ] PR open against `feature/microservices-infra-prep`

---

## Constraints
- Apply infra changes via Terraform — no manual `kubectl apply` for new resources
- Do NOT touch `backend/`, `frontend/` application code
- INFRASTRUCTURE_ARCHITECTURE.md must be updated in the same commit as any live change
- Validate `terraform plan` output before applying (founder approves the plan output)
