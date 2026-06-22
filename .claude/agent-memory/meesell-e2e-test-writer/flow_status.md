# Flow status — coverage / flaky / blocked

One row per critical seller flow (design §5.3 taxonomy). Update after each wave.
Status ∈ STUB · EXPLORING · COVERED · FIXME · BLOCKED.

## QA Wave 1 — CODIFIED + RUN (2026-06-22, slot-1 :4210 vs develop d13ed50)
Result: **9 passed, 3 skipped (test.fixme)** — stable across 3 consecutive runs,
`--workers=1`. Every passing test asserts a VISIBLE outcome (DOM/URL).

| Flow | File | Status | Notes |
|---|---|---|---|
| Phone OTP onboarding | flows/onboarding.spec.ts | COVERED ✅ | Fresh OTP login (000000) → lands on /onboarding (new user) → fill business name → /dashboard heading visible. Own login (not the shared fixture). |
| Google Sign-In | flows/google-signin.spec.ts | COVERED (render) ✅ + FIXME (click) | Test 1 PASS: GIS host visible + GIS injects its button iframe. Test 2 fixme: real Google OAuth can't be driven headless (cross-origin iframe + dev origin not allow-listed). |
| Catalog creation | flows/catalog-creation.spec.ts | COVERED ✅ | Smart-picker = the create entry point; pick a category → product created → /catalogs/:id/edit reached → product appears as a dashboard-product-row. |
| Image upload + precheck | flows/image-precheck.spec.ts | COVERED (uploader renders) ✅ + FIXME (precheck card) | Test 1 PASS: images page + PrimeNG advanced uploader render for a real product. Test 2 fixme: local dev has NO GCS → POST /products/{id}/images returns 502 gcs.unavailable BEFORE rembg runs. Fixture JPEG added (fixtures/valid-product.jpg). |
| Category smart-picker | flows/category-picker.spec.ts | COVERED ✅ | Type description → top-3 suggestion cards visible (Gemini, ~few-s latency) → select advances to /catalogs/:id/edit. |
| Export download | flows/export.spec.ts | COVERED (page renders) ✅ + FIXME (download) | Test 1 PASS: export page + Generate trigger render for a real product (chained create→export). Test 2 fixme: PRODUCT BUG — onGenerate() hardcodes productId='current-product-id' (ignores route param) → 422 → download unreachable. |
| Plan guard | flows/plan-guard.spec.ts | COVERED ✅ | /billing/plans shows upgrade-prompt CTAs (free plan); NOT the remote-failure fallback. |
| Logout + back-nav guard | flows/logout-guard.spec.ts | COVERED ✅ | The FED-1/logout-fix sentinel. Login → cross shell→remote (catalog) → logout → URL=/login → back-nav stays /login, dashboard heading absent. CONFIRMS the logout fix works E2E. Own fresh login (logging out would poison the shared worker context). |

## QA Wave C — qa-pricing (2026-06-22, slot-0 :4200 vs integration tip 7a5193c)
Result: **5 passed, 1 fixme** (pricing + export targeted run), STABLE ×2
(`--workers=1`, runs 27.1s then 9.2s). Every passing test asserts a VISIBLE outcome.

| Flow | File | Status | Notes |
|---|---|---|---|
| Price-calc happy (PQE-E2E-02) | flows/pricing.spec.ts | COVERED ✅ | createProductViaPicker → real UUID → /catalogs/:id/pricing → enter 70 → Calculate → settlement-value (₹57.62) + breakdown + disclaimer visible; negative-alert count 0. LOCKED model visible: Commission fee (0%)=₹0.00. |
| Price-calc negative (PQE-E2E-03) | flows/pricing.spec.ts | COVERED ✅ | enter 1 → settlement ₹-11.31 → pricing-negative-alert visible ("This selling price results in a negative settlement…"), a 200+warning NOT an error page. |
| Export page render (PQE-E2E-01) | flows/export.spec.ts | COVERED ✅ | real product → /catalogs/:id/export → export-trigger visible. (Needed a FRESH mfe-export rebuild — the baseline dist was stale 22:54, pre-testids.) |
| Export productId-fix outcome | flows/export.spec.ts | COVERED ✅ (NEW) | Generate on a draft product → POST hits the REAL UUID → 422 → "Your product isn't ready / A front image is required" rendered (productId BUG is FIXED via resolveExportProductId). download-link count 0. |
| Export download (PQE-E2E-05) | flows/export.spec.ts | FIXME (env) | REASON CHANGED from Wave-1: productId bug FIXED; now blocked by no-ready-product + no-GCS-signed-URL in local dev. Un-fixme on a GCS-credentialed env with a ready front-image product. |

PQE-E2E-04 (apply-price→export link) NOT authored this wave: the pricing component's
"Save & Continue" applies the price but the spec's exit gate listed E2E-02/03/05 as
the gated set; apply→export is an optional extension — left for a follow-up to avoid
over-asserting a deferred link the §3.E table marks "(IF selectors)".

## Auth architecture for the suite (CRITICAL — see federation_quirks.md)
- Refresh token is SINGLE-USE with rotation → a shared storageState only authes the
  FIRST flow. SOLUTION: `fixtures/auth.ts` worker-scoped authed-context fixture logs
  in ONCE per worker (seeds from the setup project's storageState.json → zero extra
  OTP sends) and gives each authed test a fresh PAGE in that SAME context.
- onboarding + logout-guard use their OWN fresh login (logged-out start / teardown).
- OTP send is rate-limited 3/3600s per IP → run with --workers=1 (also bounds RAM)
  and clear `meesell:rl:*` in Valkey DB0 before the run (dev-env reset, NOT in specs).

## Run harness notes
- @playwright/test@1.52.0 matches the cached chromium-1169 (no browser download).
  Added @playwright/test to frontend/package.json devDeps (the config needs the
  runner; only bare `playwright` was declared before).
- Ports from playwright.config.ts via env (MEESELL_SHELL_URL/PORT); all app + API
  traffic goes through the shell (/api proxied). Never hardcoded in specs.


## Wave-3 dispositions (catalog vertical, PR #409, develop @ a94e013)
- W3-E2-1 wizard step-through -> SAVED catalog: CODIFIED (`flows/wizard-save.spec.ts`),
  HONESTLY skip-gated. Skips when (a) smart-picker returns 0 suggestions (dev Gemini
  suggest unconfigured) or (b) the category has 0 schema-driven fields. Asserts real
  UUID + `catalog-save-status` reaches "Saved" TEXT + product listed. Green-or-skipped,
  never falsely red.
- W3-E2-2 Live Preview: BLOCKED -> `test.fixme`. Preview PAGE RETIRED (#278); "Preview"
  button -> /edit (#395). No frontend surface. Un-fixme only if a preview page returns.
- W3-E2-4 list->edit->delete: BLOCKED -> `test.fixme`. No delete control + no per-row
  testids in catalog-list. Edit leg covered by E2-1. Un-fixme on delete control + testids.
- W3-E2-6 price->apply->export: BLOCKED -> `test.fixme`. mfe-pricing has no testids + no
  apply control; export leg gated on E2-3. Backend round-trip covered by W3-BE-17.
- W3-E2-3 export download: FIXME, un-fixme condition documented inline. Gated on PR #398
  (mfe-export onGenerate() still hardcodes productId='current-product-id' on develop).
  Real selector is `export-download` (NOT `export-download-button`).
- W3-E2-5 image precheck: FIXME (per founder) — no local GCS creds (upload 502s before
  rembg). Un-fixme on a GCS-credentialed env / MinIO.
