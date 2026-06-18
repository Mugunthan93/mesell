# Google Sign-In — FRONTEND Design Document

**Status:** DRAFT — for founder review. NO code written.
**Author:** meesell-frontend-coordinator (Frontend Lead)
**Date:** 2026-06-18
**Companion doc:** `docs/plans/google_auth/GOOGLE_AUTH_DESIGN_BACKEND.md` (authored in parallel — every contract here marked **[RECONCILE-BE]** must be agreed against it before any code).
**Mode:** Design only. This document does not change behaviour; it proposes it.

---

## 0. Scope, founder-locked decisions, and grounding facts

### 0.1 Founder-locked decisions (designed to, not re-litigated)

1. **DUAL IDENTITY** — a user may sign up / log in with **EITHER** phone OTP **OR** Google. The Google button therefore appears on **both** `/login` and `/signup`, alongside the existing phone form.
2. **OAUTH FLOW = Google Identity Services (GIS) ID-token.** The Google button (or One-Tap) returns a `credential` (a Google-issued **ID token**, a JWT). The frontend POSTs that credential to a new backend endpoint. The backend verifies it, returns `access_token` + `expires_in`, and sets the HttpOnly refresh cookie — **exactly like the existing OTP verify path**. After success the FE fetches `/me` and calls `AuthService.setSession` + `scheduleRefresh` — **identical to the current otp-verify success path**.

### 0.2 As-built facts this design is grounded in (verified 2026-06-18)

| Fact | Source |
|---|---|
| Auth pages live in the federated remote `mfe-auth` (port 4206), exposing `./LoginComponent`, `./SignupComponent`, `./OtpVerifyComponent`. | `apps/mfe-auth/federation.config.js`, `public-api.ts` |
| Login/signup currently inject only `Router` + `AuthApiService`; they call `sendOtp(phone)` then navigate to `/otp-verify` with `state:{phone}`. They do **not** touch `AuthService`. | `login.component.ts`, `signup.component.ts` |
| The **success-wiring lives entirely in `otp-verify.component.ts`** (`onSubmit`): `verifyOtp → me → setSession(token, user) → scheduleRefresh → navigate('/dashboard')`. This is the canonical pattern the Google path must mirror. | `otp-verify.component.ts` L202–251 |
| `AuthApiService` (in `@mesell/core`, **not** mfe-auth) owns all auth HTTP. `verifyOtp`/`refresh`/`logout` use `withCredentials:true`; `sendOtp`/`me` do not. All paths are `${environment.apiBase}/api/v1/auth/...`. | `auth-api.service.ts` |
| `AuthService` (`@mesell/core`, `providedIn:'root'`, the **federation singleton**) holds the in-memory token. `setSession(token, user, expiresIn?)` auto-pairs `scheduleRefresh` when `expiresIn` is supplied. | `auth.service.ts` L47–112 |
| `setSession` auto-schedules refresh only when the 3rd arg is given. otp-verify currently uses the **2-arg** form and calls `scheduleRefresh(resp.expires_in)` explicitly. | `auth.service.ts` L77–83 |
| Onboarding gate is **Path B**: `MeResponse.onboarding_complete` (always present, default `false`). The **shell** reads it to show/hide the Onboarding nav-item. otp-verify navigates unconditionally to `/dashboard`; the onboarding component itself navigates to `/dashboard` after submit. There is currently **no post-login redirect to `/onboarding`**. | `auth.service.ts` L30–32, `shell.component.ts` L80, `otp-verify.component.ts` L219/233 |
| Environment config is `@mesell/env` (`environment.ts` dev / `environment.prod.ts` prod, swapped via `fileReplacements`). Today it carries only `production`, `name`, `apiBase`. There is **no** secrets/runtime-config injection — values are compile-time constants. | `libs/env/*` |
| `@mesell/core` is `shareAll({singleton:true})` in every remote's federation config — a single AuthService/AuthApiService instance is shared across boundaries. | all `federation.config.js` |
| UI primitives available: `MeeButton` (`@mesell/ui-kit`, inputs `label/variant/size/loading/disabled/fullWidth/icon`, output `clicked`), `MeeAlertBanner` (`@mesell/composites`, inputs `variant`('error'|'warning'|'info'|'success') + `message`, `role="alert"` + focus-on-appear), `AuthLayoutComponent` (`@mesell/composites`). PrimeNG is **forbidden outside `libs/ui-kit/`**. | grep + component reads |

### 0.3 Constraints inherited (non-negotiable)

- Standalone components only; OnPush default; Reactive Forms; TypeScript strict + strictTemplates ON.
- No NgRx/state library; services + RxJS + signals.
- FE-D5: access token in-memory only, **never** localStorage/sessionStorage. Google credential must **never** be persisted either — it is consumed once and discarded.
- PrimeNG imports stay inside `libs/ui-kit/`.
- No third-party Angular Google-auth wrapper library (e.g. `@abacritt/angularx-social-login`) — we load **GIS directly** to keep the federation share-graph and CSP surface minimal. (Open question OQ-7.)

---

## A. GIS INTEGRATION APPROACH

### A.1 Loading the GIS script in a federated remote

**Decision: lazy, programmatic script injection from inside the auth remote — NOT a `<script>` in `index.html`.**

Rationale:
- The auth pages are a **federated remote**. The shell's `index.html` is the live document at runtime; the remote's `apps/mfe-auth/src/index.html` is used **only** in standalone dev-serve mode (per memory: a remote built by `@angular/build:application` needs its own index.html, but it is not the runtime document when federated). Putting `<script src="https://accounts.google.com/gsi/client">` in either index.html is wrong: in the shell it loads GIS on **every** page (dashboard, catalog, etc.) where it is never used; in the remote index.html it never runs in federated mode.
- GIS is only needed on `/login` and `/signup`. Lazy-load it when one of those components initialises.

**Mechanism: a small injectable loader service, `GoogleIdentityService`, placed in `@mesell/core`** (alongside `AuthService`/`AuthApiService`) so:
- it is a federation singleton (the GIS `<script>` is injected **once** for the whole app, even if the user bounces login↔signup);
- it has no PrimeNG/UI dependency, so it belongs in core, not ui-kit;
- both `LoginComponent` and `SignupComponent` (and any future caller) share one instance and one in-flight load promise.

Loader responsibilities:
1. `load(): Promise<void>` — idempotent. If `window.google?.accounts?.id` already exists, resolve immediately. Otherwise inject `<script src="https://accounts.google.com/gsi/client" async defer>` into `document.head`, resolve on `onload`, reject on `onerror`. Guard against double-injection with an in-flight promise field.
2. `initialize(callback)` — calls `google.accounts.id.initialize({ client_id, callback, use_fedcm_for_prompt: true, auto_select: false })`. Idempotent per page mount.
3. `renderButton(el: HTMLElement, opts)` — calls `google.accounts.id.renderButton(el, {...})`.
4. (Optional, OQ-2) `prompt()` — One-Tap.
5. `cancel()` / cleanup helper for `ngOnDestroy`.

The service depends on `environment` (`@mesell/env`) for the client id (§E) and is `providedIn:'root'`.

**Window typing:** add a minimal ambient `.d.ts` (e.g. `libs/core/types/google-gsi.d.ts`) declaring the slice of `window.google.accounts.id` we use (`initialize`, `renderButton`, `prompt`, `disableAutoSelect`). We do **not** pull in `@types/google.accounts` to avoid a global-type footprint conflict across the federated builds — a hand-rolled minimal declaration is safer and smaller. (Confirm in OQ-7.)

### A.2 Official Google button vs One-Tap

**Decision for V1: render the official Google button via `renderButton` on both pages. One-Tap (`prompt()`) is DEFERRED** (OQ-2).

Rationale:
- The official rendered button is the lowest-friction, most predictable, Google-branding-compliant option, and it works on mobile webviews where One-Tap can be flaky.
- One-Tap (the auto-prompt bubble) is a nice add-on but introduces FedCM/third-party-cookie edge cases and a more complex consent UX. Defer until the basic flow is proven in staging.
- Both produce the **same** `credential` callback shape, so adding One-Tap later is additive (call `prompt()` after `initialize`) with zero contract change.

`renderButton` options: `{ type:'standard', theme:'outline', size:'large', text:'continue_with', shape:'pill', logo_alignment:'left', width: <container px> }`. `text` differs subtly per page — `signup_with` on `/signup`, `continue_with` (or `signin_with`) on `/login` — purely cosmetic; the backend treats both identically (dual-identity upsert).

### A.3 The credential callback

`initialize({ callback })` receives `(response: { credential: string; select_by: string })`. `response.credential` is the Google ID-token JWT.

Because the GIS callback fires **outside Angular's zone/change-detection context**, the component callback must:
- be a bound arrow/closure capturing `this`;
- marshal back into Angular reactivity by setting **signals** (the components are signal-based and OnPush — signal writes schedule CD correctly even from outside the zone in zoneless mode, which this app uses);
- hand the credential to the shared success-wiring helper (§C) which runs the RxJS pipeline via `AuthApiService`.

### A.4 SSR / federation caveats and cleanup

- **No SSR** in this app (CSR PWA), so `document`/`window` access in the loader is safe — but the loader still guards `typeof window === 'undefined'` defensively (cheap insurance if SSR is ever added).
- **Federation:** GIS is **not** an npm dependency, so it does **not** enter the Native-Federation share graph at all — zero impact on `shareAll`, zero `skip` list change in `federation.config.js`. The script is a runtime browser asset fetched from `accounts.google.com`. This is the cleanest possible federation story.
- **Cleanup on `ngOnDestroy`:** call `google.accounts.id.cancel()` (dismisses any pending One-Tap) and `google.accounts.id.disableAutoSelect()` is **not** called on destroy (it would wipe the user's auto-select preference); we only call it on explicit logout if One-Tap is later enabled. The injected `<script>` is **left in the DOM** (idempotent loader means re-mounting login reuses it — removing it would force re-download).
- **CSP:** federated remotes plus GIS introduce new external origins. This is a cross-doc dependency with infra (Sub-plan 7 / C-CSP-1). See §E.3.

---

## B. CONTRACT WITH BACKEND  **[RECONCILE-BE]**

### B.1 New endpoint

```
POST /api/v1/auth/google/verify
Body: { "credential": "<google-id-token-jwt>" }
Headers: Content-Type: application/json
withCredentials: true   ← response sets HttpOnly refresh_token cookie (Path=/api/v1/auth), exactly like otp/verify
```

**Response shape — REUSE `VerifyOtpResponse` verbatim** (no new type):

```ts
interface VerifyOtpResponse {
  access_token: string;
  expires_in: number;
  token_type: 'bearer';
}
```

Reusing this type is deliberate: the success-wiring (§C) becomes literally identical to the OTP path and the `/me` hydration is unchanged. **[RECONCILE-BE]** — backend must return the same field names/types and set the same cookie. If backend wants to signal "new user just created via Google" (for onboarding routing, §F), that should ride on `GET /auth/me` (e.g. `onboarding_complete:false`), **not** be added to this response — keep the verify response symmetric with OTP. Flag this preference to backend.

### B.2 New `AuthApiService` method

Added to `libs/core/services/auth-api.service.ts` (the existing auth HTTP singleton — **not** mfe-auth, to preserve the no-circular-dep rule):

```ts
// New path constant alongside AUTH_OTP_VERIFY etc.
const AUTH_GOOGLE_VERIFY = `${environment.apiBase}/api/v1/auth/google/verify`;

/**
 * POST /api/v1/auth/google/verify
 * credential = the Google Identity Services ID token (JWT) from the GIS callback.
 * withCredentials: true — response sets the HttpOnly refresh_token cookie,
 * identical to verifyOtp(). Reuses VerifyOtpResponse (dual-identity, symmetric).
 */
googleVerify(credential: string): Observable<VerifyOtpResponse> {
  return this.http.post<VerifyOtpResponse>(
    AUTH_GOOGLE_VERIFY,
    { credential },
    { withCredentials: true },
  );
}
```

Note the `withCredentials:true` (matches `verifyOtp`) — required for the refresh cookie. The credential is sent in the body, never logged, never persisted.

### B.3 Contract reconciliation checklist (with backend doc)

| Item | FE assumption | Must match BE doc |
|---|---|---|
| Path | `POST /api/v1/auth/google/verify` | [RECONCILE-BE] |
| Request field | `{ credential: string }` | [RECONCILE-BE] |
| Response | `VerifyOtpResponse` (access_token/expires_in/token_type) | [RECONCILE-BE] |
| Cookie | sets HttpOnly refresh_token, `Path=/api/v1/auth`, same as otp/verify | [RECONCILE-BE] |
| `audience`/client-id | backend verifies the ID token `aud` == our GOOGLE_OAUTH_CLIENT_ID | [RECONCILE-BE] — FE and BE **must** pin the *same* client id |
| Error envelope | `{ detail: string }` with status codes (see §D) | [RECONCILE-BE] |
| New-user onboarding signal | via `/me` `onboarding_complete`, not in verify response | [RECONCILE-BE] (preference) |
| CORS/credentials | if cross-origin apiBase ever used, BE `allow_credentials=True` + origin allowlist | infra/BE |

---

## C. SUCCESS WIRING

### C.1 The duplication problem and the chosen solution

otp-verify's `onSubmit` (L202–251) contains the canonical pattern: `<auth-call> → me → setSession → scheduleRefresh → navigate`, with a graceful `/me`-failure fallback. The Google flow needs the **same** tail. We must not copy-paste this into login + signup (two new copies = three drifting implementations).

**Decision: extract the post-auth tail into a single shared helper, owned by `@mesell/core`, consumed by all three success points (Google-on-login, Google-on-signup, and — as a follow-up refactor — otp-verify).**

Proposed: a method on `AuthService` (cleanest — it already owns `setSession`/`scheduleRefresh` and the `meToUser` mapping logic):

```ts
/**
 * completeLogin — shared post-credential success tail (Google + OTP).
 * Given an access token + expiry from any verify endpoint:
 *   fetch /me → setSession(token, user, expires_in) → (auto scheduleRefresh)
 *   → resolve with the routing target (onboarding gate aware, §F).
 * On /me failure: still set a minimal session (token only) + scheduleRefresh,
 * resolve with a safe default route. NEVER rejects on /me failure (mirrors current fallback).
 */
completeLogin(resp: VerifyOtpResponse): Observable<{ route: string[] }>;
```

This collapses §C's three call sites to:

```ts
this.authApi.googleVerify(credential).pipe(
  switchMap(resp => this.auth.completeLogin(resp)),
  catchError(handleGoogleError),
).subscribe(({ route }) => this.router.navigate(route));
```

`completeLogin` uses `setSession(token, user, expires_in)` — the **3-arg** form that auto-schedules refresh (per `auth.service.ts` L77–83), so we no longer need the explicit `scheduleRefresh` call. The routing target (`/dashboard` vs `/onboarding`) is computed inside `completeLogin` from `me.onboarding_complete` (§F), keeping the gate decision in one place.

**Refactor note (separate, optional):** once `completeLogin` exists, otp-verify's `onSubmit` tail can be migrated to call it too, deleting its duplicated `me→setSession→scheduleRefresh→navigate` block. This is recommended but can be a **follow-up PR** to keep the Google PR focused and low-risk (OQ-5). The Google feature does **not** depend on the otp-verify refactor.

### C.2 Where the GIS-specific glue lives

- The **loader + button render + callback** glue is per-component (login, signup) because the rendered button DOM target is per-page. But the glue is tiny: `ngAfterViewInit → loader.load() → initialize(this.onCredential) → renderButton(buttonEl)`; `onCredential = (resp) => this.onGoogleCredential(resp.credential)`.
- `onGoogleCredential(credential)` sets `googleLoading.set(true)`, then runs the §C.1 pipeline.
- To avoid duplicating even this small glue across login + signup, an **optional** shared `GoogleSignInButtonComponent` (a `mee-*`-style composite in `@mesell/composites`) could encapsulate the loader+render+callback and emit `(credential)`/`(error)` outputs, leaving each page to wire only the success pipeline. This is the cleaner long-term shape (OQ-3) — recommended.

---

## D. UI / UX

### D.1 Placement and layout (login + signup)

Insert **below** the phone form, separated by an "or" divider, on both pages:

```
[ MeeSell logo ]
Welcome back / Create your account
─ phone form (unchanged) ─
[ Continue → ] (phone)

      ──────  or  ──────

[  G  Continue with Google  ]   ← GIS-rendered button (full width)

(error banner appears at top, existing position)
```

- Divider: a thin centred rule with the word "or" — a small presentational element (local styles, design tokens, no new ui-kit primitive needed; or a trivial `mee-divider` if we want reuse — OQ-3 ties in).
- The Google button is **GIS-rendered** (we do not style a `mee-button` to look like Google — Google's branding guidelines require their button). It sits in a `<div #googleBtn>` whose width we pass to `renderButton(width)` so it matches the phone CTA width.
- The existing per-page error banner (`mee-alert-banner`) at the top is reused for Google errors too (§D.3).

### D.2 Loading / disabled states

- A dedicated `googleLoading` signal per page (separate from the phone `loading` signal).
- While `googleLoading()` is true: overlay a spinner/disabled veil on the Google button area, and **disable the phone form's submit** (`[disabled]="form.invalid || loading() || googleLoading()"`) so the two flows can't race.
- Conversely, while phone `loading()` is true, the Google button area is visually disabled (the GIS button cannot be truly disabled, so we cover it with a click-blocking overlay + `aria-disabled`).
- The GIS button has its own internal click→popup state; our `googleLoading` covers the **post-credential** network call (`googleVerify → me`).

### D.3 Error handling (surfaced via existing `mee-alert-banner`)

| Failure | Detection | User-facing message (banner `variant="error"`) |
|---|---|---|
| User closed the Google popup / dismissed One-Tap | GIS callback never fires; or `prompt` `notDisplayed/skipped` moment (One-Tap only). For the rendered button, a closed popup simply yields no callback — no banner needed (user chose to cancel). | (none — silent; reset `googleLoading` if it was set) |
| GIS script failed to load | `loader.load()` promise rejects (`onerror`) | "Couldn't load Google sign-in. Check your connection and try again." |
| Network error on `googleVerify` (offline / 0 status) | `HttpErrorResponse` status 0 | "You appear to be offline. Please try again." (offline banner from AuthLayout also shows) |
| Backend rejects the credential (invalid/expired ID token, aud mismatch) | 400/401 | "Google sign-in failed. Please try again." |
| Rate limited | 429 | "Too many attempts. Please try again later." |
| Server error | 5xx | "Something went wrong. Please try again." |
| `/me` fails after a successful verify | handled inside `completeLogin` fallback — session still set, route to safe default | (no banner; logged in with minimal user) |

Error copy follows the existing tone in login/signup/otp-verify. Banner auto-focuses (existing `mee-alert-banner` a11y behaviour).

---

## E. CONFIG

### E.1 Adding `googleOauthClientId` to the environment

The client id is **not a secret** (it is public, embedded in the page by design), so it is safe to ship as a compile-time `@mesell/env` value — no runtime secret-injection mechanism is needed. Extend the `Environment` interface:

```ts
// libs/env/environment.interface.ts
export interface Environment {
  readonly production: boolean;
  readonly name: 'development' | 'production';
  readonly apiBase: string;
  /** Google Identity Services OAuth 2.0 Web client id (public; embedded by design). */
  readonly googleOauthClientId: string;
}
```

```ts
// environment.ts (dev)
googleOauthClientId: '<DEV_GOOGLE_WEB_CLIENT_ID>',   // dev OAuth client (authorized origin http://localhost:4200)
// environment.prod.ts (prod)
googleOauthClientId: '<PROD_GOOGLE_WEB_CLIENT_ID>',  // prod OAuth client (authorized origin https://app.meesell.in)
```

### E.2 Dev vs prod Google Cloud OAuth client

- **Two OAuth Web clients** in the Google Cloud console (one dev, one prod), each with its **Authorized JavaScript origins** set:
  - dev: `http://localhost:4200` (the shell dev origin — the user always interacts with the shell, not the remote at :4206, so the **shell origin** must be authorized). **[RECONCILE-BE/infra]** confirm the dev origin sellers/devs actually hit.
  - prod: the production app origin (e.g. `https://app.meesell.in`).
- The **same** client id must be pinned on the backend for `aud` verification (§B.3). FE and BE share the env value source-of-truth conceptually — flag to backend + infra so the three stay in lockstep (mirrors the existing `apiBase`/CORS lockstep note in `environment.ts`).

### E.3 CSP (cross-doc — infra)

GIS requires CSP allowances when CSP lands (currently none — C-CSP-1, Sub-plan 7):
- `script-src https://accounts.google.com/gsi/client`
- `frame-src https://accounts.google.com/gsi/` (the button/One-Tap iframe)
- `connect-src https://accounts.google.com/gsi/` (token issuance)
- `style-src` may need `https://accounts.google.com/gsi/style`

This is **add-only** to whatever CSP infra authors (must not strip the existing CORS / refresh-cookie behaviour). **Memo to infra required** (see §J).

---

## F. NEW-USER / ONBOARDING UX

### F.1 The problem

A brand-new Google user has **no phone number**. The dual-identity model says they can exist with only a Google identity. Today the onboarding gate is Path B: `MeResponse.onboarding_complete` drives the shell nav-item, and post-login navigation goes straight to `/dashboard`.

### F.2 Proposed FE routing (depends on backend dual-identity rules — **[RECONCILE-BE]**)

`completeLogin` (§C.1) computes the route from `/me`:
- if `me.onboarding_complete === false` → navigate to **`/onboarding`** (not `/dashboard`);
- else → `/dashboard`.

This is a small, principled improvement over today's unconditional `/dashboard` and naturally handles the brand-new Google user (who will have `onboarding_complete:false`). It also benefits brand-new OTP users once otp-verify adopts `completeLogin` (§C.1 refactor).

**Caveat / cross-doc dependency:** whether a Google-only user is *required* to capture a phone number (e.g. for OTP fallback, WhatsApp, Meesho compliance) is a **backend/product decision**, not a FE one. Options the backend doc must resolve:
1. Phone is optional for Google users → onboarding does not force phone → current onboarding form's phone field becomes optional for Google-origin users.
2. Phone is required → onboarding must include a phone-capture (+OTP-verify?) step for Google users → a new onboarding sub-step is needed (additional FE work, separate ticket).

**FE flags this as OQ-1 and will not design the phone-capture sub-step until backend rules are locked.** For V1 of *this* feature, FE routes new Google users to existing `/onboarding`; whatever fields onboarding requires is governed by the onboarding feature + backend, unchanged by this doc.

### F.3 `AuthUser` impact

`AuthUser` already carries optional fields and `onboarding_complete`. A Google user with no phone is a concern: `AuthUser.phone` and `MeResponse.phone` are currently **required (non-optional)**. **[RECONCILE-BE]** — if Google users can lack a phone, `MeResponse.phone` may need to become nullable, which ripples to `AuthUser.phone` and `meToUser`. This is a **breaking-ish type change** the backend doc must confirm. Flagged as OQ-4. (If backend always synthesises/requires a phone at onboarding, no change needed.)

---

## G. ACCESSIBILITY & MOBILE

- **Tap targets:** the GIS-rendered button at `size:'large'` is ≥ 44px tall — meets the existing 44px rule used across auth pages. The "or" divider is decorative (`aria-hidden` on the rule, the word "or" as plain text).
- **Mobile (Tirupur sellers, 360px):** the Google button width is set dynamically to the card content width (the auth card is `max-width:440px`, full-width inside). Verify the GIS button renders correctly at 360px (GIS `width` max is 400px — within our card). The phone form remains the primary, lowest-data path; Google is the convenience option. Screenshots at **360px and 1280px** are a merge-gate requirement.
- **A11y:** the GIS button is Google-rendered and ships its own ARIA. Our additions: the "or" divider must not break the heading/landmark order; `googleLoading` veil uses `aria-busy`/`aria-disabled`; error banner reuses the existing focus-on-appear behaviour; keyboard order = phone form → Continue → (divider) → Google button → footer link.
- **Reduced data / blocked-script case:** if GIS fails to load (corporate proxy, ad-blocker), the page **still works** via phone OTP — the Google button area degrades to the load-error banner and the phone form is unaffected. This is a key resilience property for the Indian-seller audience.

---

## H. TEST PLAN (described, not written)

Specs run under the existing Vitest + `@angular/build:unit-test` harness (TestBed auto-init; no setup file). Remote specs are discovered via the `apps/**/*.spec.ts` glob.

### H.1 `AuthApiService` spec (`libs/core/services/auth-api.service.spec.ts` — extend)
- `googleVerify(credential)` POSTs to `/api/v1/auth/google/verify` with body `{credential}` and `withCredentials:true`; returns the `VerifyOtpResponse` shape. (HttpTestingController.)

### H.2 `AuthService` spec (extend) — `completeLogin`
- happy path: given a `VerifyOtpResponse`, calls `me`, calls `setSession(token, user, expires_in)`, returns `{route:['/dashboard']}` when `onboarding_complete:true`.
- onboarding gate: returns `{route:['/onboarding']}` when `onboarding_complete:false`.
- `/me` failure: still sets a minimal session, schedules refresh, returns a safe default route, never errors.

### H.3 `GoogleIdentityService` spec (new)
- `load()` is idempotent (second call resolves without re-injecting); rejects on script `onerror`; resolves immediately if `window.google.accounts.id` pre-exists. (Mock `document.createElement`/`window.google`.)
- `initialize`/`renderButton` delegate to the mocked `google.accounts.id` with the env client id.

### H.4 `LoginComponent` / `SignupComponent` specs (extend)
- renders the Google button container; calls `loader.load → initialize → renderButton` on `ngAfterViewInit`.
- `onGoogleCredential` → calls `authApi.googleVerify` then `auth.completeLogin` then `router.navigate(route)`.
- error matrix (§D.3): load-failure banner, 400/401 banner, 429 banner, offline banner; `googleLoading` resets in every error branch.
- phone form is disabled while `googleLoading()` and vice-versa.

### H.5 `GoogleSignInButtonComponent` spec (if OQ-3 adopts the shared composite)
- emits `(credential)` on callback, `(error)` on load failure; renders into its `ViewChild` host.

### H.6 Integration smoke (optional, shell-level)
- mirror the SP06 C4 write smoke: a successful Google verify mutates the shared `@mesell/core` AuthService singleton (`isAuthenticated()` flips true) across the federation boundary.

---

## I. OPEN QUESTIONS / FOUNDER DECISIONS

| # | Question | Owner | FE recommendation |
|---|---|---|---|
| **OQ-1** | Is a phone number **required** for Google-only users (onboarding phone-capture step), or optional? Drives whether onboarding needs a new sub-step. | Founder + backend | Make phone **optional** for Google users in V1; defer phone-capture-with-OTP to a follow-up if compliance demands it. |
| **OQ-2** | Enable **One-Tap** (`prompt()`) in V1, or rendered button only? | Founder | Rendered button only for V1; One-Tap additive later. |
| **OQ-3** | Extract a shared `GoogleSignInButtonComponent` composite (+ optional `mee-divider`) vs inline glue in each page? | Frontend Lead | Extract the shared composite — removes login/signup duplication, single test surface. |
| **OQ-4** | Can `MeResponse.phone` / `AuthUser.phone` be **null** for Google users? (Breaking-ish type change if yes.) | Backend | Keep `phone` required by synthesising/forcing it at onboarding; otherwise FE makes both nullable. |
| **OQ-5** | Refactor otp-verify to also use `completeLogin` in the same PR, or a follow-up? | Frontend Lead | Follow-up PR — keep the Google PR focused/low-risk. |
| **OQ-6** | Onboarding-gate redirect (`onboarding_complete:false → /onboarding`) applies to **all** logins now (OTP + Google) — acceptable behaviour change? | Founder | Yes — it is the correct gate behaviour and harmless for existing complete users. |
| **OQ-7** | Direct GIS script (no wrapper lib) + hand-rolled minimal `window.google` typing — confirm we avoid `@abacritt/angularx-social-login` and `@types/google.accounts`? | Frontend Lead | Confirm: direct GIS keeps the federation share-graph + CSP surface minimal. |
| **OQ-8** | Dev/prod Google OAuth client ids + **authorized JS origins** (shell origin, not remote :4206). Who provisions the GCP OAuth clients? | Infra/founder | Provision two Web clients; authorize the **shell** origins. |
| **OQ-9** | Is `/api/v1/auth/google/verify` the agreed path + `{credential}` request + `VerifyOtpResponse` response + same refresh cookie? | Backend | Adopt verbatim for symmetry with OTP. |

### Cross-doc dependencies to reconcile before code
- **[RECONCILE-BE]** §B (endpoint/contract), §F.3/OQ-4 (phone nullability), OQ-1 (phone requirement), OQ-9 (path/shapes).
- **Infra:** §E.3 CSP add-only (memo), OQ-8 OAuth client provisioning + authorized origins.

---

## J. Handoffs this design implies (post-approval)

1. **Memo → backend** (`handoff_google_auth_contract.md`): reconcile §B + OQ-1/4/9. Inter-lead request row on `feature_board_frontend.md` (OPEN, 48h SLA).
2. **Memo → infra** (`handoff_google_auth_csp_origins.md`): §E.3 CSP add-only + OQ-8 OAuth client/origins.
3. No code, no specialist dispatch until: founder approves this doc **and** the backend contract is reconciled. Then standard HYBRID dispatch — service-builder (`AuthApiService.googleVerify` + `GoogleIdentityService` + `AuthService.completeLogin`), component-builder (login/signup button wiring + optional shared composite), ui-styler (divider, loading veil, 360/1280 polish, a11y).
