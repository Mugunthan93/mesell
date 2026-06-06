---
name: section-1-locked
description: FRONTEND_ARCHITECTURE.md §1 LOCKED 2026-06-05 post backend ratification of FE-D5+FE-D6 with 3 founder-ratified strengthenings (Lua EVAL, HMAC-pepper, Path=/api/v1/auth)
metadata:
  type: project
---

# FRONTEND_ARCHITECTURE.md §1 LOCKED 2026-06-05

## Lock chain of custody

1. Founder ratified Angular 18 framework 2026-06-05 — gated all §0 LOCK
2. Founder reviewed §1 + flagged JWT-in-localStorage as unacceptable
3. Frontend coordinator authored FE-D5 + FE-D6 + 7-item handoff memo to backend
4. Backend coordinator ratified all 7 deltas + added 3 substantive engineering strengthenings (all founder-ratified per STATUS_MASTER.md 2026-06-05)
5. Frontend coordinator reconciled FE doc against backend ratification — 6 edits
6. §1 STATUS: DRAFT → LOCKED 2026-06-05

## The 3 backend strengthenings (binding contract for FE specialists)

**S1 — Lua EVAL for refresh rotation atomicity** (over MULTI/EXEC).
- Single round-trip atomic CAS, no WATCH race window
- `SCRIPT LOAD` once at startup → `EVALSHA` thereafter → `EVAL` fallback on `NOSCRIPT` post-restart
- **Frontend impact: zero** — backend implementation detail. Frontend just calls `/api/v1/auth/refresh` and trusts the response.

**S2 — HMAC-SHA256 with `REFRESH_TOKEN_PEPPER` for Valkey keyspace** (over plain SHA-256).
- Keyspace: `cache:refresh:{hmac_sha256(token, REFRESH_TOKEN_PEPPER)}` in Valkey DB 0
- Rationale: Valkey-only breach yields nothing without Secret Manager-stored pepper
- `REFRESH_TOKEN_PEPPER` is NOT YET POPULATED — infra-builder writes it during auth-builder dispatch
- **Frontend impact: minor — documentation accuracy.** Updated FE-D5 + §1.B + §1.F + §4 to reference HMAC-with-pepper. Added §22A risk 11 to track the infra dependency.

**S3 — Cookie `Path=/api/v1/auth`** (corrected from my memo's `Path=/auth`).
- The endpoints are mounted at `/api/v1/auth/refresh` and `/api/v1/auth/logout`
- Browser cookie Path matching is prefix-based. `Path=/auth` would never have matched these requests — refresh flow would have silently failed.
- This is a bug fix to my memo, not a design call.
- **Frontend impact: 4 places updated** — FE-D5 ruling, §1.B cookie-flow appendix, §1.F split-storage table, §4 logout flow.

## How to apply

**For me (coordinator) — going forward:**
- The cookie attribute set is now: `HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth; Domain=.mesell.xyz; Max-Age=<env-driven>`. This is the canonical form for any doc reference.
- The Valkey allowlist keyspace is `cache:refresh:{hmac_sha256(token, REFRESH_TOKEN_PEPPER)}`. Never plain sha256.
- The rotation mechanism is Lua `EVAL` (atomic, single round-trip). If a future doc needs to describe rotation, cite this.
- §1 LOCK is now binding. No further amendments without founder turn.

**For specialists I dispatch:**
- `meesell-angular-service-builder` (first recommended dispatch — service layer is feature-agnostic):
  - `AuthService` MUST hold access token in memory only (signal). No localStorage write. EVER.
  - `AuthService.bootstrap()` fires `POST /api/v1/auth/refresh` (full path), not `/auth/refresh`.
  - All `/api/v1/auth/*` HttpClient calls use `withCredentials: true` so the refresh cookie travels.
  - `RefreshInterceptor` deduplicates concurrent refresh calls via shared `Observable` (single in-flight refresh per AuthService instance).
  - `AuthService.scheduleRefresh(expires_in - 30)` reads from the response — no env coupling.
  - `AuthService.logout()` fires `POST /api/v1/auth/logout`, clears the in-memory accessToken signal, navigates to `/`.
- `meesell-angular-component-builder` (later dispatch):
  - Navbar logout button calls `AuthService.logout()` — does NOT manage tokens itself.
  - OTP verify component receives `{access_token, expires_in}` from the verify response and passes to `AuthService.setAccess()`.

## Pre-deploy checklist (added to STATUS_FRONTEND hand-off)

Before the frontend deploy can ship:
- [ ] Backend iam module deployed (auth endpoints live)
- [ ] `REFRESH_TOKEN_PEPPER` populated in Secret Manager (otherwise refresh returns 500)
- [ ] CORS confirmed on `api.mesell.xyz` for `/api/v1/auth/*` with `Access-Control-Allow-Credentials: true` and explicit Origin allowlist
- [ ] Refresh cookie `Domain=.mesell.xyz` confirmed in Set-Cookie response from backend
- [ ] Smoke test: OTP verify → refresh (with short `ACCESS_TOKEN_TTL_SECONDS=30` in staging) → logout → refresh returns 401

The first 3 items are infra-builder responsibilities. Items 4-5 are auth-builder responsibilities. Frontend coordinator tracks but does not own.
