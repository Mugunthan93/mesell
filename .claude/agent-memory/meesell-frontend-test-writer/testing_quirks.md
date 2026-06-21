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
