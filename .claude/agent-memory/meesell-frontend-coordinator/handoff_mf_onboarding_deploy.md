# Handoff → meesell-infra-builder — mfe-onboarding remote hosting (D24)

**From:** meesell-frontend-coordinator (Frontend Lead) · **Date:** 2026-06-11 · **SLA:** 48h
**Re:** MF Sub-Plan 03 — third Native Federation remote `mfe-onboarding` (after mfe-pricing SP01, mfe-export SP02).

## Status
- SP03 frontend MERGED to integration (PR #67, e2035330); founder-gate PR #68 (integration→develop) OPEN.
- **D13 hosting is DEFERRED to the SP04-05 era by founder ruling** (this remote's hosting criteria are
  "locally-proven" class — localhost-served + headless-curl validated). This memo RECORDS the prefix + matrix
  fan-out for when the GCS/CDN surface is stood up; it is NOT a new active hosting request. (Do NOT open another
  infra hosting ticket for SP03 — the SP01 D13 row + SP02's already cover the pattern.)

## What infra owns when hosting lights (per GATE4_CONFIRMATION.md Option C, infra-owned)
- **GCS prefix:** `gs://meesell-frontend/{env}/mfe-onboarding/{version}/` (browser/ subdir holds remoteEntry.json +
  chunks). Mirrors mfe-pricing/mfe-export prefixes.
- **Manifest URL (per-env):** `https://remotes.mesell.xyz/{env}/mfe-onboarding/{version}/remoteEntry.json`.
  Dev manifest currently `http://localhost:4202/remoteEntry.json` (port 4202; pricing 4201).
- **C-CI-1 matrix fan-out:** `mfe-onboarding` is the THIRD per-remote build unit for `cloudbuild.remote.yaml` /
  the dorny/paths-filter matrix. Path trigger: `frontend/apps/mfe-onboarding/**`. NOTE: a change to `shared/**`
  (`frontend/libs/**`) must rebuild ALL remotes — SP03 promoted `AuthLayoutComponent` into `libs/composites/` and
  this remote SHARES `@mesell/core` (`_mesell_core` chunk), so a libs/core or libs/composites change invalidates it.
- **CSP / staging:** inherited — no CSP today (D14); CSP authored ADD-ONLY at SP07 (D42, dev-smoke-first). Staging
  remotes off-cluster (C-STAGING-1).

## New surface vs pricing/export (FYI for infra)
mfe-onboarding is the FIRST remote that consumes the shared `@mesell/core` AuthService singleton at runtime. The
remoteEntry's `shared[]` includes `_mesell_core-*.js` (singleton). When versioning/CDN-caching shared chunks, the
shell + ALL AuthService-consuming remotes must resolve the SAME `@mesell/core` module URL (import-map) — do NOT
serve a stale duplicate per remote, or you reintroduce the singleton-drift the C5 contract prevents.
