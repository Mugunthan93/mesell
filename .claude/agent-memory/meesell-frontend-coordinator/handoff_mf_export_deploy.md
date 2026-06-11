# Handoff → meesell-infra-builder: mfe-export second-remote deploy (D19)

**From:** meesell-frontend-coordinator (Frontend Lead)
**To:** meesell-infra-builder
**Date opened:** 2026-06-11
**Feature:** mfe-export (MF Sub-Plan 02, R6)
**SLA:** 48h before escalation
**Priority:** LOW — D13 hosting DEFERRED to SP04-05 era (founder ruling, parallel-wave). This memo
RECORDS the second-remote surface so it is captured when hosting actually lands; it does NOT open a
new active hosting request (the SP01 request handoff_mf_pricing_deploy.md already owns the GCS/CDN
surface, and one infra hosting inter-lead row is already OPEN from SP01).

## What landed (frontend side, dev-validated)
- `apps/mfe-export/` Native Federation remote built GREEN (3.43s) → `dist/mfe-export/browser/remoteEntry.json`
  + ESM chunks (ExportComponent-*.js). Group PR #60 squash-merged `565d754` to feature/mfe-export/integration;
  founder-gate PR (integration→develop) OPEN.
- Manifest now holds TWO remotes: `{mfe-pricing:4201, mfe-export:4202}` (localhost dev URLs). The two-remote
  manifest resolves both remoteEntry.json → 200 simultaneously (proven by curl).

## What infra needs to wire WHEN hosting lands (SP04-05 era, per D13 deferral)
1. **Second GCS prefix (D19 / GATE4 C-RES-2):** upload mfe-export's `remoteEntry.json` + chunks to
   `gs://meesell-frontend/{env}/mfe-export/{version}/` — same bucket + Cloud CDN + `remotes.mesell.xyz`
   host + GCP-managed cert (C-ROUTE-1) the SP01 pilot stood up. No new infra primitive — just a new prefix.
2. **cloudbuild.remote.yaml matrix fan-out (C-CI-1):** confirm the `dorny/paths-filter` matrix treats
   `apps/mfe-export/**` as its OWN build unit — a change under apps/mfe-export/ rebuilds ONLY mfe-export,
   NOT the shell or mfe-pricing. (SP01 added apps/mfe-pricing/** as the first per-remote unit; mfe-export is
   the second. `shared/**` / `libs/**` changes must still rebuild ALL remotes.)
3. **Per-env manifest URL templating:** the prod manifest entry for mfe-export must point at
   `https://remotes.mesell.xyz/{env}/mfe-export/{version}/remoteEntry.json` (version-pinned, NO `latest` —
   D44 per SP07). The shell build ships the manifest verbatim into dist/frontend/browser/.

## Not blocking the frontend merge
Dev-validation uses localhost-served remotes, so the founder-gate PR does NOT block on the GCS surface.
This is the same posture as the pilot.

## Cross-ref
- handoff_mf_pricing_deploy.md (SP01 — the active hosting request this memo extends)
- handoff_mf_ci_prep.md (C-CI-1 matrix)
- docs/plans/infra/GATE4_CONFIRMATION.md (C-RES-2 / C-ROUTE-1 / C-CI-1 — infra-owned)
- docs/plans/module_federation/SUB_PLAN_02_export_extraction.md §D19
