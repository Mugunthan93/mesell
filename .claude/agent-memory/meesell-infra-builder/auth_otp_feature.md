---
name: auth-otp-feature
description: auth-otp Feature 1 — infra builder scope, secrets status, K8s surfaces, runbook
metadata:
  type: project
---

Feature: auth-otp (Feature 1 of 9 V1 features)
Status: PLAN READY → IN REVIEW (PR #3 open on feature/auth-otp/planning)
Plan document: docs/plans/features/auth-otp/FEATURE_PLAN.md
Date seeded: 2026-06-10

## Your role in this feature

You are the standalone infra lead. You:
- Are dispatched directly by the founder (no backend/frontend coordinator above you for infra)
- Own `docs/status/feature_board_infra.md` — update it at session start and session close
- Self-review your own PR (then founder does final gate)
- Can run in PHASE A (parallel with backend Phase A — no deps on backend or frontend code)
- Use Template G in FEATURE_PLAN.md for your dispatch prompt

## Branch you own

`feature/auth-otp/infra` (to be created from `feature/auth-otp` after plan is LOCKED)

Do NOT create branches until FEATURE_PLAN.md PR #3 merges to develop and the tracker shows LOCKED.

## Secrets status (confirmed 2026-06-09)

ALL 4 required secrets for auth-otp are LIVE in GCP Secret Manager:
- `refresh-token-pepper` ✅ VERSION 1 LIVE
- `razorpay-webhook-secret` ✅ VERSION 1 LIVE (2026-06-09)
- `msg91-auth-key` ✅ VERSION 1 LIVE ⚠️ IP whitelist: verify 122.164.85.51 is whitelisted in MSG91 dashboard before marking gate-2 green
- `jwt-secret` ✅ VERSION 1 LIVE

NO new secrets need to be created for this feature. Your work is env var wiring + K8s manifest updates only.

## Exact files you need to modify

Read `docs/INFRASTRUCTURE_PLAYBOOK.md` FIRST to find the actual live manifest paths.
The `.claude/CLAUDE.md` k8s/ tree (postgres.yaml, valkey.yaml, ingress.yaml) is DOCUMENTATION-ONLY — not the live manifests.

What you need to add to the live K8s deployment manifests:

**dev namespace:**
- `ACCESS_TOKEN_TTL_SECONDS=30` (integer, not string)
- `REFRESH_TOKEN_TTL_SECONDS=120` (integer, not string)
- `CORS_ALLOWED_ORIGINS=["https://dev.mesell.xyz"]`
- `CORS_ALLOW_CREDENTIALS=true`
- `REFRESH_TOKEN_PEPPER` → Secret Manager ref `refresh-token-pepper`
- `RAZORPAY_WEBHOOK_SECRET` → Secret Manager ref `razorpay-webhook-secret`

**staging namespace:**
- `ACCESS_TOKEN_TTL_SECONDS=60`
- `REFRESH_TOKEN_TTL_SECONDS=300`
- Same CORS + secret refs as dev

## New file you must create

`docs/runbooks/auth-secret-rotation.md` — documents:
1. How to rotate REFRESH_TOKEN_PEPPER without invalidating live sessions (versioned rotation, not hard cutover)
2. Emergency revocation path: mass DEL of `cache:refresh:*` keys in Valkey DB 0 (all users logged out — document blast radius)

## Mandatory pre-apply check

`kubectl apply --dry-run=server -f <manifest>` for BOTH namespaces — must be CLEAN before any live apply.

## TTL values (from BACKEND_ARCHITECTURE.md §5.D — authoritative)

| Env | ACCESS_TOKEN_TTL_SECONDS | REFRESH_TOKEN_TTL_SECONDS |
|-----|--------------------------|---------------------------|
| dev | 30 | 120 |
| staging | 60 | 300 |
| prod | 900 | 604800 |

## What to update when your session completes

Update this file with:
- Actual K8s manifest paths you modified (from INFRASTRUCTURE_PLAYBOOK.md)
- dry-run result for dev: CLEAN | ERROR
- dry-run result for staging: CLEAN | ERROR
- MSG91 IP whitelist: confirmed working | needs update for 122.164.85.51
- `docs/runbooks/auth-secret-rotation.md`: created | blocked
- PR # for feature/auth-otp/infra → feature/auth-otp

---

## SESSION COMPLETE — mesell-auth-otp-infra-session-1 (2026-06-11)

Status: COMPLETE. Infra group PR #45 squash-merged to feature/auth-otp/integration (SHA d2b734e). Integration→develop PR #46 OPEN (founder gate — NOT merged by me).

### Actual files modified/created
- `k8s/config.yaml` (MODIFY) — dev ConfigMap: ACCESS_TOKEN_TTL_SECONDS 900→30, REFRESH_TOKEN_TTL_SECONDS 604800→120, CORS_ALLOWED_ORIGINS → https://dev.mesell.xyz. (TTL/CORS keys pre-existed from §20 2026-06-08; this corrected VALUES to dev.)
- `k8s/overlays/staging/kustomization.yaml` + `k8s/overlays/staging/config.yaml` (NEW) — self-contained staging ConfigMap: ns=staging, APP_ENV=staging, ACCESS=60, REFRESH=300, CORS=https://staging.mesell.xyz.
- `docs/runbooks/auth-secret-rotation.md` (NEW) — §1 dev/staging natural-expiry, §2 prod dual-pepper grace window (R5), §3 emergency revocation, §4 pre-flight, §5 follow-ups.
- board + STATUS_INFRA updated.

### Re-audit verdict
Memo's "exact env vars to add" were ALREADY in config.yaml/secrets.yaml.example. Real gaps were (1) dev config held PROD values, (2) no staging surface, (3) no runbook. So this feature's infra work was a VALUE-correction + overlay-creation + doc, NOT new env-var keys.

### dry-run result
- dev base: kubectl kustomize k8s → clean (after a minimal base kustomization was tried then REMOVED — see KUSTOMIZE GOTCHA in MEMORY.md). Validated via `kubectl kustomize` + python yaml.safe_load_all.
- staging overlay: kubectl kustomize k8s/overlays/staging → clean exit 0, correct patched values.
- `kubectl apply --dry-run=server`: NOT POSSIBLE — cluster unreachable (34.180.58.185:6443 refused). Founder-flag F3: re-run at deploy time.

### MSG91 IP whitelist
NOT verified (cluster down, no OTP send). Carry-forward to S1.5/S3.1 dev smoke gate — verify 122.164.85.51 (or current founder IP) whitelisted before backend gate-2 green.

### Secrets verified live (values never printed)
refresh-token-pepper, razorpay-webhook-secret, msg91-auth-key, jwt-secret — each 1 ENABLED version.

### PR
feature/auth-otp/infra → feature/auth-otp/integration: PR #45 — MERGED (squash d2b734e).
feature/auth-otp/integration → develop: PR #46 — OPEN (founder gate).
