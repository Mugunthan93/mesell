# Frontend spec files authored

Ledger of every Karma/Jasmine `.spec.ts` written: path (adjacent to source), wave,
and the component/service it covers. Append after each task.

| Path | Wave | Component / Service |
|---|---|---|
| `frontend/libs/core/guards/auth.guard.spec.ts` | qa-wave-1 | `authGuard` CanActivateFn — redirect to /login when unauthenticated; pass-through when authenticated |

## Notes on mfe-pricing spec fix (same wave, same PR #383)
- `frontend/apps/mfe-pricing/src/app/pricing.component.spec.ts` — MODIFIED (not authored from scratch)
- Fix 1 (:241 TS2352): cast `PriceCalcNoPricingDataError as unknown as Record<string, unknown>` — TypeScript requires the double-cast because the interface has no index signature and does not sufficiently overlap with `Record<string, unknown>`.
- Fix 2 (:266 TS2367): `(errorState as string) === 'server_error'` — the local type is narrowed to the literal `'no_pricing_data'` so TS correctly flags that the two strings can never be equal without the cast. The test intent (asserting the state is NOT server_error) is preserved.
