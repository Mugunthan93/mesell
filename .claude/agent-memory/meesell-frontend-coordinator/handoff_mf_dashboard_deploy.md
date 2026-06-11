# HANDOFF → meesell-infra-builder — mfe-dashboard (SP04) hosting

**From:** meesell-frontend-coordinator (Frontend Lead)
**Date:** 2026-06-11
**Status:** RECORD-ONLY (D13 hosting deferred to consolidated wave per founder ruling) — register the 4th remote so the eventual hosting/CI/CDN config covers it.
**Decision:** D29 (per SP04 plan).

## What landed
- New Native-Federation remote **`mfe-dashboard`** (port **4204**) extracting F1 landing (PUBLIC) + F6 dashboard (AUTH).
- Group PR #84 squash-merged to `feature/mfe-dashboard/integration` (a6ad02f); develop merged in conflict-free (7c2800c); founder-gate PR #86 OPEN (integration→develop).
- Exposes TWO components from one remoteEntry.json: `./LandingComponent` + `./DashboardComponent`.

## Infra asks (when D13 hosting wave lands)
1. **GCS prefix:** `gs://meesell-frontend/{env}/mfe-dashboard/{version}/` (mirrors pricing/export/onboarding).
2. **CI matrix unit (C-CI-1):** `apps/mfe-dashboard/**` as its own per-remote build unit in `cloudbuild.remote.yaml` / dorny/paths-filter matrix.
3. **Prod manifest URL template:** `https://remotes.mesell.xyz/{env}/mfe-dashboard/{version}/remoteEntry.json`.
4. **Singleton CDN constraint:** CDN must serve the SAME `@mesell/ui-kit` + `@mesell/composites` module URLs to shell + mfe-dashboard. (No `@mesell/core` consumer here — neither page injects AuthService, so core is correctly absent from this remote's shared[]; `shared/**` does NOT trigger a rebuild-all for this slice.)

## CSP flag (HIGH-STAKES — for SP07)
- mfe-dashboard is the **FIRST remote federating a PUBLIC pre-auth route** (landing at `/`). Its remoteEntry is fetched with NO Authorization header (D27/D29) as a static public asset.
- Together with SP06 auth (the other public remote), landing is the **highest-stakes CSP surface**. CSP authoring is ADD-ONLY, dev-smoke-first, deferred to SP07 (D14→resolved by D42, founder-RULED APPROVED 2026-06-11). Do NOT strip CORS or the refresh `Set-Cookie` when CSP lands.

## Localhost dev-validated
- Manifest dev URL `http://localhost:4204/remoteEntry.json`; prod surface pending the hosting wave.
