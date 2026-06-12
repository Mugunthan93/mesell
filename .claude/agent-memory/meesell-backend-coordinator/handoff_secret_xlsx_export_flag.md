# handoff_secret_xlsx_export_flag.md — infra inter-lead memo

**From:** meesell-backend-coordinator (mesell-xlsx-export-backend-session-1, STEP 3)
**To:** meesell-infra-builder
**Opened:** 2026-06-12
**Status:** OPEN
**Board row:** feature_board_backend.md → Inter-lead requests open → row "xlsx-export".

## Request

Wire the **5th V1 feature flag** `FEATURE_XLSX_EXPORT_ENABLED` into k8s ConfigMaps:

| Namespace | Value | Rationale |
|---|---|---|
| dev | `true` | Feature exercised in dev. POST `/products/{id}/export-xlsx` reachable. |
| staging | `false` | **D2 staging gate.** Stays false until: (1) the 15 golden round-trip fixtures pass x3 consecutive develop-HEAD CI runs (gate-5 `golden_roundtrip`), AND (2) a manual Meesho supplier-panel upload of a generated XLSX is accepted by a human. |

## Behavior contract (so infra knows what the flag gates)

- When `FEATURE_XLSX_EXPORT_ENABLED=false`: **POST** `/products/{id}/export-xlsx` returns **404** `{"detail": "XLSX export is disabled in this environment"}`.
- **GET** `/exports/{id}` is **NOT gated** (R1 founder ruling) — in-flight export polls must keep working regardless of the flag. The guard lives only in the POST handler.
- Default in `shared/config.py` is `bool = True` (so absence of the env var = enabled; staging must explicitly set `false`).

## Coordination note (important)

`meesell-infra-builder` has an **in-flight session** wiring the OTHER 4 V1 feature flags
(`FEATURE_SMART_PICKER_ENABLED`, `FEATURE_CATALOG_FORM_ENABLED`, `FEATURE_AI_AUTOFILL_ENABLED`,
`FEATURE_IMAGE_PRECHECK_ENABLED`) on branch `feature/image-precheck-infra`.

This 5th flag should **join that PR** (preferred — keeps all 5 V1 feature flags ConfigMap-consistent
across dev/staging in one landing) **or** land as an immediate follow-up PR. Do not let the 5 flags
drift into partial coverage.

## Source of truth

- Flag declaration: `backend/app/shared/config.py` section 3.2 block (`FEATURE_XLSX_EXPORT_ENABLED`).
- D2 staging gate: `docs/plans/features/xlsx-export/FEATURE_PLAN.md` D2.
- Merge-gate verdict: STATUS_BACKEND.md 2026-06-12 block + the founder-gate PR body.

## Resolution protocol

Per the decentralized memo protocol: read this memo, add your own incoming-side row to
`feature_board_infra` (your board — I do NOT write it), wire the ConfigMap, then mark this board's
row RESOLVED with the landing PR number. 48h SLA before I escalate to founder via STATUS_MASTER.
