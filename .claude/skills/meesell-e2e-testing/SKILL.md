---
name: meesell-e2e-testing
description: >-
  MeeSell's conventions and critical-flow taxonomy for writing Playwright
  end-to-end tests against the shell + 6-remote module-federation app. Use this
  skill WHENEVER you are writing or editing Playwright tests (anything under
  frontend/e2e/), designing a page object, setting up storageState auth, or the
  user says "write E2E tests", "Playwright", "test the seller journey", "browser
  test", or "QA the full app" — even if they don't say "Playwright" explicitly.
  Apply it before authoring any E2E test so selectors are discovered live (never
  from memory), ports come from config (never hardcoded), and every test asserts
  a visible outcome. Do NOT use it for pytest (defer to meesell-backend-testing)
  or Angular Karma/Jasmine specs (defer to meesell-frontend-testing).
---

# MeeSell E2E Testing — Conventions & Critical-Flow Taxonomy

These are the locked rules for writing Playwright E2E tests for the MeeSell app
(Angular 18+ Native-Federation: shell `:4200` host + remotes `:4201–4207`,
backend `:8000`). They exist so a test never asserts a hallucinated selector,
never hardcodes a port, and never "passes" on a console log instead of a real
user-visible outcome. They derive from `CLAUDE.md` (Decision #14 in-memory token
+ FE-D5 cookie) and the live federation port map, which win if anything here
disagrees.

## Conventions

### Two-phase mandate (NON-NEGOTIABLE)

1. **Exploration phase first.** Launch the full dev stack (`/mesell:dev`), use
   `agent-browser` to navigate the LIVE app, discover real selectors, and observe
   actual auth behaviour across shell → remote navigation. Deposit every stable
   selector into
   `.claude/agent-memory/meesell-e2e-test-writer/selector_registry.md`.
2. **Codification phase second.** Author the Playwright `.spec.ts` using ONLY the
   selectors found in phase 1. **Never write a selector from memory or
   documentation** — the app ships zero `data-testid` today, so selectors must be
   added to the app (coordinate via memo) and then verified live before use.

On every later wave, read `selector_registry.md` FIRST and only launch
`agent-browser` for flows/components not yet mapped — each wave is cheaper than
the last.

### Additional conventions

- **Page-object pattern** — one class per remote (`ShellPage`, `CatalogPage`,
  `DashboardPage`, `ExportPage`, …) in `frontend/e2e/page-objects/`. Specs talk to
  page objects, never to raw locators.
- **Pre-authenticate via `storageState`** — `auth.setup.ts` runs the phone-OTP
  flow ONCE (dev bypass `000000`, verify field is `otp` not `code`) and saves the
  session to `storageState.json`; all flows depend on the `setup` project. Because
  the access JWT is in-memory and the refresh token is an HttpOnly cookie
  (Decision #14 / FE-D5), storageState captures the COOKIE and the app
  silently refreshes on first navigation — do not try to inject a token into
  localStorage.
- **No hardcoded ports** — read every base URL from `playwright.config.ts`
  (env-overridable). Slot-N math: shell `4200 + N*10`, mfe[i] `4201 + N*10 + i`,
  backend `8000 + N*10`.
- **One file per seller flow** in `frontend/e2e/flows/`.
- **Assert a VISIBLE outcome** — a DOM element, a navigation (URL), or a file
  download event. Never assert only a network call or a console log.
- **Mark flaky tests with `test.fixme()` + a reason** rather than deleting them,
  and record the reason in `federation_quirks.md`.

## Critical-Flow Taxonomy (all must have coverage)

| Flow | File | What is asserted |
|---|---|---|
| Phone OTP onboarding | `onboarding.spec.ts` | OTP input → verify → plan screen → dashboard heading visible |
| Google Sign-In | `google-signin.spec.ts` | GIS button clickable → redirect → dashboard (no plan screen for a linked account) |
| Catalog creation wizard | `catalog-creation.spec.ts` | Shell → catalog remote → all wizard steps complete → saved catalog appears in the dashboard list |
| Image upload + precheck | `image-precheck.spec.ts` | Upload a valid JPEG → quality-gate result card visible with a numeric score |
| Category smart-picker | `category-picker.spec.ts` | Description typed → top-3 suggestions appear → selection updates the form field |
| Export download | `export.spec.ts` | Export button clicked → file download event triggered → downloaded file non-empty |
| Plan guard | `plan-guard.spec.ts` | Locked feature accessed on the free plan → upgrade prompt visible, not a blank screen or 404 |
| Logout + back-nav guard | `logout-guard.spec.ts` | Logout → browser back → redirected to `/login`, protected page not rendered |

## Federation gotchas (the highest-value things to watch live)

- **shell → remote navigation can drop the session** if the shared `@mesell/core`
  AuthService singleton is not deduped (empty version / divergent chunk hash).
  The `logout-guard` flow is the regression sentinel for this class. Record any
  live recurrence in `federation_quirks.md`.
- **Stale remote bundle** — a remote serving an old build (worktree-port pinning,
  `no-cache` vs `no-store`) makes "fixes don't show". Run against a freshly built
  stack; record the symptom if seen.

## Quick checklist before finishing an E2E task

- [ ] Exploration done; every selector is in `selector_registry.md`
- [ ] No selector written from memory/docs; none hardcoded in the spec
- [ ] All ports/base URLs come from `playwright.config.ts`
- [ ] One page object per remote; specs use page objects only
- [ ] `auth.setup.ts` storageState reused; flows depend on the `setup` project
- [ ] Every test asserts a visible outcome (DOM / navigation / download)
- [ ] Flaky tests are `test.fixme()` with a reason logged in `federation_quirks.md`
