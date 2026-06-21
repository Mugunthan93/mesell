# QA Wave 1 — Consolidated Test Report

**Author:** `meesell-qa-coordinator` (QA Lead — the fourth coordinator pillar)
**Wave:** QA Wave 1
**Date:** 2026-06-22
**Branch base:** `develop` @ `9c2fc7f` (worktree `docs/qa-wave-1-report`)
**Lanes:** backend · frontend · e2e (all three executed against a live local stack)

---

## Executive summary

QA Wave 1 stood up the **QA pillar** (4 agents + 3 testing skills + a Playwright
scaffold, growing the fleet 19 → 23) and then **executed comprehensive tests across
all three lanes** — backend, frontend, and end-to-end.

**Headline:** the testing initiative **found and fixed a real HIGH product bug
(broken logout)** and **found a second (broken XLSX export)** before any user ever
hit them. The broken-logout fix is the marquee proof that the QA pillar pays for
itself: a silent re-authentication via the HttpOnly refresh cookie meant the
"Logout" button left the user logged in — discovered only because the E2E
exploration phase drove the real DOM, not a mock.

| Lane | PR | Squash SHA | Result |
|---|---|---|---|
| Backend | #380 | `5da7af9` | **1314 passed / 28 skipped / 0 failed** (full suite); gate spot-rerun of the 9 new/extended files = **66 passed** |
| Frontend | #383 | `39b428a` | **1527 passed / 61 failed / 20 skipped** (Vitest umbrella); the 61 reds are **PRE-EXISTING**, not introduced by Wave 1 |
| E2E | #385 | `70fe9f3` | **9 passed / 3 `test.fixme`** (Playwright, `--workers=1`, stable ×3) |
| Logout fix | #381 | `456494e` | HIGH product bug fixed (cookie-revoke + navigate) + 3 regression tests + E2E sentinel |

All squash SHAs above are confirmed reachable from `develop`.

---

## Per-lane results

### Backend — PR #380 (squash `5da7af9`)

- **Full suite:** `1314 passed / 28 skipped / 0 failed`
  - Runner: `backend/.venv/bin/python -m pytest`, Python 3.11, `TEST_DATABASE_URL=…meesell_test`
  - The `_resolved_db.endswith("_test")` safety guard was honoured — no test ran against a non-`_test` database.
- **Gate spot-rerun** of the 9 new/extended files: `66 passed`.
- **Zero real external calls** — Gemini, MSG91, Razorpay, and GCS were all mocked at the adapter boundary.
- **13 new tests added.** Per-case:

  | ID | Case | Assertion |
  |---|---|---|
  | P0.1 | Prod OTP-bypass rejection | (already covered before this wave — confirmed present) |
  | P0.2 | OTP rate-limit | Nth request returns `429` |
  | P0.3 | Google-verify collision | `409` when the email belongs to a different `google_sub` |
  | P0.4 | Settlement math | `₹61.78` **paise-exact**; unknown leaf → `422` |
  | P0.5 | Tampered webhook | `401` on a bad Razorpay signature |
  | P0.6 | Budget-cap boundary | at-ceiling spend raises (₹500 cap enforced) |
  | P0.7 | `categories/suggest` method contract | `405` on `GET` (route is `POST`) |
  | P1.8 | Suggest contract | returns a top-3 shape |
  | P1.9 | Autofill (mocked shape) | idempotent against the mocked Gemini response |
  | P1.10 | Enum regression | `size_in_ltrs:"3.5"` → `200` (closes the historical PATCH-path enum 422) |

- **DEFERRED → Wave 2:** **P1.11** (export-ZIP member structure) **self-skips** because the helper signature it was written against is wrong. It asserts nothing useful as written, so it was correctly left as a skip rather than merged as an assertion-free pass. Carried forward.

### Frontend — PR #383 (squash `39b428a`)

- **Vitest umbrella:** `1527 passed / 61 failed / 20 skipped`.
  - mfe-billing project: `591 passed / 5 failed` (the 5 are part of the 61 pre-existing).
- **Unblocked the umbrella build:** fixed the pre-existing `mfe-pricing` spec TypeScript blocker (`TS2352` / `TS2367`) that previously prevented the umbrella Vitest run from compiling at all.
- **Net-new:** `frontend/libs/core/guards/auth.guard.spec.ts` — 3 green tests covering the route guard.
- **The 61 failures are PRE-EXISTING** — confirmed three independent ways:
  1. None of the 61 live in the files PR #383 touched.
  2. They exist at the merge-base (before any Wave-1 commit).
  3. They reproduce on a clean checkout of `develop`.
  They are therefore **NOT introduced by Wave 1**; they are logged as Wave-2 carry-forward (see Findings, W2-FE-1 … W2-FE-8).

### E2E — PR #385 (squash `70fe9f3`)

- **Run:** `playwright test --workers=1` → `9 passed / 3 test.fixme`. Stable across **3 consecutive runs** (no flake).
- The E2E lane is a **two-phase** discipline: a live `agent-browser` exploration discovered the real selectors first, the page objects were given `data-testid`s (added to the components in PR #381), and only then were the flows codified. No selector was written from memory.
- **Per-flow:**

  | Flow | Result | Notes |
  |---|---|---|
  | Phone-OTP onboarding | **PASS** | OTP dev bypass `000000`, verify field `otp` |
  | Catalog creation | **PASS** | wizard step-through |
  | Category smart-picker | **PASS** | suggestions list |
  | Plan guard | **PASS** | free-tier gated route |
  | **Logout + back-nav guard** | **PASS** | the federation auth-singleton sentinel — validates the #381 logout fix end-to-end |
  | Google Sign-In (render) | **PASS** | GIS button renders |
  | Image pre-check (uploader) | **PASS** | file input + uploader present |
  | Export (page) | **PASS** | export page renders |
- **3 `test.fixme` (intentionally deferred, each pointing at a known cause):**

  | Deferred flow | Why |
  |---|---|
  | export-download | the mfe-export `productId` bug (below) makes the download path 422 — fix the bug, then un-fixme |
  | image-precheck-result | no local GCS → backend returns `502 gcs.unavailable`; needs a mocked GCS seam or a CI GCS |
  | google-signin-click | headless Google OAuth is undriveable; the consent screen cannot be automated |

---

## Product bugs found BY testing

### 1. HIGH — broken logout (FIXED)

The E2E exploration phase found that `AuthService.logout()` (in `frontend/libs/core/services/auth.service.ts`) **neither called the server-side cookie-revoke nor navigated away** — so the HttpOnly refresh cookie silently **re-authenticated** the user. The "Logout" button did not log the user out.

- **Fix — PR #381 (`456494e`):** `logout()` now does a best-effort cookie revoke (`this.authApi.logout()`, fire-and-forget so a network failure never blocks local logout) **and** `this.router.navigate(['/login'])`. `forceLogout()` (the token-rotation cascade guard) was given symmetric behaviour.
- **Regression coverage:** 3 unit tests on the logout path, **plus** the E2E `logout-guard` flow that asserts the outcome end-to-end (session does not survive a logout, and back-nav does not re-auth).
- **Why it matters:** this is the marquee proof the QA pillar pays for itself — a silent-re-auth security/UX defect that only a live DOM-driven flow would catch, caught and fixed inside the first wave.

### 2. broken XLSX export (FILED, not yet fixed)

`frontend/apps/mfe-export/src/app/export.component.ts` `onGenerate()` **hardcodes** the product id:

```ts
// export.component.ts:431
const productId = 'current-product-id';   // TODO(V1): read from ActivatedRoute snapshot.params['id']
this.exportApi.initiate(productId).subscribe({ ... });
```

instead of reading the route `:id` (`ActivatedRoute.snapshot.params['id']`). The service then POSTs to `/api/v1/products/current-product-id/export-xlsx` — a bogus path — which **422s**, so the export download is unreachable.

- **Status:** FILED. An **inter-lead request is open to the frontend-coordinator** to read `productId` from `ActivatedRoute`. This is also the cause of the `export-download` E2E `test.fixme` — once fixed, that flow un-fixmes.

---

## Visual evidence (screenshots)

**E2E per-flow (this wave) — `/tmp/e2e-run/screens/*.png`:**

- `00-setup-dashboard.png` — auth.setup landed on dashboard
- `01-catalog-creation.png`
- `02-category-picker.png`
- `03-export-page.png`
- `04-image-uploader.png`
- `05-plan-guard.png`
- `06-google-signin.png`
- `07-logout-guard-login.png` — logout returns to /login (the #381 fix, visually)
- `08-onboarding-dashboard.png`

**Earlier corroborating captures:**

- `/tmp/catalog-verify/*.png` — catalog-logout fix round-trip (`01-catalogs-loggedin`, `02-billing-plans-loggedin`, `03-catalogs-roundtrip`)
- `/tmp/gauth-preflight/*.png` — Google sign-in readiness (`01-login-with-google-button`, `02-final-state`)

---

## Verbal evidence

**Live `/api/radar` detector snapshot** (captured at report time, `2026-06-21T22:21:49Z`) — every detector quiet, nothing firing:

```json
{
  "generated_iso": "2026-06-21T22:21:49Z",
  "counters": [
    {"name": "auth-401-storm",        "count": 0, "threshold": 3, "firing": false},
    {"name": "python-traceback",      "count": 0, "threshold": 1, "firing": false},
    {"name": "http-500",              "count": 0, "threshold": 1, "firing": false},
    {"name": "csp-violation",         "count": 0, "threshold": 1, "firing": false},
    {"name": "login-redirect",        "count": 0, "threshold": 3, "firing": false},
    {"name": "federation-singleton",  "count": 0, "threshold": 1, "firing": false},
    {"name": "route-404",             "count": 0, "threshold": 1, "firing": false}
  ]
}
```

Of note: `federation-singleton` and `login-redirect` (the two detectors tied to the
auth-singleton logout regression) are both at `count: 0` — consistent with the FED-1
fix (PR #373) and the #381 logout fix holding on the live stack.

**Live `/api/logs?service=backend&n=20`** (redacted runtime sample) — clean window, no
errors in the sampled tail:

```json
{"service": "backend", "count": 0, "lines": [], "generated_iso": "2026-06-21T22:21:49Z"}
```

**Runner summary lines** (the canonical "verbal" pass evidence):

- Backend: `1314 passed, 28 skipped` (full) · `66 passed` (gate spot-rerun)
- Frontend: `1527 passed, 61 failed, 20 skipped` (Vitest umbrella; 61 pre-existing)
- E2E: `9 passed, 3 test.fixme` (Playwright `--workers=1`, stable ×3)

---

## Findings / Wave-2 carry-forward

**Frontend pre-existing reds (the 61), triaged into named items:**

| ID | Sev | Item |
|---|---|---|
| W2-FE-1 | HIGH | refresh-interceptor auth-refresh-storm race |
| W2-FE-2 | HIGH | `OtpVerifyComponent.errorMessage` missing |
| W2-FE-3 | — | onboarding/profile `mee-auth-layout` |
| W2-FE-4 | — | landing bootstrap |
| W2-FE-5 | — | shell + missing `/onboarding` route (NG04002) |
| W2-FE-6 | — | empty-state icon |
| W2-FE-7 | — | `auth-write.smoke` |
| W2-FE-8 | — | ui-kit message / otp-input |

**Other carry-forward:**

- **Backend P1.11** — export-ZIP member structure test (wrong helper signature; self-skips today). Re-write against the correct helper and assert ZIP member names.
- **The 3 E2E `test.fixme`** — export-download, image-precheck-result, google-signin-click (each blocked on a concrete cause above).
- **mfe-export `productId` bug fix** — read `productId` from `ActivatedRoute`; un-fixme the export-download flow once landed (inter-lead request open to frontend-coordinator).

---

## Founder summary

QA Wave 1 ran **three real test lanes** against a live local stack — not mocks of
the runs themselves. **Backend** is fully green: `1314 passed / 0 failed`, with 13
new tests covering the money-and-auth-critical paths (OTP rate-limit, Google-verify
collision, paise-exact settlement, tampered-webhook rejection, the ₹500 budget cap,
and the suggest/autofill/enum contracts) — and zero real external calls.
**Frontend** Vitest passes `1527`; the `61` reds were proven pre-existing (three
ways) and are filed as Wave-2 items, not regressions from this wave. **E2E** passes
`9` Playwright flows (3 stable runs) with 3 intentionally deferred.

The wave **found two product bugs before any user could**: a **HIGH broken-logout**
bug (the Logout button silently re-authenticated via the HttpOnly cookie) — now
**FIXED** with a cookie-revoke + navigation plus unit and E2E regression coverage —
and a **broken XLSX export** (a hardcoded `'current-product-id'` instead of the route
id) — now **FILED** to the frontend lead. Carried to Wave 2: the 8 named pre-existing
frontend reds, one deferred backend export-ZIP test, the 3 deferred E2E flows, and
the export `productId` fix.
