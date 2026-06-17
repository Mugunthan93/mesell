# handoff_secret_flag_parity_flags.md — infra inter-lead request

**From:** meesell-backend-coordinator
**To:** meesell-infra-builder
**Session:** mesell-flag-parity-sweep-session-1 (STEP 3 merge-gate)
**Date:** 2026-06-12
**Status:** OPEN

## Request

The flag-parity sweep wires the final 3 V1 backend feature flags into `backend/app/shared/config.py` (landed on `chore/flag-parity`, FOUNDER GATE PR OPEN->develop). After that PR merges to develop, inject the 3 new flags into the k8s ConfigMaps (same pattern as the 5 already-wired flags):

| Flag | dev ConfigMap | staging ConfigMap |
|---|---|---|
| `FEATURE_PRICE_CALCULATOR_ENABLED` | `true` | `false` |
| `FEATURE_TRACKING_DASHBOARD_ENABLED` | `true` | `false` |
| `FEATURE_LIVE_PREVIEW_ENABLED` | `false` | `false` |

## Notes

- **live-preview ships DARK.** `FEATURE_LIVE_PREVIEW_ENABLED` is the ONLY V1 flag whose code default is `False` (gated rollout per FEATURE_PLAN D3). It stays `false` in BOTH dev and staging. The founder flips the **dev** ConfigMap to `true` only when the preview frontend wires up. Do NOT default it true.
- price-calculator + tracking-dashboard follow the standard D2 posture: dev=true, staging=false until staging soak passes.
- These 3 should JOIN the in-flight feature-flag ConfigMap PR (infra was wiring the other flags on a feature-flag-infra branch) or land as an immediate follow-up, so ALL V1 flags are ConfigMap-consistent across dev/staging.
- Config-only; no new secret, no new infra primitive. The flags are runtime `Settings` fields read from the existing config object.

## Cross-ref

- Sibling memo for the 5th flag (xlsx): `handoff_secret_xlsx_export_flag.md`.
- Audit memo: `audit_flag_parity_sweep.md`.
- Board: `feature_board_backend.md` Inter-lead requests open (this request's outgoing row).
