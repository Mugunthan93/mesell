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

## QA Wave 2 — auth frontend lane (2026-06-22, PR #397)

| Path | Wave | Component / Service |
|---|---|---|
| `frontend/apps/mfe-auth/src/app/auth-error-map.spec.ts` | qa-wave-2 | `mapSendOtpError` / `mapVerifyOtpError` / `mapGoogleError` pure functions — 18 table-driven cases, no TestBed [NET-NEW] |
| `frontend/apps/mfe-auth/src/app/auth-write.smoke.spec.ts` | qa-wave-2 | smoke suite — logout drain + onboarding route stub fix [MODIFIED: FIX-RED] |
| `frontend/apps/mfe-auth/src/app/login.component.spec.ts` | qa-wave-2 | `LoginComponent` — GIS load success/failure paths [MODIFIED: HARDEN] |
| `frontend/apps/mfe-auth/src/app/otp-verify.component.spec.ts` | qa-wave-2 | `OtpVerifyComponent` — logout drain + TestBed reset fix [MODIFIED: FIX-RED] |
| `frontend/libs/composites/auth-layout/auth-layout.component.spec.ts` | qa-wave-2 | `AuthLayoutComponent` — render, brand, aria-label, ng-content projection [MODIFIED: HARDEN] |
| `frontend/libs/core/interceptors/error.interceptor.spec.ts` | qa-wave-2 | `errorInterceptor` — terminal-401 / forceLogout path with both interceptors in chain [MODIFIED: HARDEN] |
| `frontend/libs/core/interceptors/refresh.interceptor.spec.ts` | qa-wave-2 | `refreshInterceptor` — cases i/j/k (auth-storm sentinel) [MODIFIED: FIX-RED HIGH] |
| `frontend/libs/core/services/auth.service.spec.ts` | qa-wave-2 | `AuthService` — localStorage in-memory-only assertion, 4 new cases (Decision #14) [MODIFIED: HARDEN] |

Note: `auth-api.service.spec.ts` — FE-AUTH-09 already covered (`withCredentials:true` on refresh + logout); no changes needed.
