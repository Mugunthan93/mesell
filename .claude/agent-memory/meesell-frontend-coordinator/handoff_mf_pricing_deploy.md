# Handoff → meesell-infra-builder — mfe-pricing remote hosting (D13 / Option-C)

**From:** meesell-frontend-coordinator (Frontend Lead)
**Date opened:** 2026-06-11
**Feature:** mfe-pricing (MF Sub-Plan 01 — the pilot)
**SLA:** 48h before escalation to founder via STATUS_MASTER.md
**Board row:** feature_board_frontend.md → Inter-lead requests open (outgoing).

## Context
MF Sub-Plan 01 (mfe-pricing pilot) is BUILT and merged to
`feature/mfe-pricing/integration` (frontend group PR squash-merged). The remote
builds independently and produces a static artefact set. Per GATE4_CONFIRMATION.md
Option-C (C-RES-2), federation remotes are hosted OFF-cluster as static GCS bundles
behind Cloud CDN — NOT in-cluster pods (Option A INFEASIBLE on e2-standard-2).

The frontend has validated EVERYTHING that is locally provable WITHOUT the GCS
surface (the pilot does not block on infra — dev validation uses a localhost-served
remote). What remains is the actual cloud hosting surface, which is infra-owned.

## The built artefact (what frontend produces)
- `ng build mfe-pricing` → `frontend/dist/mfe-pricing/browser/` containing:
  - `remoteEntry.json` (the federation manifest — name `mfe-pricing`, exposes `./PricingComponent`)
  - `PricingComponent-<hash>.js` (the exposed component chunk, ~10 KB)
  - shared dep chunks (@angular/*, rxjs, primeng, @mesell/ui-kit, @mesell/composites)
  - `index.html` (standalone dev-serve only — NOT used in federation)
- Build is reproducible, ~3.4s, esbuild-based (Native Federation `kind: remote`).

## The asks (D13 / C-RES-2 / C-ROUTE-1 / C-CI-1)
1. **GCS bucket + Cloud CDN** at `gs://meesell-frontend/{env}/mfe-pricing/{version}/`
   served as `https://remotes.mesell.xyz/{env}/mfe-pricing/{version}/remoteEntry.json`.
2. **`remotes.mesell.xyz` DNS** — Namecheap A record + GCP-managed cert (C-ROUTE-1,
   NOT cert-manager).
3. **`cloudbuild.remote.yaml`** — upload pipeline: `ng build mfe-pricing` → `gsutil rsync`
   the `dist/mfe-pricing/browser/` tree to the versioned GCS path (C-CI-1). This is the
   FIRST per-remote build/deploy unit — it complements the C-CI-1 matrix work already
   in flight (chore/ci-matrix-c-ci-1 worktree observed).
4. **Per-env manifest templating** — the shell's `public/federation.manifest.json` must
   resolve to the env-correct CDN URL at deploy time (dev/staging/prod). Today it ships
   the DEV localhost URL `http://localhost:4201/remoteEntry.json`. Infra owns the
   prod/staging URL substitution (R-SP1-5 manifest drift mitigation).

## What is NOT in scope for this memo
- CSP (`script-src https://remotes.mesell.xyz`) — DEFERRED to SP07 (D14/D42 RULED,
  ADD-ONLY CSP, dev-smoke-first). Do NOT author CSP for the pilot.
- The shell relocation to apps/shell/ — DEFERRED to SP07 (D9/D43 RULED RELOCATE).

## Locally-proven vs hosting-pending (§9.A item 8)
PROVEN locally (no infra needed): remote builds independently, remoteEntry.json valid,
exposes correct, shared singletons not duplicated, served remoteEntry.json HTTP 200 at
the manifest URL, broken-URL HTTP 404 → fallback path. PENDING infra: the GCS/CDN
surface + prod manifest URL. The pilot's §9.A-8 is "locally proven / hosting handed to infra".

## How to resolve (decentralized memory protocol)
Read this memo + add YOUR OWN incoming-side row to YOUR board
(feature_board_infra*.md). Do NOT edit feature_board_frontend.md (sole-writer). When
the GCS surface is live + the prod manifest URL is templated, the Frontend Lead flips
the pilot's prod manifest entry and marks this CLOSED on its own board.
