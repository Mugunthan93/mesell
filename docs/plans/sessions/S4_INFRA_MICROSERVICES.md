# Session Dispatch: Infra — Microservices
**Session name:** `mesell-infra-microservices-infra-session-1`
**Project:** `/Users/mugunthansrinivasan/Project/mesell`
**Status:** IN PROGRESS — ratification package returned to founder 2026-06-10. S1 complete, Model C ACTIVE (2026-06-10), pilot-hardened (PILOT_REPORT.md). Can run parallel with S2. The infra DRAFT plan (`docs/plans/infra/microservices_infra_plan.md`) is NOT flipped to APPROVED by this session — the founder rules on it. This session produced the ratification package (appended below) for the master session to put to the founder.

---

## Prerequisite
Session 1 (repo-management) is COMPLETE. Model C is ACTIVE (2026-06-10).
Session 2 (microservices) Sub-Plan A should be in progress or complete —
infra session can run in parallel with Session 2 on non-overlapping work.

---

## Mission
Review and ratify the Infra Microservices Plan (`docs/plans/infra/microservices_infra_plan.md`)
— **this ratification is genuinely still pending and IS this session's gate.**
Lock the VM sizing, gateway routing, and DB isolation decisions. Execute the
infrastructure preparation that unblocks the first microservice extraction.

**Context — the MS MASTER_PLAN is already LOCKED** (post-V1 roadmap, 2026-06-10);
only the *infra* sub-plan ratification remains. Impact analysis found the current
free **e2-standard-2 CANNOT host the extracted 8-service topology** (≈1600m+ CPU
required vs ~950m the free tier affords). The VM sizing decision in this session
**must therefore account for ≥ e2-standard-4** (≈₹2.5–6k/month depending on tier).
Execution is **post-V1**.

---

## Read first (in this order)
1. `docs/plans/infra/microservices_infra_plan.md` — the plan to ratify
2. `docs/plans/repo_management/PILOT_REPORT.md` — Model C pilot findings (F1–F3)
3. `docs/plans/repo_management/MASTER_PLAN.md` §1.2/§6.5/§9.5 as amended v1.1 (F1–F3)
4. `docs/INFRASTRUCTURE_ARCHITECTURE.md` — current live state
5. `docs/DEVOPS_ARCHITECTURE.md` — current CI/CD pipeline
6. `k8s/` — all current manifests
7. `.claude/agent-memory/meesell-infra-builder/MEMORY.md`

---

## Open decisions — get founder answer in this session

1. **Dev VM resize: e2-standard-2 → ≥ e2-standard-4**
   - Confirmed by impact analysis: the extracted 8-service topology needs
     ≈1600m+ CPU; the current free e2-standard-2 affords only ~950m. The
     existing topology cannot fit in 2 vCPU. **Non-negotiable for migration.**
   - Cost: ~₹2.5–6k/month (vs ~₹1,750/month today), tier-dependent.
   - Confirm to proceed OR select `e2-standard-4` vs `e2-standard-8`.

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
- **F1 (pilot ruling):** the integration branch for this feature is
  `feature/microservices-infra-prep/integration` — open the group PR against the
  integration branch, NOT a bare `feature/microservices-infra-prep`.

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
Open PR to `feature/microservices-infra-prep/integration` (F1)
Update `docs/status/feature_board_infra.md`
Update `docs/INFRASTRUCTURE_ARCHITECTURE.md` with all changes

---

## Acceptance gate — session is DONE when
- [ ] `microservices_infra_plan.md` status = APPROVED (this session's ratification gate)
- [ ] Dev VM resized to ≥ e2-standard-4, K8s nodes healthy
- [ ] PgBouncer running, existing services connect through it
- [ ] Gateway IngressRoute template committed and tested
- [ ] INFRASTRUCTURE_ARCHITECTURE.md updated
- [ ] PR open against `feature/microservices-infra-prep/integration` (F1)

---

## Constraints
- Apply infra changes via Terraform — no manual `kubectl apply` for new resources
- Do NOT touch `backend/`, `frontend/` application code
- INFRASTRUCTURE_ARCHITECTURE.md must be updated in the same commit as any live change
- Validate `terraform plan` output before applying (founder approves the plan output)

---

# RATIFICATION PACKAGE — returned to founder 2026-06-10

**Produced by** `meesell-infra-builder` (session `mesell-infra-microservices-infra-session-1`).
**Posture override (this session):** `docs/plans/infra/microservices_infra_plan.md` stays **DRAFT**. This session does NOT flip it to APPROVED. It packages the open decisions for founder ruling (mirror of how S5/MF was resolved via a confirmation doc, not a self-ratification). ZERO cluster / Terraform / manifest mutations were made. Step 3/4/5 of the dispatch (VM resize, PgBouncer deploy, IngressRoute) are EXECUTION steps — deferred until the founder rules + execution is post-V1.

**Inputs read:** the DRAFT infra plan (full), `docs/plans/microservices_migration/MASTER_PLAN.md` (LOCKED v1.1), `docs/plans/infra/GATE4_CONFIRMATION.md` (my MF Gate-4 headroom math), `docs/INFRASTRUCTURE_ARCHITECTURE.md`, `docs/DEVOPS_ARCHITECTURE.md`, own MEMORY.md.

> **Execution timing:** all decisions below take effect at **microservices-extraction time (post-V1-launch)**, per MS MASTER_PLAN Revision 1.0. None of this spends money or changes infra today.

---

## Decision 1 — Dev VM sizing: `e2-standard-2` → `≥ e2-standard-4`

| | |
|---|---|
| **Question** | Can the extracted 8-service topology run on the current free `e2-standard-2` (2 vCPU / 8 GB)? If not, which machine type? |
| **Options** | (A) Keep `e2-standard-2`, run each service at 1 api + 1 worker with shrunk CPU requests. (B) Upgrade dev VM to `e2-standard-4` (4 vCPU / 16 GB). (C) `e2-standard-8` (8 vCPU / 32 GB). |
| **Evidence** | DRAFT §6.3 sizing matrix sums app-pod CPU **requests** to **~1750m (api+gateway) + ~950m (workers) ≈ 2400m–2700m at the documented per-service requests**, before infra pods. Infra pods (postgres 200m, valkey 100m, studio 100m, traefik ~100m, cert-manager 3×50m, K3s system ~150m) add **~700m**. Total **≈ 2450m–3400m of CPU requests vs 2000m allocatable** on `e2-standard-2`. Cross-checked against `GATE4_CONFIRMATION.md` Answer 3: the dev node has **2000m allocatable, 1650m already requested by the CURRENT monolith (api 2×200m + worker 2×250m + infra), ~350m free** — and the scheduler gates on **requests, not usage** (live usage is only 190m). The current node cannot even fit the §6.3 matrix at 1 replica each. The MS MASTER_PLAN Revision 1.0 already records the same conclusion verbatim: *"full extraction forces VM upgrade e2-standard-2 → ≥ e2-standard-4 (~₹2.5–6k/mo)."* |
| **Cost** | `e2-standard-4` ≈ **₹5,200/mo** (vs ~₹2,600/mo today) — **a new spend of ~₹2,600/mo, FAR above the ₹500/mo founder-sign-off gate.** `e2-standard-8` ≈ ₹10,400/mo. Within the `meesell-dev-budget` ₹25,000 cap and GCP free-credit window, but explicit founder cost sign-off is mandatory. |
| **RECOMMENDATION** | **(B) `e2-standard-4`.** Non-negotiable for the migration — `e2-standard-2` is infeasible (DRAFT §6.1 conclusion + R-MS-2 "Certain/High"). `e2-standard-4` (4 vCPU = 4000m allocatable) fits the §6.3 matrix (~2450m–3400m) with headroom AND matches the future staging spec, so dev/staging stay symmetric. Reject (A): CPU-budget surgery to fit 24 pods on 2 vCPU is fragile and loses api-layer HA. Reject (C) for V1.5: `e2-standard-8` is over-provisioned until measured load proves the need; revisit at prod sizing (MS-ENV-3). **Do NOT correct the DRAFT's §6.1 Option (A)-recommendation in-plan** (that's the founder's call) — but flag it: §6.1 currently recommends "(A) for V1 dev" which CONTRADICTS its own §6.3 math and the LOCKED MASTER_PLAN. See Consistency Delta #1. |

## Decision 2 — MS-GW-1: API gateway routing strategy

| | |
|---|---|
| **Question** | Path-prefix routing under one host, or host-based subdomains per service? |
| **Options** | (A) Path-prefix: `api.mesell.xyz/auth/*`, `/catalog/*`, … — 1 TLS cert, 1 Traefik IngressRoute, no DNS changes. (B) Host-based: `auth.api.mesell.xyz`, … — separate cert per service, 8 new DNS records + 8 ACME renewals. (C) Custom FastAPI gateway pod (BFF) — full code control, +1 deploy unit. |
| **Evidence** | DRAFT §2.4 recommends (A). Cross-check: the LOCKED MASTER_PLAN §2.C **independently arrived at the SAME answer** — Traefik IngressRoute, path-prefix on the existing `api.mesell.xyz`, JWT validation stays in-service (NOT at gateway). The MASTER_PLAN even fixes the exact prefix table (`/api/v1/auth/*` → iam-svc, etc.). The existing `api.mesell.xyz` LE cert already covers the single host (no cert-manager churn). Frontend keeps one `API_BASE_URL`; CORS config does not fan out. Note a prefix-shape delta: DRAFT uses short prefixes (`/auth/`, `/catalog/`); MASTER_PLAN uses full API paths (`/api/v1/auth/`, `/api/v1/products/`). The MASTER_PLAN paths are authoritative — they match the 28 already-wired routes. |
| **RECOMMENDATION** | **(A) Traefik IngressRoute, path-prefix** — using the **MASTER_PLAN §2.C prefix table** (full `/api/v1/<resource>/*` paths), not the DRAFT's abbreviated `/auth/` form. Zero cert/DNS churn, one origin for clients, and it concurs with the already-LOCKED backend roadmap. Defer (B) host-based to V2 only if team boundaries demand per-service cert/DNS isolation. Keep (C) custom-pod on the menu ONLY if cross-service orchestration / BFF response-shaping becomes a real V1.5 need (DRAFT §2.4 lists the triggers). **DRAFT §2.4 should adopt the MASTER_PLAN's full-path prefix table to eliminate the divergence** — see Consistency Delta #2. |

## Decision 3 — MS-DB-1: Connection pool approach

| | |
|---|---|
| **Question** | 8 services × per-service pools will blow `max_connections=100`. How do we keep within budget? |
| **Options** | (A) PgBouncer transaction-pool mode (multiplex N app conns → ~20 backend conns). (B) Right-size per-service pools to ~10 → ~80–127 total. (C) Raise Postgres `max_connections` to 200 (~+500MB pod memory). |
| **Evidence** | DRAFT §3.3: current monolith = 60 + 6 baseline = 66 < 100 (safe). Naive 8-service worst case = **360 connections** — 3.6× over budget. Even the DRAFT's right-sized matrix (Option B) lands at **127 + 6 = 133, still over 100**. The MASTER_PLAN §2.E confirms shared-Postgres-with-per-service-schema and per-service pools sized by traffic (catalog largest, dashboard smallest) but does **not** itself pick the multiplexing mechanism — it leaves the pool mechanism to this infra plan. So MS-DB-1 is genuinely an infra-owned decision, no MASTER_PLAN conflict. PgBouncer transaction-pool caveat (DRAFT §3.3): forbids cross-transaction prepared statements; asyncpg needs `executemany_mode='values_only'`, `pool_pre_ping=False`, and statement-cache disabled — must be smoke-tested per service (R-MS-8). |
| **RECOMMENDATION** | **Phased: (B)+(C) first, then (A) before any traffic-bearing cutover.** Ship MS-DB-3 (per-service pool right-sizing in code + `max_connections=200`) first — low risk, immediately unblocks the early extractions (export, dashboard, image, pricing — all low-pool services). Then ship MS-DB-4 (PgBouncer transaction-pool) as **mandatory before staging→prod traffic cutover**, because (B)+(C) alone is a tight 133-vs-200 fit that does not scale past V1.5 and `max_connections=200` costs ~+500MB on the postgres pod (acceptable on `e2-standard-4`, not on `e2-standard-2`). This matches the DRAFT §3.3 "recommended path" exactly. The pure-(A)-now framing in the S4 dispatch open-decision list is fine as the end-state, but the safe execution sequence is B+C → A. |

---

## Consistency check — DRAFT infra plan vs LOCKED MS MASTER_PLAN v1.1 + Option-C federation

**Verdict: no blocking contradictions. The DRAFT is architecturally consistent with the LOCKED MASTER_PLAN on every load-bearing decision (shared-Postgres-schema-per-service, shared-Valkey-DB-allocation, Traefik path-prefix gateway, JWT-validated-in-service, Strangler-Fig order). Four non-blocking deltas to reconcile when the DRAFT is revised post-ratification:**

- **Delta #1 (must fix) — VM sizing self-contradiction in DRAFT §6.1.** §6.1 recommends "(A) `e2-standard-2` for V1 dev" while its OWN §6.3 math and risk R-MS-2 ("Certain/High") prove `e2-standard-2` cannot host the topology, and the LOCKED MASTER_PLAN Rev 1.0 records "≥ e2-standard-4" as forced. The §6.1 recommendation line is stale relative to the locked conclusion. **Fix on revision:** flip §6.1 recommendation to (B) `e2-standard-4`, consistent with Decision 1 above.

- **Delta #2 (should fix) — gateway prefix shape.** DRAFT §2.4 uses abbreviated prefixes (`api.mesell.xyz/auth/*`); MASTER_PLAN §2.C uses full API paths (`/api/v1/auth/*`) matching the 28 wired routes. Adopt the MASTER_PLAN full-path table in the DRAFT to avoid a routing-config divergence at execution.

- **Delta #3 (note only) — service naming.** DRAFT uses `svc-auth … svc-billing` (8 services incl. a `svc-billing` for Razorpay). MASTER_PLAN uses `iam / customer / category / catalog / image / pricing / dashboard / export` (8 modules; Razorpay webhook lives in `iam`, plan_guard is a `core/` concern enforced per-resource-owner, NOT a separate billing service). **The MASTER_PLAN module set is authoritative** (it's LOCKED and maps to the real `backend/app/modules/<module>/` layout). The DRAFT's `svc-billing`/`svc-quality` slugs do not exist as backend modules. On revision, the DRAFT should re-key its 8 services to the MASTER_PLAN module names so K8s resource names, image streams, and CI matrix entries line up with the actual extraction order (export → dashboard → image → pricing → customer → category → iam → catalog).

- **Delta #4 (note only) — namespace strategy.** DRAFT §2.1 recommends single `dev` namespace for all services; MASTER_PLAN §2.D / §5.D assume the same single-namespace-per-env model (per-service schema + Secret, not per-service namespace). Consistent — no change.

**Does Option-C federation hosting change the MS math? — NO, but it HELPS.** Per `GATE4_CONFIRMATION.md` (C-RES-2), the 6 module-federation REMOTES ship as static bundles in **GCS + Cloud CDN, OUTSIDE K3s (0 in-cluster CPU)**; only the shell stays in-cluster (a ~0-net-CPU swap for the retiring `frontend` Deployment). This means the frontend migration does **not** consume any of the dev node's CPU headroom that the MS topology needs — the MS sizing math (Decision 1) is computed on backend service pods alone and is **unaffected** by the federation cutover. Net effect: Option-C is favorable — it keeps the frontend off the CPU budget entirely, so the `e2-standard-4` upgrade is sized purely for the 8 backend services + infra pods, with no frontend contention. **No MS-math revision needed; flag for the record that the two migrations are CPU-orthogonal under Option-C.**

---

## What this session did NOT do (and why)
- Did NOT flip the DRAFT to APPROVED (founder's call — posture override for this session).
- Did NOT resize the VM, deploy PgBouncer, or author the IngressRoute (execution steps; gated on founder ruling + post-V1 timing; ZERO mutations mandated).
- Did NOT touch `docs/plans/module_federation/` (sibling S3) or `docs/plans/microservices_migration/` (sibling S2) — read-only cross-reference only.
- Surface written this session: `docs/plans/infra/` (none — DRAFT untouched) + this S4 doc only.

## Founder actions requested
1. Rule on Decision 1 (VM `e2-standard-4` — **cost sign-off > ₹500/mo required**), Decision 2 (gateway = path-prefix, MASTER_PLAN paths), Decision 3 (DB pools = B+C then A).
2. On approval, authorize the master session to flip `microservices_infra_plan.md` STATUS → APPROVED **with Deltas #1–#3 reconciled** in the same edit.
3. Confirm execution timing = post-V1-launch (per MASTER_PLAN Rev 1.0) — no infra spend until then.
