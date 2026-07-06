# Session mesell-fe-unit-suite-green-frontend-session-1 — 2026-07-06 — W2-FE unit suite GREEN (action #4 of V1_CONFORMANCE_REPORT)

**Mode:** FAST-MODE chore (spec-only). Founder-approved via the launching agent as action #4 of `docs/status/V1_CONFORMANCE_REPORT.md @ ed6c99a`. RELAUNCH after a prior instance died at session limit during triage (nothing had landed — no board row, no memory, no commits).

## Ground truth (reusable)

- **Runner = Vitest 4.1.8 (jsdom 28), ZONELESS. NOT Karma.** Invoke: `pnpm exec ng test frontend --watch=false`. The `frontend` project's `test` target (angular.json) includes `../../**/*.spec.ts` → it compiles + runs the ENTIRE workspace suite (all apps + libs, ~111 files). Consequence: **one TS compile error in ANY spec is build-blocking → 0 tests run** (the report's "build-blocking mfe type errors").
- **`fakeAsync()`/`tick()` do NOT work — zoneless.** Angular's `fakeAsync` needs `zone.js/testing`, absent here → `Error: zone-testing.js is needed for the fakeAsync() test helper` thrown at COLLECTION time (kills the whole file as a "Failed Suite", tests uncounted). The house pattern for RxJS `timer()` backoff is `import { vi } from 'vitest'` + `vi.useFakeTimers()` at test top + `vi.advanceTimersByTime(ms)` + `vi.useRealTimers()` in `afterEach`. Canonical model spec: `libs/core/services/api-client.service.spec.ts` (retry-filter suite, comment L18-20 spells it out). HttpTestingController flush is synchronous and coexists fine with fake timers.
- **Worktree bootstrap on the 8GB machine:** `MESELL_ALLOW_MASTER_GIT=1 git -C <master> worktree add /tmp/mesell-wt/fespecs origin/develop` → `cd frontend && pnpm install --frozen-lockfile` (5s, pnpm hard-links from global store) → `pnpm rebuild esbuild @parcel/watcher lmdb msgpackr-extract`. Full suite runs in ~5-13s.

## What was red (measured on origin/develop @ c24e158 — NEWER than the report's e1d2c1e/5e8e28f)

Actual count was **28 failed tests across 3 files + 1 build-blocking file** — NOT the report's approximate "~61" (intervening commits #501/#502 etc. already cleared the rest). 4 clusters:

| Cluster | File | Root cause | Fix | Size |
|---|---|---|---|---|
| A (build-block) | `apps/mfe-catalog/.../image-uploader.component.spec.ts` | 3× **TS2367** — model tests hard-code `const x = 1`, TS narrows to literal `1`, `x === 0` = "no overlap" | annotate the consts `: number` (narrowing can't collapse) | 4 lines |
| B (file-level) | `libs/core/interceptors/retry.interceptor.spec.ts` | 8× `fakeAsync()` → zone-testing error at collection (zoneless) | rewrite to `vi.useFakeTimers()`/`vi.advanceTimersByTime()`, mirror api-client spec | whole file |
| C (1 test) | `libs/ui-kit/input-number/input-number.component.spec.ts` | "render info icon when tooltip is set" queried `i.pi-info-circle` = null. The icon lives **inside `@if (label())`**; test set only `tooltip`, no `label` | add `setInput('label', ...)` to the test (real wizard usage always has a label) | 4 lines |
| D (27 tests) | `apps/mfe-onboarding/.../onboarding.component.spec.ts` | **NG0303** `[testId]` not a known prop of `mee-input`. PR #490 added `[testId]` to the 7 mee-input FIELDS but the spec's `MeeInputStub` never got the input (only the `mee-button` stub did) | add `@Input() testId` to `MeeInputStub` | 1 line |

## Result

Before: build-blocking (0 ran) → after Cluster-A fix: `3 files / 28 failed | 1999 passed | 7 skipped`. After B/C/D: **`111 files passed (111)` · `2035 passed | 7 skipped (2042)` · EXIT 0.** (+8 total-count = retry file now COLLECTS its 8 tests, previously uncounted.) The 7 skips are pre-existing (unchanged).

## Discipline notes / observations (non-blocking → board)

- **SURGICAL honored:** every change is `*.spec.ts`. Zero component/service edits. No component "bug fix" — Cluster C's "tooltip icon requires a label" is a defensible design (help icon sits in the label row), not a clear bug; the `input-number` component is owned by the `catalog-wizard-ux-fixes` #509 evolution (founder gate) — did NOT touch it.
- The image-uploader Cluster-A tests are "pure-fn model" tests (hard-coded consts, no real component) — the same house-style noted at the image-precheck gate. Left as-is (green now); a real-component-test hardening pass is a QA chore, not this session's scope.
- Landed **direct to develop** (fast-mode chore, founder-approved action #4) via `push origin HEAD:develop`, matching recent develop fix-commit norm (f5d6477 etc.). Rule B: specs-only → NO localhost rebuild needed.
