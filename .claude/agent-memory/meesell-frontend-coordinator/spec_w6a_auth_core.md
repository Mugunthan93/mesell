---
name: spec-w6a-auth-core
description: HYBRID step-1 TASK SPEC for Wave 6 Wave A (wave6-auth-core) — the foundation slice. Interceptor chain + ApiClient/ErrorService/NetworkService + AuthService.bootstrap/scheduleRefresh + real OTP login + D33 promotions + DISCREPANCY-1 re-point + authHeaders() removal. SPEC ONLY — no code, no dispatch, no git executed by the spec author.
metadata:
  type: project
  session: mesell-wave6-auth-core-spec-session-1
  status: SPEC — awaiting master step-2 dispatch
  base: origin/develop @ db556b9 (#109 Wave 6 MASTER PLAN landed)
---

# Wave 6 · Wave A — `wave6-auth-core` — TASK SPEC

> HYBRID step-1 deliverable. The session window dispatches the named specialists (step 2) with this spec; I am re-dispatched for the merge gate (step 3). I wrote NO feature code, called NO Task, ran NO git this session.

## 0. Governing decisions (all 4 founder calls RULED 2026-06-11 — as recommended)

The Wave 6 MASTER PLAN §7 DECISION-1..4 are now RULED. This spec treats them as LOCKED:

1. **DECISION-1 → pricing = SERVER-calc.** `POST /products/{id}/price-calc`; retire client-side P&L math. **Affects Wave D, not Wave A** — recorded here so the Wave D spec inherits it. No Wave A action.
2. **DECISION-2 → DISCREPANCY-1 fixed FRONTEND-side.** smart-picker `CategoryService.selectCategory()` re-points `POST /api/v1/catalogs` → `POST /api/v1/products`. **This IS a Wave A action** (it lives in the same `@mesell/core`-touching foundation slice because it pairs with the `authHeaders()` removal in the same file). §5 below.
3. **DECISION-3 → `AuthUser` extension = ADDITIVE-OPTIONAL** (`plan?`, `phone` reconciled, `created_at?`). §4 below.
4. **DECISION-4 → wave layout CONFIRMED**: 4 waves / 2 lanes / Wave A monolithic-serial-alone. This slice runs ALONE and MUST merge to develop before Wave B/C dispatch.

MASTER PLAN §7 must be flipped DRAFT→RULED in a separate docs chore (lead, fast-mode) — NOT part of this build slice. Flagged in the return.

---

## 1. Slice identity & scope

- **Slice:** `wave6-auth-core` (Wave 6, Wave A — foundation).
- **Remote topology touched:** the SHARED surface — `@mesell/core` (libs/core), shell `apps/shell/src/app/app.config.ts`, ALL 6 remote `apps/mfe-*/src/main.ts`, and the one already-wired service `apps/mfe-catalog/src/app/smart-picker/services/category.service.ts`. This is the ONLY Wave 6 slice allowed to touch the shared surface (DECISION-4). Every downstream wave touches only its own remote.
- **V1 routes exercised:** `/login`, `/signup`, `/otp-verify` (mfe-auth, port 4206 — real OTP login wiring) + EVERY authenticated route transitively (the interceptor chain + bootstrap gate them all). The route TABLES are frozen (federation cutover) — this slice does NOT edit `app.routes.ts`.
- **Specialists:** `meesell-angular-service-builder` (PRIMARY — interceptors, ApiClient/ErrorService/NetworkService, AuthService extension, AuthApiService, DISCREPANCY-1, authHeaders removal, registration) → then `meesell-angular-component-builder` (mfe-auth login/signup/otp-verify real-flow wiring) → then `meesell-angular-ui-styler` (auth + global error/offline UI states). Serial order is MANDATORY (§8).

### Scope IN (this slice only)
- `libs/core/interceptors/jwt.interceptor.ts` (NEW)
- `libs/core/interceptors/refresh.interceptor.ts` (NEW)
- `libs/core/interceptors/error.interceptor.ts` (NEW)
- `libs/core/services/api-client.service.ts` (NEW — typed HttpClient wrapper)
- `libs/core/services/error.service.ts` (NEW)
- `libs/core/services/network.service.ts` (NEW)
- `libs/core/services/auth.service.ts` (EXTEND — bootstrap(), scheduleRefresh(), AuthUser additive-optional)
- `libs/core/models/product.model.ts` (NEW — D33 Product promotion)
- `libs/core/index.ts` (EXTEND — barrel exports for the new public surface)
- `apps/mfe-auth/src/app/auth-api.service.ts` (NEW — send/verify/logout/me wrapper) **or** `libs/core/services/auth-api.service.ts` — see §3.5 placement ruling
- `apps/mfe-auth/src/app/{login,signup,otp-verify}.component.ts` (EDIT — real flow)
- `apps/mfe-catalog/src/app/smart-picker/services/category.service.ts` (EDIT — DISCREPANCY-1 + remove authHeaders())
- `apps/shell/src/app/app.config.ts` (EDIT — register 3 interceptors + APP_INITIALIZER bootstrap)
- ALL 6 `apps/mfe-*/src/main.ts` (EDIT — register the same 3 interceptors for dev-serve)
- NEW `*.spec.ts` for every new service/interceptor (HttpTestingController)

### Scope OUT (defer / STOP)
- Any `backend/` change → **STOP** (§9). Backend surface is LOCKED.
- AI prompts / `ai_ops/` → AI lane.
- Infra hosting / CSP / cluster → carried to cutover week (SP07).
- Page data wiring for dashboard/onboarding/catalog-form/images/preview/export/pricing → Waves B/C/D.
- `app.routes.ts` route tables → frozen.
- Pricing client-vs-server resolution → Wave D (DECISION-1 noted only).

---

## 2. Ground-truth contract (cited file:line — NO invented shapes)

All paths under `/api/v1`. Verified on `origin/develop`.

### 2.1 iam — `backend/app/modules/iam/schemas.py` + `router.py`

| Endpoint | Method · Path (`router.py` L) | Request schema | Response schema (`schemas.py` L) |
|---|---|---|---|
| send OTP | `POST /auth/otp/send` (L47, 202) | `SendOtpRequest{phone}` (L31-34) | `SendOtpResponse{request_id: str}` (L37-40) |
| verify OTP | `POST /auth/otp/verify` (L66) | `VerifyOtpRequest{phone, otp}` (L43-47) | `VerifyOtpResponse{access_token: str, expires_in: int, token_type: 'bearer'}` (L50-59) + `Set-Cookie: refresh_token` |
| refresh | `POST /auth/refresh` (L94) | (no body — cookie is input) | `RefreshResponse{access_token, expires_in, token_type}` (L62-71) + rotated `Set-Cookie` |
| logout | `POST /auth/logout` (L136, 204) | (no body — cookie) | `204` + cookie clear (max_age=0) |
| me | `GET /auth/me` (L162) | — | `MeResponse{user_id: UUID, phone: str, plan: 'free', created_at: datetime, last_login_at: datetime\|null}` (L74-83) |

**Phone regex (LOCKED):** `SendOtpRequest.phone` / `VerifyOtpRequest.phone` = `^\+[1-9]\d{1,14}$` (generic E.164, e.g. `+919876543210`). `VerifyOtpRequest.otp` = `^\d{6}$` (6 digits).

**Cookie (verified `router.py` L63-65, L70-89):** `refresh_token`; `Path=/api/v1/auth`; `Domain=.mesell.xyz`; `Secure`; `HttpOnly`; `SameSite=strict`. **R-W6-7 RESOLVED** — the live `Path` is `/api/v1/auth`, NOT the memo's stale `/auth`. The frontend NEVER touches this cookie (HttpOnly); the browser auto-attaches it to `/api/v1/auth/*` requests when `withCredentials: true`.

### 2.2 Error envelope (LOCKED) — `backend/app/core/errors.py` L125-138

Every error response is `{ detail: string, code: string, validation_message_id: string, request_id: string }`. The `errorInterceptor` (§3.3) MUST type against ALL FOUR keys — the MASTER PLAN's `{detail}`-only assumption is INCOMPLETE; the as-built envelope is richer. 422 validation adds an `errors[]` array (L163) for field enumeration — type it `errors?: unknown[]`.

### 2.3 catalog `ProductResponse` (D33 Product source) — `backend/app/modules/catalog/schemas.py` L113-130

```
ProductResponse:
  id: UUID            -> string
  catalog_id: UUID    -> string
  category_id: UUID   -> string
  name: str | None    -> string | null
  status: Literal['draft','ready']  -> 'draft' | 'ready'
  fields: dict[str,Any]             -> Record<string, unknown>
  ai_suggestions: dict[str,Any]|None = None  -> Record<string, unknown> | null
  created_at: datetime  -> string  (ISO-8601 TZ)
  updated_at: datetime  -> string
```

### 2.4 catalog create body (DISCREPANCY-1 target) — `schemas.py` L37-51

`CreateProductRequest{ catalog_id: UUID|null = null, category_id: UUID, name: str|null = null }` (`extra='forbid'`). smart-picker currently sends `{category_id}` only → VALID (catalog_id null → backend auto-creates a default-named catalog; name null → "Untitled product"). The RESPONSE is `ProductResponse{id,…}`; the `id` is a **product** id. The navigation target `/catalogs/:id/edit` is correct (the edit route loads a product by id).

### 2.5 As-built frontend ground truth (what must change)

- `libs/core/services/auth.service.ts` — `AuthUser{id: number, name: string, phone: string}` (L3-7); signals `_token`/`_user`; `setSession/logout/getToken`; NO `bootstrap`/`scheduleRefresh`; NO HttpClient. **MISMATCH: backend `MeResponse` has NO `id:number` and NO `name`** — it has `user_id: UUID(string)`, `phone`, `plan`, `created_at`, `last_login_at`. §4 reconciles this additively.
- `libs/core/index.ts` — exports `AuthService`, `AuthUser` (type), `authGuard` only.
- `apps/shell/src/app/app.config.ts` — has `provideHttpClient(withFetch())` (L20) with NO interceptors + a Wave-7 deferral comment. mee-ui deep-imported (L9, L22). **The Wave-7 comment becomes Wave-6-actual now.**
- All 6 remote `main.ts`: `provideHttpClient(withFetch())` EXISTS only in `mfe-catalog/src/main.ts` (L18, L32). The other 5 (pricing/export/onboarding/dashboard/auth) have NO `provideHttpClient` — they bootstrap with `provideRouter` + `provideAnimationsAsync` only.
- `mfe-catalog/.../category.service.ts` — `authHeaders()` helper (L47-52); `suggest()` (L96-105) calls it; `selectCategory()` (L119-130) posts to `/api/v1/catalogs` (BUG) and uses `authHeaders()`.
- `mfe-auth` components: `login.onSubmit` (L94-100) validates `/^[6-9]\d{9}$/` (10-digit, NO +91) then `setTimeout(1500)`→`navigate(['/otp-verify'])` — **passes NO phone**. `otp-verify.onSubmit` (L143-156) `setTimeout(1500)`→`setSession('mock-token',{id:1,name:'Seller',phone:'+91XXXXXXXXXX'})`→`navigate(['/dashboard'])`. `signup` mirrors login.

---

## 3. The build — §3.x in dependency order

### 3.0 D33 Product model (FIRST — downstream waves consume it)
`libs/core/models/product.model.ts` (NEW): `export interface Product` per §2.3 transcription. `export type ProductStatus = 'draft' | 'ready'`. Add to `libs/core/index.ts`: `export type { Product, ProductStatus } from './models/product.model';`. **`export type` — erased at runtime, zero chunk cost** (R-W6-3 mitigation). This is the §2.3-row-1 D33 promotion. (The `AuthUser` extension is §4.)

### 3.1 `jwtInterceptor` — `libs/core/interceptors/jwt.interceptor.ts` (NEW)
Functional `HttpInterceptorFn`. `const token = inject(AuthService).getToken();` → if present, `req.clone({ setHeaders: { Authorization: \`Bearer ${token}\` } })`; else pass through. **SKIP the `/api/v1/auth/*` send/verify/refresh/logout calls** — those are public/cookie-auth and must NOT carry a stale Bearer (guard with a `req.url.includes('/api/v1/auth/')` early return, OR rely on token being null pre-login; explicit skip is safer and documented). This REPLACES the per-service `authHeaders()` helper everywhere.

### 3.2 `refreshInterceptor` — `libs/core/interceptors/refresh.interceptor.ts` (NEW)
On `401` from a NON-`/auth/*` request: call `POST /api/v1/auth/refresh` with `withCredentials: true` (cookie auto-sent). On refresh success → `AuthService.setSession(newToken, currentUser)` (preserve user; or re-hydrate via `/me` if user is null) → retry the original request with the new Bearer. On refresh FAILURE (401 from /refresh) → `AuthService.logout()` + `Router.navigate(['/login'])` + rethrow. **Single-flight gate (R-W6-4):** a `BehaviorSubject<string|null>` (or a shared `refresh$` observable) so N concurrent 401s share ONE in-flight `/auth/refresh`; queued requests wait on the same refresh and retry with the resulting token. Do NOT fire N refreshes. **Never** loop: a 401 on `/auth/refresh` itself must NOT re-enter refresh (the `/auth/*` skip from §3.1 + an explicit "already refreshing /auth/refresh" guard covers this).

### 3.3 `errorInterceptor` — `libs/core/interceptors/error.interceptor.ts` (NEW)
LOWEST priority (last in chain). `catchError` → map `HttpErrorResponse` to the §2.2 typed envelope `{detail, code, validation_message_id, request_id, errors?}` → push to `ErrorService` (non-blocking, does NOT swallow — `rethrow` after recording so callers' own `catchError` matrices still run). Does NOT handle 401 (that's refresh's job — error interceptor sees only what refresh already rethrew).

### 3.4 `ApiClient` / `ErrorService` / `NetworkService` — `libs/core/services/*` (NEW)
- **`ApiClient`** (`providedIn:'root'`): typed thin wrapper over HttpClient — `get<T>(path, opts?)`, `post<T>(path, body, opts?)`, `patch<T>`, `delete<T>`. Centralises the `/api/v1` base (paths passed WITHOUT the prefix OR with it — pick ONE convention and document; recommend callers pass the FULL `/api/v1/...` path to match the existing CategoryService literal, minimising churn). `retryOn503` opt-in flag per the §4-LOCKED design (memory `section_4_locked.md`): a bounded retry (e.g. 2×, backoff) ONLY when the caller opts in. Downstream waves' services use ApiClient; this slice wires it but does not force-migrate CategoryService's raw HttpClient (CategoryService keeps its own typed call — re-point + de-header only; an ApiClient migration there is OPTIONAL and must not expand scope).
- **`ErrorService`** (`providedIn:'root'`): a signal/subject surface the errorInterceptor writes to; the shell (or any component) reads it to render a global error affordance. Holds the last typed envelope + a clear() method. Does NOT itself show a toast (UI layer decides).
- **`NetworkService`** (`providedIn:'root'`): `online` signal from `window.navigator.onLine` + `online`/`offline` events. Surfaces offline so the graceful-degradation pattern (§6) can render an offline banner instead of a confusing 0-status error.

### 3.5 `AuthApiService` — placement ruling
Place at **`libs/core/services/auth-api.service.ts`** (`providedIn:'root'`), NOT in mfe-auth. RATIONALE: `bootstrap()` (§4) lives in `@mesell/core` `AuthService` and calls refresh+me; logout is callable anywhere; refresh is called by the refreshInterceptor (also core). Keeping the HTTP auth calls in core avoids a circular shell→remote dependency and keeps the singleton chunk self-contained. Methods: `sendOtp(phone): Observable<SendOtpResponse>`, `verifyOtp(phone, otp): Observable<VerifyOtpResponse>` (`withCredentials: true`), `refresh(): Observable<RefreshResponse>` (`withCredentials: true`), `logout(): Observable<void>` (`withCredentials: true`), `me(): Observable<MeResponse>`. **`withCredentials: true` ONLY on verify/refresh/logout** (the refresh-cookie path) — NOT on send, NOT on me (R-W6-5 — over-applying `withCredentials` is a CORS-credentials surface). Add `MeResponse`/`SendOtpResponse`/`VerifyOtpResponse`/`RefreshResponse` as TS interfaces in core (transcribed §2.1) — promote `MeResponse` to core (consumed by bootstrap + onboarding + dashboard greeting per MASTER PLAN §2.2) but keep the others auth-infra-local to the AuthApiService file (single consumer).

### 3.6 Interceptor registration (shell + all 6 remotes)
Chain order **jwt → refresh → error**:
```
provideHttpClient(withFetch(), withInterceptors([jwtInterceptor, refreshInterceptor, errorInterceptor]))
```
- **`apps/shell/src/app/app.config.ts`**: replace the L20 `provideHttpClient(withFetch())` + delete the Wave-7 deferral comment (L16-19) — it is now actual. Add the `APP_INITIALIZER` (or `provideAppInitializer`) that calls `AuthService.bootstrap()` (§4). app.config is MY domain — the named exception granted to this spec.
- **mfe-catalog main.ts**: it already has `provideHttpClient(withFetch())` (L32) — add the `withInterceptors([...])`. Import the 3 interceptors from `@mesell/core`.
- **5 remotes WITHOUT HttpClient** (pricing/export/onboarding/dashboard/auth main.ts): ADD `provideHttpClient(withFetch(), withInterceptors([jwtInterceptor, refreshInterceptor, errorInterceptor]))` to each `providers[]`. NOTE: in FEDERATED mode the remote's main.ts providers are NOT used (only the shell root injector + route providers apply — proven #101) — so this registration is for DEV-SERVE standalone parity. Both sites needed (the #101 ruling).
- **Sheriff-reachability (R-SP3-1, P0):** importing the interceptors from `@mesell/core` into a remote main.ts ADDS `@mesell/core` to that remote's import graph. Each remote main.ts MUST still route to ALL its exposes (already true post-cutover) AND now also pulls core via the interceptor import. After build, RE-RUN the §6.G singleton grep per touched remote (no second `_mesell_core.js`, interceptors are functional fns not classes — low risk, but VERIFY).

---

## 4. `AuthUser` extension (DECISION-3 — ADDITIVE-OPTIONAL) + `bootstrap()` / `scheduleRefresh()`

### 4.1 AuthUser reconciliation (the load-bearing call)
The current `AuthUser{id:number, name:string, phone:string}` does NOT match `MeResponse`. Per DECISION-3 (additive-OPTIONAL, no remote breaks):

```ts
export interface AuthUser {
  // legacy fields kept OPTIONAL so existing inline constructors (otp-verify mock) don't break
  id?: number;            // legacy mock field; real backend has no numeric id — see user_id
  name?: string;          // legacy mock field; backend MeResponse has no name (V1)
  phone: string;          // REQUIRED — present in both legacy and MeResponse
  // additive from MeResponse (DECISION-3)
  user_id?: string;       // MeResponse.user_id (UUID) — the real identity key
  plan?: 'free';          // MeResponse.plan
  created_at?: string;    // MeResponse.created_at (ISO-8601)
  last_login_at?: string | null;  // MeResponse.last_login_at
}
```
**Why optional, not a clean replace:** `otp-verify.component.ts` (and the SP06 C4 smoke spec) construct `AuthUser` inline with `{id, name, phone}`. Making `id`/`name` required-removed would break those at compile time + churn the SP06 smoke. ADDITIVE-OPTIONAL = zero breakage, real fields available. The real-login path (§4.3) populates `user_id/plan/created_at` from `/me`; the mock `id/name` fade out as otp-verify migrates to the real flow. **STOP if a clean replace is attempted** — DECISION-3 is additive-optional, not a breaking change.

### 4.2 `scheduleRefresh()`
After `setSession`, schedule a proactive refresh BEFORE access-token expiry. The token TTL is `expires_in` (seconds) from verify/refresh responses — `AuthService` reads it and sets a timer for `(expires_in - 30)s` (FE-D6: frontend trusts `expires_in`, no env coupling) that calls `AuthApiService.refresh()` → on success `setSession(newToken, user)` + reschedule. Clear the timer on `logout()`. Guard against SSR/zoneless edge cases (use `setTimeout`; clear in logout). This is the silent-refresh path; the reactive 401→refresh (§3.2) is the safety net.

### 4.3 `bootstrap()`
On app init (shell APP_INITIALIZER): call `AuthApiService.refresh()` (cookie auto-sent, `withCredentials`). On SUCCESS → `setSession(access_token, <user-from-me>)` (call `me()` to hydrate `AuthUser` with `user_id/phone/plan/created_at`) + `scheduleRefresh()`. On FAILURE (401 — no/expired cookie) → stay logged-out (no redirect from bootstrap; the route guard handles unauth navigation). This is the page-RELOAD survival path (FE-D5: no token in storage → re-derive from the HttpOnly cookie). bootstrap MUST resolve (never reject) so app init does not hang — swallow the refresh 401 into a logged-out state.

---

## 5. Real OTP login wiring (mfe-auth) + DISCREPANCY-1

### 5.1 login / signup (`login.component.ts`, `signup.component.ts`)
Replace the `setTimeout(1500)→navigate` mock. On submit: `AuthApiService.sendOtp(phone)`. **Phone normalisation:** the form validates `/^[6-9]\d{9}$/` (10-digit, no prefix); backend requires E.164 `+91...`. PREPEND `+91` before the call: `sendOtp('+91' + raw)`. On success (202 `{request_id}`) → navigate to `/otp-verify` **carrying the phone** (and optionally request_id) — use Router state (`navigate(['/otp-verify'], { state: { phone } })`) OR a small shared signal on AuthService (`pendingPhone`). RECOMMEND Router state to avoid widening AuthService. Error matrix: 400 (bad phone) → inline field error; 429 (rate limit 3/h) → "Too many attempts, try later" banner; 5xx → retry affordance. signup mirrors login (same send flow; V1 has no separate signup endpoint — both routes call send).

### 5.2 otp-verify (`otp-verify.component.ts`)
Replace `setTimeout→setSession('mock-token',...)`. Read the phone from Router state (or AuthService.pendingPhone). On submit: `AuthApiService.verifyOtp(phone, otp)` (`withCredentials: true`). On success (`VerifyOtpResponse{access_token, expires_in}`) → call `me()` to hydrate the user → `AuthService.setSession(access_token, user)` (the C4 write path, now REAL token) → `scheduleRefresh()` (or let setSession trigger it) → `navigate(['/dashboard'])`. The `Set-Cookie: refresh_token` is handled by the browser (requires `withCredentials` — already on verify). Error matrix: 400 (bad/expired otp) → inline "Invalid or expired code"; 401 → same; 429 → resend cooldown. PRESERVE the existing `setInterval` resend-countdown (D18 timer pattern — don't rewrite); wire `resendOtp()` to `sendOtp(phone)`. PRESERVE `ngOnDestroy` clearInterval.

### 5.3 logout
Wherever logout fires (shell chrome / profile — NOT this slice's component, but the AuthApiService method is built here): `AuthApiService.logout()` (`withCredentials`) → `AuthService.logout()` (clears in-memory token + cancels scheduleRefresh timer). Idempotent (backend 204 both times).

### 5.4 DISCREPANCY-1 + authHeaders() removal (CategoryService)
In `apps/mfe-catalog/src/app/smart-picker/services/category.service.ts`:
- **Re-point** `selectCategory()`: `POST /api/v1/catalogs` → `POST /api/v1/products` (L121). Body stays `{ category_id: categoryId }` (valid against `CreateProductRequest` §2.4 — catalog_id null auto-creates). Response stays `{id}` (it's now a product id; the `/catalogs/:id/edit` navigation is correct). Update the JSDoc (L107-118) to say `POST /products`.
- **Remove `authHeaders()`** (L47-52) and the `headers: this.authHeaders()` options on `suggest()` (L100) and `selectCategory()` (L122). The global `jwtInterceptor` now attaches Bearer. Remove the now-unused `HttpHeaders` import (L2) and the Wave-7 migration note (L18-22) — it is now done. KEEP the error matrix `handleSuggestError` and the `AuthService` injection (still used for the 401→logout in the matrix — though with refreshInterceptor live, the 401 path may rarely fire; keep the matrix as the in-component fallback, it is harmless and contract-correct).
- The existing CategoryService specs MUST be updated to assert the new URL (`/api/v1/products`) and the ABSENCE of a manual Authorization header (the interceptor adds it; HttpTestingController on the service-under-test alone won't see the interceptor unless the test provides it — assert the request has NO manual header, and add a separate jwtInterceptor spec).

---

## 6. Graceful-degradation pattern (DEFINED ONCE — later waves COPY this verbatim)

> **R-W6-1 (P0). The merge gate REJECTS any wired service that removes its mock without this pattern.**

**The pattern (canonical, from #101 CategoryService, generalised):**

1. **Every wired `*-api.service.ts` method has a `catchError` error matrix** mapping `HttpErrorResponse.status` to a typed outcome:
   - **401** → handled by `refreshInterceptor` (retry) → only reaches the service if refresh ALSO failed → service's matrix calls `AuthService.logout()` + returns `EMPTY`/fallback (session invalidated).
   - **402** (plan-guard quota) → return a contract-shaped fallback (empty list / `fallback_offered: true`) — NEVER throw.
   - **400** (caller validation) → return `EMPTY` or surface a field error; the caller owns input validation.
   - **404** (feature-flag-off or not-found) → contract-shaped empty/fallback.
   - **5xx** (server unavailable) → contract-shaped fallback (NOT a crash).
2. **The component renders an EXPLICIT state for every outcome** — `loading` / `error` / `empty` / `data` signals. Use `MeeEmptyState` (composites) for the empty/fallback card + a retry affordance; NEVER let an unhandled throw white-screen the page. The component subscribes with `{ next, error }` and sets the error signal in `error` (defence-in-depth even though the service `catchError`s).
3. **`NetworkService.online` gates an offline banner** — when offline, render "You are offline" instead of a confusing 0-status error.
4. **`ErrorService`** receives the typed envelope from `errorInterceptor` for any global surface (e.g. a shell toast for unexpected 5xx) — non-blocking, does not replace the per-service matrix.

**Wave A's own application of the pattern:** the auth components (login/signup/otp-verify) render inline form errors + banners per §5.1/§5.2; they do not white-screen on send/verify failure. bootstrap() swallows its refresh-401 into a logged-out state (§4.3) — the canonical "backend unreachable → page-level state, not crash" for the app-init path.

**STOP condition restatement:** a wired service with NO `catchError` = automatic merge-gate REJECT (R-W6-1).

---

## 7. Branch plan (Model C — documented, NOT executed by the spec author)

Per MASTER PLAN §4.1 + proven SP01-07 Model C. The LEAD executes these at step-2 dispatch time (not the spec author, not now):

- **Integration branch:** `feature/wave6-auth-core/integration` cut from `origin/develop` tip (currently `db556b9` — RE-FETCH at dispatch; develop is busy with Gate-4 lanes). **F3-protected** via `gh api PUT .../protection` with a JSON-file body (the -f/-F mixing produces malformed payload — memory): `required_status_checks: null`, review-count 0, force-push off, deletions off.
- **Group branch:** `feature/wave6-auth-core/frontend` cut from the integration branch.
- **Worktree:** `/tmp/mesell-wt/w6a-auth-core` (or `/tmp/mesell-wt/w6a-frontend`). `pnpm install --config.dangerously-allow-all-builds=true` (~5s, extracts esbuild darwin-arm64 in the .pnpm store; do NOT panic on a failing top-level `node_modules/esbuild/bin` check — verify via `find node_modules/.pnpm -path "*@esbuild*darwin*" -name esbuild`). Run `./node_modules/.bin/ng build <project>` directly (not `pnpm build`).
- **Master tree:** NEVER branch-switch it; create branches via `git branch <name> <start>` + push, never `checkout`.
- **Founder-gate PR:** `feature/wave6-auth-core/integration` → `develop`, title `[FOUNDER GATE — DO NOT MERGE]`, **LEFT OPEN** — the lead does NOT approve it (D1). The lead DOES gate + squash-merge the `frontend` → `integration` group PR (lead-gate APPROVE comment, self-approval blocked → `gh pr merge --squash --admin`; branch delete via `gh api -X DELETE .../git/refs/heads/<branch>`).
- **5-calendar-day cap** on the open group branch (STOP / escalate per repo-mgmt §1.2).

---

## 8. Builder sequence (SERIAL — mandatory) + dispatch headers

The three specialists run SERIAL on the SAME `feature/wave6-auth-core/frontend` branch. Parallel is UNSAFE (all three touch overlapping files: service-builder creates the core surface the components import; ui-styler restyles the component templates the component-builder edits).

1. **`meesell-angular-service-builder` (session-1)** — the FOUNDATION. Builds: D33 Product model (§3.0); the 3 interceptors (§3.1-3.3); ApiClient/ErrorService/NetworkService (§3.4); AuthApiService + auth-infra interfaces (§3.5); AuthService extension — AuthUser additive-optional + bootstrap() + scheduleRefresh() (§4); interceptor registration in shell app.config + all 6 remote main.ts (§3.6); DISCREPANCY-1 re-point + authHeaders() removal in CategoryService (§5.4); ALL new `*.spec.ts` with HttpTestingController (jwt/refresh/error interceptors, ApiClient, AuthApiService send/verify/refresh/logout/me, AuthService bootstrap/scheduleRefresh, updated CategoryService specs). MUST commit the interceptor-registration changes and re-run the §6.G singleton grep.
2. **`meesell-angular-component-builder` (session-2)** — mfe-auth real flow. Edits login/signup (§5.1: real sendOtp + +91 normalisation + phone hand-off) and otp-verify (§5.2: real verifyOtp + me() hydrate + real-token setSession + resend wiring). Updates the SP06 C4 smoke spec ONLY as needed for the AuthUser additive change (the mock `{id,name,phone}` still compiles — additive-optional — so likely NO C4 change; if a change is needed, it is annotation-only — STOP and report if the C4 smoke would need its ASSERTIONS rewritten, that signals a contract drift). Renders the graceful-degradation states (§6) for the auth pages.
3. **`meesell-angular-ui-styler` (session-3)** — auth error/loading states + the global offline banner + ErrorService surface styling. Tailwind + mee-* primitives only; boundary 0 (no PrimeNG outside ui-kit). 360px + 1280px screenshots of login / otp-verify in loading + error states for the PR.

### Dispatch header template (each specialist)
```
PROJECT BOUNDARY: /Users/mugunthansrinivasan/Project/mesell. Stay inside frontend/. NO backend/ changes.
SESSION: mesell-wave6-auth-core-frontend-session-{N}
TASK: <the §-slice above for this specialist>
CONTEXT: Wave 6 Wave A foundation slice. Ground truth = spec_w6a_auth_core.md §2 (cited backend file:line). Branch feature/wave6-auth-core/frontend, worktree /tmp/mesell-wt/w6a-auth-core. The 4 founder DECISIONS are RULED (§0). Graceful-degradation pattern = §6 (MANDATORY). FE-D5 in-memory token, refresh cookie is backend-owned HttpOnly (Path=/api/v1/auth).
OUTPUT: <files + the §5 validation checklist evidence the PR template needs>
```

---

## 9. Validation checklist (the step-3 merge gate runs ALL of these, skeptical-lead, in a review worktree)

- **Builds GREEN ≤ 90 s (D12):** shell (`ng build frontend`) AND all 6 remotes (`ng build mfe-{pricing,export,onboarding,dashboard,catalog,auth}`). Record each time. Build > 90 s = STOP.
- **Full suite, NO drop:** baseline = **47 spec files on develop @ db556b9** (verified: `git ls-tree -r --name-only origin/develop -- frontend/ | grep -c '\.spec\.ts$'` = 47). New service/interceptor specs make the count MONOTONICALLY RISE. A DROP = silent test-discovery failure (SP0 cwd-glob gotcha) = HARD REJECT. Re-confirm `apps/<remote>/**/*.spec.ts` + `../apps/**` discovery globs still match. `CI=true ng test`, 0 fail / 0 skip, exit 0.
- **Boundary grep = 0:** `grep -rn "from 'primeng" frontend/apps frontend/libs --include=*.ts | grep -v libs/ui-kit/` → 0.
- **Singleton non-drift (P0, R-W6-3 / §6.G):** in EVERY remote dist that now imports interceptors from `@mesell/core` (at minimum mfe-catalog + mfe-auth + whichever remotes' main.ts pull core), prove EXACTLY ONE `_mesell_core.js` chunk; AuthService class DEFINITION lives ONLY there (not inlined into a component/interceptor chunk); interceptors are functional fns (no `class` inlining); Product/AuthUser are `export type` (erased — zero chunk). The interceptors + extended AuthUser must NOT inline into remotes. Grep the exposed-component chunks for `class AuthService` (must be 0 outside `_mesell_core.js`).
- **Interceptor-registration proof PER REMOTE:** for shell app.config + all 6 main.ts, confirm `withInterceptors([jwtInterceptor, refreshInterceptor, errorInterceptor])` present in that order (grep each file). The 5 previously-HttpClient-less remotes now have `provideHttpClient`.
- **Mock-backend contract tests for 401→refresh→retry (R-W6-11 — NO tunnel, pure-function/fake-http):** a `refresh.interceptor.spec.ts` using `HttpTestingController`: (a) a 401 on a protected call triggers exactly ONE `POST /api/v1/auth/refresh`; (b) on refresh-200 the original request is RETRIED with the new Bearer and succeeds; (c) on refresh-401 → `AuthService.logout()` called + navigate /login + original errors; (d) single-flight: TWO concurrent 401s fire ONE refresh (assert exactly one `/auth/refresh` request flush) and BOTH retry with the new token; (e) a 401 on `/auth/refresh` itself does NOT re-enter refresh (no loop). LIVE federated 401→refresh→retry smoke is a CUTOVER-WEEK item (joins SP07 R-SP7-1, joint backend+infra) — NOT a Wave A blocker.
- **`bootstrap()` spec:** refresh-200 → setSession + me() hydrate + scheduleRefresh scheduled; refresh-401 → stays logged-out, RESOLVES (never rejects).
- **AuthService spec:** AuthUser additive-optional compiles with both the legacy `{id,name,phone}` mock AND the real `{user_id,phone,plan,created_at}` shape; scheduleRefresh fires at `expires_in-30`s (fakeAsync+tick); logout cancels the timer.
- **Contract greps:** (a) `grep "of(.*).pipe(.*delay"` in any TOUCHED service = 0 (CategoryService had no delay — confirm none introduced); (b) the wired URLs match §2.1 EXACTLY (`/api/v1/auth/otp/send`, `/auth/otp/verify`, `/auth/refresh`, `/auth/logout`, `/auth/me`, `/api/v1/products` for selectCategory); (c) `localStorage`/`sessionStorage` = 0 (FE-D5); (d) `withCredentials: true` ONLY on verify/refresh/logout (grep — NOT on send, me, suggest, products).
- **TS strict + strictTemplates ON:** `tsc` app + spec EXIT 0.
- **authHeaders() removed:** `grep -rn "authHeaders" frontend/apps` = 0.
- **a11y + screenshots:** keyboard nav on login/otp forms; aria on inputs/buttons; 360px + 1280px screenshots of login + otp-verify in loading + error states (per PR template). The interceptor/service work has no visual surface (zero-visual carve-out applies to the pure-infra files); the auth-page edits DO need screenshots.
- **PR template fully filled** (no `<>` placeholders), bundle delta noted (expect a one-time `@mesell/core` interceptor-chunk add to the shell initial — like #101's +10.49 kB HttpClient infra chunk; downstream waves near-zero).
- **Gate-4 note:** record which Wave A endpoints have Gate-4 (real-Postgres CI) coverage when Gate-4 lands (pass-3 in flight). Wave A does NOT block on Gate-4 (§5.2 of MASTER PLAN).

---

## 10. STOP conditions (escalate to founder / master — do NOT paper over)

1. **ANY `backend/` change needed = STOP and report.** The backend surface is LOCKED (28 endpoints, schemas, error envelope, cookie config all verified §2). If wiring reveals a missing/wrong endpoint, that is a cross-lead memo to backend, NOT a backend edit by this slice.
2. **Any contract discrepancy BEYOND the 3 known (DISCREPANCY-1 already resolved by DECISION-2; the `Decimal` pricing ambiguity is Wave D; the `PaginatedProductsResponse.items` vs MASTER-PLAN's `products` naming is Wave B dashboard) = STOP.** A NEW 4xx/shape surprise at runtime → STOP the slice, raise a backend memo, do NOT add a client-side shim (§5.3 / R-W6-2).
   - **Pre-flagged Wave-B doc-nit (NOT a Wave A blocker, recorded for the Wave B spec):** MASTER PLAN §1.2 row 26 says `DashboardResponse{products[], total, page}`; the as-built schema is `PaginatedProductsResponse{items[], total, page, limit}` (catalog/schemas.py L230-238). `items` not `products`. Correct it in the Wave B spec; flag the master-plan row as a transcription nit.
3. **Build > 90 s (D12)** — even with MF now live, escalate.
4. **TS strict accidentally disabled.**
5. **Singleton §6.G grep shows a duplicated `@mesell/core` chunk** (interceptors or AuthUser inlined into a remote) = P0 reject (R-W6-3).
6. **Any wired service shipped without a `catchError` matrix** = automatic reject (R-W6-1).
7. **A clean (breaking) AuthUser replace attempted** instead of additive-optional = STOP (violates DECISION-3).
8. **The SP06 C4 smoke would need its ASSERTIONS (not just annotations) rewritten** to pass with the new AuthUser = signals an unexpected contract drift = STOP and report.
9. **`feature/wave6-auth-core/frontend` open > 5 calendar days** unmerged.
10. **A refresh-loop** (401 on /auth/refresh re-entering refresh) observed in the interceptor spec = design defect, fix before merge.

---

## 11. Open ambiguities + ground-truth resolutions (resolved here, NOT punted)

| # | Ambiguity | Resolution (ground-truth) |
|---|---|---|
| A1 | MASTER PLAN says cookie `Path=/auth`; memo says same | RESOLVED: live `Path=/api/v1/auth` (router.py L64). R-W6-7 closed. Use `/api/v1/auth/*` for `withCredentials` scoping. |
| A2 | Error envelope `{detail}` only? | RESOLVED: it is `{detail, code, validation_message_id, request_id}` (+`errors?[]` on 422) per errors.py L125-138. errorInterceptor types all 4. |
| A3 | AuthUser `id:number`+`name` vs MeResponse | RESOLVED: backend has NEITHER (only `user_id:UUID`, `phone`, `plan`, `created_at`, `last_login_at`). DECISION-3 additive-OPTIONAL: keep legacy `id?/name?` optional, ADD `user_id?/plan?/created_at?/last_login_at?`, `phone` stays required. §4.1. |
| A4 | Does login pass phone to otp-verify? | RESOLVED: NO (login.onSubmit navigates with no state, L99). The spec ADDS phone hand-off via Router state (§5.1). |
| A5 | Login form is 10-digit, backend is E.164 | RESOLVED: prepend `+91` before sendOtp (§5.1). The form regex `/^[6-9]\d{9}$/` stays; normalisation happens at the service-call boundary. |
| A6 | Where does AuthApiService live? | RESOLVED: `libs/core/services/auth-api.service.ts` (core, not mfe-auth) — bootstrap+refresh are core-owned; avoids shell→remote circular dep (§3.5). |
| A7 | Does CategoryService migrate to ApiClient? | RESOLVED: NO — re-point URL + remove authHeaders only; ApiClient migration there is OPTIONAL and out-of-scope (don't expand). CategoryService keeps its typed raw HttpClient call (§5.4). |
| A8 | `selectCategory` body valid against `POST /products`? | RESOLVED: YES — `{category_id}` is valid `CreateProductRequest` (catalog_id null auto-creates, name null defaults). §2.4. Response `id` is a product id; `/catalogs/:id/edit` nav is correct. |
| A9 | Does `withFetch()` support `withCredentials`? | RESOLVED: yes — `withCredentials` is a per-request `HttpClient` option, orthogonal to the fetch backend. Scope it per-call (verify/refresh/logout), NOT globally (R-W6-5). |
| A10 | Wave6 plan path: prompt said `docs/plans/wave6_api_wiring/MASTER_PLAN.md`, missing locally | RESOLVED: it EXISTS on `origin/develop` @ `db556b9` (#109); local develop was behind. NOT a missing-doc blocker. (Flag: re-sync local develop before any git execution.) |
| A11 | MASTER PLAN §7 still DRAFT despite rulings | The 4 DECISIONs are RULED (founder, 2026-06-11). A separate docs chore (lead, fast-mode) flips §7 DRAFT→RULED + adds a revision row. NOT part of this build slice. |

---

## 12. Cross-lead memos to open (lead, at dispatch — recorded, not yet filed)

- **→ backend (`meesell-backend-coordinator`):** confirm the LIVE `Set-Cookie` header on verify/refresh matches `refresh_token; Domain=.mesell.xyz; Path=/api/v1/auth; HttpOnly; Secure; SameSite=Strict` AND that CORS responds `Access-Control-Allow-Credentials: true` + `Access-Control-Allow-Origin` echoes the shell origin (not `*`, which is incompatible with credentials). R-W6-7. (The schema/router are verified; the CORS+credentials runtime is the open item — it's an infra+backend live-config check, gated to cutover-week smoke but memo now so it's not a surprise.)
- **→ infra (`meesell-infra-builder`):** the 401→refresh→retry LIVE smoke needs a reachable dev env with the refresh cookie crossing `dev.mesell.xyz → api.mesell.xyz`; piggyback on the SP07 cutover-week CSP smoke (R-SP7-1). Note CSP `connect-src` must allow `api.mesell.xyz` for the refresh call.
- **→ ai (`meesell-ai-coordinator`):** NONE for Wave A (AI boundary is Wave C autofill / Wave D image-precheck — re-read `feature_board_ai.md` before those waves per MASTER PLAN §6).
