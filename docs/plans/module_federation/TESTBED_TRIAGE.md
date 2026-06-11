# TestBed Failure Triage — Module Federation Gate 3 Baseline

**Status:** COMPLETE — Gate 3 satisfied
**Author:** meesell-frontend-coordinator (Frontend Lead)
**Session:** mesell-testbed-triage-frontend-session-1
**Date:** 2026-06-10
**Scope:** TRIAGE ONLY — zero source/test/config changes were made. The only new file is this document.

---

## 1. Purpose

The Module Federation MASTER_PLAN.md (APPROVED 2026-06-10) §9 Gate 3 requires that the
**38 pre-existing Angular 21 + Vitest TestBed test failures** be *triaged — not fixed* — so
federation's 34-file relocation (Sub-plan 0) starts from a **known-red baseline** and any new
failures introduced by relocation are distinguishable from pre-existing ones.

This document is that baseline.

---

## 2. Method

- **Package manager:** pnpm (pnpm-lock.yaml present; no package-lock.json). `pnpm install --frozen-lockfile` → "Already up to date" (node_modules present).
- **Test command:** `pnpm test` → `ng test` → **`@angular/build:unit-test`** builder (Angular's official unit-test target, Vitest-backed). No custom `vitest.config.*` exists; the builder auto-injects TestBed init.
- **No source/test/config files were modified.** Tests were run exactly as committed on `develop`.

### Toolchain as-run

| Package | Version |
|---|---|
| @angular/core | ^21.2.0 |
| @angular/build | ^21.2.14 |
| @angular/compiler | ^21.2.0 |
| vitest | ^4.1.8 (resolved; declared ^4.0.8) |
| primeng | ^21.1.9 |
| @primeuix/themes | ^2.0.3 |
| typescript | ~5.9.2 |

---

## 3. Result — Summary Counts

```
Test Files   38 passed (38)
Tests       392 passed (392)
Duration    4.49 s
```

| Bucket | Meaning | Count |
|---|---|---|
| **H** (harness) | TestBed/compiler-resolution crash (the historically-recorded Angular 21 + Vitest + PrimeNG issue) | **0** |
| **A** (assertion) | Test runs but genuinely fails an expectation — possible real bug | **0** |
| **O** (other) | Import/setup/misc failure | **0** |
| **Skipped / quarantined / `.only` / `.todo`** | Failures masked by being disabled | **0** |
| **TOTAL FAILING** | | **0** |

A repo-wide scan for `.skip` / `.only` / `.todo` / `xit` / `xdescribe` returned **zero matches** —
the green result is genuine, not masked by disabled tests.

---

## 4. Actual-vs-Recorded Reconciliation (38 → 0)

**Recorded (Waves 3-5 era):** "38 pre-existing TestBed test *failures*."
**Actual (2026-06-10, this run):** **0 failures.** There are exactly **38 spec *files*** on disk, all passing, totalling 392 green tests.

**Why the drift — the "38" was always the file count, and the harness crash was since resolved:**

1. The historical TestBed crash (Angular 21 + Vitest 4 + PrimeNG 21 needing an explicit
   `@angular/compiler` setup file — recorded in MEMORY.md Wave 2B/Wave 5 entries) was a
   **harness-init problem that blocked all spec files at once.** When every one of the 38 spec
   files crashed at TestBed bootstrap, the failure was naturally counted as "38 failures" —
   i.e. one-per-file — which is identical to the 38-file count.
2. The fix landed in commit **`7001b44` "feat(frontend): migrate to Angular 21 + PrimeNG 21 — Waves 3-5 complete"**.
   The `@angular/build:unit-test` builder (v21.2.14) **auto-injects** the TestBed/compiler
   initialization — visible in the build output as the generated **`init-testbed.js`** and
   **`vitest-mock-patch.js`** chunks. No hand-written `vitest.setup.ts`/`test-setup.ts` is needed;
   the builder supplies it. This is the official replacement for the manual `@angular/compiler`
   setup file the historical workaround was reaching for.
3. The Wave 5 mitigation noted in memory (extracting pure-function `.model.ts` logic so it could
   be unit-tested *without* TestBed) reduced TestBed surface area, but the headline fix is the
   builder upgrade — TestBed-dependent component specs now bootstrap cleanly.

**Conclusion:** the 38 were never genuine assertion failures. They were a single harness-init
crash fanned out across 38 files, and that crash is resolved on current `develop`.

---

## 5. Per-File Status (all 38 spec files — all PASS)

| # | Spec file | Bucket | Status |
|---|---|---|---|
| 1 | app/app.spec.ts | — | PASS |
| 2 | app/features/landing/landing.component.spec.ts | — | PASS |
| 3 | app/features/account/onboarding/onboarding.component.spec.ts | — | PASS |
| 4 | app/features/auth/login.component.spec.ts | — | PASS |
| 5 | app/features/auth/signup.component.spec.ts | — | PASS |
| 6 | app/features/auth/otp-verify/otp-verify.component.spec.ts | — | PASS |
| 7 | app/features/profile/profile.component.spec.ts | — | PASS |
| 8 | app/features/dashboard/dashboard.component.spec.ts | — | PASS |
| 9 | app/features/catalog-new/catalog-new.component.spec.ts | — | PASS |
| 10 | app/features/catalog-form/catalog-form/catalog-form.component.spec.ts | — | PASS |
| 11 | app/features/images/image-uploader/image-uploader.component.spec.ts | — | PASS |
| 12 | app/features/preview/preview/preview.component.spec.ts | — | PASS |
| 13 | app/features/pricing/pricing/pricing.component.spec.ts | — | PASS |
| 14 | app/features/export/export/export.component.spec.ts | — | PASS |
| 15 | app/layouts/shell/shell.component.spec.ts | — | PASS |
| 16 | app/layouts/auth-layout/auth-layout.component.spec.ts | — | PASS |
| 17 | app/shared/page-header/page-header.component.spec.ts | — | PASS |
| 18 | app/shared/stat-card/stat-card.component.spec.ts | — | PASS |
| 19 | app/shared/status-badge/status-badge.component.spec.ts | — | PASS |
| 20 | app/shared/empty-state/empty-state.component.spec.ts | — | PASS |
| 21 | app/shared/loading-skeleton/loading-skeleton.component.spec.ts | — | PASS |
| 22 | app/ui/button/button.component.spec.ts | — | PASS |
| 23 | app/ui/input/input.component.spec.ts | — | PASS |
| 24 | app/ui/otp-input/otp-input.component.spec.ts | — | PASS |
| 25 | app/ui/textarea/textarea.component.spec.ts | — | PASS |
| 26 | app/ui/password-input/password-input.component.spec.ts | — | PASS |
| 27 | app/ui/badge/badge.component.spec.ts | — | PASS |
| 28 | app/ui/card/card.component.spec.ts | — | PASS |
| 29 | app/ui/table/table.component.spec.ts | — | PASS |
| 30 | app/ui/dialog/dialog.component.spec.ts | — | PASS |
| 31 | app/ui/file-upload/file-upload.component.spec.ts | — | PASS |
| 32 | app/ui/steps/steps.component.spec.ts | — | PASS |
| 33 | app/ui/select/select.component.spec.ts | — | PASS |
| 34 | app/ui/tree-select/tree-select.component.spec.ts | — | PASS |
| 35 | app/ui/skeleton/skeleton.component.spec.ts | — | PASS |
| 36 | app/ui/progress-bar/progress-bar.component.spec.ts | — | PASS |
| 37 | app/ui/toast/toast.component.spec.ts | — | PASS |
| 38 | app/ui/confirm-dialog/confirm-dialog.component.spec.ts | — | PASS |

(File-name resolution derived from the builder's emitted `spec-*` chunk names; all 38 spec files
on disk are accounted for and every corresponding test file reported PASS.)

---

## 6. Known Fix Path (already applied — recorded for completeness)

The historical workaround target was: *"add an `@angular/compiler` setup file so PrimeNG-importing
components can bootstrap under TestBed in the zoneless Vitest 4 environment."*

**This is no longer an open task.** The `@angular/build:unit-test` builder auto-generates the
equivalent (`init-testbed.js` + `vitest-mock-patch.js`) at build time. There is **no future task to
schedule** for the harness — it is resolved on `develop`. Should a manual setup file ever be needed
(e.g. for additional global mocks during federation), the scope would be a single
`src/test-setup.ts` referenced from the builder config — estimated < 0.5 agent-session — but it is
**not required today**.

---

## 7. Gate 3 Verdict

> **Gate 3 SATISFIED.** The TestBed baseline is acknowledged and reconciled: the historically
> recorded "38 failures" were a single harness-init crash fanned across the 38 spec files, resolved
> by the Angular 21 builder upgrade in commit `7001b44`. Current `develop` runs **38/38 spec files
> green, 392/392 tests passing, 0 failing, 0 skipped.**
>
> **Sub-plan 0 may treat exactly N = 0 failures as expected-red.** Any test failure that appears
> during federation's 34-file relocation is therefore a **NEW regression attributable to the
> relocation**, not a pre-existing condition, and must be fixed before that Sub-plan's PR merges.

---

## 8. Revision History

| Date | Change | Author |
|---|---|---|
| 2026-06-10 | Initial triage — Gate 3 baseline established; 38→0 reconciled | meesell-frontend-coordinator |
