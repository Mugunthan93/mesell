# HANDOFF -> meesell-infra-builder — Sub-Plan C (`image` extraction) INFRA work-package

**From:** meesell-backend-coordinator (session `mesell-ms-image-backend-session-1`, 2026-06-13, MS-C PHASE 2 — EXECUTION)
**To:** meesell-infra-builder (standalone agent — executes its own lane directly; no specialists)
**Memo protocol:** §7.5 decentralized. I add the outgoing Inter-lead request row to MY board; infra lead reads this memo + adds the incoming row to ITS board. I never edit the infra board.
**SUPERSEDES** the Phase-1 (2026-06-12) handoff draft — the §0.10 row is now RULED (Option B), no longer decision-dependent.
**GATE:** SATISFIED — MS-A founder gate merged; recipe + SHIM_CONTRACT on develop; §0.10 RULED Option B (PR #197 / `d4aa572`). Infra lane is UNBLOCKED, parallel with MS-B.

**CUT POINT:** integration branch is STOOD UP at `feature/microservices-image/integration` = origin/develop tip **`d4aa572`**. Cut the infra branch from it: `git worktree add <path> -b feature/microservices-image/infra feature/microservices-image/integration`.

---

## 0. Scope
The svc-image extraction's INFRA surfaces. Backend specialists own `backend/services/svc-image/app/**`; infra lead owns everything below, committed on `feature/microservices-image/infra` (cut from `…/integration`), infra-lead-reviewed, merged into integration alongside the backend group PRs. Dev namespace ONLY.

---

## 1. Infra deliverables (all dev-namespace, current hardware UNLESS §3 D3 trigger fires)

| # | Surface | Spec | Source authority |
|---|---|---|---|
| I1 | `backend/services/svc-image/Dockerfile` | FROM python:3.12-slim; install svc-image `requirements.txt`; one image serves api + worker (entrypoint differs). Carries Pillow (~30MB) + google-cloud-storage + ai_ops (gemini SDK + langfuse). **rembg DEFERRED (RULED recommended, §3.G — zero call sites in backend/app)** → image is meaningfully SMALLER; NO rembg/onnxruntime/u2net ONNX layer. If founder/AI-lead reverse the defer at Phase 2, +rembg+onnxruntime ~300MB + u2net ~170MB (pre-bake the model). Build against the DEFERRED posture unless told otherwise. | SUB_PLAN_0C §3.G, §7 |
| I2 | `k8s/svc-image/deployment.yaml` | **api 1 replica:** req 50m CPU / 128Mi, lim 200m/512Mi (routes + signed-URL gen). **DEDICATED Celery worker 1 replica:** req 500m CPU / 1Gi, lim 1000m / 2Gi (Pillow decode + ai_ops watermark). svc-image worker is the HEAVIEST container in the early waves. Numbers PROVISIONAL — validate against real precheck memory profile at Phase 2. rembg-deferred keeps the worker working-set bounded (no ONNX). | SUB_PLAN_0C §7; MS-A I2 precedent |
| I3 | `k8s/svc-image/service.yaml` | ClusterIP `svc-image:8001`. | MASTER_PLAN §2.C |
| I4 | Traefik IngressRoute | Route `/api/v1/products/{id}/images*` -> `svc-image:8001`. `/internal/products/{product_id}/images` NOT Traefik-exposed (cluster-DNS only — export-svc calls it via K3s DNS). | MASTER_PLAN §2.C, D4 |
| I5 | Postgres schema + role | `CREATE SCHEMA image; GRANT USAGE ON SCHEMA image TO image_user; GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA image TO image_user;` PLUS **`GRANT INSERT ON public.audit_events TO image_user`** (cross-schema audit write — `image.precheck.completed` worker audit, tasks.py). **§0.10 — RULED OPTION B (founder 2026-06-13, PR #197): GRANT NO `products` READ ACCESS to `image_user`.** The transitional `GRANT SELECT ON public.products` (former Option A) is DISCARDED — do NOT grant it. The repository scopes by `product_id` alone, post the catalog `assert_product_ownership` HTTP shim (no cross-schema SQL read). The ONLY cross-schema grant is the audit INSERT above. | MASTER_PLAN §2.D / §5.B; SUB_PLAN_0C §0.10 RULED; recipe §7A |
| I6 | GCS service account | SA with `storage.objectAdmin` scoped to the `meesell-images/{user_id}/...` prefix (upload + signed-URL + worker download). ADC from pod SA (gcs.py reads instance metadata — no JSON env). | MASTER_PLAN §2.E; gcs.py |
| I7 | Secret injection | svc-image pod needs: `DATABASE_URL`(@schema image), `VALKEY_URL`, `JWT_SECRET`(shared — local JWT verify D7/A2), `GCS_*`, **`GEMINI_API_KEY`**, **`LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY`/`LANGFUSE_HOST`**, **`AI_OPS_*`** (daily-cap config), `APP_ENV`. image IS AI-consuming (UNLIKE export) -> GEMINI+LANGFUSE REQUIRED. **NOT** MSG91/RAZORPAY. `langfuse-secret-key` already populated per §22 audit. | SUB_PLAN_0C §3 (trimmed Settings) / §4; MASTER_PLAN §5.D |
| I8 | Valkey budget-brake access | svc-image's vendored ai_ops reads/writes SHARED Valkey **DB 0** budget keys `ai:cost:daily:{date}`, `ai:cost:pending:{date}`, `ai:budget:reservation:{id}` — UN-prefixed (global ₹500 cap per D6). svc-image's `VALKEY_URL` MUST point at the SAME Valkey instance as the monolith/other AI services. DB 0 = budget+sessions+OTP+rate-limits; DB 1 broker; DB 2 results; DB 3 cache. | MASTER_PLAN §2.E, §5.C; SUB_PLAN_0C §4 |
| I9 | Celery queue wiring | svc-image worker consumes a DEDICATED queue **`svc-image`** (broker Valkey DB 1, results DB 2, keys prefixed `svc-image:`). **NOTE (live-state change):** PR #143 MERGED to develop — the MONOLITH celery_app now routes `image.precheck` -> queue **`image-tasks`** (NOT default). svc-image's dedicated queue is `svc-image` regardless (its OWN celery_app declares it). The monolith `image-tasks` queue is monolith-only and is dropped at cutover. One-off Valkey backfill of in-flight `image.precheck` state at cutover (tasks row-level idempotent — re-run safe). | SUB_PLAN_0C §0.9, §3; celery_app.py:126-127 @ d4aa572 |
| I10 | D5 / MS-DB-3 pool right-size | Per-service `pool_size` matrix + `max_connections=200`. Should already be in place from MS-0/MS-A; confirm svc-image's small api pool + worker NullPool fit under the 200 budget alongside monolith + svc-export + svc-dashboard. | infra plan §3.2, MS-DB-3 |

---

## 2. D5 / PgBouncer sequencing
- MS-DB-3 (pool right-size + max_connections=200) ships BEFORE any service moves — should already be done. Confirm it covers svc-image.
- MS-DB-4 (PgBouncer transaction-pool) = mandatory before traffic-bearing PROD cutover ONLY. MS-C is dev-only/zero-traffic -> NOT a MS-C blocker.
- PgBouncer async caveat (when MS-DB-4 lands): `pool_pre_ping=False` + `executemany_mode='values_only'` — infra-lane concern, not MS-C.

---

## 3. Hardware / VM — POSSIBLE D3 TRIGGER at MS-2 deploy (FLAG LOUDLY)
svc-image is the HEAVIEST container in the early waves (Pillow + ai_ops watermark; rembg DEFERRED so NO ONNX working set). At MS-2 the node hosts monolith + svc-export (MS-1) + svc-dashboard (MS-2 tiny) + svc-image (MS-2, HEAVY) — the most likely early-wave node-fill point.
- **D3 (e2-standard-4, ~₹2,600/mo) is PLAN-pre-approved ONLY.** The SPEND gets an EXPLICIT FRESH FOUNDER ASK at the moment services outgrow the node — NOT at execution start.
- **ACTION:** run capacity math (monolith + svc-export + svc-dashboard + svc-image worker at I2 sizing) BEFORE the MS-2 deploy. If it overflows e2-standard-2, STOP and flag to founder for the D3 upgrade — do NOT silently provision. rembg-deferred (already the posture) is the cheapest mitigation.

---

## 4. Constraints
- dev namespace ONLY. NO staging/prod manifests in MS-C.
- NO terraform beyond dev-scope. New node pool / VM upgrade / IAM beyond the one image SA -> flag to founder, do not execute.
- `/internal/*` routes NOT Traefik-exposed (absence of IngressRoute = isolation; NetworkPolicy is V2).
- Infra branch = `feature/microservices-image/infra`, infra-lead-reviewed, squash into integration. Founder gates integration->develop (NOT me, NOT infra lead).
- Parallel-lane with MS-B (dashboard) infra: svc-image manifests in `k8s/svc-image/`; shared k8s files additive/union-merge.

---

## 5. What I (backend lead) need back from infra (backend merge-gate depends on)
- I5 confirmed: `image_user` HAS `INSERT ON public.audit_events` (else `image.precheck.completed` worker audit fails; the integration test asserting an audit row fails).
- I5 §0.10 confirmed: `image_user` has **NO `products` read grant** (Option B — no cross-schema read exists; the transitional grant was DISCARDED). If a `products` SELECT grant appears anywhere in the role setup, that is a regression — remove it.
- I8 confirmed: svc-image's VALKEY_URL hits the SHARED instance so the global ₹500 budget brake stays coordinated (an integration test asserts cross-service `ai:cost:daily:{date}` coherence).
- I2/§3 confirmed: svc-image worker DEPLOYED at the heavy sizing AND the node still fits (so I can confirm "fits node, no D3 ask") — OR the founder D3 ask was raised+approved before deploy.
- I7 confirmed: GEMINI+LANGFUSE secrets injected (image is AI-consuming).

SLA: 48h before escalating to founder via STATUS_MASTER blockers (§7.5). I open the Inter-lead request row on my board at Phase 2 dispatch.
