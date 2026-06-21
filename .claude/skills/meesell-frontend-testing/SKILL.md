---
name: meesell-frontend-testing
description: >-
  MeeSell's conventions and coverage taxonomy for writing Angular Karma/Jasmine
  specs for the frontend. Use this skill WHENEVER you are writing or editing
  Angular component or service specs (*.spec.ts under frontend/), mocking a
  service in a component test, asserting signal-derived DOM state, or the user
  says "write tests for the frontend", "add a component/service spec", "cover
  this component", or "QA the Angular app" — even if they don't say "Karma" or
  "Jasmine" explicitly. Apply it before authoring any Angular spec so specs sit
  adjacent to source and never inject real services. Do NOT use it for pytest
  (defer to meesell-backend-testing) or Playwright E2E (defer to
  meesell-e2e-testing).
---

# MeeSell Frontend Testing — Conventions & Coverage Taxonomy

These are the locked rules for writing Karma/Jasmine specs for the MeeSell
frontend (Angular 18+, standalone components, TypeScript strict, RxJS + signals,
Tailwind + PrimeNG/Material, Native Federation shell + remotes). They exist so a
spec never injects a real service, never asserts on stale change-detection state,
and lives next to the code it tests. They derive from `CLAUDE.md` (Angular
conventions + Decisions 9–13), which wins if anything here disagrees.

## Conventions

- **Standalone component testing** via `TestBed.configureTestingModule({ imports:
  [ComponentUnderTest] })` — standalone components are imported, not declared.
- **Mock services with `jasmine.createSpyObj`** — never inject a real service into
  a component test. Provide the spy via `{ provide: RealService, useValue: spy }`.
- **Flush signals with `TestBed.flushEffects()`** before asserting any
  signal-derived DOM state, and call `fixture.detectChanges()` after a state
  mutation — `ChangeDetectionStrategy.OnPush` components do not refresh on their
  own.
- **`HttpClientTestingModule` + `HttpTestingController`** for anything that
  triggers HTTP; assert the request (URL + method + headers) and flush a mock
  response. Call `httpMock.verify()` in `afterEach`.
- **Spec files live ADJACENT to source** (`foo.component.spec.ts` next to
  `foo.component.ts`) — never in a separate top-level `tests/` folder. (The
  Playwright E2E suite is the one exception and lives in `frontend/e2e/`.)
- **Test naming:** `it('should {behaviour} when {condition}')`.
- **No real timers / no real federation fetch.** A component test never loads a
  remote — mock the loader seam. Federation wiring is E2E's job.
- **Run evidence.** Paste the `ng test` (or project-scoped `ng test <app>`)
  summary in the PR.

## Coverage Taxonomy

| Layer | Mandatory test cases |
|---|---|
| UI Kit (20+ components) | Each component renders without error; `@Input()` bindings propagate to the DOM; `@Output()` emitters fire on user interaction |
| Page components | Loading state: spinner visible when `loading()` is true; error state: snackbar/toast triggered; happy path: data from the mock service renders correctly |
| Services | State mutation via `BehaviorSubject` / signal updates on API response; HTTP calls verified via `HttpTestingController`; error path calls the snackbar/toast (`MatSnackBar.open()` or PrimeNG `MessageService`) |
| Auth guard | Redirects to `/login` when `AuthService.token()` returns null; passes through when the token is valid |
| JWT interceptor | `Authorization: Bearer {token}` header attached when a token is present; request passes through unchanged when the token is null |
| Catalog service | `list()` state transition; `create()` appends to the signal; `update()` patches in place; subscription teardown on component destroy (no leak) |

## MeeSell-specific quirks (record new ones in testing_quirks.md)

- **PrimeNG** components often need their module imported into the TestBed and a
  `MessageService` provider — a missing `MessageService` surfaces as NG0201
  (a real bug seen in `app.spec.ts`). Provide it in component tests that toast.
- **Signals vs OnPush:** assert AFTER both `flushEffects()` and
  `detectChanges()`; asserting before either reads stale DOM.
- **Federation-aware mocks:** the shared `@mesell/core` `AuthService` is a
  cross-remote singleton at runtime — in a unit test always provide a fresh spy,
  never the real singleton, so tests don't leak auth state into each other.

## Quick checklist before finishing a frontend-test task

- [ ] Spec sits adjacent to its source file
- [ ] Component under test imported into TestBed; all services are spies
- [ ] `flushEffects()` + `detectChanges()` before asserting signal-derived DOM
- [ ] HTTP asserted via `HttpTestingController`; `verify()` in `afterEach`
- [ ] `it('should … when …')` naming; behaviour, not implementation, asserted
- [ ] `ng test` output pasted in the PR description
