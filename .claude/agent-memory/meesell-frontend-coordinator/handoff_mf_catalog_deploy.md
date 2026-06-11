# Handoff → meesell-infra-builder — mfe-catalog (SP05) deploy

**From:** meesell-frontend-coordinator (Frontend Lead)
**Date:** 2026-06-11
**Topic:** 5th Native-Federation remote `mfe-catalog` hosting + CI matrix unit (D35)
**Status:** RECORD-ONLY hosting request — D13 production hosting deferred to the consolidated SP04-05 hosting wave per founder ruling; this extends the open SP01/SP04-05 hosting asks, not a new active blocker.

## What landed
- `apps/mfe-catalog/` Native-Federation remote (port 4205 dev), group PR #77 squash `f11d0bf` → `feature/mfe-catalog/integration`; founder-gate PR #82 (integration→develop) OPEN.
- Exposes a Routes ARRAY `./CatalogRoutes` (the FIRST routes-expose). Manifest dev entry: `"mfe-catalog": "http://localhost:4205/remoteEntry.json"`.

## Infra asks
1. **GCS prefix** for the 5th remote: `gs://meesell-frontend/{env}/mfe-catalog/{version}/` (parallels mfe-pricing/export/onboarding prefixes).
2. **Prod manifest URL template:** `https://remotes.mesell.xyz/{env}/mfe-catalog/{version}/remoteEntry.json` (D35). Manifest stays localhost for dev; per-env templating is infra-owned.
3. **C-CI-1 matrix:** confirm `dorny/paths-filter` fans out `apps/mfe-catalog/**` as its OWN build unit (cloudbuild.remote.yaml), siblings to mfe-pricing/export/onboarding.
4. **`shared/**`-rebuilds-all:** NOT triggered this slice — D33 produced ZERO model promotions, so no new `@mesell/core` cross-remote consumer was introduced. `libs/` is untouched by SP05. The catalog remote shares `@mesell/ui-kit` + `@mesell/composites` (own chunks) — CDN must serve the SAME `@mesell/ui-kit`/`@mesell/composites` module URLs to shell + catalog remote to preserve singletons (same rule as the onboarding `@mesell/core` note).

## Forward note (dashboard convergence — D33)
When mfe-dashboard (SP04) is extracted/reconciled, its product/catalog list types MAY re-point to any future promoted `@mesell/core` canonical Product/Catalog types — that is a SEPARATE post-SP05 follow-up PR (NOT touched by SP05; SP05 did not edit any sibling remote's internals).
