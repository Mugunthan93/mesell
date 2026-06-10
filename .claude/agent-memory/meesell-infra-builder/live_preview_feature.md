---
name: live-preview-feature
description: live-preview Feature 6 — infra builder role, K8s env var wiring, gated rollout runbook
metadata:
  type: project
---

# Live Preview (Feature 6) — Infra Builder Brief

**Status:** PLAN READY (FEATURE_PLAN.md awaiting master consolidation 2026-06-10)
**FEATURE_PLAN.md:** `docs/plans/features/live-preview/FEATURE_PLAN.md` (~1100 lines)
**Your role:** Standalone — you are not led by another coordinator. You self-review the infra group PR, then founder gate.
**Branch you own:** `feature/live-preview/infra` (cut by master from `feature/live-preview` integration branch)

## What you build

Per Template F in FEATURE_PLAN.md §Dispatch templates:

1. K8s deployment env vars across 3 namespaces:
   - **Dev:** `FEATURE_LIVE_PREVIEW_ENABLED="true"` (API pod) + `NG_APP_FEATURE_LIVE_PREVIEW_ENABLED=true` (frontend build)
   - **Staging:** `FEATURE_LIVE_PREVIEW_ENABLED="false"` initially + `NG_APP_...=false`. Flips to `true` AFTER founder visual-diff approval on the integration PR.
   - **Prod:** `FEATURE_LIVE_PREVIEW_ENABLED="false"` initially + `NG_APP_...=false`. Flips to `true` AFTER ≥7 days clean on staging.

2. `docs/runbooks/live-preview-rollout.md` (NEW) — documents the 3-stage rollout and the rollback procedure.

3. NO new secrets. NO new buckets. NO new ingress rules. Cost impact: ₹0/month.

## The gated rollout posture (D3)

The feature flag IS the kill-switch. If Meesho redesigns their feed-card mid-V1 making our clone stale (risk #1 in the risk register), you flip `FEATURE_LIVE_PREVIEW_ENABLED=false` across all envs in ~5 minutes:
- Edit the K8s manifest
- `kubectl rollout restart deployment/api-{namespace}`
- Rebuild + deploy frontend with `=false`
- Users see "Preview unavailable" placeholder instead of broken render

This is the safety net for the qualitative visual-diff approach.

## Self-review checks before opening PR

The 6-check review protocol is in FEATURE_PLAN.md §Review + iteration protocol. Top items:

1. `kubectl apply --dry-run=server` clean for ALL 3 namespaces.
2. Env values are STRINGS `"true"` / `"false"` (NOT integers, NOT unquoted booleans). K8s requires string env values; Pydantic Settings coerces to bool on load.
3. Frontend build args set for all 3 envs.
4. `live-preview-rollout.md` covers all 3 stages (dev → staging-approval → prod-after-soak) AND the rollback procedure.
5. Cost impact stated in PR body as ₹0.
6. No secrets touched.

## Read FIRST

`docs/INFRASTRUCTURE_PLAYBOOK.md` — live state is SSOT; do NOT blindly apply CLAUDE.md k8s/ tree. The playbook is more current than the snapshot.

## After feature merges to develop

Update `docs/status/feature_board_infra.md` row: live-preview → MERGED.

If Meesho redesigns post-launch:
- Set flag to `false` across all envs (5-min rollback per runbook)
- Notify backend + frontend coords of the rollback so they can dispatch ui-styler for re-clone
- After re-clone PR merges, flip flag back to `true` (re-runs the staging-approval gate)
