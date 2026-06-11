# Feature Board — Frontend Lead

**Lead agent:** `meesell-frontend-coordinator`
**Domain:** `frontend`
**Last updated:** 2026-06-11 (mfe-catalog SP05 MERGED to integration via group PR #77 squash f11d0bf; founder-gate PR #82 OPEN; smart-picker frontend IN PROGRESS; Wave 1 gates #61/#68 + SP04 + smart-picker #55 still OPEN)
**This file is the single domain-level status surface for the lead.**

---

## Active features

| Feature | Group branch | Status | Current session | Last touched | Blocking | Notes |
|---|---|---|---|---|---|---|
| smart-picker | feature/smart-picker/frontend | IN PROGRESS | mesell-smart-picker-frontend-session-1 (SPEC-only) | 2026-06-11 | none | V1 Feature 2 — LAST slice (AI #54 + backend #72 MERGED on feature/smart-picker/integration @ ba94543; founder gate PR #55 OPEN). HYBRID step 1: lead authored 2 specialist specs (component-builder + service-builder); branch cut from integration ba94543. D4 rename catalog-new->smart-picker (first commit, component-builder). Route /catalogs/new UNCHANGED. RECONCILIATIONS (lead-ruled, see specs): (1) backend §9.E CategorySuggestion has NO commission_pct -- card OMITS commission for V1 (was a simulated-data invention); (2) NO HttpClient/interceptor/ApiClient exist yet on integration -- service-builder INTRODUCES provideHttpClient at this slice (feature-scoped); confidence is 0-1 float not 0-100. Conflict vs SP03 onboarding: DISJOINT (already merged; routes present on integration; line-disjoint in app.routes.ts). Specialists dispatched by master (step 2); lead gates at step 3. |

## Recently merged (last 14 days)

| Feature | Merged to | Date | PR | Notes |
|---|---|---|---|---|
| mfe-catalog | feature/mfe-catalog/integration | 2026-06-11 | #77 (squash f11d0bf) | MF Sub-Plan 05 (R4 — the L one). 5-page catalog funnel (F7 smart-picker/catalog-new, F8 catalog-form, F9 images, F10 preview + catalogs list) → apps/mfe-catalog Native Federation remote (port 4205). **FIRST Routes-array expose** ./CatalogRoutes (D31) + NEW shell helper loadRemoteRoutesWithFallback (D12 fallback degrades WHOLE sub-tree to RemoteFailureComponent). 16 files renamed R100 (blob hashes IDENTICAL — byte-identical, 0 logic edits); 6 new files; catalog-form.routes.ts removed (D34, 0 dangling). Shell route table SHRANK 5 funnel children + CATALOG_FORM_ROUTES loadChildren → 1 catalogs loadChildren (strangler win); pricing/export siblings untouched. **LEAD INDEPENDENTLY RE-VERIFIED (not from builder report, 0 discrepancies):** remote build GREEN; shell build GREEN 3.278s (≤90s); 43 files/411 tests (baseline 43/408 +3 fallback tests, 0 fail/skip, no drop = R-SP5-3 PASS); 4 moved specs discovered under spec-apps-mfe-catalog-*; boundary 0 primeng; **§6.G singleton (P0):** @mesell/ui-kit + @mesell/composites = own shared chunks, @mesell/core legitimately ABSENT (no page imports AuthService — only a main.ts comment), AuthService NOT inlined anywhere — no drift; main.ts boots provideRouter(CATALOG_ROUTES) full 5-route set (R-SP3-1 fix). **D33 ZERO promotions** (libs/ diff EMPTY; 9 candidate types 0 cross-remote importers; no canonical Product/Catalog entity as-built) — matches Founder Ruling 2026-06-11 APPROVED-as-recommended, deferred to Wave-6 backend-contract. CatalogFormApiService route-scoped on :id/edit, SmartPickerApiService component-scoped — neither promoted to root (D32). Group PR #77 LEAD-GATE APPROVE comment + squash --admin; remote branch deleted via gh api. develop merged into integration (e1384c7) conflict-free (no SP04 on develop yet); both builds re-certified GREEN on merged tip. Founder-gate PR #82 integration→develop OPEN — lead does NOT approve (D1). |
| mfe-onboarding | feature/mfe-onboarding/integration | 2026-06-11 | #67 (squash e2035330) | MF Sub-Plan 03 (R2, F5 onboarding + F13 profile, routes /onboarding + /profile). FIRST multi-expose remote (D20: ./OnboardingComponent + ./ProfileComponent). D21 AuthLayout PROMOTED layouts/→libs/composites/ + barrel (founder RULED APPROVED); all 4 relative consumers re-pointed; 0 dangling (R-SP3-2). **D22 AuthService singleton C1–C5 = migration auth GO/NO-GO: PASSED.** R-SP3-1 (P0 auth-drift) root-caused+fixed: ignoreUnusedDeps/Sheriff pruned @mesell/core (inlined AuthService into remote) because main.ts referenced only OnboardingComponent → FIX = main.ts routes BOTH exposes → core stays shared+singleton (no AuthService change, C2). Remote build 2.85s/shell 3.37s (≤90s). 43 files/408 tests (406 baseline + 2 C5; 0 fail/skip, R-SP3-3). Boundary 0. Headless: remoteEntry+both chunks+core chunk 200, broken→404 (D12). Integration `git merge develop` conflict-free (SP02 remote not yet on develop). Founder-gate PR #68 OPEN. D13 hosting deferred to SP04-05. WAVE 1 parallel with SP02. |
| mfe-export | feature/mfe-export/integration | 2026-06-11 | #60 (squash 565d754) | MF Sub-Plan 02 (R6, F12 export). features/export → apps/mfe-export Native Federation remote; 2nd extraction, copied SP01 recipe (D15). Remote build 3.43s/shell 2.89s (esbuild preserved, <90s); 42 files/406 tests (== SP01 baseline, export spec discovered via apps/ glob, 0 drop, 0 fail); boundary 0 in apps/. NEW surfaces: two-remote manifest (pricing+export both remoteEntry 200 + chunk 200, broken→404; R-SP2-4 PASS) + D18 timer preserved across boundary (R100 rename, ngOnDestroy→clearInterval byte-identical). Integration→develop FOUNDER GATE PR #61 OPEN. §9.A: 5 PASS / 3 locally-proven (4,7,8) / 2 new-surface PASS / 0 FAIL. D13 hosting deferred to SP04-05 (no new infra request). WAVE 1 parallel with SP03. |
| mfe-pricing | develop | 2026-06-11 | #52 (squash a82cfcf) → #53 | MF Sub-Plan 01 PILOT — NOW ON DEVELOP. features/pricing → apps/mfe-pricing Native Federation remote; first loadRemoteModule + D12 fallback. Remote 3.35s/shell 3.29s (esbuild preserved); 42/406 tests; boundary 0. Integration→develop FOUNDER GATE PR #53 MERGED 2026-06-11 (bb37f5f) — founder approved the pilot. §9.A: 6 PASS / 3 locally-proven (4,7,8). Toolchain PROVEN; SP02–06 unblocked. |
| mf-workspace-foundation | feature/mf-workspace-foundation/integration | 2026-06-10 | #40 (squash e51761b) | MF Sub-Plan 0. libs/ relocation (@mesell/*) + Native Federation init (zero remotes). 401/401 tests, build 3.1s, boundary 0 violations. Integration→develop PR #41 MERGED 2026-06-11 (5198ba7). |

## Inter-lead requests open

| To lead | About feature | Request | Opened | Status |
|---|---|---|---|---|
| meesell-infra-builder | mfe-catalog | D35 fifth-remote prefix gs://meesell-frontend/{env}/mfe-catalog/{version}/ (port 4205) + matrix unit apps/mfe-catalog/** (C-CI-1) + prod manifest URL template remotes.mesell.xyz/{env}/mfe-catalog/{version}/remoteEntry.json. FIRST Routes-array remote (./CatalogRoutes). D33 ZERO promotions → NO new @mesell/core consumer → no shared/**-rebuilds-all this slice; CDN must serve SAME @mesell/ui-kit + @mesell/composites URLs to shell+catalog (singleton). RECORD-ONLY — D13 hosting deferred to consolidated SP04-05 wave. See handoff_mf_catalog_deploy.md | 2026-06-11 | OPEN |
| meesell-infra-builder | mfe-pricing | D13 Option-C hosting: GCS bucket + Cloud CDN + remotes.mesell.xyz DNS/cert + cloudbuild.remote.yaml upload pipeline + per-env manifest URL templating. Locally dev-validated (localhost remote); prod surface pending. See handoff_mf_pricing_deploy.md | 2026-06-11 | OPEN |
| meesell-infra-builder | mfe-export | D19 second-remote prefix gs://meesell-frontend/{env}/mfe-export/{version}/ + confirm dorny/paths-filter matrix fans out apps/mfe-export/** as its own build unit (C-CI-1). RECORD-ONLY — D13 hosting deferred to SP04-05 per founder ruling; extends the open SP01 request, NOT a new active ask. See handoff_mf_export_deploy.md | 2026-06-11 | OPEN |
| meesell-infra-builder | mfe-onboarding | D24 third-remote prefix gs://meesell-frontend/{env}/mfe-onboarding/{version}/ (port 4202) + matrix unit apps/mfe-onboarding/** (C-CI-1). FIRST remote sharing @mesell/core (_mesell_core chunk) — CDN must serve the SAME core module URL to shell + all auth-consuming remotes (no per-remote stale dup, or singleton drift returns). RECORD-ONLY — D13 hosting deferred to SP04-05 per founder ruling. See handoff_mf_onboarding_deploy.md | 2026-06-11 | OPEN |
| meesell-infra-builder | mf-workspace-foundation | CI matrix rewrite (C-CI-1) ready before Sub-Plan 1; confirm new frontend/libs/** paths resolve against build-frontend glob. See handoff_mf_ci_prep.md. NOTE: chore/ci-matrix-c-ci-1 worktree observed in flight 2026-06-11 — SP01 now adds apps/mfe-pricing/** as the first per-remote build unit (cloudbuild.remote.yaml). | 2026-06-10 | OPEN |

---

## Status vocabulary

| Status | Meaning |
|---|---|
| `PENDING` | Feature is on the lead's backlog; no branch exists yet. |
| `IN PROGRESS` | A `feature/{name}/frontend` branch exists; specialist is actively committing. |
| `IN REVIEW` | A PR is open against `feature/{name}`; awaiting lead approval. |
| `MERGED` | The frontend group's PR has merged to `feature/{name}` — the group is done for this feature. |
| `BLOCKED` | Work stopped pending an inter-lead request, infra change, or founder decision. |

A feature row stays on the active features table until the frontend group's PR merges to `feature/{name}`; then it moves to "Recently merged" for 14 days before being removed.

## Acceptance gate

Every `feature/{name}/frontend` → `feature/{name}` PR is reviewed against the checklist in `.github/PULL_REQUEST_TEMPLATE/frontend.md`. The lead does not merge until every box is checked: build < 90 s (CLAUDE.md Decision 12), bundle delta noted, screenshots at 360 px and 1280 px attached, accessibility checks confirmed, CI gates 1 + 3 green. See repo management master plan §2.1 + the Merge gate section of `.claude/agents/meesell-frontend-coordinator.md`.
