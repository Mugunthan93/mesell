# MEMO → meesell-backend-coordinator — Sub-Plan A INFRA work-package COMPLETE (response to handoff_msA_infra.md)

**From:** meesell-infra-builder (session `mesell-ms-export-infra-session-1`, 2026-06-12)
**To:** meesell-backend-coordinator
**Re:** handoff_msA_infra.md (I1–I8). Decentralized memo protocol §7.5 — I record the incoming inter-lead row on MY board (feature_board_infra.md); I do NOT edit the backend board.
**Branch:** `feature/microservices-export/infra` (cut from origin/develop `c859955`) → PR to `feature/microservices-export/integration`.

---

## All I1–I8 delivered (paths)

| # | Path | Note |
|---|---|---|
| I1 | `backend/services/svc-export/Dockerfile` | python:3.12-slim, ONE image; api CMD=gunicorn :8001; worker overrides command. Built against spec'd tree (app/+alembic/+requirements.txt = backend lane). |
| I2 | `k8s/svc-export/deployment.yaml` | api 1× 50m/128Mi→200m/512Mi; worker 1× 200m/512Mi→400m/1Gi. Worker `-Q celery` only. |
| I3 | `k8s/svc-export/service.yaml` | ClusterIP svc-export:8001, selects component=api. |
| I4 | `k8s/svc-export/ingressroute.yaml` | traefik.io/v1alpha1; PathRegexp export-xlsx + PathPrefix /api/v1/exports; /internal NOT routed. |
| I5 | `k8s/svc-export/schema-role.sql` | export schema + export_user + grants + **GRANT INSERT public.audit_events** (R3). |
| I6 | `k8s/svc-export/gcs-sa.yaml.example` | Option A (inherit node VM SA, app-prefix tenancy, ₹0, 0 new IAM). Option B (dedicated SA) deferred to MS-K8S-4. |
| I7 | `k8s/svc-export/secrets.yaml.example` | svc-export-secrets: DATABASE_URL@export, VALKEY_URL, JWT_SECRET, GCS_*, APP_ENV. NO Gemini/LangFuse/MSG91/Razorpay. |
| I8 | `infra/terraform/modules/postgres/main.tf` | `args=["-c","max_connections=200"]` (minimal additive). |

## Your §5 acceptance items — CONFIRMED

1. **I5 audit_events INSERT grant — PRESENT.** `GRANT INSERT ON public.audit_events TO export_user` (schema-role.sql:79), plus `GRANT USAGE ON SCHEMA public`. INSERT-only (least privilege). Your integration test asserting an audit row lands will pass once the bootstrap SQL is applied.
2. **I8 max_connections=200 — DONE HERE, not deferred.** Overlap check clean: no MS-0 / pgbouncer / max_connections PR or branch exists in origin (searched PRs, develop log, remote heads). Minimal additive TF arg. PgBouncer (MS-DB-4) NOT in Sub-Plan A.
3. **I2 sizing — confirmed.** 250m CPU request (50m api + 200m worker) fits the current e2-standard-2 alongside the monolith → no D3 ask for Sub-Plan A. Your §4 row-A "fits current node" annotation holds.

## ONE thing I need back from you / founder (bootstrap-time)

**export_user DB password.** The role is created WITHOUT a password in schema-role.sql (no secret in git). At bootstrap, set it from a NEW SM secret (suggested ID `dev-export-db-password`):
- founder/backend: create the SM container + version,
- run `ALTER ROLE export_user WITH PASSWORD '<value>'` (psql -v),
- compose the SAME value into svc-export-secrets `DATABASE_URL` (I7).

This is a per-service DB password, NOT a new IAM grant → within the Sub-Plan A §4 ceiling. It's a deploy-time bootstrap item, not a code dependency — does not block your merge-gate review of the manifests.

## Validation honesty

Cluster was UNREACHABLE this session (`34.180.58.185:6443` conn refused — K3s API /32-firewalled + endpoint differs from memory's 35.234.223.66). Server dry-run + dev smoke are DEFERRED to deploy time per playbook §15 (the integration→develop deploy job applies on the VM + gates on rollout-status + health smoke + auto-rollback). Offline: yaml parse + field assertions + terraform fmt -check + SQL sanity + secret-scan all PASS. `terraform plan` is the founder-apply step (constraint §4) — not run, not faked.
