# Angular Observability Wave — SPEC

## Feature: GlobalErrorHandler + RetryInterceptor

### Goal
Add Angular observability primitives to @mesell/core:
1. `GlobalErrorHandler` — catches uncaught JS errors (zone.js window.onerror path) and
   normalises them into the typed `ApiErrorEnvelope` for `ErrorService`.
2. `retryInterceptor` — wraps every HTTP call with exponential-backoff retries for
   network failures (status 0) and idempotent 5xx responses.
3. Wire both into the shell + all 7 remotes. Add `provideBrowserGlobalErrorListeners()`
   to all remotes (missing from original bootstrap).

### Files

| File | Action |
|------|--------|
| `frontend/libs/core/errors/global-error-handler.ts` | NEW |
| `frontend/libs/core/errors/global-error-handler.spec.ts` | NEW |
| `frontend/libs/core/interceptors/retry.interceptor.ts` | NEW |
| `frontend/libs/core/interceptors/retry.interceptor.spec.ts` | NEW |
| `frontend/libs/core/index.ts` | UPDATE — add both exports |
| `frontend/apps/shell/src/app/app.config.ts` | UPDATE — wire GlobalErrorHandler + retryInterceptor |
| `frontend/apps/mfe-auth/src/main.ts` | UPDATE |
| `frontend/apps/mfe-billing/src/main.ts` | UPDATE |
| `frontend/apps/mfe-catalog/src/main.ts` | UPDATE |
| `frontend/apps/mfe-dashboard/src/main.ts` | UPDATE |
| `frontend/apps/mfe-export/src/main.ts` | UPDATE |
| `frontend/apps/mfe-onboarding/src/main.ts` | UPDATE |
| `frontend/apps/mfe-pricing/src/main.ts` | UPDATE |

### Interceptor chain (shell + all remotes after change)
`[jwtInterceptor, retryInterceptor, refreshInterceptor, errorInterceptor]`

Rationale:
- jwt sets Bearer header first
- retryInterceptor wraps outer: retries network failures + idempotent 5xx BEFORE refresh
- refreshInterceptor handles 401 (inner of retry)
- errorInterceptor records final envelope (innermost)

### Retry policy
- count: 3
- delay: 2^(retryCount-1) * 1000ms → 1s, 2s, 4s
- Retry conditions: status===0 (any method) OR (status>=500 AND method in {GET,HEAD,OPTIONS,PUT})
- Non-retriable: 4xx, POST/PATCH/DELETE 5xx
- resetOnSuccess: true

### Locked decisions respected
- No NgRx / Zustand (locked decision 10)
- No localStorage JWT (locked decision 14 amendment)
- No new npm dependencies
- No @mesell/core version bump (federation singleton dedup uses "1.0.0")
- No mappingVersion change
