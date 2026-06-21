# Frontend testing quirks

PrimeNG, signal, and federation-aware mock patterns + the pitfalls that bite in
Angular unit tests. Append a note whenever a TestBed setup surprises you.

## Seeded from prior project memory (2026-06-22)
- **PrimeNG + NG0201:** a component that toasts needs a `MessageService` provider in
  the TestBed — a missing one throws NG0201 (seen live in `app.spec.ts`).
- **Signals vs OnPush:** assert AFTER both `flushEffects()` and `detectChanges()`;
  asserting before either reads stale DOM.
- **Federation-aware mocks:** the shared `@mesell/core` `AuthService` is a
  cross-remote singleton at runtime — in a unit test always provide a fresh spy,
  never the real singleton, so auth state doesn't leak between tests.
- **Never load a real remote in a unit test** — mock the loader seam; federation
  wiring belongs to E2E.

## QA Wave 1 learnings (2026-06-22)

- **TS2352 double-cast pattern:** when an interface has no index signature, `obj as Record<string, unknown>` fails with "insufficient overlap". Fix: cast via `unknown` first: `obj as unknown as Record<string, unknown>`. This is the safe escape hatch for probing for absent keys on typed objects.
- **TS2367 narrowed-literal comparison:** a `const x: 'foo' = 'foo'; x === 'bar'` comparison is a TS error because the types have no overlap. Fix: `(x as string) === 'bar'` to relax the check while keeping the runtime assertion. The test intent (prove a value is NOT something) is preserved.
- **Functional guard testing pattern (Angular 21):** use `TestBed.runInInjectionContext(() => myGuard({} as never, {} as never))` to run a `CanActivateFn` in a DI context without navigating the real router. Provide the `Router` via `provideRouter([...routes])` so `router.createUrlTree(['/login'])` can produce a proper UrlTree. Verify the result is a `UrlTree` instance and check `.toString()` for the path.
- **Runner is Vitest (not Karma):** `@angular/build:unit-test` emits `.spec-*.js` chunks; test discovery uses `include` patterns relative to `sourceRoot (src/)`. Pre-test `tsc --noEmit -p tsconfig.spec.json` is a fast way to detect TS errors before paying the full build cost.
- **Pre-existing non-deterministic failures (refresh.interceptor i/j/k):** these tests use the real AuthService with `setupReal()` and two concurrent HTTP controllers, which creates async races. They pass ~60% of runs. Document as pre-existing; do NOT attempt to fix in the test-writer lane (they require feature code changes to AuthService's finalize() race guard — file back to coordinator).
- **ng test --include does not work with native-federation buildTarget:** only `frontend` and `mfe-billing` have `@angular/build:unit-test` test targets. Other remotes' specs are included via the `frontend` project's `include` glob (`../../**/*.spec.ts`). Never add `--include` flags for scoping within a project — it breaks with native-federation `buildTarget` warning.
