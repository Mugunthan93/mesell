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
