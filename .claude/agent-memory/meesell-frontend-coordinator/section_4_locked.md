---
name: section-4-locked
description: FRONTEND_ARCHITECTURE.md §4 (core/ Cross-Cutting Foundation) LOCKED 2026-06-05 with retryOn503 opt-in flag (Look 1 applied); Looks 2 + 3 deferred to V1.5
metadata:
  type: project
---

# FRONTEND_ARCHITECTURE.md §4 LOCKED 2026-06-05

## The 3 walkthrough Look outcomes

**Look 1 — APPLIED.** Added opt-in `retryOn503: boolean` to `ApiOptions` in §4.E.1:
- Default `false` — caller handles via RxJS `retry()` per call when they want
- When `true` — ApiClient retries up to 3 times with exponential backoff (1s, 2s, 4s) before letting the error reach ErrorInterceptor
- Documented use sites: autofill (Gemini cold start), image upload (GCS hiccup), export trigger (Celery queue backpressure)
- Documented anti-use: catalog autosave PATCH — loud failure is correct UX because the seller needs to see the offline banner immediately, not have us swallow the error with backoff

**Look 2 — DEFERRED to V1.5.** `NetworkService` stays online-only (`navigator.onLine`) for V1:
- `navigator.connection.effectiveType` ('slow-2g', '2g', '3g', '4g') is the planned V1.5 addition
- V1 doesn't have it because no V1 feature has adaptive behavior to drive (no low-data mode, no image quality switching)
- The signal is added WHEN a V1.5 feature surfaces a concrete need

**Look 3 — DEFERRED to V1.5.** "Report this issue" button in error snackbar:
- V1 surface: traceId-in-Details-dialog (sellers screenshot + email support manually)
- Deferred because the receiving support endpoint doesn't exist yet
- V1.5 adds the endpoint + the button as a single dispatch

## Founder directive FE-D8 (recorded same turn as §4 LOCK)

> "For upcoming sections, decide drill-down depth myself."

The coordinator owns the depth call per section based on:
- How much new content needs locking (deep vs already-covered-elsewhere)
- Whether specialists will need this level of detail (high stakes vs simple inventory)
- Whether the section has cross-section dependencies that need explicit contracts vs implicit references

Founder evaluates at lock time and revises if too shallow or too deep. This delegation reduces founder review load on sections that don't need it.

## §4 final shape (10 subsections)

| Sub | Locks |
|---|---|
| A | What §4 establishes |
| B | The 4-interceptor chain (Jwt → Locale → Refresh → Error) — registration order is load-bearing |
| C | `AuthService` API — `accessToken` signal + `isAuthenticated`/`userId`/`plan` computed + bootstrap/setAccess/scheduleRefresh/logout/clear lifecycle |
| D | `AuthGuard` (active) + `PlanGuard` (wired-but-inert in V1) |
| E | `ApiClient` typed wrapper — methods + `ApiError` shape + `retryOn503` opt-in (Look 1) |
| F | `ErrorService` — 4 surface methods (showError/Warning/Info/Success) with MatSnackBar |
| G | `NetworkService` — `navigator.onLine` signal (V1 only; effectiveType is V1.5 — Look 2) |
| H | InjectionToken set — `API_BASE_URL` + `ENV_CONFIG` |
| I | Cross-feature models in `@core/models/` — 9 typed interfaces mirroring backend response shapes; `meesho_*` fields STRIPPED per Philosophy M10/F1 |
| J | What §4 does NOT cover |

## Key contracts locked

**`AuthService` public API (signals + methods):**
```typescript
accessToken: Signal<string | null>            // in-memory ONLY (FE-D5)
userId: Signal<UUID | null>                   // computed from JWT
plan: Signal<PlanTier | null>                 // computed from JWT
isAuthenticated: Signal<boolean>              // computed
bootstrap(): Observable<boolean>              // /auth/refresh on AuthGuard
setAccess(response): void                     // after verify or refresh
scheduleRefresh(expiresIn): void              // schedules next refresh at (exp - 30s)
logout(): Observable<void>                    // /auth/logout (server-side DEL + cookie clear)
clear(): void                                 // wipes without server call (unrecoverable 401)
```

**`ApiClient` public API:**
```typescript
get<T>(path, options?): Observable<T>
post<T>(path, body, options?): Observable<T>
patch<T>(path, body, options?): Observable<T>
put<T>(path, body, options?): Observable<T>
delete<T = void>(path, options?): Observable<T>
postMultipart<T>(path, formData, options?): Observable<T>

ApiOptions {
  params?: Record<string, string|number|boolean>
  headers?: Record<string, string>
  withCredentials?: boolean      // auto-true for /auth/*
  retryOn503?: boolean           // NEW per Look 1; default false
}
```

**Interceptor chain (canonical order):**
```
JwtInterceptor → LocaleInterceptor → RefreshInterceptor → ErrorInterceptor → HttpClient
```

**`ApiError` shape:**
```typescript
class ApiError extends Error {
  kind: 'http' | 'network' | 'parse'
  status: number          // 0 for network
  code: string | null     // backend's machine-readable code
  displayMessage: string  // locale-resolved
  traceId: string | null  // backend's x-request-id header
  raw: HttpErrorResponse | null
}
```

## How to apply when specialists eventually scaffold

For `meesell-angular-service-builder`:
- Create `core/auth/auth.service.ts` per §4.C signal+method signatures
- Create `core/interceptors/{jwt,locale,refresh,error}.interceptor.ts` per §4.B
- Create `core/api/api-client.service.ts` with the 6-method surface + `ApiOptions` interface including `retryOn503`
- Create `core/services/{error,network}.service.ts` per §4.F + §4.G
- Create `core/tokens/{api-base-url,env-config}.token.ts` per §4.H
- Create 9 model interfaces in `core/models/` per §4.I — strip `meesho_*` fields if any appear (those are backend bugs)
- Register all interceptors via `provideHttpClient(withInterceptors([...]))` in `app.config.ts` in the canonical order
