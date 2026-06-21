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
