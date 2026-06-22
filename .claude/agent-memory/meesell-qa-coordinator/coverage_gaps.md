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
## Onboarding Wave C e2e CLOSED + SCRIBED writer-memory findings (PR #411, 2026-06-22, mesell-qa-onboarding-e2e-session-1 GATE)
Onboarding e2e merged to `feature/qa-onboarding/integration` (`e5a44a3`); 11 passed / 3 test.fixme / 0 failed (writer; gate static + source ground-truth — the live re-run was blocked by a contaminated dev stack, disclosed). The e2e-test-writer could NOT write its own memory (worktree write-protection) — the gate SCRIBES its findings here, in the qa-coordinator memory, per the brief.

**SCRIBED → `selector_registry.md` (newly LIVE-VERIFIED 2026-06-22, slot-1 shell :4210, integration tip `7e86054`; all also ground-truthed in source by the gate):**
- **mfe-onboarding — onboarding form (post-#399 persist-fix).** The OLD businessName/city/gst mock form is GONE; `onboarding-business-name` testid is REMOVED (0 occurrences in source). The shipped form is the seller-profile manufacturer/packer/country set:
  - Form fields are `mee-input` wrappers with NO testid → driven by `getByLabel(<substring>)` (each renders a real `<label [for]>`→`<input>`; substring match tolerates required "… *" labels). Verified labels: `Manufacturer Name` (L176), `Manufacturer Address`, `Manufacturer Pincode` (L188), `Packer Name` (L194), `Packer Address`, `Packer Pincode` (L206); Country of Origin defaults "India" (pre-valid, left untouched).
  - Submit button = the ONE testid on the page: `getByTestId('onboarding-submit')` (L224) → click `.locator('button')`. Also the "fresh user routed to onboarding" visible marker.
  - Skip link = `<a role="button">I'll set this up later →</a>` (L239), NO testid → `getByRole('button', { name: /set this up later/i })`.
  - Submit-error banner = `mee-alert-banner` (no testid) emitting `role="alert"` → `getByRole('alert')`.
- **mfe-auth — error banner** is the same `mee-alert-banner` → `getByRole('alert')` (shared by /login + /otp-verify). The pre-existing auth testids (login-phone-input, login-request-otp, login-google-host, otp-input, otp-verify-submit) remain LIVE.

**SCRIBED → `federation_quirks.md` (re-confirmed §5-note-3):** the WHOLE stack (shell + ALL 7 remotes) must be rebuilt + aligned from the integration tip before e2e exploration — rebuilding remotes alone is INSUFFICIENT (the shell is the `@mesell/core`/`@mesell/ui-kit` singleton host; a stale shell silently no-ops `[testId]` passthroughs). The writer rebuilt slot-1 shell :4210 + all 7 remotes from integration tip `7e86054` (the baseline reuse was pre-#381 and lacked the testids). RE-CONFIRMED live this wave. (Corollary observed by the gate: a half-rebuilt/contaminated stack — some remotes on slot-0 ports, no backend — is the default broken state; do not trust a partial running stack for a gate re-run.)

## Onboarding Wave C — NEW product bug + carry (2026-06-22)
- **NEW PRODUCT BUG — onboarding pincode NOT-NULL 500.** The onboarding form sends `null` for empty manufacturer/packer pincode but `seller_profile` DB columns are NOT NULL → submit-without-pincode = 500 `NotNullViolationError`. Filed → frontend-coordinator (Director deciding fix owner). Fix: FE make pincode required and/or BE nullable-or-422. E2E tests fill valid pincodes so they pass.
- **Carry (unchanged):** mfe-export route-productId product bug (export-download fixme); image-precheck (GCS/MinIO env); google-click (cross-origin GIS OAuth); CI wiring memo → infra.

## qa-image-ai Wave A gate outcome (2026-06-22) — what closed / what remains
- **IA-RED-1 (cost-meter column drift)** — FIX AUTHORED & VERIFIED in PR #431 (perf test +
  cost_tracker canonical-shape contract). NOT yet landed (PR REJECTED for the unrelated
  test_route_integration.py fixture bug). Closes on the corrected re-do PR.
- **image pipeline gaps (CMYK/sub-res/non-white-BG/invalid-JPEG/watermark true|false|uncertain/audit)**
  — covered by test_precheck_pipeline_gaps.py (10 cases), VERIFIED GREEN as a group; lands on re-do.
- **image ROUTE gaps (IMG-BE-01/07/09/11)** — authored but the FILE fails 2/4 in-process
  (`_otp_client` event-loop fixture bug). OPEN until the writer reuses the loop-bound conftest client.
- **IA-RED-2 (eval `_run_one_fixture` stub)** — STILL OPEN. Guard harness authored; the real-scorer
  wiring is the AI lane's product change (`feature/qa-image-ai/ai`). Stub-guard retirement OWED at the
  ai-coordinator `/ai` gate (memo filed).
- **autofill UI component naming / E2E** — untouched this lane (Wave B/C scope).

## qa-image-ai Wave B (frontend) — gate outcome + scribed writer findings (2026-06-22)
PR #442 (`feature/qa-image-ai/frontend` → integration, squash `c87d800`) — APPROVE. +42 tests-only, 217/217 green (vitest re-run by the gate). Source-verified writer findings scribed here:
- **AutofillButtonComponent / FieldDiffComponent DO NOT EXIST as separate components** (V1 spec §3.C named them; ground-truth `grep -rl 'class AutofillButtonComponent|class FieldDiffComponent'` = NONE). The autofill button + yellow-highlight diff overlay are **INLINE in `CatalogFormComponent`**: button at template L264 (`mee-ai-fill-row`), `onAutofill()` at component L720. Filed as a SPEC GAP (not a red). Any future autofill-UI test/E2E must target the inline surface, NOT a phantom component. Coverage delivered at the service/model seam (`catalog-form.model.ts`: `isAiSuggested`/`clearAiSuggestion`/`mergeAiSuggestions`/`extractSuggestionEntries`/`dismissSuggestion`).
- **onAutofill DUAL-WRITE note (source L732-733):** the `next:` handler writes BOTH `this.aiSuggestions.set(values)` (the highlight overlay) AND `this.fieldValues.update(cur => ({...cur, ...values}))` (pre-fills the inputs) in the SAME tick. So the V1 "no auto-apply" model is: fields ARE pre-filled for review, but the overlay highlight persists until the user edits (`clearAiSuggestionIfPresent` on blur/change) or dismisses (`dismissSuggestion`, removes overlay only, keeps the field value). IMG-FE-09 asserts exactly this dual-write. Error path L736-738 = `autofilling.set(false)` + toast `'AI fill failed. Please try again.'` (non-empty, no blank-key regression). Any contract test on autofill MUST account for the dual-write — asserting only-overlay or only-fieldValues misreads the as-built.
- **IMG-FE-06 is PRE-COVERED, do not re-spec:** `image.service.spec.ts` (mfe-catalog/images/image-uploader/) has the 22-test `HttpTestingController` error matrix (upload 401→logout+EMPTY / 404→EMPTY / 500→EMPTY; pollImages 401→logout / 404→`of({images:[]})` / 500→`of({images:[]})`). The Wave B uploader spec correctly did NOT duplicate it.

## qa-catalog Wave C (e2e) gate outcome (2026-06-22, mesell-qa-wave-catalog-e2e-session-1) — APPROVED → WAVE COMPLETE
PR #462 squash-merged `1fdd5ea` into `feature/qa-catalog/integration`. qa-catalog COMPLETE
(A backend c8f4255/#435 + CAT-BUG-1 fix c20ee0e/#437; B frontend 3476b0e/#451; C e2e
1fdd5ea/#462). READY for the FOUNDER's integration→develop merge.

CLOSED this lane:
- **CAT-E2E-04** = the CAT-BUG-1 LIVE regression guard (smart-picker outer-stream survival).
  CONFIRMED real: injects a 429 (the RETHROWN path) → inner `catchError` keeps `valueChanges`
  alive → retype recovers. Would FAIL pre-#437. Registry-live-verified selectors.
- CAT-E2E-01/02 existing happy paths kept.

STILL OPEN (carried, filed as inter-lead requests):
- **Category-schema seed gap (NEW, real)** — `GET /categories/{id}/schema` 404s for
  picker-suggestable categories (schema seeded ~100 prewarmed; picker suggests from the full
  3,772-leaf tree) → empty edit form. Blocks CAT-E2E-05 (autosave) + CAT-E2E-06 (AI-fill).
  → data-engineer + backend (Director also tracking).
- **Browse-fallback link + empty-state CTA ship NO data-testid** — CAT-E2E-03/07 fixme on
  source-derived role/name selectors. → frontend-coordinator (add data-testid).
- **Live `--workers=1` run OWED** — slot-2 torn down + 8GB swap ceiling refused a rebuild;
  the gate fell back to source ground-truth + a CLEAN `--list` re-run. Re-run when the swap
  ceiling clears.
