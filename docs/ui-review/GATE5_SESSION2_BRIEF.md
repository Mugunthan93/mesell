# Gate 5 — `mesell-ui-review-session-2` Launch Brief

**Authored:** 2026-06-13 by `meesell-frontend-coordinator` (frontend lead)
**Session to launch:** `mesell-ui-review-session-2`
**Supersedes:** the session-1 setup (`GATE5_FINDINGS.md` header) — route table corrected from live config below.

---

## 1. Purpose & precondition

- **Goal:** complete the Gate 5 founder-eyes visual pass. Session-1 reviewed **0/14 routes** — it was blocked at route 1 by **F-001** (shell blank-screen, P0).
- **Precondition CLEARED:** F-001 is **RESOLVED** — PR **#203**, squash `1ae5939` (now develop tip). The shell bootstraps in a real browser (lead-verified headless-Chromium boot smoke: 6/6 routes PASS, `/login` renders the real mfe-auth form, zero "Unable to resolve specifier"). Fix = approach (a) barrel imports for `@mesell/ui-kit/*` + approach (c) unshare `@primeuix/themes` in all 7 `federation.config.js`.
- **Gate state:** UNBLOCKED to schedule, NOT yet passed. This session walks the routes and renders a PASS / FAIL / CONDITIONAL verdict.

---

## 2. Dev-server setup — 7 servers

Run each in its own terminal from `frontend/` (pnpm workspace root):

| # | Command | Project | Port |
|---|---------|---------|------|
| 1 | `pnpm start:shell` | shell (host) | **4200** |
| 2 | `pnpm start:mfe-pricing` | mfe-pricing | **4201** |
| 3 | `pnpm start:mfe-export` | mfe-export | **4202** |
| 4 | `pnpm start:mfe-onboarding` | mfe-onboarding | **4203** |
| 5 | `pnpm start:mfe-dashboard` | mfe-dashboard | **4204** |
| 6 | `pnpm start:mfe-catalog` | mfe-catalog | **4205** |
| 7 | `pnpm start:mfe-auth` | mfe-auth | **4206** |

Ports are pinned in `frontend/angular.json` (serve target per project) and in `frontend/apps/shell/public/federation.manifest.json`. `start:shell` = `ng serve frontend --port 4200`; the rest inherit their port from angular.json.

**`ERR_PNPM_IGNORED_BUILDS` is already fixed on develop** — the `pnpm-workspace.yaml` `allowBuilds` entries were committed `true` under #203 (`1ae5939`). `pnpm start:*` will not hit the ignored-builds hard-fail. If a fresh worktree still trips it, run `pnpm install --config.dangerously-allow-all-builds=true` once.

### Pre-flight (run BEFORE reviewing — proves the F-001 fix holds locally)

```bash
# 1) every remoteEntry.json returns 200
for p in 4201 4202 4203 4204 4205 4206; do \
  echo -n "$p: "; curl -s -o /dev/null -w "%{http_code}\n" http://localhost:$p/remoteEntry.json; done
# expect: all 200

# 2) the F-001 smoke proof — /login renders the REAL login form, NOT a blank screen
#    Open http://localhost:4200/login in the browser. EXPECT: "Welcome back" heading +
#    the +91 mobile-number input + "Continue →" button (the mfe-auth LoginComponent).
#    If blank white screen → STOP, F-001 has regressed, escalate to master session.
```

A non-empty body alone is NOT proof (a 404 page is non-empty). Confirm the **actual login form selector** (`mee-login` / "Welcome back" heading) is mounted — this is the anti-false-pass check that F-001 taught us.

---

## 3. Browser

- **Safari Responsive Design Mode** (founder is Safari-only — no Chrome, resource constraint).
- Review **every route at 360px AND 1280px** (mobile + desktop).
- **Carry-forward (NOT a Gate 5 blocker):** target users are Android/Chrome. An Android-phone-over-LAN (or headless Playwright) Chrome-engine spot-check is recommended **pre-prod**, but does not block this gate.

---

## 4. AUTH PREREQUISITE — dev-login path (INVESTIGATED — read this before reviewing guarded routes)

Many routes are behind `authGuard` (dashboard, all `/catalogs/*`, `/profile`, `/onboarding`). The guard logic (`frontend/libs/core/guards/auth.guard.ts`) is:

```ts
if (auth.isAuthenticated()) return true;
return router.createUrlTree(['/login']);
```

and `isAuthenticated` (`frontend/libs/core/services/auth.service.ts:49`) is purely:

```ts
readonly isAuthenticated = computed(() => this._token() !== null);
```

— an **in-memory signal**, set only by `AuthService.setSession(token, user)`. There is **no localStorage / cookie hydration on the frontend** for the guard.

### Finding: there is NO frontend dev-OTP bypass, and NO backend test-OTP

Traced end to end:
- `LoginComponent.onSubmit()` → `AuthApiService.sendOtp()` → **real** `POST /api/v1/auth/otp/send`.
- `OtpVerifyComponent.onSubmit()` → `AuthApiService.verifyOtp()` → **real** `POST /api/v1/auth/otp/verify` → then `setSession()`.
- Backend `iam/service.py::send_otp_for_login` generates a **crypto-random** 6-digit OTP (`secrets.choice`), stores **only its SHA-256 hash** in Valkey (TTL 300 s), and dispatches it **exclusively via the live MSG91 vendor API** (`adapters/msg91.py`). The OTP plaintext is **NEVER logged, never returned** (locked invariant, `service.py` L9). There is **no `DEV_MODE` / `TEST_OTP` / fixed-OTP / console-log fallback** anywhere in the IAM module or msg91 adapter (grep-confirmed).
- The frontend has **no `proxy.conf.json`** and angular.json declares no `proxyConfig`, so on a pure `ng serve` dev stack `/api/v1/*` calls go nowhere (no backend wired into :4200).

**Consequence:** a founder running ONLY the 7 frontend dev servers **cannot complete a real OTP login** — there is no backend, and even with one, the OTP arrives by real SMS via MSG91.

### Recommended dev-login path for session-2 (no backend required)

Because the guard reads only the in-memory `_token` signal, inject a session directly in the browser console after the shell boots. The robust intent is:

> Resolve the root `AuthService` singleton and call
> `setSession('dev-token', { phone: '+919876543210', user_id: 'dev', plan: 'free' })`.
> `isAuthenticated()` then returns true and every `authGuard` route renders **without a backend**.

In Angular dev-mode (`ng serve` is non-optimized), the global `ng` debug API is normally available. From any shell route (e.g. `http://localhost:4200/login`), open the Safari Web Inspector console and resolve `AuthService` via the injector on `app-root`, then call `setSession(...)` on it.

> **OPEN SETUP QUESTION for the founder / master session** — confirm the exact console one-liner works against this dev build (whether `ng.getInjector(...)` can reach the `AuthService` class token cleanly). Capture the working snippet during pre-flight.

**Alternative (cleaner, may need a tiny dev-only hook):** if `ng.getInjector` cannot reach `AuthService` cleanly, the master session can add a **dev-only** `window.__authDev = (auth) => auth.setSession(...)` shim in `main.ts` behind an `isDevMode()` check (a separate tracked frontend task — NOT done in this brief, flagged so the founder isn't blocked).

### OPEN setup questions for the founder (resolve BEFORE the guarded-route portion)

1. **Is a backend even expected on the dev stack for Gate 5?** If yes, the founder needs: backend running + `proxy.conf.json` wiring `/api` → backend + a way to receive the MSG91 SMS on a real phone (or a backend-side test OTP that does not currently exist).
2. **If no backend (frontend-only review):** confirm the `ng.getInjector(...).setSession(...)` console one-liner works in dev mode, OR approve the small `isDevMode()` `window.__authDev` shim. **This is the one thing that may block the guarded-route half of session-2.**
3. Public routes (`/`, `/login`, `/signup`, `/otp-verify`) need **no** auth and can be reviewed immediately regardless.

---

## 5. Accurate route inventory (derived from live config 2026-06-13)

Sources: `frontend/apps/shell/src/app/app.routes.ts`, `federation.manifest.json`, each remote's `federation.config.js` exposes, and `mfe-catalog/src/app/catalog.routes.ts`.

**Correction vs session-1 table:** auth pages are now **mfe-auth (:4206)** (were "shell-local features/auth"); dashboard + landing are **mfe-dashboard (:4204)** (was shell-local); the entire `/catalogs/*` funnel is **mfe-catalog (:4205)** via a single `loadChildren` ./CatalogRoutes (were shell-local). Profile + onboarding remain **mfe-onboarding (:4203)**.

| # | Route | Auth | Type → Remote (port) | Exposed name | 360px | 1280px |
|---|-------|------|----------------------|--------------|:-----:|:------:|
| 1 | `/` (landing) | public | federated → **mfe-dashboard (:4204)** | `./LandingComponent` | ⬜ | ⬜ |
| 2 | `/login` | public | federated → **mfe-auth (:4206)** | `./LoginComponent` | ⬜ | ⬜ |
| 3 | `/signup` | public | federated → **mfe-auth (:4206)** | `./SignupComponent` | ⬜ | ⬜ |
| 4 | `/otp-verify` | public* | federated → **mfe-auth (:4206)** | `./OtpVerifyComponent` | ⬜ | ⬜ |
| 5 | `/dashboard` | **guard** | federated → **mfe-dashboard (:4204)** | `./DashboardComponent` | ⬜ | ⬜ |
| 6 | `/catalogs` (list) | **guard** | federated → **mfe-catalog (:4205)** | `./CatalogRoutes` → `''` | ⬜ | ⬜ |
| 7 | `/catalogs/new` (smart-picker) | **guard** | federated → **mfe-catalog (:4205)** | `./CatalogRoutes` → `new` | ⬜ | ⬜ |
| 8 | `/catalogs/:id/edit` | **guard** | federated → **mfe-catalog (:4205)** | `./CatalogRoutes` → `:id/edit` | ⬜ | ⬜ |
| 9 | `/catalogs/:id/images` | **guard** | federated → **mfe-catalog (:4205)** | `./CatalogRoutes` → `:id/images` | ⬜ | ⬜ |
| 10 | `/catalogs/:id/preview` | **guard** | federated → **mfe-catalog (:4205)** | `./CatalogRoutes` → `:id/preview` | ⬜ | ⬜ |
| 11 | `/profile` | **guard** | federated → **mfe-onboarding (:4203)** | `./ProfileComponent` | ⬜ | ⬜ |
| 12 | `/onboarding` | **guard** | federated → **mfe-onboarding (:4203)** | `./OnboardingComponent` | ⬜ | ⬜ |
| 13 | `/catalogs/:id/pricing` | **guard** | federated → **mfe-pricing (:4201)** | `./PricingComponent` | ⬜ | ⬜ |
| 14 | `/catalogs/:id/export` | **guard** | federated → **mfe-export (:4202)** | `./ExportComponent` | ⬜ | ⬜ |

\* `/otp-verify` is a public top-level route but self-redirects to `/login` if reached without Router navigation state (`{ phone }`). To review it, arrive via the login flow (enter a number → Continue) OR navigate with `history.state.phone` set. **14 routes total. ALL 6 remotes are exercised.** No route is shell-local anymore except the `ShellComponent` layout wrapper itself (the protected-area chrome).

**For `:id` routes (7, 8, 9, 10, 13, 14):** any placeholder id renders (data is seed/simulated in the remotes). Use e.g. `/catalogs/abc123/pricing`.

---

## 6. Review process & routing rule

1. For each route × width: capture in Safari RDM, note any issue in `docs/ui-review/GATE5_FINDINGS.md` (continue the existing file — append under a new `## mesell-ui-review-session-2` section; do not overwrite session-1 history).
2. Per finding use the F-NNN format already in the file; severity **P0 / P1 / P2** (legend in the findings file).
3. **Routing rule for fixes:**
   - **styling-only** (spacing, color, contrast, overflow, responsive break, typo) → dispatch `meesell-angular-ui-styler` **directly** (lead-owned, fast mode). Record the batch in the "Fix Batches Dispatched" table.
   - **anything logic / routing / services / federation** (blank route, wrong component, guard misfire, remote-load error, data shape) → **finding-only**, hand to the master session. Do NOT attempt a fix in this session.

---

## 7. Fallback test (carried from session-1 — never run; run it this session)

For each of the 6 remotes: kill its dev server, reload its route, confirm `RemoteFailureComponent` renders (icon `cloud_off`, message "This module is temporarily unavailable…", **Retry** CTA — `frontend/apps/shell/src/app/core/remote-failure.component.ts`) **instead of a crash or blank screen**. Then restart the server and confirm the route recovers. The catalog remote degrades the **whole** `/catalogs` sub-tree to a single catch-all fallback route (`loadRemoteRoutesWithFallback`).

| Remote (port) | Route to test | Kill & reload | Fallback shown (not crash) | Restart & recovers |
|---------------|---------------|:-------------:|:--------------------------:|:------------------:|
| mfe-pricing (:4201) | `/catalogs/x/pricing` | ⬜ | ⬜ | ⬜ |
| mfe-export (:4202) | `/catalogs/x/export` | ⬜ | ⬜ | ⬜ |
| mfe-onboarding (:4203) | `/profile` | ⬜ | ⬜ | ⬜ |
| mfe-dashboard (:4204) | `/dashboard` | ⬜ | ⬜ | ⬜ |
| mfe-catalog (:4205) | `/catalogs` | ⬜ | ⬜ | ⬜ |
| mfe-auth (:4206) | `/login` | ⬜ | ⬜ | ⬜ |

Note: dashboard + auth fallbacks were observed working under the F-001 investigation (`handleRemoteLoadError`); confirm formally here.

---

## 8. Session-end requirements

- [ ] `docs/ui-review/GATE5_FINDINGS.md` updated: all findings appended under a session-2 section + the route inventory checkboxes filled + the fallback table filled.
- [ ] A **Gate verdict** recorded in `GATE5_FINDINGS.md`: **PASS / FAIL / CONDITIONAL** (CONDITIONAL = passes except for a tracked styling batch in flight).
- [ ] `docs/status/STATUS_FRONTEND.md` — append an UPDATE block (report format) referencing the gate verdict.
- [ ] If any styling batch was dispatched to `meesell-angular-ui-styler`, append the batch learnings to the ui-styler memory.
- [ ] Close-out report with the handoff list (any P0/P1 federation/logic findings routed to master session; any open setup question).

---

## 9. Carry-forward follow-ups (tracked in `STATUS_FRONTEND.md`, NOT part of session-2 manual review)

(a) **Permanent CI browser-boot smoke gate** — promote the headless browser-boot smoke to a standing CI federation gate with **anti-false-pass selector assertions** (assert the real component selector is mounted AND the route is not a 404 — not merely a non-empty body, which is how F-001 slipped through). Frontend lead + infra/CI. Separate tracked item.

(b) **Authenticated `/profile` card capture** — the deferred visual capture of `/profile` needs a real (or injected) session; it is covered by the §4 dev-login path resolution in this session.

---

**Launch gate:** §2 pre-flight green (6× remoteEntry 200 + `/login` renders the real form) AND §4 open setup question 2 resolved (dev-login path confirmed) → session-2 may run the full 14-route pass. Public routes 1–4 can be reviewed without resolving §4.
