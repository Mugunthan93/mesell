# Coverage gaps — accumulated across waves

The running ledger of untested (or under-tested) surfaces. Survives between
sessions: read it at the start of every wave so each spec targets the real gaps,
and prune an entry only when a merged test PR closes it.

## Known at bootstrap (2026-06-22)
- ~~Frontend ships ZERO `data-testid` attributes~~ → **CLOSED by #381** (~30 stable testids
  across shell + all 6 remotes) and consumed by the Wave-1 e2e lane (#385).
- ~~E2E flow specs in `frontend/e2e/flows/` are intentional STUBS~~ → **CLOSED by #385**:
  all 8 taxonomy flows codified (onboarding, catalog-creation, category-picker, image-precheck,
  export, plan-guard, logout-guard, google-signin). 9 green / 3 `test.fixme` (env/product-bug
  blocked — see below).
- Backend/frontend per-feature coverage was mapped at Wave-1 dispatch; Wave-1 landed backend
  (#380), frontend (#381/#383), and e2e (#385) on develop.

## Open gaps after Wave 1 (owed to Wave 2 / the TEST_REPORT)
- **mfe-export route-productId PRODUCT BUG** — XLSX export is broken through the UI (component
  hardcodes `productId='current-product-id'`). E2E export-download is `test.fixme` until fixed;
  filed → frontend-coordinator (`handoff_mfe_export_productid_bug.md`).
- **3 e2e `test.fixme`** — export-download (on the bug above), image-precheck-result (needs a
  GCS-credentialed env / MinIO — local dev 502s), google-signin-click (needs a Google test
  identity + allow-listed origin, or a stubbed GIS credential callback). Un-fixme conditions
  logged in `federation_quirks.md`.
- **61 pre-existing frontend reds** (#383 gate, full `ng test frontend` = 1527 pass / 61 fail /
  20 skip) — catalogued as Wave-2 carry-forward on the board. HIGH-signal: the
  `refresh.interceptor` auth-storm sentinel + the `OtpVerifyComponent.errorMessage` gap.
- **1 backend P1 skip** — the export-ZIP member-structure test (#380) self-skipped on a wrong
  `_build_xlsx_bytes(...)` signature assumption; fix the signature + assert in Wave 2.
- **CI wiring** — the e2e suite + the `ng test` umbrella + the backend gate are not yet wired
  into CI (the native-federation `buildTarget` is unsupported by `@angular/build:unit-test`;
  e2e needs Playwright browsers + a slot stack). Memo owed → infra.

## qa-onboarding Wave A (backend) — CLOSED gaps (2026-06-22, gate-verified on integration aa4345d)
The following onboarding-wave backend gaps (listed above under "Onboarding wave planning") are now
CLOSED by the merged Wave A tests (14 passed / 1 skipped):
- iam `otp/send` invalid-phone 422 (OB-BE-02), `otp/verify` wrong-code 401 / expired 401 / verify-429
  (OB-BE-05/06/07), `me` unauth 401 + pre-profile flag-false (OB-BE-17/18), `me` authed shape (OB-BE-16),
  otp/send happy (OB-BE-01). CLOSED.
- google verify invalid-token 401 + email_verified=false 401 (OB-BE-22/23). CLOSED.
- nullable-identity CHECK direct DB test (OB-BE-25, x3 — reject-both-null + 2 positive). CLOSED.
- customer active-categories replace semantics (OB-BE-31). CLOSED.
- customer get-404 / active-categories unknown-super 422 / compliance not-declared 404 + missing-fields
  422 / required-fields wizard map (OB-BE-27/30/32/33/34) — confirmed pre-existing in
  `test_customer_routes.py`; NOT a gap.

STILL OPEN after Wave A:
- **OB-BE-24** Google flag-OFF → 404 — SKIPPED (process-singleton isolation). Needs an app-factory
  fixture (fresh ASGI app per test) to assert cleanly. Carried.
- **OB-BE-38** DPDP consent — NOT modelled in V1 customer schema (grep-verified). SPEC gap → V1.5;
  no test until a `consent` column exists.
- Onboarding Waves B (frontend OB-FE-01..20) + C (e2e OB-E2E-01..08) — PENDING, not yet dispatched.
  Wave B carries the onboarding-`onSubmit` PRODUCT bug fix (data-loss; owner angular-component-builder).
